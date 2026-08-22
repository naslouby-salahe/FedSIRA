from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.schema import NBaiotDomain
from fedsira.domain.enums import ClaimState, TernaryOutcome
from fedsira.domain.records import NonNegativeInt, PositiveInt
from fedsira.protocol.reproduction import next_reproducer_domain


class BaselineIdentity(StrEnum):
    LOCAL_ONLY_REFERENCE = "Local-Only Reference"
    CENTRALIZED_REFERENCE = "Centralized Reference"
    FEDAVG_REFERENCE = "FedAvg Reference"
    CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION = "Client Review with Direct Source Admission"
    CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN = "Client Review then One Independent Retrain"
    ONE_INDEPENDENT_RETRAIN = "One Independent Retrain"
    CANDIDATE_FREE_FULL_PATH = "Candidate-Free Full Path"
    MULTIPLE_RETRAINS_WITH_DIRECT_KRUM = "Multiple Retrains with Direct Krum"
    THREE_ROW_COORDINATE_MEDIAN_ALTERNATIVE = "Three-Row Coordinate-Median Alternative"


STANDARD_FL_BASELINE_ROUNDS: Final[PositiveInt] = 20
STANDARD_FL_BASELINE_LOCAL_EPOCHS_PER_ROUND: Final[PositiveInt] = 1
POST_REFERENCE_RETRAIN_MAXIMUM_LOCAL_EPOCHS: Final[PositiveInt] = 5

TUNING_FORBIDDEN_ROLES: Final[frozenset[Role]] = frozenset({Role.REPORT_TEST, Role.FINAL_GATE})


@dataclass(frozen=True)
class PostReferenceDataAccess:
    source_target_view: Role
    non_source_target_view: Role
    supported_replay_view: Role


ORDINARY_POST_REFERENCE_DATA_ACCESS: Final[PostReferenceDataAccess] = PostReferenceDataAccess(
    source_target_view=Role.SOURCE_PROPOSAL,
    non_source_target_view=Role.REPRODUCTION,
    supported_replay_view=Role.POST_REFERENCE_REPLAY,
)


def domain_target_view(
    domain: NBaiotDomain,
    source_domain: NBaiotDomain | None,
    data_access: PostReferenceDataAccess,
) -> Role:
    if domain == source_domain:
        return data_access.source_target_view
    return data_access.non_source_target_view


def validate_role_not_used_for_tuning(role: Role) -> None:
    if role in TUNING_FORBIDDEN_ROLES:
        raise ValueError(f"role {role.value} must never be used for baseline tuning")


def domain_without_target_view_may_participate(baseline_allows_full_participation: bool) -> bool:
    return baseline_allows_full_participation


def first_eligible_non_source_reproducer(
    reproducer_order: Sequence[NBaiotDomain], non_source_eligible_domains: frozenset[NBaiotDomain]
) -> NBaiotDomain | None:
    return next_reproducer_domain(reproducer_order, frozenset(), non_source_eligible_domains)


def single_fresh_verifier_domain(
    verifier_assignment_order: Sequence[NBaiotDomain],
    excluded_domains: frozenset[NBaiotDomain],
    adequate_eligible_domains: frozenset[NBaiotDomain],
) -> NBaiotDomain | None:
    return next_reproducer_domain(
        verifier_assignment_order, excluded_domains, adequate_eligible_domains
    )


def single_fresh_verifier_outcome(
    verifier_domain: NBaiotDomain | None, verifier_vote: TernaryOutcome | None
) -> ClaimState:
    if verifier_domain is None:
        return ClaimState.DORMANT
    if verifier_vote is TernaryOutcome.POSITIVE:
        return ClaimState.ADMITTED
    return ClaimState.REJECTED_CLAIM


def review_style_baseline_outcome(
    adequate_reviewer_count: NonNegativeInt,
    positive_report_count: NonNegativeInt,
    panel_size: PositiveInt,
    required_positive_reports: PositiveInt,
) -> ClaimState:
    if adequate_reviewer_count < panel_size:
        return ClaimState.DORMANT
    if positive_report_count >= required_positive_reports:
        return ClaimState.ADMITTED
    return ClaimState.REJECTED_CLAIM
