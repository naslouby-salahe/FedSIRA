from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas
import torch

from fedsira.baselines.calibration import (
    clip_source_update,
    cosine_distance_matrix,
    density_cluster_labels,
    l2_normalize,
    sanitization_clip_bounds,
    select_largest_density_cluster,
    trimmed_mean_aggregate,
)
from fedsira.baselines.references import (
    centralized_reference_local_epochs,
    centralized_reference_pooled_rows,
    fedavg_reference_post_reference_local_epochs,
    fedavg_reference_post_reference_participants,
    fedavg_reference_post_reference_rounds,
    local_only_reference_local_epochs,
    local_only_reference_training_role,
)
from fedsira.baselines.registry import POST_REFERENCE_RETRAIN_MAXIMUM_LOCAL_EPOCHS
from fedsira.baselines.robust_aggregation import (
    client_sampling_round_order,
    krum_reference_post_reference_rounds,
    krum_reference_round_participants,
)
from fedsira.baselines.source_authority import secure_continual_assessment_post_reference_rounds
from fedsira.boundaries.capability_granularity import (
    apply_root_cause_feature_shift,
    root_cause_for_sample,
    target_row_ids_for_contract,
)
from fedsira.boundaries.epistemic_failure import (
    apply_attacker_induced_common_context,
    apply_shared_spurious_feature,
    diagnostic_marker_metric_or_insufficient,
    match_diagnostic_benign_report_test_rows,
    relabel_shared_label_error_rows,
    select_shared_label_error_rows,
    select_spurious_feature_rows,
)
from fedsira.config.schema import ScientificConfig
from fedsira.datasets.common import ROLE_HASH_TOKEN, Role
from fedsira.datasets.nbaiot.materialization import view_parquet_path
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_CLASS_ORDER,
    NBAIOT_DOMAIN_HASH_TOKEN,
    NBAIOT_DOMAIN_ORDER,
    NBaiotClass,
    NBaiotDomain,
)
from fedsira.domain.enums import (
    CapabilityContractScope,
    EvaluationInsufficiencyReason,
    RootCause,
    SeedNamespace,
)
from fedsira.domain.records import ArtifactDigest, CanonicalToken, DerivedSeed, MasterSeed
from fedsira.evaluation.aggregation import (
    coefficient_of_variation,
    domain_disparity,
    equal_weight_domain_mean,
    interquartile_range,
    percentile_10_domain_target_f1,
    worst_domain_target_f1,
)
from fedsira.evaluation.metrics import (
    benign_false_alarm_rate,
    compute_confusion_counts_by_class,
    f1_for_class,
    macro_f1,
    supported_macro_f1_harm,
)
from fedsira.evaluation.records import MetricResult
from fedsira.evaluation.screen import (
    ScreenLossObservation,
    run_proposal_screen_for_domain,
    screen_fold_index,
)
from fedsira.experiments.registry import EpistemicFailureType, ReproducerCondition
from fedsira.learning.anchor import run_anchor_fedavg_training
from fedsira.learning.federated import run_fedavg_round, train_one_client_locally
from fedsira.learning.post_reference import run_post_reference_training
from fedsira.learning.scoring import logits_for_samples
from fedsira.models.mlp import (
    FedSIRAClassifier,
    flatten_trainable_parameters,
    load_flat_trainable_parameters,
)
from fedsira.protocol.synthesis import CertifiedReproductionRow, select_krum_update
from fedsira.runtime.determinism import (
    canonical_bytes,
    derive_uint32,
    local_training_seed,
    namespace_seed,
    seed_job_local_rng_streams,
)

ANCHOR_TRAINING_ALGORITHM_TOKEN = "ANCHOR_FEDAVG"
SOURCE_TRAINING_ALGORITHM_TOKEN = "SOURCE_CANDIDATE"
REPRODUCTION_TRAINING_ALGORITHM_TOKEN = "REPRODUCTION"
FEDAVG_REFERENCE_TRAINING_ALGORITHM_TOKEN = "FEDAVG_REFERENCE"
SECURE_CONTINUAL_ASSESSMENT_TRAINING_ALGORITHM_TOKEN = "SECURE_CONTINUAL_ASSESSMENT"
LOCAL_ONLY_REFERENCE_TRAINING_ALGORITHM_TOKEN = "LOCAL_ONLY_REFERENCE"
CENTRALIZED_REFERENCE_TRAINING_ALGORITHM_TOKEN = "CENTRALIZED_REFERENCE"
DENSITY_CLUSTER_TRIMMED_MEAN_TRAINING_ALGORITHM_TOKEN = "DENSITY_CLUSTER_TRIMMED_MEAN"
CALIBRATION_TRAINING_ALGORITHM_TOKEN = "ANCHOR_ROUND_CALIBRATION"
CLEAN_TRAINING_CONDITION_TOKEN = ReproducerCondition.CLEAN.value


@dataclass(frozen=True)
class PreparedRows:
    sample_ids: tuple[ArtifactDigest, ...]
    features: tuple[tuple[float, ...], ...]
    labels: tuple[CanonicalToken, ...]

    @property
    def row_count(self) -> int:
        return len(self.sample_ids)


@dataclass(frozen=True)
class RealAnchor:
    input_width: int
    output_width: int
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
    feature_names: tuple[CanonicalToken, ...]
    root_cause_a_feature_name: CanonicalToken
    root_cause_b_feature_name: CanonicalToken
    shift_value: float


def _scope_and_shift_rows(
    rows: PreparedRows, root_cause_scope: RootCauseScope
) -> PreparedRows | None:
    root_cause_a_ids = frozenset(
        sample_id
        for sample_id in rows.sample_ids
        if root_cause_for_sample(sample_id) is RootCause.A
    )
    root_cause_b_ids = frozenset(rows.sample_ids) - root_cause_a_ids
    allowed_ids = target_row_ids_for_contract(
        root_cause_scope.contract_scope, root_cause_a_ids, root_cause_b_ids
    )
    a_index = root_cause_scope.feature_names.index(root_cause_scope.root_cause_a_feature_name)
    b_index = root_cause_scope.feature_names.index(root_cause_scope.root_cause_b_feature_name)
    kept_sample_ids: list[ArtifactDigest] = []
    kept_features: list[tuple[float, ...]] = []
    kept_labels: list[CanonicalToken] = []
    for sample_id, features, label in zip(rows.sample_ids, rows.features, rows.labels, strict=True):
        if sample_id not in allowed_ids:
            continue
        row_root_cause = root_cause_for_sample(sample_id)
        shifted = apply_root_cause_feature_shift(
            torch.tensor(features, dtype=torch.float32),
            row_root_cause,
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
        sample_ids=tuple(kept_sample_ids),
        features=tuple(kept_features),
        labels=tuple(kept_labels),
    )


