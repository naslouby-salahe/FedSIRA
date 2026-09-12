from __future__ import annotations

from collections.abc import Hashable
from pathlib import Path
from typing import TypeVar

import torch

from fedsira.datasets.common import (
    HeterogeneityScope,
    RealAnchor,
    Role,
    flat_parameters_identity,
)
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_CLASS_ORDER,
    NBAIOT_DOMAIN_ORDER,
    NBaiotClass,
    nbaiot_adapter,
)
from fedsira.domain.enums import AdmissionOpeningMode
from fedsira.domain.types import (
    AlgorithmName,
    ArtifactDigest,
    BooleanValue,
    DomainId,
    ExampleCount,
    FederatedRoundCount,
    LocalEpochCount,
    MasterSeed,
    ReconstructionError,
    RoundIndex,
)
from fedsira.evaluation.metrics import (
    non_source_domains,
)
from fedsira.learning.federated import (
    ANCHOR_TRAINING_ALGORITHM_TOKEN,
    LocalTrainingClient,
    run_fedavg_round,
    train_one_client_locally,
    training_seed,
)
from fedsira.learning.model import (
    FedSIRAClassifier,
    flatten_trainable_parameters,
    load_flat_trainable_parameters,
)
from fedsira.learning.post_reference import (
    combined_post_reference_rows,
    train_source_candidate_delta,
)
from fedsira.learning.training import (
    ModelState,
    WeightedModelState,
    load_model_state,
    model_state_from_classifier,
)
from fedsira.protocol.baselines.defenses import (
    client_sampling_round_order,
    clip_source_update,
    cosine_distance_matrix,
    density_cluster_labels,
    krum_reference_post_reference_rounds,
    krum_reference_round_participants,
    l2_normalize,
    reconstruction_error,
    reconstruction_filter_accepts,
    reconstruction_filter_calibration_error_count,
    reconstruction_filter_reweight,
    reconstruction_rejection_threshold,
    sanitization_clip_bounds,
    secure_continual_assessment_post_reference_rounds,
    select_largest_density_cluster,
    trimmed_mean_aggregate,
)
from fedsira.protocol.baselines.registry import (
    fedavg_reference_post_reference_local_epochs,
    fedavg_reference_post_reference_participants,
    fedavg_reference_post_reference_rounds,
    post_reference_retrain_maximum_local_epochs,
    recovery_after_source_admission_rounds,
    update_reconstruction_local_epochs,
)
from fedsira.protocol.synthesis import CertifiedReproductionRow, select_krum_update
from fedsira.runtime import current_application_context


def one_independent_retrain_local_epochs() -> LocalEpochCount:
    return post_reference_retrain_maximum_local_epochs()


def candidate_free_full_path_opening_mode() -> AdmissionOpeningMode:
    return AdmissionOpeningMode.CANDIDATE_FREE


def validate_candidate_free_full_path_opening_mode(mode: AdmissionOpeningMode) -> None:
    if mode is not AdmissionOpeningMode.CANDIDATE_FREE:
        raise ValueError(
            "Candidate-Free Full Path must open the claim from confirmed anchor failure"
        )


Domain = TypeVar("Domain", bound=Hashable)

FEDAVG_REFERENCE_TRAINING_ALGORITHM_TOKEN: AlgorithmName = "FEDAVG_REFERENCE"
SECURE_CONTINUAL_ASSESSMENT_TRAINING_ALGORITHM_TOKEN: AlgorithmName = "SECURE_CONTINUAL_ASSESSMENT"
RECOVERY_AFTER_SOURCE_ADMISSION_TRAINING_ALGORITHM_TOKEN: AlgorithmName = (
    "RECOVERY_AFTER_SOURCE_ADMISSION"
)


