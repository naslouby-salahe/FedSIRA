from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

import torch

from fedsira.attacks import (
    apply_trigger_transform,
    relabel_triggered_rows_as_benign,
    select_source_backdoor_poison_rows,
)
from fedsira.datasets.nbaiot.schema import NBaiotClass
from fedsira.domain.enums import CapabilityContractScope
from fedsira.domain.models import MetricResult
from fedsira.domain.types import (
    ArtifactDigest,
    ClassLabel,
    DerivedSeed,
    ExampleCount,
    FeatureCount,
    FeatureIndex,
    FeatureName,
    FeatureVector,
    Probability,
    TriggerFeatureValue,
)
from fedsira.experiments.definitions import EpistemicFailureType


@dataclass(frozen=True)
class PreparedRows:
    sample_ids: tuple[ArtifactDigest, ...]
    features: tuple[FeatureVector, ...]
    labels: tuple[ClassLabel, ...]

    @property
    def row_count(self) -> ExampleCount:
        return len(self.sample_ids)


@dataclass(frozen=True)
class RealAnchor:
    input_width: FeatureCount
    output_width: FeatureCount
    flat_parameters: torch.Tensor
    dataset_manifest_hash: ArtifactDigest
    round_start_flat_parameters: tuple[torch.Tensor, ...]


@dataclass(frozen=True)
class DomainTargetMetrics:
    target_f1: MetricResult
    supported_macro_f1: MetricResult
    benign_far: MetricResult


@dataclass(frozen=True)
class RootCauseScope:
    contract_scope: CapabilityContractScope
    feature_names: tuple[FeatureName, ...]
    root_cause_a_feature_name: FeatureName
    root_cause_b_feature_name: FeatureName
    shift_value: TriggerFeatureValue
    balanced_selection_seed: DerivedSeed | None = None


@dataclass(frozen=True)
class BackdoorScope:
    attack_generation_seed: DerivedSeed
    poison_fraction: Probability
    trigger_feature_indices: tuple[FeatureIndex, ...]
    trigger_value: TriggerFeatureValue


@dataclass(frozen=True)
class HeterogeneityScope:
    heterogeneity_namespace_seed: DerivedSeed
    selected_feature_names: tuple[FeatureName, ...]
    feature_names: tuple[FeatureName, ...]
    shift_magnitude: TriggerFeatureValue


@dataclass(frozen=True)
class EpistemicFailureScope:
    failure_type: EpistemicFailureType
    strength: TriggerFeatureValue
    attack_generation_seed: DerivedSeed
    feature_names: tuple[FeatureName, ...]
    spurious_feature_name: FeatureName
    spurious_feature_value: TriggerFeatureValue
    common_context_feature_names: tuple[FeatureName, ...]
    common_context_trigger_value: TriggerFeatureValue


def poison_backdoor_rows(rows: PreparedRows, scope: BackdoorScope) -> PreparedRows:
    poisoned_ids = select_source_backdoor_poison_rows(
        rows.sample_ids, scope.poison_fraction, scope.attack_generation_seed
    )
    if not poisoned_ids:
        return rows
    poisoned_id_set = frozenset(poisoned_ids)
    labels_by_row_id = OrderedDict(
        zip(rows.sample_ids, (NBaiotClass(label) for label in rows.labels), strict=True)
    )
    relabeled = relabel_triggered_rows_as_benign(labels_by_row_id, poisoned_ids)
    kept_features: list[tuple[float, ...]] = []
    kept_labels: list[ClassLabel] = []
    for sample_id, features in zip(rows.sample_ids, rows.features, strict=True):
        if sample_id not in poisoned_id_set:
            kept_features.append(features)
            kept_labels.append(relabeled[sample_id].value)
            continue
        triggered = apply_trigger_transform(
            torch.tensor(features, dtype=torch.float32),
            scope.trigger_feature_indices,
            scope.trigger_value,
        )
        kept_features.append(tuple(float(value) for value in triggered))
        kept_labels.append(relabeled[sample_id].value)
    return PreparedRows(
        sample_ids=rows.sample_ids, features=tuple(kept_features), labels=tuple(kept_labels)
    )
