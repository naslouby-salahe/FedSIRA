from __future__ import annotations

from pathlib import Path

import torch

from fedsira.baselines.references import (
    fedavg_reference_post_reference_local_epochs,
    fedavg_reference_post_reference_participants,
    fedavg_reference_post_reference_rounds,
    post_reference_retrain_maximum_local_epochs,
)
from fedsira.baselines.source_model import secure_continual_assessment_post_reference_rounds
from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.schema import NBaiotClass, NBaiotDomain
from fedsira.domain.types import AlgorithmName, BooleanValue, FederatedRoundCount, MasterSeed
from fedsira.evaluation.domain import non_source_domains
from fedsira.experiments.workflow import (
    RealAnchor,
    flat_parameters_identity,
    load_prepared_rows,
)
from fedsira.learning.aggregation import load_model_state, model_state_from_classifier
from fedsira.learning.anchor_training import training_seed
from fedsira.learning.federated import LocalTrainingClient, run_fedavg_round
from fedsira.learning.model import (
    FedSIRAClassifier,
    flatten_trainable_parameters,
    load_flat_trainable_parameters,
)
from fedsira.learning.post_reference_training import combined_post_reference_rows
from fedsira.runtime import current_application_context

FEDAVG_REFERENCE_TRAINING_ALGORITHM_TOKEN: AlgorithmName = "FEDAVG_REFERENCE"
SECURE_CONTINUAL_ASSESSMENT_TRAINING_ALGORITHM_TOKEN: AlgorithmName = "SECURE_CONTINUAL_ASSESSMENT"
RECOVERY_AFTER_SOURCE_ADMISSION_TRAINING_ALGORITHM_TOKEN: AlgorithmName = (
    "RECOVERY_AFTER_SOURCE_ADMISSION"
)


def train_ordinary_fedavg_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
    rounds: FederatedRoundCount,
    algorithm_token: AlgorithmName,
    exclude_source_from_participants: BooleanValue = False,
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    source_rows_available = (
        not exclude_source_from_participants
        and source_domain is not None
        and (
            load_prepared_rows(
                prepared_root, source_domain, NBaiotClass.GAFGYT_COMBO, Role.SOURCE_PROPOSAL
            )
            is not None
        )
    )
    participants = fedavg_reference_post_reference_participants(
        non_source_domains(source_domain), source_domain, source_rows_available
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
            combined = combined_post_reference_rows(prepared_root, domain, role)
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
    source_domain: NBaiotDomain | None,
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
    source_domain: NBaiotDomain | None,
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
    source_domain: NBaiotDomain | None,
) -> torch.Tensor | None:
    return train_ordinary_fedavg_delta(
        prepared_root,
        master_seed,
        anchor,
        source_domain,
        post_reference_retrain_maximum_local_epochs(),
        RECOVERY_AFTER_SOURCE_ADMISSION_TRAINING_ALGORITHM_TOKEN,
        exclude_source_from_participants=True,
    )
