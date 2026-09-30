from __future__ import annotations

import csv
from collections.abc import Callable
from enum import StrEnum
from io import StringIO

from fedsira.artifacts.paths import experiment_metric_evidence_root
from fedsira.config import PublicationRoundingConfig
from fedsira.domain.enums import (
    AblationVariant,
    BoundCondition,
    ByteUnit,
    ClaimState,
    ComparisonFamily,
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
from fedsira.domain.models import ScientificCell
from fedsira.domain.types import (
    ByteCount,
    ComparisonName,
    FormattedStatisticText,
    FrozenDomainModel,
    MasterSeed,
    MethodName,
    MetricName,
    MetricValue,
    ProtocolRuleText,
    PValue,
    ReportCellText,
    ReportColumnText,
    RowCount,
    ScenarioName,
    ScientificCellSemanticKeyTuple,
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
from fedsira.experiments.byzantine import (
    compromised_reproducer_count,
    compromised_verifier_count,
)
from fedsira.experiments.collapse import (
    CollapseDecision,
    CollapseDecisionKind,
    ResolvedCore,
)
from fedsira.experiments.definitions import (
    ADMISSION_DELAY_DECOMPOSITION_NAME,
    AGGREGATE_METRICS_PARQUET_NAME,
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
from fedsira.reporting.aggregate import (
    AggregateMetricEvidenceRow,
    read_aggregate_metric_evidence,
)
from fedsira.reporting.telemetry import EfficiencyMetricObservation, efficiency_telemetry
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


def format_median_interquartile_range(
    median: MetricValue,
    first_quartile: MetricValue,
    third_quartile: MetricValue,
    metric: MetricName,
) -> FormattedStatisticText:
    if metric in (
        DescriptiveScientificMetric.GPU_SECONDS,
        DescriptiveScientificMetric.WALL_CLOCK_SECONDS,
    ):
        decimals = _publication_rounding().seconds_decimals
        median_text = f"{median:.{decimals}f}"
        first_text = f"{first_quartile:.{decimals}f}"
        third_text = f"{third_quartile:.{decimals}f}"
    else:
        median_text = format_metric_value(median, metric)
        first_text = format_metric_value(first_quartile, metric)
        third_text = format_metric_value(third_quartile, metric)
    return f"{median_text} [{first_text},{third_text}]"


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
    columns = (
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
    )
    rows: list[tuple[ReportCellText, ...]] = []
    lineage: list[RenderedComparisonLineage] = []
    for family in comparison_results:
        for comparison in family.comparisons:
            definition = comparison.definition
            row_index = len(rows)
            rows.append(_statistical_summary_row(family, comparison))
            lineage.append(
                RenderedComparisonLineage(
                    row_index=row_index,
                    source_columns=columns,
                    experiment=definition.experiment,
                    family=family.family,
                    comparison_name=definition.comparison_name,
                    method=definition.method,
                    scenario=definition.scientific_scenario,
                    metric=definition.metric,
                    paired_master_seeds=comparison.paired_master_seeds,
                    source_cell_semantic_keys=comparison_source_semantic_keys(comparison),
                )
            )
    return RenderedTable(
        name=TableName.STATISTICAL_SUMMARY,
        csv_text=csv_text(columns, tuple(rows)),
        comparison_lineage=tuple(lineage),
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
            tuple(rows),
        ),
    )


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


class ComparisonDisplayedValue(StrEnum):
    MEAN_PAIRED_DIFFERENCE = "mean-paired-difference"
    ADJUSTED_P_VALUE = "adjusted-p-value"
    CONFIDENCE_INTERVAL_95 = "confidence-interval-95"
    COMPARISON_STATE = "comparison-state"
    MATERIALITY = "materiality"


def format_comparison_displayed_value(
    comparison: ComparisonResult | None,
    displayed: ComparisonDisplayedValue,
) -> FormattedStatisticText:
    if displayed is ComparisonDisplayedValue.MEAN_PAIRED_DIFFERENCE:
        return format_metric_value(
            None if comparison is None else comparison.mean_paired_difference
        )
    if displayed is ComparisonDisplayedValue.ADJUSTED_P_VALUE:
        return format_p_value(None if comparison is None else comparison.adjusted_p_value)
    if displayed is ComparisonDisplayedValue.CONFIDENCE_INTERVAL_95:
        return _comparison_confidence_interval(comparison)
    if displayed is ComparisonDisplayedValue.COMPARISON_STATE:
        if comparison is None:
            return ReportCellLiteral.NOT_AVAILABLE
        return comparison.comparison_state
    if displayed is ComparisonDisplayedValue.MATERIALITY:
        return _materiality_text(comparison)
    raise ValueError(f"unsupported comparison display: {displayed}")


def _comparison_cell_lineage(
    row_index: RowCount,
    column: ReportColumnName,
    displayed: ComparisonDisplayedValue,
    comparison: ComparisonResult,
) -> RenderedComparisonCellLineage:
    definition = comparison.definition
    return RenderedComparisonCellLineage(
        row_index=row_index,
        source_column=column,
        displayed_value=displayed,
        experiment=definition.experiment,
        family=definition.family,
        comparison_name=definition.comparison_name,
        method=definition.method,
        scenario=definition.scientific_scenario,
        metric=definition.metric,
    )


def _aggregate_metric_row(
    experiment: ExperimentName,
    method: MethodName,
    scenario: ScenarioName,
    metric: MetricName,
) -> AggregateMetricEvidenceRow | None:
    path = experiment_metric_evidence_root(experiment) / AGGREGATE_METRICS_PARQUET_NAME
    matches = tuple(
        row
        for row in read_aggregate_metric_evidence(path, experiment)
        if row.method == method and row.condition == scenario and row.metric == metric
    )
    if len(matches) > 1:
        raise ValueError(
            f"{experiment}/{method}/{scenario}/{metric}: duplicate aggregate metric evidence"
        )
    return matches[0] if matches else None


def _aggregate_metric_mean(
    experiment: ExperimentName,
    method: MethodName,
    scenario: ScenarioName,
    metric: MetricName,
) -> MetricValue | None:
    row = _aggregate_metric_row(experiment, method, scenario, metric)
    return None if row is None else row.mean_value


def _outcome_metric_text(
    outcomes: tuple[CellExecutionOutcome, ...],
    experiment: ExperimentName,
    method: MethodName,
    scenario: ScenarioName,
    metric: MetricName,
) -> FormattedStatisticText:
    del outcomes
    return format_metric_value(_aggregate_metric_mean(experiment, method, scenario, metric), metric)


def _outcome_metric_confidence_interval(
    outcomes: tuple[CellExecutionOutcome, ...],
    experiment: ExperimentName,
    method: MethodName,
    scenario: ScenarioName,
    metric: ComparisonMetric,
) -> FormattedStatisticText:
    del outcomes
    row = _aggregate_metric_row(experiment, method, scenario, metric)
    return format_aggregate_statistic(row, AggregateDisplayStatistic.CONFIDENCE_INTERVAL_95)


def _efficiency_timing_summary(
    observations: tuple[EfficiencyMetricObservation, ...],
    method: MethodName,
    metric: MetricName,
) -> FormattedStatisticText:
    observation = next(
        (item for item in observations if item.method == method and item.metric == metric),
        None,
    )
    if observation is None:
        return ReportCellLiteral.NOT_AVAILABLE
    return format_median_interquartile_range(
        observation.median,
        observation.first_quartile,
        observation.third_quartile,
        metric,
    )


def _descriptive_timing_value(
    outcomes: tuple[CellExecutionOutcome, ...],
    experiment: ExperimentName,
    method: MethodName,
    scenario: ScenarioName,
    metric: MetricName,
    efficiency_observations: tuple[EfficiencyMetricObservation, ...],
) -> FormattedStatisticText:
    if experiment == EFFICIENCY_MEASUREMENT_NAME:
        return _efficiency_timing_summary(efficiency_observations, method, metric)
    del outcomes
    return format_metric_value(_aggregate_metric_mean(experiment, method, scenario, metric), metric)


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
    del outcomes, comparison_results
    row = _aggregate_metric_row(experiment, method, scenario, metric)
    return format_aggregate_statistic(
        row,
        AggregateDisplayStatistic.MEAN_AND_SAMPLE_STANDARD_DEVIATION,
    )


def render_primary_results_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    outcomes: tuple[CellExecutionOutcome, ...],
) -> RenderedTable:
    definition = experiment_by_name(PRIMARY_CONFIRMATORY_EVALUATION_NAME)
    methods_scenarios = tuple(
        (method, scenario) for scenario in definition.conditions for method in definition.methods
    )
    expected = frozenset(methods_scenarios)
    observed = frozenset(
        (comparison.definition.method, comparison.definition.scientific_scenario)
        for family in comparison_results
        for comparison in family.comparisons
        if comparison.definition.experiment == PRIMARY_CONFIRMATORY_EVALUATION_NAME
    ) | frozenset(
        (outcome.cell.method, outcome.cell.condition)
        for outcome in outcomes
        if outcome.cell.experiment == PRIMARY_CONFIRMATORY_EVALUATION_NAME
    )
    if not observed.issubset(expected):
        raise ValueError(
            "Primary Results table: observed evidence is outside the registered design"
        )
    rows: list[tuple[ReportCellText, ...]] = []
    aggregate_lineage: list[RenderedAggregateCellLineage] = []
    for row_index, (method, scenario) in enumerate(methods_scenarios):
        rows.append(
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
        )
        for column, metric, statistic in (
            (
                ReportColumnName.TARGET_F1_MEAN,
                ComparisonMetric.TARGET_F1,
                AggregateDisplayStatistic.MEAN_AND_SAMPLE_STANDARD_DEVIATION,
            ),
            (
                ReportColumnName.TARGET_F1_95_CI,
                ComparisonMetric.TARGET_F1,
                AggregateDisplayStatistic.CONFIDENCE_INTERVAL_95,
            ),
            (
                ReportColumnName.SUPPORTED_MACRO_F1_HARM,
                ComparisonMetric.SUPPORTED_MACRO_F1_HARM,
                AggregateDisplayStatistic.MEAN_AND_SAMPLE_STANDARD_DEVIATION,
            ),
            (
                ReportColumnName.BENIGN_FALSE_ALARM_RATE_INCREASE,
                ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE,
                AggregateDisplayStatistic.MEAN_AND_SAMPLE_STANDARD_DEVIATION,
            ),
            (
                ComparisonMetric.ATTACK_SUCCESS_RATE,
                ComparisonMetric.ATTACK_SUCCESS_RATE,
                AggregateDisplayStatistic.MEAN_AND_SAMPLE_STANDARD_DEVIATION,
            ),
            (
                ReportColumnName.MALICIOUS_ADMISSION,
                ComparisonMetric.MALICIOUS_ADMISSION,
                AggregateDisplayStatistic.MEAN_AND_SAMPLE_STANDARD_DEVIATION,
            ),
            (
                ReportColumnName.LEGITIMATE_ADMISSION,
                ComparisonMetric.LEGITIMATE_ADMISSION,
                AggregateDisplayStatistic.MEAN_AND_SAMPLE_STANDARD_DEVIATION,
            ),
            (
                ReportColumnName.WORST_DOMAIN_TARGET_F1,
                ComparisonMetric.WORST_DOMAIN_TARGET_F1,
                AggregateDisplayStatistic.MEAN_AND_SAMPLE_STANDARD_DEVIATION,
            ),
        ):
            aggregate_lineage.append(
                RenderedAggregateCellLineage(
                    row_index=row_index,
                    source_column=column,
                    experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                    method=method,
                    scenario=scenario,
                    metric=metric,
                    statistic=statistic,
                )
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
            tuple(rows),
        ),
        aggregate_lineage=tuple(aggregate_lineage),
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
        else ("Survives" if source_exclusion_decision.survives else ClaimState.NOT_SUPPORTED)
    )
    methods = experiment_by_name(SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME).methods
    source_scenario = PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT
    target_noninferiority_status: FormattedStatisticText = ReportCellLiteral.NOT_AVAILABLE
    target_noninferiority_comparison = _comparison_result(
        comparison_results,
        SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
        SourceExclusionMethod.FULL_FEDSIRA,
        source_scenario,
        ComparisonMetric.TARGET_F1,
    )
    if target_noninferiority_comparison is not None:
        target_noninferiority_status = format_comparison_displayed_value(
            target_noninferiority_comparison,
            ComparisonDisplayedValue.COMPARISON_STATE,
        )
    rows: list[tuple[ReportCellText, ...]] = []
    aggregate_lineage: list[RenderedAggregateCellLineage] = []
    comparison_cell_lineage: list[RenderedComparisonCellLineage] = []
    for row_index, method in enumerate(methods):
        source_asr_comparison = _comparison_result(
            comparison_results,
            SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
            method,
            source_scenario,
            ComparisonMetric.ATTACK_SUCCESS_RATE,
        )
        rows.append(
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
                format_comparison_displayed_value(
                    source_asr_comparison,
                    ComparisonDisplayedValue.MEAN_PAIRED_DIFFERENCE,
                ),
                format_comparison_displayed_value(
                    source_asr_comparison,
                    ComparisonDisplayedValue.ADJUSTED_P_VALUE,
                ),
                format_comparison_displayed_value(
                    source_asr_comparison,
                    ComparisonDisplayedValue.CONFIDENCE_INTERVAL_95,
                ),
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
        )
        for column, metric in (
            (ReportColumnName.POST_PRODUCTION_ASR, ComparisonMetric.ATTACK_SUCCESS_RATE),
            (ReportColumnName.TARGET_F1, ComparisonMetric.TARGET_F1),
            (ReportColumnName.SUPPORTED_F1_HARM, ComparisonMetric.SUPPORTED_MACRO_F1_HARM),
            (
                ReportColumnName.BENIGN_FPR_INCREASE,
                ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE,
            ),
        ):
            aggregate_lineage.append(
                RenderedAggregateCellLineage(
                    row_index=row_index,
                    source_column=column,
                    experiment=SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
                    method=method,
                    scenario=source_scenario,
                    metric=metric,
                    statistic=AggregateDisplayStatistic.MEAN_AND_SAMPLE_STANDARD_DEVIATION,
                )
            )
        if source_asr_comparison is not None:
            comparison_cell_lineage.extend(
                _comparison_cell_lineage(
                    row_index,
                    column,
                    displayed,
                    source_asr_comparison,
                )
                for column, displayed in (
                    (
                        ReportColumnName.ASR_DIFFERENCE_VS_FEDSIRA,
                        ComparisonDisplayedValue.MEAN_PAIRED_DIFFERENCE,
                    ),
                    (ReportColumnName.ADJUSTED_P, ComparisonDisplayedValue.ADJUSTED_P_VALUE),
                    (
                        ReportColumnName.CONFIDENCE_INTERVAL_95,
                        ComparisonDisplayedValue.CONFIDENCE_INTERVAL_95,
                    ),
                )
            )
        if (
            method == SourceExclusionMethod.FULL_FEDSIRA
            and target_noninferiority_comparison is not None
        ):
            comparison_cell_lineage.append(
                _comparison_cell_lineage(
                    row_index,
                    ReportColumnName.TARGET_NONINFERIORITY_PASS,
                    ComparisonDisplayedValue.COMPARISON_STATE,
                    target_noninferiority_comparison,
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
            tuple(rows),
        ),
        aggregate_lineage=tuple(aggregate_lineage),
        comparison_cell_lineage=tuple(comparison_cell_lineage),
    )


