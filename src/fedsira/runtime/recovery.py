from fedsira.domain.enums import FailureClass
from fedsira.domain.records import ArtifactDigest, BooleanValue, RetryCount
from fedsira.runtime.state import is_automatically_retriable


def automatic_recovery_permitted(
    failure_class: FailureClass,
    attempts_used: RetryCount,
    automatic_infrastructure_retries_per_cell_phase: RetryCount,
) -> BooleanValue:
    if not is_automatically_retriable(failure_class):
        return False
    return attempts_used < automatic_infrastructure_retries_per_cell_phase


def validate_recovered_checkpoint_lineage(
    expected_checkpoint_digest: ArtifactDigest, recovered_checkpoint_digest: ArtifactDigest
) -> None:
    if expected_checkpoint_digest != recovered_checkpoint_digest:
        raise ValueError(
            "recovered checkpoint digest does not match the expected hash-valid lineage"
        )
