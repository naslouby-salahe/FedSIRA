from collections.abc import Sequence
from enum import StrEnum
from typing import Final

from fedsira.datasets.common import Role
from fedsira.domain.enums import ClaimState, TernaryOutcome
from fedsira.domain.records import (
    BooleanFlag,
    DomainId,
    FrozenDomainModel,
    NonNegativeInt,
    PositiveInt,
)
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
    MULTIPLE_MODEL_CERTIFIED_ENSEMBLE = "Multiple-Model Certified Ensemble"
    INDEPENDENT_LOCAL_REFERENCE_WITH_SOURCE_ADMISSION = (
        "Independent Local Reference with Source Admission"
    )
    UPDATE_RECONSTRUCTION_FILTER = "Update Reconstruction Filter"
    DENSITY_CLUSTER_TRIMMED_MEAN = "Density-Cluster Trimmed Mean"
    SECURE_CONTINUAL_ASSESSMENT_REFERENCE = "Secure Continual Assessment Reference"
    RECOVERY_AFTER_SOURCE_ADMISSION = "Recovery after Source Admission"
    SOURCE_UPDATE_SANITIZATION_REFERENCE = "Source-Update Sanitization Reference"
    KRUM_ROBUST_AGGREGATION_REFERENCE = "Krum Robust Aggregation Reference"


class BaselineValidationFixture(StrEnum):
    LEGITIMATE_TARGET_CAPABILITY = "Legitimate Target Capability"
    USEFUL_BACKDOORED_SOURCE_5_PERCENT = "Useful Backdoored Source — 5%"
    MODEL_REPLACEMENT_BACKDOOR = "Model-Replacement Backdoor"


BASELINE_VALIDATION_FIXTURE_MAP: Final[dict[BaselineIdentity, BaselineValidationFixture]] = {
    BaselineIdentity.LOCAL_ONLY_REFERENCE: BaselineValidationFixture.LEGITIMATE_TARGET_CAPABILITY,
    BaselineIdentity.CENTRALIZED_REFERENCE: BaselineValidationFixture.LEGITIMATE_TARGET_CAPABILITY,
    BaselineIdentity.FEDAVG_REFERENCE: BaselineValidationFixture.LEGITIMATE_TARGET_CAPABILITY,
    BaselineIdentity.ONE_INDEPENDENT_RETRAIN: (
        BaselineValidationFixture.LEGITIMATE_TARGET_CAPABILITY
    ),
    BaselineIdentity.CANDIDATE_FREE_FULL_PATH: (
        BaselineValidationFixture.LEGITIMATE_TARGET_CAPABILITY
    ),
    BaselineIdentity.MULTIPLE_MODEL_CERTIFIED_ENSEMBLE: (
        BaselineValidationFixture.LEGITIMATE_TARGET_CAPABILITY
    ),
    BaselineIdentity.CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION: (
        BaselineValidationFixture.USEFUL_BACKDOORED_SOURCE_5_PERCENT
    ),
    BaselineIdentity.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN: (
        BaselineValidationFixture.USEFUL_BACKDOORED_SOURCE_5_PERCENT
    ),
    BaselineIdentity.RECOVERY_AFTER_SOURCE_ADMISSION: (
        BaselineValidationFixture.USEFUL_BACKDOORED_SOURCE_5_PERCENT
    ),
    BaselineIdentity.SOURCE_UPDATE_SANITIZATION_REFERENCE: (
        BaselineValidationFixture.USEFUL_BACKDOORED_SOURCE_5_PERCENT
    ),
    BaselineIdentity.INDEPENDENT_LOCAL_REFERENCE_WITH_SOURCE_ADMISSION: (
        BaselineValidationFixture.USEFUL_BACKDOORED_SOURCE_5_PERCENT
    ),
    BaselineIdentity.SECURE_CONTINUAL_ASSESSMENT_REFERENCE: (
        BaselineValidationFixture.USEFUL_BACKDOORED_SOURCE_5_PERCENT
    ),
    BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM: (
        BaselineValidationFixture.MODEL_REPLACEMENT_BACKDOOR
    ),
    BaselineIdentity.THREE_ROW_COORDINATE_MEDIAN_ALTERNATIVE: (
        BaselineValidationFixture.MODEL_REPLACEMENT_BACKDOOR
    ),
    BaselineIdentity.UPDATE_RECONSTRUCTION_FILTER: (
        BaselineValidationFixture.MODEL_REPLACEMENT_BACKDOOR
    ),
    BaselineIdentity.DENSITY_CLUSTER_TRIMMED_MEAN: (
        BaselineValidationFixture.MODEL_REPLACEMENT_BACKDOOR
    ),
    BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE: (
        BaselineValidationFixture.MODEL_REPLACEMENT_BACKDOOR
    ),
}

if BASELINE_VALIDATION_FIXTURE_MAP.keys() != set(BaselineIdentity):
    raise AssertionError("every registered baseline must have exactly one predeclared fixture")


STANDARD_FL_BASELINE_ROUNDS: Final[PositiveInt] = 20
STANDARD_FL_BASELINE_LOCAL_EPOCHS_PER_ROUND: Final[PositiveInt] = 1
POST_REFERENCE_RETRAIN_MAXIMUM_LOCAL_EPOCHS: Final[PositiveInt] = 5

TUNING_FORBIDDEN_ROLES: Final[frozenset[Role]] = frozenset({Role.REPORT_TEST, Role.FINAL_GATE})


class PostReferenceDataAccess(FrozenDomainModel):
    source_target_view: Role
    non_source_target_view: Role
    supported_replay_view: Role


ORDINARY_POST_REFERENCE_DATA_ACCESS: Final[PostReferenceDataAccess] = PostReferenceDataAccess(
    source_target_view=Role.SOURCE_PROPOSAL,
    non_source_target_view=Role.REPRODUCTION,
    supported_replay_view=Role.POST_REFERENCE_REPLAY,
)


def domain_target_view(
    domain: DomainId,
    source_domain: DomainId | None,
    data_access: PostReferenceDataAccess = ORDINARY_POST_REFERENCE_DATA_ACCESS,
) -> Role:
    if domain == source_domain:
        return data_access.source_target_view
    return data_access.non_source_target_view


def validate_role_not_used_for_tuning(role: Role) -> None:
    if role in TUNING_FORBIDDEN_ROLES:
        raise ValueError(f"role {role.value} must never be used for baseline tuning")


def domain_without_target_view_may_participate(
    baseline_allows_full_participation: BooleanFlag,
) -> BooleanFlag:
    return baseline_allows_full_participation


def first_eligible_non_source_reproducer(
    reproducer_order: Sequence[DomainId], non_source_eligible_domains: frozenset[DomainId]
) -> DomainId | None:
    return next_reproducer_domain(reproducer_order, frozenset(), non_source_eligible_domains)


def single_fresh_verifier_domain(
    verifier_assignment_order: Sequence[DomainId],
    excluded_domains: frozenset[DomainId],
    adequate_eligible_domains: frozenset[DomainId],
) -> DomainId | None:
    return next_reproducer_domain(
        verifier_assignment_order, excluded_domains, adequate_eligible_domains
    )


def single_fresh_verifier_outcome(
    verifier_domain: DomainId | None, verifier_vote: TernaryOutcome | None
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
