from __future__ import annotations

from pathlib import Path

import torch

from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.schema import NBAIOT_CLASS_ORDER, NBaiotClass, NBaiotDomain
from fedsira.domain.models import MetricResult
from fedsira.domain.types import FeatureIndex, TriggerFeatureValue
from fedsira.experiments.workflow import RealAnchor, load_prepared_rows, tensor_view
from fedsira.learning.model import FedSIRAClassifier, load_flat_trainable_parameters
from fedsira.learning.scoring import logits_for_samples


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
