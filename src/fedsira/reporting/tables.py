from __future__ import annotations

import math

from fedsira.config import PublicationRoundingConfig
from fedsira.domain.enums import CoreMethodIdentity
from fedsira.domain.types import (
    ExperimentName,
    FormattedStatisticText,
    FrozenDomainModel,
    MethodName,
    MetricName,
    MetricValue,
    PValue,
    RowCount,
    ScenarioName,
    TableName,
    TextValue,
)
from fedsira.evaluation.comparisons import (
    ComparisonDefinition,
    ComparisonFamilyResult,
    ComparisonMetric,
    ComparisonReferenceKind,
    ComparisonResult,
    ComparisonState,
    ComparisonTestKind,
    MaterialityDirection,
    ablation_metric,
)
from fedsira.evaluation.summaries import (
    bootstrap_percentile_confidence_interval,
    quantile_type7,
)
from fedsira.experiments.collapse import (
    CollapseDecision,
    CollapseDecisionKind,
    ResolvedCore,
)
from fedsira.experiments.definitions import (
    ADMISSION_DELAY_DECOMPOSITION_NAME,
    BYZANTINE_BOUND_VIOLATION_NAME,
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    CELL_METRICS_TABLE_NAME,
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
    AblationVariant,
    BoundCondition,
    DescriptiveScientificMetric,
    PrimaryScenario,
    SecondaryScenario,
    SourceExclusionMethod,
    ablation_scenario_for_variant,
    experiment_by_name,
)
from fedsira.experiments.execution import CellExecutionOutcome
from fedsira.experiments.planning import ExperimentPlan
from fedsira.reporting.protocol_tables import (
    render_baseline_protocol_table,
    render_dataset_and_domain_protocol_table,
    render_experiment_plan_table,
    render_metric_and_statistics_protocol_table,
    render_model_and_training_protocol_table,
    render_primary_domain_statistics_table,
    render_security_and_capability_contract_protocol_table,
)
from fedsira.reporting.rendering import RenderedTable, render_cell_metrics
from fedsira.reporting.rendering import csv_text as _csv_text
from fedsira.runtime import current_application_context

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
)


def render_experiment_cell_metrics_table(
    outcomes: tuple[CellExecutionOutcome, ...],
) -> RenderedTable:
    return render_cell_metrics(outcomes, CELL_METRICS_TABLE_NAME, format_metric_value)


def _publication_rounding() -> PublicationRoundingConfig:
    statistics = current_application_context().scientific_config.metrics_and_statistics
    return statistics.publication_rounding


def format_metric_value(value: MetricValue | None) -> FormattedStatisticText:
    rounding = _publication_rounding()
    if value is None:
        return "NA"
    return f"{value:.{rounding.f1_accuracy_rates_decimals}f}"


def format_p_value(value: PValue | None) -> FormattedStatisticText:
    rounding = _publication_rounding()
    if value is None:
        return "NA"
    if value < rounding.p_value_display_floor:
        return f"<{rounding.p_value_display_floor:.4f}"
    return f"{value:.{rounding.p_value_significant_digits}g}"


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
        else (f"[{comparison.confidence_interval[0]:.3f},{comparison.confidence_interval[1]:.3f}]")
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
        format_metric_value(comparison.mean_paired_difference),
        format_metric_value(comparison.median_paired_difference),
        effect,
        format_p_value(comparison.raw_p_value),
        format_p_value(comparison.adjusted_p_value),
        confidence_interval,
        materiality,
        "pass" if comparison.comparison_state is ComparisonState.PASSED else "fail",
        "pass" if comparison.materiality_passes is not False else "fail",
        comparison.comparison_state.value,
    )


