from __future__ import annotations

from pathlib import Path

from fedsira.domain.enums import ExperimentLifecycleState
from fedsira.domain.types import (
    ExperimentName,
    FigureName,
    FrozenDomainModel,
    ReportVerificationFailure,
    RepositoryPath,
    SchemaVersion,
    ScientificCellCount,
    TableName,
    VerificationPassed,
)
from fedsira.evaluation.comparisons import ComparisonFamilyResult
from fedsira.experiments.collapse import CollapseDecision, ResolvedCore
from fedsira.experiments.definitions import (
    ADMISSION_DELAY_DECOMPOSITION_NAME,
    BYZANTINE_BOUND_VIOLATION_NAME,
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
    MECHANISM_ABLATION_NAME,
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    SECONDARY_DATASET_GENERALIZATION_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    experiment_by_name,
)
from fedsira.experiments.execution import CellExecutionOutcome, ExperimentExecutionResult
from fedsira.experiments.planning import ExperimentPlan
from fedsira.reporting import tables as table_renderers
from fedsira.reporting.figures import (
    EfficiencyMetricObservation,
    EvidenceStateFraction,
    render_admission_delay_decomposition,
    render_capability_granularity_boundary,
    render_compromised_reproducer_boundary,
    render_compromised_verifier_boundary,
    render_heterogeneity_synthesis_boundary,
    render_mandatory_figures,
    render_protocol_schematic,
    render_secondary_generalization,
    render_security_utility_tradeoff,
    render_shared_epistemic_failure,
    render_useful_backdoored_source,
    validate_mandatory_figures_covered,
)
from fedsira.reporting.tables import (
    MANUSCRIPT_TABLE_NAMES,
    RenderedTable,
    render_experiment_cell_metrics_table,
    render_mandatory_tables,
)
from fedsira.reporting.verification import (
    CompletenessVerificationResult,
    ExperimentLifecycleRecord,
)

EXPORT_SCHEMA_VERSION: SchemaVersion = "fedsira|report_export|1"

_RESULT_TABLE_EVIDENCE: tuple[tuple[TableName, tuple[ExperimentName, ...]], ...] = (
    ("Primary Results", (PRIMARY_CONFIRMATORY_EVALUATION_NAME,)),
    ("Source-Exclusion Results", (SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,)),
    ("Ablation Results", (MECHANISM_ABLATION_NAME,)),
    (
        "Byzantine Robustness",
        (
            COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
            COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
            BYZANTINE_BOUND_VIOLATION_NAME,
        ),
    ),
    (
        "Failure Boundaries",
        (
            EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
            SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
            CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
            HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
        ),
    ),
    (
        "Delay and Efficiency",
        (
            ADMISSION_DELAY_DECOMPOSITION_NAME,
            EFFICIENCY_MEASUREMENT_NAME,
        ),
    ),
    ("Generalization Results", (SECONDARY_DATASET_GENERALIZATION_NAME,)),
)


class ExperimentReportSummary(FrozenDomainModel):
    schema_version: SchemaVersion
    experiment: ExperimentName
    lifecycle_state: ExperimentLifecycleState
    completed_cell_count: ScientificCellCount
    planned_cell_count: ScientificCellCount


class ExperimentArtifactManifest(FrozenDomainModel):
    schema_version: SchemaVersion
    experiment: ExperimentName
    lifecycle_state: ExperimentLifecycleState
    artifacts: tuple[RepositoryPath, ...]


class ProjectReproducibilitySummary(FrozenDomainModel):
    schema_version: SchemaVersion
    experiment_states: tuple[ExperimentLifecycleRecord, ...]
    verification_passed: VerificationPassed
    verification_failures: tuple[ReportVerificationFailure, ...]
    mandatory_tables: tuple[TableName, ...]
    materialized_tables: tuple[TableName, ...]
    pending_mandatory_tables: tuple[TableName, ...]
    pending_mandatory_figures: tuple[FigureName, ...]


class ReportExportResult(FrozenDomainModel):
    experiment: ExperimentName | None
    exported_paths: tuple[RepositoryPath, ...]
    verification: CompletenessVerificationResult


def _results_root() -> Path:
    return Path("results")


def _write_table(root: Path, table: RenderedTable) -> Path:
    destination = root / f"{table.name}.csv"
    destination.write_text(table.csv_text + "\n")
    return destination


