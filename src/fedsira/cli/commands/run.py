from pathlib import Path

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import ExperimentLifecycleState
from fedsira.experiments.collapse import (
    CollapseDecision,
    collapse_decision_from_comparison_families,
    materialize_resolved_core,
)
from fedsira.experiments.execution import (
    CellExecutionOutcome,
    ExecutionRecordStore,
    ExperimentExecutionResult,
    comparison_results_for_experiment,
    run_experiment,
)
from fedsira.experiments.planning import ScientificCell
from fedsira.experiments.protocol_executor import ProtocolCellExecutor
from fedsira.experiments.registry import COLLAPSE_EXPERIMENT_NAMES


def render_result(result: ExperimentExecutionResult) -> str:
    lines: list[str] = []
    lines.append(f"FedSIRA run: {result.experiment}")
    lines.append(f"experiment state: {result.lifecycle_state.value}")
    lines.append(f"cells: {result.cell_completion_count}/{len(result.outcomes)} completed")
    for outcome in result.outcomes:
        lines.append(
            f"  {outcome.cell.method:<45} {outcome.cell.condition:<40} "
            f"seed={outcome.cell.master_seed:>5} -> {outcome.terminal_state}"
        )
    if result.comparison_results:
        lines.append("")
        lines.append("comparisons:")
        for family in result.comparison_results:
            lines.append(f"  family: {family.family.value}")
            for comparison in family.comparisons:
                result_text = comparison.comparison_state
                p_value = (
                    f"p={comparison.adjusted_p_value:.4f}"
                    if comparison.adjusted_p_value is not None
                    else "p=NA"
                )
                lines.append(
                    f"    {comparison.definition.canonical_name:<110} "
                    f"{result_text:<22} {p_value}"
                )
    return "\n".join(lines)


def _materialize_core_if_complete(experiment: str) -> None:
    if experiment not in COLLAPSE_EXPERIMENT_NAMES:
        return
    store = ExecutionRecordStore(Path("outputs"))
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    decisions: list[CollapseDecision] = []
    alpha = config.metrics_and_statistics.multiplicity.family_wise_alpha
    collapse_family_names = (
        "proposal-screen necessity",
        "plurality necessity",
        "source-exclusion central claim",
        "external reproduction verification necessity",
    )
    for collapse_experiment in COLLAPSE_EXPERIMENT_NAMES:
        records = store.read_all_outcomes(collapse_experiment)
        if not records:
            return
        outcomes = tuple(
            CellExecutionOutcome(
                cell=ScientificCell(
                    experiment=record.experiment,
                    method=record.method,
                    condition=record.condition,
                    master_seed=record.master_seed,
                ),
                terminal_state=record.terminal_state,
                failure=None,
                metrics=record.metrics,
            )
            for record in records
        )
        comparison_results = comparison_results_for_experiment(
            collapse_experiment, outcomes, config
        )
        family_names = {family.family.value for family in comparison_results}
        matched_family = next(
            (family for family in family_names if family in collapse_family_names),
            None,
        )
        if matched_family is None:
            return
        decisions.append(
            collapse_decision_from_comparison_families(matched_family, comparison_results, alpha)
        )
    if len(decisions) == len(COLLAPSE_EXPERIMENT_NAMES):
        core = materialize_resolved_core(tuple(decisions))
        print(f"Resolved FedSIRA Core materialized: {core.identity_token}")


def execute(name: str, overwrite: bool) -> None:
    result = run_experiment(
        name,
        ProtocolCellExecutor(),
        overwrite=overwrite,
        resolved_core_complete=False,
    )
    print(render_result(result))
    if (
        result.lifecycle_state is ExperimentLifecycleState.COMPLETED
        and not overwrite
        and result.execution_digest
    ):
        print(f"already-completed: execution digest {result.execution_digest}")
    if result.lifecycle_state is ExperimentLifecycleState.COMPLETED:
        _materialize_core_if_complete(name)
    if result.lifecycle_state in (
        ExperimentLifecycleState.FAILED,
        ExperimentLifecycleState.INVALID,
        ExperimentLifecycleState.BLOCKED,
    ):
        raise SystemExit(1)