@dataclass(frozen=True)
class EpistemicFailureScope:
    failure_type: EpistemicFailureType
    strength: float
    attack_generation_seed: DerivedSeed
    feature_names: tuple[CanonicalToken, ...]
    spurious_feature_name: CanonicalToken
    spurious_feature_value: float
    common_context_feature_names: tuple[CanonicalToken, ...]
    common_context_trigger_value: float


def _relabel_shared_label_error_rows(
    rows: PreparedRows, scope: EpistemicFailureScope
) -> tuple[PreparedRows, tuple[bool, ...]]:
    selected = (
        select_shared_label_error_rows(
            rows.sample_ids, scope.strength, scope.attack_generation_seed
        )
        or ()
    )
    selected_ids = frozenset(selected)
    labels_by_row_id = {
        sample_id: NBaiotClass(label)
        for sample_id, label in zip(rows.sample_ids, rows.labels, strict=True)
    }
    relabeled = relabel_shared_label_error_rows(labels_by_row_id, selected)
    new_labels = tuple(relabeled[sample_id].value for sample_id in rows.sample_ids)
    is_supported_mask = tuple(sample_id not in selected_ids for sample_id in rows.sample_ids)
    return (
        PreparedRows(sample_ids=rows.sample_ids, features=rows.features, labels=new_labels),
        is_supported_mask,
    )


