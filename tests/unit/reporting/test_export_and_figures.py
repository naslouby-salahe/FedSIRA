import csv
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pandas
import pytest
from matplotlib.figure import Figure

from fedsira.artifacts.paths import artifact_slot_directory
from fedsira.artifacts.store import read_current_artifact
from fedsira.config import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import (
    AdmissionOpeningMode,
    AdmissionState,
    BaselineIdentity,
    CapabilityContractScope,
    ComparisonMetric,
    CoreMethodIdentity,
    DatasetId,
    ExperimentLifecycleState,
    MetricObservationKey,
    OpeningMode,
    PrimaryScenario,
    RootCauseMixture,
    SourceExclusionMethod,
)
from fedsira.domain.models import (
    ScientificCell,
)
from fedsira.domain.types import (
    ArtifactDigest,
    MasterSeed,
    RelativePathText,
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
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
)
from fedsira.experiments.engine import (
    AdmissionStateObservation,
    CellExecutionOutcome,
    ExecutionProvenance,
    ExecutionRecordStore,
    ExperimentExecutionResult,
)
from fedsira.experiments.planning import (
    build_plan,
)
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
    EfficiencyMetricObservation,
    EvidenceStateFraction,
    render_capability_granularity_boundary,
    render_evidence_arrival_trajectory,
    render_protocol_schematic,
    render_security_utility_tradeoff,
    render_useful_backdoored_source,
    validate_mandatory_figures_covered,
)
from fedsira.reporting.protocol_tables import render_experiment_plan_table
from fedsira.reporting.publication import (
    read_table_figure_export,
    table_figure_source_data_slot,
)
from fedsira.reporting.tables import (
    format_byte_value,
    format_metric_value,
    format_p_value,
    render_delay_and_efficiency_table,
    render_experiment_cell_metrics_table,
    render_primary_results_table,
)
from fedsira.reporting.verification import (
    CompletenessVerificationResult,
    ExperimentLifecycleRecord,
)
from fedsira.runtime import (
    REPOSITORY_ROOT,
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
    return result.model_copy(
        update={
            "comparison_results": (
                ComparisonFamilyResult(family=definitions[0].family, comparisons=comparisons),
            ),
            "provenance": result.provenance or _record_provenance(),
        }
    )


def _published_source_data_identity(result: ExperimentExecutionResult) -> ArtifactDigest:
    slot = table_figure_source_data_slot(result.experiment)
    current = read_current_artifact(REPOSITORY_ROOT / artifact_slot_directory(slot))
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


def test_capability_granularity_boundary_uses_completed_outcome_evidence(tmp_path: Path) -> None:
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
    destination = tmp_path / "Capability-Granularity Boundary.png"
    assert render_capability_granularity_boundary((), destination, (outcome,)) == destination
    assert destination.is_file()


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
    tmp_path: Path,
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
    with pytest.raises(ValueError, match="missing comparison evidence"):
        export_experiment_report(result, tmp_path)


def test_export_experiment_report_blocks_efficiency_figure_without_repeated_telemetry(
    tmp_path: Path,
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
    with pytest.raises(ValueError, match="missing timing and resource telemetry"):
        export_experiment_report(result, tmp_path)


def test_experiment_evidence_verification_rejects_missing_metric_artifact(tmp_path: Path) -> None:
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
    export_experiment_report(_with_primary_comparison_evidence(result), tmp_path)
    (tmp_path / "metrics" / "primary" / CELL_METRICS_PARQUET_NAME).unlink()
    verification = verify_experiment_artifacts(
        result,
        tmp_path / "tables" / "main",
        tmp_path / "figures" / "main",
        tmp_path / "metrics" / "primary",
        tmp_path / "metrics" / "primary" / "summary.json",
        _published_source_data_identity(result),
        tmp_path,
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
    export_experiment_report(result, experiment_root)
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


def test_experiment_evidence_verification_rejects_wrong_summary_identity(tmp_path: Path) -> None:
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
    export_experiment_report(_with_primary_comparison_evidence(result), tmp_path)
    summary_path = tmp_path / "metrics" / "primary" / "summary.json"
    summary = ExperimentReportSummary.model_validate_json(summary_path.read_text())
    summary_path.write_text(
        summary.model_copy(update={"experiment": EFFICIENCY_MEASUREMENT_NAME}).model_dump_json()
    )
    verification = verify_experiment_artifacts(
        result,
        tmp_path / "tables" / "main",
        tmp_path / "figures" / "main",
        tmp_path / "metrics" / "primary",
        summary_path,
        _published_source_data_identity(result),
        tmp_path,
        _published_exported_paths(result),
    )
    assert not verification.passed
    assert any("belongs to another experiment" in failure for failure in verification.failures)


def test_experiment_evidence_verification_rejects_stale_summary_digest(tmp_path: Path) -> None:
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
    export_experiment_report(_with_primary_comparison_evidence(result), tmp_path)
    summary_path = tmp_path / "metrics" / "primary" / "summary.json"
    summary = ExperimentReportSummary.model_validate_json(summary_path.read_text())
    summary_path.write_text(
        summary.model_copy(update={"execution_digest": "0" * 64}).model_dump_json()
    )
    verification = verify_experiment_artifacts(
        result,
        tmp_path / "tables" / "main",
        tmp_path / "figures" / "main",
        tmp_path / "metrics" / "primary",
        summary_path,
        _published_source_data_identity(result),
        tmp_path,
        _published_exported_paths(result),
    )
    assert not verification.passed
    assert any("execution digest is stale" in failure for failure in verification.failures)


def test_experiment_evidence_verification_rejects_empty_required_table(tmp_path: Path) -> None:
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
    export_experiment_report(_with_primary_comparison_evidence(result), tmp_path)
    table_path = tmp_path / "tables" / "main" / "Cell Metrics.csv"
    table_path.write_text("")
    verification = verify_experiment_artifacts(
        result,
        tmp_path / "tables" / "main",
        tmp_path / "figures" / "main",
        tmp_path / "metrics" / "primary",
        tmp_path / "metrics" / "primary" / "summary.json",
        _published_source_data_identity(result),
        tmp_path,
        _published_exported_paths(result),
    )
    assert not verification.passed
    assert any(
        "Cell Metrics: rendered table is empty" in failure for failure in verification.failures
    )


def test_experiment_evidence_verification_rejects_empty_required_figure(tmp_path: Path) -> None:
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
    export_experiment_report(_with_primary_comparison_evidence(result), tmp_path)
    figure_path = tmp_path / "figures" / "main" / "FedSIRA Protocol Schematic.png"
    figure_path.write_bytes(b"")
    verification = verify_experiment_artifacts(
        result,
        tmp_path / "tables" / "main",
        tmp_path / "figures" / "main",
        tmp_path / "metrics" / "primary",
        tmp_path / "metrics" / "primary" / "summary.json",
        _published_source_data_identity(result),
        tmp_path,
        _published_exported_paths(result),
    )
    assert not verification.passed
    assert any(
        "required figure FedSIRA Protocol Schematic" in failure for failure in verification.failures
    )


def test_primary_results_uses_observed_outcome_metrics_for_method_summaries() -> None:
    table = render_primary_results_table(
        (),
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
        ),
    )
    row = next(csv.reader((table.csv_text.splitlines()[1],)))
    assert row[2] == "0.800 ± 0.000"
    assert row[3] == "[0.800,0.800]"
    assert row[4] == "0.020 ± 0.000"
    assert row[7] == "0.000 ± 0.000"
    assert row[10] == "1"


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

    def capture_figure(figure: Figure, *_args: object, **_kwargs: object) -> None:
        observed_labels.extend(
            tuple(label.get_text() for label in axis.get_yticklabels()) for axis in figure.axes
        )

    monkeypatch.setattr(Figure, "savefig", capture_figure)
    destination = tmp_path / "tradeoff.png"
    render_security_utility_tradeoff(
        (
            ComparisonFamilyResult(
                family=primary[0].family,
                comparisons=(
                    *(result_for(definition) for definition in primary),
                    result_for(second_primary_target),
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
    assert len(target_labels) == 2
    assert any(str(primary[0].scientific_scenario) in label for label in target_labels)
    assert any(str(second_primary_target.scientific_scenario) in label for label in target_labels)
    assert all(str(primary[0].reference_method) in label for label in target_labels)
    assert all(str(unrelated.experiment) not in label for label in target_labels)


def test_render_useful_backdoored_source_uses_completed_outcome_metrics(tmp_path: Path) -> None:
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
    path = render_useful_backdoored_source((), destination, (outcome,))
    assert path.exists()


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
        ),
        provenance=_record_provenance(),
    )
    materialized = materialize_experiment_evidence(
        result,
        tmp_path / "metrics",
        tmp_path / "telemetry",
    )
    cell_rows = pandas.read_parquet(materialized.paths[0])
    aggregate_rows = pandas.read_parquet(materialized.paths[2])
    assert cell_rows.loc[0, "dataset"] == DatasetId.N_BAIOT
    assert cell_rows.loc[0, "cell_semantic_key"] == cell.semantic_key
    assert cell_rows.loc[0, "configuration_digest"] == "a" * 64
    assert cell_rows.loc[0, "dataset_manifest_hash"] == "b" * 64
    assert cell_rows.loc[0, "scoring_artifact_ids"] == ["c" * 64]
    assert aggregate_rows.loc[0, "source_observation_ids"] == [cell_rows.loc[0, "observation_id"]]
    assert aggregate_rows.loc[0, "source_cell_semantic_keys"] == [cell.semantic_key]


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


def test_project_evidence_trajectory_uses_persisted_cycle_and_terminal_state(
    tmp_path: Path,
) -> None:
    store = ExecutionRecordStore(tmp_path)
    store.write_outcome(
        CellExecutionOutcome(
            cell=ScientificCell(
                experiment=EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
                method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
                condition="Immediate Quorum",
                master_seed=1103,
            ),
            terminal_state=ExperimentLifecycleState.COMPLETED,
            failure=None,
            state_trajectory=(
                AdmissionStateObservation(cycle=0, state=AdmissionState.DORMANT),
                AdmissionStateObservation(cycle=2, state=AdmissionState.ADMITTED),
            ),
        ),
        _record_provenance(),
    )
    trajectory = project_evidence_trajectory(store)
    assert {(item.cycle, item.state.value, item.fraction) for item in trajectory} >= {
        (0, "Dormant", 1.0),
        (2, "Admitted", 1.0),
    }


def test_evidence_arrival_trajectory_preserves_expired_state(tmp_path: Path) -> None:
    destination = tmp_path / "trajectory.png"
    states = (
        EvidenceStateFraction(
            condition="Permanent Singleton",
            cycle=0,
            state=AdmissionState.DORMANT,
            fraction=1.0,
        ),
        EvidenceStateFraction(
            condition="Permanent Singleton",
            cycle=1,
            state=AdmissionState.EXPIRED,
            fraction=1.0,
        ),
    )

    assert render_evidence_arrival_trajectory(states, destination) == destination
    assert destination.is_file()


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


def test_project_efficiency_telemetry_aggregates_completed_outcome_timings() -> None:
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
    assert {
        (observation.metric, observation.median)
        for observation in project_efficiency_telemetry((outcome,))
    } == {
        ("post-evidence-wall-clock-seconds", 3.0),
        ("communication-bytes", 11.0),
        ("peak-gpu-memory-bytes", 22.0),
    }


def test_project_efficiency_telemetry_uses_canonical_type7_quantiles() -> None:
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

    (observation,) = project_efficiency_telemetry(outcomes)

    assert observation.median == 5.0
    assert observation.first_quartile == 4.0
    assert observation.third_quartile == 6.0
    assert observation.seed_count == 3


def test_delay_and_efficiency_table_uses_unique_outcome_evidence_rows() -> None:
    outcomes = (
        CellExecutionOutcome(
            cell=ScientificCell(
                experiment=EFFICIENCY_MEASUREMENT_NAME,
                method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
                condition="Efficiency",
                master_seed=1103,
            ),
            terminal_state=ExperimentLifecycleState.COMPLETED,
            failure=None,
            metrics=(
                ("post-evidence-wall-clock-seconds", 3.0),
                ("peak-gpu-memory-bytes", 10.0),
                ("peak-host-rss-bytes", 20.0),
                ("communication-bytes", 30.0),
                ("model-transmissions", 40.0),
            ),
        ),
    )
    table = render_delay_and_efficiency_table((), outcomes)
    row = next(csv.reader((table.csv_text.splitlines()[1],)))
    assert row[:3] == [
        "Efficiency Measurement",
        CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
        "Efficiency",
    ]
    assert row[8] == "3.00 [3.00,3.00]"
    assert row[10] == "0.00 GiB"
    assert row[11] == "0.00 GiB"
    assert row[12] == "0.00 GiB"
    assert row[13] == "40.000"


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
