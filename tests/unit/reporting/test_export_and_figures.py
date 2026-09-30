import csv
from collections.abc import Iterator
from math import isclose
from pathlib import Path
from typing import Any, cast

import pandas
import pytest
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from fedsira.artifacts.paths import (
    artifact_slot_directory,
    artifact_staging_root,
    current_repository_root,
    experiment_metric_evidence_root,
    experiment_telemetry_evidence_root,
)
from fedsira.artifacts.store import (
    ArtifactManifest,
    ArtifactSlot,
    publish_artifact,
    read_current_artifact,
)
from fedsira.config import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import (
    AdmissionOpeningMode,
    AdmissionState,
    ArtifactDependencyKind,
    ArtifactFamily,
    ArtifactProducer,
    BaselineIdentity,
    CapabilityContractScope,
    ComparisonMetric,
    CoreMethodIdentity,
    DatasetId,
    DelayPhaseMetric,
    DescriptiveScientificMetric,
    EfficiencyCondition,
    EvidenceArrivalSchedule,
    ExperimentLifecycleState,
    ExperimentName,
    FigureName,
    MetricObservationKey,
    OpeningMode,
    PrimaryScenario,
    ReportCellLiteral,
    ReportColumnName,
    ReproducerCondition,
    RootCauseMixture,
    SecondaryScenario,
    SourceExclusionMethod,
    VerifierCondition,
)
from fedsira.domain.models import (
    ScientificCell,
)
from fedsira.domain.types import (
    ArtifactDigest,
    MasterSeed,
    MethodName,
    MetricName,
    MetricValue,
    RelativePathText,
    ScenarioName,
    ScientificCellCount,
)
from fedsira.evaluation.comparison_evidence import (
    COMPARISON_EVIDENCE_PROCEDURE_IDENTITY,
    COMPARISON_EVIDENCE_SCHEMA_VERSION,
    PersistedComparisonEvidence,
    comparison_evidence_slot,
)
from fedsira.evaluation.comparisons import (
    ComparisonDefinition,
    ComparisonFamilyResult,
    ComparisonReferenceKind,
    ComparisonResult,
    ComparisonState,
    build_comparison_registry,
)
from fedsira.experiments.collapse import (
    CollapseDecision,
    CollapseDecisionKind,
    ProductionUpdateRule,
    ReproductionRowRequirement,
    ResolvedCore,
    RowVerificationMode,
)
from fedsira.experiments.definitions import (
    ADMISSION_DELAY_DECOMPOSITION_NAME,
    BYZANTINE_BOUND_VIOLATION_NAME,
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    COLLAPSE_EXPERIMENT_NAMES,
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_FALSE_NEGATIVE_BOUNDARY_FIGURE_NAME,
    COMPROMISED_VERIFIER_FALSE_POSITIVE_BOUNDARY_FIGURE_NAME,
    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    SECONDARY_DATASET_GENERALIZATION_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    STATE_TRAJECTORY_FRACTIONS_PARQUET_NAME,
    experiment_by_name,
)
from fedsira.experiments.engine import (
    AdmissionStateObservation,
    CellExecutionOutcome,
    ExecutionProvenance,
    ExperimentExecutionResult,
)
from fedsira.experiments.planning import (
    build_plan,
)
from fedsira.reporting.aggregate import AggregateMetricEvidenceRow
from fedsira.reporting.export import (
    CELL_METRICS_PARQUET_NAME,
    ExperimentReportSummary,
    ReportExportResult,
    export_experiment_report,
    export_project_summary,
    materialize_experiment_evidence,
    project_efficiency_telemetry,
    project_evidence_trajectory,
    verify_experiment_artifacts,
    verify_persisted_experiment_report,
)
from fedsira.reporting.figures import (
    MANDATORY_FIGURE_NAMES,
    REPRODUCER_STRATEGY_CONDITIONS,
    EfficiencyMetricObservation,
    EvidenceStateFraction,
    render_admission_delay_decomposition,
    render_capability_granularity_boundary,
    render_collapse_decision_effects,
    render_compromised_reproducer_boundary,
    render_efficiency_profile,
    render_evidence_arrival_trajectory,
    render_experiment_figures,
    render_protocol_schematic,
    render_secondary_generalization,
    render_security_utility_tradeoff,
    render_useful_backdoored_source,
    validate_mandatory_figures_covered,
)
from fedsira.reporting.protocol_tables import render_experiment_plan_table
from fedsira.reporting.publication import (
    publish_claim_state_artifact,
    publish_metric_evidence,
    read_claim_state_artifact,
    read_table_figure_export,
    table_figure_source_data_slot,
)
from fedsira.reporting.tables import (
    AggregateDisplayStatistic,
    format_byte_value,
    format_metric_value,
    format_p_value,
    render_byzantine_robustness_table,
    render_delay_and_efficiency_table,
    render_experiment_cell_metrics_table,
    render_failure_boundaries_table,
    render_generalization_results_table,
    render_primary_results_table,
    render_source_exclusion_results_table,
    render_statistical_summary_table,
)
from fedsira.reporting.verification import (
    CompletenessVerificationResult,
    ExperimentLifecycleRecord,
)
from fedsira.runtime import (
    ApplicationContext,
    bound_application_context,
    current_application_context,
)

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)


@pytest.fixture
def isolated_repository(tmp_path: Path) -> Iterator[Path]:
    context: ApplicationContext = current_application_context().model_copy(
        update={"repository_root": tmp_path}
    )
    with bound_application_context(context):
        yield tmp_path


def _with_primary_comparison_evidence(
    result: ExperimentExecutionResult,
) -> ExperimentExecutionResult:
    required_metrics = frozenset(
        (
            ComparisonMetric.TARGET_F1,
            ComparisonMetric.ATTACK_SUCCESS_RATE,
            ComparisonMetric.MALICIOUS_ADMISSION,
        )
    )
    definitions = tuple(
        definition
        for definition in build_comparison_registry()
        if (
            definition.experiment == PRIMARY_CONFIRMATORY_EVALUATION_NAME
            and definition.metric in required_metrics
        )
    )
    comparisons = tuple(
        ComparisonResult(
            definition=definition,
            paired_differences=(0.1, 0.1, 0.1),
            complete_seed_count=3,
            mean_paired_difference=0.1,
            median_paired_difference=0.1,
            paired_standardized_effect=1.0,
            raw_p_value=0.01,
            adjusted_p_value=0.01,
            confidence_interval=(0.05, 0.15),
            materiality_passes=True,
            comparison_state=ComparisonState.PASSED,
        )
        for definition in definitions
    )
    families = (ComparisonFamilyResult(family=definitions[0].family, comparisons=comparisons),)
    comparison_slot = comparison_evidence_slot(result.experiment)
    comparison_manifest, _reused = publish_artifact(
        slot=comparison_slot,
        producer=ArtifactProducer.EVALUATION_PRODUCER,
        payload=PersistedComparisonEvidence(
            schema_version=COMPARISON_EVIDENCE_SCHEMA_VERSION,
            experiment=result.experiment,
            metric_evidence_digest=result.execution_digest,
            families=families,
        )
        .model_dump_json()
        .encode("utf-8"),
        dependencies=(),
        procedure_identity=COMPARISON_EVIDENCE_PROCEDURE_IDENTITY,
        slot_directory=current_repository_root() / artifact_slot_directory(comparison_slot),
        staging_root=current_repository_root() / artifact_staging_root(),
    )
    return result.model_copy(
        update={
            "comparison_results": families,
            "comparison_artifact_id": comparison_manifest.identity,
            "provenance": result.provenance or _record_provenance(),
        }
    )


def _materialize_run_evidence(result: ExperimentExecutionResult) -> None:
    materialized = materialize_experiment_evidence(
        result,
        experiment_metric_evidence_root(result.experiment),
        experiment_telemetry_evidence_root(result.experiment),
    )
    publish_metric_evidence(result.experiment, result.execution_digest, materialized.paths)


def _published_source_data_identity(result: ExperimentExecutionResult) -> ArtifactDigest:
    slot = table_figure_source_data_slot(result.experiment)
    current = read_current_artifact(
        current_application_context().repository_root / artifact_slot_directory(slot)
    )
    assert current is not None
    manifest, _payload = current
    return manifest.identity


def _published_exported_paths(result: ExperimentExecutionResult) -> tuple[RelativePathText, ...]:
    payload = read_table_figure_export(result.experiment)
    assert payload is not None
    return payload.exported_paths


def test_format_metric_value_na_and_rounding() -> None:
    rounding = CONFIG.metrics_and_statistics.publication_rounding
    assert format_metric_value(None) == "NA"
    assert format_metric_value(0.5) == f"{0.5:.{rounding.f1_accuracy_rates_decimals}f}"


def test_format_p_value_floor_and_rounding() -> None:
    rounding = CONFIG.metrics_and_statistics.publication_rounding
    assert format_p_value(None) == "NA"
    assert format_p_value(rounding.p_value_display_floor / 2).startswith("<")
    value = rounding.p_value_display_floor + 0.01
    assert format_p_value(value) == f"{value:.{rounding.p_value_significant_digits}g}"


def test_capability_granularity_boundary_uses_persisted_aggregate_evidence(
    tmp_path: Path,
    isolated_repository: Path,
) -> None:
    outcome = CellExecutionOutcome(
        cell=ScientificCell(
            experiment=CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
            method=CapabilityContractScope.BROAD_TARGET_ONLY,
            condition=RootCauseMixture.BALANCED_50_50,
            master_seed=1103,
        ),
        terminal_state=ExperimentLifecycleState.COMPLETED,
        failure=None,
        metrics=(
            (ComparisonMetric.FALSE_SAME_CAPABILITY_CERTIFICATION_RATE, 0.25),
            (MetricObservationKey.ROOT_CAUSE_A_TARGET_F1, 0.7),
            (MetricObservationKey.ROOT_CAUSE_B_TARGET_F1, 0.6),
        ),
    )
    result = ExperimentExecutionResult(
        experiment=CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
        lifecycle_state=ExperimentLifecycleState.COMPLETED,
        outcomes=(outcome,),
        provenance=_record_provenance(),
    )
    _materialize_run_evidence(result)
    destination = tmp_path / "Capability-Granularity Boundary.png"
    assert render_capability_granularity_boundary((), destination, (outcome,)) == destination
    assert destination.is_file()