def _mark_rows(
    rows: PreparedRows, scope: EpistemicFailureScope, selected_ids: frozenset[ArtifactDigest]
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
        if is_common_context:
            shifted = apply_attacker_induced_common_context(tensor, feature_indices, trigger_value)
        else:
            shifted = apply_shared_spurious_feature(tensor, feature_indices[0], trigger_value)
        marked_features.append(tuple(float(value) for value in shifted.squeeze(0)))
    return PreparedRows(
        sample_ids=rows.sample_ids, features=tuple(marked_features), labels=rows.labels
    )


def _apply_epistemic_target_marker(
    rows: PreparedRows, scope: EpistemicFailureScope
) -> PreparedRows:
    selected = (
        select_spurious_feature_rows(rows.sample_ids, scope.strength, scope.attack_generation_seed)
        or ()
    )
    return _mark_rows(rows, scope, frozenset(selected))


def _view_key(domain: NBaiotDomain, class_id: NBaiotClass, role: Role) -> CanonicalToken:
    return f"{NBAIOT_DOMAIN_HASH_TOKEN[domain]}_{class_id.value}_{ROLE_HASH_TOKEN[role]}"


def real_evidence_available(prepared_root: Path) -> bool:
    return prepared_root.exists() and any(prepared_root.glob("*.parquet"))


def load_prepared_rows(
    prepared_root: Path, domain: NBaiotDomain, class_id: NBaiotClass, role: Role
) -> PreparedRows | None:
    path = view_parquet_path(prepared_root, _view_key(domain, class_id, role))
    if not path.exists():
        return None
    frame: pandas.DataFrame = pandas.read_parquet(path)
    if len(frame) == 0:
        return None
    feature_names = tuple(
        column for column in frame.columns if column not in ("sample_id", "label")
    )
    sample_ids = tuple(str(value) for value in frame["sample_id"])
    features = tuple(
        tuple(float(value) for value in row)
        for row in frame[list(feature_names)].itertuples(index=False)
    )
    labels = tuple(str(value) for value in frame["label"])
    return PreparedRows(sample_ids=sample_ids, features=features, labels=labels)


def prepared_feature_names(prepared_root: Path) -> tuple[CanonicalToken, ...] | None:
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
        hasher.update(canonical_bytes(path.name, path.stat().st_size))
    return hasher.hexdigest()


def _tensor_view(
    rows: PreparedRows | None,
) -> tuple[torch.Tensor, torch.Tensor, tuple[ArtifactDigest, ...]] | None:
    if rows is None:
        return None
    features = torch.tensor(rows.features, dtype=torch.float32)
    label_to_index = {class_id.value: index for index, class_id in enumerate(NBAIOT_CLASS_ORDER)}
    labels = torch.tensor([label_to_index[label] for label in rows.labels], dtype=torch.long)
    return features, labels, rows.sample_ids


def _training_seed(
    master_seed: MasterSeed,
    manifest_hash: ArtifactDigest,
    start_checkpoint_identity: ArtifactDigest,
    algorithm_token: CanonicalToken,
    domain: NBaiotDomain,
    round_index: int,
) -> DerivedSeed:
    local_training_namespace_seed = namespace_seed(master_seed, SeedNamespace.LOCAL_TRAINING)
    return local_training_seed(
        local_training_namespace_seed,
        manifest_hash,
        start_checkpoint_identity,
        algorithm_token,
        NBAIOT_DOMAIN_HASH_TOKEN[domain],
        CLEAN_TRAINING_CONDITION_TOKEN,
        round_index,
    )


def _flat_parameters_identity(flat_parameters: torch.Tensor) -> ArtifactDigest:
    return hashlib.sha256(flat_parameters.detach().cpu().numpy().tobytes()).hexdigest()


def train_anchor(
    prepared_root: Path, config: ScientificConfig, master_seed: MasterSeed
) -> RealAnchor | None:
    first_rows = load_prepared_rows(
        prepared_root, NBAIOT_DOMAIN_ORDER[0], NBaiotClass.BENIGN, Role.ANCHOR_TRAIN
    )
    if first_rows is None:
        return None
    input_width = len(first_rows.features[0])
    output_width = len(NBAIOT_CLASS_ORDER)
    manifest_hash = dataset_manifest_hash(prepared_root)
    initialization_seed = namespace_seed(master_seed, SeedNamespace.MODEL_INITIALIZATION)
    seed_job_local_rng_streams(initialization_seed)
    initial_state = FedSIRAClassifier(input_width, output_width).state_dict()
    clients_per_round: list[
        tuple[tuple[torch.Tensor, torch.Tensor, tuple[ArtifactDigest, ...], DerivedSeed], ...]
    ] = []
    for round_index in range(config.model.anchor_fedavg.rounds):
        round_clients: list[
            tuple[torch.Tensor, torch.Tensor, tuple[ArtifactDigest, ...], DerivedSeed]
        ] = []
        for domain in NBAIOT_DOMAIN_ORDER:
            combined_features: list[torch.Tensor] = []
            combined_labels: list[torch.Tensor] = []
            combined_sample_ids: list[ArtifactDigest] = []
            for class_id in NBAIOT_CLASS_ORDER:
                if class_id is NBaiotClass.GAFGYT_COMBO:
                    continue
                tensor_view = _tensor_view(
                    load_prepared_rows(prepared_root, domain, class_id, Role.ANCHOR_TRAIN)
                )
                if tensor_view is None:
                    continue
                features, labels, sample_ids = tensor_view
                combined_features.append(features)
                combined_labels.append(labels)
                combined_sample_ids.extend(sample_ids)
            if not combined_features:
                continue
            training_seed = _training_seed(
                master_seed,
                manifest_hash,
                "anchor-start",
                ANCHOR_TRAINING_ALGORITHM_TOKEN,
                domain,
                round_index,
            )
            round_clients.append(
                (
                    torch.cat(combined_features, dim=0),
                    torch.cat(combined_labels, dim=0),
                    tuple(combined_sample_ids),
                    training_seed,
                )
            )
        if not round_clients:
            return None
        clients_per_round.append(tuple(round_clients))
    final_state, round_checkpoints = run_anchor_fedavg_training(
        input_width,
        output_width,
        initial_state,
        config.model.optimizer.anchor_and_standard_fl_learning_rate,
        config.model.optimizer,
        config.model.training,
        config.model.anchor_fedavg,
        clients_per_round,
    )
    model = FedSIRAClassifier(input_width, output_width)
    model.load_state_dict(final_state)
    round_start_flat_parameters = tuple(
        _flatten_state_dict(input_width, output_width, state)
        for state in (initial_state, *round_checkpoints[:-1])
    )
    return RealAnchor(
        input_width=input_width,
        output_width=output_width,
        flat_parameters=flatten_trainable_parameters(model),
        dataset_manifest_hash=manifest_hash,
        round_start_flat_parameters=round_start_flat_parameters,
    )


def anchor_round_calibration_updates(
    prepared_root: Path,
    config: ScientificConfig,
    master_seed: MasterSeed,
    anchor: RealAnchor,
) -> tuple[torch.Tensor, ...]:
    updates: list[torch.Tensor] = []
    for round_index, round_start_flat in enumerate(anchor.round_start_flat_parameters):
        for domain in NBAIOT_DOMAIN_ORDER:
            combined_features: list[torch.Tensor] = []
            combined_labels: list[torch.Tensor] = []
            combined_sample_ids: list[ArtifactDigest] = []
            for class_id in NBAIOT_CLASS_ORDER:
                if class_id is NBaiotClass.GAFGYT_COMBO:
                    continue
                tensor_view = _tensor_view(
                    load_prepared_rows(prepared_root, domain, class_id, Role.ANCHOR_VALIDATION)
                )
                if tensor_view is None:
                    continue
                features, labels, sample_ids = tensor_view
                combined_features.append(features)
                combined_labels.append(labels)
                combined_sample_ids.extend(sample_ids)
            if not combined_features:
                continue
            features = torch.cat(combined_features, dim=0)
            labels = torch.cat(combined_labels, dim=0)
            sample_ids = tuple(combined_sample_ids)
            training_seed = _training_seed(
                master_seed,
                anchor.dataset_manifest_hash,
                _flat_parameters_identity(round_start_flat),
                CALIBRATION_TRAINING_ALGORITHM_TOKEN,
                domain,
                round_index,
            )
            round_start_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
            load_flat_trainable_parameters(round_start_model, round_start_flat)
            client_state_dict, _example_count = train_one_client_locally(
                round_start_model.state_dict(),
                anchor.input_width,
                anchor.output_width,
                config.model.optimizer.anchor_and_standard_fl_learning_rate,
                config.model.optimizer,
                config.model.training,
                1,
                features,
                labels,
                sample_ids,
                training_seed,
            )
            client_flat = _flatten_state_dict(
                anchor.input_width, anchor.output_width, client_state_dict
            )
            updates.append(client_flat - round_start_flat)
    return tuple(updates)


def train_source_update_sanitization_delta(
    prepared_root: Path,
    config: ScientificConfig,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
) -> torch.Tensor | None:
    if source_domain is None:
        return None
    source_delta = train_source_candidate_delta(
        prepared_root, config, master_seed, anchor, source_domain
    )
    if source_delta is None:
        return None
    calibration_updates = anchor_round_calibration_updates(
        prepared_root, config, master_seed, anchor
    )
    if not calibration_updates:
        return None
    clip_bounds = sanitization_clip_bounds(
        calibration_updates,
        config.baselines.source_update_sanitization.coordinate_bound_percentile,
    )
    return clip_source_update(source_delta, clip_bounds)


def train_local_only_reference_checkpoint(
    prepared_root: Path,
    config: ScientificConfig,
    master_seed: MasterSeed,
    domain: NBaiotDomain,
) -> torch.Tensor | None:
    training_role = local_only_reference_training_role()
    combined_features: list[torch.Tensor] = []
    combined_labels: list[torch.Tensor] = []
    combined_sample_ids: list[ArtifactDigest] = []
    for class_id in NBAIOT_CLASS_ORDER:
        if class_id is NBaiotClass.GAFGYT_COMBO:
            continue
        tensor_view = _tensor_view(
            load_prepared_rows(prepared_root, domain, class_id, training_role)
        )
        if tensor_view is None:
            continue
        features, labels, sample_ids = tensor_view
        combined_features.append(features)
        combined_labels.append(labels)
        combined_sample_ids.extend(sample_ids)
    if not combined_features:
        return None
    features = torch.cat(combined_features, dim=0)
    labels = torch.cat(combined_labels, dim=0)
    sample_ids = tuple(combined_sample_ids)
    input_width = features.shape[1]
    output_width = len(NBAIOT_CLASS_ORDER)
    initialization_seed = derive_uint32(
        "LOCAL_ONLY_REFERENCE_INIT",
        namespace_seed(master_seed, SeedNamespace.MODEL_INITIALIZATION),
        NBAIOT_DOMAIN_HASH_TOKEN[domain],
    )
    seed_job_local_rng_streams(initialization_seed)
    initial_state = FedSIRAClassifier(input_width, output_width).state_dict()
    training_seed = _training_seed(
        master_seed,
        dataset_manifest_hash(prepared_root),
        "local-only-start",
        LOCAL_ONLY_REFERENCE_TRAINING_ALGORITHM_TOKEN,
        domain,
        0,
    )
    final_state, _example_count = train_one_client_locally(
        initial_state,
        input_width,
        output_width,
        config.model.optimizer.anchor_and_standard_fl_learning_rate,
        config.model.optimizer,
        config.model.training,
        local_only_reference_local_epochs(config.baselines),
        features,
        labels,
        sample_ids,
        training_seed,
    )
    final_model = FedSIRAClassifier(input_width, output_width)
    final_model.load_state_dict(final_state)
    return flatten_trainable_parameters(final_model)


def train_centralized_reference_checkpoint(
    prepared_root: Path,
    config: ScientificConfig,
    master_seed: MasterSeed,
) -> torch.Tensor | None:
    domain_features: dict[NBaiotDomain, torch.Tensor] = {}
    domain_labels: dict[NBaiotDomain, torch.Tensor] = {}
    domain_sample_ids: dict[NBaiotDomain, tuple[ArtifactDigest, ...]] = {}
    for domain in NBAIOT_DOMAIN_ORDER:
        combined_features: list[torch.Tensor] = []
        combined_labels: list[torch.Tensor] = []
        combined_sample_ids: list[ArtifactDigest] = []
        for class_id in NBAIOT_CLASS_ORDER:
            if class_id is NBaiotClass.GAFGYT_COMBO:
                continue
            tensor_view = _tensor_view(
                load_prepared_rows(prepared_root, domain, class_id, Role.ANCHOR_TRAIN)
            )
            if tensor_view is None:
                continue
            features, labels, sample_ids = tensor_view
            combined_features.append(features)
            combined_labels.append(labels)
            combined_sample_ids.extend(sample_ids)
        if not combined_features:
            continue
        domain_features[domain] = torch.cat(combined_features, dim=0)
        domain_labels[domain] = torch.cat(combined_labels, dim=0)
        domain_sample_ids[domain] = tuple(combined_sample_ids)
    if not domain_features:
        return None
    pooled_features = centralized_reference_pooled_rows(domain_features)
    pooled_labels = centralized_reference_pooled_rows(domain_labels)
    pooled_sample_ids = tuple(
        sample_id
        for domain in NBAIOT_DOMAIN_ORDER
        if domain in domain_sample_ids
        for sample_id in domain_sample_ids[domain]
    )
    input_width = pooled_features.shape[1]
    output_width = len(NBAIOT_CLASS_ORDER)
    initialization_seed = derive_uint32(
        "CENTRALIZED_REFERENCE_INIT",
        namespace_seed(master_seed, SeedNamespace.MODEL_INITIALIZATION),
    )
    seed_job_local_rng_streams(initialization_seed)
    initial_state = FedSIRAClassifier(input_width, output_width).state_dict()
    training_seed = _training_seed(
        master_seed,
        dataset_manifest_hash(prepared_root),
        "centralized-start",
        CENTRALIZED_REFERENCE_TRAINING_ALGORITHM_TOKEN,
        NBAIOT_DOMAIN_ORDER[0],
        0,
    )
    final_state, _example_count = train_one_client_locally(
        initial_state,
        input_width,
        output_width,
        config.model.optimizer.anchor_and_standard_fl_learning_rate,
        config.model.optimizer,
        config.model.training,
        centralized_reference_local_epochs(config.baselines),
        pooled_features,
        pooled_labels,
        pooled_sample_ids,
        training_seed,
    )
    final_model = FedSIRAClassifier(input_width, output_width)
    final_model.load_state_dict(final_state)
    return flatten_trainable_parameters(final_model)


def _combined_post_reference_rows(
    prepared_root: Path,
    domain: NBaiotDomain,
    target_role: Role,
    root_cause_scope: RootCauseScope | None = None,
    epistemic_failure_scope: EpistemicFailureScope | None = None,
) -> tuple[torch.Tensor, torch.Tensor, tuple[ArtifactDigest, ...], torch.Tensor] | None:
    target_rows = load_prepared_rows(prepared_root, domain, NBaiotClass.GAFGYT_COMBO, target_role)
    if target_rows is not None and root_cause_scope is not None:
        target_rows = _scope_and_shift_rows(target_rows, root_cause_scope)
    if (
        target_rows is not None
        and epistemic_failure_scope is not None
        and epistemic_failure_scope.failure_type
        in (
            EpistemicFailureType.SHARED_SPURIOUS_FEATURE,
            EpistemicFailureType.ATTACKER_INDUCED_COMMON_CONTEXT,
        )
    ):
        target_rows = _apply_epistemic_target_marker(target_rows, epistemic_failure_scope)
    target_tensor = _tensor_view(target_rows)
    if target_tensor is None:
        return None
    target_features, target_labels, target_sample_ids = target_tensor
    supported_features: list[torch.Tensor] = [target_features]
    supported_labels: list[torch.Tensor] = [target_labels]
    supported_sample_ids: list[ArtifactDigest] = list(target_sample_ids)
    is_supported: list[torch.Tensor] = [torch.zeros(target_features.shape[0], dtype=torch.bool)]
    for class_id in NBAIOT_CLASS_ORDER:
        if class_id is NBaiotClass.GAFGYT_COMBO:
            continue
        rows = load_prepared_rows(prepared_root, domain, class_id, Role.POST_REFERENCE_REPLAY)
        relabeled_mask: tuple[bool, ...] | None = None
        if (
            rows is not None
            and class_id is NBaiotClass.BENIGN
            and epistemic_failure_scope is not None
            and epistemic_failure_scope.failure_type is EpistemicFailureType.SHARED_LABEL_ERROR
        ):
            rows, relabeled_mask = _relabel_shared_label_error_rows(rows, epistemic_failure_scope)
        replay_tensor = _tensor_view(rows)
        if replay_tensor is None:
            continue
        features, labels, sample_ids = replay_tensor
        supported_features.append(features)
        supported_labels.append(labels)
        supported_sample_ids.extend(sample_ids)
        if relabeled_mask is not None:
            is_supported.append(torch.tensor(relabeled_mask, dtype=torch.bool))
        else:
            is_supported.append(torch.ones(features.shape[0], dtype=torch.bool))
    return (
        torch.cat(supported_features, dim=0),
        torch.cat(supported_labels, dim=0),
        tuple(supported_sample_ids),
        torch.cat(is_supported, dim=0),
    )


def train_domain_reproduction_delta(
    prepared_root: Path,
    config: ScientificConfig,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    domain: NBaiotDomain,
    root_cause_scope: RootCauseScope | None = None,
    epistemic_failure_scope: EpistemicFailureScope | None = None,
) -> torch.Tensor | None:
    combined = _combined_post_reference_rows(
        prepared_root, domain, Role.REPRODUCTION, root_cause_scope, epistemic_failure_scope
    )
    if combined is None:
        return None
    features, labels, sample_ids, is_supported = combined
    anchor_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(anchor_model, anchor.flat_parameters)
    current_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(current_model, anchor.flat_parameters)
    training_seed = _training_seed(
        master_seed,
        anchor.dataset_manifest_hash,
        _flat_parameters_identity(anchor.flat_parameters),
        REPRODUCTION_TRAINING_ALGORITHM_TOKEN,
        domain,
        -1,
    )
    seed_job_local_rng_streams(training_seed)
    optimizer = torch.optim.AdamW(
        current_model.parameters(),
        lr=config.model.optimizer.post_reference_learning_rate,
        betas=config.model.optimizer.betas,
        eps=config.model.optimizer.epsilon,
        weight_decay=config.model.optimizer.weight_decay,
    )
    loss_function = torch.nn.CrossEntropyLoss()
    run_post_reference_training(
        anchor_model,
        current_model,
        optimizer,
        loss_function,
        config.model.training,
        config.model.post_reference,
        features,
        labels,
        is_supported,
        sample_ids,
        training_seed,
        config.model.post_reference.local_epochs,
    )
    return flatten_trainable_parameters(current_model) - anchor.flat_parameters


def train_source_candidate_delta(
    prepared_root: Path,
    config: ScientificConfig,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain,
) -> torch.Tensor | None:
    combined = _combined_post_reference_rows(prepared_root, source_domain, Role.SOURCE_PROPOSAL)
    if combined is None:
        return None
    features, labels, sample_ids, is_supported = combined
    anchor_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(anchor_model, anchor.flat_parameters)
    current_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(current_model, anchor.flat_parameters)
    training_seed = _training_seed(
        master_seed,
        anchor.dataset_manifest_hash,
        _flat_parameters_identity(anchor.flat_parameters),
        SOURCE_TRAINING_ALGORITHM_TOKEN,
        source_domain,
        -1,
    )
    seed_job_local_rng_streams(training_seed)
    optimizer = torch.optim.AdamW(
        current_model.parameters(),
        lr=config.model.optimizer.post_reference_learning_rate,
        betas=config.model.optimizer.betas,
        eps=config.model.optimizer.epsilon,
        weight_decay=config.model.optimizer.weight_decay,
    )
    loss_function = torch.nn.CrossEntropyLoss()
    run_post_reference_training(
        anchor_model,
        current_model,
        optimizer,
        loss_function,
        config.model.training,
        config.model.post_reference,
        features,
        labels,
        is_supported,
        sample_ids,
        training_seed,
        config.model.post_reference.local_epochs,
    )
    return flatten_trainable_parameters(current_model) - anchor.flat_parameters


def _train_ordinary_fedavg_delta(
    prepared_root: Path,
    config: ScientificConfig,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
    rounds: int,
    algorithm_token: CanonicalToken,
) -> torch.Tensor | None:
    source_rows_available = source_domain is not None and (
        load_prepared_rows(
            prepared_root, source_domain, NBaiotClass.GAFGYT_COMBO, Role.SOURCE_PROPOSAL
        )
        is not None
    )
    participants = fedavg_reference_post_reference_participants(
        non_source_domains(source_domain), source_domain, source_rows_available
    )
    if not participants:
        return None
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, anchor.flat_parameters)
    state_dict = model.state_dict()
    local_epochs = fedavg_reference_post_reference_local_epochs()
    any_round_trained = False
    for round_index in range(rounds):
        round_clients: list[
            tuple[torch.Tensor, torch.Tensor, tuple[ArtifactDigest, ...], DerivedSeed]
        ] = []
        for domain in participants:
            target_role = Role.SOURCE_PROPOSAL if domain == source_domain else Role.REPRODUCTION
            combined = _combined_post_reference_rows(prepared_root, domain, target_role)
            if combined is None:
                continue
            features, labels, sample_ids, _is_supported = combined
            training_seed = _training_seed(
                master_seed,
                anchor.dataset_manifest_hash,
                _flat_parameters_identity(anchor.flat_parameters),
                algorithm_token,
                domain,
                round_index,
            )
            round_clients.append((features, labels, sample_ids, training_seed))
        if not round_clients:
            continue
        any_round_trained = True
        state_dict = run_fedavg_round(
            state_dict,
            anchor.input_width,
            anchor.output_width,
            config.model.optimizer.anchor_and_standard_fl_learning_rate,
            config.model.optimizer,
            config.model.training,
            local_epochs,
            round_clients,
        )
    if not any_round_trained:
        return None
    final_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    final_model.load_state_dict(state_dict)
    return flatten_trainable_parameters(final_model) - anchor.flat_parameters


