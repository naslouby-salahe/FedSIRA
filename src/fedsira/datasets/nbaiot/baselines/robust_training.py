from __future__ import annotations

from pathlib import Path

import torch

from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.baselines.calibration import (
    cosine_distance_matrix,
    density_cluster_labels,
    l2_normalize,
    select_largest_density_cluster,
    trimmed_mean_aggregate,
)
from fedsira.datasets.nbaiot.evaluation.domain import non_source_domains
from fedsira.datasets.nbaiot.learning.anchor_training import training_seed
from fedsira.datasets.nbaiot.learning.post_reference_training import combined_post_reference_rows
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER, NBaiotClass, NBaiotDomain
from fedsira.datasets.nbaiot.workflow import (
    HeterogeneityScope,
    RealAnchor,
    flat_parameters_identity,
    load_prepared_rows,
)
from fedsira.domain.types import MasterSeed
from fedsira.learning.aggregation import ModelState, load_model_state, model_state_from_classifier
from fedsira.learning.federated import LocalTrainingClient, train_one_client_locally
from fedsira.learning.model import (
    FedSIRAClassifier,
    flatten_trainable_parameters,
    load_flat_trainable_parameters,
)
from fedsira.protocol.baselines.references import (
    fedavg_reference_post_reference_participants,
    post_reference_retrain_maximum_local_epochs,
)
from fedsira.protocol.baselines.robust_aggregation import (
    client_sampling_round_order,
    krum_reference_post_reference_rounds,
    krum_reference_round_participants,
)
from fedsira.protocol.synthesis import CertifiedReproductionRow, select_krum_update
from fedsira.runtime import current_application_context

DENSITY_CLUSTER_TRIMMED_MEAN_TRAINING_ALGORITHM_TOKEN = "DENSITY_CLUSTER_TRIMMED_MEAN"


def _flatten_model_state(anchor: RealAnchor, state: ModelState) -> torch.Tensor:
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_model_state(model, state)
    return flatten_trainable_parameters(model)


def train_krum_reference_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
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
                non_source_domains(source_domain), master_seed, round_index
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
                prepared_root, domain, role, heterogeneity_scope=heterogeneity_scope
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
    source_domain: NBaiotDomain | None,
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    source_rows_available = (
        source_domain is not None
        and load_prepared_rows(
            prepared_root, source_domain, NBaiotClass.GAFGYT_COMBO, Role.SOURCE_PROPOSAL
        )
        is not None
    )
    participants = fedavg_reference_post_reference_participants(
        NBAIOT_DOMAIN_ORDER,
        non_source_domains(source_domain),
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
        contributing_domains: list[NBaiotDomain] = []
        raw_updates: list[torch.Tensor] = []
        for domain in participants:
            role = Role.SOURCE_PROPOSAL if domain == source_domain else Role.REPRODUCTION
            combined = combined_post_reference_rows(prepared_root, domain, role)
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
