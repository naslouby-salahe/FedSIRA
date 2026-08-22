from fedsira.baselines.independent_retraining import (
    candidate_free_full_path_opening_mode,
    one_independent_retrain_local_epochs,
)
from fedsira.domain.enums import ClaimOpeningMode


def test_one_independent_retrain_local_epochs_is_five() -> None:
    assert one_independent_retrain_local_epochs() == 5


def test_candidate_free_full_path_uses_candidate_free_opening_mode() -> None:
    assert candidate_free_full_path_opening_mode() is ClaimOpeningMode.CANDIDATE_FREE
