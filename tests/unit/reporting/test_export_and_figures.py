from pathlib import Path

import pytest

from fedsira.analysis.claims import ClaimStateResult, FinalClaimState
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import ClaimOpeningMode, ExperimentLifecycleState
from fedsira.experiments.collapse import (
    CollapseDecision,
    CollapseDecisionKind,
    ResolvedCore,
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
from fedsira.reporting.verification import CompletenessVerificationResult

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


def test_render_experiment_plan_table_is_markdown() -> None:
    plan = build_plan()
    table = render_experiment_plan_table(plan)
    lines = table.splitlines()
    assert lines[0].startswith("| experiment |")
    assert "| --- |" in lines[1]
    assert len(lines) - 2 == len(plan.experiments)


def test_render_claim_support_table_rejects_unknown_state() -> None:
    states = (
        ClaimStateResult(claim_id="x", state=FinalClaimState.SUPPORTED, scope="s", reason="r"),
    )
    table = render_claim_support_table(states)
    assert "| x | s | Supported |" in table


def test_derive_claim_states_for_export_no_evidence_is_not_tested() -> None:
    states = derive_claim_states_for_export({}, PRODUCTION_CONFIG_PATH)
    assert all(state.state is FinalClaimState.NOT_TESTED for state in states)


def _collapse_decisions() -> list[CollapseDecision]:
    return [
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
    ]


def _override_results_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("fedsira.reporting.export._results_root", lambda: tmp_path)


def test_export_project_summary_materializes_tables_and_figures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = build_plan()
    lifecycle = {
        planned.definition.name: ExperimentLifecycleState.COMPLETED for planned in plan.experiments
    }
    verification = CompletenessVerificationResult(passed=True, failures=())
    claim_states = derive_claim_states_for_export({}, PRODUCTION_CONFIG_PATH)

    _override_results_root(tmp_path, monkeypatch)
    result = export_project_summary(
        plan,
        claim_states,
        lifecycle,
        PRODUCTION_CONFIG_PATH,
        verification,
    )
    assert isinstance(result, ReportExportResult)
    exported_paths = tuple(result.exported_paths)
    assert exported_paths
    for path in exported_paths:
        assert path.exists()


def test_export_project_summary_with_decisions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = build_plan()
    lifecycle = {
        planned.definition.name: ExperimentLifecycleState.COMPLETED for planned in plan.experiments
    }
    verification = CompletenessVerificationResult(passed=True, failures=())
    claim_states = derive_claim_states_for_export({}, PRODUCTION_CONFIG_PATH)
    resolved_core = ResolvedCore(
        proposal_assistance_survives=True,
        plurality_survives=True,
        direct_source_exclusion_survives=True,
        external_verification_survives=True,
        opening_mode=ClaimOpeningMode.PROPOSAL_ASSISTED,
        reproduction_row_requirement="three",
        row_verification_mode="committee",
        production_update_rule="krum",
    )
    _override_results_root(tmp_path, monkeypatch)
    result = export_project_summary(
        plan,
        claim_states,
        lifecycle,
        PRODUCTION_CONFIG_PATH,
        verification,
        collapse_decisions=_collapse_decisions(),
        resolved_core=resolved_core,
    )
    assert result.exported_paths


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
