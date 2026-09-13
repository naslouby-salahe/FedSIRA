from __future__ import annotations

import csv
import math
from collections.abc import Callable
from io import StringIO

from fedsira.config import PublicationRoundingConfig
from fedsira.domain.enums import (
    AblationVariant,
    BoundCondition,
    ByteUnit,
    CoreMethodIdentity,
    DelayPhaseMetric,
    DescriptiveScientificMetric,
    ExperimentName,
    PrimaryScenario,
    ReportCellLiteral,
    ReportColumnName,
    SecondaryScenario,
    SourceExclusionMethod,
    TableName,
)
from fedsira.domain.types import (
    ByteCount,
    FormattedStatisticText,
    FrozenDomainModel,
    MethodName,
    MetricName,
    MetricValue,
    ProtocolRuleText,
    PValue,
    ReportCellText,
    ReportColumnText,
    RowCount,
    ScenarioName,
    TableCsvText,
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
from fedsira.evaluation.statistics import (
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
    ablation_scenario_for_variant,
    experiment_by_name,
)
from fedsira.experiments.engine import (
    CellExecutionOutcome,
)
from fedsira.runtime import current_application_context

MANUSCRIPT_TABLE_NAMES: tuple[TableName, ...] = (
    TableName.DATASET_AND_DOMAIN_PROTOCOL,
    TableName.PRIMARY_DOMAIN_STATISTICS,
    TableName.MODEL_AND_TRAINING_PROTOCOL,
    TableName.SECURITY_AND_CAPABILITY_CONTRACT_PROTOCOL,
    TableName.BASELINE_PROTOCOL,
    TableName.EXPERIMENT_PLAN,
    TableName.METRIC_AND_STATISTICS_PROTOCOL,
    TableName.PRIMARY_RESULTS,
    TableName.SOURCE_EXCLUSION_RESULTS,
    TableName.COLLAPSE_DECISIONS,
    TableName.ABLATION_RESULTS,
    TableName.BYZANTINE_ROBUSTNESS,
    TableName.FAILURE_BOUNDARIES,
    TableName.DELAY_AND_EFFICIENCY,
    TableName.GENERALIZATION_RESULTS,
    TableName.STATISTICAL_SUMMARY,
)


def render_experiment_cell_metrics_table(
    outcomes: tuple[CellExecutionOutcome, ...],
) -> RenderedTable:
    return render_cell_metrics(outcomes, CELL_METRICS_TABLE_NAME, format_metric_value)


def _publication_rounding() -> PublicationRoundingConfig:
    statistics = current_application_context().scientific_config.metrics_and_statistics
    return statistics.publication_rounding


BYTE_VALUED_METRICS: tuple[MetricName, ...] = (
    DescriptiveScientificMetric.PEAK_GPU_MEMORY_BYTES,
    DescriptiveScientificMetric.PEAK_HOST_RSS_BYTES,
    DescriptiveScientificMetric.COMMUNICATION_BYTES,
    DescriptiveScientificMetric.PERSISTENT_STORAGE_BYTES,
)

BYTE_UNIT_LABELS: tuple[tuple[ByteUnit, ReportCellText, ByteCount], ...] = (
    (ByteUnit.IEC, "GiB", 1024**3),
)


RATE_VALUED_METRICS: tuple[MetricName, ...] = (
    ComparisonMetric.LEGITIMATE_ADMISSION,
    ComparisonMetric.MALICIOUS_ADMISSION,
    ComparisonMetric.ATTACK_SUCCESS_RATE,
    ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE,
    ComparisonMetric.FALSE_LAUNCH,
    ComparisonMetric.FALSE_SAME_CAPABILITY_CERTIFICATION_RATE,
    DescriptiveScientificMetric.DORMANT_ADMISSION_RATE,
    DescriptiveScientificMetric.VERIFIER_ABSTENTION_RATE,
    DescriptiveScientificMetric.REPRODUCTION_ABSTENTION_RATE,
    DescriptiveScientificMetric.DEFINED_DOMAIN_FRACTION,
)


def format_rate_value(value: MetricValue | None) -> FormattedStatisticText:
    rounding = _publication_rounding()
    if value is None:
        return ReportCellLiteral.NOT_AVAILABLE
    return f"{value * 100.0:.{rounding.percentage_decimals}f}%"


def format_metric_value(
    value: MetricValue | None, metric: MetricName | None = None
) -> FormattedStatisticText:
    if metric is not None and metric in BYTE_VALUED_METRICS:
        return format_byte_value(value)
    if metric is not None and metric in RATE_VALUED_METRICS:
        return format_rate_value(value)
    rounding = _publication_rounding()
    if value is None:
        return ReportCellLiteral.NOT_AVAILABLE
    return f"{value:.{rounding.f1_accuracy_rates_decimals}f}"


def format_byte_value(value: MetricValue | None) -> FormattedStatisticText:
    rounding = _publication_rounding()
    if value is None:
        return ReportCellLiteral.NOT_AVAILABLE
    for unit, label, scale in BYTE_UNIT_LABELS:
        if unit is rounding.byte_units:
            return f"{value / scale:.{rounding.byte_decimals}f} {label}"
    raise ValueError(f"unsupported byte unit: {rounding.byte_units}")


def format_p_value(value: PValue | None) -> FormattedStatisticText:
    rounding = _publication_rounding()
    if value is None:
        return ReportCellLiteral.NOT_AVAILABLE
    if value < rounding.p_value_display_floor:
        return f"<{rounding.p_value_display_floor:.4f}"
    return f"{value:.{rounding.p_value_significant_digits}g}"


def _comparison_reference_label(definition: ComparisonDefinition) -> ReportCellText:
    if definition.reference_kind is ComparisonReferenceKind.ZERO:
        return ComparisonReferenceKind.ZERO
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
) -> tuple[ReportCellText, ...]:
    definition = comparison.definition
    effect_decimals = _publication_rounding().effect_size_decimals
    effect = (
        ReportCellLiteral.NOT_AVAILABLE
        if comparison.paired_standardized_effect is None
        else f"{comparison.paired_standardized_effect:.{effect_decimals}f}"
    )
    confidence_interval = (
        ReportCellLiteral.NOT_AVAILABLE
        if comparison.confidence_interval is None
        else (f"[{comparison.confidence_interval[0]:.3f},{comparison.confidence_interval[1]:.3f}]")
    )
    margin = ReportCellLiteral.NOT_AVAILABLE
    if definition.margin is not None:
        margin = f"{definition.margin:.3f}"
    materiality = (
        ReportCellLiteral.NOT_AVAILABLE
        if definition.material_threshold is None
        else f"{definition.material_threshold:.3f}"
    )
    reference_label = _comparison_reference_label(definition)
    comparison_identity = (
        f"{definition.method} vs {reference_label} | "
        f"{definition.scientific_scenario} | {definition.metric}"
    )
    test_kind: ComparisonTestKind = definition.test_kind
    materiality_direction: MaterialityDirection = definition.materiality_direction
    return (
        family.family,
        comparison_identity,
        definition.metric,
        definition.orientation,
        test_kind,
        materiality_direction,
        margin,
        str(comparison.complete_seed_count),
        format_metric_value(comparison.mean_paired_difference, definition.metric),
        format_metric_value(comparison.median_paired_difference, definition.metric),
        effect,
        format_p_value(comparison.raw_p_value),
        format_p_value(comparison.adjusted_p_value),
        confidence_interval,
        materiality,
        (
            ReportCellLiteral.PASS
            if comparison.comparison_state is ComparisonState.PASSED
            else ReportCellLiteral.FAIL
        ),
        (
            ReportCellLiteral.PASS
            if comparison.materiality_passes is not False
            else ReportCellLiteral.FAIL
        ),
        comparison.comparison_state,
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
        name=TableName.STATISTICAL_SUMMARY,
        csv_text=csv_text(
            (
                ReportColumnName.COMPARISON_FAMILY,
                ReportColumnName.COMPARISON,
                ReportColumnName.METRIC,
                ReportColumnName.DIRECTION,
                ReportColumnName.TEST_KIND,
                ReportColumnName.MATERIALITY_DIRECTION,
                ReportColumnName.MARGIN,
                ReportColumnName.N_PAIRS,
                ReportColumnName.MEAN_DIFFERENCE,
                ReportColumnName.MEDIAN_DIFFERENCE,
                ReportColumnName.PAIRED_DZ,
                ReportColumnName.RAW_P,
                ReportColumnName.HOLM_P,
                ReportColumnName.CONFIDENCE_INTERVAL_95,
                ReportColumnName.MATERIALITY_THRESHOLD,
                ReportColumnName.STATISTICAL_PASS,
                ReportColumnName.MATERIALITY_PASS,
                ReportColumnName.FINAL_COMPARISON_STATE,
            ),
            rows,
        ),
    )


