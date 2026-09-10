from __future__ import annotations

from pathlib import Path

import torch

from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_CLASS_ORDER,
    NBAIOT_DOMAIN_ORDER,
    NBAIOT_TRIGGER_FEATURES,
    NBaiotClass,
    NBaiotDomain,
)
from fedsira.domain.models import MetricResult
from fedsira.domain.types import FeatureIndex, FeatureName, MetricValue, TriggerFeatureValue
from fedsira.experiments.scenarios import apply_attacker_induced_common_context
from fedsira.experiments.workflow import (
    RealAnchor,
    load_prepared_rows,
    prepared_feature_names,
    tensor_view,
)
from fedsira.learning.model import FedSIRAClassifier, load_flat_trainable_parameters
from fedsira.learning.scoring import logits_for_samples
from fedsira.protocol.baselines.calibration import recovery_alarm_threshold
from fedsira.runtime import current_application_context


def compute_source_backdoor_asr(
    prepared_root: Path,
    anchor: RealAnchor,
    production_flat_parameters: torch.Tensor,
    source_domain: NBaiotDomain,
    trigger_feature_indices: tuple[FeatureIndex, ...],
    trigger_value: TriggerFeatureValue,
) -> MetricResult:
    rows = tensor_view(
        load_prepared_rows(prepared_root, source_domain, NBaiotClass.GAFGYT_UDP, Role.REPORT_TEST)
    )
    if rows is None:
        return MetricResult(value=None, denominator=0)
    features, _labels, _sample_ids = rows
    triggered_features = features.clone()
    for feature_index in trigger_feature_indices:
        triggered_features[:, feature_index] = trigger_value
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, production_flat_parameters)
    model.eval()
    with torch.no_grad():
        predictions = torch.argmax(logits_for_samples(model, triggered_features), dim=1)
    benign_index = NBAIOT_CLASS_ORDER.index(NBaiotClass.BENIGN)
    asr = float((predictions == benign_index).float().mean())
    return MetricResult(value=asr, denominator=triggered_features.shape[0])


def triggered_to_benign_rate(
    prepared_root: Path,
    anchor: RealAnchor,
    flat_parameters: torch.Tensor,
    domain: NBaiotDomain,
    role: Role,
    trigger_feature_names: tuple[FeatureName, ...],
    trigger_value: TriggerFeatureValue,
) -> MetricResult:
    feature_names = prepared_feature_names(prepared_root)
    rows = load_prepared_rows(prepared_root, domain, NBaiotClass.GAFGYT_UDP, role)
    if feature_names is None or rows is None:
        return MetricResult(value=None, denominator=0)
    trigger_indices = [feature_names.index(name) for name in trigger_feature_names]
    features = torch.tensor(rows.features, dtype=torch.float32)
    triggered_features = apply_attacker_induced_common_context(
        features, trigger_indices, trigger_value
    )
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, flat_parameters)
    model.eval()
    with torch.no_grad():
        predictions = torch.argmax(logits_for_samples(model, triggered_features), dim=-1)
    benign_index = NBAIOT_CLASS_ORDER.index(NBaiotClass.BENIGN)
    rate = float((predictions == benign_index).float().mean())
    return MetricResult(value=rate, denominator=len(rows.sample_ids))


def recovery_backdoor_alarm_threshold(
    prepared_root: Path, anchor: RealAnchor
) -> MetricValue | None:
    config = current_application_context().scientific_config
    trigger_value = (
        config.attacks_and_boundaries.hidden_source_backdoor.trigger_value_after_standardization
    )
    rates: list[MetricValue] = []
    for domain in NBAIOT_DOMAIN_ORDER:
        rate = triggered_to_benign_rate(
            prepared_root,
            anchor,
            anchor.flat_parameters,
            domain,
            Role.ANCHOR_VALIDATION,
            NBAIOT_TRIGGER_FEATURES,
            trigger_value,
        )
        if rate.value is not None:
            rates.append(rate.value)
    if not rates:
        return None
    return recovery_alarm_threshold(
        tuple(rates), config.baselines.recovery_after_source_admission.backdoor_alarm_percentile
    )
