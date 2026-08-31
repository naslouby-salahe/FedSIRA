from fedsira.baselines.references import post_reference_retrain_maximum_local_epochs
from fedsira.domain.enums import ClaimOpeningMode
from fedsira.domain.records import LocalEpochCount


def one_independent_retrain_local_epochs() -> LocalEpochCount:
    return post_reference_retrain_maximum_local_epochs()


def candidate_free_full_path_opening_mode() -> ClaimOpeningMode:
    return ClaimOpeningMode.CANDIDATE_FREE
