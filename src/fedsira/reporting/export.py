from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from fedsira.analysis.claims import (
    CLAIM_DEFINITIONS,
    ClaimEvidence,
    ClaimStateResult,
    derive_claim_states,
)
from fedsira.analysis.comparisons import ComparisonFamilyResult
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import ClaimState, ExperimentLifecycleState
from fedsira.domain.records import (
    BooleanValue,
    ClaimId,
    ExperimentName,
    FrozenDomainModel,
    MethodName,
    MetricName,
    MetricValue,
    RepositoryPath,
    SchemaVersion,
    ScientificCellCount,
    TableName,
)
from fedsira.experiments.collapse import CollapseDecision, ResolvedCore
from fedsira.experiments.execution import ExperimentExecutionResult
from fedsira.experiments.planning import ExperimentPlan
from fedsira.reporting import figures as figure_renderers
from fedsira.reporting import tables as table_renderers
from fedsira.reporting.figures import validate_mandatory_figures_covered
from fedsira.reporting.tables import MANUSCRIPT_TABLE_NAMES, RenderedTable
from fedsira.reporting.verification import CompletenessVerificationResult

EXPORT_SCHEMA_VERSION: SchemaVersion = "fedsira|report_export|1"


class ExperimentStateExport(FrozenDomainModel):
    experiment: ExperimentName
    state: ExperimentLifecycleState


class ExperimentReportSummary(FrozenDomainModel):
    schema_version: SchemaVersion
    experiment: ExperimentName
    lifecycle_state: ExperimentLifecycleState
    completed_cell_count: ScientificCellCount
    planned_cell_count: ScientificCellCount


class ProjectReproducibilitySummary(FrozenDomainModel):
    schema_version: SchemaVersion
    experiment_states: tuple[ExperimentStateExport, ...]
    verification_passed: BooleanValue
    verification_failures: tuple[str, ...]
    mandatory_tables: tuple[TableName, ...]
    materialized_tables: tuple[TableName, ...]
    pending_mandatory_tables: tuple[TableName, ...]
    pending_mandatory_figures: tuple[str, ...]


class ReportExportResult(FrozenDomainModel):
    experiment: ExperimentName | None
    exported_paths: tuple[RepositoryPath, ...]
    verification: CompletenessVerificationResult


def claim_definition_count() -> ScientificCellCount:
    return len(CLAIM_DEFINITIONS)


def _results_root() -> Path:
    return Path("results")


def _write_table(root: Path, table: RenderedTable) -> Path:
    destination = root / f"{table.name}.csv"
    destination.write_text(table.csv_text + "\n")
    return destination


def derive_claim_states_for_export(
    claim_evidence: Mapping[ClaimId, ClaimEvidence] | None = None,
    config_path: Path = PRODUCTION_CONFIG_PATH,
) -> tuple[ClaimStateResult, ...]:
    config = load_scientific_config(config_path)
    return derive_claim_states(
        claim_evidence or {},
        config.metrics_and_statistics.materiality,
        config.claim_support_thresholds,
        config.metrics_and_statistics.technical_completion.minimum_complete_pairs_for_claim_support,
        config.metrics_and_statistics.multiplicity.family_wise_alpha,
    )


def export_experiment_report(
    result: ExperimentExecutionResult,
    config_path: Path,
    experiment_root: Path,
) -> ReportExportResult:
    if result.lifecycle_state is not ExperimentLifecycleState.COMPLETED:
        verification = CompletenessVerificationResult(
            passed=False,
            failures=(f"{result.experiment}: experiment is not complete",),
        )
        return ReportExportResult(
            experiment=result.experiment,
            exported_paths=(),
            verification=verification,
        )

    config = load_scientific_config(config_path)
    rounding = config.metrics_and_statistics.publication_rounding
    tables_root = experiment_root / "tables" / "main"
    metrics_root = experiment_root / "metrics" / "primary"
    tables_root.mkdir(parents=True, exist_ok=True)
    metrics_root.mkdir(parents=True, exist_ok=True)

    exported: list[Path] = []
    if result.comparison_results:
        statistical_table = table_renderers.render_statistical_summary_table(
            result.comparison_results,
            rounding,
        )
        exported.append(_write_table(tables_root, statistical_table))

    summary = ExperimentReportSummary(
        schema_version=EXPORT_SCHEMA_VERSION,
        experiment=result.experiment,
        lifecycle_state=result.lifecycle_state,
        completed_cell_count=result.cell_completion_count,
        planned_cell_count=len(result.outcomes),
    )
    summary_path = metrics_root / "summary.json"
    summary_path.write_text(summary.model_dump_json(indent=2) + "\n")
    exported.append(summary_path)
    verification = CompletenessVerificationResult(passed=True, failures=())
    return ReportExportResult(
        experiment=result.experiment,
        exported_paths=tuple(str(path) for path in exported),
        verification=verification,
    )


