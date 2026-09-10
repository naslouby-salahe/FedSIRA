from __future__ import annotations

from pathlib import Path

import torch

from fedsira.baselines.references import (
    local_only_reference_local_epochs,
    local_only_reference_training_role,
)
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_CLASS_ORDER,
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
