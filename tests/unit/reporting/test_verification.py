from fedsira.domain.enums import ExperimentLifecycleState
from fedsira.experiments.planning import build_plan
from fedsira.reporting.verification import (
    CompletenessVerificationResult,
    ExperimentLifecycleRecord,
    ExperimentTerminalCount,
    verify_experiments_completed,
    verify_experiments_reached_terminal_state,
    verify_no_stale_ancestors,
    verify_planned_cell_count_satisfied,
)


def test_execution_evidence_verification_requires_each_planned_cell() -> None:
    plan = build_plan()
    counts = tuple(
        ExperimentTerminalCount(experiment=item.definition.name, count=len(item.cells))
        for item in plan.experiments
    )
    assert verify_planned_cell_count_satisfied(plan, counts).passed
    assert not verify_planned_cell_count_satisfied(plan, ()).passed


def test_execution_evidence_verification_requires_complete_terminal_experiments() -> None:
    states = (
        ExperimentLifecycleRecord(
            experiment="Data and Domain Evidence Validation",
            state=ExperimentLifecycleState.COMPLETED,
        ),
        ExperimentLifecycleRecord(
            experiment="Protocol Invariant Validation",
            state=ExperimentLifecycleState.RUNNING,
        ),
    )
    assert verify_experiments_completed(states, ("Data and Domain Evidence Validation",)).passed
    assert not verify_experiments_reached_terminal_state(
        states, ("Protocol Invariant Validation",)
    ).passed


def test_stale_artifact_evidence_blocks_completion() -> None:
    assert verify_no_stale_ancestors(()).passed
    assert not verify_no_stale_ancestors(("a" * 64,)).passed
    assert CompletenessVerificationResult(passed=True, failures=()).passed
