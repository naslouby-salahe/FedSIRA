from fedsira.domain.models import AdmissionDelayDecomposition


def test_admission_delay_decomposition_sums_post_evidence_components() -> None:
    decomposition = AdmissionDelayDecomposition(
        logical_information_arrival_cycles=3,
        assignment_seconds=1.0,
        reproduce_seconds=2.0,
        verify_seconds=3.0,
        synthesize_seconds=4.0,
    )
    assert decomposition.post_evidence_wall_clock_seconds == 10.0
