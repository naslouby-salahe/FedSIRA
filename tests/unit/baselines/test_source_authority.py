import torch

from fedsira.datasets.common import Role
from fedsira.domain.enums import AdmissionState, ReviewPanelProfile
from fedsira.protocol.baselines.defenses import (
    CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES,
    client_review_direct_admission_production_is_source,
    client_review_then_retrain_local_epochs,
    client_review_then_retrain_should_discard_source_weights,
    review_panel_requirements,
)


def test_client_review_composite_screen_roles_and_reviewer_count() -> None:
    assert CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES == (
        Role.CANDIDATE_SCREEN,
        Role.POST_REFERENCE_REPLAY,
    )
    assert review_panel_requirements(ReviewPanelProfile.CLIENT_REVIEW)[0] == 3


def test_secure_continual_assessment_reviewer_gate_is_two_of_three() -> None:
    assert review_panel_requirements(ReviewPanelProfile.SECURE_CONTINUAL_ASSESSMENT) == (3, 2)


def test_client_review_direct_admission_production_is_source() -> None:
    source_update = torch.tensor([1.0, 2.0, 3.0])
    assert client_review_direct_admission_production_is_source(source_update, source_update) is True
    other = torch.tensor([1.0, 2.0, 4.0])
    assert client_review_direct_admission_production_is_source(other, source_update) is False


def test_client_review_then_retrain_discards_source_weights_only_when_admitted() -> None:
    assert client_review_then_retrain_should_discard_source_weights(AdmissionState.ADMITTED) is True
    assert (
        client_review_then_retrain_should_discard_source_weights(AdmissionState.REJECTED) is False
    )
    assert client_review_then_retrain_should_discard_source_weights(AdmissionState.DORMANT) is False


def test_client_review_then_retrain_local_epochs_is_five() -> None:
    assert client_review_then_retrain_local_epochs() == 5
