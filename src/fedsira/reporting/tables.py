from __future__ import annotations

from collections.abc import Sequence

from fedsira.analysis.claims import ClaimStateResult, FinalClaimState
from fedsira.analysis.comparisons import ComparisonFamilyResult
from fedsira.config.schema import PublicationRoundingConfig
from fedsira.domain.records import CanonicalToken
from fedsira.experiments.collapse import CollapseDecision, ResolvedCore
from fedsira.experiments.planning import ExperimentPlan

MANUSCRIPT_TABLE_NAMES: tuple[CanonicalToken, ...] = (
    "Dataset and Domain Protocol",
    "Primary Domain Statistics",
    "Model and Training Protocol",
    "Security and Capability-Contract Protocol",
    "Baseline Protocol",
    "Experiment Plan",
    "Metric and Statistics Protocol",
    "Primary Results",
    "Source-Exclusion Results",
    "Collapse Decisions",
    "Ablation Results",
    "Byzantine Robustness",
    "Failure Boundaries",
    "Delay and Efficiency",
    "Generalization Results",
    "Statistical Summary",
    "Claim Support",
)


def format_metric_value(value: float | None, rounding: PublicationRoundingConfig) -> str:
    if value is None:
        return "NA"
    return f"{value:.{rounding.f1_accuracy_rates_decimals}f}"


def format_p_value(value: float | None, rounding: PublicationRoundingConfig) -> str:
    if value is None:
        return "NA"
    if value < rounding.p_value_display_floor:
        return f"<{rounding.p_value_display_floor:.4f}"
    return f"{value:.{rounding.p_value_significant_digits}g}"


def render_experiment_plan_table(plan: ExperimentPlan) -> str:
    header = (
        "| experiment | class | methods | conditions | seeds | nominal run count | claim family |"
    )
    separator = "| --- | --- | --- | --- | ---: | ---: | --- |"
    rows: list[str] = []
    for planned in plan.experiments:
        definition = planned.definition
        rows.append(
            f"| {definition.name} | {definition.experiment_class.value} | "
            f"{len(definition.methods)} | {len(definition.conditions)} | "
            f"{definition.seed_count} | {len(planned.cells)} | "
            f"{definition.claim_family if definition.claim_family else '—'} |"
        )
    return "\n".join((header, separator, *rows))


def render_statistical_summary_table(
    comparison_results: Sequence[ComparisonFamilyResult],
    rounding: PublicationRoundingConfig,
) -> str:
    header = (
        "| claim | comparison | metric | direction | margin | n pairs | mean difference | "
        "median difference | paired dz | raw p | Holm p | 95% CI | materiality threshold | "
        "statistical pass | materiality pass | final comparison state |"
    )
    separator = (
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | "
        "---: | --- | --- | --- |"
    )
    rows: list[str] = []
    for family in comparison_results:
        for comparison in family.comparisons:
            definition = comparison.definition
            mean = format_metric_value(comparison.mean_paired_difference, rounding)
            median = format_metric_value(comparison.median_paired_difference, rounding)
            effect = (
                "NA"
                if comparison.paired_standardized_effect is None
                else f"{comparison.paired_standardized_effect:.3f}"
            )
            raw_p = format_p_value(comparison.raw_p_value, rounding)
            adjusted_p = format_p_value(comparison.adjusted_p_value, rounding)
            ci = (
                "NA"
                if comparison.confidence_interval is None
                else (
                    f"[{comparison.confidence_interval[0]:.3f}, "
                    f"{comparison.confidence_interval[1]:.3f}]"
                )
            )
            margin = "—" if definition.margin is None else f"{definition.margin:.3f}"
            materiality = (
                "—"
                if definition.material_threshold is None
                else f"{definition.material_threshold:.3f}"
            )
            statistical_pass = "pass" if comparison.comparison_state == "Passed" else "fail"
            materiality_pass = "pass" if comparison.materiality_passes is not False else "fail"
            rows.append(
                f"| {family.family.value} | {definition.canonical_name} | "
                f"{definition.metric} | {definition.orientation.value} | {margin} | "
                f"{comparison.complete_seed_count} | {mean} | {median} | {effect} | "
                f"{raw_p} | {adjusted_p} | {ci} | {materiality} | "
                f"{statistical_pass} | {materiality_pass} | "
                f"{comparison.comparison_state} |"
            )
    return "\n".join((header, separator, *rows))


def render_claim_support_table(claim_states: Sequence[ClaimStateResult]) -> str:
    header = "| claim | exact scoped claim | claim state |"
    separator = "| --- | --- | --- |"
    known_states = frozenset(
        {
            FinalClaimState.SUPPORTED,
            FinalClaimState.PARTIALLY_SUPPORTED,
            FinalClaimState.CONDITIONAL,
            FinalClaimState.MECHANISM_ONLY,
            FinalClaimState.NULL_RESULT,
            FinalClaimState.NOT_SUPPORTED,
            FinalClaimState.NOT_TESTED,
        }
    )
    rows: list[str] = []
    for state in claim_states:
        if state.state not in known_states:
            raise ValueError(f"unknown claim state {state.state}")
        rows.append(f"| {state.claim_id} | {state.scope} | {state.state.value} |")
    return "\n".join((header, separator, *rows))


def render_collapse_decisions_table(
    decisions: Sequence[CollapseDecision],
    resolved_core: ResolvedCore,
    rounding: PublicationRoundingConfig,
) -> str:
    header = (
        "| mechanism | primary material effect | adjusted p | liveness/safety constraint | "
        "survival rule | observed outcome | core action |"
    )
    separator = "| --- | --- | ---: | --- | --- | --- | --- |"
    rows: list[str] = []
    for decision in decisions:
        p_value = "NA" if decision.adjusted_p_value is None else f"{decision.adjusted_p_value:.4f}"
        constraint = "pass" if decision.constraint_passes else "fail"
        outcome = "survives" if decision.survives else "removed"
        rows.append(
            f"| {decision.kind.value} | "
            f"{decision.primary_material_effect or 'NA'} | {p_value} | "
            f"{constraint} | mechanical | {outcome} | {outcome} |"
        )
    source_influence = (
        "source-excluded" if resolved_core.direct_source_exclusion_survives else "source-influenced"
    )
    rows.append(
        f"| resolved core | {resolved_core.identity_token} | — | "
        f"{source_influence} | mapping | — | {resolved_core.production_update_rule} |"
    )
    return "\n".join((header, separator, *rows))
