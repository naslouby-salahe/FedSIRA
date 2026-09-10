from __future__ import annotations

from collections import OrderedDict
from collections.abc import Sequence
from pathlib import Path

import torch

from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_CLASS_ORDER,
    NBAIOT_DOMAIN_ORDER,
    NBaiotClass,
    NBaiotDomain,
)
from fedsira.domain.enums import RootCause
from fedsira.domain.types import ArtifactDigest, ClassLabel
from fedsira.evaluation.comparisons import ComparisonMetric
from fedsira.evaluation.metrics import (
    benign_false_alarm_rate,
    compute_confusion_counts_by_class,
    f1_for_class,
    macro_f1,
    metric_value,
    report_metric_set,
)
from fedsira.experiments.scenarios import root_cause_for_sample
from fedsira.experiments.workflow import (
    DomainTargetMetrics,
    HeterogeneityScope,
    RealAnchor,
    RootCauseScope,
    apply_heterogeneity_shift,
    load_prepared_rows,
    scope_and_shift_rows,
    tensor_view,
)
from fedsira.learning.model import FedSIRAClassifier, load_flat_trainable_parameters
from fedsira.learning.scoring import logits_for_samples


def evaluate_domain(
    prepared_root: Path,
    anchor: RealAnchor,
    flat_parameters: torch.Tensor,
    domain: NBaiotDomain,
    role: Role,
    target_role: Role | None = None,
    root_cause_scope: RootCauseScope | None = None,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> DomainTargetMetrics | None:
    true_labels: list[ClassLabel] = []
    predicted_labels: list[ClassLabel] = []
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, flat_parameters)
    model.eval()
    with torch.no_grad():
        for class_id in NBAIOT_CLASS_ORDER:
            row_role = (
                target_role
                if target_role is not None and class_id is NBaiotClass.GAFGYT_COMBO
                else role
            )
            rows = load_prepared_rows(prepared_root, domain, class_id, row_role)
            if (
                class_id is NBaiotClass.GAFGYT_COMBO
                and root_cause_scope is not None
                and rows is not None
            ):
                rows = scope_and_shift_rows(rows, root_cause_scope)
            if rows is not None and heterogeneity_scope is not None:
                rows = apply_heterogeneity_shift(rows, domain, heterogeneity_scope)
            tensor_rows = tensor_view(rows)
            if tensor_rows is None:
                continue
            features, _labels, _sample_ids = tensor_rows
            predictions = torch.argmax(logits_for_samples(model, features), dim=-1)
            predicted_cpu = predictions.detach().cpu()
            prediction_indices = tuple(
                int(predicted_cpu[index].item()) for index in range(predicted_cpu.numel())
            )
            true_labels.extend(class_id.value for _ in range(features.shape[0]))
            predicted_labels.extend(NBAIOT_CLASS_ORDER[index].value for index in prediction_indices)
    if not true_labels:
        return None
    class_tokens = tuple(class_id.value for class_id in NBAIOT_CLASS_ORDER)
    counts_by_class = compute_confusion_counts_by_class(true_labels, predicted_labels, class_tokens)
    f1_by_class = OrderedDict(
        (token, f1_for_class(counts)) for token, counts in counts_by_class.items()
    )
    supported_tokens = tuple(token for token in class_tokens if token != NBaiotClass.GAFGYT_COMBO)
    supported_f1 = OrderedDict(
        (token, f1_by_class[token]) for token in supported_tokens if token in f1_by_class
    )
    report = report_metric_set(
        true_labels,
        predicted_labels,
        class_tokens,
        NBaiotClass.GAFGYT_COMBO,
        NBaiotClass.BENIGN,
        supported_tokens,
    )
    return DomainTargetMetrics(
        target_f1=metric_value(report, ComparisonMetric.TARGET_F1.value),
        supported_macro_f1=macro_f1(supported_f1),
        benign_far=benign_false_alarm_rate(true_labels, predicted_labels, NBaiotClass.BENIGN),
    )


def non_source_domains(source_domain: NBaiotDomain | None) -> tuple[NBaiotDomain, ...]:
    return tuple(domain for domain in NBAIOT_DOMAIN_ORDER if domain != source_domain)


def root_cause_partitioned_row_ids(
    prepared_root: Path, domains: Sequence[NBaiotDomain]
) -> tuple[frozenset[ArtifactDigest], frozenset[ArtifactDigest], frozenset[ArtifactDigest]]:
    root_cause_a_ids: set[ArtifactDigest] = set()
    root_cause_b_ids: set[ArtifactDigest] = set()
    supported_ids: set[ArtifactDigest] = set()
    for domain in domains:
        target_rows = load_prepared_rows(
            prepared_root, domain, NBaiotClass.GAFGYT_COMBO, Role.POST_REFERENCE_REPLAY
        )
        if target_rows is not None:
            for sample_id in target_rows.sample_ids:
                if root_cause_for_sample(sample_id) is RootCause.A:
                    root_cause_a_ids.add(sample_id)
                else:
                    root_cause_b_ids.add(sample_id)
        for class_id in NBAIOT_CLASS_ORDER:
            if class_id is NBaiotClass.GAFGYT_COMBO:
                continue
            supported_rows = load_prepared_rows(
                prepared_root, domain, class_id, Role.POST_REFERENCE_REPLAY
            )
            if supported_rows is not None:
                supported_ids.update(supported_rows.sample_ids)
    return (frozenset(root_cause_a_ids), frozenset(root_cause_b_ids), frozenset(supported_ids))