def render_statistical_summary_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
) -> RenderedTable:
    rows = tuple(
        _statistical_summary_row(family, comparison)
        for family in comparison_results
        for comparison in family.comparisons
    )
    return RenderedTable(
        name="Statistical Summary",
        csv_text=_csv_text(
            (
                "comparison_family",
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


COLLAPSE_SURVIVAL_RULES: tuple[tuple[CollapseDecisionKind, TextValue], ...] = (
    (
        CollapseDecisionKind.PROPOSAL_ASSISTANCE,
        (
            "at least one of false-launch reduction >=0.15, reproduction-attempt "
            "reduction >=25% relative, or post-evidence-overhead reduction >=20% relative "
            "passes Holm-adjusted p<0.05, with legitimate-admission degradation <=0.05 and "
            "malicious-admission worsening <=0.02"
        ),
    ),
    (
        CollapseDecisionKind.PLURALITY,
        (
            "malicious admission decreases by >=0.10 or worst-domain target F1 increases by "
            ">=0.05 with Holm-adjusted p<0.05, legitimate-admission degradation <=0.05, and "
            "supported macro-F1 harm <=0.02"
        ),
    ),
    (
        CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION,
        (
            "post-production ASR decreases by >=0.20 with adjusted p<0.05, target-F1 "
            "non-inferiority within 0.02, and Capability Contract support/FAR constraints"
        ),
    ),
    (
        CollapseDecisionKind.EXTERNAL_VERIFICATION,
        (
            "malicious admission reduction >=0.10 or worst-domain target-F1 increase >=0.05 "
            "with adjusted p<0.05 and legitimate-admission degradation <=0.05"
        ),
    ),
)


def _collapse_survival_rule(kind: CollapseDecisionKind) -> TextValue:
    for registered_kind, rule in COLLAPSE_SURVIVAL_RULES:
        if registered_kind is kind:
            return rule
    raise ValueError(f"unsupported collapse decision kind {kind.value}")


def _collapse_core_action(
    kind: CollapseDecisionKind,
    resolved_core: ResolvedCore,
) -> TextValue:
    if kind is CollapseDecisionKind.PROPOSAL_ASSISTANCE:
        return resolved_core.opening_mode.value
    if kind is CollapseDecisionKind.PLURALITY:
        return resolved_core.reproduction_row_requirement.value
    if kind is CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION:
        return "source-excluded" if resolved_core.source_excluded else "source-influenced"
    if kind is CollapseDecisionKind.EXTERNAL_VERIFICATION:
        return resolved_core.row_verification_mode.value
    raise ValueError(f"unsupported collapse decision kind {kind.value}")


def _collapse_observed_outcome(decision: CollapseDecision) -> TextValue:
    if decision.kind is CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION and not decision.survives:
        return "Central Not Supported"
    return "Survives" if decision.survives else "Removed"


def render_collapse_decisions_table(
    decisions: tuple[CollapseDecision, ...],
    resolved_core: ResolvedCore,
) -> RenderedTable:
    rows = tuple(
        (
            decision.kind.value,
            decision.comparator,
            decision.primary_material_effect or "none",
            format_p_value(decision.adjusted_p_value),
            "pass" if decision.constraint_passes else "fail",
            _collapse_survival_rule(decision.kind),
            _collapse_observed_outcome(decision),
            _collapse_core_action(decision.kind, resolved_core),
        )
        for decision in decisions
    )
    return RenderedTable(
        name="Collapse Decisions",
        csv_text=_csv_text(
            (
                "mechanism",
                "comparator",
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


def _comparison_value(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    experiment: ExperimentName,
    method: MethodName,
    scenario: ScenarioName,
    metric: MetricName,
) -> FormattedStatisticText:
    for family in comparison_results:
        for comparison in family.comparisons:
            definition = comparison.definition
            if (
                definition.experiment == experiment
                and definition.method == method
                and definition.scientific_scenario == scenario
                and definition.metric is metric
            ):
                return format_metric_value(comparison.mean_paired_difference)
    return "NA"


def _comparison_result(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    experiment: ExperimentName,
    method: MethodName,
    scenario: ScenarioName,
    metric: ComparisonMetric,
) -> ComparisonResult | None:
    for family in comparison_results:
        for comparison in family.comparisons:
            definition = comparison.definition
            if (
                definition.experiment == experiment
                and definition.method == method
                and definition.scientific_scenario == scenario
                and definition.metric is metric
            ):
                return comparison
    return None


def _comparison_confidence_interval(comparison: ComparisonResult | None) -> FormattedStatisticText:
    if comparison is None or comparison.confidence_interval is None:
        return "NA"
    return f"[{comparison.confidence_interval[0]:.3f},{comparison.confidence_interval[1]:.3f}]"


def _materiality_text(comparison: ComparisonResult | None) -> FormattedStatisticText:
    if comparison is None or comparison.materiality_passes is None:
        return "NA"
    return "pass" if comparison.materiality_passes else "fail"


def _outcome_metric_values(
    outcomes: tuple[CellExecutionOutcome, ...],
    experiment: ExperimentName,
    method: MethodName,
    scenario: ScenarioName,
    metric: MetricName,
) -> tuple[MetricValue, ...]:
    return tuple(
        value
        for outcome in sorted(outcomes, key=lambda item: item.cell.master_seed)
        if (
            outcome.completed
            and outcome.cell.experiment == experiment
            and outcome.cell.method == method
            and outcome.cell.condition == scenario
        )
        for metric_name, value in outcome.metrics
        if metric_name == metric and value is not None
    )


def _outcome_metric_mean(
    outcomes: tuple[CellExecutionOutcome, ...],
    experiment: ExperimentName,
    method: MethodName,
    scenario: ScenarioName,
    metric: MetricName,
) -> MetricValue | None:
    values = _outcome_metric_values(outcomes, experiment, method, scenario, metric)
    return None if not values else sum(values) / len(values)


def _outcome_metric_text(
    outcomes: tuple[CellExecutionOutcome, ...],
    experiment: ExperimentName,
    method: MethodName,
    scenario: ScenarioName,
    metric: MetricName,
) -> FormattedStatisticText:
    return format_metric_value(_outcome_metric_mean(outcomes, experiment, method, scenario, metric))


def _outcome_metric_confidence_interval(
    outcomes: tuple[CellExecutionOutcome, ...],
    experiment: ExperimentName,
    method: MethodName,
    scenario: ScenarioName,
    metric: ComparisonMetric,
) -> FormattedStatisticText:
    values = _outcome_metric_values(outcomes, experiment, method, scenario, metric)
    config = current_application_context().scientific_config
    interval = bootstrap_percentile_confidence_interval(
        values,
        config.metrics_and_statistics.bootstrap,
        config.seeds_and_determinism.analysis_seed,
    )
    if interval is None:
        return "NA"
    return f"[{interval[0]:.3f},{interval[1]:.3f}]"


def _outcome_timing_median_iqr(
    outcomes: tuple[CellExecutionOutcome, ...],
    experiment: ExperimentName,
    method: MethodName,
    scenario: ScenarioName,
    metric: MetricName,
) -> FormattedStatisticText:
    values = _outcome_metric_values(outcomes, experiment, method, scenario, metric)
    if not values:
        return "NA"
    ordered_values = tuple(sorted(values))
    median = quantile_type7(ordered_values, 0.5)
    first_quartile = quantile_type7(ordered_values, 0.25)
    third_quartile = quantile_type7(ordered_values, 0.75)
    decimals = _publication_rounding().seconds_decimals
    return f"{median:.{decimals}f} [{first_quartile:.{decimals}f},{third_quartile:.{decimals}f}]"


def _descriptive_timing_value(
    outcomes: tuple[CellExecutionOutcome, ...],
    experiment: ExperimentName,
    method: MethodName,
    scenario: ScenarioName,
    metric: MetricName,
) -> FormattedStatisticText:
    if experiment == EFFICIENCY_MEASUREMENT_NAME:
        return _outcome_timing_median_iqr(outcomes, experiment, method, scenario, metric)
    return format_metric_value(_outcome_metric_mean(outcomes, experiment, method, scenario, metric))


def _completed_outcome_count(
    outcomes: tuple[CellExecutionOutcome, ...],
    experiment: ExperimentName,
    method: MethodName,
    scenario: ScenarioName,
) -> TextValue:
    return str(
        sum(
            1
            for outcome in outcomes
            if (
                outcome.completed
                and outcome.cell.experiment == experiment
                and outcome.cell.method == method
                and outcome.cell.condition == scenario
            )
        )
    )


def _outcome_summary_or_comparison(
    outcomes: tuple[CellExecutionOutcome, ...],
    comparison_results: tuple[ComparisonFamilyResult, ...],
    experiment: ExperimentName,
    method: MethodName,
    scenario: ScenarioName,
    metric: ComparisonMetric,
) -> FormattedStatisticText:
    values = _outcome_metric_values(outcomes, experiment, method, scenario, metric)
    if values:
        mean = sum(values) / len(values)
        sample_standard_deviation = (
            0.0
            if len(values) == 1
            else math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))
        )
        decimals = _publication_rounding().f1_accuracy_rates_decimals
        return f"{mean:.{decimals}f} ± {sample_standard_deviation:.{decimals}f}"
    return _comparison_value(comparison_results, experiment, method, scenario, metric)


def render_primary_results_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    outcomes: tuple[CellExecutionOutcome, ...],
) -> RenderedTable:
    methods_scenarios: list[tuple[MethodName, ScenarioName]] = []
    seen: set[tuple[MethodName, ScenarioName]] = set()
    for family in comparison_results:
        for comparison in family.comparisons:
            definition = comparison.definition
            if definition.experiment != PRIMARY_CONFIRMATORY_EVALUATION_NAME:
                continue
            key = (definition.method, definition.scientific_scenario)
            if key in seen:
                continue
            seen.add(key)
            methods_scenarios.append(key)
    for outcome in outcomes:
        if outcome.cell.experiment != PRIMARY_CONFIRMATORY_EVALUATION_NAME:
            continue
        key = (outcome.cell.method, outcome.cell.condition)
        if key in seen:
            continue
        seen.add(key)
        methods_scenarios.append(key)
    rows = tuple(
        (
            method,
            scenario,
            _outcome_summary_or_comparison(
                outcomes,
                comparison_results,
                PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                method,
                scenario,
                ComparisonMetric.TARGET_F1,
            ),
            _outcome_metric_confidence_interval(
                outcomes,
                PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                method,
                scenario,
                ComparisonMetric.TARGET_F1,
            ),
            _outcome_summary_or_comparison(
                outcomes,
                comparison_results,
                PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                method,
                scenario,
                ComparisonMetric.SUPPORTED_MACRO_F1_HARM,
            ),
            _outcome_summary_or_comparison(
                outcomes,
                comparison_results,
                PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                method,
                scenario,
                ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE,
            ),
            _outcome_summary_or_comparison(
                outcomes,
                comparison_results,
                PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                method,
                scenario,
                ComparisonMetric.ATTACK_SUCCESS_RATE,
            ),
            _outcome_summary_or_comparison(
                outcomes,
                comparison_results,
                PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                method,
                scenario,
                ComparisonMetric.MALICIOUS_ADMISSION,
            ),
            _outcome_summary_or_comparison(
                outcomes,
                comparison_results,
                PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                method,
                scenario,
                ComparisonMetric.LEGITIMATE_ADMISSION,
            ),
            _outcome_summary_or_comparison(
                outcomes,
                comparison_results,
                PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                method,
                scenario,
                ComparisonMetric.WORST_DOMAIN_TARGET_F1,
            ),
            _completed_outcome_count(
                outcomes,
                PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                method,
                scenario,
            ),
        )
        for method, scenario in methods_scenarios
    )
    return RenderedTable(
        name="Primary Results",
        csv_text=_csv_text(
            (
                "method",
                "scenario",
                "target_f1_mean",
                "target_f1_95_ci",
                "supported_macro_f1_harm",
                "benign_false_alarm_rate_increase",
                ComparisonMetric.ATTACK_SUCCESS_RATE.value,
                "malicious_admission",
                "legitimate_admission",
                "worst_domain_target_f1",
                "complete_seed_count",
            ),
            rows,
        ),
    )


def render_source_exclusion_results_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    outcomes: tuple[CellExecutionOutcome, ...],
    collapse_decisions: tuple[CollapseDecision, ...] | None,
) -> RenderedTable:
    source_exclusion_decision = next(
        (
            decision
            for decision in collapse_decisions or ()
            if decision.kind is CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION
        ),
        None,
    )
    source_exclusion_gate_outcome: FormattedStatisticText = (
        "NA"
        if source_exclusion_decision is None
        else ("Survives" if source_exclusion_decision.survives else "Not Supported")
    )
    methods: list[MethodName] = []
    seen: set[MethodName] = set()
    for family in comparison_results:
        for comparison in family.comparisons:
            definition = comparison.definition
            if definition.experiment != SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME:
                continue
            if definition.method in seen:
                continue
            seen.add(definition.method)
            methods.append(definition.method)
    source_scenario = PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value
    for outcome in outcomes:
        if outcome.cell.experiment != SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME:
            continue
        if outcome.cell.condition != source_scenario or outcome.cell.method in seen:
            continue
        seen.add(outcome.cell.method)
        methods.append(outcome.cell.method)
    methods.sort(
        key=lambda method: (
            0 if method == SourceExclusionMethod.FULL_FEDSIRA else 1,
            asr
            if (
                asr := _outcome_metric_mean(
                    outcomes,
                    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
                    method,
                    source_scenario,
                    ComparisonMetric.ATTACK_SUCCESS_RATE,
                )
            )
            is not None
            else math.inf,
            method,
        )
    )
    target_noninferiority_status: FormattedStatisticText = "NA"
    target_noninferiority_comparison = _comparison_result(
        comparison_results,
        SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
        SourceExclusionMethod.FULL_FEDSIRA,
        source_scenario,
        ComparisonMetric.TARGET_F1,
    )
    if target_noninferiority_comparison is not None:
        target_noninferiority_status = target_noninferiority_comparison.comparison_state.value
    rows = tuple(
        (
            method,
            _outcome_summary_or_comparison(
                outcomes,
                comparison_results,
                SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
                method,
                source_scenario,
                ComparisonMetric.ATTACK_SUCCESS_RATE,
            ),
            format_metric_value(
                None
                if source_asr_comparison is None
                else source_asr_comparison.mean_paired_difference
            ),
            format_p_value(
                None if source_asr_comparison is None else source_asr_comparison.adjusted_p_value
            ),
            _comparison_confidence_interval(source_asr_comparison),
            _outcome_summary_or_comparison(
                outcomes,
                comparison_results,
                SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
                method,
                source_scenario,
                ComparisonMetric.TARGET_F1,
            ),
            (
                target_noninferiority_status
                if method == SourceExclusionMethod.FULL_FEDSIRA
                else "NA"
            ),
            _outcome_summary_or_comparison(
                outcomes,
                comparison_results,
                SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
                method,
                source_scenario,
                ComparisonMetric.SUPPORTED_MACRO_F1_HARM,
            ),
            _outcome_summary_or_comparison(
                outcomes,
                comparison_results,
                SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
                method,
                source_scenario,
                ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE,
            ),
            source_exclusion_gate_outcome,
        )
        for method in methods
        for source_asr_comparison in (
            _comparison_result(
                comparison_results,
                SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
                method,
                source_scenario,
                ComparisonMetric.ATTACK_SUCCESS_RATE,
            ),
        )
    )
    return RenderedTable(
        name="Source-Exclusion Results",
        csv_text=_csv_text(
            (
                "method",
                "post_production_asr",
                "asr_difference_vs_fedsira",
                "adjusted_p",
                "confidence_interval_95",
                "target_f1",
                "target_noninferiority_pass",
                "supported_f1_harm",
                "benign_fpr_increase",
                "source_exclusion_gate_outcome",
            ),
            rows,
        ),
    )


def render_ablation_results_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    outcomes: tuple[CellExecutionOutcome, ...],
) -> RenderedTable:
    rows: list[tuple[TextValue, ...]] = []
    for variant in AblationVariant:
        scenario = ablation_scenario_for_variant(variant)
        metric, _orientation = ablation_metric(variant)
        comparison = _comparison_result(
            comparison_results,
            MECHANISM_ABLATION_NAME,
            variant.value,
            scenario,
            metric,
        )
        is_reference = variant is AblationVariant.FULL_FEDSIRA
        rows.append(
            (
                variant.value,
                variant.value,
                scenario,
                metric.value,
                (
                    "reference row"
                    if is_reference
                    else format_metric_value(
                        None if comparison is None else comparison.mean_paired_difference
                    )
                ),
                (
                    "reference row"
                    if is_reference
                    else format_p_value(None if comparison is None else comparison.adjusted_p_value)
                ),
                (
                    "reference row"
                    if is_reference
                    else _materiality_text(None if comparison is None else comparison)
                ),
                _outcome_summary_or_comparison(
                    outcomes,
                    comparison_results,
                    MECHANISM_ABLATION_NAME,
                    variant.value,
                    scenario,
                    ComparisonMetric.TARGET_F1,
                ),
                _outcome_summary_or_comparison(
                    outcomes,
                    comparison_results,
                    MECHANISM_ABLATION_NAME,
                    variant.value,
                    scenario,
                    ComparisonMetric.SUPPORTED_MACRO_F1_HARM,
                ),
                _outcome_summary_or_comparison(
                    outcomes,
                    comparison_results,
                    MECHANISM_ABLATION_NAME,
                    variant.value,
                    scenario,
                    ComparisonMetric.ATTACK_SUCCESS_RATE,
                ),
                _completed_outcome_count(
                    outcomes,
                    MECHANISM_ABLATION_NAME,
                    variant.value,
                    scenario,
                ),
            )
        )
    return RenderedTable(
        name="Ablation Results",
        csv_text=_csv_text(
            (
                "variant",
                "targeted_mechanism",
                "scenario",
                "primary_metric",
                "difference_from_full_reference",
                "adjusted_p",
                "materiality_pass",
                "target_f1",
                "supported_harm",
                "asr_or_malicious_admission",
                "complete_seeds",
            ),
            tuple(rows),
        ),
    )


class ByzantineBoundaryRow(FrozenDomainModel):
    bound_status: TextValue
    compromised_count: RowCount
    strategy: TextValue


def _condition_compromised_count(condition: ScenarioName) -> RowCount:
    if condition.startswith("Two"):
        return 2
    if condition.startswith("One"):
        return 1
    return 0


def _byzantine_boundary(
    experiment: ExperimentName,
    condition: ScenarioName,
) -> ByzantineBoundaryRow:
    config = current_application_context().scientific_config
    if experiment == BYZANTINE_BOUND_VIOLATION_NAME:
        for bound_condition in BoundCondition:
            if bound_condition.value == condition:
                return ByzantineBoundaryRow(
                    bound_status=(
                        "Within Bound" if condition.endswith("Within Bound") else "Above Bound"
                    ),
                    compromised_count=_condition_compromised_count(condition),
                    strategy=condition,
                )
    elif experiment == COMPROMISED_REPRODUCER_ROBUSTNESS_NAME:
        within_bound_maximum = config.protocol.synthesis.maximum_byzantine_reproduction_rows
        compromised = _condition_compromised_count(condition)
        return ByzantineBoundaryRow(
            bound_status="Within Bound" if compromised <= within_bound_maximum else "Above Bound",
            compromised_count=compromised,
            strategy=condition,
        )
    elif experiment == COMPROMISED_VERIFIER_ROBUSTNESS_NAME:
        within_bound_maximum = config.protocol.verification.maximum_byzantine_verifiers_per_panel
        compromised = _condition_compromised_count(condition)
        return ByzantineBoundaryRow(
            bound_status="Within Bound" if compromised <= within_bound_maximum else "Above Bound",
            compromised_count=compromised,
            strategy=condition,
        )
    raise ValueError(f"unsupported Byzantine boundary condition {condition!r}")


def render_byzantine_robustness_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    outcomes: tuple[CellExecutionOutcome, ...],
) -> RenderedTable:
    rows: list[tuple[TextValue, ...]] = []
    for family in comparison_results:
        for comparison in family.comparisons:
            definition = comparison.definition
            if definition.experiment not in (
                COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
                COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
                BYZANTINE_BOUND_VIOLATION_NAME,
            ):
                continue
            boundary = _byzantine_boundary(
                definition.experiment,
                definition.scientific_scenario,
            )
            rows.append(
                (
                    family.family.value,
                    definition.method,
                    definition.scientific_scenario,
                    boundary.bound_status,
                    str(boundary.compromised_count),
                    boundary.strategy,
                    _outcome_summary_or_comparison(
                        outcomes,
                        comparison_results,
                        definition.experiment,
                        definition.method,
                        definition.scientific_scenario,
                        ComparisonMetric.MALICIOUS_ADMISSION,
                    ),
                    _outcome_summary_or_comparison(
                        outcomes,
                        comparison_results,
                        definition.experiment,
                        definition.method,
                        definition.scientific_scenario,
                        ComparisonMetric.LEGITIMATE_ADMISSION,
                    ),
                    _outcome_summary_or_comparison(
                        outcomes,
                        comparison_results,
                        definition.experiment,
                        definition.method,
                        definition.scientific_scenario,
                        ComparisonMetric.ATTACK_SUCCESS_RATE,
                    ),
                    _outcome_summary_or_comparison(
                        outcomes,
                        comparison_results,
                        definition.experiment,
                        definition.method,
                        definition.scientific_scenario,
                        ComparisonMetric.TARGET_F1,
                    ),
                    _outcome_metric_text(
                        outcomes,
                        definition.experiment,
                        definition.method,
                        definition.scientific_scenario,
                        DescriptiveScientificMetric.CERTIFIED_ROW_YIELD.value,
                    ),
                    _outcome_metric_text(
                        outcomes,
                        definition.experiment,
                        definition.method,
                        definition.scientific_scenario,
                        DescriptiveScientificMetric.DORMANT_ADMISSION_RATE.value,
                    ),
                    str(comparison.complete_seed_count),
                )
            )
    rows.sort(key=lambda row: (row[0], row[3] != "Within Bound", int(row[4]), row[1], row[2]))
    return RenderedTable(
        name="Byzantine Robustness",
        csv_text=_csv_text(
            (
                "bound_family",
                "method",
                "condition",
                "bound_status",
                "compromised_count",
                "strategy",
                "malicious_admission",
                "legitimate_admission",
                ComparisonMetric.ATTACK_SUCCESS_RATE.value,
                "target_f1",
                "certified_yield",
                "dormant_rate",
                "complete_seeds",
            ),
            tuple(rows),
        ),
    )


