from typing import Final

import torch

from fedsira.baselines.registry import POST_REFERENCE_RETRAIN_MAXIMUM_LOCAL_EPOCHS
from fedsira.config.schema import BaselinesConfig, MaterialityConfig
from fedsira.datasets.common import Role
from fedsira.domain.enums import ClaimState
from fedsira.domain.records import PositiveInt, Probability

CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES: Final[tuple[Role, Role]] = (
    Role.CANDIDATE_SCREEN,
    Role.POST_REFERENCE_REPLAY,
)
CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT: Final[PositiveInt] = 3


def client_review_direct_admission_production_is_source(
    production_update: torch.Tensor, source_update: torch.Tensor
) -> bool:
    return torch.equal(production_update, source_update)


def validate_client_review_composite_screen(roles: tuple[Role, ...]) -> None:
    if roles != CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES:
        raise ValueError(
            "client review must use the fixed composite screen view: "
            "target Candidate Screen rows plus supported Post-Reference Replay rows"
        )


def validate_client_review_reviewer_count(reviewer_count: int) -> None:
    if reviewer_count != CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT:
        raise ValueError(
            f"client review requires exactly {CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT} reviewers"
        )


def client_review_then_retrain_should_discard_source_weights(review_outcome: ClaimState) -> bool:
    return review_outcome is ClaimState.ADMITTED


def client_review_then_retrain_local_epochs() -> PositiveInt:
    return POST_REFERENCE_RETRAIN_MAXIMUM_LOCAL_EPOCHS


def independent_local_reference_reviewer_is_positive(
    source_satisfies_capability_contract: bool,
    source_supported_macro_f1: Probability,
    local_reference_supported_macro_f1: Probability,
    source_benign_false_alarm_rate: Probability,
    local_reference_benign_false_alarm_rate: Probability,
    materiality_config: MaterialityConfig,
) -> bool:
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


def secure_continual_assessment_post_reference_rounds(
    baselines_config: BaselinesConfig,
) -> PositiveInt:
    return baselines_config.secure_continual_assessment_post_reference_rounds
