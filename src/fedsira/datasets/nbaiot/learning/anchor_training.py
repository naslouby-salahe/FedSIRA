from __future__ import annotations

from pathlib import Path

import torch

from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_CLASS_ORDER,
    NBAIOT_DOMAIN_ORDER,
    NBaiotClass,
    NBaiotDomain,
    nbaiot_domain_hash_token,
)
from fedsira.datasets.nbaiot.workflow import (
    RealAnchor,
    dataset_manifest_hash,
    load_prepared_rows,
    tensor_view,
)
from fedsira.domain.enums import SeedNamespace
from fedsira.domain.types import (
    AlgorithmName,
    ArtifactDigest,
    DerivedSeed,
    FeatureCount,
    MasterSeed,
    RoundIndex,
)
from fedsira.experiments.definitions import ReproducerCondition
from fedsira.learning.aggregation import ModelState, load_model_state, model_state_from_classifier
from fedsira.learning.anchor import run_anchor_fedavg_training
from fedsira.learning.federated import LocalTrainingClient
from fedsira.learning.model import (
    FedSIRAClassifier,
    flatten_trainable_parameters,
)
from fedsira.runtime import (
    current_application_context,
    local_training_seed,
    namespace_seed,
    seed_job_local_rng_streams,
)

ANCHOR_TRAINING_ALGORITHM_TOKEN: AlgorithmName = "ANCHOR_FEDAVG"
ANCHOR_TRAINING_CONDITION_TOKEN = ReproducerCondition.CLEAN


def training_seed(
    master_seed: MasterSeed,
    manifest_hash: ArtifactDigest,
    start_checkpoint_identity: ArtifactDigest,
    algorithm_token: AlgorithmName,
    domain: NBaiotDomain,
    round_index: RoundIndex,
) -> DerivedSeed:
    return local_training_seed(
        namespace_seed(master_seed, SeedNamespace.LOCAL_TRAINING),
        manifest_hash,
        start_checkpoint_identity,
        algorithm_token,
        nbaiot_domain_hash_token(domain),
        ANCHOR_TRAINING_CONDITION_TOKEN,
        round_index,
    )


def _flatten_model_state(
    state: ModelState, input_width: FeatureCount, output_width: FeatureCount
) -> torch.Tensor:
    model = FedSIRAClassifier(input_width, output_width)
    load_model_state(model, state)
    return flatten_trainable_parameters(model)


def train_anchor(prepared_root: Path, master_seed: MasterSeed) -> RealAnchor | None:
    config = current_application_context().scientific_config
    first_rows = load_prepared_rows(
        prepared_root, NBAIOT_DOMAIN_ORDER[0], NBaiotClass.BENIGN, Role.ANCHOR_TRAIN
    )
    if first_rows is None:
        return None
    input_width = len(first_rows.features[0])
    output_width = len(NBAIOT_CLASS_ORDER)
    manifest_hash = dataset_manifest_hash(prepared_root)
    seed_job_local_rng_streams(namespace_seed(master_seed, SeedNamespace.MODEL_INITIALIZATION))
    initial_state = model_state_from_classifier(FedSIRAClassifier(input_width, output_width))
    clients_per_round: list[tuple[LocalTrainingClient, ...]] = []
    for round_index in range(config.model.anchor_fedavg.rounds):
        round_clients: list[LocalTrainingClient] = []
        for domain in NBAIOT_DOMAIN_ORDER:
            combined_features: list[torch.Tensor] = []
            combined_labels: list[torch.Tensor] = []
            combined_sample_ids: list[ArtifactDigest] = []
            for class_id in NBAIOT_CLASS_ORDER:
                if class_id is NBaiotClass.GAFGYT_COMBO:
                    continue
                rows = tensor_view(
                    load_prepared_rows(prepared_root, domain, class_id, Role.ANCHOR_TRAIN)
                )
                if rows is None:
                    continue
                features, labels, sample_ids = rows
                combined_features.append(features)
                combined_labels.append(labels)
                combined_sample_ids.extend(sample_ids)
            if not combined_features:
                continue
            round_clients.append(
                LocalTrainingClient(
                    features=torch.cat(combined_features, dim=0),
                    labels=torch.cat(combined_labels, dim=0),
                    sample_ids=tuple(combined_sample_ids),
                    training_seed=training_seed(
                        master_seed,
                        manifest_hash,
                        "anchor-start",
                        ANCHOR_TRAINING_ALGORITHM_TOKEN,
                        domain,
                        round_index,
                    ),
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
        tuple(clients_per_round),
    )
    model = FedSIRAClassifier(input_width, output_width)
    load_model_state(model, final_state)
    return RealAnchor(
        input_width=input_width,
        output_width=output_width,
        flat_parameters=flatten_trainable_parameters(model),
        dataset_manifest_hash=manifest_hash,
        round_start_flat_parameters=tuple(
            _flatten_model_state(state, input_width, output_width)
            for state in (initial_state, *round_checkpoints[:-1])
        ),
    )