def _strength_from_condition(condition: ScenarioName) -> TextValue:
    if "|" not in condition:
        return "not applicable"
    return condition.rsplit("|", 1)[1]


def _scope_boundary_for_boundary_experiment(experiment: ExperimentName) -> TextValue:
    if experiment == SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME:
        return "corrupted operational evidence; clean oracle reported separately"
    if experiment == EVIDENCE_SCARCITY_AND_DORMANCY_NAME:
        return "logical evidence arrival; not compute overhead"
    if experiment == CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME:
        return "Capability Contract granularity scope"
    if experiment == HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME:
        return "tested heterogeneity range"
    raise ValueError(f"unsupported failure-boundary experiment {experiment!r}")


def render_failure_boundaries_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    outcomes: tuple[CellExecutionOutcome, ...],
) -> RenderedTable:
    rows: list[tuple[TextValue, ...]] = []
    boundary_experiments = (
        EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
        SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
        CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
        HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
    )
    for experiment in boundary_experiments:
        definition = experiment_by_name(experiment)
        for method in definition.methods:
            for condition in definition.conditions:
                if not any(
                    outcome.completed
                    and outcome.cell.experiment == experiment
                    and outcome.cell.method == method
                    and outcome.cell.condition == condition
                    for outcome in outcomes
                ):
                    continue
                is_oracle_experiment = experiment == SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME
                rows.append(
                    (
                        experiment,
                        condition,
                        _strength_from_condition(condition),
                        _outcome_summary_or_comparison(
                            outcomes,
                            comparison_results,
                            experiment,
                            method,
                            condition,
                            ComparisonMetric.LEGITIMATE_ADMISSION,
                        ),
                        _outcome_summary_or_comparison(
                            outcomes,
                            comparison_results,
                            experiment,
                            method,
                            condition,
                            ComparisonMetric.TARGET_F1,
                        ),
                        _outcome_summary_or_comparison(
                            outcomes,
                            comparison_results,
                            experiment,
                            method,
                            condition,
                            ComparisonMetric.WORST_DOMAIN_TARGET_F1,
                        ),
                        (
                            _outcome_summary_or_comparison(
                                outcomes,
                                comparison_results,
                                experiment,
                                method,
                                condition,
                                ComparisonMetric.TARGET_F1,
                            )
                            if is_oracle_experiment
                            else "NA"
                        ),
                        _scope_boundary_for_boundary_experiment(experiment)
                        if is_oracle_experiment
                        else "Not an Epistemic-Oracle Experiment",
                    )
                )
    return RenderedTable(
        name="Failure Boundaries",
        csv_text=_csv_text(
            (
                "boundary_family",
                "condition",
                "strength",
                "admission_dormancy",
                "target_f1",
                "worst_domain_f1",
                "clean_oracle_error",
                "scope_boundary",
            ),
            tuple(rows),
        ),
    )