COLLAPSE_SURVIVAL_RULES: tuple[tuple[CollapseDecisionKind, ProtocolRuleText], ...] = (
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


def _collapse_survival_rule(kind: CollapseDecisionKind) -> ProtocolRuleText:
    for registered_kind, rule in COLLAPSE_SURVIVAL_RULES:
        if registered_kind is kind:
            return rule
    raise ValueError(f"unsupported collapse decision kind {kind}")


def _collapse_core_action(
    kind: CollapseDecisionKind,
    resolved_core: ResolvedCore,
) -> ReportCellText:
    if kind is CollapseDecisionKind.PROPOSAL_ASSISTANCE:
        return resolved_core.opening_mode
    if kind is CollapseDecisionKind.PLURALITY:
        return resolved_core.reproduction_row_requirement
    if kind is CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION:
        return "source-excluded" if resolved_core.source_excluded else "source-influenced"
    if kind is CollapseDecisionKind.EXTERNAL_VERIFICATION:
        return resolved_core.row_verification_mode
    raise ValueError(f"unsupported collapse decision kind {kind}")


def _collapse_observed_outcome(decision: CollapseDecision) -> ReportCellText:
    if decision.kind is CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION and not decision.survives:
        return "Central Not Supported"
    return "Survives" if decision.survives else "Removed"


def render_collapse_decisions_table(
    decisions: tuple[CollapseDecision, ...],
    resolved_core: ResolvedCore,
) -> RenderedTable:
    rows = tuple(
        (
            decision.kind,
            decision.comparator,
            decision.primary_material_effect or ReportCellLiteral.NONE,
            format_p_value(decision.adjusted_p_value),
            (ReportCellLiteral.PASS if decision.constraint_passes else ReportCellLiteral.FAIL),
            _collapse_survival_rule(decision.kind),
            _collapse_observed_outcome(decision),
            _collapse_core_action(decision.kind, resolved_core),
        )
        for decision in decisions
    )
    return RenderedTable(
        name=TableName.COLLAPSE_DECISIONS,
        csv_text=csv_text(
            (
                ReportColumnName.MECHANISM,
                ReportColumnName.COMPARATOR,
                ReportColumnName.PRIMARY_MATERIAL_EFFECT,
                ReportColumnName.ADJUSTED_P,
                ReportColumnName.LIVENESS_SAFETY_CONSTRAINT,
                ReportColumnName.SURVIVAL_RULE,
                ReportColumnName.OBSERVED_OUTCOME,
                ReportColumnName.CORE_ACTION,
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
                return format_metric_value(
                    comparison.mean_paired_difference,
                    comparison.definition.metric,
                )
    return ReportCellLiteral.NOT_AVAILABLE


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


def _comparison_confidence_interval(
    comparison: ComparisonResult | None,
) -> FormattedStatisticText:
    if comparison is None or comparison.confidence_interval is None:
        return ReportCellLiteral.NOT_AVAILABLE
    return f"[{comparison.confidence_interval[0]:.3f},{comparison.confidence_interval[1]:.3f}]"


def _materiality_text(comparison: ComparisonResult | None) -> FormattedStatisticText:
    if comparison is None or comparison.materiality_passes is None:
        return ReportCellLiteral.NOT_AVAILABLE
    return ReportCellLiteral.PASS if comparison.materiality_passes else ReportCellLiteral.FAIL


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
    return format_metric_value(
        _outcome_metric_mean(outcomes, experiment, method, scenario, metric), metric
    )


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
        return ReportCellLiteral.NOT_AVAILABLE
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
        return ReportCellLiteral.NOT_AVAILABLE
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
    return format_metric_value(
        _outcome_metric_mean(outcomes, experiment, method, scenario, metric), metric
    )


def _completed_outcome_count(
    outcomes: tuple[CellExecutionOutcome, ...],
    experiment: ExperimentName,
    method: MethodName,
    scenario: ScenarioName,
) -> ReportCellText:
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
        name=TableName.PRIMARY_RESULTS,
        csv_text=csv_text(
            (
                ReportColumnName.METHOD,
                ReportColumnName.SCENARIO,
                ReportColumnName.TARGET_F1_MEAN,
                ReportColumnName.TARGET_F1_95_CI,
                ReportColumnName.SUPPORTED_MACRO_F1_HARM,
                ReportColumnName.BENIGN_FALSE_ALARM_RATE_INCREASE,
                ComparisonMetric.ATTACK_SUCCESS_RATE,
                ReportColumnName.MALICIOUS_ADMISSION,
                ReportColumnName.LEGITIMATE_ADMISSION,
                ReportColumnName.WORST_DOMAIN_TARGET_F1,
                ReportColumnName.COMPLETE_SEED_COUNT,
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
        ReportCellLiteral.NOT_AVAILABLE
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
    source_scenario = str(PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT)
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
            (
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
                else math.inf
            ),
            method,
        )
    )
    target_noninferiority_status: FormattedStatisticText = ReportCellLiteral.NOT_AVAILABLE
    target_noninferiority_comparison = _comparison_result(
        comparison_results,
        SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
        SourceExclusionMethod.FULL_FEDSIRA,
        source_scenario,
        ComparisonMetric.TARGET_F1,
    )
    if target_noninferiority_comparison is not None:
        target_noninferiority_status = target_noninferiority_comparison.comparison_state
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
                else ReportCellLiteral.NOT_AVAILABLE
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
        name=TableName.SOURCE_EXCLUSION_RESULTS,
        csv_text=csv_text(
            (
                ReportColumnName.METHOD,
                ReportColumnName.POST_PRODUCTION_ASR,
                ReportColumnName.ASR_DIFFERENCE_VS_FEDSIRA,
                ReportColumnName.ADJUSTED_P,
                ReportColumnName.CONFIDENCE_INTERVAL_95,
                ReportColumnName.TARGET_F1,
                ReportColumnName.TARGET_NONINFERIORITY_PASS,
                ReportColumnName.SUPPORTED_F1_HARM,
                ReportColumnName.BENIGN_FPR_INCREASE,
                ReportColumnName.SOURCE_EXCLUSION_GATE_OUTCOME,
            ),
            rows,
        ),
    )


def render_ablation_results_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    outcomes: tuple[CellExecutionOutcome, ...],
) -> RenderedTable:
    rows: list[tuple[ReportCellText, ...]] = []
    for variant in AblationVariant:
        scenario = ablation_scenario_for_variant(variant)
        is_reference = variant is AblationVariant.FULL_FEDSIRA
        metric = (
            ComparisonMetric.ATTACK_SUCCESS_RATE if is_reference else ablation_metric(variant)[0]
        )
        comparison = _comparison_result(
            comparison_results,
            MECHANISM_ABLATION_NAME,
            variant,
            scenario,
            metric,
        )
        rows.append(
            (
                variant,
                variant,
                scenario,
                metric,
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
                    variant,
                    scenario,
                    ComparisonMetric.TARGET_F1,
                ),
                _outcome_summary_or_comparison(
                    outcomes,
                    comparison_results,
                    MECHANISM_ABLATION_NAME,
                    variant,
                    scenario,
                    ComparisonMetric.SUPPORTED_MACRO_F1_HARM,
                ),
                _outcome_summary_or_comparison(
                    outcomes,
                    comparison_results,
                    MECHANISM_ABLATION_NAME,
                    variant,
                    scenario,
                    ComparisonMetric.ATTACK_SUCCESS_RATE,
                ),
                _completed_outcome_count(
                    outcomes,
                    MECHANISM_ABLATION_NAME,
                    variant,
                    scenario,
                ),
            )
        )
    return RenderedTable(
        name=TableName.ABLATION_RESULTS,
        csv_text=csv_text(
            (
                ReportColumnName.VARIANT,
                ReportColumnName.TARGETED_MECHANISM,
                ReportColumnName.SCENARIO,
                ReportColumnName.PRIMARY_METRIC,
                ReportColumnName.DIFFERENCE_FROM_FULL_REFERENCE,
                ReportColumnName.ADJUSTED_P,
                ReportColumnName.MATERIALITY_PASS,
                ReportColumnName.TARGET_F1,
                ReportColumnName.SUPPORTED_HARM,
                ReportColumnName.ASR_OR_MALICIOUS_ADMISSION,
                ReportColumnName.COMPLETE_SEEDS,
            ),
            tuple(rows),
        ),
    )


class ByzantineBoundaryRow(FrozenDomainModel):
    bound_status: ReportCellText
    compromised_count: RowCount
    strategy: ScenarioName


def _condition_compromised_count(condition: ScenarioName) -> RowCount:
    return 2 if condition.startswith("Two") else 1 if condition.startswith("One") else 0


def _byzantine_boundary(
    experiment: ExperimentName,
    condition: ScenarioName,
) -> ByzantineBoundaryRow:
    config = current_application_context().scientific_config
    if experiment == BYZANTINE_BOUND_VIOLATION_NAME:
        for bound_condition in BoundCondition:
            if bound_condition == condition:
                return ByzantineBoundaryRow(
                    bound_status=(
                        "Within Bound" if condition.endswith("Within Bound") else "Above Bound"
                    ),
                    compromised_count=_condition_compromised_count(condition),
                    strategy=condition,
                )
    elif experiment == COMPROMISED_REPRODUCER_ROBUSTNESS_NAME:
        limit = config.protocol.synthesis.maximum_byzantine_reproduction_rows
        compromised = _condition_compromised_count(condition)
        return ByzantineBoundaryRow(
            bound_status="Within Bound" if compromised <= limit else "Above Bound",
            compromised_count=compromised,
            strategy=condition,
        )
    elif experiment == COMPROMISED_VERIFIER_ROBUSTNESS_NAME:
        limit = config.protocol.verification.maximum_byzantine_verifiers_per_panel
        compromised = _condition_compromised_count(condition)
        return ByzantineBoundaryRow(
            bound_status="Within Bound" if compromised <= limit else "Above Bound",
            compromised_count=compromised,
            strategy=condition,
        )
    raise ValueError(f"unsupported Byzantine boundary condition {condition!r}")


def render_byzantine_robustness_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    outcomes: tuple[CellExecutionOutcome, ...],
) -> RenderedTable:
    rows: list[tuple[ReportCellText, ...]] = []
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
                    family.family,
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
                        DescriptiveScientificMetric.CERTIFIED_ROW_YIELD,
                    ),
                    _outcome_metric_text(
                        outcomes,
                        definition.experiment,
                        definition.method,
                        definition.scientific_scenario,
                        DescriptiveScientificMetric.DORMANT_ADMISSION_RATE,
                    ),
                    str(comparison.complete_seed_count),
                )
            )
    rows.sort(key=lambda row: (row[0], row[3] != "Within Bound", int(row[4]), row[1], row[2]))
    return RenderedTable(
        name=TableName.BYZANTINE_ROBUSTNESS,
        csv_text=csv_text(
            (
                ReportColumnName.BOUND_FAMILY,
                ReportColumnName.METHOD,
                ReportColumnName.CONDITION,
                ReportColumnName.BOUND_STATUS,
                ReportColumnName.COMPROMISED_COUNT,
                ReportColumnName.STRATEGY,
                ReportColumnName.MALICIOUS_ADMISSION,
                ReportColumnName.LEGITIMATE_ADMISSION,
                ComparisonMetric.ATTACK_SUCCESS_RATE,
                ReportColumnName.TARGET_F1,
                ReportColumnName.CERTIFIED_YIELD,
                ReportColumnName.DORMANT_RATE,
                ReportColumnName.COMPLETE_SEEDS,
            ),
            tuple(rows),
        ),
    )


