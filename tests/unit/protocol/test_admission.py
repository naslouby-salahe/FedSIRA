import pytest

from fedsira.domain.enums import ClaimState
from fedsira.protocol.admission import validate_admission_requires_final_gate


def test_admitted_state_requires_valid_final_gate_artifact() -> None:
    validate_admission_requires_final_gate(ClaimState.ADMITTED, True)
    with pytest.raises(ValueError, match="final-gate"):
        validate_admission_requires_final_gate(ClaimState.ADMITTED, False)


def test_non_admitted_state_does_not_require_final_gate_artifact() -> None:
    validate_admission_requires_final_gate(ClaimState.DORMANT, False)
