from __future__ import annotations

from pathlib import Path

import torch

from fedsira.baselines.calibration import (
    clip_source_update,
    reconstruction_error,
    reconstruction_filter_accepts,
    reconstruction_filter_calibration_error_count,
    reconstruction_filter_reweight,
    reconstruction_rejection_threshold,
    sanitization_clip_bounds,
)
from fedsira.baselines.references import (
    fedavg_reference_post_reference_participants,
    post_reference_retrain_maximum_local_epochs,
)
from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_CLASS_ORDER,
    NBAIOT_DOMAIN_ORDER,
    NBaiotClass,
    NBaiotDomain,
)
from fedsira.domain.types import (
    AlgorithmName,
    ArtifactDigest,
    ExampleCount,
    LocalEpochCount,
    MasterSeed,
    ReconstructionError,
    RoundIndex,
)
from fedsira.evaluation.domain import non_source_domains
from fedsira.experiments.workflow import (
    RealAnchor,
    flat_parameters_identity,
    load_prepared_rows,
    tensor_view,
)
from fedsira.learning.aggregation import (
    ModelState,
    WeightedModelState,
    load_model_state,
    model_state_from_classifier,
)
from fedsira.learning.anchor_training import ANCHOR_TRAINING_ALGORITHM_TOKEN, training_seed
from fedsira.learning.federated import LocalTrainingClient, train_one_client_locally
from fedsira.learning.model import (
    FedSIRAClassifier,
    flatten_trainable_parameters,
    load_flat_trainable_parameters,
)
from fedsira.learning.post_reference_training import (
    combined_post_reference_rows,
    train_source_candidate_delta,
)
from fedsira.runtime import current_application_context

CALIBRATION_TRAINING_ALGORITHM_TOKEN: AlgorithmName = "ANCHOR_ROUND_CALIBRATION"
UPDATE_RECONSTRUCTION_FILTER_TRAINING_ALGORITHM_TOKEN: AlgorithmName = (
    "UPDATE_RECONSTRUCTION_FILTER"
)


def _flatten_model_state(anchor: RealAnchor, state: ModelState) -> torch.Tensor:
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_model_state(model, state)
    return flatten_trainable_parameters(model)


def _client_delta_from_role(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    domain: NBaiotDomain,
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
        rows = tensor_view(load_prepared_rows(prepared_root, domain, class_id, role))
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
    source_domain: NBaiotDomain | None,
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
        and load_prepared_rows(
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
    state = model_state_from_classifier(model)
    any_round_trained = False
    for round_index in range(post_reference_retrain_maximum_local_epochs()):
        current_flat = _flatten_model_state(anchor, state)
        accepted_states: list[WeightedModelState] = []
        for domain in participants:
            role = Role.SOURCE_PROPOSAL if domain == source_domain else Role.REPRODUCTION
            combined = combined_post_reference_rows(prepared_root, domain, role)
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
    source_domain: NBaiotDomain | None,
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    if source_domain is None:
        return None
    source_delta = train_source_candidate_delta(prepared_root, master_seed, anchor, source_domain)
    if source_delta is None:
        return None
    calibration_updates = anchor_round_calibration_updates(prepared_root, master_seed, anchor)
    if not calibration_updates:
        return None
    clip_bounds = sanitization_clip_bounds(
        calibration_updates, config.baselines.source_update_sanitization.coordinate_bound_percentile
    )
    return clip_source_update(source_delta, clip_bounds)
