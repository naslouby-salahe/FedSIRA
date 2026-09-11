from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

import torch

from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.evaluation.domain import evaluate_domain, non_source_domains
from fedsira.datasets.nbaiot.learning.post_reference_training import train_domain_reproduction_delta
from fedsira.datasets.nbaiot.scenarios import (
    diagnostic_marker_metric_or_insufficient,
    match_diagnostic_benign_report_test_rows,
    select_spurious_feature_rows,
)
from fedsira.datasets.nbaiot.schema import NBAIOT_CLASS_ORDER, NBaiotClass, NBaiotDomain
from fedsira.datasets.nbaiot.workflow import (
    EpistemicFailureScope,
    PreparedRows,
    RealAnchor,
    load_prepared_rows,
    mark_epistemic_rows,
)
from fedsira.domain.enums import EvaluationInsufficiencyReason
from fedsira.domain.models import MetricResult
from fedsira.domain.types import DomainCount, MasterSeed
from fedsira.evaluation.metrics import supported_macro_f1_harm
from fedsira.evaluation.summaries import equal_weight_domain_mean
from fedsira.experiments.definitions import EpistemicFailureType
from fedsira.learning.model import FedSIRAClassifier, load_flat_trainable_parameters
from fedsira.learning.scoring import logits_for_samples, per_sample_cross_entropy


def _diagnostic_marker_for_domain(
    prepared_root: Path,
    anchor: RealAnchor,
    production_flat: torch.Tensor,
    domain: NBaiotDomain,
    scope: EpistemicFailureScope,
) -> tuple[MetricResult, EvaluationInsufficiencyReason | None]:
    target_rows = load_prepared_rows(
        prepared_root, domain, NBaiotClass.GAFGYT_COMBO, Role.REPORT_TEST
    )
    benign_rows = load_prepared_rows(prepared_root, domain, NBaiotClass.BENIGN, Role.REPORT_TEST)
    if target_rows is None or benign_rows is None:
        return diagnostic_marker_metric_or_insufficient(None, 0.0)
    selected_target_ids = (
        select_spurious_feature_rows(
            target_rows.sample_ids, scope.strength, scope.attack_generation_seed
        )
        or ()
    )
    if not selected_target_ids:
        return diagnostic_marker_metric_or_insufficient(None, 0.0)
    target_index_by_id = OrderedDict(
        (sample_id, index) for index, sample_id in enumerate(target_rows.sample_ids)
    )
    anchor_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(anchor_model, anchor.flat_parameters)
    target_class_index = NBAIOT_CLASS_ORDER.index(NBaiotClass.GAFGYT_COMBO)
    selected_target_features = torch.tensor(
        [target_rows.features[target_index_by_id[sample_id]] for sample_id in selected_target_ids],
        dtype=torch.float32,
    )
    target_confidence_labels = torch.argmax(
        logits_for_samples(anchor_model, selected_target_features), dim=-1
    )
    target_report_losses = tuple(
        zip(
            selected_target_ids,
            (
                float(value)
                for value in per_sample_cross_entropy(
                    anchor_model, selected_target_features, target_confidence_labels
                )
            ),
            strict=True,
        )
    )
    benign_features = torch.tensor(benign_rows.features, dtype=torch.float32)
    benign_confidence_labels = torch.argmax(
        logits_for_samples(anchor_model, benign_features), dim=-1
    )
    benign_report_losses = tuple(
        zip(
            benign_rows.sample_ids,
            (
                float(value)
                for value in per_sample_cross_entropy(
                    anchor_model, benign_features, benign_confidence_labels
                )
            ),
            strict=True,
        )
    )
    matched_pairs = match_diagnostic_benign_report_test_rows(
        target_report_losses, benign_report_losses
    )
    if matched_pairs is None:
        return diagnostic_marker_metric_or_insufficient(None, 0.0)
    matched_benign_ids = tuple(benign_id for _target_id, benign_id in matched_pairs)
    benign_index_by_id = OrderedDict(
        (sample_id, index) for index, sample_id in enumerate(benign_rows.sample_ids)
    )
    matched_benign_rows = PreparedRows(
        sample_ids=matched_benign_ids,
        features=tuple(
            benign_rows.features[benign_index_by_id[sample_id]] for sample_id in matched_benign_ids
        ),
        labels=tuple(NBaiotClass.BENIGN for _ in matched_benign_ids),
    )
    marked_rows = mark_epistemic_rows(matched_benign_rows, scope, frozenset(matched_benign_ids))
    production_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(production_model, production_flat)
    production_model.eval()
    with torch.no_grad():
        marked_features = torch.tensor(marked_rows.features, dtype=torch.float32)
        predictions = torch.argmax(logits_for_samples(production_model, marked_features), dim=-1)
    marker_rate = float((predictions == target_class_index).float().mean())
    return diagnostic_marker_metric_or_insufficient(matched_pairs, marker_rate)


