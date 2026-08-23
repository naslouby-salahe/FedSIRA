from __future__ import annotations

from collections.abc import Mapping, Sequence

from fedsira.domain.enums import CellPhaseState, ExperimentLifecycleState, ScientificCellPhase
from fedsira.domain.records import CanonicalToken
from fedsira.experiments.planning import ExperimentPlan, ScientificCell
from fedsira.experiments.registry import (
    AblationVariant,
    BoundCondition,
    CapabilityContractGranularity,
    EpistemicFailureType,
    RootCauseMixture,
    experiment_by_name,
)

REQUIRED_CELL_PHASES: frozenset[ScientificCellPhase] = frozenset(
    {
        ScientificCellPhase.PREPARE,
        ScientificCellPhase.TRAIN,
        ScientificCellPhase.SCORE,
        ScientificCellPhase.PROTOCOL_EVALUATION,
        ScientificCellPhase.METRIC_AGGREGATION,
        ScientificCellPhase.STATISTICAL_ANALYSIS,
    }
)

TERMINAL_CELL_STATES: frozenset[CellPhaseState] = frozenset(
    {CellPhaseState.COMPLETED, CellPhaseState.FAILED, CellPhaseState.INVALID}
)

_EPISTEMIC_STRENGTHS: dict[EpistemicFailureType, tuple[str, ...]] = {
    EpistemicFailureType.SHARED_LABEL_ERROR: ("0.05", "0.10", "0.20"),
    EpistemicFailureType.SHARED_SPURIOUS_FEATURE: ("0.25", "0.50", "1.00"),
    EpistemicFailureType.ATTACKER_INDUCED_COMMON_CONTEXT: ("0.25", "0.50", "1.00"),
}

_CONDITION_VOCABULARY: dict[CanonicalToken, frozenset[str]] = {
    "Byzantine-Bound Violation": frozenset(condition.value for condition in BoundCondition),
    "Shared Epistemic-Failure Boundary": frozenset(
        f"{failure_type.value}|{strength}"
        for failure_type in EpistemicFailureType
        for strength in _EPISTEMIC_STRENGTHS[failure_type]
    ),
    "Capability Under-Specification Boundary": frozenset(
        mixture.value for mixture in RootCauseMixture
    ),
}

_METHOD_VOCABULARY: dict[CanonicalToken, frozenset[str]] = {
    "Capability Under-Specification Boundary": frozenset(
        granularity.value for granularity in CapabilityContractGranularity
    ),
    "Mechanism Ablation": frozenset(variant.value for variant in AblationVariant),
}


def validate_experiment_name_is_registered(experiment: CanonicalToken) -> None:
    experiment_by_name(experiment)


def validate_condition_vocabulary(plan: ExperimentPlan) -> None:
    for planned in plan.experiments:
        allowed = _CONDITION_VOCABULARY.get(planned.definition.name)
        if allowed is not None:
            for cell in planned.cells:
                if cell.condition not in allowed:
                    raise ValueError(
                        f"cell {cell.semantic_key} uses condition {cell.condition!r} "
                        f"outside the fixed {planned.definition.name} vocabulary"
                    )
        allowed_methods = _METHOD_VOCABULARY.get(planned.definition.name)
        if allowed_methods is not None:
            for cell in planned.cells:
                if cell.method not in allowed_methods:
                    raise ValueError(
                        f"cell {cell.semantic_key} uses method {cell.method!r} "
                        f"outside the fixed {planned.definition.name} vocabulary"
                    )


def validate_experiment_prerequisites_met(
    experiment: CanonicalToken,
    prerequisite_states: Mapping[CanonicalToken, ExperimentLifecycleState],
) -> None:
    definition = experiment_by_name(experiment)
    for prerequisite in definition.prerequisites:
        state = prerequisite_states.get(prerequisite)
        if state is not ExperimentLifecycleState.COMPLETED:
            raise ValueError(
                f"experiment {experiment} requires prerequisite {prerequisite} "
                f"to be Completed, found {state.value if state is not None else 'unknown'}"
            )


def validate_no_duplicate_semantic_cells(plan: ExperimentPlan) -> None:
    seen: set[CanonicalToken] = set()
    for planned in plan.experiments:
        for cell in planned.cells:
            if cell.semantic_key in seen:
                raise ValueError(f"duplicate semantic cell {cell.semantic_key}")
            seen.add(cell.semantic_key)


def validate_cell_phase_sequence(
    phases: Sequence[ScientificCellPhase],
) -> None:
    if len(phases) != len(set(phases)):
        raise ValueError("a cell phase may appear at most once in its execution sequence")
    for phase in phases:
        if phase not in REQUIRED_CELL_PHASES:
            raise ValueError(f"unknown scientific cell phase {phase.value}")


def validate_cell_terminal_record(
    cell: ScientificCell,
    terminal_state: CellPhaseState,
) -> None:
    if terminal_state not in TERMINAL_CELL_STATES:
        raise ValueError(
            f"cell {cell.semantic_key} terminal state {terminal_state.value} is not terminal"
        )
