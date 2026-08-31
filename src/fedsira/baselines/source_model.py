from typing import Final

import torch

from fedsira.baselines.references import post_reference_retrain_maximum_local_epochs
from fedsira.config.models import MaterialityConfig
from fedsira.datasets.common import Role
from fedsira.domain.enums import ClaimState
from fedsira.domain.types import (
    CapabilityContractSatisfied,
    DiscardSourceWeights,
    FederatedRoundCount,
    LocalEpochCount,
    Probability,
    ReviewerCount,
    ReviewerPositiveDecision,
    SourceIsProductionUpdate,
)
from fedsira.runtime.state import current_application_context

CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES: Final[tuple[Role, Role]] = (
    Role.CANDIDATE_SCREEN,
    Role.POST_REFERENCE_REPLAY,
)
CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT: Final[ReviewerCount] = 3
SECURE_CONTINUAL_ASSESSMENT_REVIEWER_COUNT: Final[ReviewerCount] = 3
SECURE_CONTINUAL_ASSESSMENT_REQUIRED_POSITIVE_REVIEWS: Final[ReviewerCount] = 2
INDEPENDENT_LOCAL_REFERENCE_REVIEWER_COUNT: Final[ReviewerCount] = 3
INDEPENDENT_LOCAL_REFERENCE_REQUIRED_POSITIVE_REVIEWS: Final[ReviewerCount] = 2


def client_review_direct_admission_production_is_source(
    production_update: torch.Tensor, source_update: torch.Tensor
) -> SourceIsProductionUpdate:
    return torch.equal(production_update, source_update)


def validate_client_review_composite_screen(roles: tuple[Role, ...]) -> None:
    if roles != CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES:
        raise ValueError(
            "client review must use the fixed composite screen view: "
            "target Candidate Screen rows plus supported Post-Reference Replay rows"
        )


def validate_client_review_reviewer_count(reviewer_count: ReviewerCount) -> None:
    if reviewer_count != CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT:
        raise ValueError(
            f"client review requires exactly {CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT} reviewers"
        )


def client_review_then_retrain_should_discard_source_weights(
    review_outcome: ClaimState,
) -> DiscardSourceWeights:
    return review_outcome is ClaimState.ADMITTED


def client_review_then_retrain_local_epochs() -> LocalEpochCount:
    return post_reference_retrain_maximum_local_epochs()


def independent_local_reference_reviewer_is_positive(
    source_satisfies_capability_contract: CapabilityContractSatisfied,
    source_supported_macro_f1: Probability,
    local_reference_supported_macro_f1: Probability,
    source_benign_false_alarm_rate: Probability,
    local_reference_benign_false_alarm_rate: Probability,
    materiality_config: MaterialityConfig,
) -> ReviewerPositiveDecision:
    if not source_satisfies_capability_contract:
        return False
    if (
        source_supported_macro_f1
        < local_reference_supported_macro_f1
        - materiality_config.supported_macro_f1_noninferiority_margin
    ):
        return False
    return (
        source_benign_false_alarm_rate
        <= local_reference_benign_false_alarm_rate
        + materiality_config.benign_false_alarm_rate_noninferiority_margin
    )


def secure_continual_assessment_post_reference_rounds() -> FederatedRoundCount:
    baselines = current_application_context().scientific_config.baselines
    return baselines.secure_continual_assessment_post_reference_rounds
