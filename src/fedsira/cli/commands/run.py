from pathlib import Path

from fedsira.artifacts.paths import workspace_root_for_family
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import ArtifactFamily, ExperimentLifecycleState
from fedsira.domain.records import ExperimentName, OverwriteExisting
from fedsira.experiments.collapse import (
    CollapseDecision,
    collapse_decision_from_comparison_families,
    materialize_resolved_core,
    publish_resolved_core,
    read_resolved_core,
)
from fedsira.experiments.execution import (
    CellExecutionOutcome,
    ExecutionRecordStore,
    ExperimentExecutionResult,
    collapse_evaluation_from_store,
    comparison_results_for_experiment,
    run_experiment,
)
from fedsira.experiments.planning import ScientificCell
from fedsira.experiments.protocol_executor import ProtocolCellExecutor
from fedsira.experiments.registry import (
    COLLAPSE_EXPERIMENT_NAMES,
    ClaimFamily,
    experiment_by_name,
)

RESOLVED_CORE_PUBLISHED_DIRECTORY = workspace_root_for_family(
    ArtifactFamily.FIXED_PROTOCOL_CONFIGURATION
)


def render_result(result: ExperimentExecutionResult) -> str:
    lines: list[str] = [
        f"FedSIRA run: {result.experiment}",
        f"experiment state: {result.lifecycle_state.value}",
        f"cells: {result.cell_completion_count}/{len(result.outcomes)} completed",
    ]
    for outcome in result.outcomes:
        lines.append(
            f"  {outcome.cell.method:<45} {outcome.cell.condition:<40} "
            f"seed={outcome.cell.master_seed:>5} -> {outcome.terminal_state.value}"
        )
    if result.comparison_results:
        lines.extend(("", "comparisons:"))
        for family in result.comparison_results:
            lines.append(f"  family: {family.family.value}")
            for comparison in family.comparisons:
                p_value = (
                    f"p={comparison.adjusted_p_value:.4f}"
                    if comparison.adjusted_p_value is not None
                    else "p=NA"
                )
                lines.append(
                    f"    {comparison.definition.comparison_name:<110} "
                    f"{comparison.comparison_state.value:<22} {p_value}"
                )
    return "\n".join(lines)


def _materialize_core_if_complete(experiment: ExperimentName) -> None:
    if experiment not in COLLAPSE_EXPERIMENT_NAMES:
        return
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    store = ExecutionRecordStore(
        Path(config.runtime.repository_layout.execution_workspace)
    )
    evaluation = collapse_evaluation_from_store(store, config)
    decisions: list[CollapseDecision] = []
    collapse_families = frozenset(
        {
            ClaimFamily.PROPOSAL_SCREEN_NECESSITY,
            ClaimFamily.PLURALITY_NECESSITY,
            ClaimFamily.SOURCE_EXCLUSION_CENTRAL_CLAIM,
            ClaimFamily.EXTERNAL_VERIFICATION_NECESSITY,
        }
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
        definition = experiment_by_name(collapse_experiment)
        comparison_results = comparison_results_for_experiment(
            collapse_experiment,
            definition.dataset,
            outcomes,
            config,
            store,
        )
        matched_family = next(
            (
                result.family
                for result in comparison_results
                if result.family in collapse_families
            ),
            None,
        )
        if matched_family is None:
            return
        decisions.append(
            collapse_decision_from_comparison_families(
                matched_family,
                comparison_results,
                evaluation=evaluation,
                materiality_config=config.metrics_and_statistics.materiality,
            )
        )
    if len(decisions) != len(COLLAPSE_EXPERIMENT_NAMES):
        return
    core = materialize_resolved_core(tuple(decisions))
    publish_resolved_core(RESOLVED_CORE_PUBLISHED_DIRECTORY, core)
    print(f"Resolved FedSIRA Core materialized: {core.decision_identity}")


def execute(name: ExperimentName, overwrite: OverwriteExisting) -> None:
    resolved_core = read_resolved_core(RESOLVED_CORE_PUBLISHED_DIRECTORY)
    result = run_experiment(
        name,
        ProtocolCellExecutor(resolved_core=resolved_core),
        overwrite=overwrite,
        resolved_core_complete=resolved_core is not None,
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
