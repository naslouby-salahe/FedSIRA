from fedsira.domain.enums import ClaimState


def validate_admission_requires_final_gate(
    state: ClaimState, final_gate_artifact_is_valid: bool
) -> None:
    if state is ClaimState.ADMITTED and not final_gate_artifact_is_valid:
        raise ValueError("Admitted state requires a valid final-gate artifact")
