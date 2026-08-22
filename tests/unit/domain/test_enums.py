import pytest

from fedsira.domain.enums import (
    ArtifactLifecycleState,
    CellPhaseState,
    DatasetId,
    ExperimentLifecycleState,
    FailureClass,
    ScientificCellPhase,
    SeedNamespace,
)


def test_dataset_id_has_exactly_the_two_roadmap_datasets() -> None:
    assert {member.value for member in DatasetId} == {"N-BaIoT", "CICIoT2023"}


def test_seed_namespace_has_exactly_fifteen_fixed_tokens() -> None:
    assert len(list(SeedNamespace)) == 15
    assert "BOOTSTRAP" not in {member.value for member in SeedNamespace}


def test_failure_class_has_exactly_nine_classes() -> None:
    assert len(list(FailureClass)) == 9


def test_scientific_cell_phase_has_exactly_six_phases() -> None:
    assert len(list(ScientificCellPhase)) == 6


def test_artifact_lifecycle_state_members() -> None:
    assert {member.value for member in ArtifactLifecycleState} == {
        "Staging",
        "Complete",
        "Stale",
        "Retired",
    }


def test_experiment_lifecycle_state_members() -> None:
    assert {member.value for member in ExperimentLifecycleState} == {
        "Not Started",
        "Blocked",
        "Ready",
        "Running",
        "Completed",
        "Failed",
        "Invalid",
    }


def test_cell_phase_state_members() -> None:
    assert {member.value for member in CellPhaseState} == {
        "Planned",
        "Running",
        "Completed",
        "Failed",
        "Invalid",
    }


def test_enum_members_are_not_equal_to_plain_strings_by_construction() -> None:
    with pytest.raises(ValueError):
        DatasetId("not-a-real-dataset")
