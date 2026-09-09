import csv
from pathlib import Path

import pytest

from fedsira.config import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import (
    AdmissionOpeningMode,
    CoreMethodIdentity,
    ExperimentLifecycleState,
    RootCauseMixture,
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
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    PrimaryScenario,
)
from fedsira.experiments.execution import CellExecutionOutcome, ExecutionRecordStore
from fedsira.experiments.planning import ScientificCell, build_plan
from fedsira.reporting.export import (
    ReportExportResult,
    export_project_summary,
)
from fedsira.reporting.figures import (
    MANDATORY_FIGURE_NAMES,
    render_capability_granularity_boundary,
    render_protocol_schematic,
    render_security_utility_tradeoff,
    render_useful_backdoored_source,
    validate_mandatory_figures_covered,
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
from fedsira.workflows.report import (
    project_efficiency_telemetry,
    project_evidence_trajectory,
)

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)


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
        metrics=(("false-same-capability-rate", 0.25),),
    )
    destination = tmp_path / "Capability-Granularity Boundary.png"
    assert render_capability_granularity_boundary((), destination, (outcome,)) == destination
    assert destination.is_file()


def test_render_experiment_plan_table_is_csv() -> None:
    plan = build_plan()
    table = render_experiment_plan_table(plan)
    lines = table.csv_text.splitlines()
    assert table.name == "Experiment Plan"
    assert (
        lines[0] == "experiment,class,methods,conditions,seeds,nominal_run_count,comparison_family"
    )
    assert len(lines) - 1 == len(plan.experiments)


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
            survives=True,
            primary_material_effect="false-launch",
            adjusted_p_value=0.01,
            constraint_passes=True,
            reason="mechanical collapse rule",
        ),
        CollapseDecision(
            kind=CollapseDecisionKind.PLURALITY,
            survives=True,
            primary_material_effect="malicious-admission",
            adjusted_p_value=0.02,
            constraint_passes=True,
            reason="mechanical collapse rule",
        ),
        CollapseDecision(
            kind=CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION,
            survives=True,
            primary_material_effect="asr",
            adjusted_p_value=0.03,
            constraint_passes=True,
            reason="mechanical collapse rule",
        ),
        CollapseDecision(
            kind=CollapseDecisionKind.EXTERNAL_VERIFICATION,
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
    monkeypatch.setattr("fedsira.reporting.export._results_root", lambda: tmp_path)


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
    )
    assert isinstance(result, ReportExportResult)
    assert not result.exported_paths
    assert not result.verification.passed
    assert any("Primary Results" in failure for failure in result.verification.failures)
    assert any("Statistical Summary" in failure for failure in result.verification.failures)


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
    )
    assert not result.exported_paths
    assert not result.verification.passed


def test_render_security_utility_tradeoff_empty_is_no_evidence(tmp_path: Path) -> None:
    destination = tmp_path / "tradeoff.png"
    path = render_security_utility_tradeoff((), destination)
    assert path.exists()


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
            ("attack-success-rate", 0.1),
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
                experiment=ADMISSION_DELAY_DECOMPOSITION_NAME,
                method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
                condition="Immediate Quorum",
                master_seed=1103,
            ),
            terminal_state=ExperimentLifecycleState.COMPLETED,
            failure=None,
            metrics=(("terminal-state", 1.0), ("evidence-arrival-cycle", 2.0)),
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
            experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
            method="Resolved FedSIRA Core",
            condition="Legitimate Unsupported Capability",
            master_seed=1103,
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
        (observation.metric, observation.value)
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
    assert row[:2] == ["Resolved FedSIRA Core", "Efficiency"]
    assert row[7] == "3.00 [3.00,3.00]"
    assert row[10:14] == ["10.000", "20.000", "30.000", "40.000"]
