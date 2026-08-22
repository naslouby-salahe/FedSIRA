from fedsira.baselines.registry import POST_REFERENCE_RETRAIN_MAXIMUM_LOCAL_EPOCHS
from fedsira.domain.enums import ClaimOpeningMode
from fedsira.domain.records import PositiveInt


def one_independent_retrain_local_epochs() -> PositiveInt:
    return POST_REFERENCE_RETRAIN_MAXIMUM_LOCAL_EPOCHS


def candidate_free_full_path_opening_mode() -> ClaimOpeningMode:
    return ClaimOpeningMode.CANDIDATE_FREE