def _verify_experiment_artifacts(
    result: ExperimentExecutionResult,
    tables_root: Path,
    figures_root: Path,
    summary_path: Path,
) -> CompletenessVerificationResult:
    specification = experiment_by_name(result.experiment).artifacts
    failures: list[ReportVerificationFailure] = []
    if specification.metrics_required and (
        not summary_path.is_file() or not summary_path.read_text(encoding="utf-8").strip()
    ):
        failures.append(f"{result.experiment}: metric summary is missing or empty")
    for table_name in specification.required_tables:
        path = tables_root / f"{table_name}.csv"
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            failures.append(f"{result.experiment}: required table {table_name} is missing or empty")
    for figure_name in specification.required_figures:
        path = figures_root / f"{figure_name}.png"
        if not path.is_file() or path.stat().st_size == 0:
            failures.append(
                f"{result.experiment}: required figure {figure_name} is missing or empty"
            )
    return CompletenessVerificationResult(passed=not failures, failures=tuple(failures))


def _render_specialized_figure(
    result: ExperimentExecutionResult,
    figures_root: Path,
) -> Path | None:
    figure: Path | None = None
    if result.experiment is COMPROMISED_REPRODUCER_ROBUSTNESS_NAME:
        figure = render_compromised_reproducer_boundary(
            result.comparison_results,
            figures_root / "Compromised-Reproducer Boundary.png",
            result.outcomes,
        )
    elif result.experiment is COMPROMISED_VERIFIER_ROBUSTNESS_NAME:
        figure = render_compromised_verifier_boundary(
            result.comparison_results,
            figures_root / "Compromised-Verifier Boundary.png",
            result.outcomes,
        )
    elif result.experiment is SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME:
        figure = render_shared_epistemic_failure(
            result.comparison_results,
            figures_root / "Shared Epistemic Failure.png",
            result.outcomes,
        )
    elif result.experiment is CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME:
        figure = render_capability_granularity_boundary(
            result.comparison_results,
            figures_root / "Capability-Granularity Boundary.png",
            result.outcomes,
        )
    elif result.experiment is HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME:
        figure = render_heterogeneity_synthesis_boundary(
            result.comparison_results,
            figures_root / "Heterogeneity Synthesis Boundary.png",
            result.outcomes,
        )
    elif result.experiment is ADMISSION_DELAY_DECOMPOSITION_NAME:
        figure = render_admission_delay_decomposition(
            result.comparison_results,
            figures_root / "Admission-Delay Decomposition.png",
            result.outcomes,
        )
    elif result.experiment is SECONDARY_DATASET_GENERALIZATION_NAME:
        figure = render_secondary_generalization(
            result.comparison_results,
            figures_root / "Secondary Generalization.png",
        )
    return figure


def _render_experiment_figures(
    result: ExperimentExecutionResult,
    figures_root: Path,
) -> tuple[Path, ...]:
    figures: list[Path] = [
        render_protocol_schematic(figures_root / "FedSIRA Protocol Schematic.png")
    ]
    if not result.comparison_results:
        return tuple(figures)
    if result.experiment is PRIMARY_CONFIRMATORY_EVALUATION_NAME:
        figures.append(
            render_security_utility_tradeoff(
                result.comparison_results,
                figures_root / "Primary Security-Utility Tradeoff.png",
            )
        )
    elif result.experiment is SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME:
        figures.append(
            render_useful_backdoored_source(
                result.comparison_results,
                figures_root / "Useful Backdoored Source.png",
                result.outcomes,
            )
        )
    else:
        specialized = _render_specialized_figure(result, figures_root)
        if specialized is not None:
            figures.append(specialized)
    return tuple(figures)