def render_delay_and_efficiency_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    outcomes: tuple[CellExecutionOutcome, ...],
) -> RenderedTable:
    rows_to_render: list[tuple[ExperimentName, MethodName, ScenarioName]] = []
    seen: set[tuple[ExperimentName, MethodName, ScenarioName]] = set()
    relevant_experiments = frozenset(
        (ADMISSION_DELAY_DECOMPOSITION_NAME, EFFICIENCY_MEASUREMENT_NAME)
    )
    for family in comparison_results:
        for comparison in family.comparisons:
            definition = comparison.definition
            key = (definition.experiment, definition.method, definition.scientific_scenario)
            if definition.experiment not in relevant_experiments or key in seen:
                continue
            seen.add(key)
            rows_to_render.append(key)
    for outcome in outcomes:
        cell = outcome.cell
        key = (cell.experiment, cell.method, cell.condition)
        if cell.experiment not in relevant_experiments or key in seen:
            continue
        seen.add(key)
        rows_to_render.append(key)
    rows = tuple(
        (
            experiment,
            method,
            scenario,
            format_metric_value(
                _outcome_metric_mean(
                    outcomes,
                    experiment,
                    method,
                    scenario,
                    DescriptiveScientificMetric.T_EVIDENCE.value,
                )
            ),
            _descriptive_timing_value(outcomes, experiment, method, scenario, "assignment-seconds"),
            _descriptive_timing_value(outcomes, experiment, method, scenario, "reproduce-seconds"),
            _descriptive_timing_value(outcomes, experiment, method, scenario, "verify-seconds"),
            _descriptive_timing_value(outcomes, experiment, method, scenario, "synthesize-seconds"),
            _descriptive_timing_value(
                outcomes,
                experiment,
                method,
                scenario,
                DescriptiveScientificMetric.WALL_CLOCK_SECONDS.value,
            ),
            _descriptive_timing_value(
                outcomes,
                experiment,
                method,
                scenario,
                DescriptiveScientificMetric.GPU_SECONDS.value,
            ),
            format_metric_value(
                _outcome_metric_mean(
                    outcomes,
                    experiment,
                    method,
                    scenario,
                    DescriptiveScientificMetric.PEAK_GPU_MEMORY_BYTES.value,
                )
            ),
            format_metric_value(
                _outcome_metric_mean(
                    outcomes,
                    experiment,
                    method,
                    scenario,
                    DescriptiveScientificMetric.PEAK_HOST_RSS_BYTES.value,
                )
            ),
            format_metric_value(
                _outcome_metric_mean(
                    outcomes,
                    experiment,
                    method,
                    scenario,
                    DescriptiveScientificMetric.COMMUNICATION_BYTES.value,
                )
            ),
            format_metric_value(
                _outcome_metric_mean(
                    outcomes,
                    experiment,
                    method,
                    scenario,
                    DescriptiveScientificMetric.MODEL_TRANSMISSIONS.value,
                )
            ),
            format_metric_value(
                _outcome_metric_mean(
                    outcomes,
                    experiment,
                    method,
                    scenario,
                    DescriptiveScientificMetric.PERSISTENT_STORAGE_BYTES.value,
                )
            ),
        )
        for experiment, method, scenario in rows_to_render
    )
    return RenderedTable(
        name="Delay and Efficiency",
        csv_text=_csv_text(
            (
                "experiment",
                "method",
                "condition",
                "t_evidence",
                "assignment_seconds",
                "reproduction_seconds",
                "verification_seconds",
                "synthesis_seconds",
                "post_evidence_wall_clock",
                "gpu_seconds",
                "peak_gpu_memory",
                "host_rss",
                "communication_bytes",
                "transmissions",
                "storage_bytes",
            ),
            rows,
        ),
    )


