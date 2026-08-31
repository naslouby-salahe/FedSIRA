from __future__ import annotations

import csv
from io import StringIO

from fedsira.analysis.claims import ClaimStateResult
from fedsira.analysis.comparisons import (
    ComparisonDefinition,
    ComparisonFamilyResult,
    ComparisonReferenceKind,
    ComparisonResult,
    ComparisonState,
    ComparisonTestKind,
    MaterialityDirection,
)
from fedsira.config.schema import PublicationRoundingConfig
from fedsira.domain.records import (
    FormattedStatisticText,
    FrozenDomainModel,
    MetricValue,
    PValue,
    TableCsvText,
    TableName,
    TextValue,
)
from fedsira.experiments.collapse import (
    CollapseDecision,
    CollapseDecisionKind,
    ProductionUpdateRule,
    ReproductionRowRequirement,
    ResolvedCore,
    RowVerificationMode,
)
from fedsira.experiments.planning import ExperimentPlan
from fedsira.experiments.registry import ExperimentClass

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
    csv_text: TableCsvText


def _csv_text(
    header: tuple[TextValue, ...],
    rows: tuple[tuple[TextValue, ...], ...],
) -> TextValue:
    buffer = StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue().rstrip("\n")


def format_metric_value(
    value: MetricValue | None,
    rounding: PublicationRoundingConfig,
) -> FormattedStatisticText:
    if value is None:
        return "NA"
    return f"{value:.{rounding.f1_accuracy_rates_decimals}f}"


def format_p_value(
    value: PValue | None,
    rounding: PublicationRoundingConfig,
) -> FormattedStatisticText:
    if value is None:
        return "NA"
    if value < rounding.p_value_display_floor:
        return f"<{rounding.p_value_display_floor:.4f}"
    return f"{value:.{rounding.p_value_significant_digits}g}"


def _experiment_class_label(experiment_class: ExperimentClass) -> TextValue:
    return experiment_class.value


def render_experiment_plan_table(plan: ExperimentPlan) -> RenderedTable:
    rows = tuple(
        (
            planned.definition.name,
            _experiment_class_label(planned.definition.experiment_class),
            str(len(planned.definition.methods)),
            str(len(planned.definition.conditions)),
            str(planned.definition.seed_count),
            str(len(planned.cells)),
            (
                planned.definition.claim_family.value
                if planned.definition.claim_family is not None
                else "NA"
            ),
        )
        for planned in plan.experiments
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


def _comparison_reference_label(definition: ComparisonDefinition) -> TextValue:
    if definition.reference_kind is ComparisonReferenceKind.ZERO:
        return ComparisonReferenceKind.ZERO.value
    if (
        definition.reference_experiment == definition.experiment
        and definition.reference_scenario == definition.scientific_scenario
    ):
        return definition.reference_method
    if (
        definition.reference_experiment == definition.experiment
        and definition.reference_method == definition.method
    ):
        return definition.reference_scenario
    return (
        f"{definition.reference_experiment} / "
        f"{definition.reference_scenario} / {definition.reference_method}"
    )


def _statistical_summary_row(
    family: ComparisonFamilyResult,
    comparison: ComparisonResult,
    rounding: PublicationRoundingConfig,
) -> tuple[TextValue, ...]:
    definition = comparison.definition
    effect = (
        "NA"
        if comparison.paired_standardized_effect is None
        else f"{comparison.paired_standardized_effect:.3f}"
    )
    confidence_interval = (
        "NA"
        if comparison.confidence_interval is None
        else (
            f"[{comparison.confidence_interval[0]:.3f}," f"{comparison.confidence_interval[1]:.3f}]"
        )
    )
    margin = "NA" if definition.margin is None else f"{definition.margin:.3f}"
    materiality = (
        "NA" if definition.material_threshold is None else f"{definition.material_threshold:.3f}"
    )
    reference_label = _comparison_reference_label(definition)
    comparison_identity = (
        f"{definition.method} vs {reference_label} | "
        f"{definition.scientific_scenario} | {definition.metric.value}"
    )
    test_kind: ComparisonTestKind = definition.test_kind
    materiality_direction: MaterialityDirection = definition.materiality_direction
    return (
        family.family.value,
        comparison_identity,
        definition.metric.value,
        definition.orientation.value,
        test_kind.value,
        materiality_direction.value,
        margin,
        str(comparison.complete_seed_count),
        format_metric_value(comparison.mean_paired_difference, rounding),
        format_metric_value(comparison.median_paired_difference, rounding),
        effect,
        format_p_value(comparison.raw_p_value, rounding),
        format_p_value(comparison.adjusted_p_value, rounding),
        confidence_interval,
        materiality,
        "pass" if comparison.comparison_state is ComparisonState.PASSED else "fail",
        "pass" if comparison.materiality_passes is not False else "fail",
        comparison.comparison_state.value,
    )


def render_statistical_summary_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    rounding: PublicationRoundingConfig,
) -> RenderedTable:
    rows = tuple(
        _statistical_summary_row(family, comparison, rounding)
        for family in comparison_results
        for comparison in family.comparisons
    )
    return RenderedTable(
        name="Statistical Summary",
        csv_text=_csv_text(
            (
                "claim",
                "comparison",
                "metric",
                "direction",
                "test_kind",
                "materiality_direction",
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


def render_claim_support_table(
    claim_states: tuple[ClaimStateResult, ...],
) -> RenderedTable:
    rows = tuple((state.claim_id, state.scope, state.state.value) for state in claim_states)
    return RenderedTable(
        name="Claim Support",
        csv_text=_csv_text(
            ("claim", "exact_scoped_claim", "claim_state"),
            rows,
        ),
    )


def _decision_kind_label(kind: CollapseDecisionKind) -> TextValue:
    return kind.value


def render_collapse_decisions_table(
    decisions: tuple[CollapseDecision, ...],
    resolved_core: ResolvedCore,
    rounding: PublicationRoundingConfig,
) -> RenderedTable:
    decision_rows = tuple(
        (
            _decision_kind_label(decision.kind),
            decision.primary_material_effect or "NA",
            format_p_value(decision.adjusted_p_value, rounding),
            "pass" if decision.constraint_passes else "fail",
            "mechanical",
            "survives" if decision.survives else "removed",
            "survives" if decision.survives else "removed",
            "NA",
            "NA",
        )
        for decision in decisions
    )
    source_influence = (
        "source-excluded" if resolved_core.direct_source_exclusion_survives else "source-influenced"
    )
    production_update_rule: ProductionUpdateRule = resolved_core.production_update_rule
    row_verification_mode: RowVerificationMode = resolved_core.row_verification_mode
    reproduction_row_requirement: ReproductionRowRequirement = (
        resolved_core.reproduction_row_requirement
    )
    resolved_row = (
        "resolved core",
        resolved_core.decision_identity,
        "NA",
        source_influence,
        "mapping",
        "NA",
        production_update_rule.value,
        row_verification_mode.value,
        reproduction_row_requirement.value,
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
                "row_verification_mode",
                "reproduction_row_requirement",
            ),
            (*decision_rows, resolved_row),
        ),
    )
