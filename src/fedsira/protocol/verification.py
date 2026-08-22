from collections.abc import Sequence

from fedsira.config.schema import VerificationConfig
from fedsira.datasets.nbaiot.schema import NBaiotDomain
from fedsira.domain.enums import ClaimState
from fedsira.domain.records import NonNegativeInt, PositiveFloat


def verifier_is_eligible(
    verifier_domain: NBaiotDomain,
    source_domain: NBaiotDomain | None,
    reproducer_domain: NBaiotDomain,
) -> bool:
    if verifier_domain == reproducer_domain:
        return False
    return source_domain is None or verifier_domain != source_domain


def verifier_assignment_timestamp_is_valid(
    verifier_assignment_timestamp: PositiveFloat, reproduction_commitment_timestamp: PositiveFloat
) -> bool:
    return verifier_assignment_timestamp > reproduction_commitment_timestamp


def panel_votes_are_one_per_domain(panel_domain_votes: Sequence[NBaiotDomain]) -> bool:
    return len(panel_domain_votes) == len(set(panel_domain_votes))


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
