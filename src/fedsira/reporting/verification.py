from __future__ import annotations

from fedsira.analysis.claims import ClaimStateResult, FinalClaimState
from fedsira.domain.enums import ExperimentLifecycleState
from fedsira.domain.records import (
    CheckpointIdentity,
    ClaimDefinitionCount,
    ExperimentName,
    FrozenDomainModel,
    ReportVerificationFailure,
    ScientificCellCount,
    VerificationPassed,
)
from fedsira.experiments.execution import TERMINAL_EXPERIMENT_STATES, PersistedExecutionRecord
from fedsira.experiments.planning import ExperimentPlan, PlannedExperiment


class ExperimentTerminalCount(FrozenDomainModel):
    experiment: ExperimentName
    count: ScientificCellCount


class ExperimentLifecycleRecord(FrozenDomainModel):
    experiment: ExperimentName
    state: ExperimentLifecycleState


class CompletenessVerificationResult(FrozenDomainModel):
    passed: VerificationPassed
    failures: tuple[ReportVerificationFailure, ...]


def terminal_count_for_planned_experiment(
    planned: PlannedExperiment,
    records: tuple[PersistedExecutionRecord, ...],
) -> ScientificCellCount:
    planned_keys = frozenset(cell.semantic_key for cell in planned.cells)
    return sum(record.semantic_key in planned_keys for record in records)


def _terminal_count(
    records: tuple[ExperimentTerminalCount, ...],
    experiment: ExperimentName,
) -> ScientificCellCount:
    for record in records:
        if record.experiment == experiment:
            return record.count
    return 0


def _lifecycle_state(
    records: tuple[ExperimentLifecycleRecord, ...],
    experiment: ExperimentName,
) -> ExperimentLifecycleState | None:
    for record in records:
        if record.experiment == experiment:
            return record.state
    return None


def verify_planned_cell_count_satisfied(
    plan: ExperimentPlan,
    terminal_record_counts: tuple[ExperimentTerminalCount, ...],
) -> CompletenessVerificationResult:
    failures: list[ReportVerificationFailure] = []
    for planned in plan.experiments:
        expected = len(planned.cells)
        observed = _terminal_count(terminal_record_counts, planned.definition.name)
        if observed != expected:
            failures.append(
                f"{planned.definition.name}: expected {expected} terminal cell records, "
                f"found {observed}"
            )
    return CompletenessVerificationResult(passed=not failures, failures=tuple(failures))


def verify_experiments_completed(
    lifecycle_states: tuple[ExperimentLifecycleRecord, ...],
    expected_experiments: tuple[ExperimentName, ...],
) -> CompletenessVerificationResult:
    failures: list[ReportVerificationFailure] = []
    for experiment in expected_experiments:
        state = _lifecycle_state(lifecycle_states, experiment)
        if state is not ExperimentLifecycleState.COMPLETED:
            failures.append(
                f"{experiment}: lifecycle state is "
                f"{state.value if state is not None else 'unknown'}, expected Completed"
            )
    return CompletenessVerificationResult(passed=not failures, failures=tuple(failures))


def verify_experiments_reached_terminal_state(
    lifecycle_states: tuple[ExperimentLifecycleRecord, ...],
    expected_experiments: tuple[ExperimentName, ...],
) -> CompletenessVerificationResult:
    failures: list[ReportVerificationFailure] = []
    for experiment in expected_experiments:
        state = _lifecycle_state(lifecycle_states, experiment)
        if state is None or state not in TERMINAL_EXPERIMENT_STATES:
            failures.append(
                f"{experiment}: lifecycle state is "
                f"{state.value if state is not None else 'unknown'}, not terminal"
            )
    return CompletenessVerificationResult(passed=not failures, failures=tuple(failures))


def verify_no_stale_ancestors(
    stale_ancestor_identities: tuple[CheckpointIdentity, ...],
) -> CompletenessVerificationResult:
    return CompletenessVerificationResult(
        passed=not stale_ancestor_identities,
        failures=tuple(stale_ancestor_identities),
    )


def verify_claim_states_derivable(
    claim_states: tuple[ClaimStateResult, ...],
    expected_claim_count: ClaimDefinitionCount,
) -> CompletenessVerificationResult:
    failures: list[ReportVerificationFailure] = []
    if len(claim_states) != expected_claim_count:
        failures.append(
            f"derived {len(claim_states)} claim states, expected {expected_claim_count}"
        )
    unresolved = tuple(
        claim.claim_id for claim in claim_states if claim.state is FinalClaimState.NOT_TESTED
    )
    if unresolved:
        failures.append(f"claims lack complete verified evidence: {', '.join(unresolved)}")
    return CompletenessVerificationResult(passed=not failures, failures=tuple(failures))