GENERALIZATION_SCOPE_LABEL: TextValue = "Data/Attack Generalization Only"


def _generalization_references(
    comparison_results: tuple[ComparisonFamilyResult, ...],
) -> tuple[MethodName, ...]:
    references: list[MethodName] = []
    for family in comparison_results:
        for comparison in family.comparisons:
            definition = comparison.definition
            if definition.experiment != SECONDARY_DATASET_GENERALIZATION_NAME:
                continue
            if definition.reference_kind is not ComparisonReferenceKind.SCIENTIFIC_CELL:
                continue
            if definition.reference_method in references:
                continue
            references.append(definition.reference_method)
    return tuple(references)


def render_generalization_results_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    outcomes: tuple[CellExecutionOutcome, ...],
) -> RenderedTable:
    definition = experiment_by_name(SECONDARY_DATASET_GENERALIZATION_NAME)
    references = _generalization_references(comparison_results)
    reference_label = ";".join(references) if references else "no predeclared comparator"
    rows: list[tuple[TextValue, ...]] = []
    for method in definition.methods:
        for secondary_scenario in SecondaryScenario:
            scenario = secondary_scenario.value
            comparison = next(
                (
                    _comparison_result(
                        comparison_results,
                        SECONDARY_DATASET_GENERALIZATION_NAME,
                        CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
                        scenario,
                        metric,
                    )
                    for metric in (
                        ComparisonMetric.TARGET_F1,
                        ComparisonMetric.MALICIOUS_ADMISSION,
                    )
                ),
                None,
            )
            is_reference_row = method == CoreMethodIdentity.RESOLVED_FEDSIRA_CORE
            rows.append(
                (
                    method,
                    scenario,
                    _outcome_summary_or_comparison(
                        outcomes,
                        comparison_results,
                        SECONDARY_DATASET_GENERALIZATION_NAME,
                        method,
                        scenario,
                        ComparisonMetric.TARGET_F1,
                    ),
                    _outcome_summary_or_comparison(
                        outcomes,
                        comparison_results,
                        SECONDARY_DATASET_GENERALIZATION_NAME,
                        method,
                        scenario,
                        ComparisonMetric.SUPPORTED_MACRO_F1_HARM,
                    ),
                    _outcome_summary_or_comparison(
                        outcomes,
                        comparison_results,
                        SECONDARY_DATASET_GENERALIZATION_NAME,
                        method,
                        scenario,
                        ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE,
                    ),
                    _outcome_summary_or_comparison(
                        outcomes,
                        comparison_results,
                        SECONDARY_DATASET_GENERALIZATION_NAME,
                        method,
                        scenario,
                        ComparisonMetric.MALICIOUS_ADMISSION,
                    ),
                    _outcome_summary_or_comparison(
                        outcomes,
                        comparison_results,
                        SECONDARY_DATASET_GENERALIZATION_NAME,
                        method,
                        scenario,
                        ComparisonMetric.LEGITIMATE_ADMISSION,
                    ),
                    (
                        "0.000 (reference method)"
                        if is_reference_row
                        else format_metric_value(
                            None
                            if comparison is None or comparison.mean_paired_difference is None
                            else -comparison.mean_paired_difference
                        )
                    ),
                    (reference_label if is_reference_row else "not a predeclared comparison"),
                    (
                        format_p_value(None if comparison is None else comparison.adjusted_p_value)
                        if is_reference_row
                        else "not a predeclared comparison"
                    ),
                    (
                        _materiality_text(comparison)
                        if is_reference_row
                        else "not a predeclared comparison"
                    ),
                    GENERALIZATION_SCOPE_LABEL,
                )
            )
    return RenderedTable(
        name="Generalization Results",
        csv_text=_csv_text(
            (
                "method",
                "scenario",
                "target_f1_or_gain",
                "supported_harm",
                "benign_false_alarm_rate_increase",
                "malicious_admission",
                "legitimate_admission",
                "paired_effect_vs_fedsira",
                "predeclared_comparator",
                "adjusted_p",
                "materiality_pass",
                "scope_label",
            ),
            tuple(rows),
        ),
    )