def train_fedavg_reference_delta(
    prepared_root: Path,
    config: ScientificConfig,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
) -> torch.Tensor | None:
    return _train_ordinary_fedavg_delta(
        prepared_root,
        config,
        master_seed,
        anchor,
        source_domain,
        fedavg_reference_post_reference_rounds(config.baselines),
        FEDAVG_REFERENCE_TRAINING_ALGORITHM_TOKEN,
    )


def train_secure_continual_assessment_delta(
    prepared_root: Path,
    config: ScientificConfig,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
) -> torch.Tensor | None:
    return _train_ordinary_fedavg_delta(
        prepared_root,
        config,
        master_seed,
        anchor,
        source_domain,
        secure_continual_assessment_post_reference_rounds(config.baselines),
        SECURE_CONTINUAL_ASSESSMENT_TRAINING_ALGORITHM_TOKEN,
    )


def _flatten_state_dict(
    input_width: int, output_width: int, state_dict: dict[str, torch.Tensor]
) -> torch.Tensor:
    model = FedSIRAClassifier(input_width, output_width)
    model.load_state_dict(state_dict)
    return flatten_trainable_parameters(model)


def train_krum_reference_delta(
    prepared_root: Path,
    config: ScientificConfig,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
) -> torch.Tensor | None:
    eligible_domains = non_source_domains(source_domain)
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, anchor.flat_parameters)
    state_dict = model.state_dict()
    participant_count = config.protocol.synthesis.committee_size
    for round_index in range(krum_reference_post_reference_rounds(config.baselines)):
        round_order = client_sampling_round_order(eligible_domains, master_seed, round_index)
        participants = krum_reference_round_participants(round_order, None, participant_count)
        if participants is None:
            return None
        current_flat = _flatten_state_dict(anchor.input_width, anchor.output_width, state_dict)
        committee: list[CertifiedReproductionRow] = []
        for domain in participants:
            target_role = Role.SOURCE_PROPOSAL if domain == source_domain else Role.REPRODUCTION
            combined = _combined_post_reference_rows(prepared_root, domain, target_role)
            if combined is None:
                continue
            features, labels, sample_ids, _is_supported = combined
            training_seed = _training_seed(
                master_seed,
                anchor.dataset_manifest_hash,
                _flat_parameters_identity(anchor.flat_parameters),
                "KRUM_REFERENCE",
                domain,
                round_index,
            )
            client_state_dict, _example_count = train_one_client_locally(
                state_dict,
                anchor.input_width,
                anchor.output_width,
                config.model.optimizer.anchor_and_standard_fl_learning_rate,
                config.model.optimizer,
                config.model.training,
                1,
                features,
                labels,
                sample_ids,
                training_seed,
            )
            client_flat = _flatten_state_dict(
                anchor.input_width, anchor.output_width, client_state_dict
            )
            committee.append(
                CertifiedReproductionRow(
                    reproducer_domain=domain, update_vector=client_flat - current_flat
                )
            )
        if len(committee) < participant_count:
            return None
        krum_delta = select_krum_update(
            committee, config.protocol.synthesis.maximum_byzantine_reproduction_rows
        ).update_vector
        next_flat = current_flat + krum_delta
        next_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
        load_flat_trainable_parameters(next_model, next_flat)
        state_dict = next_model.state_dict()
    final_flat = _flatten_state_dict(anchor.input_width, anchor.output_width, state_dict)
    return final_flat - anchor.flat_parameters


