from fedsira.domain.enums import FailureClass
from fedsira.domain.types import AutomaticRecoveryPermitted, RetryCount
from fedsira.runtime.state import is_automatically_retriable


def automatic_recovery_permitted(
    failure_class: FailureClass,
    attempts_used: RetryCount,
    automatic_infrastructure_retries_per_cell_phase: RetryCount,
) -> AutomaticRecoveryPermitted:
    if not is_automatically_retriable(failure_class):
        return False
    return attempts_used < automatic_infrastructure_retries_per_cell_phase
