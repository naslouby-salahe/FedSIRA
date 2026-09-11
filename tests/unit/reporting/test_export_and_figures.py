import csv
from pathlib import Path

import pytest

from fedsira.config import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import (
    AdmissionOpeningMode,
    AdmissionState,
    CoreMethodIdentity,
    ExperimentLifecycleState,
    RootCauseMixture,
)
from fedsira.evaluation.comparisons import (
    ComparisonFamilyResult,
    ComparisonMetric,
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
    PrimaryScenario,
)
from fedsira.experiments.execution import (
    AdmissionStateObservation,
    CellExecutionOutcome,
    ExecutionRecordStore,
    ExperimentExecutionResult,
)
from fedsira.experiments.planning import ScientificCell, build_plan
from fedsira.reporting.export import (
    ExperimentReportSummary,
    ReportExportResult,
    export_experiment_report,
    export_project_summary,
    project_efficiency_telemetry,
    project_evidence_trajectory,
    verify_experiment_artifacts,
)
from fedsira.reporting.figures import (
    MANDATORY_FIGURE_NAMES,
    EvidenceStateFraction,
    render_capability_granularity_boundary,
    render_protocol_schematic,
    render_security_utility_tradeoff,
    render_useful_backdoored_source,
    validate_mandatory_figures_covered,
)
from fedsira.reporting.materialization import (
    CELL_METRICS_PARQUET_NAME,
)
from fedsira.reporting.tables import (
    format_metric_value,
    format_p_value,
    render_delay_and_efficiency_table,
    render_experiment_plan_table,
    render_primary_results_table,
)
from fedsira.reporting.verification import (
    CompletenessVerificationResult,
    ExperimentLifecycleRecord,
)

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)


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
            )
        }
    )


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
            method="Broad Target Only",
            condition=RootCauseMixture.BALANCED_50_50.value,
            master_seed=1103,
        ),
        terminal_state=ExperimentLifecycleState.COMPLETED,
        failure=None,
        metrics=(
            ("false-same-capability-rate", 0.25),
            ("root-cause-a-target-f1", 0.7),
            ("root-cause-b-target-f1", 0.6),
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
        outcomes=(
            CellExecutionOutcome(
                cell=ScientificCell(
                    experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                    method="Resolved FedSIRA Core",
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
        outcomes=(
            CellExecutionOutcome(
                cell=ScientificCell(
                    experiment=EFFICIENCY_MEASUREMENT_NAME,
                    method="Resolved FedSIRA Core",
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
                    method="Resolved FedSIRA Core",
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
    )
    assert not verification.passed
    assert any(CELL_METRICS_PARQUET_NAME in failure for failure in verification.failures)


def test_experiment_evidence_verification_rejects_wrong_summary_identity(tmp_path: Path) -> None:
    result = ExperimentExecutionResult(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        lifecycle_state=ExperimentLifecycleState.COMPLETED,
        outcomes=(
            CellExecutionOutcome(
                cell=ScientificCell(
                    experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                    method="Resolved FedSIRA Core",
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
                    method="Resolved FedSIRA Core",
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
                    method="Resolved FedSIRA Core",
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
                    method="Resolved FedSIRA Core",
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
                    method="Resolved FedSIRA Core",
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


def _collapse_decisions() -> tuple[CollapseDecision, ...]:
    return (
        CollapseDecision(
            kind=CollapseDecisionKind.PROPOSAL_ASSISTANCE,
            comparator="Candidate-Free",
            survives=True,
            primary_material_effect="false-launch",
            adjusted_p_value=0.01,
            constraint_passes=True,
            reason="mechanical collapse rule",
        ),
        CollapseDecision(
            kind=CollapseDecisionKind.PLURALITY,
            comparator="One Independent Retrain",
            survives=True,
            primary_material_effect="malicious-admission",
            adjusted_p_value=0.02,
            constraint_passes=True,
            reason="mechanical collapse rule",
        ),
        CollapseDecision(
            kind=CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION,
            comparator="Source-Update Sanitization Reference",
            survives=True,
            primary_material_effect="asr",
            adjusted_p_value=0.03,
            constraint_passes=True,
            reason="mechanical collapse rule",
        ),
        CollapseDecision(
            kind=CollapseDecisionKind.EXTERNAL_VERIFICATION,
            comparator="Multiple Retrains with Direct Krum",
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
            method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
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


def test_render_useful_backdoored_source_uses_completed_outcome_metrics(tmp_path: Path) -> None:
    destination = tmp_path / "source-exclusion.png"
    outcome = CellExecutionOutcome(
        cell=ScientificCell(
            experiment=SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
            method="Full FedSIRA",
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


def test_project_evidence_trajectory_uses_persisted_cycle_and_terminal_state(
    tmp_path: Path,
) -> None:
    store = ExecutionRecordStore(tmp_path)
    store.write_outcome(
        CellExecutionOutcome(
            cell=ScientificCell(
                experiment=EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
                method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
                condition="Immediate Quorum",
                master_seed=1103,
            ),
            terminal_state=ExperimentLifecycleState.COMPLETED,
            failure=None,
            state_trajectory=(
                AdmissionStateObservation(cycle=0, state=AdmissionState.DORMANT),
                AdmissionStateObservation(cycle=2, state=AdmissionState.ADMITTED),
            ),
        )
    )
    trajectory = project_evidence_trajectory(store)
    assert {(item.cycle, item.state.value, item.fraction) for item in trajectory} >= {
        (0, "Dormant", 1.0),
        (2, "Admitted", 1.0),
    }


def test_project_efficiency_telemetry_aggregates_completed_outcome_timings() -> None:
    outcome = CellExecutionOutcome(
        cell=ScientificCell(
            experiment=EFFICIENCY_MEASUREMENT_NAME,
            method="Resolved FedSIRA Core",
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


def test_delay_and_efficiency_table_uses_unique_outcome_evidence_rows() -> None:
    outcomes = (
        CellExecutionOutcome(
            cell=ScientificCell(
                experiment=EFFICIENCY_MEASUREMENT_NAME,
                method="Resolved FedSIRA Core",
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
    assert row[:3] == ["Efficiency Measurement", "Resolved FedSIRA Core", "Efficiency"]
    assert row[8] == "3.00 [3.00,3.00]"
    assert row[10] == "10.000"
    assert row[11] == "20.000"
    assert row[12] == "30.000"
    assert row[13] == "40.000"