def train_density_cluster_trimmed_mean_delta(
    prepared_root: Path,
    config: ScientificConfig,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
) -> torch.Tensor | None:
    source_rows_available = source_domain is not None and (
        load_prepared_rows(
            prepared_root, source_domain, NBaiotClass.GAFGYT_COMBO, Role.SOURCE_PROPOSAL
        )
        is not None
    )
    participants = fedavg_reference_post_reference_participants(
        non_source_domains(source_domain), source_domain, source_rows_available
    )
    if not participants:
        return None
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, anchor.flat_parameters)
    state_dict = model.state_dict()
    any_round_trained = False
    for round_index in range(POST_REFERENCE_RETRAIN_MAXIMUM_LOCAL_EPOCHS):
        current_flat = _flatten_state_dict(anchor.input_width, anchor.output_width, state_dict)
        contributing_domains: list[NBaiotDomain] = []
        raw_updates: list[torch.Tensor] = []
        for domain in participants:
            target_role = Role.SOURCE_PROPOSAL if domain == source_domain else Role.REPRODUCTION
            combined = _combined_post_reference_rows(prepared_root, domain, target_role)
            if combined is None:
                continue
            features, labels, sample_ids, _is_supported = combined
            training_seed = _training_seed(
                master_seed,
                anchor.dataset_manifest_hash,
                _flat_parameters_identity(anchor.flat_parameters),
                DENSITY_CLUSTER_TRIMMED_MEAN_TRAINING_ALGORITHM_TOKEN,
                domain,
                round_index,
            )
            client_state_dict, _example_count = train_one_client_locally(
                state_dict,
                anchor.input_width,
                anchor.output_width,
                config.model.optimizer.anchor_and_standard_fl_learning_rate,
                config.model.optimizer,
                config.model.training,
                1,
                features,
                labels,
                sample_ids,
                training_seed,
            )
            client_flat = _flatten_state_dict(
                anchor.input_width, anchor.output_width, client_state_dict
            )
            contributing_domains.append(domain)
            raw_updates.append(client_flat - current_flat)
        if not raw_updates:
            continue
        normalized = l2_normalize(raw_updates)
        distance_matrix = cosine_distance_matrix(normalized)
        cluster_labels = density_cluster_labels(
            distance_matrix, config.baselines.density_cluster_trimmed_mean
        )
        selected_domains = select_largest_density_cluster(
            tuple(contributing_domains), cluster_labels, distance_matrix
        )
        if not selected_domains:
            continue
        selected_updates = [
            raw_updates[contributing_domains.index(domain)] for domain in selected_domains
        ]
        aggregated_update = trimmed_mean_aggregate(
            selected_updates,
            config.baselines.density_cluster_trimmed_mean.minimum_cluster_size_for_trimming,
            config.baselines.density_cluster_trimmed_mean.trim_each_tail_count,
        )
        next_flat = current_flat + aggregated_update
        next_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
        load_flat_trainable_parameters(next_model, next_flat)
        state_dict = next_model.state_dict()
        any_round_trained = True
    if not any_round_trained:
        return None
    final_flat = _flatten_state_dict(anchor.input_width, anchor.output_width, state_dict)
    return final_flat - anchor.flat_parameters


