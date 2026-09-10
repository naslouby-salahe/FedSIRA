from fedsira.domain.enums import AdmissionOpeningMode
from fedsira.domain.types import LocalEpochCount
from fedsira.protocol.baselines.references import post_reference_retrain_maximum_local_epochs


def one_independent_retrain_local_epochs() -> LocalEpochCount:
    return post_reference_retrain_maximum_local_epochs()


def candidate_free_full_path_opening_mode() -> AdmissionOpeningMode:
    return AdmissionOpeningMode.CANDIDATE_FREE