def train_ordinary_fedavg_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: DomainId | None,
    rounds: FederatedRoundCount,
    algorithm_token: AlgorithmName,
    exclude_source_from_participants: BooleanValue = False,
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    source_rows_available = (
        not exclude_source_from_participants
        and source_domain is not None
        and (
            nbaiot_adapter(prepared_root).load_rows(
                source_domain, NBaiotClass.GAFGYT_COMBO, Role.SOURCE_PROPOSAL
            )
            is not None
        )
    )
    participants = fedavg_reference_post_reference_participants(
        NBAIOT_DOMAIN_ORDER,
        non_source_domains(nbaiot_adapter(prepared_root), source_domain),
        source_domain,
        source_rows_available,
    )
    if not participants:
        return None
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, anchor.flat_parameters)
    state = model_state_from_classifier(model)
    local_epochs = fedavg_reference_post_reference_local_epochs()
    any_round_trained = False
    for round_index in range(rounds):
        round_clients: list[LocalTrainingClient] = []
        for domain in participants:
            role = Role.SOURCE_PROPOSAL if domain == source_domain else Role.REPRODUCTION
            combined = combined_post_reference_rows(nbaiot_adapter(prepared_root), domain, role)
            if combined is None:
                continue
            features, labels, sample_ids, _is_supported = combined
            round_clients.append(
                LocalTrainingClient(
                    features=features,
                    labels=labels,
                    sample_ids=sample_ids,
                    training_seed=training_seed(
                        master_seed,
                        anchor.dataset_manifest_hash,
                        flat_parameters_identity(anchor.flat_parameters),
                        algorithm_token,
                        domain,
                        round_index,
                    ),
                )
            )
        if not round_clients:
            continue
        any_round_trained = True
        state = run_fedavg_round(
            state,
            anchor.input_width,
            anchor.output_width,
            config.model.optimizer.anchor_and_standard_fl_learning_rate,
            config.model.optimizer,
            config.model.training,
            local_epochs,
            tuple(round_clients),
        )
    if not any_round_trained:
        return None
    final_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_model_state(final_model, state)
    return flatten_trainable_parameters(final_model) - anchor.flat_parameters


def train_fedavg_reference_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: DomainId | None,
) -> torch.Tensor | None:
    return train_ordinary_fedavg_delta(
        prepared_root,
        master_seed,
        anchor,
        source_domain,
        fedavg_reference_post_reference_rounds(),
        FEDAVG_REFERENCE_TRAINING_ALGORITHM_TOKEN,
    )


def train_secure_continual_assessment_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: DomainId | None,
) -> torch.Tensor | None:
    return train_ordinary_fedavg_delta(
        prepared_root,
        master_seed,
        anchor,
        source_domain,
        secure_continual_assessment_post_reference_rounds(),
        SECURE_CONTINUAL_ASSESSMENT_TRAINING_ALGORITHM_TOKEN,
    )


def train_recovery_after_source_admission_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: DomainId | None,
) -> torch.Tensor | None:
    return train_ordinary_fedavg_delta(
        prepared_root,
        master_seed,
        anchor,
        source_domain,
        recovery_after_source_admission_rounds(),
        RECOVERY_AFTER_SOURCE_ADMISSION_TRAINING_ALGORITHM_TOKEN,
        exclude_source_from_participants=True,
    )


DENSITY_CLUSTER_TRIMMED_MEAN_TRAINING_ALGORITHM_TOKEN = "DENSITY_CLUSTER_TRIMMED_MEAN"  # TODO: should be enum


def _flatten_model_state(anchor: RealAnchor, state: ModelState) -> torch.Tensor:
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_model_state(model, state)
    return flatten_trainable_parameters(model)