def _strength_from_condition(condition: ScenarioName) -> ReportCellText:
    if "|" not in condition:
        return "not applicable"
    return condition.rsplit("|", 1)[1]


def _scope_boundary_for_boundary_experiment(experiment: ExperimentName) -> ReportCellText:
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
    rows: list[tuple[ReportCellText, ...]] = []
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
                            else ReportCellLiteral.NOT_AVAILABLE
                        ),
                        (
                            _scope_boundary_for_boundary_experiment(experiment)
                            if is_oracle_experiment
                            else "Not an Epistemic-Oracle Experiment"
                        ),
                    )
                )
    return RenderedTable(
        name=TableName.FAILURE_BOUNDARIES,
        csv_text=csv_text(
            (
                ReportColumnName.BOUNDARY_FAMILY,
                ReportColumnName.CONDITION,
                ReportColumnName.STRENGTH,
                ReportColumnName.ADMISSION_DORMANCY,
                ReportColumnName.TARGET_F1,
                ReportColumnName.WORST_DOMAIN_F1,
                ReportColumnName.CLEAN_ORACLE_ERROR,
                ReportColumnName.SCOPE_BOUNDARY,
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
            key = (
                definition.experiment,
                definition.method,
                definition.scientific_scenario,
            )
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
                    DescriptiveScientificMetric.T_EVIDENCE,
                )
            ),
            _descriptive_timing_value(
                outcomes, experiment, method, scenario, DelayPhaseMetric.ASSIGNMENT_SECONDS
            ),
            _descriptive_timing_value(
                outcomes, experiment, method, scenario, DelayPhaseMetric.REPRODUCE_SECONDS
            ),
            _descriptive_timing_value(
                outcomes, experiment, method, scenario, DelayPhaseMetric.VERIFY_SECONDS
            ),
            _descriptive_timing_value(
                outcomes, experiment, method, scenario, DelayPhaseMetric.SYNTHESIZE_SECONDS
            ),
            _descriptive_timing_value(
                outcomes,
                experiment,
                method,
                scenario,
                DescriptiveScientificMetric.WALL_CLOCK_SECONDS,
            ),
            _descriptive_timing_value(
                outcomes,
                experiment,
                method,
                scenario,
                DescriptiveScientificMetric.GPU_SECONDS,
            ),
            format_metric_value(
                _outcome_metric_mean(
                    outcomes,
                    experiment,
                    method,
                    scenario,
                    DescriptiveScientificMetric.PEAK_GPU_MEMORY_BYTES,
                ),
                DescriptiveScientificMetric.PEAK_GPU_MEMORY_BYTES,
            ),
            format_metric_value(
                _outcome_metric_mean(
                    outcomes,
                    experiment,
                    method,
                    scenario,
                    DescriptiveScientificMetric.PEAK_HOST_RSS_BYTES,
                ),
                DescriptiveScientificMetric.PEAK_HOST_RSS_BYTES,
            ),
            format_metric_value(
                _outcome_metric_mean(
                    outcomes,
                    experiment,
                    method,
                    scenario,
                    DescriptiveScientificMetric.COMMUNICATION_BYTES,
                ),
                DescriptiveScientificMetric.COMMUNICATION_BYTES,
            ),
            format_metric_value(
                _outcome_metric_mean(
                    outcomes,
                    experiment,
                    method,
                    scenario,
                    DescriptiveScientificMetric.MODEL_TRANSMISSIONS,
                )
            ),
            format_metric_value(
                _outcome_metric_mean(
                    outcomes,
                    experiment,
                    method,
                    scenario,
                    DescriptiveScientificMetric.PERSISTENT_STORAGE_BYTES,
                ),
                DescriptiveScientificMetric.PERSISTENT_STORAGE_BYTES,
            ),
        )
        for experiment, method, scenario in rows_to_render
    )
    return RenderedTable(
        name=TableName.DELAY_AND_EFFICIENCY,
        csv_text=csv_text(
            (
                ReportColumnName.EXPERIMENT,
                ReportColumnName.METHOD,
                ReportColumnName.CONDITION,
                ReportColumnName.T_EVIDENCE,
                ReportColumnName.ASSIGNMENT_SECONDS,
                ReportColumnName.REPRODUCTION_SECONDS,
                ReportColumnName.VERIFICATION_SECONDS,
                ReportColumnName.SYNTHESIS_SECONDS,
                ReportColumnName.POST_EVIDENCE_WALL_CLOCK,
                ReportColumnName.GPU_SECONDS,
                ReportColumnName.PEAK_GPU_MEMORY,
                ReportColumnName.HOST_RSS,
                ReportColumnName.COMMUNICATION_BYTES,
                ReportColumnName.TRANSMISSIONS,
                ReportColumnName.STORAGE_BYTES,
            ),
            rows,
        ),
    )


