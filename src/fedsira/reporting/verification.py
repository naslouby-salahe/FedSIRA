from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from fedsira.domain.enums import ExperimentLifecycleState
from fedsira.domain.records import CanonicalToken
from fedsira.experiments.execution import is_terminal_experiment_state
from fedsira.experiments.planning import ExperimentPlan


@dataclass(frozen=True)
class CompletenessVerificationResult:
    passed: bool
    failures: tuple[CanonicalToken, ...]

    def __bool__(self) -> bool:
        return self.passed


def verify_planned_cell_count_satisfied(
    plan: ExperimentPlan,
    terminal_record_counts: Mapping[CanonicalToken, int],
) -> CompletenessVerificationResult:
    failures: list[CanonicalToken] = []
    for planned in plan.experiments:
        expected = len(planned.cells)
        observed = terminal_record_counts.get(planned.definition.name, 0)
        if observed != expected:
            failures.append(
                f"{planned.definition.name}: expected {expected} terminal cell records, "
                f"found {observed}"
            )
    return CompletenessVerificationResult(passed=not failures, failures=tuple(failures))


def verify_experiments_completed(
    lifecycle_states: Mapping[CanonicalToken, ExperimentLifecycleState],
    expected_experiments: Sequence[CanonicalToken],
) -> CompletenessVerificationResult:
    failures: list[CanonicalToken] = []
    for experiment in expected_experiments:
        state = lifecycle_states.get(experiment)
        if state is not ExperimentLifecycleState.COMPLETED:
            failures.append(
                f"{experiment}: lifecycle state is "
                f"{state.value if state is not None else 'unknown'}, expected Completed"
            )
    return CompletenessVerificationResult(passed=not failures, failures=tuple(failures))


def verify_experiments_reached_terminal_state(
    lifecycle_states: Mapping[CanonicalToken, ExperimentLifecycleState],
    expected_experiments: Sequence[CanonicalToken],
) -> CompletenessVerificationResult:
    failures: list[CanonicalToken] = []
    for experiment in expected_experiments:
        state = lifecycle_states.get(experiment)
        if state is None or not is_terminal_experiment_state(state):
            failures.append(
                f"{experiment}: lifecycle state is "
                f"{state.value if state is not None else 'unknown'}, not terminal"
            )
    return CompletenessVerificationResult(passed=not failures, failures=tuple(failures))


def verify_no_stale_ancestors(
    stale_ancestor_identities: Sequence[CanonicalToken],
) -> CompletenessVerificationResult:
    return CompletenessVerificationResult(
        passed=not stale_ancestor_identities,
        failures=tuple(stale_ancestor_identities),
    )


def verify_claim_states_derivable(
    claim_state_count: int, expected_claim_count: int
) -> CompletenessVerificationResult:
    if claim_state_count != expected_claim_count:
        return CompletenessVerificationResult(
            passed=False,
            failures=(
                f"derived {claim_state_count} claim states, expected {expected_claim_count}",
            ),
        )
    return CompletenessVerificationResult(passed=True, failures=())