def train_krum_reference_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: DomainId | None,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, anchor.flat_parameters)
    state = model_state_from_classifier(model)
    participant_count = config.protocol.synthesis.committee_size
    for round_index in range(krum_reference_post_reference_rounds()):
        participants = krum_reference_round_participants(
            client_sampling_round_order(
                non_source_domains(nbaiot_adapter(prepared_root), source_domain),
                master_seed,
                round_index,
            ),
            None,
            participant_count,
        )
        if participants is None:
            return None
        current_flat = _flatten_model_state(anchor, state)
        committee: list[CertifiedReproductionRow] = []
        for domain in participants:
            role = Role.SOURCE_PROPOSAL if domain == source_domain else Role.REPRODUCTION
            combined = combined_post_reference_rows(
                nbaiot_adapter(prepared_root), domain, role, heterogeneity_scope=heterogeneity_scope
            )
            if combined is None:
                continue
            features, labels, sample_ids, _is_supported = combined
            client_result = train_one_client_locally(
                state,
                anchor.input_width,
                anchor.output_width,
                config.model.optimizer.anchor_and_standard_fl_learning_rate,
                config.model.optimizer,
                config.model.training,
                1,
                LocalTrainingClient(
                    features=features,
                    labels=labels,
                    sample_ids=sample_ids,
                    training_seed=training_seed(
                        master_seed,
                        anchor.dataset_manifest_hash,
                        flat_parameters_identity(anchor.flat_parameters),
                        "KRUM_REFERENCE",
                        domain,
                        round_index,
                    ),
                ),
            )
            committee.append(
                CertifiedReproductionRow(
                    reproducer_domain=domain,
                    update_vector=_flatten_model_state(anchor, client_result.state) - current_flat,
                )
            )
        if len(committee) < participant_count:
            return None
        next_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
        load_flat_trainable_parameters(
            next_model,
            current_flat
            + select_krum_update(
                committee, config.protocol.synthesis.maximum_byzantine_reproduction_rows
            ).update_vector,
        )
        state = model_state_from_classifier(next_model)
    return _flatten_model_state(anchor, state) - anchor.flat_parameters


def train_density_cluster_trimmed_mean_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: DomainId | None,
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    source_rows_available = (
        source_domain is not None
        and nbaiot_adapter(prepared_root).load_rows(
            source_domain, NBaiotClass.GAFGYT_COMBO, Role.SOURCE_PROPOSAL
        )
        is not None
    )
    participants = fedavg_reference_post_reference_participants(
        NBAIOT_DOMAIN_ORDER,
        non_source_domains(nbaiot_adapter(prepared_root), source_domain),
        source_domain,
        source_rows_available,
    )
    if not participants:
        return None
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, anchor.flat_parameters)
    state = model_state_from_classifier(model)
    any_round_trained = False
    for round_index in range(update_reconstruction_local_epochs()):
        current_flat = _flatten_model_state(anchor, state)
        contributing_domains: list[DomainId] = []
        raw_updates: list[torch.Tensor] = []
        for domain in participants:
            role = Role.SOURCE_PROPOSAL if domain == source_domain else Role.REPRODUCTION
            combined = combined_post_reference_rows(nbaiot_adapter(prepared_root), domain, role)
            if combined is None:
                continue
            features, labels, sample_ids, _is_supported = combined
            result = train_one_client_locally(
                state,
                anchor.input_width,
                anchor.output_width,
                config.model.optimizer.anchor_and_standard_fl_learning_rate,
                config.model.optimizer,
                config.model.training,
                1,
                LocalTrainingClient(
                    features=features,
                    labels=labels,
                    sample_ids=sample_ids,
                    training_seed=training_seed(
                        master_seed,
                        anchor.dataset_manifest_hash,
                        flat_parameters_identity(anchor.flat_parameters),
                        DENSITY_CLUSTER_TRIMMED_MEAN_TRAINING_ALGORITHM_TOKEN,
                        domain,
                        round_index,
                    ),
                ),
            )
            contributing_domains.append(domain)
            raw_updates.append(_flatten_model_state(anchor, result.state) - current_flat)
        if not raw_updates:
            continue
        distance_matrix = cosine_distance_matrix(l2_normalize(tuple(raw_updates)))
        selected_domains = select_largest_density_cluster(
            tuple(contributing_domains),
            density_cluster_labels(distance_matrix, config.baselines.density_cluster_trimmed_mean),
            distance_matrix,
        )
        if not selected_domains:
            continue
        selected_updates = tuple(
            raw_updates[contributing_domains.index(domain)] for domain in selected_domains
        )
        next_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
        load_flat_trainable_parameters(
            next_model,
            current_flat
            + trimmed_mean_aggregate(
                selected_updates,
                config.baselines.density_cluster_trimmed_mean.minimum_cluster_size_for_trimming,
                config.baselines.density_cluster_trimmed_mean.trim_each_tail_count,
            ),
        )
        state = model_state_from_classifier(next_model)
        any_round_trained = True
    return (
        _flatten_model_state(anchor, state) - anchor.flat_parameters if any_round_trained else None
    )