def export_experiment_report(
    result: ExperimentExecutionResult,
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

    tables_root = experiment_root / "tables" / "main"
    figures_root = experiment_root / "figures" / "main"
    metrics_root = experiment_root / "metrics" / "primary"
    tables_root.mkdir(parents=True, exist_ok=True)
    figures_root.mkdir(parents=True, exist_ok=True)
    metrics_root.mkdir(parents=True, exist_ok=True)

    exported: list[Path] = [
        _write_table(tables_root, render_experiment_cell_metrics_table(result.outcomes)),
        *_render_experiment_figures(result, figures_root),
    ]
    if result.comparison_results:
        statistical_table = table_renderers.render_statistical_summary_table(
            result.comparison_results,
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
    manifest_path = experiment_root / "manifest.json"
    manifest = ExperimentArtifactManifest(
        schema_version=EXPORT_SCHEMA_VERSION,
        experiment=result.experiment,
        lifecycle_state=result.lifecycle_state,
        artifacts=tuple(str(path) for path in exported),
    )
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n")
    exported.append(manifest_path)
    verification = _verify_experiment_artifacts(result, tables_root, figures_root, summary_path)
    return ReportExportResult(
        experiment=result.experiment,
        exported_paths=tuple(str(path) for path in exported),
        verification=verification,
    )


def _report_material_failures(
    pending_tables: tuple[TableName, ...],
    pending_figures: tuple[FigureName, ...],
) -> tuple[ReportVerificationFailure, ...]:
    failures: list[ReportVerificationFailure] = []
    if pending_tables:
        failures.append(f"mandatory tables not materialized: {', '.join(pending_tables)}")
    if pending_figures:
        failures.append(f"mandatory figures not materialized: {', '.join(pending_figures)}")
    return tuple(failures)


def _missing_result_evidence(
    comparison_results: tuple[ComparisonFamilyResult, ...],
) -> tuple[ReportVerificationFailure, ...]:
    evidenced_experiments = frozenset(
        comparison.definition.experiment
        for family in comparison_results
        for comparison in family.comparisons
    )
    failures: list[ReportVerificationFailure] = []
    for table_name, expected_experiments in _RESULT_TABLE_EVIDENCE:
        missing = tuple(
            experiment
            for experiment in expected_experiments
            if experiment not in evidenced_experiments
        )
        if missing:
            failures.append(f"{table_name}: missing comparison evidence for {', '.join(missing)}")
    if not comparison_results:
        failures.append("Statistical Summary: no comparison evidence")
    return tuple(failures)


def export_project_summary(
    plan: ExperimentPlan,
    lifecycle_states: tuple[ExperimentLifecycleRecord, ...],
    verification: CompletenessVerificationResult,
    collapse_decisions: tuple[CollapseDecision, ...] | None = None,
    resolved_core: ResolvedCore | None = None,
    comparison_results: tuple[ComparisonFamilyResult, ...] = (),
    outcomes: tuple[CellExecutionOutcome, ...] = (),
    evidence_trajectory: tuple[EvidenceStateFraction, ...] | None = None,
    telemetry: tuple[EfficiencyMetricObservation, ...] | None = None,
) -> ReportExportResult:
    if not verification.passed:
        return ReportExportResult(
            experiment=None,
            exported_paths=(),
            verification=verification,
        )

    evidence_failures = _missing_result_evidence(comparison_results)
    if evidence_failures:
        return ReportExportResult(
            experiment=None,
            exported_paths=(),
            verification=CompletenessVerificationResult(
                passed=False,
                failures=evidence_failures,
            ),
        )

    project_root = _results_root() / "project_summary"
    tables_root = project_root / "tables" / "main"
    reproducibility_root = project_root / "reproducibility" / "execution"
    figures_root = project_root / "figures" / "main"
    for directory in (tables_root, reproducibility_root, figures_root):
        directory.mkdir(parents=True, exist_ok=True)

    exported: list[Path] = []
    materialized_tables: list[TableName] = []

    for table in render_mandatory_tables(
        plan,
        collapse_decisions=collapse_decisions,
        resolved_core=resolved_core,
        comparison_results=comparison_results,
        outcomes=outcomes,
    ):
        exported.append(_write_table(tables_root, table))
        materialized_tables.append(table.name)

    exported.extend(
        render_mandatory_figures(
            comparison_results,
            figures_root,
            evidence_trajectory=evidence_trajectory,
            telemetry=telemetry,
            outcomes=outcomes,
        )
    )

    pending_tables = tuple(
        name for name in MANUSCRIPT_TABLE_NAMES if name not in materialized_tables
    )
    pending_figures = validate_mandatory_figures_covered(tuple(exported))
    material_failures = _report_material_failures(pending_tables, pending_figures)
    final_verification = CompletenessVerificationResult(
        passed=not material_failures,
        failures=material_failures,
    )
    reproducibility_summary = ProjectReproducibilitySummary(
        schema_version=EXPORT_SCHEMA_VERSION,
        experiment_states=lifecycle_states,
        verification_passed=final_verification.passed,
        verification_failures=final_verification.failures,
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
        verification=final_verification,
    )
