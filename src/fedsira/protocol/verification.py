from collections.abc import Sequence

from fedsira.config.schema import VerificationConfig
from fedsira.domain.enums import ClaimState, SeedNamespace, TernaryOutcome
from fedsira.domain.records import (
    ArtifactDigest,
    DerivedSeed,
    DomainId,
    NamespaceSeed,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
)
from fedsira.runtime.determinism import derive_uint32, deterministic_order

VERIFIER_ASSIGNMENT_SEPARATOR = SeedNamespace.VERIFIER_ASSIGNMENT.value
BYZANTINE_SELECTION_SEPARATOR = SeedNamespace.BYZANTINE_SELECTION.value
COMMITTEE_DRAW_SEPARATOR = SeedNamespace.COMMITTEE_DRAW.value


def verifier_is_eligible(
    verifier_domain: DomainId,
    source_domain: DomainId | None,
    reproducer_domain: DomainId,
    allow_source_as_verifier: bool = False,
) -> bool:
    if verifier_domain == reproducer_domain:
        return False
    if allow_source_as_verifier:
        return True
    return source_domain is None or verifier_domain != source_domain


def verifier_assignment_timestamp_is_valid(
    verifier_assignment_timestamp: PositiveFloat, reproduction_commitment_timestamp: PositiveFloat
) -> bool:
    return verifier_assignment_timestamp > reproduction_commitment_timestamp


def panel_votes_are_one_per_domain(panel_domain_votes: Sequence[DomainId]) -> bool:
    return len(panel_domain_votes) == len(set(panel_domain_votes))


def verifier_assignment_seed_for_row(
    verifier_assignment_namespace_seed: NamespaceSeed, reproduction_commitment_hash: ArtifactDigest
) -> DerivedSeed:
    return derive_uint32(
        VERIFIER_ASSIGNMENT_SEPARATOR,
        verifier_assignment_namespace_seed,
        reproduction_commitment_hash,
    )


def deterministic_verifier_panel(
    eligible_domains: Sequence[DomainId], row_seed: DerivedSeed, panel_size: PositiveInt
) -> tuple[DomainId, ...]:
    return deterministic_order(eligible_domains, VERIFIER_ASSIGNMENT_SEPARATOR, row_seed)[
        :panel_size
    ]


def byzantine_selection_order(
    eligible_domains: Sequence[DomainId], byzantine_selection_namespace_seed: NamespaceSeed
) -> tuple[DomainId, ...]:
    return deterministic_order(
        eligible_domains, BYZANTINE_SELECTION_SEPARATOR, byzantine_selection_namespace_seed
    )


def select_compromised_verifiers(
    byzantine_order: Sequence[DomainId], compromised_count: NonNegativeInt
) -> frozenset[DomainId]:
    return frozenset(byzantine_order[:compromised_count])


def construct_above_bound_panel(
    compromised_domains: Sequence[DomainId],
    honest_post_commitment_order: Sequence[DomainId],
    panel_size: PositiveInt,
) -> tuple[DomainId, ...]:
    remaining_slots = panel_size - len(compromised_domains)
    return tuple(compromised_domains) + tuple(honest_post_commitment_order[:remaining_slots])


def diagnostic_committee_panel(
    eligible_domains: Sequence[DomainId],
    committee_draw_namespace_seed: NamespaceSeed,
    panel_size: PositiveInt,
) -> tuple[DomainId, ...]:
    return deterministic_order(
        eligible_domains, COMMITTEE_DRAW_SEPARATOR, committee_draw_namespace_seed
    )[:panel_size]


def reproduction_row_is_certified(
    panel_reports: Sequence[TernaryOutcome],
    panel_size: PositiveInt,
    required_positive_reports: PositiveInt,
) -> bool:
    if len(panel_reports) < panel_size:
        return False
    positive_count = sum(1 for report in panel_reports if report is TernaryOutcome.POSITIVE)
    return positive_count >= required_positive_reports


def verification_pending_transition(
    adequate_eligible_verifier_count: NonNegativeInt,
    panel_positive_report_count: NonNegativeInt,
    resolved_row_requirement_reached: bool,
    verification_config: VerificationConfig,
) -> ClaimState:
    if adequate_eligible_verifier_count < verification_config.panel_size:
        return ClaimState.REPRODUCTION_PENDING
    if panel_positive_report_count < verification_config.required_positive_reports:
        return ClaimState.REPRODUCTION_PENDING
    if resolved_row_requirement_reached:
        return ClaimState.SYNTHESIS_PENDING
    return ClaimState.REPRODUCTION_PENDING