def render_mandatory_tables(
    plan: ExperimentPlan,
    collapse_decisions: tuple[CollapseDecision, ...] | None,
    resolved_core: ResolvedCore | None,
    comparison_results: tuple[ComparisonFamilyResult, ...],
    outcomes: tuple[CellExecutionOutcome, ...],
) -> tuple[RenderedTable, ...]:
    tables = [
        render_dataset_and_domain_protocol_table(),
        render_primary_domain_statistics_table(),
        render_model_and_training_protocol_table(),
        render_security_and_capability_contract_protocol_table(),
        render_baseline_protocol_table(),
        render_experiment_plan_table(plan),
        render_metric_and_statistics_protocol_table(),
        render_primary_results_table(comparison_results, outcomes),
        render_source_exclusion_results_table(
            comparison_results,
            outcomes,
            collapse_decisions,
        ),
    ]
    if collapse_decisions is not None and resolved_core is not None:
        tables.append(render_collapse_decisions_table(collapse_decisions, resolved_core))
    else:
        tables.append(
            RenderedTable(
                name="Collapse Decisions",
                csv_text=_csv_text(
                    (
                        "mechanism",
                        "comparator",
                        "primary_material_effect",
                        "adjusted_p",
                        "liveness_safety_constraint",
                        "survival_rule",
                        "observed_outcome",
                        "core_action",
                    ),
                    (),
                ),
            )
        )
    tables.extend(
        (
            render_ablation_results_table(comparison_results, outcomes),
            render_byzantine_robustness_table(comparison_results, outcomes),
            render_failure_boundaries_table(comparison_results, outcomes),
            render_delay_and_efficiency_table(comparison_results, outcomes),
            render_generalization_results_table(comparison_results, outcomes),
            render_statistical_summary_table(comparison_results),
        )
    )
    return tuple(tables)