def test_compromised_reproducer_boundary_separates_registered_attack_strategies(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import fedsira.reporting.figures as figures_module

    method = CoreMethodIdentity.RESOLVED_FEDSIRA_CORE
    outcome = CellExecutionOutcome(
        cell=ScientificCell(
            experiment=COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
            method=method,
            condition=ReproducerCondition.CLEAN,
            master_seed=1103,
        ),
        terminal_state=ExperimentLifecycleState.COMPLETED,
        failure=None,
        metrics=(),
    )

    def missing_aggregate(
        _outcomes: tuple[CellExecutionOutcome, ...],
        _experiment: ExperimentName,
        _method: MethodName,
        _condition: ScenarioName,
        _metric: MetricName,
    ) -> MetricValue | None:
        return None

    monkeypatch.setattr(figures_module, "_aggregate_metric_mean", missing_aggregate)
    legend_labels: list[tuple[str, ...]] = []

    def capture_figure(self: Figure, destination: Path, *, dpi: int) -> None:
        del dpi
        legend_labels.extend(tuple(axis.get_legend_handles_labels()[1]) for axis in self.axes)
        Path(destination).write_bytes(b"figure fixture")

    monkeypatch.setattr(Figure, "savefig", capture_figure)
    destination = tmp_path / "reproducer-boundary.png"

    assert render_compromised_reproducer_boundary((), destination, (outcome,)) == destination

    expected_labels = {
        f"{strategy}\n{registered_method}"
        for strategy, _one_condition, _two_condition in REPRODUCER_STRATEGY_CONDITIONS
        for registered_method in experiment_by_name(COMPROMISED_REPRODUCER_ROBUSTNESS_NAME).methods
    }
    assert len(legend_labels) == 2
    assert all(set(labels) == expected_labels for labels in legend_labels)


def test_compromised_verifier_boundary_publishes_separate_modes_with_exact_risk_annotation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import fedsira.reporting.figures as figures_module

    definition = experiment_by_name(COMPROMISED_VERIFIER_ROBUSTNESS_NAME)
    method = definition.methods[0]
    outcome = CellExecutionOutcome(
        cell=ScientificCell(
            experiment=COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
            method=method,
            condition=VerifierCondition.ALL_HONEST,
            master_seed=1103,
        ),
        terminal_state=ExperimentLifecycleState.COMPLETED,
        failure=None,
        metrics=(),
    )

    def missing_aggregate(
        _outcomes: tuple[CellExecutionOutcome, ...],
        _experiment: ExperimentName,
        _method: MethodName,
        _condition: ScenarioName,
        _metric: MetricName,
    ) -> MetricValue | None:
        return None

    monkeypatch.setattr(figures_module, "_aggregate_metric_mean", missing_aggregate)
    rendered: list[tuple[str, tuple[str, ...]]] = []

    def capture_figure(self: Figure, destination: Path, *, dpi: int) -> None:
        del dpi
        axis = self.axes[0]
        rendered.append((axis.get_title(), tuple(text.get_text() for text in axis.texts)))
        Path(destination).write_bytes(b"figure fixture")

    monkeypatch.setattr(Figure, "savefig", capture_figure)
    false_positive_path = (
        tmp_path / f"{COMPROMISED_VERIFIER_FALSE_POSITIVE_BOUNDARY_FIGURE_NAME}.png"
    )
    false_negative_path = (
        tmp_path / f"{COMPROMISED_VERIFIER_FALSE_NEGATIVE_BOUNDARY_FIGURE_NAME}.png"
    )

    result = ExperimentExecutionResult(
        experiment=COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
        lifecycle_state=ExperimentLifecycleState.COMPLETED,
        outcomes=(outcome,),
        provenance=_record_provenance(),
    )
    paths = render_experiment_figures(result, tmp_path, (), ())

    assert paths == (
        tmp_path / f"{FigureName.PROTOCOL_SCHEMATIC}.png",
        false_positive_path,
        false_negative_path,
    )
    assert tuple(title for title, _annotations in rendered[1:]) == (
        FigureName.COMPROMISED_VERIFIER_FALSE_POSITIVE_BOUNDARY,
        FigureName.COMPROMISED_VERIFIER_FALSE_NEGATIVE_BOUNDARY,
    )
    assert all(
        any(annotation.startswith("Random-profile exact P(K ≥ 2) = ") for annotation in annotations)
        for _title, annotations in rendered[1:]
    )
    assert definition.artifacts.required_figures == (
        FigureName.PROTOCOL_SCHEMATIC,
        COMPROMISED_VERIFIER_FALSE_POSITIVE_BOUNDARY_FIGURE_NAME,
        COMPROMISED_VERIFIER_FALSE_NEGATIVE_BOUNDARY_FIGURE_NAME,
    )


def test_render_experiment_plan_table_is_csv() -> None:
    plan = build_plan()
    table = render_experiment_plan_table(plan)
    lines = table.csv_text.splitlines()
    assert table.name == "Experiment Plan"
    assert lines[0] == (
        "experiment,class,methods,scenarios_or_variants,seeds,nominal_run_count,"
        "primary_metrics,claim_family,prerequisite,downstream_role"
    )
    assert len(lines) - 1 == len(plan.experiments)


def test_export_experiment_report_blocks_primary_figure_without_comparison_evidence(
    isolated_repository: Path,
) -> None:
    result = ExperimentExecutionResult(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        lifecycle_state=ExperimentLifecycleState.COMPLETED,
        provenance=_record_provenance(),
        outcomes=(
            CellExecutionOutcome(
                cell=ScientificCell(
                    experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                    method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
                    condition="Legitimate Unsupported Capability",
                    master_seed=1103,
                ),
                terminal_state=ExperimentLifecycleState.COMPLETED,
                failure=None,
                metrics=(("target-f1", 0.8),),
            ),
        ),
    )
    _materialize_run_evidence(result)
    with pytest.raises(ValueError, match="missing comparison evidence"):
        export_experiment_report(result, isolated_repository / "results")


def test_export_experiment_report_blocks_efficiency_figure_without_repeated_telemetry(
    isolated_repository: Path,
) -> None:
    result = ExperimentExecutionResult(
        experiment=EFFICIENCY_MEASUREMENT_NAME,
        lifecycle_state=ExperimentLifecycleState.COMPLETED,
        provenance=_record_provenance(),
        outcomes=(
            CellExecutionOutcome(
                cell=ScientificCell(
                    experiment=EFFICIENCY_MEASUREMENT_NAME,
                    method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
                    condition="timed",
                    master_seed=1103,
                ),
                terminal_state=ExperimentLifecycleState.COMPLETED,
                failure=None,
                metrics=(
                    ("post-evidence-wall-clock-seconds", 1.5),
                    ("peak-host-rss-bytes", 32.0),
                ),
            ),
        ),
    )
    _materialize_run_evidence(result)
    with pytest.raises(ValueError, match="missing timing and resource telemetry"):
        export_experiment_report(result, isolated_repository / "results")


def test_experiment_evidence_verification_rejects_missing_metric_artifact(
    isolated_repository: Path,
) -> None:
    result = ExperimentExecutionResult(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        lifecycle_state=ExperimentLifecycleState.COMPLETED,
        outcomes=(
            CellExecutionOutcome(
                cell=ScientificCell(
                    experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                    method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
                    condition="Legitimate Unsupported Capability",
                    master_seed=1103,
                ),
                terminal_state=ExperimentLifecycleState.COMPLETED,
                failure=None,
                metrics=(("target-f1", 0.8),),
            ),
        ),
    )
    result = _with_primary_comparison_evidence(result)
    _materialize_run_evidence(result)
    experiment_root = isolated_repository / "results"
    export_experiment_report(result, experiment_root)
    metrics_root = experiment_metric_evidence_root(result.experiment)
    (metrics_root / CELL_METRICS_PARQUET_NAME).unlink()
    verification = verify_experiment_artifacts(
        result,
        experiment_root / "tables" / "main",
        experiment_root / "figures" / "main",
        metrics_root,
        experiment_root / "metrics" / "primary" / "summary.json",
        _published_source_data_identity(result),
        experiment_root,
        _published_exported_paths(result),
    )
    assert not verification.passed
    assert any(CELL_METRICS_PARQUET_NAME in failure for failure in verification.failures)


def test_persisted_experiment_report_verifies_published_products_without_rebuilding(
    isolated_repository: Path,
) -> None:
    result = _with_primary_comparison_evidence(
        ExperimentExecutionResult(
            experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
            lifecycle_state=ExperimentLifecycleState.COMPLETED,
            provenance=_record_provenance(),
            outcomes=(
                CellExecutionOutcome(
                    cell=ScientificCell(
                        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                        method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
                        condition="Legitimate Unsupported Capability",
                        master_seed=1103,
                    ),
                    terminal_state=ExperimentLifecycleState.COMPLETED,
                    failure=None,
                    metrics=(("target-f1", 0.8),),
                ),
            ),
        )
    )
    experiment_root = isolated_repository / "experiment"
    _materialize_run_evidence(result)
    required_run_evidence = tuple(
        experiment_metric_evidence_root(result.experiment) / filename
        for filename in experiment_by_name(result.experiment).artifacts.required_metric_artifacts
    )
    assert all(path.is_file() for path in required_run_evidence)
    assert not experiment_root.exists()
    export_experiment_report(result, experiment_root)
    assert (experiment_root / "metrics" / "primary" / "summary.json").is_file()
    before = tuple(
        sorted(
            (
                path.relative_to(experiment_root).as_posix(),
                path.is_dir(),
                path.read_bytes() if path.is_file() else None,
            )
            for path in experiment_root.rglob("*")
        )
    )

    verified = verify_persisted_experiment_report(result, experiment_root)

    assert verified.verification.passed, verified.verification.failures
    assert verified.exported_paths
    after = tuple(
        sorted(
            (
                path.relative_to(experiment_root).as_posix(),
                path.is_dir(),
                path.read_bytes() if path.is_file() else None,
            )
            for path in experiment_root.rglob("*")
        )
    )
    assert after == before


def test_experiment_evidence_verification_rejects_wrong_summary_identity(
    isolated_repository: Path,
) -> None:
    result = ExperimentExecutionResult(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        lifecycle_state=ExperimentLifecycleState.COMPLETED,
        outcomes=(
            CellExecutionOutcome(
                cell=ScientificCell(
                    experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                    method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
                    condition="Legitimate Unsupported Capability",
                    master_seed=1103,
                ),
                terminal_state=ExperimentLifecycleState.COMPLETED,
                failure=None,
                metrics=(("target-f1", 0.8),),
            ),
        ),
    )
    result = _with_primary_comparison_evidence(result)
    _materialize_run_evidence(result)
    experiment_root = isolated_repository / "results"
    export_experiment_report(result, experiment_root)
    summary_path = experiment_root / "metrics" / "primary" / "summary.json"
    summary = ExperimentReportSummary.model_validate_json(summary_path.read_text())
    summary_path.write_text(
        summary.model_copy(update={"experiment": EFFICIENCY_MEASUREMENT_NAME}).model_dump_json()
    )
    verification = verify_experiment_artifacts(
        result,
        experiment_root / "tables" / "main",
        experiment_root / "figures" / "main",
        experiment_metric_evidence_root(result.experiment),
        summary_path,
        _published_source_data_identity(result),
        experiment_root,
        _published_exported_paths(result),
    )
    assert not verification.passed
    assert any("belongs to another experiment" in failure for failure in verification.failures)


def test_experiment_evidence_verification_rejects_stale_summary_digest(
    isolated_repository: Path,
) -> None:
    result = ExperimentExecutionResult(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        lifecycle_state=ExperimentLifecycleState.COMPLETED,
        outcomes=(
            CellExecutionOutcome(
                cell=ScientificCell(
                    experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                    method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
                    condition="Legitimate Unsupported Capability",
                    master_seed=1103,
                ),
                terminal_state=ExperimentLifecycleState.COMPLETED,
                failure=None,
                metrics=(("target-f1", 0.8),),
            ),
        ),
    )
    result = _with_primary_comparison_evidence(result)
    _materialize_run_evidence(result)
    experiment_root = isolated_repository / "results"
    export_experiment_report(result, experiment_root)
    summary_path = experiment_root / "metrics" / "primary" / "summary.json"
    summary = ExperimentReportSummary.model_validate_json(summary_path.read_text())
    summary_path.write_text(
        summary.model_copy(update={"execution_digest": "0" * 64}).model_dump_json()
    )
    verification = verify_experiment_artifacts(
        result,
        experiment_root / "tables" / "main",
        experiment_root / "figures" / "main",
        experiment_metric_evidence_root(result.experiment),
        summary_path,
        _published_source_data_identity(result),
        experiment_root,
        _published_exported_paths(result),
    )
    assert not verification.passed
    assert any("execution digest is stale" in failure for failure in verification.failures)


def test_experiment_evidence_verification_rejects_empty_required_table(
    isolated_repository: Path,
) -> None:
    result = ExperimentExecutionResult(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        lifecycle_state=ExperimentLifecycleState.COMPLETED,
        outcomes=(
            CellExecutionOutcome(
                cell=ScientificCell(
                    experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                    method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
                    condition="Legitimate Unsupported Capability",
                    master_seed=1103,
                ),
                terminal_state=ExperimentLifecycleState.COMPLETED,
                failure=None,
                metrics=(("target-f1", 0.8),),
            ),
        ),
    )
    result = _with_primary_comparison_evidence(result)
    _materialize_run_evidence(result)
    experiment_root = isolated_repository / "results"
    export_experiment_report(result, experiment_root)
    table_path = experiment_root / "tables" / "main" / "Cell Metrics.csv"
    table_path.write_text("")
    verification = verify_experiment_artifacts(
        result,
        experiment_root / "tables" / "main",
        experiment_root / "figures" / "main",
        experiment_metric_evidence_root(result.experiment),
        experiment_root / "metrics" / "primary" / "summary.json",
        _published_source_data_identity(result),
        experiment_root,
        _published_exported_paths(result),
    )
    assert not verification.passed
    assert any(
        "Cell Metrics: rendered table is empty" in failure for failure in verification.failures
    )


def test_experiment_evidence_verification_rejects_empty_required_figure(
    isolated_repository: Path,
) -> None:
    result = ExperimentExecutionResult(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        lifecycle_state=ExperimentLifecycleState.COMPLETED,
        outcomes=(
            CellExecutionOutcome(
                cell=ScientificCell(
                    experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                    method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
                    condition="Legitimate Unsupported Capability",
                    master_seed=1103,
                ),
                terminal_state=ExperimentLifecycleState.COMPLETED,
                failure=None,
                metrics=(("target-f1", 0.8),),
            ),
        ),
    )
    result = _with_primary_comparison_evidence(result)
    _materialize_run_evidence(result)
    experiment_root = isolated_repository / "results"
    export_experiment_report(result, experiment_root)
    figure_path = experiment_root / "figures" / "main" / "FedSIRA Protocol Schematic.png"
    figure_path.write_bytes(b"")
    verification = verify_experiment_artifacts(
        result,
        experiment_root / "tables" / "main",
        experiment_root / "figures" / "main",
        experiment_metric_evidence_root(result.experiment),
        experiment_root / "metrics" / "primary" / "summary.json",
        _published_source_data_identity(result),
        experiment_root,
        _published_exported_paths(result),
    )
    assert not verification.passed
    assert any(
        "required figure FedSIRA Protocol Schematic" in failure for failure in verification.failures
    )


def test_primary_results_uses_persisted_aggregate_metrics_for_method_summaries(
    isolated_repository: Path,
) -> None:
    outcomes = (
        CellExecutionOutcome(
            cell=ScientificCell(
                experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
                condition="Legitimate Unsupported Capability",
                master_seed=1103,
            ),
            terminal_state=ExperimentLifecycleState.COMPLETED,
            failure=None,
            metrics=(
                ("target-f1", 0.8),
                ("supported-macro-f1-harm", 0.02),
                ("benign-false-alarm-rate-increase", 0.01),
                ("attack-success-rate", 0.2),
                ("malicious-admission", 0.0),
                ("legitimate-admission", 1.0),
                ("worst-domain-target-f1", 0.7),
            ),
        ),
    )
    result = ExperimentExecutionResult(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        lifecycle_state=ExperimentLifecycleState.COMPLETED,
        outcomes=outcomes,
        provenance=_record_provenance(),
    )
    _materialize_run_evidence(result)
    table = render_primary_results_table((), outcomes)
    row = next(csv.reader((table.csv_text.splitlines()[1],)))
    assert row[2] == "0.800 ± 0.000"
    assert row[3] == "[0.800,0.800]"
    assert row[4] == "0.020 ± 0.000"
    assert row[7] == "0.000 ± 0.000"
    assert row[10] == "1"


def test_primary_results_table_retains_every_registered_method_scenario_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_aggregate(
        _experiment: ExperimentName,
        _method: MethodName,
        _scenario: ScenarioName,
        _metric: MetricName,
    ) -> AggregateMetricEvidenceRow | None:
        return None

    monkeypatch.setattr(
        "fedsira.reporting.tables._aggregate_metric_row",
        missing_aggregate,
    )
    definition = experiment_by_name(PRIMARY_CONFIRMATORY_EVALUATION_NAME)
    table = render_primary_results_table((), ())
    rows = tuple(csv.reader(table.csv_text.splitlines()))[1:]

    assert tuple((row[0], row[1]) for row in rows) == tuple(
        (method, scenario) for scenario in definition.conditions for method in definition.methods
    )
    assert all(row[2:10] == [ReportCellLiteral.NOT_AVAILABLE] * 8 for row in rows)
    assert all(row[10] == "0" for row in rows)


def test_source_exclusion_table_retains_every_registered_method_without_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_aggregate(
        _experiment: ExperimentName,
        _method: MethodName,
        _scenario: ScenarioName,
        _metric: MetricName,
    ) -> AggregateMetricEvidenceRow | None:
        return None

    monkeypatch.setattr(
        "fedsira.reporting.tables._aggregate_metric_row",
        missing_aggregate,
    )
    definition = experiment_by_name(SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME)
    table = render_source_exclusion_results_table((), (), None)
    rows = tuple(csv.reader(table.csv_text.splitlines()))[1:]

    assert tuple(row[0] for row in rows) == definition.methods
    assert all(row[1:6] == [ReportCellLiteral.NOT_AVAILABLE] * 5 for row in rows)
    assert all(row[6] == ReportCellLiteral.NOT_AVAILABLE for row in rows)
    assert len(table.aggregate_lineage) == len(definition.methods) * 4
    assert {lineage.method for lineage in table.aggregate_lineage} == set(definition.methods)


def test_failure_boundary_table_retains_registered_method_condition_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_aggregate(
        _experiment: ExperimentName,
        _method: MethodName,
        _scenario: ScenarioName,
        _metric: MetricName,
    ) -> AggregateMetricEvidenceRow | None:
        return None

    monkeypatch.setattr(
        "fedsira.reporting.tables._aggregate_metric_row",
        missing_aggregate,
    )
    boundary_experiments = (
        EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
        SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
        CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
        HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
    )
    expected_rows = tuple(
        (experiment, method, condition)
        for experiment in boundary_experiments
        for definition in (experiment_by_name(experiment),)
        for method in definition.methods
        for condition in definition.conditions
    )

    table = render_failure_boundaries_table((), ())
    rows = tuple(csv.reader(table.csv_text.splitlines()))[1:]

    assert tuple((row[0], row[1], row[2]) for row in rows) == expected_rows
    shared = experiment_by_name(SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME)
    assert len(table.aggregate_lineage) == len(expected_rows) * 3 + len(shared.methods) * len(
        shared.conditions
    )


def test_delay_efficiency_table_retains_full_registered_cells_with_missing_metrics_na(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_aggregate(
        _experiment: ExperimentName,
        _method: MethodName,
        _scenario: ScenarioName,
        _metric: MetricName,
    ) -> AggregateMetricEvidenceRow | None:
        return None

    monkeypatch.setattr(
        "fedsira.reporting.tables._aggregate_metric_row",
        missing_aggregate,
    )
    efficiency_method = experiment_by_name(EFFICIENCY_MEASUREMENT_NAME).methods[0]
    telemetry = (
        EfficiencyMetricObservation(
            method=efficiency_method,
            metric=DescriptiveScientificMetric.WALL_CLOCK_SECONDS,
            median=1.0,
            first_quartile=0.5,
            third_quartile=1.5,
            seed_count=3,
        ),
    )
    expected_rows = tuple(
        (experiment, method, condition)
        for experiment in (ADMISSION_DELAY_DECOMPOSITION_NAME, EFFICIENCY_MEASUREMENT_NAME)
        for definition in (experiment_by_name(experiment),)
        for method in definition.methods
        for condition in definition.conditions
    )

    table = render_delay_and_efficiency_table((), (), telemetry)
    rows = tuple(csv.reader(table.csv_text.splitlines()))[1:]

    assert tuple((row[0], row[1], row[2]) for row in rows) == expected_rows
    assert all(row[3] == ReportCellLiteral.NOT_AVAILABLE for row in rows)
    delay = experiment_by_name(ADMISSION_DELAY_DECOMPOSITION_NAME)
    assert len(table.aggregate_lineage) == len(delay.methods) * len(delay.conditions) * 12


def test_byzantine_table_retains_registered_method_condition_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_aggregate(
        _experiment: ExperimentName,
        _method: MethodName,
        _scenario: ScenarioName,
        _metric: MetricName,
    ) -> AggregateMetricEvidenceRow | None:
        return None

    monkeypatch.setattr(
        "fedsira.reporting.tables._aggregate_metric_row",
        missing_aggregate,
    )
    experiments = (
        COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
        COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
        BYZANTINE_BOUND_VIOLATION_NAME,
    )
    expected_rows = {
        (experiment, method, condition)
        for experiment in experiments
        for definition in (experiment_by_name(experiment),)
        for method in definition.methods
        for condition in definition.conditions
    }

    table = render_byzantine_robustness_table((), ())
    rows = tuple(csv.reader(table.csv_text.splitlines()))[1:]

    assert len(rows) == len(expected_rows)
    assert {(row[0], row[1], row[2]) for row in rows} == expected_rows
    assert len(table.aggregate_lineage) == len(expected_rows) * 6


def test_generalization_table_retains_registered_cells_and_aggregate_lineage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_aggregate(
        _experiment: ExperimentName,
        _method: MethodName,
        _scenario: ScenarioName,
        _metric: MetricName,
    ) -> AggregateMetricEvidenceRow | None:
        return None

    monkeypatch.setattr(
        "fedsira.reporting.tables._aggregate_metric_row",
        missing_aggregate,
    )
    definition = experiment_by_name(SECONDARY_DATASET_GENERALIZATION_NAME)
    table = render_generalization_results_table((), ())
    rows = tuple(csv.reader(table.csv_text.splitlines()))[1:]
    expected = tuple(
        (method, scenario) for method in definition.methods for scenario in SecondaryScenario
    )

    assert tuple((row[0], row[1]) for row in rows) == expected
    assert len(table.aggregate_lineage) == len(expected) * 5


def test_primary_descriptive_summary_does_not_fall_back_to_paired_comparison() -> None:
    definition = next(
        item
        for item in build_comparison_registry()
        if (
            item.experiment == PRIMARY_CONFIRMATORY_EVALUATION_NAME
            and item.method == CoreMethodIdentity.RESOLVED_FEDSIRA_CORE
            and item.scientific_scenario == "Legitimate Unsupported Capability"
            and item.metric is ComparisonMetric.TARGET_F1
        )
    )
    comparison = ComparisonResult(
        definition=definition,
        paired_differences=(0.4,),
        complete_seed_count=1,
        mean_paired_difference=0.4,
        median_paired_difference=0.4,
        paired_standardized_effect=None,
        raw_p_value=None,
        adjusted_p_value=None,
        confidence_interval=(0.1, 0.7),
        materiality_passes=None,
        comparison_state=ComparisonState.UNDEFINED,
    )
    table = render_primary_results_table(
        (ComparisonFamilyResult(family=definition.family, comparisons=(comparison,)),),
        (
            CellExecutionOutcome(
                cell=ScientificCell(
                    experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                    method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
                    condition="Legitimate Unsupported Capability",
                    master_seed=1103,
                ),
                terminal_state=ExperimentLifecycleState.COMPLETED,
                failure=None,
                metrics=(("target-f1", None),),
            ),
        ),
    )
    row = next(csv.reader((table.csv_text.splitlines()[1],)))
    assert row[2] == "NA"
    assert len(table.aggregate_lineage) == 42 * 8
    assert len({item.row_index for item in table.aggregate_lineage}) == 42
    assert any(
        item.source_column is ReportColumnName.TARGET_F1_95_CI
        and item.statistic is AggregateDisplayStatistic.CONFIDENCE_INTERVAL_95
        for item in table.aggregate_lineage
    )


def test_statistical_summary_rows_retain_comparison_cell_lineage() -> None:
    definition = next(
        item
        for item in build_comparison_registry()
        if item.experiment == PRIMARY_CONFIRMATORY_EVALUATION_NAME
    )
    comparison = ComparisonResult(
        definition=definition,
        paired_differences=(0.2, -0.1),
        complete_seed_count=2,
        mean_paired_difference=0.05,
        median_paired_difference=0.05,
        paired_standardized_effect=0.2,
        raw_p_value=0.5,
        adjusted_p_value=0.75,
        confidence_interval=(-0.2, 0.3),
        materiality_passes=None,
        comparison_state=ComparisonState.INCONCLUSIVE_TECHNICAL,
        paired_master_seeds=(1103, 1109),
    )

    table = render_statistical_summary_table(
        (ComparisonFamilyResult(family=definition.family, comparisons=(comparison,)),)
    )

    assert len(table.comparison_lineage) == 1
    lineage = table.comparison_lineage[0]
    assert lineage.row_index == 0
    assert lineage.experiment == definition.experiment
    assert lineage.comparison_name == definition.comparison_name
    assert lineage.paired_master_seeds == (1103, 1109)
    assert len(lineage.source_cell_semantic_keys) == 4
    assert ReportColumnName.HOLM_P in lineage.source_columns


def _collapse_decisions() -> tuple[CollapseDecision, ...]:
    return (
        CollapseDecision(
            kind=CollapseDecisionKind.PROPOSAL_ASSISTANCE,
            comparator=OpeningMode.CANDIDATE_FREE,
            survives=True,
            primary_material_effect="false-launch",
            adjusted_p_value=0.01,
            constraint_passes=True,
            reason="mechanical collapse rule",
        ),
        CollapseDecision(
            kind=CollapseDecisionKind.PLURALITY,
            comparator=BaselineIdentity.ONE_INDEPENDENT_RETRAIN,
            survives=True,
            primary_material_effect="malicious-admission",
            adjusted_p_value=0.02,
            constraint_passes=True,
            reason="mechanical collapse rule",
        ),
        CollapseDecision(
            kind=CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION,
            comparator=BaselineIdentity.SOURCE_UPDATE_SANITIZATION_REFERENCE,
            survives=True,
            primary_material_effect="asr",
            adjusted_p_value=0.03,
            constraint_passes=True,
            reason="mechanical collapse rule",
        ),
        CollapseDecision(
            kind=CollapseDecisionKind.EXTERNAL_VERIFICATION,
            comparator=BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM,
            survives=True,
            primary_material_effect="malicious-admission",
            adjusted_p_value=0.04,
            constraint_passes=True,
            reason="mechanical collapse rule",
        ),
    )


def _lifecycle_records() -> tuple[ExperimentLifecycleRecord, ...]:
    plan = build_plan(resolved_core_complete=True)
    return tuple(
        ExperimentLifecycleRecord(
            experiment=planned.definition.name,
            state=ExperimentLifecycleState.COMPLETED,
        )
        for planned in plan.experiments
    )


def _override_results_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("fedsira.reporting.export.project_summary_root", lambda: tmp_path)


def _no_missing_result_evidence(
    _comparison_results: tuple[ComparisonFamilyResult, ...],
    _outcomes: tuple[CellExecutionOutcome, ...],
) -> tuple[str, ...]:
    return ()


def _publish_claim_upstream(
    family: ArtifactFamily,
    producer: ArtifactProducer,
    instance: str,
) -> ArtifactManifest:
    slot = ArtifactSlot(
        family=family,
        instance=instance,
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    )
    manifest, _reused = publish_artifact(
        slot=slot,
        producer=producer,
        payload=b"upstream-evidence",
        dependencies=(),
        procedure_identity="fedsira|claim-upstream-fixture|1",
        slot_directory=current_repository_root() / artifact_slot_directory(slot),
        staging_root=current_repository_root() / artifact_staging_root(),
    )
    return manifest


def test_export_project_summary_blocks_empty_result_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = build_plan(resolved_core_complete=True)
    verification = CompletenessVerificationResult(passed=True, failures=())
    _override_results_root(tmp_path, monkeypatch)
    result = export_project_summary(
        plan,
        _lifecycle_records(),
        verification,
        collapse_decisions=None,
        resolved_core=None,
        comparison_results=(),
        outcomes=(),
        evidence_trajectory=(),
        telemetry=(),
    )
    assert isinstance(result, ReportExportResult)
    assert not result.exported_paths
    assert not result.verification.passed
    assert any("Primary Results" in failure for failure in result.verification.failures)
    assert any("Statistical Summary" in failure for failure in result.verification.failures)


def test_export_project_summary_writes_nothing_without_final_claim_decisions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _override_results_root(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "fedsira.reporting.export._missing_result_evidence", _no_missing_result_evidence
    )
    result = export_project_summary(
        build_plan(resolved_core_complete=True),
        _lifecycle_records(),
        CompletenessVerificationResult(passed=True, failures=()),
        collapse_decisions=None,
        resolved_core=None,
        comparison_results=(),
        outcomes=(),
        evidence_trajectory=(
            EvidenceStateFraction(
                condition="Immediate Quorum",
                cycle=0,
                state=AdmissionState.ADMITTED,
                fraction=1.0,
                instance_count=1,
                instance_total=1,
            ),
        ),
        telemetry=(
            EfficiencyMetricObservation(
                method=BaselineIdentity.FEDAVG_REFERENCE,
                metric=ComparisonMetric.TARGET_F1,
                median=0.5,
                first_quartile=0.4,
                third_quartile=0.6,
                seed_count=10,
            ),
        ),
    )

    assert not result.verification.passed
    assert result.verification.failures == (
        "Claim states: final evidence-driven decisions are not available",
    )
    assert not result.exported_paths
    assert not tuple(tmp_path.iterdir())


def test_project_summary_publishes_claim_states_before_blocking_unresolved_claims(
    isolated_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _override_results_root(isolated_repository / "project-summary", monkeypatch)
    monkeypatch.setattr(
        "fedsira.reporting.export._missing_result_evidence", _no_missing_result_evidence
    )
    statistical = _publish_claim_upstream(
        ArtifactFamily.STATISTICAL_COMPARISON_ARTIFACT,
        ArtifactProducer.EVALUATION_PRODUCER,
        "statistical-comparisons",
    )
    gate = _publish_claim_upstream(
        ArtifactFamily.FINAL_GATE_DECISION,
        ArtifactProducer.FINAL_GATE_EVALUATOR,
        "final-gate",
    )

    result = export_project_summary(
        build_plan(resolved_core_complete=True),
        _lifecycle_records(),
        CompletenessVerificationResult(passed=True, failures=()),
        collapse_decisions=None,
        resolved_core=None,
        comparison_results=(),
        outcomes=(),
        evidence_trajectory=(
            EvidenceStateFraction(
                condition="Immediate Quorum",
                cycle=0,
                state=AdmissionState.ADMITTED,
                fraction=1.0,
                instance_count=1,
                instance_total=1,
            ),
        ),
        telemetry=(
            EfficiencyMetricObservation(
                method=BaselineIdentity.FEDAVG_REFERENCE,
                metric=ComparisonMetric.TARGET_F1,
                median=0.5,
                first_quartile=0.4,
                third_quartile=0.6,
                seed_count=10,
            ),
        ),
        claim_upstream_manifests=(statistical, gate),
    )

    claim_artifact = read_claim_state_artifact((statistical, gate))
    assert not result.verification.passed
    assert result.verification.failures == (
        "Claim states: final evidence-driven decisions are not available",
    )
    assert not result.exported_paths
    assert claim_artifact is not None
    assert claim_artifact[0].dependencies[0].kind is ArtifactDependencyKind.ARTIFACT
    assert len(claim_artifact[1].claim_summary.decisions) == 19
    assert (
        publish_claim_state_artifact(
            claim_artifact[1].claim_inputs,
            (statistical, gate),
        )[0].identity
        == claim_artifact[0].identity
    )


def test_export_project_summary_accepts_descriptive_experiments_without_comparisons(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = build_plan(resolved_core_complete=True)
    verification = CompletenessVerificationResult(passed=True, failures=())
    _override_results_root(tmp_path, monkeypatch)
    descriptive_outcome = CellExecutionOutcome(
        cell=ScientificCell(
            experiment=EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
            method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
            condition="Immediate Quorum",
            master_seed=1103,
        ),
        terminal_state=ExperimentLifecycleState.COMPLETED,
        failure=None,
        metrics=(("legitimate-admission", 1.0),),
    )
    result = export_project_summary(
        plan,
        _lifecycle_records(),
        verification,
        collapse_decisions=None,
        resolved_core=None,
        comparison_results=(),
        outcomes=(descriptive_outcome,),
        evidence_trajectory=(
            EvidenceStateFraction(
                condition="Immediate Quorum",
                cycle=0,
                state=AdmissionState.ADMITTED,
                fraction=1.0,
                instance_count=1,
                instance_total=1,
            ),
        ),
        telemetry=(),
    )
    failures = result.verification.failures
    assert not any(
        EVIDENCE_SCARCITY_AND_DORMANCY_NAME in failure and "missing required" in failure
        for failure in failures
    )


def test_export_project_summary_with_collapse_decisions_still_requires_result_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = build_plan(resolved_core_complete=True)
    verification = CompletenessVerificationResult(passed=True, failures=())
    resolved_core = ResolvedCore(
        proposal_assistance_survives=True,
        plurality_survives=True,
        direct_source_exclusion_survives=True,
        external_verification_survives=True,
        opening_mode=AdmissionOpeningMode.PROPOSAL_ASSISTED,
        reproduction_row_requirement=ReproductionRowRequirement.FIVE_CERTIFIED_NON_SOURCE_ROWS,
        row_verification_mode=RowVerificationMode.THREE_VERIFIER_TWO_OF_THREE,
        production_update_rule=ProductionUpdateRule.KRUM_CERTIFIED_ROWS,
    )
    _override_results_root(tmp_path, monkeypatch)
    result = export_project_summary(
        plan,
        _lifecycle_records(),
        verification,
        collapse_decisions=_collapse_decisions(),
        resolved_core=resolved_core,
        comparison_results=(),
        outcomes=(),
        evidence_trajectory=(),
        telemetry=(),
    )
    assert not result.exported_paths
    assert not result.verification.passed


def test_render_security_utility_tradeoff_blocks_without_evidence(tmp_path: Path) -> None:
    destination = tmp_path / "tradeoff.png"
    with pytest.raises(ValueError, match="missing comparison evidence"):
        render_security_utility_tradeoff((), destination)


def test_security_utility_tradeoff_uses_primary_family_and_disambiguates_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    definitions = build_comparison_registry()
    primary = tuple(
        next(
            definition
            for definition in definitions
            if definition.experiment == PRIMARY_CONFIRMATORY_EVALUATION_NAME
            and definition.metric is metric
            and definition.scientific_scenario == PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT
        )
        for metric in (
            ComparisonMetric.TARGET_F1,
            ComparisonMetric.ATTACK_SUCCESS_RATE,
            ComparisonMetric.MALICIOUS_ADMISSION,
        )
    )
    second_primary_target = next(
        definition
        for definition in definitions
        if definition.experiment == PRIMARY_CONFIRMATORY_EVALUATION_NAME
        and definition.metric is ComparisonMetric.TARGET_F1
        and definition.scientific_scenario == PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY
    )
    unrelated = next(
        definition
        for definition in definitions
        if definition.experiment != PRIMARY_CONFIRMATORY_EVALUATION_NAME
        and definition.metric is ComparisonMetric.TARGET_F1
    )

    def result_for(definition: ComparisonDefinition) -> ComparisonResult:
        return ComparisonResult(
            definition=definition,
            paired_differences=(0.1, 0.1, 0.1),
            complete_seed_count=3,
            mean_paired_difference=0.1,
            median_paired_difference=0.1,
            paired_standardized_effect=1.0,
            raw_p_value=0.01,
            adjusted_p_value=0.01,
            confidence_interval=(0.05, 0.15),
            materiality_passes=True,
            comparison_state=ComparisonState.PASSED,
        )

    observed_labels: list[tuple[str, ...]] = []
    observed_annotations: list[str] = []

    def capture_figure(figure: Figure, *_args: object, **_kwargs: object) -> None:
        observed_labels.extend(
            tuple(label.get_text() for label in axis.get_yticklabels()) for axis in figure.axes
        )
        observed_annotations.extend(text.get_text() for axis in figure.axes for text in axis.texts)

    monkeypatch.setattr(Figure, "savefig", capture_figure)
    destination = tmp_path / "tradeoff.png"
    render_security_utility_tradeoff(
        (
            ComparisonFamilyResult(
                family=primary[0].family,
                comparisons=(
                    *(result_for(definition) for definition in primary),
                    result_for(second_primary_target).model_copy(
                        update={
                            "paired_differences": (),
                            "complete_seed_count": 0,
                            "mean_paired_difference": None,
                            "median_paired_difference": None,
                            "paired_standardized_effect": None,
                            "raw_p_value": None,
                            "adjusted_p_value": None,
                            "confidence_interval": None,
                            "materiality_passes": None,
                            "comparison_state": ComparisonState.INCONCLUSIVE_TECHNICAL,
                            "paired_master_seeds": (),
                        }
                    ),
                ),
            ),
            ComparisonFamilyResult(
                family=unrelated.family,
                comparisons=(result_for(unrelated),),
            ),
        ),
        destination,
    )

    target_labels = observed_labels[0]
    expected_target_definitions = tuple(
        definition
        for definition in definitions
        if definition.experiment == PRIMARY_CONFIRMATORY_EVALUATION_NAME
        and definition.metric is ComparisonMetric.TARGET_F1
    )
    assert len(target_labels) == len(expected_target_definitions)
    assert any(str(primary[0].scientific_scenario) in label for label in target_labels)
    assert ReportCellLiteral.NOT_AVAILABLE in observed_annotations
    assert any(str(second_primary_target.scientific_scenario) in label for label in target_labels)
    assert set(target_labels) == {
        f"{definition.scientific_scenario}\n{definition.method} vs {definition.reference_method}"
        for definition in expected_target_definitions
    }
    assert all(str(unrelated.experiment) not in label for label in target_labels)


def test_render_useful_backdoored_source_uses_persisted_aggregate_metrics(
    tmp_path: Path,
    isolated_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "source-exclusion.png"
    outcome = CellExecutionOutcome(
        cell=ScientificCell(
            experiment=SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
            method=SourceExclusionMethod.FULL_FEDSIRA,
            condition=PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,
            master_seed=1103,
        ),
        terminal_state=ExperimentLifecycleState.COMPLETED,
        failure=None,
        metrics=(
            ("asr", 0.1),
            ("target-f1", 0.8),
        ),
    )
    result = ExperimentExecutionResult(
        experiment=SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
        lifecycle_state=ExperimentLifecycleState.COMPLETED,
        outcomes=(outcome,),
        provenance=_record_provenance(),
    )
    _materialize_run_evidence(result)
    legend_labels: list[str] = []

    def capture_figure(self: Figure, destination: Path, *, dpi: int) -> None:
        del dpi
        legend_labels.extend(self.axes[0].get_legend_handles_labels()[1])
        Path(destination).write_bytes(b"figure fixture")

    monkeypatch.setattr(Figure, "savefig", capture_figure)
    path = render_useful_backdoored_source((), destination, (outcome,))
    assert path.exists()
    assert {
        str(method)
        for method in experiment_by_name(SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME).methods
    } <= set(legend_labels)


def test_render_protocol_schematic_writes_file(tmp_path: Path) -> None:
    destination = tmp_path / "schematic.png"
    render_protocol_schematic(destination)
    assert destination.exists()


def test_validate_mandatory_figures_covered() -> None:
    schematic_name = "FedSIRA Protocol Schematic"
    missing = validate_mandatory_figures_covered((Path(f"{schematic_name}.png"),))
    assert schematic_name in MANDATORY_FIGURE_NAMES
    assert schematic_name not in missing
    assert len(missing) == len(MANDATORY_FIGURE_NAMES) - 1
    all_missing = validate_mandatory_figures_covered(())
    assert set(all_missing) == set(MANDATORY_FIGURE_NAMES)


def _record_provenance() -> ExecutionProvenance:
    return ExecutionProvenance(
        configuration_digest="a" * 64,
        code_revision=None,
        dataset_manifest_hash="b" * 64,
    )


def test_metric_evidence_embeds_cell_lineage_and_source_metric_references(
    tmp_path: Path,
) -> None:
    cell = ScientificCell(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
        condition="Legitimate Unsupported Capability",
        master_seed=1103,
    )
    result = ExperimentExecutionResult(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        lifecycle_state=ExperimentLifecycleState.COMPLETED,
        outcomes=(
            CellExecutionOutcome(
                cell=cell,
                terminal_state=ExperimentLifecycleState.COMPLETED,
                failure=None,
                metrics=((ComparisonMetric.TARGET_F1, 0.8),),
                scoring_artifact_ids=("c" * 64,),
            ),
            CellExecutionOutcome(
                cell=cell.model_copy(update={"master_seed": 1217}),
                terminal_state=ExperimentLifecycleState.FAILED,
                failure=None,
                metrics=((ComparisonMetric.TARGET_F1, 0.1),),
            ),
        ),
        provenance=_record_provenance(),
    )
    materialized = materialize_experiment_evidence(
        result,
        tmp_path / "metrics",
        tmp_path / "telemetry",
    )
    cell_rows = pandas.read_parquet(materialized.paths[0])
    seed_rows = pandas.read_parquet(materialized.paths[1])
    aggregate_rows = pandas.read_parquet(materialized.paths[2])
    assert cell_rows.loc[0, "dataset"] == DatasetId.N_BAIOT
    assert cell_rows.loc[0, "cell_semantic_key"] == cell.semantic_key
    assert cell_rows.loc[0, "configuration_digest"] == "a" * 64
    assert cell_rows.loc[0, "dataset_manifest_hash"] == "b" * 64
    assert cell_rows.loc[0, "scoring_artifact_ids"] == ["c" * 64]
    assert len(seed_rows) == 1
    assert seed_rows.loc[0, "master_seed"] == 1103
    assert seed_rows.loc[0, "value"] == 0.8
    assert seed_rows.loc[0, "source_observation_ids"] == [cell_rows.loc[0, "observation_id"]]
    assert len(aggregate_rows) == 1
    assert aggregate_rows.loc[0, "observation_count"] == 1
    assert aggregate_rows.loc[0, "source_observation_ids"] == [cell_rows.loc[0, "observation_id"]]
    assert aggregate_rows.loc[0, "source_cell_semantic_keys"] == [cell.semantic_key]
    assert aggregate_rows.loc[0, "seed_count"] == 1
    assert aggregate_rows.loc[0, "mean_value"] == 0.8
    assert aggregate_rows.loc[0, "median_value"] == 0.8
    assert aggregate_rows.loc[0, "first_quartile"] == 0.8
    assert aggregate_rows.loc[0, "third_quartile"] == 0.8


def test_seed_metric_evidence_aggregates_repetitions_within_seed(
    tmp_path: Path,
) -> None:
    cell = ScientificCell(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
        condition="Legitimate Unsupported Capability",
        master_seed=1103,
        repetition=1,
    )
    outcomes = tuple(
        CellExecutionOutcome(
            cell=cell.model_copy(update=updates),
            terminal_state=ExperimentLifecycleState.COMPLETED,
            failure=None,
            metrics=((ComparisonMetric.TARGET_F1, value),),
        )
        for updates, value in (
            ({"repetition": 1}, 0.6),
            ({"repetition": 2}, 0.8),
            ({"master_seed": 1217, "repetition": 1}, 0.9),
        )
    )
    result = ExperimentExecutionResult(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        lifecycle_state=ExperimentLifecycleState.COMPLETED,
        outcomes=outcomes,
        provenance=_record_provenance(),
    )

    materialized = materialize_experiment_evidence(
        result,
        tmp_path / "metrics",
        tmp_path / "telemetry",
    )
    seed_rows = pandas.read_parquet(materialized.paths[1])
    aggregate_rows = pandas.read_parquet(materialized.paths[2])
    seed_records = cast(list[dict[str, object]], cast(Any, seed_rows).to_dict(orient="records"))

    assert [record["value"] for record in seed_records] == [0.7, 0.9]
    assert [record["master_seed"] for record in seed_records] == [1103, 1217]
    source_ids = cast(
        list[list[str]], [record["source_observation_ids"] for record in seed_records]
    )
    assert tuple(map(len, source_ids)) == (2, 1)
    assert len(aggregate_rows) == 1
    assert aggregate_rows.loc[0, "seed_count"] == 2
    assert aggregate_rows.loc[0, "observation_count"] == 3
    assert aggregate_rows.loc[0, "mean_value"] == 0.8


def test_comparison_evidence_embeds_paired_seed_and_both_source_cells(
    tmp_path: Path,
) -> None:
    definition = next(
        definition
        for definition in build_comparison_registry()
        if definition.experiment == PRIMARY_CONFIRMATORY_EVALUATION_NAME
        and definition.reference_kind is ComparisonReferenceKind.SCIENTIFIC_CELL
    )
    comparison = ComparisonResult(
        definition=definition,
        paired_differences=(),
        complete_seed_count=1,
        mean_paired_difference=None,
        median_paired_difference=None,
        paired_standardized_effect=None,
        raw_p_value=None,
        adjusted_p_value=None,
        confidence_interval=None,
        materiality_passes=None,
        comparison_state=ComparisonState.UNDEFINED,
        paired_master_seeds=(1103,),
    )
    result = ExperimentExecutionResult(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        lifecycle_state=ExperimentLifecycleState.COMPLETED,
        outcomes=(),
        comparison_results=(
            ComparisonFamilyResult(family=definition.family, comparisons=(comparison,)),
        ),
        provenance=_record_provenance(),
        comparison_artifact_id="d" * 64,
    )
    materialized = materialize_experiment_evidence(
        result,
        tmp_path / "metrics",
        tmp_path / "telemetry",
    )
    comparison_rows = pandas.read_parquet(materialized.paths[-1])
    paired_seeds = cast(list[MasterSeed], comparison_rows.loc[0, "complete_seeds"])
    source_cells = cast(list[str], comparison_rows.loc[0, "source_cell_semantic_keys"])
    assert paired_seeds == [1103]
    assert comparison_rows.loc[0, "comparison_artifact_id"] == "d" * 64
    assert len(source_cells) == 2
    assert (
        source_cells[0]
        == ScientificCell(
            experiment=definition.experiment,
            method=definition.method,
            condition=definition.scientific_scenario,
            master_seed=1103,
        ).semantic_key
    )
    assert (
        source_cells[1]
        == ScientificCell(
            experiment=definition.reference_experiment,
            method=definition.reference_method,
            condition=definition.reference_scenario,
            master_seed=1103,
        ).semantic_key
    )


def test_project_evidence_trajectory_reads_persisted_run_side_fractions(
    isolated_repository: Path,
) -> None:
    horizon = CONFIG.protocol.resource_horizon.maximum_logical_evidence_cycles
    outcomes = tuple(
        CellExecutionOutcome(
            cell=ScientificCell(
                experiment=EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
                method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
                condition=schedule,
                master_seed=seed,
            ),
            terminal_state=ExperimentLifecycleState.COMPLETED,
            failure=None,
            state_trajectory=tuple(
                AdmissionStateObservation(
                    cycle=cycle,
                    state=(
                        AdmissionState.DORMANT
                        if cycle == 0
                        else (AdmissionState.ADMITTED if seed == 1103 else AdmissionState.REJECTED)
                        if schedule is EvidenceArrivalSchedule.IMMEDIATE_QUORUM and cycle >= 2
                        else AdmissionState.VERIFICATION_PENDING
                    ),
                )
                for cycle in range(horizon + 1)
            ),
        )
        for schedule in EvidenceArrivalSchedule
        for seed in (
            (1103, 1104) if schedule is EvidenceArrivalSchedule.IMMEDIATE_QUORUM else (1103,)
        )
    )
    result = ExperimentExecutionResult(
        experiment=EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
        lifecycle_state=ExperimentLifecycleState.COMPLETED,
        outcomes=outcomes,
        provenance=_record_provenance(),
    )
    materialized = materialize_experiment_evidence(
        result,
        experiment_metric_evidence_root(EVIDENCE_SCARCITY_AND_DORMANCY_NAME),
        experiment_telemetry_evidence_root(EVIDENCE_SCARCITY_AND_DORMANCY_NAME),
    )
    assert any(
        Path(path).name == STATE_TRAJECTORY_FRACTIONS_PARQUET_NAME for path in materialized.paths
    )
    fraction_frame = pandas.read_parquet(
        experiment_metric_evidence_root(EVIDENCE_SCARCITY_AND_DORMANCY_NAME)
        / STATE_TRAJECTORY_FRACTIONS_PARQUET_NAME
    )
    assert len(fraction_frame) == len(EvidenceArrivalSchedule) * (horizon + 1) * 5
    immediate_cycle_zero = fraction_frame[
        (fraction_frame["condition"] == EvidenceArrivalSchedule.IMMEDIATE_QUORUM)
        & (fraction_frame["logical_evidence_cycle"] == 0)
    ]
    assert len(immediate_cycle_zero) == 5
    assert 0.0 in immediate_cycle_zero["fraction_of_seed_instances"].tolist()
    for condition in EvidenceArrivalSchedule:
        for cycle in range(horizon + 1):
            cycle_rows = fraction_frame[
                (fraction_frame["condition"] == condition)
                & (fraction_frame["logical_evidence_cycle"] == cycle)
            ]
            fractions = cast("pandas.Series[float]", cycle_rows["fraction_of_seed_instances"])
            observations = cast("pandas.Series[int]", cycle_rows["observation_count"])
            seeds = cast("pandas.Series[int]", cycle_rows["seed_count"])
            assert isclose(sum(fractions), 1.0, abs_tol=1e-12)
            assert sum(observations) == seeds.iloc[0]
    _materialize_run_evidence(result)
    trajectory = project_evidence_trajectory()
    assert {(item.cycle, item.state.value, item.fraction) for item in trajectory} >= {
        (0, "Dormant", 1.0),
        (2, "Admitted", 0.5),
    }
    assert any(
        item.condition == EvidenceArrivalSchedule.PERMANENT_SINGLETON
        and item.cycle == 2
        and item.state is AdmissionState.VERIFICATION_PENDING
        and item.fraction == 1.0
        for item in trajectory
    )
    assert any(
        item.condition == EvidenceArrivalSchedule.IMMEDIATE_QUORUM
        and item.cycle >= 2
        and item.state is AdmissionState.REJECTED
        and item.fraction == 0.5
        for item in trajectory
    )


def test_evidence_arrival_trajectory_preserves_expired_state(
    isolated_repository: Path,
    tmp_path: Path,
) -> None:
    del isolated_repository
    destination = tmp_path / "trajectory.png"
    horizon = current_application_context().scientific_config.protocol.resource_horizon

    def instance_count(
        schedule: EvidenceArrivalSchedule,
        cycle: int,
        state: AdmissionState,
    ) -> ScientificCellCount:
        if schedule is EvidenceArrivalSchedule.PERMANENT_SINGLETON and cycle == 1:
            return 4 if state is AdmissionState.EXPIRED else 0
        if schedule is EvidenceArrivalSchedule.PERMANENT_SINGLETON and cycle == 2:
            return (
                3
                if state is AdmissionState.DORMANT
                else 1
                if state is AdmissionState.REJECTED
                else 0
            )
        return 4 if state is AdmissionState.DORMANT else 0

    states = tuple(
        EvidenceStateFraction(
            condition=schedule,
            cycle=cycle,
            state=state,
            fraction=instance_count(schedule, cycle, state) / 4,
            instance_count=instance_count(schedule, cycle, state),
            instance_total=4,
        )
        for schedule in EvidenceArrivalSchedule
        for cycle in range(horizon.maximum_logical_evidence_cycles + 1)
        for state in (
            AdmissionState.DORMANT,
            AdmissionState.VERIFICATION_PENDING,
            AdmissionState.ADMITTED,
            AdmissionState.REJECTED,
            AdmissionState.EXPIRED,
        )
    )

    assert render_evidence_arrival_trajectory(states, destination) == destination
    assert destination.is_file()
    unpartitioned = tuple(
        item.model_copy(update={"fraction": 0.75, "instance_count": 3})
        if (
            item.condition == EvidenceArrivalSchedule.IMMEDIATE_QUORUM
            and item.cycle == 0
            and item.state is AdmissionState.DORMANT
        )
        else item
        for item in states
    )
    with pytest.raises(ValueError, match="do not partition seeds"):
        render_evidence_arrival_trajectory(unpartitioned, tmp_path / "unpartitioned.png")


def test_evidence_arrival_trajectory_rejects_incomplete_state_grid(
    isolated_repository: Path,
    tmp_path: Path,
) -> None:
    del isolated_repository
    states = (
        EvidenceStateFraction(
            condition=EvidenceArrivalSchedule.PERMANENT_SINGLETON,
            cycle=0,
            state=AdmissionState.DORMANT,
            fraction=1.0,
            instance_count=1,
            instance_total=1,
        ),
    )
    with pytest.raises(ValueError, match="schedule grid is incomplete"):
        render_evidence_arrival_trajectory(states, tmp_path / "trajectory.png")


def test_useful_backdoored_source_figure_marks_missing_aggregate_rows_as_na(
    isolated_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    outcome = CellExecutionOutcome(
        cell=ScientificCell(
            experiment=SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
            method=SourceExclusionMethod.FULL_FEDSIRA,
            condition=PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,
            master_seed=1103,
        ),
        terminal_state=ExperimentLifecycleState.COMPLETED,
        failure=None,
        metrics=(),
    )
    annotations: list[str] = []

    def capture_rendered_figure(figure: Figure, destination: Path, *, dpi: int) -> None:
        del dpi
        annotations.extend(text.get_text() for axis in figure.axes for text in axis.texts)
        Path(destination).write_bytes(b"figure fixture")

    monkeypatch.setattr(Figure, "savefig", capture_rendered_figure)
    destination = tmp_path / "source-na.png"

    assert render_useful_backdoored_source((), destination, (outcome,)) == destination
    assert ReportCellLiteral.NOT_AVAILABLE in annotations


def test_cell_metrics_table_keeps_failed_state_and_undefined_metric() -> None:
    outcome = CellExecutionOutcome(
        cell=ScientificCell(
            experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
            method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
            condition="insufficient evidence fixture",
            master_seed=1103,
        ),
        terminal_state=ExperimentLifecycleState.FAILED,
        failure=None,
        metrics=(("supported-macro-f1-harm", None),),
    )

    rows = list(csv.reader(render_experiment_cell_metrics_table((outcome,)).csv_text.splitlines()))

    assert rows[1][5] == ExperimentLifecycleState.FAILED
    assert rows[1][6] == "supported-macro-f1-harm"
    assert rows[1][7] == "NA"


def test_admission_delay_figure_marks_missing_phase_as_na(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import fedsira.reporting.figures as figures_module

    outcome = CellExecutionOutcome(
        cell=ScientificCell(
            experiment=ADMISSION_DELAY_DECOMPOSITION_NAME,
            method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
            condition=EvidenceArrivalSchedule.IMMEDIATE_QUORUM,
            master_seed=1103,
        ),
        terminal_state=ExperimentLifecycleState.COMPLETED,
        failure=None,
        metrics=(),
    )

    def aggregate_mean(
        _outcomes: tuple[CellExecutionOutcome, ...],
        _experiment: ExperimentName,
        _method: MethodName,
        _condition: ScenarioName,
        metric: MetricName,
    ) -> MetricValue | None:
        return None if metric == DelayPhaseMetric.VERIFY_SECONDS else 2.0

    monkeypatch.setattr(
        figures_module,
        "_aggregate_metric_mean",
        aggregate_mean,
    )
    annotations: list[str] = []
    bar_heights: list[float] = []
    tick_labels: list[str] = []

    def capture_rendered_annotations(self: Figure, destination: Path, *, dpi: int) -> None:
        del destination, dpi
        annotations.extend(text.get_text() for axis in self.axes for text in axis.texts)
        tick_labels.extend(
            label.get_text() for axis in self.axes for label in axis.get_xticklabels()
        )
        bar_heights.extend(
            cast(Rectangle, patch).get_height() for axis in self.axes for patch in axis.patches
        )

    monkeypatch.setattr(Figure, "savefig", capture_rendered_annotations)
    destination = tmp_path / "delay.png"

    assert render_admission_delay_decomposition((), destination, (outcome,)) == destination
    assert ReportCellLiteral.NOT_AVAILABLE in annotations
    delay_definition = experiment_by_name(ADMISSION_DELAY_DECOMPOSITION_NAME)
    assert len(bar_heights) == 4 * len(delay_definition.methods) * len(delay_definition.conditions)
    assert not any(bar_heights)
    assert set(tick_labels) == {
        f"{method}\n{condition}"
        for method in delay_definition.methods
        for condition in delay_definition.conditions
    }


def test_efficiency_profile_retains_registered_methods_and_marks_missing_metrics_na(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    methods = experiment_by_name(EFFICIENCY_MEASUREMENT_NAME).methods
    figure_labels: list[tuple[str, ...]] = []
    figure_annotations: list[tuple[str, ...]] = []

    def capture_figure(self: Figure, destination: Path, *, dpi: int) -> None:
        del destination, dpi
        figure_labels.extend(
            tuple(label.get_text() for label in axis.get_xticklabels()) for axis in self.axes
        )
        figure_annotations.extend(
            tuple(text.get_text() for text in axis.texts) for axis in self.axes
        )

    monkeypatch.setattr(Figure, "savefig", capture_figure)
    render_efficiency_profile(
        (
            EfficiencyMetricObservation(
                method=methods[0],
                metric=DescriptiveScientificMetric.WALL_CLOCK_SECONDS,
                median=10.0,
                first_quartile=9.0,
                third_quartile=11.0,
                seed_count=3,
            ),
        ),
        tmp_path / "efficiency.png",
    )

    expected_methods = {str(method) for method in methods}
    assert len(figure_labels) == 3
    assert all(set(labels) == expected_methods for labels in figure_labels)
    assert all(ReportCellLiteral.NOT_AVAILABLE in annotations for annotations in figure_annotations)


def test_capability_boundary_figure_marks_structural_na_as_na(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import fedsira.reporting.figures as figures_module

    outcomes = tuple(
        CellExecutionOutcome(
            cell=ScientificCell(
                experiment=CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
                method=method,
                condition=RootCauseMixture.BALANCED_50_50,
                master_seed=1103,
            ),
            terminal_state=ExperimentLifecycleState.COMPLETED,
            failure=None,
            metrics=(),
        )
        for method in CapabilityContractScope
    )

    def aggregate_mean(
        _outcomes: tuple[CellExecutionOutcome, ...],
        _experiment: ExperimentName,
        method: MethodName,
        _condition: ScenarioName,
        metric: MetricName,
    ) -> MetricValue | None:
        if (
            metric == ComparisonMetric.FALSE_SAME_CAPABILITY_CERTIFICATION_RATE
            and method is CapabilityContractScope.ROOT_CAUSE_A_SCOPED
        ):
            return None
        return 0.5

    monkeypatch.setattr(figures_module, "_aggregate_metric_mean", aggregate_mean)
    annotations: list[str] = []

    def capture_rendered_annotations(self: Figure, destination: Path, *, dpi: int) -> None:
        del dpi
        annotations.extend(text.get_text() for axis in self.axes for text in axis.texts)
        Path(destination).write_bytes(b"figure fixture")

    monkeypatch.setattr(Figure, "savefig", capture_rendered_annotations)
    destination = tmp_path / "capability.png"

    assert render_capability_granularity_boundary((), destination, outcomes) == destination
    assert ReportCellLiteral.NOT_AVAILABLE in annotations


def test_secondary_generalization_figure_retains_inconclusive_comparison_as_na(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    definitions = tuple(
        item
        for item in build_comparison_registry()
        if item.experiment == SECONDARY_DATASET_GENERALIZATION_NAME
        and item.metric is ComparisonMetric.TARGET_F1
    )
    definition = definitions[0]
    inconclusive = ComparisonResult(
        definition=definition,
        paired_differences=(),
        complete_seed_count=0,
        mean_paired_difference=None,
        median_paired_difference=None,
        paired_standardized_effect=None,
        raw_p_value=None,
        adjusted_p_value=None,
        confidence_interval=None,
        materiality_passes=None,
        comparison_state=ComparisonState.INCONCLUSIVE_TECHNICAL,
    )
    annotations: list[str] = []
    labels: list[str] = []

    def capture_rendered_annotations(self: Figure, destination: Path, *, dpi: int) -> None:
        del dpi
        annotations.extend(text.get_text() for axis in self.axes for text in axis.texts)
        labels.extend(label.get_text() for axis in self.axes for label in axis.get_yticklabels())
        Path(destination).write_bytes(b"figure fixture")

    monkeypatch.setattr(Figure, "savefig", capture_rendered_annotations)
    destination = tmp_path / "generalization.png"

    assert (
        render_secondary_generalization(
            (ComparisonFamilyResult(family=definition.family, comparisons=(inconclusive,)),),
            destination,
        )
        == destination
    )
    assert ReportCellLiteral.NOT_AVAILABLE in annotations
    expected_labels = [
        f"{item.scientific_scenario}\n{item.method} vs {item.reference_method}"
        for item in definitions
    ]
    assert labels == expected_labels


def test_collapse_figure_keeps_every_preregistered_experiment_and_marks_na(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    definition = next(
        item
        for item in build_comparison_registry()
        if item.experiment in COLLAPSE_EXPERIMENT_NAMES and item.material_threshold is not None
    )
    inconclusive = ComparisonResult(
        definition=definition,
        paired_differences=(),
        complete_seed_count=0,
        mean_paired_difference=None,
        median_paired_difference=None,
        paired_standardized_effect=None,
        raw_p_value=None,
        adjusted_p_value=None,
        confidence_interval=None,
        materiality_passes=None,
        comparison_state=ComparisonState.INCONCLUSIVE_TECHNICAL,
    )
    observed_labels: tuple[str, ...] = ()
    observed_annotations: list[str] = []

    def capture_rendered_figure(figure: Figure, destination: Path, *, dpi: int) -> None:
        nonlocal observed_labels
        del dpi
        observed_labels = tuple(label.get_text() for label in figure.axes[0].get_yticklabels())
        observed_annotations.extend(text.get_text() for axis in figure.axes for text in axis.texts)
        Path(destination).write_bytes(b"figure fixture")

    monkeypatch.setattr(Figure, "savefig", capture_rendered_figure)
    destination = tmp_path / "collapse.png"

    assert (
        render_collapse_decision_effects(
            (ComparisonFamilyResult(family=definition.family, comparisons=(inconclusive,)),),
            destination,
        )
        == destination
    )
    assert observed_labels == tuple(COLLAPSE_EXPERIMENT_NAMES)
    assert ReportCellLiteral.NOT_AVAILABLE in observed_annotations


def test_project_efficiency_telemetry_reads_persisted_aggregate_timings(
    isolated_repository: Path,
) -> None:
    outcome = CellExecutionOutcome(
        cell=ScientificCell(
            experiment=EFFICIENCY_MEASUREMENT_NAME,
            method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
            condition="timed",
            master_seed=1103,
            repetition=1,
        ),
        terminal_state=ExperimentLifecycleState.COMPLETED,
        failure=None,
        metrics=(
            ("post-evidence-wall-clock-seconds", 3.0),
            ("communication-bytes", 11.0),
            ("peak-gpu-memory-bytes", 22.0),
        ),
    )
    result = ExperimentExecutionResult(
        experiment=EFFICIENCY_MEASUREMENT_NAME,
        lifecycle_state=ExperimentLifecycleState.COMPLETED,
        outcomes=(outcome,),
        provenance=_record_provenance(),
    )
    _materialize_run_evidence(result)
    assert {
        (observation.metric, observation.median)
        for observation in project_efficiency_telemetry((outcome,))
    } == {
        ("post-evidence-wall-clock-seconds", 3.0),
        ("communication-bytes", 11.0),
        ("peak-gpu-memory-bytes", 22.0),
    }


def test_project_efficiency_telemetry_uses_persisted_type7_quantiles(
    isolated_repository: Path,
) -> None:
    outcomes = tuple(
        CellExecutionOutcome(
            cell=ScientificCell(
                experiment=EFFICIENCY_MEASUREMENT_NAME,
                method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
                condition="timed",
                master_seed=1102 + seed_index,
                repetition=repetition,
            ),
            terminal_state=ExperimentLifecycleState.COMPLETED,
            failure=None,
            metrics=(("post-evidence-wall-clock-seconds", value),),
        )
        for seed_index, seed_start in enumerate((1, 3, 5), start=1)
        for repetition, value in enumerate(range(seed_start, seed_start + 5), start=1)
    )
    result = ExperimentExecutionResult(
        experiment=EFFICIENCY_MEASUREMENT_NAME,
        lifecycle_state=ExperimentLifecycleState.COMPLETED,
        outcomes=outcomes,
        provenance=_record_provenance(),
    )
    _materialize_run_evidence(result)

    (observation,) = project_efficiency_telemetry(outcomes)

    assert observation.median == 5.0
    assert observation.first_quartile == 4.0
    assert observation.third_quartile == 6.0
    assert observation.seed_count == 3


def test_delay_and_efficiency_table_uses_two_stage_efficiency_summary(
    tmp_path: Path,
    isolated_repository: Path,
) -> None:
    outcomes = tuple(
        CellExecutionOutcome(
            cell=ScientificCell(
                experiment=EFFICIENCY_MEASUREMENT_NAME,
                method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
                condition=EfficiencyCondition.TIMED,
                master_seed=1102 + seed_index,
                repetition=repetition,
            ),
            terminal_state=ExperimentLifecycleState.COMPLETED,
            failure=None,
            metrics=(
                ("post-evidence-wall-clock-seconds", float(value)),
                ("gpu-seconds", float(value + 10)),
                ("peak-gpu-memory-bytes", float(value * 1_000_000_000)),
                ("peak-host-rss-bytes", float(value * 1_000_000_000)),
                ("communication-bytes", float(value * 1_000)),
                ("model-transmissions", float(value + 20)),
                ("persistent-storage-bytes", float(value * 1_000_000_000)),
            ),
        )
        for seed_index, seed_start in enumerate((1, 3, 5), start=1)
        for repetition, value in enumerate(range(seed_start, seed_start + 5), start=1)
    )
    result = ExperimentExecutionResult(
        experiment=EFFICIENCY_MEASUREMENT_NAME,
        lifecycle_state=ExperimentLifecycleState.COMPLETED,
        outcomes=outcomes,
        provenance=_record_provenance(),
    )
    _materialize_run_evidence(result)
    table = render_delay_and_efficiency_table((), outcomes, project_efficiency_telemetry(outcomes))
    row = next(
        row
        for row in csv.reader(table.csv_text.splitlines()[1:])
        if row[0] == EFFICIENCY_MEASUREMENT_NAME
    )
    assert row[:3] == [
        "Efficiency Measurement",
        CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
        EfficiencyCondition.TIMED,
    ]
    assert row[8] == "5.00 [4.00,6.00]"
    assert row[9] == "15.00 [14.00,16.00]"

    materialized = materialize_experiment_evidence(
        result,
        tmp_path / "metrics",
        tmp_path / "telemetry",
    )
    aggregate_rows = pandas.read_parquet(materialized.paths[2])
    timing_record = cast(
        dict[str, object],
        cast(Any, aggregate_rows)
        .query("metric == 'post-evidence-wall-clock-seconds'")
        .to_dict(orient="records")[0],
    )
    assert timing_record["observation_count"] == 15
    assert timing_record["seed_count"] == 3
    assert timing_record["median_value"] == 5.0
    assert timing_record["first_quartile"] == 4.0
    assert timing_record["third_quartile"] == 6.0


def test_byte_valued_metrics_render_in_the_declared_unit_and_decimals() -> None:
    gibibyte = float(1024**3)
    assert format_byte_value(gibibyte) == "1.00 GiB"
    assert format_byte_value(2.5 * gibibyte) == "2.50 GiB"
    assert format_byte_value(None) == "NA"


def test_byte_valued_metrics_use_the_byte_formatter_by_metric_name() -> None:
    from fedsira.experiments.definitions import DescriptiveScientificMetric

    gpu_bytes = DescriptiveScientificMetric.PEAK_GPU_MEMORY_BYTES.value
    assert format_metric_value(float(1024**3), gpu_bytes) == "1.00 GiB"
    assert format_metric_value(0.1234, "target-f1") == "0.123"
