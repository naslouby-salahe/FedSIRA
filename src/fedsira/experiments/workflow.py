from __future__ import annotations

import hashlib
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

import pandas
import torch

from fedsira.datasets.common import Role, role_hash_token
from fedsira.datasets.nbaiot.preprocessing import view_parquet_path
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_CLASS_ORDER,
    NBaiotClass,
    NBaiotDomain,
    nbaiot_domain_hash_token,
)
from fedsira.domain.enums import CapabilityContractScope, RootCause
from fedsira.domain.models import MetricResult
from fedsira.domain.types import (
    ArtifactDigest,
    BooleanValue,
    ClassIndex,
    ClassLabel,
    DerivedSeed,
    ExampleCount,
    FeatureCount,
    FeatureIndex,
    FeatureName,
    FeatureVector,
    PreparedEvidencePresent,
    PreparedViewKey,
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
from fedsira.experiments.scenarios.evidence_scarcity import (
    apply_attacker_induced_common_context,
    apply_shared_spurious_feature,
    relabel_shared_label_error_rows,
    select_shared_label_error_rows,
    select_spurious_feature_rows,
)
from fedsira.experiments.scenarios.heterogeneity import feature_shift_sign
from fedsira.protocol.attacks.source import (
    apply_trigger_transform,
    relabel_triggered_rows_as_benign,
    select_source_backdoor_poison_rows,
)
from fedsira.runtime import framed_bytes


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


def prepared_view_key(domain: NBaiotDomain, class_id: NBaiotClass, role: Role) -> PreparedViewKey:
    return f"{nbaiot_domain_hash_token(domain)}_{class_id.value}_{role_hash_token(role)}"


def real_evidence_available(prepared_root: Path) -> PreparedEvidencePresent:
    return prepared_root.exists() and any(prepared_root.glob("*.parquet"))


def load_prepared_rows(
    prepared_root: Path, domain: NBaiotDomain, class_id: NBaiotClass, role: Role
) -> PreparedRows | None:
    path = view_parquet_path(prepared_root, prepared_view_key(domain, class_id, role))
    if not path.exists():
        return None
    frame: pandas.DataFrame = pandas.read_parquet(path)
    if len(frame) == 0:
        return None
    feature_names = tuple(
        column for column in frame.columns if column not in ("sample_id", "label")
    )
    sample_id_column: pandas.Series[str] = frame["sample_id"].astype(str)
    features = tuple(
        tuple(float(value) for value in row)
        for row in frame[list(feature_names)].itertuples(index=False)
    )
    label_column: pandas.Series[str] = frame["label"].astype(str)
    return PreparedRows(
        sample_ids=tuple(sample_id_column), features=features, labels=tuple(label_column)
    )


def prepared_feature_names(prepared_root: Path) -> tuple[FeatureName, ...] | None:
    parquet_files = tuple(sorted(prepared_root.glob("*.parquet")))
    if not parquet_files:
        return None
    frame: pandas.DataFrame = pandas.read_parquet(parquet_files[0])
    return tuple(column for column in frame.columns if column not in ("sample_id", "label"))


def dataset_manifest_hash(prepared_root: Path) -> ArtifactDigest:
    parquet_files = tuple(sorted(prepared_root.glob("*.parquet")))
    if not parquet_files:
        return "0" * 64
    hasher = hashlib.sha256()
    for path in parquet_files:
        hasher.update(framed_bytes(path.name, path.stat().st_size))
    return hasher.hexdigest()


def tensor_view(
    rows: PreparedRows | None,
) -> tuple[torch.Tensor, torch.Tensor, tuple[ArtifactDigest, ...]] | None:
    if rows is None:
        return None
    features = torch.tensor(rows.features, dtype=torch.float32)
    label_to_index: OrderedDict[ClassLabel, ClassIndex] = OrderedDict(
        (class_id.value, index) for index, class_id in enumerate(NBAIOT_CLASS_ORDER)
    )
    labels = torch.tensor([label_to_index[label] for label in rows.labels], dtype=torch.long)
    return (features, labels, rows.sample_ids)


def domain_anchor_train_feature_mean(
    prepared_root: Path, domain: NBaiotDomain
) -> torch.Tensor | None:
    combined_features: list[torch.Tensor] = []
    for class_id in NBAIOT_CLASS_ORDER:
        if class_id is NBaiotClass.GAFGYT_COMBO:
            continue
        view = tensor_view(load_prepared_rows(prepared_root, domain, class_id, Role.ANCHOR_TRAIN))
        if view is not None:
            features, _labels, _sample_ids = view
            combined_features.append(features)
    return None if not combined_features else torch.cat(combined_features, dim=0).mean(dim=0)


def flat_parameters_identity(flat_parameters: torch.Tensor) -> ArtifactDigest:
    values = flat_parameters.detach().cpu()
    joined = "|".join(repr(values[index].item()) for index in range(values.numel()))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


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


def relabel_shared_label_error_rows_for_scope(
    rows: PreparedRows, scope: EpistemicFailureScope
) -> tuple[PreparedRows, tuple[BooleanValue, ...]]:
    selected = (
        select_shared_label_error_rows(
            rows.sample_ids, scope.strength, scope.attack_generation_seed
        )
        or ()
    )
    selected_ids = frozenset(selected)
    labels_by_row_id = OrderedDict(
        (sample_id, NBaiotClass(label))
        for sample_id, label in zip(rows.sample_ids, rows.labels, strict=True)
    )
    relabeled = relabel_shared_label_error_rows(labels_by_row_id, selected)
    return (
        PreparedRows(
            sample_ids=rows.sample_ids,
            features=rows.features,
            labels=tuple(relabeled[sample_id].value for sample_id in rows.sample_ids),
        ),
        tuple(sample_id not in selected_ids for sample_id in rows.sample_ids),
    )


def mark_epistemic_rows(
    rows: PreparedRows,
    scope: EpistemicFailureScope,
    selected_ids: frozenset[ArtifactDigest],
) -> PreparedRows:
    if not selected_ids:
        return rows
    is_common_context = scope.failure_type is EpistemicFailureType.ATTACKER_INDUCED_COMMON_CONTEXT
    if is_common_context:
        feature_indices = tuple(
            scope.feature_names.index(name) for name in scope.common_context_feature_names
        )
        trigger_value = scope.common_context_trigger_value
    else:
        feature_indices = (scope.feature_names.index(scope.spurious_feature_name),)
        trigger_value = scope.spurious_feature_value
    marked_features: list[tuple[float, ...]] = []
    for sample_id, features in zip(rows.sample_ids, rows.features, strict=True):
        if sample_id not in selected_ids:
            marked_features.append(features)
            continue
        tensor = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
        shifted = (
            apply_attacker_induced_common_context(tensor, feature_indices, trigger_value)
            if is_common_context
            else apply_shared_spurious_feature(tensor, feature_indices[0], trigger_value)
        )
        marked_features.append(tuple(float(value) for value in shifted.squeeze(0)))
    return PreparedRows(
        sample_ids=rows.sample_ids, features=tuple(marked_features), labels=rows.labels
    )


def apply_epistemic_target_marker(rows: PreparedRows, scope: EpistemicFailureScope) -> PreparedRows:
    selected = (
        select_spurious_feature_rows(rows.sample_ids, scope.strength, scope.attack_generation_seed)
        or ()
    )
    return mark_epistemic_rows(rows, scope, frozenset(selected))
