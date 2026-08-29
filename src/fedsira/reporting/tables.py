from __future__ import annotations

import csv
from collections.abc import Sequence
from io import StringIO

from fedsira.analysis.claims import ClaimStateResult, FinalClaimState
from fedsira.analysis.comparisons import ComparisonFamilyResult
from fedsira.config.schema import PublicationRoundingConfig
from fedsira.domain.records import FrozenDomainModel, TableName, TextValue
from fedsira.experiments.collapse import CollapseDecision, ResolvedCore
from fedsira.experiments.planning import ExperimentPlan

MANUSCRIPT_TABLE_NAMES: tuple[TableName, ...] = (
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


class RenderedTable(FrozenDomainModel):
    name: TableName
    csv_text: TextValue


def _csv_text(header: Sequence[str], rows: Sequence[Sequence[str]]) -> TextValue:
    buffer = StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue().rstrip("\n")


def format_metric_value(value: float | None, rounding: PublicationRoundingConfig) -> TextValue:
    if value is None:
        return "NA"
    return f"{value:.{rounding.f1_accuracy_rates_decimals}f}"


def format_p_value(value: float | None, rounding: PublicationRoundingConfig) -> TextValue:
    if value is None:
        return "NA"
    if value < rounding.p_value_display_floor:
        return f"<{rounding.p_value_display_floor:.4f}"
    return f"{value:.{rounding.p_value_significant_digits}g}"


def render_experiment_plan_table(plan: ExperimentPlan) -> RenderedTable:
    rows: list[tuple[str, ...]] = []
    for planned in plan.experiments:
        definition = planned.definition
        rows.append(
            (
                definition.name,
                definition.experiment_class.value,
                str(len(definition.methods)),
                str(len(definition.conditions)),
                str(definition.seed_count),
                str(len(planned.cells)),
                definition.claim_family.value if definition.claim_family else "NA",
            )
        )
    return RenderedTable(
        name="Experiment Plan",
        csv_text=_csv_text(
            (
                "experiment",
                "class",
                "methods",
                "conditions",
                "seeds",
                "nominal_run_count",
                "claim_family",
            ),
            rows,
        ),
    )


def render_statistical_summary_table(
    comparison_results: Sequence[ComparisonFamilyResult],
    rounding: PublicationRoundingConfig,
) -> RenderedTable:
    rows: list[tuple[str, ...]] = []
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
            confidence_interval = (
                "NA"
                if comparison.confidence_interval is None
                else (
                    f"[{comparison.confidence_interval[0]:.3f},"
                    f"{comparison.confidence_interval[1]:.3f}]"
                )
            )
            margin = "NA" if definition.margin is None else f"{definition.margin:.3f}"
            materiality = (
                "NA"
                if definition.material_threshold is None
                else f"{definition.material_threshold:.3f}"
            )
            statistical_pass = (
                "pass" if comparison.comparison_state.value == "Passed" else "fail"
            )
            materiality_pass = "pass" if comparison.materiality_passes is not False else "fail"
            rows.append(
                (
                    family.family.value,
                    definition.comparison_identity,
                    definition.metric,
                    definition.orientation.value,
                    margin,
                    str(comparison.complete_seed_count),
                    mean,
                    median,
                    effect,
                    raw_p,
                    adjusted_p,
                    confidence_interval,
                    materiality,
                    statistical_pass,
                    materiality_pass,
                    comparison.comparison_state.value,
                )
            )
    return RenderedTable(
        name="Statistical Summary",
        csv_text=_csv_text(
            (
                "claim",
                "comparison",
                "metric",
                "direction",
                "margin",
                "n_pairs",
                "mean_difference",
                "median_difference",
                "paired_dz",
                "raw_p",
                "holm_p",
                "confidence_interval_95",
                "materiality_threshold",
                "statistical_pass",
                "materiality_pass",
                "final_comparison_state",
            ),
            rows,
        ),
    )


def render_claim_support_table(claim_states: Sequence[ClaimStateResult]) -> RenderedTable:
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
    rows: list[tuple[str, ...]] = []
    for state in claim_states:
        if state.state not in known_states:
            raise ValueError(f"unknown claim state {state.state}")
        rows.append((state.claim_id, state.scope, state.state.value))
    return RenderedTable(
        name="Claim Support",
        csv_text=_csv_text(("claim", "exact_scoped_claim", "claim_state"), rows),
    )


def render_collapse_decisions_table(
    decisions: Sequence[CollapseDecision],
    resolved_core: ResolvedCore,
    rounding: PublicationRoundingConfig,
) -> RenderedTable:
    rows: list[tuple[str, ...]] = []
    for decision in decisions:
        p_value = format_p_value(decision.adjusted_p_value, rounding)
        constraint = "pass" if decision.constraint_passes else "fail"
        outcome = "survives" if decision.survives else "removed"
        rows.append(
            (
                decision.kind.value,
                decision.primary_material_effect or "NA",
                p_value,
                constraint,
                "mechanical",
                outcome,
                outcome,
            )
        )
    source_influence = (
        "source-excluded" if resolved_core.direct_source_exclusion_survives else "source-influenced"
    )
    rows.append(
        (
            "resolved core",
            resolved_core.resolved_core_identity,
            "NA",
            source_influence,
            "mapping",
            "NA",
            resolved_core.production_update_rule,
        )
    )
    return RenderedTable(
        name="Collapse Decisions",
        csv_text=_csv_text(
            (
                "mechanism",
                "primary_material_effect",
                "adjusted_p",
                "liveness_safety_constraint",
                "survival_rule",
                "observed_outcome",
                "core_action",
            ),
            rows,
        ),
    )