def export_project_summary(
    plan: ExperimentPlan,
    claim_states: Sequence[ClaimStateResult],
    lifecycle_states: Mapping[ExperimentName, ExperimentLifecycleState],
    config_path: Path,
    verification: CompletenessVerificationResult,
    collapse_decisions: Sequence[CollapseDecision] | None = None,
    resolved_core: ResolvedCore | None = None,
    comparison_results: Sequence[ComparisonFamilyResult] = (),
    evidence_trajectory: Mapping[int, Mapping[ClaimState, float]] | None = None,
    telemetry: Mapping[MethodName, Mapping[MetricName, MetricValue]] | None = None,
) -> ReportExportResult:
    if not verification.passed:
        return ReportExportResult(
            experiment=None,
            exported_paths=(),
            verification=verification,
        )

    config = load_scientific_config(config_path)
    rounding = config.metrics_and_statistics.publication_rounding
    project_root = _results_root() / "project_summary"
    tables_root = project_root / "tables" / "main"
    claims_root = project_root / "claims"
    reproducibility_root = project_root / "reproducibility" / "execution"
    figures_root = project_root / "figures" / "main"
    for directory in (tables_root, claims_root, reproducibility_root, figures_root):
        directory.mkdir(parents=True, exist_ok=True)

    exported: list[Path] = []
    materialized_tables: list[TableName] = []

    plan_table = table_renderers.render_experiment_plan_table(plan)
    exported.append(_write_table(tables_root, plan_table))
    materialized_tables.append(plan_table.name)

    if collapse_decisions is not None and resolved_core is not None:
        collapse_table = table_renderers.render_collapse_decisions_table(
            collapse_decisions,
            resolved_core,
            rounding,
        )
        exported.append(_write_table(tables_root, collapse_table))
        materialized_tables.append(collapse_table.name)

    if comparison_results:
        statistics_table = table_renderers.render_statistical_summary_table(
            comparison_results,
            rounding,
        )
        exported.append(_write_table(tables_root, statistics_table))
        materialized_tables.append(statistics_table.name)

    claim_table = table_renderers.render_claim_support_table(claim_states)
    exported.append(_write_table(claims_root, claim_table))
    materialized_tables.append(claim_table.name)

    schematic_path = figures_root / "FedSIRA Protocol Schematic.png"
    figure_renderers.render_protocol_schematic(schematic_path)
    exported.append(schematic_path)

    security_utility_path = figures_root / "Primary Security-Utility Tradeoff.png"
    figure_renderers.render_security_utility_tradeoff(comparison_results, security_utility_path)
    exported.append(security_utility_path)

    if evidence_trajectory is not None:
        evidence_trajectory_path = figures_root / "Evidence-Arrival State Trajectory.png"
        figure_renderers.render_evidence_arrival_trajectory(
            evidence_trajectory,
            evidence_trajectory_path,
        )
        exported.append(evidence_trajectory_path)

    if telemetry is not None:
        efficiency_path = figures_root / "Efficiency Profile.png"
        figure_renderers.render_efficiency_profile(
            telemetry,
            "elapsed-seconds-per-cell",
            efficiency_path,
        )
        exported.append(efficiency_path)

    pending_tables = tuple(
        name for name in MANUSCRIPT_TABLE_NAMES if name not in materialized_tables
    )
    pending_figures = validate_mandatory_figures_covered(tuple(exported))
    reproducibility_summary = ProjectReproducibilitySummary(
        schema_version=EXPORT_SCHEMA_VERSION,
        experiment_states=tuple(
            ExperimentStateExport(experiment=name, state=state)
            for name, state in sorted(lifecycle_states.items())
        ),
        verification_passed=verification.passed,
        verification_failures=verification.failures,
        mandatory_tables=MANUSCRIPT_TABLE_NAMES,
        materialized_tables=tuple(materialized_tables),
        pending_mandatory_tables=pending_tables,
        pending_mandatory_figures=pending_figures,
    )
    reproducibility_path = reproducibility_root / "execution_summary.json"
    reproducibility_path.write_text(reproducibility_summary.model_dump_json(indent=2) + "\n")
    exported.append(reproducibility_path)

    return ReportExportResult(
        experiment=None,
        exported_paths=tuple(str(path) for path in exported),
        verification=verification,
    )