GENERALIZATION_SCOPE_LABEL: ReportCellText = "Data/Attack Generalization Only"


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
    rows: list[tuple[ReportCellText, ...]] = []
    for method in definition.methods:
        for secondary_scenario in SecondaryScenario:
            scenario = secondary_scenario
            comparison = next(
                (
                    _comparison_result(
                        comparison_results,
                        SECONDARY_DATASET_GENERALIZATION_NAME,
                        CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
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
        name=TableName.GENERALIZATION_RESULTS,
        csv_text=csv_text(
            (
                ReportColumnName.METHOD,
                ReportColumnName.SCENARIO,
                ReportColumnName.TARGET_F1_OR_GAIN,
                ReportColumnName.SUPPORTED_HARM,
                ReportColumnName.BENIGN_FALSE_ALARM_RATE_INCREASE,
                ReportColumnName.MALICIOUS_ADMISSION,
                ReportColumnName.LEGITIMATE_ADMISSION,
                ReportColumnName.PAIRED_EFFECT_VS_FEDSIRA,
                ReportColumnName.PREDECLARED_COMPARATOR,
                ReportColumnName.ADJUSTED_P,
                ReportColumnName.MATERIALITY_PASS,
                ReportColumnName.SCOPE_LABEL,
            ),
            tuple(rows),
        ),
    )


class RenderedTable(FrozenDomainModel):
    name: TableName
    csv_text: TableCsvText


def csv_text(
    header: tuple[ReportColumnText, ...],
    rows: tuple[tuple[ReportCellText, ...], ...],
) -> TableCsvText:
    buffer = StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue().rstrip("\n")


def render_cell_metrics(
    outcomes: tuple[CellExecutionOutcome, ...],
    table_name: TableName,
    format_value: Callable[[MetricValue | None], FormattedStatisticText],
) -> RenderedTable:
    rows: list[tuple[ReportCellText, ...]] = []
    for outcome in outcomes:
        for metric_name, metric_value in outcome.metrics:
            rows.append(
                (
                    outcome.cell.experiment,
                    outcome.cell.method,
                    outcome.cell.condition,
                    f"{outcome.cell.master_seed}",
                    ("" if outcome.cell.repetition is None else f"{outcome.cell.repetition}"),
                    str(outcome.terminal_state),
                    metric_name,
                    format_value(metric_value),
                )
            )
    return RenderedTable(
        name=table_name,
        csv_text=csv_text(
            (
                ReportColumnName.EXPERIMENT,
                ReportColumnName.METHOD,
                ReportColumnName.CONDITION,
                ReportColumnName.MASTER_SEED,
                ReportColumnName.REPETITION,
                ReportColumnName.TERMINAL_STATE,
                ReportColumnName.METRIC,
                ReportColumnName.VALUE,
            ),
            tuple(rows),
        ),
    )
