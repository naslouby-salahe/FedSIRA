from fedsira.domain.enums import AdmissionOpeningMode
from fedsira.protocol.baselines.independent_retraining import (
    candidate_free_full_path_opening_mode,
    one_independent_retrain_local_epochs,
)


def test_one_independent_retrain_local_epochs_is_five() -> None:
    assert one_independent_retrain_local_epochs() == 5


def test_candidate_free_full_path_uses_candidate_free_opening_mode() -> None:
    assert candidate_free_full_path_opening_mode() is AdmissionOpeningMode.CANDIDATE_FREE