def evaluate_domain(
    prepared_root: Path,
    anchor: RealAnchor,
    flat_parameters: torch.Tensor,
    domain: NBaiotDomain,
    role: Role,
    target_role: Role | None = None,
    root_cause_scope: RootCauseScope | None = None,
) -> DomainTargetMetrics | None:
    true_labels: list[CanonicalToken] = []
    predicted_labels: list[CanonicalToken] = []
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
                rows = _scope_and_shift_rows(rows, root_cause_scope)
            tensor_view = _tensor_view(rows)
            if tensor_view is None:
                continue
            features, _labels, _sample_ids = tensor_view
            logits = logits_for_samples(model, features)
            predictions = torch.argmax(logits, dim=-1)
            prediction_indices = tuple(int(value) for value in predictions.detach().cpu().numpy())
            true_labels.extend(class_id.value for _ in range(features.shape[0]))
            predicted_labels.extend(NBAIOT_CLASS_ORDER[index].value for index in prediction_indices)
    if not true_labels:
        return None
    class_tokens = tuple(class_id.value for class_id in NBAIOT_CLASS_ORDER)
    counts_by_class = compute_confusion_counts_by_class(true_labels, predicted_labels, class_tokens)
    f1_by_class = {token: f1_for_class(counts) for token, counts in counts_by_class.items()}
    supported_f1 = {
        token: f1_by_class[token]
        for token in class_tokens
        if token != NBaiotClass.GAFGYT_COMBO.value
    }
    return DomainTargetMetrics(
        target_f1=f1_by_class.get(NBaiotClass.GAFGYT_COMBO.value, MetricResult(None, 0)),
        supported_macro_f1=macro_f1(supported_f1),
        benign_far=benign_false_alarm_rate(true_labels, predicted_labels, NBaiotClass.BENIGN.value),
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
    return frozenset(root_cause_a_ids), frozenset(root_cause_b_ids), frozenset(supported_ids)


def certified_domain_delta_committee(
    prepared_root: Path,
    config: ScientificConfig,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    domains: Sequence[NBaiotDomain],
) -> dict[NBaiotDomain, torch.Tensor]:
    deltas: dict[NBaiotDomain, torch.Tensor] = {}
    for domain in domains:
        delta = train_domain_reproduction_delta(prepared_root, config, master_seed, anchor, domain)
        if delta is not None:
            deltas[domain] = delta
    return deltas


@dataclass(frozen=True)
class RealReportSummary:
    target_f1: MetricResult
    worst_domain_target_f1: MetricResult
    p10_domain_target_f1: MetricResult
    domain_disparity: MetricResult
    domain_iqr: MetricResult
    coefficient_of_variation: MetricResult
    supported_macro_f1_harm: MetricResult
    benign_far_increase: MetricResult


def compute_real_report_summary(
    prepared_root: Path,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
    production_checkpoint: torch.Tensor,
) -> RealReportSummary | None:
    domains = non_source_domains(source_domain)
    target_f1_values: list[MetricResult] = []
    supported_f1_harms: list[MetricResult] = []
    benign_far_increases: list[MetricResult] = []
    for domain in domains:
        anchor_metrics = evaluate_domain(
            prepared_root, anchor, anchor.flat_parameters, domain, Role.REPORT_TEST
        )
        production_metrics = evaluate_domain(
            prepared_root, anchor, production_checkpoint, domain, Role.REPORT_TEST
        )
        if anchor_metrics is None or production_metrics is None:
            continue
        target_f1_values.append(production_metrics.target_f1)
        supported_f1_harms.append(
            supported_macro_f1_harm(
                anchor_metrics.supported_macro_f1, production_metrics.supported_macro_f1
            )
        )
        if (
            anchor_metrics.benign_far.value is not None
            and production_metrics.benign_far.value is not None
        ):
            benign_far_increases.append(
                MetricResult(
                    production_metrics.benign_far.value - anchor_metrics.benign_far.value, 1
                )
            )
        else:
            benign_far_increases.append(MetricResult(None, 0))
    if not target_f1_values:
        return None
    return RealReportSummary(
        target_f1=equal_weight_domain_mean(target_f1_values, 1),
        worst_domain_target_f1=worst_domain_target_f1(target_f1_values),
        p10_domain_target_f1=percentile_10_domain_target_f1(target_f1_values),
        domain_disparity=domain_disparity(target_f1_values),
        domain_iqr=interquartile_range(target_f1_values),
        coefficient_of_variation=coefficient_of_variation(
            [result.value for result in target_f1_values if result.value is not None]
        ),
        supported_macro_f1_harm=equal_weight_domain_mean(supported_f1_harms, 1),
        benign_far_increase=equal_weight_domain_mean(benign_far_increases, 1),
    )


def _per_sample_cross_entropy(
    model: FedSIRAClassifier, features: torch.Tensor, labels: torch.Tensor
) -> torch.Tensor:
    model.eval()
    with torch.no_grad():
        logits = logits_for_samples(model, features)
        return torch.nn.functional.cross_entropy(logits, labels, reduction="none")


def compute_screen_differential(
    prepared_root: Path,
    config: ScientificConfig,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_delta: torch.Tensor,
    domain: NBaiotDomain,
) -> float | None:
    target_tensor = _tensor_view(
        load_prepared_rows(prepared_root, domain, NBaiotClass.GAFGYT_COMBO, Role.CANDIDATE_SCREEN)
    )
    if target_tensor is None:
        return None
    target_features, target_labels, target_sample_ids = target_tensor
    control_features_parts: list[torch.Tensor] = []
    control_labels_parts: list[torch.Tensor] = []
    control_sample_ids: list[ArtifactDigest] = []
    for class_id in NBAIOT_CLASS_ORDER:
        if class_id is NBaiotClass.GAFGYT_COMBO:
            continue
        replay_tensor = _tensor_view(
            load_prepared_rows(prepared_root, domain, class_id, Role.POST_REFERENCE_REPLAY)
        )
        if replay_tensor is None:
            continue
        features, labels, sample_ids = replay_tensor
        control_features_parts.append(features)
        control_labels_parts.append(labels)
        control_sample_ids.extend(sample_ids)
    if not control_features_parts:
        return None
    control_features = torch.cat(control_features_parts, dim=0)
    control_labels = torch.cat(control_labels_parts, dim=0)

    anchor_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(anchor_model, anchor.flat_parameters)
    source_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(source_model, anchor.flat_parameters + source_delta)

    target_anchor_loss = _per_sample_cross_entropy(anchor_model, target_features, target_labels)
    target_source_loss = _per_sample_cross_entropy(source_model, target_features, target_labels)
    control_anchor_loss = _per_sample_cross_entropy(anchor_model, control_features, control_labels)
    control_source_loss = _per_sample_cross_entropy(source_model, control_features, control_labels)

    screen_fold_seed = derive_uint32("SCREEN_FOLD_SEED", master_seed)
    fold_count = config.protocol.proposal_screen.fold_count
    fold_assignment: dict[CanonicalToken, int] = {}
    target_observations: list[ScreenLossObservation] = []
    for index, sample_id in enumerate(target_sample_ids):
        fold_assignment[sample_id] = screen_fold_index(sample_id, screen_fold_seed, fold_count)
        target_observations.append(
            ScreenLossObservation(
                sample_id, float(target_anchor_loss[index]), float(target_source_loss[index])
            )
        )
    control_observations: list[ScreenLossObservation] = []
    for index, sample_id in enumerate(control_sample_ids):
        fold_assignment[sample_id] = screen_fold_index(sample_id, screen_fold_seed, fold_count)
        control_observations.append(
            ScreenLossObservation(
                sample_id, float(control_anchor_loss[index]), float(control_source_loss[index])
            )
        )
    return run_proposal_screen_for_domain(
        fold_assignment, target_observations, control_observations, fold_count
    )


@dataclass(frozen=True)
class CapabilityUnderSpecificationSummary:
    defined_domain_count: int
    aggregate_target_f1: MetricResult
    target_f1_gain: MetricResult
    supported_macro_f1_drop: MetricResult
    benign_far_increase: MetricResult


def compute_capability_under_specification_summary(
    prepared_root: Path,
    config: ScientificConfig,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
    root_cause_scope: RootCauseScope,
) -> CapabilityUnderSpecificationSummary:
    target_f1_values: list[MetricResult] = []
    anchor_target_f1_values: list[MetricResult] = []
    supported_f1_harms: list[MetricResult] = []
    benign_far_increases: list[MetricResult] = []
    for domain in non_source_domains(source_domain):
        delta = train_domain_reproduction_delta(
            prepared_root, config, master_seed, anchor, domain, root_cause_scope
        )
        if delta is None:
            continue
        production_flat = anchor.flat_parameters + delta
        anchor_metrics = evaluate_domain(
            prepared_root,
            anchor,
            anchor.flat_parameters,
            domain,
            Role.REPORT_TEST,
            root_cause_scope=root_cause_scope,
        )
        scoped_metrics = evaluate_domain(
            prepared_root,
            anchor,
            production_flat,
            domain,
            Role.REPORT_TEST,
            root_cause_scope=root_cause_scope,
        )
        if anchor_metrics is None or scoped_metrics is None:
            continue
        target_f1_values.append(scoped_metrics.target_f1)
        anchor_target_f1_values.append(anchor_metrics.target_f1)
        supported_f1_harms.append(
            supported_macro_f1_harm(
                anchor_metrics.supported_macro_f1, scoped_metrics.supported_macro_f1
            )
        )
        if (
            anchor_metrics.benign_far.value is not None
            and scoped_metrics.benign_far.value is not None
        ):
            benign_far_increases.append(
                MetricResult(scoped_metrics.benign_far.value - anchor_metrics.benign_far.value, 1)
            )
        else:
            benign_far_increases.append(MetricResult(None, 0))
    aggregate_target_f1 = equal_weight_domain_mean(target_f1_values, 1)
    anchor_target_f1 = equal_weight_domain_mean(anchor_target_f1_values, 1)
    target_f1_gain = (
        MetricResult(aggregate_target_f1.value - anchor_target_f1.value, 1)
        if aggregate_target_f1.value is not None and anchor_target_f1.value is not None
        else MetricResult(None, 0)
    )
    return CapabilityUnderSpecificationSummary(
        defined_domain_count=len(target_f1_values),
        aggregate_target_f1=aggregate_target_f1,
        target_f1_gain=target_f1_gain,
        supported_macro_f1_drop=equal_weight_domain_mean(supported_f1_harms, 1),
        benign_far_increase=equal_weight_domain_mean(benign_far_increases, 1),
    )


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
    target_index_by_id = {
        sample_id: index for index, sample_id in enumerate(target_rows.sample_ids)
    }
    anchor_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(anchor_model, anchor.flat_parameters)
    target_class_index = NBAIOT_CLASS_ORDER.index(NBaiotClass.GAFGYT_COMBO)
    selected_target_features = torch.tensor(
        [target_rows.features[target_index_by_id[sample_id]] for sample_id in selected_target_ids],
        dtype=torch.float32,
    )
    selected_target_labels = torch.full(
        (len(selected_target_ids),), target_class_index, dtype=torch.long
    )
    target_losses = _per_sample_cross_entropy(
        anchor_model, selected_target_features, selected_target_labels
    )
    target_report_losses = tuple(
        zip(selected_target_ids, (float(value) for value in target_losses), strict=True)
    )
    benign_class_index = NBAIOT_CLASS_ORDER.index(NBaiotClass.BENIGN)
    benign_features = torch.tensor(benign_rows.features, dtype=torch.float32)
    benign_labels = torch.full((len(benign_rows.sample_ids),), benign_class_index, dtype=torch.long)
    benign_losses = _per_sample_cross_entropy(anchor_model, benign_features, benign_labels)
    benign_report_losses = tuple(
        zip(benign_rows.sample_ids, (float(value) for value in benign_losses), strict=True)
    )
    matched_pairs = match_diagnostic_benign_report_test_rows(
        target_report_losses, benign_report_losses
    )
    if matched_pairs is None:
        return diagnostic_marker_metric_or_insufficient(None, 0.0)
    matched_benign_ids = tuple(benign_id for _target_id, benign_id in matched_pairs)
    benign_index_by_id = {
        sample_id: index for index, sample_id in enumerate(benign_rows.sample_ids)
    }
    matched_benign_rows = PreparedRows(
        sample_ids=matched_benign_ids,
        features=tuple(
            benign_rows.features[benign_index_by_id[sample_id]] for sample_id in matched_benign_ids
        ),
        labels=tuple(NBaiotClass.BENIGN.value for _ in matched_benign_ids),
    )
    marked_rows = _mark_rows(matched_benign_rows, scope, frozenset(matched_benign_ids))
    production_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(production_model, production_flat)
    production_model.eval()
    with torch.no_grad():
        marked_features = torch.tensor(marked_rows.features, dtype=torch.float32)
        logits = logits_for_samples(production_model, marked_features)
        predictions = torch.argmax(logits, dim=-1)
    marker_rate = float((predictions == target_class_index).float().mean())
    return diagnostic_marker_metric_or_insufficient(matched_pairs, marker_rate)


@dataclass(frozen=True)
class SharedEpistemicFailureSummary:
    defined_domain_count: int
    aggregate_target_f1: MetricResult
    target_f1_gain: MetricResult
    supported_macro_f1_drop: MetricResult
    benign_far_increase: MetricResult
    diagnostic_marker: MetricResult


def compute_shared_epistemic_failure_summary(
    prepared_root: Path,
    config: ScientificConfig,
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
            config,
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
        if (
            anchor_metrics.benign_far.value is not None
            and production_metrics.benign_far.value is not None
        ):
            benign_far_increases.append(
                MetricResult(
                    production_metrics.benign_far.value - anchor_metrics.benign_far.value, 1
                )
            )
        else:
            benign_far_increases.append(MetricResult(None, 0))
        if has_diagnostic_marker:
            marker_result, _reason = _diagnostic_marker_for_domain(
                prepared_root, anchor, production_flat, domain, epistemic_failure_scope
            )
            diagnostic_markers.append(marker_result)
    aggregate_target_f1 = equal_weight_domain_mean(target_f1_values, 1)
    anchor_target_f1 = equal_weight_domain_mean(anchor_target_f1_values, 1)
    target_f1_gain = (
        MetricResult(aggregate_target_f1.value - anchor_target_f1.value, 1)
        if aggregate_target_f1.value is not None and anchor_target_f1.value is not None
        else MetricResult(None, 0)
    )
    return SharedEpistemicFailureSummary(
        defined_domain_count=len(target_f1_values),
        aggregate_target_f1=aggregate_target_f1,
        target_f1_gain=target_f1_gain,
        supported_macro_f1_drop=equal_weight_domain_mean(supported_f1_harms, 1),
        benign_far_increase=equal_weight_domain_mean(benign_far_increases, 1),
        diagnostic_marker=equal_weight_domain_mean(diagnostic_markers, 1),
    )