CALIBRATION_TRAINING_ALGORITHM_TOKEN: AlgorithmName = "ANCHOR_ROUND_CALIBRATION"
UPDATE_RECONSTRUCTION_FILTER_TRAINING_ALGORITHM_TOKEN: AlgorithmName = (
    "UPDATE_RECONSTRUCTION_FILTER"
)


def _client_delta_from_role(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    domain: DomainId,
    round_index: RoundIndex,
    round_start_flat: torch.Tensor,
    role: Role,
    local_epochs: LocalEpochCount,
    algorithm_token: AlgorithmName,
) -> tuple[torch.Tensor, ExampleCount] | None:
    config = current_application_context().scientific_config
    combined_features: list[torch.Tensor] = []
    combined_labels: list[torch.Tensor] = []
    combined_sample_ids: list[ArtifactDigest] = []
    for class_id in NBAIOT_CLASS_ORDER:
        if class_id is NBaiotClass.GAFGYT_COMBO:
            continue
        rows = nbaiot_adapter(prepared_root).tensor_view(
            nbaiot_adapter(prepared_root).load_rows(domain, class_id, role)
        )
        if rows is None:
            continue
        features, labels, sample_ids = rows
        combined_features.append(features)
        combined_labels.append(labels)
        combined_sample_ids.extend(sample_ids)
    if not combined_features:
        return None
    training_rows = torch.cat(combined_features, dim=0)
    training_labels = torch.cat(combined_labels, dim=0)
    derived_seed = training_seed(
        master_seed,
        anchor.dataset_manifest_hash,
        flat_parameters_identity(round_start_flat),
        algorithm_token,
        domain,
        round_index,
    )
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, round_start_flat)
    client_result = train_one_client_locally(
        model_state_from_classifier(model),
        anchor.input_width,
        anchor.output_width,
        config.model.optimizer.anchor_and_standard_fl_learning_rate,
        config.model.optimizer,
        config.model.training,
        local_epochs,
        LocalTrainingClient(
            features=training_rows,
            labels=training_labels,
            sample_ids=tuple(combined_sample_ids),
            training_seed=derived_seed,
        ),
    )
    return (
        _flatten_model_state(anchor, client_result.state) - round_start_flat,
        client_result.example_count,
    )


def anchor_round_calibration_updates(
    prepared_root: Path, master_seed: MasterSeed, anchor: RealAnchor
) -> tuple[torch.Tensor, ...]:
    updates: list[torch.Tensor] = []
    for round_index, round_start_flat in enumerate(anchor.round_start_flat_parameters):
        for domain in NBAIOT_DOMAIN_ORDER:
            result = _client_delta_from_role(
                prepared_root,
                master_seed,
                anchor,
                domain,
                round_index,
                round_start_flat,
                Role.ANCHOR_VALIDATION,
                1,
                CALIBRATION_TRAINING_ALGORITHM_TOKEN,
            )
            if result is not None:
                updates.append(result[0])
    return tuple(updates)


def anchor_round_reconstruction_calibration_errors(
    prepared_root: Path, master_seed: MasterSeed, anchor: RealAnchor
) -> tuple[ReconstructionError, ...]:
    config = current_application_context().scientific_config
    errors: list[ReconstructionError] = []
    expected_maximum_count = reconstruction_filter_calibration_error_count(
        len(anchor.round_start_flat_parameters), len(NBAIOT_DOMAIN_ORDER)
    )
    for round_index, round_start_flat in enumerate(anchor.round_start_flat_parameters):
        for domain in NBAIOT_DOMAIN_ORDER:
            submitted = _client_delta_from_role(
                prepared_root,
                master_seed,
                anchor,
                domain,
                round_index,
                round_start_flat,
                Role.ANCHOR_TRAIN,
                config.model.anchor_fedavg.local_epochs_per_round,
                ANCHOR_TRAINING_ALGORITHM_TOKEN,
            )
            reconstructed = _client_delta_from_role(
                prepared_root,
                master_seed,
                anchor,
                domain,
                round_index,
                round_start_flat,
                Role.ANCHOR_VALIDATION,
                1,
                CALIBRATION_TRAINING_ALGORITHM_TOKEN,
            )
            if submitted is not None and reconstructed is not None:
                errors.append(
                    reconstruction_error(
                        submitted[0],
                        reconstructed[0],
                        config.baselines.reconstruction_filter.normalization_epsilon,
                    )
                )
    if len(errors) > expected_maximum_count:
        raise ValueError(
            f"computed {len(errors)} calibration errors, exceeding the derived maximum of "
            f"{expected_maximum_count} for {len(NBAIOT_DOMAIN_ORDER)} domains and "
            f"{len(anchor.round_start_flat_parameters)} anchor rounds"
        )
    return tuple(errors)