def render_ablation_results_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    outcomes: tuple[CellExecutionOutcome, ...],
) -> RenderedTable:
    rows: list[tuple[ReportCellText, ...]] = []
    aggregate_lineage: list[RenderedAggregateCellLineage] = []
    comparison_cell_lineage: list[RenderedComparisonCellLineage] = []
    for variant in AblationVariant:
        scenario = ablation_scenario_for_variant(variant)
        row_index = len(rows)
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
                    else format_comparison_displayed_value(
                        comparison,
                        ComparisonDisplayedValue.MEAN_PAIRED_DIFFERENCE,
                    )
                ),
                (
                    "reference row"
                    if is_reference
                    else format_comparison_displayed_value(
                        comparison,
                        ComparisonDisplayedValue.ADJUSTED_P_VALUE,
                    )
                ),
                (
                    "reference row"
                    if is_reference
                    else format_comparison_displayed_value(
                        comparison,
                        ComparisonDisplayedValue.MATERIALITY,
                    )
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
        for column, aggregate_metric in (
            (ReportColumnName.TARGET_F1, ComparisonMetric.TARGET_F1),
            (ReportColumnName.SUPPORTED_HARM, ComparisonMetric.SUPPORTED_MACRO_F1_HARM),
            (ReportColumnName.ASR_OR_MALICIOUS_ADMISSION, ComparisonMetric.ATTACK_SUCCESS_RATE),
        ):
            aggregate_lineage.append(
                RenderedAggregateCellLineage(
                    row_index=row_index,
                    source_column=column,
                    experiment=MECHANISM_ABLATION_NAME,
                    method=variant,
                    scenario=scenario,
                    metric=aggregate_metric,
                    statistic=AggregateDisplayStatistic.MEAN_AND_SAMPLE_STANDARD_DEVIATION,
                )
            )
        if not is_reference and comparison is not None:
            comparison_cell_lineage.extend(
                _comparison_cell_lineage(row_index, column, displayed, comparison)
                for column, displayed in (
                    (
                        ReportColumnName.DIFFERENCE_FROM_FULL_REFERENCE,
                        ComparisonDisplayedValue.MEAN_PAIRED_DIFFERENCE,
                    ),
                    (ReportColumnName.ADJUSTED_P, ComparisonDisplayedValue.ADJUSTED_P_VALUE),
                    (ReportColumnName.MATERIALITY_PASS, ComparisonDisplayedValue.MATERIALITY),
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
        aggregate_lineage=tuple(aggregate_lineage),
        comparison_cell_lineage=tuple(comparison_cell_lineage),
    )


class ByzantineBoundaryRow(FrozenDomainModel):
    bound_status: ReportCellText
    compromised_count: RowCount
    strategy: ScenarioName


BOUND_CONDITION_DESIGN: tuple[tuple[BoundCondition, RowCount, ReportCellText], ...] = (
    (BoundCondition.ONE_BYZANTINE_REPRODUCER_WITHIN_BOUND, 1, "Within Bound"),
    (BoundCondition.TWO_BYZANTINE_REPRODUCERS_ABOVE_BOUND, 2, "Above Bound"),
    (BoundCondition.ONE_BYZANTINE_VERIFIER_WITHIN_BOUND, 1, "Within Bound"),
    (BoundCondition.TWO_BYZANTINE_VERIFIERS_ABOVE_BOUND, 2, "Above Bound"),
)


def _byzantine_boundary(
    experiment: ExperimentName,
    condition: ScenarioName,
) -> ByzantineBoundaryRow:
    config = current_application_context().scientific_config
    if experiment == BYZANTINE_BOUND_VIOLATION_NAME:
        for bound_condition, compromised_count, bound_status in BOUND_CONDITION_DESIGN:
            if bound_condition == condition:
                return ByzantineBoundaryRow(
                    bound_status=bound_status,
                    compromised_count=compromised_count,
                    strategy=condition,
                )
    elif experiment == COMPROMISED_REPRODUCER_ROBUSTNESS_NAME:
        limit = config.protocol.synthesis.maximum_byzantine_reproduction_rows
        compromised = compromised_reproducer_count(condition)
        return ByzantineBoundaryRow(
            bound_status="Within Bound" if compromised <= limit else "Above Bound",
            compromised_count=compromised,
            strategy=condition,
        )
    elif experiment == COMPROMISED_VERIFIER_ROBUSTNESS_NAME:
        limit = config.protocol.verification.maximum_byzantine_verifiers_per_panel
        compromised = compromised_verifier_count(condition)
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
    del comparison_results
    rows: list[tuple[ReportCellText, ...]] = []
    aggregate_lineage: list[RenderedAggregateCellLineage] = []
    identities = tuple(
        (experiment, method, condition)
        for experiment in (
            COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
            COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
            BYZANTINE_BOUND_VIOLATION_NAME,
        )
        for definition in (experiment_by_name(experiment),)
        for method in definition.methods
        for condition in definition.conditions
    )
    identities = tuple(
        sorted(
            identities,
            key=lambda identity: (
                _byzantine_boundary(identity[0], identity[2]).bound_status != "Within Bound",
                _byzantine_boundary(identity[0], identity[2]).compromised_count,
                identity[0],
                identity[1],
                identity[2],
            ),
        )
    )
    for row_index, (experiment, method, condition) in enumerate(identities):
        boundary = _byzantine_boundary(experiment, condition)
        rows.append(
            (
                experiment,
                method,
                condition,
                boundary.bound_status,
                str(boundary.compromised_count),
                boundary.strategy,
                _outcome_summary_or_comparison(
                    outcomes,
                    (),
                    experiment,
                    method,
                    condition,
                    ComparisonMetric.MALICIOUS_ADMISSION,
                ),
                _outcome_summary_or_comparison(
                    outcomes,
                    (),
                    experiment,
                    method,
                    condition,
                    ComparisonMetric.LEGITIMATE_ADMISSION,
                ),
                _outcome_summary_or_comparison(
                    outcomes,
                    (),
                    experiment,
                    method,
                    condition,
                    ComparisonMetric.ATTACK_SUCCESS_RATE,
                ),
                _outcome_summary_or_comparison(
                    outcomes,
                    (),
                    experiment,
                    method,
                    condition,
                    ComparisonMetric.TARGET_F1,
                ),
                _outcome_metric_text(
                    outcomes,
                    experiment,
                    method,
                    condition,
                    DescriptiveScientificMetric.CERTIFIED_ROW_YIELD,
                ),
                _outcome_metric_text(
                    outcomes,
                    experiment,
                    method,
                    condition,
                    DescriptiveScientificMetric.DORMANT_ADMISSION_RATE,
                ),
                _completed_outcome_count(outcomes, experiment, method, condition),
            )
        )
        for column, metric, statistic in (
            (
                ReportColumnName.MALICIOUS_ADMISSION,
                ComparisonMetric.MALICIOUS_ADMISSION,
                AggregateDisplayStatistic.MEAN_AND_SAMPLE_STANDARD_DEVIATION,
            ),
            (
                ReportColumnName.LEGITIMATE_ADMISSION,
                ComparisonMetric.LEGITIMATE_ADMISSION,
                AggregateDisplayStatistic.MEAN_AND_SAMPLE_STANDARD_DEVIATION,
            ),
            (
                ComparisonMetric.ATTACK_SUCCESS_RATE,
                ComparisonMetric.ATTACK_SUCCESS_RATE,
                AggregateDisplayStatistic.MEAN_AND_SAMPLE_STANDARD_DEVIATION,
            ),
            (
                ReportColumnName.TARGET_F1,
                ComparisonMetric.TARGET_F1,
                AggregateDisplayStatistic.MEAN_AND_SAMPLE_STANDARD_DEVIATION,
            ),
            (
                ReportColumnName.CERTIFIED_YIELD,
                DescriptiveScientificMetric.CERTIFIED_ROW_YIELD,
                AggregateDisplayStatistic.MEAN_VALUE,
            ),
            (
                ReportColumnName.DORMANT_RATE,
                DescriptiveScientificMetric.DORMANT_ADMISSION_RATE,
                AggregateDisplayStatistic.MEAN_VALUE,
            ),
        ):
            aggregate_lineage.append(
                RenderedAggregateCellLineage(
                    row_index=row_index,
                    source_column=column,
                    experiment=experiment,
                    method=method,
                    scenario=condition,
                    metric=metric,
                    statistic=statistic,
                )
            )
    return RenderedTable(
        name=TableName.BYZANTINE_ROBUSTNESS,
        csv_text=csv_text(
            (
                ReportColumnName.EXPERIMENT,
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
        aggregate_lineage=tuple(aggregate_lineage),
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
    aggregate_lineage: list[RenderedAggregateCellLineage] = []
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
                is_oracle_experiment = experiment == SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME
                row_index = len(rows)
                rows.append(
                    (
                        experiment,
                        method,
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
                for column, metric in (
                    (ReportColumnName.ADMISSION_DORMANCY, ComparisonMetric.LEGITIMATE_ADMISSION),
                    (ReportColumnName.TARGET_F1, ComparisonMetric.TARGET_F1),
                    (ReportColumnName.WORST_DOMAIN_F1, ComparisonMetric.WORST_DOMAIN_TARGET_F1),
                ):
                    aggregate_lineage.append(
                        RenderedAggregateCellLineage(
                            row_index=row_index,
                            source_column=column,
                            experiment=experiment,
                            method=method,
                            scenario=condition,
                            metric=metric,
                            statistic=AggregateDisplayStatistic.MEAN_AND_SAMPLE_STANDARD_DEVIATION,
                        )
                    )
                if is_oracle_experiment:
                    aggregate_lineage.append(
                        RenderedAggregateCellLineage(
                            row_index=row_index,
                            source_column=ReportColumnName.CLEAN_ORACLE_ERROR,
                            experiment=experiment,
                            method=method,
                            scenario=condition,
                            metric=ComparisonMetric.TARGET_F1,
                            statistic=AggregateDisplayStatistic.MEAN_AND_SAMPLE_STANDARD_DEVIATION,
                        )
                    )
    return RenderedTable(
        name=TableName.FAILURE_BOUNDARIES,
        csv_text=csv_text(
            (
                ReportColumnName.BOUNDARY_FAMILY,
                ReportColumnName.METHOD,
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
        aggregate_lineage=tuple(aggregate_lineage),
    )


def render_delay_and_efficiency_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    outcomes: tuple[CellExecutionOutcome, ...],
    efficiency_observations: tuple[EfficiencyMetricObservation, ...] = (),
) -> RenderedTable:
    if not efficiency_observations:
        efficiency_observations = efficiency_telemetry(outcomes)
    aggregate_lineage: list[RenderedAggregateCellLineage] = []
    rows_to_render: list[tuple[ExperimentName, MethodName, ScenarioName]] = []
    del comparison_results
    for experiment in (
        ADMISSION_DELAY_DECOMPOSITION_NAME,
        EFFICIENCY_MEASUREMENT_NAME,
    ):
        definition = experiment_by_name(experiment)
        rows_to_render.extend(
            (experiment, method, scenario)
            for method in definition.methods
            for scenario in definition.conditions
        )
    rows = tuple(
        (
            experiment,
            method,
            scenario,
            format_metric_value(
                _aggregate_metric_mean(
                    experiment,
                    method,
                    scenario,
                    DescriptiveScientificMetric.T_EVIDENCE,
                )
            ),
            _descriptive_timing_value(
                outcomes,
                experiment,
                method,
                scenario,
                DelayPhaseMetric.ASSIGNMENT_SECONDS,
                efficiency_observations,
            ),
            _descriptive_timing_value(
                outcomes,
                experiment,
                method,
                scenario,
                DelayPhaseMetric.REPRODUCE_SECONDS,
                efficiency_observations,
            ),
            _descriptive_timing_value(
                outcomes,
                experiment,
                method,
                scenario,
                DelayPhaseMetric.VERIFY_SECONDS,
                efficiency_observations,
            ),
            _descriptive_timing_value(
                outcomes,
                experiment,
                method,
                scenario,
                DelayPhaseMetric.SYNTHESIZE_SECONDS,
                efficiency_observations,
            ),
            _descriptive_timing_value(
                outcomes,
                experiment,
                method,
                scenario,
                DescriptiveScientificMetric.WALL_CLOCK_SECONDS,
                efficiency_observations,
            ),
            _descriptive_timing_value(
                outcomes,
                experiment,
                method,
                scenario,
                DescriptiveScientificMetric.GPU_SECONDS,
                efficiency_observations,
            ),
            _descriptive_timing_value(
                outcomes,
                experiment,
                method,
                scenario,
                DescriptiveScientificMetric.PEAK_GPU_MEMORY_BYTES,
                efficiency_observations,
            ),
            _descriptive_timing_value(
                outcomes,
                experiment,
                method,
                scenario,
                DescriptiveScientificMetric.PEAK_HOST_RSS_BYTES,
                efficiency_observations,
            ),
            _descriptive_timing_value(
                outcomes,
                experiment,
                method,
                scenario,
                DescriptiveScientificMetric.COMMUNICATION_BYTES,
                efficiency_observations,
            ),
            _descriptive_timing_value(
                outcomes,
                experiment,
                method,
                scenario,
                DescriptiveScientificMetric.MODEL_TRANSMISSIONS,
                efficiency_observations,
            ),
            _descriptive_timing_value(
                outcomes,
                experiment,
                method,
                scenario,
                DescriptiveScientificMetric.PERSISTENT_STORAGE_BYTES,
                efficiency_observations,
            ),
        )
        for experiment, method, scenario in rows_to_render
    )
    delay_metrics: tuple[tuple[ReportColumnName, MetricName], ...] = (
        (ReportColumnName.T_EVIDENCE, DescriptiveScientificMetric.T_EVIDENCE),
        (ReportColumnName.ASSIGNMENT_SECONDS, DelayPhaseMetric.ASSIGNMENT_SECONDS),
        (ReportColumnName.REPRODUCTION_SECONDS, DelayPhaseMetric.REPRODUCE_SECONDS),
        (ReportColumnName.VERIFICATION_SECONDS, DelayPhaseMetric.VERIFY_SECONDS),
        (ReportColumnName.SYNTHESIS_SECONDS, DelayPhaseMetric.SYNTHESIZE_SECONDS),
        (ReportColumnName.POST_EVIDENCE_WALL_CLOCK, DescriptiveScientificMetric.WALL_CLOCK_SECONDS),
        (ReportColumnName.GPU_SECONDS, DescriptiveScientificMetric.GPU_SECONDS),
        (ReportColumnName.PEAK_GPU_MEMORY, DescriptiveScientificMetric.PEAK_GPU_MEMORY_BYTES),
        (ReportColumnName.HOST_RSS, DescriptiveScientificMetric.PEAK_HOST_RSS_BYTES),
        (ReportColumnName.COMMUNICATION_BYTES, DescriptiveScientificMetric.COMMUNICATION_BYTES),
        (ReportColumnName.TRANSMISSIONS, DescriptiveScientificMetric.MODEL_TRANSMISSIONS),
        (ReportColumnName.STORAGE_BYTES, DescriptiveScientificMetric.PERSISTENT_STORAGE_BYTES),
    )
    for row_index, (experiment, method, scenario) in enumerate(rows_to_render):
        if experiment == ADMISSION_DELAY_DECOMPOSITION_NAME:
            aggregate_lineage.extend(
                RenderedAggregateCellLineage(
                    row_index=row_index,
                    source_column=column,
                    experiment=experiment,
                    method=method,
                    scenario=scenario,
                    metric=metric,
                    statistic=AggregateDisplayStatistic.MEAN_VALUE,
                )
                for column, metric in delay_metrics
            )
            continue
        if experiment != EFFICIENCY_MEASUREMENT_NAME:
            continue
        for metric_index, (column, metric) in enumerate(delay_metrics):
            aggregate_row = _aggregate_metric_row(experiment, method, scenario, metric)
            if aggregate_row is None:
                continue
            statistic = (
                AggregateDisplayStatistic.MEAN_VALUE
                if metric is DescriptiveScientificMetric.T_EVIDENCE
                else AggregateDisplayStatistic.MEDIAN_AND_INTERQUARTILE_RANGE
            )
            if rows[row_index][metric_index + 3] != format_aggregate_statistic(
                aggregate_row,
                statistic,
                metric,
            ):
                continue
            aggregate_lineage.append(
                RenderedAggregateCellLineage(
                    row_index=row_index,
                    source_column=column,
                    experiment=experiment,
                    method=method,
                    scenario=scenario,
                    metric=metric,
                    statistic=statistic,
                )
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
        aggregate_lineage=tuple(aggregate_lineage),
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
    aggregate_lineage: list[RenderedAggregateCellLineage] = []
    for method in definition.methods:
        for secondary_scenario in SecondaryScenario:
            scenario = secondary_scenario
            row_index = len(rows)
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
            for column, metric in (
                (ReportColumnName.TARGET_F1_OR_GAIN, ComparisonMetric.TARGET_F1),
                (ReportColumnName.SUPPORTED_HARM, ComparisonMetric.SUPPORTED_MACRO_F1_HARM),
                (
                    ReportColumnName.BENIGN_FALSE_ALARM_RATE_INCREASE,
                    ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE,
                ),
                (ReportColumnName.MALICIOUS_ADMISSION, ComparisonMetric.MALICIOUS_ADMISSION),
                (ReportColumnName.LEGITIMATE_ADMISSION, ComparisonMetric.LEGITIMATE_ADMISSION),
            ):
                aggregate_lineage.append(
                    RenderedAggregateCellLineage(
                        row_index=row_index,
                        source_column=column,
                        experiment=SECONDARY_DATASET_GENERALIZATION_NAME,
                        method=method,
                        scenario=scenario,
                        metric=metric,
                        statistic=AggregateDisplayStatistic.MEAN_AND_SAMPLE_STANDARD_DEVIATION,
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
        aggregate_lineage=tuple(aggregate_lineage),
    )


class RenderedTable(FrozenDomainModel):
    name: TableName
    csv_text: TableCsvText
    comparison_lineage: tuple[RenderedComparisonLineage, ...] = ()
    comparison_cell_lineage: tuple[RenderedComparisonCellLineage, ...] = ()
    aggregate_lineage: tuple[RenderedAggregateCellLineage, ...] = ()


class RenderedComparisonLineage(FrozenDomainModel):
    row_index: RowCount
    source_columns: tuple[ReportColumnName, ...]
    experiment: ExperimentName
    family: ComparisonFamily
    comparison_name: ComparisonName
    method: MethodName
    scenario: ScenarioName
    metric: MetricName
    paired_master_seeds: tuple[MasterSeed, ...]
    source_cell_semantic_keys: ScientificCellSemanticKeyTuple


class RenderedComparisonCellLineage(FrozenDomainModel):
    row_index: RowCount
    source_column: ReportColumnName
    displayed_value: ComparisonDisplayedValue
    experiment: ExperimentName
    family: ComparisonFamily
    comparison_name: ComparisonName
    method: MethodName
    scenario: ScenarioName
    metric: ComparisonMetric


class AggregateDisplayStatistic(StrEnum):
    MEAN_VALUE = "mean-value"
    MEAN_AND_SAMPLE_STANDARD_DEVIATION = "mean-and-sample-standard-deviation"
    CONFIDENCE_INTERVAL_95 = "confidence-interval-95"
    MEDIAN_AND_INTERQUARTILE_RANGE = "median-and-interquartile-range"


class RenderedAggregateCellLineage(FrozenDomainModel):
    row_index: RowCount
    source_column: ReportColumnName | ComparisonMetric
    experiment: ExperimentName
    method: MethodName
    scenario: ScenarioName
    metric: MetricName
    statistic: AggregateDisplayStatistic


def format_aggregate_statistic(
    row: AggregateMetricEvidenceRow | None,
    statistic: AggregateDisplayStatistic,
    metric: MetricName | None = None,
) -> FormattedStatisticText:
    if row is None:
        return ReportCellLiteral.NOT_AVAILABLE
    if statistic is AggregateDisplayStatistic.MEAN_VALUE:
        return format_metric_value(row.mean_value, metric)
    if statistic is AggregateDisplayStatistic.CONFIDENCE_INTERVAL_95:
        if row.confidence_interval_lower is None or row.confidence_interval_upper is None:
            return ReportCellLiteral.NOT_AVAILABLE
        return f"[{row.confidence_interval_lower:.3f},{row.confidence_interval_upper:.3f}]"
    if statistic is AggregateDisplayStatistic.MEDIAN_AND_INTERQUARTILE_RANGE:
        if metric is None:
            raise ValueError("median/IQR display requires its metric identity")
        return format_median_interquartile_range(
            row.median_value,
            row.first_quartile,
            row.third_quartile,
            metric,
        )
    if statistic is AggregateDisplayStatistic.MEAN_AND_SAMPLE_STANDARD_DEVIATION:
        decimals = _publication_rounding().f1_accuracy_rates_decimals
        return f"{row.mean_value:.{decimals}f} ± {row.sample_standard_deviation:.{decimals}f}"
    raise ValueError(f"unsupported aggregate display statistic: {statistic}")


def comparison_source_semantic_keys(
    comparison: ComparisonResult,
) -> ScientificCellSemanticKeyTuple:
    definition = comparison.definition
    keys = [
        ScientificCell(
            experiment=definition.experiment,
            method=definition.method,
            condition=definition.scientific_scenario,
            master_seed=seed,
        ).semantic_key
        for seed in comparison.paired_master_seeds
    ]
    if definition.reference_kind is ComparisonReferenceKind.SCIENTIFIC_CELL:
        keys.extend(
            ScientificCell(
                experiment=definition.reference_experiment,
                method=definition.reference_method,
                condition=definition.reference_scenario,
                master_seed=seed,
            ).semantic_key
            for seed in comparison.paired_master_seeds
        )
    return tuple(keys)


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
