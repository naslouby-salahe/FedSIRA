import torch

from fedsira.baselines.source_model import (
    CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES,
    CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT,
    SECURE_CONTINUAL_ASSESSMENT_REQUIRED_POSITIVE_REVIEWS,
    SECURE_CONTINUAL_ASSESSMENT_REVIEWER_COUNT,
    client_review_direct_admission_production_is_source,
    client_review_then_retrain_local_epochs,
    client_review_then_retrain_should_discard_source_weights,
)
from fedsira.datasets.common import Role
from fedsira.domain.enums import ClaimState


def test_client_review_composite_screen_roles_and_reviewer_count() -> None:
    assert CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES == (
        Role.CANDIDATE_SCREEN,
        Role.POST_REFERENCE_REPLAY,
    )
    assert CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT == 3


def test_secure_continual_assessment_reviewer_gate_is_two_of_three() -> None:
    assert SECURE_CONTINUAL_ASSESSMENT_REVIEWER_COUNT == 3
    assert SECURE_CONTINUAL_ASSESSMENT_REQUIRED_POSITIVE_REVIEWS == 2


def test_client_review_direct_admission_production_is_source() -> None:
    source_update = torch.tensor([1.0, 2.0, 3.0])
    assert client_review_direct_admission_production_is_source(source_update, source_update) is True
    other = torch.tensor([1.0, 2.0, 4.0])
    assert client_review_direct_admission_production_is_source(other, source_update) is False


def test_client_review_then_retrain_discards_source_weights_only_when_admitted() -> None:
    assert client_review_then_retrain_should_discard_source_weights(ClaimState.ADMITTED) is True
    assert (
        client_review_then_retrain_should_discard_source_weights(ClaimState.REJECTED_CLAIM) is False
    )
    assert client_review_then_retrain_should_discard_source_weights(ClaimState.DORMANT) is False


def test_client_review_then_retrain_local_epochs_is_five() -> None:
    assert client_review_then_retrain_local_epochs() == 5