def train_update_reconstruction_filter_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: DomainId | None,
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    calibration_errors = anchor_round_reconstruction_calibration_errors(
        prepared_root, master_seed, anchor
    )
    if not calibration_errors:
        return None
    rejection_threshold = reconstruction_rejection_threshold(
        calibration_errors, config.baselines.reconstruction_filter.calibration_percentile
    )
    source_rows_available = (
        source_domain is not None
        and nbaiot_adapter(prepared_root).load_rows(
            source_domain, NBaiotClass.GAFGYT_COMBO, Role.SOURCE_PROPOSAL
        )
        is not None
    )
    participants = fedavg_reference_post_reference_participants(
        NBAIOT_DOMAIN_ORDER,
        non_source_domains(nbaiot_adapter(prepared_root), source_domain),
        source_domain,
        source_rows_available,
    )
    if not participants:
        return None
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, anchor.flat_parameters)
    state = model_state_from_classifier(model)
    any_round_trained = False
    for round_index in range(post_reference_retrain_maximum_local_epochs()):
        current_flat = _flatten_model_state(anchor, state)
        accepted_states: list[WeightedModelState] = []
        for domain in participants:
            role = Role.SOURCE_PROPOSAL if domain == source_domain else Role.REPRODUCTION
            combined = combined_post_reference_rows(nbaiot_adapter(prepared_root), domain, role)
            if combined is None:
                continue
            features, labels, sample_ids, _is_supported = combined
            client_result = train_one_client_locally(
                state,
                anchor.input_width,
                anchor.output_width,
                config.model.optimizer.anchor_and_standard_fl_learning_rate,
                config.model.optimizer,
                config.model.training,
                1,
                LocalTrainingClient(
                    features=features,
                    labels=labels,
                    sample_ids=sample_ids,
                    training_seed=training_seed(
                        master_seed,
                        anchor.dataset_manifest_hash,
                        flat_parameters_identity(anchor.flat_parameters),
                        UPDATE_RECONSTRUCTION_FILTER_TRAINING_ALGORITHM_TOKEN,
                        domain,
                        round_index,
                    ),
                ),
            )
            reconstructed = _client_delta_from_role(
                prepared_root,
                master_seed,
                anchor,
                domain,
                round_index,
                current_flat,
                Role.ANCHOR_VALIDATION,
                1,
                CALIBRATION_TRAINING_ALGORITHM_TOKEN,
            )
            if reconstructed is None:
                continue
            submitted_delta = _flatten_model_state(anchor, client_result.state) - current_flat
            error = reconstruction_error(
                submitted_delta,
                reconstructed[0],
                config.baselines.reconstruction_filter.normalization_epsilon,
            )
            if reconstruction_filter_accepts(error, rejection_threshold):
                accepted_states.append(client_result)
        reweighted = reconstruction_filter_reweight(tuple(accepted_states))
        if reweighted is not None:
            state = reweighted
            any_round_trained = True
    if not any_round_trained:
        return None
    return _flatten_model_state(anchor, state) - anchor.flat_parameters


def train_source_update_sanitization_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: DomainId | None,
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    if source_domain is None:
        return None
    source_delta = train_source_candidate_delta(
        nbaiot_adapter(prepared_root), master_seed, anchor, source_domain
    )
    if source_delta is None:
        return None
    calibration_updates = anchor_round_calibration_updates(prepared_root, master_seed, anchor)
    if not calibration_updates:
        return None
    clip_bounds = sanitization_clip_bounds(
        calibration_updates, config.baselines.source_update_sanitization.coordinate_bound_percentile
    )
    return clip_source_update(source_delta, clip_bounds)
