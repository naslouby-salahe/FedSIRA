from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

import torch

from fedsira.attacks import (
    apply_trigger_transform,
    relabel_triggered_rows_as_benign,
    select_source_backdoor_poison_rows,
)
from fedsira.datasets.nbaiot.schema import NBaiotClass, NBaiotDomain
from fedsira.domain.enums import CapabilityContractScope, RootCause
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
from fedsira.experiments.scenarios.capability_granularity import (
    apply_root_cause_feature_shift,
    balanced_capability_selection,
    root_cause_for_sample,
    target_row_ids_for_contract,
)
from fedsira.experiments.scenarios.heterogeneity import feature_shift_sign


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


def apply_heterogeneity_shift(
    rows: PreparedRows, domain: NBaiotDomain, scope: HeterogeneityScope
) -> PreparedRows:
    feature_indices_and_signs = tuple(
        (
            scope.feature_names.index(feature_name),
            feature_shift_sign(domain, feature_name, scope.heterogeneity_namespace_seed),
        )
        for feature_name in scope.selected_feature_names
    )
    shifted_features: list[tuple[float, ...]] = []
    for features in rows.features:
        tensor = torch.tensor(features, dtype=torch.float32)
        for feature_index, sign in feature_indices_and_signs:
            tensor[feature_index] = tensor[feature_index] + sign * scope.shift_magnitude
        shifted_features.append(tuple(float(value) for value in tensor))
    return PreparedRows(
        sample_ids=rows.sample_ids, features=tuple(shifted_features), labels=rows.labels
    )


def scope_and_shift_rows(
    rows: PreparedRows, root_cause_scope: RootCauseScope
) -> PreparedRows | None:
    root_cause_a_ids = frozenset(
        sample_id
        for sample_id in rows.sample_ids
        if root_cause_for_sample(sample_id) is RootCause.A
    )
    root_cause_b_ids = frozenset(rows.sample_ids) - root_cause_a_ids
    if root_cause_scope.balanced_selection_seed is not None:
        selected_a_ids, selected_b_ids = balanced_capability_selection(
            sorted(root_cause_a_ids),
            sorted(root_cause_b_ids),
            root_cause_scope.balanced_selection_seed,
        )
        root_cause_a_ids = frozenset(selected_a_ids)
        root_cause_b_ids = frozenset(selected_b_ids)
    allowed_ids = target_row_ids_for_contract(
        root_cause_scope.contract_scope, root_cause_a_ids, root_cause_b_ids
    )
    a_index = root_cause_scope.feature_names.index(root_cause_scope.root_cause_a_feature_name)
    b_index = root_cause_scope.feature_names.index(root_cause_scope.root_cause_b_feature_name)
    kept_sample_ids: list[ArtifactDigest] = []
    kept_features: list[tuple[float, ...]] = []
    kept_labels: list[ClassLabel] = []
    for sample_id, features, label in zip(rows.sample_ids, rows.features, rows.labels, strict=True):
        if sample_id not in allowed_ids:
            continue
        shifted = apply_root_cause_feature_shift(
            torch.tensor(features, dtype=torch.float32),
            root_cause_for_sample(sample_id),
            a_index,
            b_index,
            root_cause_scope.shift_value,
        )
        kept_sample_ids.append(sample_id)
        kept_features.append(tuple(float(value) for value in shifted))
        kept_labels.append(label)
    if not kept_sample_ids:
        return None
    return PreparedRows(
        sample_ids=tuple(kept_sample_ids), features=tuple(kept_features), labels=tuple(kept_labels)
    )
