import math
from collections.abc import Sequence

import torch

from fedsira.domain.enums import TernaryOutcome
from fedsira.domain.records import DomainId, NonNegativeInt, PositiveInt, Probability


def minimum_honest_positive_count(
    observed_positive_count: NonNegativeInt, maximum_byzantine_count: NonNegativeInt
) -> NonNegativeInt:
    return max(observed_positive_count - maximum_byzantine_count, 0)


def krum_minimum_committee_size(maximum_byzantine_rows: NonNegativeInt) -> PositiveInt:
    return 2 * maximum_byzantine_rows + 3


def krum_committee_is_admissible(
    committee_size: PositiveInt, maximum_byzantine_rows: NonNegativeInt
) -> bool:
    return committee_size >= krum_minimum_committee_size(maximum_byzantine_rows)


def first_cycle_with_minimum_eligible_evidence_holders(
    eligible_holder_counts_by_cycle: Sequence[NonNegativeInt], minimum_required: PositiveInt
) -> NonNegativeInt | None:
    for cycle_index, count in enumerate(eligible_holder_counts_by_cycle):
        if count >= minimum_required:
            return cycle_index
    return None


def validate_no_safety_claim_before_tau_k(
    claimed_completion_cycle: NonNegativeInt, tau_k: NonNegativeInt | None
) -> None:
    if tau_k is None or claimed_completion_cycle < tau_k:
        raise ValueError("safety completion claimed before the required evidence-arrival cycle")


def deduplicate_reports_by_proxy(
    reports: Sequence[tuple[DomainId, TernaryOutcome]],
) -> dict[DomainId, TernaryOutcome]:
    deduplicated: dict[DomainId, TernaryOutcome] = {}
    for domain, outcome in reports:
        deduplicated.setdefault(domain, outcome)
    return deduplicated


def validate_exactly_one_source_domain(source_domains: Sequence[DomainId]) -> None:
    if len(source_domains) != 1:
        raise ValueError(
            f"a claim instance must have exactly one source domain, got {len(source_domains)}"
        )


def diagnostic_at_least_two_byzantine_probability(
    eligible_pool_size: PositiveInt,
    byzantine_domain_count: NonNegativeInt,
    committee_size: PositiveInt,
) -> Probability:
    upper_bound = min(committee_size, byzantine_domain_count)
    numerator = sum(
        math.comb(byzantine_domain_count, compromised_count)
        * math.comb(eligible_pool_size - byzantine_domain_count, committee_size - compromised_count)
        for compromised_count in range(2, upper_bound + 1)
    )
    denominator = math.comb(eligible_pool_size, committee_size)
    return numerator / denominator


def reproduction_update_vector(
    anchor_flat_parameters: torch.Tensor, reproduced_flat_parameters: torch.Tensor
) -> torch.Tensor:
    return reproduced_flat_parameters - anchor_flat_parameters
