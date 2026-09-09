from __future__ import annotations

from dataclasses import dataclass

import torch

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
