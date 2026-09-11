from collections.abc import Hashable, Mapping, Sequence
from typing import TypeVar

import torch

from fedsira.datasets.common import Role
from fedsira.domain.types import (
    DomainId,
    DomainLocalEvaluation,
    FederatedRoundCount,
    LocalEpochCount,
    SourceAvailable,
)
from fedsira.runtime import current_application_context

Domain = TypeVar("Domain", bound=Hashable)


def local_only_reference_local_epochs() -> LocalEpochCount:
    return current_application_context().scientific_config.baselines.local_only_reference_epochs


def local_only_reference_training_role() -> Role:
    return Role.ANCHOR_TRAIN


def local_only_reference_evaluation_is_domain_local(
    checkpoint_domain: DomainId, evaluation_domain: DomainId
) -> DomainLocalEvaluation:
    return checkpoint_domain == evaluation_domain


def centralized_reference_local_epochs() -> LocalEpochCount:
    return current_application_context().scientific_config.baselines.centralized_reference_epochs


def pool_domain_rows(
    ordered_domains: Sequence[DomainId], domain_rows: Mapping[DomainId, torch.Tensor]
) -> torch.Tensor:
    return torch.cat([domain_rows[domain] for domain in ordered_domains], dim=0)


def centralized_reference_pooled_rows(
    ordered_rows: Sequence[torch.Tensor],
) -> torch.Tensor:
    return torch.cat(tuple(ordered_rows), dim=0)


def fedavg_reference_post_reference_rounds() -> FederatedRoundCount:
    return current_application_context().scientific_config.baselines.fedavg_post_reference_rounds


def standard_fl_anchor_rounds() -> FederatedRoundCount:
    return current_application_context().scientific_config.model.anchor_fedavg.rounds


def fedavg_reference_post_reference_local_epochs() -> LocalEpochCount:
    return (
        current_application_context().scientific_config.model.anchor_fedavg.local_epochs_per_round
    )


def post_reference_retrain_maximum_local_epochs() -> LocalEpochCount:
    return current_application_context().scientific_config.model.post_reference.local_epochs


def fedavg_reference_post_reference_participants(
    domain_order: Sequence[Domain],
    post_reference_eligible_domains: Sequence[Domain],
    source_domain: Domain | None,
    source_is_available: SourceAvailable,
) -> tuple[Domain, ...]:
    participant_set = set(post_reference_eligible_domains)
    if source_is_available and source_domain is not None:
        participant_set.add(source_domain)
    return tuple(domain for domain in domain_order if domain in participant_set)
