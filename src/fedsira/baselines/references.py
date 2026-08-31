from collections.abc import Mapping, Sequence

import torch

from fedsira.baselines.registry import (
    STANDARD_FL_BASELINE_LOCAL_EPOCHS_PER_ROUND,
    STANDARD_FL_BASELINE_ROUNDS,
)
from fedsira.config.schema import BaselinesConfig
from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER, NBaiotDomain
from fedsira.domain.records import BooleanValue, PositiveInt, SourceAvailable


def local_only_reference_local_epochs(baselines_config: BaselinesConfig) -> PositiveInt:
    return baselines_config.local_only_reference_epochs


def local_only_reference_training_role() -> Role:
    return Role.ANCHOR_TRAIN


def local_only_reference_evaluation_is_domain_local(
    checkpoint_domain: NBaiotDomain, evaluation_domain: NBaiotDomain
) -> BooleanValue:
    return checkpoint_domain == evaluation_domain


def centralized_reference_local_epochs(baselines_config: BaselinesConfig) -> PositiveInt:
    return baselines_config.centralized_reference_epochs


def pool_domain_rows(
    ordered_domains: Sequence[NBaiotDomain], domain_rows: Mapping[NBaiotDomain, torch.Tensor]
) -> torch.Tensor:
    return torch.cat([domain_rows[domain] for domain in ordered_domains], dim=0)


def centralized_reference_pooled_rows(
    domain_rows: Mapping[NBaiotDomain, torch.Tensor],
) -> torch.Tensor:
    ordered_domains = [domain for domain in NBAIOT_DOMAIN_ORDER if domain in domain_rows]
    return pool_domain_rows(ordered_domains, domain_rows)


def fedavg_reference_post_reference_rounds(baselines_config: BaselinesConfig) -> PositiveInt:
    return baselines_config.fedavg_post_reference_rounds


def standard_fl_anchor_rounds() -> PositiveInt:
    return STANDARD_FL_BASELINE_ROUNDS


def fedavg_reference_post_reference_local_epochs() -> PositiveInt:
    return STANDARD_FL_BASELINE_LOCAL_EPOCHS_PER_ROUND


def fedavg_reference_post_reference_participants(
    post_reference_eligible_domains: Sequence[NBaiotDomain],
    source_domain: NBaiotDomain | None,
    source_is_available: SourceAvailable,
) -> tuple[NBaiotDomain, ...]:
    participant_set = set(post_reference_eligible_domains)
    if source_is_available and source_domain is not None:
        participant_set.add(source_domain)
    return tuple(domain for domain in NBAIOT_DOMAIN_ORDER if domain in participant_set)
