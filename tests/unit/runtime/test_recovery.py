import pytest

from fedsira.domain.enums import FailureClass
from fedsira.runtime.recovery import (
    automatic_recovery_permitted,
    validate_recovered_checkpoint_lineage,
)


def test_infrastructure_interruption_is_permitted_once() -> None:
    assert automatic_recovery_permitted(FailureClass.INFRASTRUCTURE_INTERRUPTION, 0, 1)


def test_infrastructure_interruption_is_not_permitted_after_limit_reached() -> None:
    assert not automatic_recovery_permitted(FailureClass.INFRASTRUCTURE_INTERRUPTION, 1, 1)


def test_numerical_failure_is_never_automatically_retried() -> None:
    assert not automatic_recovery_permitted(FailureClass.NUMERICAL_FAILURE, 0, 1)


def test_data_invalid_is_never_automatically_retried() -> None:
    assert not automatic_recovery_permitted(FailureClass.DATA_INVALID, 0, 1)


def test_matching_checkpoint_digest_is_accepted() -> None:
    digest = "a" * 64
    validate_recovered_checkpoint_lineage(digest, digest)


def test_mismatched_checkpoint_digest_is_rejected() -> None:
    with pytest.raises(ValueError):
        validate_recovered_checkpoint_lineage("a" * 64, "b" * 64)