@dataclass(frozen=True)
class SharedEpistemicFailureSummary:
    defined_domain_count: DomainCount
    aggregate_target_f1: MetricResult
    target_f1_gain: MetricResult
    supported_macro_f1_drop: MetricResult
    benign_far_increase: MetricResult
    diagnostic_marker: MetricResult


def compute_shared_epistemic_failure_summary(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
    epistemic_failure_scope: EpistemicFailureScope,
) -> SharedEpistemicFailureSummary:
    target_f1_values: list[MetricResult] = []
    anchor_target_f1_values: list[MetricResult] = []
    supported_f1_harms: list[MetricResult] = []
    benign_far_increases: list[MetricResult] = []
    diagnostic_markers: list[MetricResult] = []
    has_diagnostic_marker = epistemic_failure_scope.failure_type in (
        EpistemicFailureType.SHARED_SPURIOUS_FEATURE,
        EpistemicFailureType.ATTACKER_INDUCED_COMMON_CONTEXT,
    )
    for domain in non_source_domains(source_domain):
        delta = train_domain_reproduction_delta(
            prepared_root,
            master_seed,
            anchor,
            domain,
            epistemic_failure_scope=epistemic_failure_scope,
        )
        if delta is None:
            continue
        production_flat = anchor.flat_parameters + delta
        anchor_metrics = evaluate_domain(
            prepared_root, anchor, anchor.flat_parameters, domain, Role.REPORT_TEST
        )
        production_metrics = evaluate_domain(
            prepared_root, anchor, production_flat, domain, Role.REPORT_TEST
        )
        if anchor_metrics is None or production_metrics is None:
            continue
        target_f1_values.append(production_metrics.target_f1)
        anchor_target_f1_values.append(anchor_metrics.target_f1)
        supported_f1_harms.append(
            supported_macro_f1_harm(
                anchor_metrics.supported_macro_f1, production_metrics.supported_macro_f1
            )
        )
        if anchor_metrics.benign_far.value is None or production_metrics.benign_far.value is None:
            benign_far_increases.append(MetricResult(value=None, denominator=0))
        else:
            benign_far_increases.append(
                MetricResult(
                    value=production_metrics.benign_far.value - anchor_metrics.benign_far.value,
                    denominator=1,
                )
            )
        if has_diagnostic_marker:
            marker_result, _reason = _diagnostic_marker_for_domain(
                prepared_root, anchor, production_flat, domain, epistemic_failure_scope
            )
            diagnostic_markers.append(marker_result)
    aggregate_target_f1 = equal_weight_domain_mean(tuple(target_f1_values), 1)
    anchor_target_f1 = equal_weight_domain_mean(tuple(anchor_target_f1_values), 1)
    target_f1_gain = (
        MetricResult(value=aggregate_target_f1.value - anchor_target_f1.value, denominator=1)
        if aggregate_target_f1.value is not None and anchor_target_f1.value is not None
        else MetricResult(value=None, denominator=0)
    )
    return SharedEpistemicFailureSummary(
        defined_domain_count=len(target_f1_values),
        aggregate_target_f1=aggregate_target_f1,
        target_f1_gain=target_f1_gain,
        supported_macro_f1_drop=equal_weight_domain_mean(tuple(supported_f1_harms), 1),
        benign_far_increase=equal_weight_domain_mean(tuple(benign_far_increases), 1),
        diagnostic_marker=equal_weight_domain_mean(tuple(diagnostic_markers), 1),
    )
