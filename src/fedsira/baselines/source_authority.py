from typing import Final

import torch

from fedsira.baselines.registry import POST_REFERENCE_RETRAIN_MAXIMUM_LOCAL_EPOCHS
from fedsira.datasets.common import Role
from fedsira.domain.enums import ClaimState
from fedsira.domain.records import PositiveInt

CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES: Final[tuple[Role, Role]] = (
    Role.CANDIDATE_SCREEN,
    Role.POST_REFERENCE_REPLAY,
)
CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT: Final[PositiveInt] = 3


def client_review_direct_admission_production_is_source(
    production_update: torch.Tensor, source_update: torch.Tensor
) -> bool:
    return torch.equal(production_update, source_update)


def client_review_then_retrain_should_discard_source_weights(review_outcome: ClaimState) -> bool:
    return review_outcome is ClaimState.ADMITTED


def client_review_then_retrain_local_epochs() -> PositiveInt:
    return POST_REFERENCE_RETRAIN_MAXIMUM_LOCAL_EPOCHS
