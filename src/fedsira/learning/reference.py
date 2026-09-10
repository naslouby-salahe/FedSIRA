from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import torch

from fedsira.baselines.references import (
    centralized_reference_local_epochs,
    centralized_reference_pooled_rows,
    local_only_reference_local_epochs,
    local_only_reference_training_role,
)
from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_CLASS_ORDER,
    NBAIOT_DOMAIN_ORDER,
    NBaiotClass,
    NBaiotDomain,
    nbaiot_domain_hash_token,
)
from fedsira.domain.enums import SeedNamespace
from fedsira.domain.types import AlgorithmName, ArtifactDigest, MasterSeed
from fedsira.experiments.workflow import dataset_manifest_hash, load_prepared_rows, tensor_view
from fedsira.learning.aggregation import load_model_state, model_state_from_classifier
from fedsira.learning.anchor_training import training_seed
from fedsira.learning.federated import LocalTrainingClient, train_one_client_locally
from fedsira.learning.model import FedSIRAClassifier, flatten_trainable_parameters
from fedsira.runtime import current_application_context
from fedsira.runtime_execution import derive_uint32, namespace_seed, seed_job_local_rng_streams

LOCAL_ONLY_REFERENCE_TRAINING_ALGORITHM_TOKEN: AlgorithmName = "LOCAL_ONLY_REFERENCE"
CENTRALIZED_REFERENCE_TRAINING_ALGORITHM_TOKEN: AlgorithmName = "CENTRALIZED_REFERENCE"


def train_local_only_reference_checkpoint(
    prepared_root: Path, master_seed: MasterSeed, domain: NBaiotDomain
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    combined_features: list[torch.Tensor] = []
    combined_labels: list[torch.Tensor] = []
    combined_sample_ids: list[ArtifactDigest] = []
    training_role = local_only_reference_training_role()
    for class_id in NBAIOT_CLASS_ORDER:
        if class_id is NBaiotClass.GAFGYT_COMBO:
            continue
        rows = tensor_view(load_prepared_rows(prepared_root, domain, class_id, training_role))
        if rows is None:
            continue
        features, labels, sample_ids = rows
        combined_features.append(features)
        combined_labels.append(labels)
        combined_sample_ids.extend(sample_ids)
    if not combined_features:
        return None
    features = torch.cat(combined_features, dim=0)
    labels = torch.cat(combined_labels, dim=0)
    input_width = features.shape[1]
    output_width = len(NBAIOT_CLASS_ORDER)
    seed_job_local_rng_streams(
        derive_uint32(
            "LOCAL_ONLY_REFERENCE_INIT",
            namespace_seed(master_seed, SeedNamespace.MODEL_INITIALIZATION),
            nbaiot_domain_hash_token(domain),
        )
    )
    initial_state = model_state_from_classifier(FedSIRAClassifier(input_width, output_width))
    client_result = train_one_client_locally(
        initial_state,
        input_width,
        output_width,
        config.model.optimizer.anchor_and_standard_fl_learning_rate,
        config.model.optimizer,
        config.model.training,
        local_only_reference_local_epochs(),
        LocalTrainingClient(
            features=features,
            labels=labels,
            sample_ids=tuple(combined_sample_ids),
            training_seed=training_seed(
                master_seed,
                dataset_manifest_hash(prepared_root),
                "local-only-start",
                LOCAL_ONLY_REFERENCE_TRAINING_ALGORITHM_TOKEN,
                domain,
                0,
            ),
        ),
    )
    final_model = FedSIRAClassifier(input_width, output_width)
    load_model_state(final_model, client_result.state)
    return flatten_trainable_parameters(final_model)


def train_centralized_reference_checkpoint(
    prepared_root: Path, master_seed: MasterSeed
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    domain_features: OrderedDict[NBaiotDomain, torch.Tensor] = OrderedDict()
    domain_labels: OrderedDict[NBaiotDomain, torch.Tensor] = OrderedDict()
    domain_sample_ids: OrderedDict[NBaiotDomain, tuple[ArtifactDigest, ...]] = OrderedDict()
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
    seed_job_local_rng_streams(
        derive_uint32(
            "CENTRALIZED_REFERENCE_INIT",
            namespace_seed(master_seed, SeedNamespace.MODEL_INITIALIZATION),
        )
    )
    initial_state = model_state_from_classifier(FedSIRAClassifier(input_width, output_width))
    client_result = train_one_client_locally(
        initial_state,
        input_width,
        output_width,
        config.model.optimizer.anchor_and_standard_fl_learning_rate,
        config.model.optimizer,
        config.model.training,
        centralized_reference_local_epochs(),
        LocalTrainingClient(
            features=pooled_features,
            labels=pooled_labels,
            sample_ids=pooled_sample_ids,
            training_seed=training_seed(
                master_seed,
                dataset_manifest_hash(prepared_root),
                "centralized-start",
                CENTRALIZED_REFERENCE_TRAINING_ALGORITHM_TOKEN,
                NBAIOT_DOMAIN_ORDER[0],
                0,
            ),
        ),
    )
    final_model = FedSIRAClassifier(input_width, output_width)
    load_model_state(final_model, client_result.state)
    return flatten_trainable_parameters(final_model)
