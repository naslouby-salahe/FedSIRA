import pytest

from fedsira.domain.enums import (
    ArtifactLifecycleState,
    CellPhaseState,
    DatasetId,
    ExperimentLifecycleState,
    FailureClass,
    ScientificCellPhase,
    SeedDerivationLabel,
)


def test_dataset_id_has_exactly_the_two_roadmap_datasets() -> None:
    assert {member.value for member in DatasetId} == {"N-BaIoT", "CICIoT2023"}


def test_seed_derivation_label_retains_the_fifteen_namespace_tokens() -> None:
    namespace_tokens = {
        "DATA_SPLIT",
        "DOMAIN_PARTITION",
        "MODEL_INITIALIZATION",
        "CLIENT_SAMPLING",
        "SOURCE_SELECTION",
        "SOURCE_TRAINING",
        "ATTACK_GENERATION",
        "SCREEN_DOMAIN_ORDER",
        "SCREEN_FOLD",
        "REPRODUCER_ORDER",
        "VERIFIER_ASSIGNMENT",
        "BYZANTINE_SELECTION",
        "LOCAL_TRAINING",
        "COMMITTEE_DRAW",
        "HETEROGENEITY",
    }
    assert namespace_tokens.issubset({member.value for member in SeedDerivationLabel})
    assert "BOOTSTRAP" not in {member.value for member in SeedDerivationLabel}


def test_failure_class_has_exactly_nine_classes() -> None:
    assert len(list(FailureClass)) == 9


def test_scientific_cell_phase_has_exactly_six_phases() -> None:
    assert len(list(ScientificCellPhase)) == 6


def test_artifact_lifecycle_state_members() -> None:
    assert {member.value for member in ArtifactLifecycleState} == {
        "Staging",
        "Complete",
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
