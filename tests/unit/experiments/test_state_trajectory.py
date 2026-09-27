from fedsira.domain.enums import AdmissionState, MetricObservationKey
from fedsira.experiments.handlers import ProtocolCellExecutor


def test_evidence_scarcity_trajectory_expires_dormant_claim_at_resource_horizon() -> None:
    trajectory = ProtocolCellExecutor().evidence_scarcity_trajectory((), AdmissionState.DORMANT)

    assert trajectory[0].state is AdmissionState.DORMANT
    assert trajectory[-2].state is AdmissionState.DORMANT
    assert trajectory[-1].state is AdmissionState.EXPIRED


def test_evidence_scarcity_trajectory_preserves_earlier_terminal_outcome() -> None:
    trajectory = ProtocolCellExecutor().evidence_scarcity_trajectory(
        ((MetricObservationKey.EVIDENCE_ARRIVAL_CYCLE, 0.0),), AdmissionState.ADMITTED
    )

    assert trajectory[-1].state is AdmissionState.ADMITTED
