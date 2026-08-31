from pathlib import Path

import pytest

from fedsira.analysis.claims import ClaimStateResult, FinalClaimState
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import ClaimOpeningMode, ExperimentLifecycleState
from fedsira.experiments.collapse import (
    CollapseDecision,
    CollapseDecisionKind,
    ProductionUpdateRule,
    ReproductionRowRequirement,
    ResolvedCore,
    RowVerificationMode,
)
from fedsira.experiments.planning import build_plan
from fedsira.reporting.export import (
    ReportExportResult,
    derive_claim_states_for_export,
    export_project_summary,
)
from fedsira.reporting.figures import (
    MANDATORY_FIGURE_NAMES,
    render_protocol_schematic,
    render_security_utility_tradeoff,
    validate_mandatory_figures_covered,
)
from fedsira.reporting.tables import (
    format_metric_value,
    format_p_value,
    render_claim_support_table,
    render_experiment_plan_table,
)
from fedsira.reporting.verification import (
    CompletenessVerificationResult,
    ExperimentLifecycleRecord,
)

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)


def test_format_metric_value_na_and_rounding() -> None:
    rounding = CONFIG.metrics_and_statistics.publication_rounding
    assert format_metric_value(None, rounding) == "NA"
    assert format_metric_value(0.5, rounding) == f"{0.5:.{rounding.f1_accuracy_rates_decimals}f}"


def test_format_p_value_floor_and_rounding() -> None:
    rounding = CONFIG.metrics_and_statistics.publication_rounding
    assert format_p_value(None, rounding) == "NA"
    assert format_p_value(rounding.p_value_display_floor / 2, rounding).startswith("<")
    value = rounding.p_value_display_floor + 0.01
    assert format_p_value(value, rounding) == f"{value:.{rounding.p_value_significant_digits}g}"


def test_render_experiment_plan_table_is_csv() -> None:
    plan = build_plan()
    table = render_experiment_plan_table(plan)
    lines = table.csv_text.splitlines()
    assert table.name == "Experiment Plan"
    assert lines[0] == "experiment,class,methods,conditions,seeds,nominal_run_count,claim_family"
    assert len(lines) - 1 == len(plan.experiments)


def test_render_claim_support_table_uses_typed_state() -> None:
    states = (
        ClaimStateResult(
            claim_id="x",
            state=FinalClaimState.SUPPORTED,
            scope="s",
            reason="r",
        ),
    )
    table = render_claim_support_table(states)
    assert table.name == "Claim Support"
    assert "x,s,Supported" in table.csv_text


def test_derive_claim_states_for_export_no_evidence_is_not_tested() -> None:
    states = derive_claim_states_for_export(())
    assert all(state.state is FinalClaimState.NOT_TESTED for state in states)


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


def test_export_project_summary_records_missing_mandatory_material(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = build_plan(resolved_core_complete=True)
    verification = CompletenessVerificationResult(passed=True, failures=())
    claim_states = derive_claim_states_for_export(())
    _override_results_root(tmp_path, monkeypatch)
    result = export_project_summary(
        plan,
        claim_states,
        _lifecycle_records(),
        verification,
    )
    assert isinstance(result, ReportExportResult)
    assert result.exported_paths
    assert not result.verification.passed
    assert any("mandatory" in failure for failure in result.verification.failures)
    for exported_path in result.exported_paths:
        assert Path(exported_path).exists()


def test_export_project_summary_with_collapse_decisions_records_typed_core(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = build_plan(resolved_core_complete=True)
    verification = CompletenessVerificationResult(passed=True, failures=())
    claim_states = derive_claim_states_for_export(())
    resolved_core = ResolvedCore(
        proposal_assistance_survives=True,
        plurality_survives=True,
        direct_source_exclusion_survives=True,
        external_verification_survives=True,
        opening_mode=ClaimOpeningMode.PROPOSAL_ASSISTED,
        reproduction_row_requirement=ReproductionRowRequirement.FIVE_CERTIFIED_NON_SOURCE_ROWS,
        row_verification_mode=RowVerificationMode.THREE_VERIFIER_TWO_OF_THREE,
        production_update_rule=ProductionUpdateRule.KRUM_CERTIFIED_ROWS,
    )
    _override_results_root(tmp_path, monkeypatch)
    result = export_project_summary(
        plan,
        claim_states,
        _lifecycle_records(),
        verification,
        collapse_decisions=_collapse_decisions(),
        resolved_core=resolved_core,
    )
    assert result.exported_paths
    assert not result.verification.passed


def test_render_security_utility_tradeoff_empty_is_no_evidence(tmp_path: Path) -> None:
    destination = tmp_path / "tradeoff.png"
    path = render_security_utility_tradeoff((), destination)
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
