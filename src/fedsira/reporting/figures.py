from __future__ import annotations

import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import TypeAlias

import numpy
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from fedsira.domain.enums import (
    AdmissionState,
    CoreMethodIdentity,
    DelayPhaseMetric,
    DescriptiveScientificMetric,
    ExperimentLifecycleState,
    ExperimentName,
    FigureAxisName,
    FigureLegendLabel,
    FigureName,
    FigurePanelTitle,
    HeterogeneityRegime,
    MetricObservationKey,
    PrimaryScenario,
    ProtocolSchematicStage,
    ReportCellLiteral,
    RootCauseMixture,
    VerifierCondition,
)
from fedsira.domain.types import (
    AttackStrength,
    EvidenceCycleIndex,
    FigureAnnotationText,
    FigureAxisLabel,
    FigureLegendText,
    FrozenDomainModel,
    MethodName,
    MetricName,
    MetricValue,
    Probability,
    ProtocolRuleText,
    ReproductionRowCount,
    ScenarioName,
    ScientificCellCount,
)
from fedsira.evaluation.comparisons import (
    CapabilityContractScope,
    ComparisonFamilyResult,
    ComparisonMetric,
    ComparisonResult,
)
from fedsira.evaluation.statistics import bootstrap_percentile_confidence_interval
from fedsira.experiments.definitions import (
    ADMISSION_DELAY_DECOMPOSITION_FIGURE_NAME,
    ADMISSION_DELAY_DECOMPOSITION_NAME,
    CAPABILITY_GRANULARITY_BOUNDARY_FIGURE_NAME,
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    COLLAPSE_DECISION_EFFECTS_FIGURE_NAME,
    COLLAPSE_EXPERIMENT_NAMES,
    COMPROMISED_REPRODUCER_BOUNDARY_FIGURE_NAME,
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_BOUNDARY_FIGURE_NAME,
    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    EFFICIENCY_PROFILE_FIGURE_NAME,
    EVIDENCE_ARRIVAL_STATE_TRAJECTORY_FIGURE_NAME,
    EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
    HETEROGENEITY_SYNTHESIS_BOUNDARY_FIGURE_NAME,
    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    PRIMARY_SECURITY_UTILITY_TRADEOFF_FIGURE_NAME,
    PROTOCOL_SCHEMATIC_FIGURE_NAME,
    SECONDARY_DATASET_GENERALIZATION_NAME,
    SECONDARY_GENERALIZATION_FIGURE_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
    SHARED_EPISTEMIC_FAILURE_FIGURE_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    USEFUL_BACKDOORED_SOURCE_FIGURE_NAME,
    EpistemicFailureType,
)
from fedsira.experiments.engine import (
    CellExecutionOutcome,
    ExecutionRecordStore,
    ExperimentExecutionResult,
)
from fedsira.experiments.planning import ExperimentPlan
from fedsira.runtime import current_application_context

BoundarySeries: TypeAlias = tuple[
    tuple[FigureLegendText, tuple[ScientificCellCount, ...], tuple[MetricValue | None, ...]],
    ...,
]
AxisDraw: TypeAlias = Callable[[Axes], None]


class EvidenceStateFraction(FrozenDomainModel):
    condition: ScenarioName
    cycle: EvidenceCycleIndex
    state: AdmissionState
    fraction: Probability


class EfficiencyMetricObservation(FrozenDomainModel):
    method: MethodName
    metric: MetricName
    median: MetricValue
    first_quartile: MetricValue
    third_quartile: MetricValue
    seed_count: ScientificCellCount


MANDATORY_FIGURE_NAMES: tuple[FigureName, ...] = (
    FigureName.PROTOCOL_SCHEMATIC,
    FigureName.PRIMARY_SECURITY_UTILITY_TRADEOFF,
    FigureName.USEFUL_BACKDOORED_SOURCE,
    FigureName.COLLAPSE_DECISION_EFFECTS,
    FigureName.COMPROMISED_REPRODUCER_BOUNDARY,
    FigureName.COMPROMISED_VERIFIER_BOUNDARY,
    FigureName.EVIDENCE_ARRIVAL_STATE_TRAJECTORY,
    FigureName.SHARED_EPISTEMIC_FAILURE,
    FigureName.CAPABILITY_GRANULARITY_BOUNDARY,
    FigureName.HETEROGENEITY_SYNTHESIS_BOUNDARY,
    FigureName.ADMISSION_DELAY_DECOMPOSITION,
    FigureName.EFFICIENCY_PROFILE,
    FigureName.SECONDARY_GENERALIZATION,
)
FIGURE_ANNOTATION_INSET: Probability = 1 / 100
PROTOCOL_SCHEMATIC_DESCRIPTION_WIDTH = 12


def state_fraction(
    observations: tuple[EvidenceStateFraction, ...],
    condition: ScenarioName,
    cycle: EvidenceCycleIndex,
    state: AdmissionState,
) -> Probability:
    for observation in observations:
        if (
            observation.condition == condition
            and observation.cycle == cycle
            and observation.state is state
        ):
            return observation.fraction
    return 0.0


def efficiency_observation(
    observations: tuple[EfficiencyMetricObservation, ...],
    method: MethodName,
    metric: MetricName,
) -> EfficiencyMetricObservation:
    for observation in observations:
        if observation.method == method and observation.metric == metric:
            return observation
    raise ValueError(f"missing efficiency telemetry for {method} / {metric}")


def validate_mandatory_figures_covered(
    rendered_figures: tuple[Path, ...],
) -> tuple[FigureName, ...]:
    rendered_names = frozenset(path.stem for path in rendered_figures)
    return tuple(name for name in MANDATORY_FIGURE_NAMES if name not in rendered_names)


PROTOCOL_SCHEMATIC_STEPS: tuple[tuple[ProtocolSchematicStage, ProtocolRuleText], ...] = (
    (
        ProtocolSchematicStage.SOURCE_COMMITMENT,
        "immutable source artifact committed with direct production weight exactly 0.0",
    ),
    (
        ProtocolSchematicStage.FIXED_CAPABILITY_CONTRACT,
        "immutable Capability Contract identity published once the opening is complete",
    ),
    (
        ProtocolSchematicStage.NON_SOURCE_REPRODUCTION,
        "non-source candidate domains reproduced once in Reproducer Order",
    ),
    (
        ProtocolSchematicStage.POST_COMMITMENT_VERIFIER_PANELS,
        "three-member verifier panels assigned strictly after the reproduction commitment",
    ),
    (
        ProtocolSchematicStage.EXTERNAL_REPRODUCTION_VERIFICATION,
        "committed reproduction rows certified by independent external reports",
    ),
    (
        ProtocolSchematicStage.KRUM,
        "source-excluded Krum synthesis whenever the resolved path requires plurality",
    ),
    (
        ProtocolSchematicStage.FINAL_FRESH_GATE,
        "fresh final-gate domains evaluate the constructed production update",
    ),
    (
        ProtocolSchematicStage.ADMISSION_DORMANCY_OR_REJECTION,
        "production authority, continued dormancy awaiting evidence, or terminal rejection",
    ),
)


def render_protocol_schematic(destination: Path) -> Path:
    figure = Figure(figsize=(10, 2.5))
    axis = figure.add_subplot(1, 1, 1)
    axis.axis("off")
    for index, (stage, description) in enumerate(PROTOCOL_SCHEMATIC_STEPS):
        x_position = index * 1.25
        axis.text(x_position, 0.5, stage, ha="center", va="center", fontsize=8)
        axis.text(
            x_position,
            0.25,
            textwrap.fill(description, PROTOCOL_SCHEMATIC_DESCRIPTION_WIDTH),
            ha="center",
            va="center",
            fontsize=5,
        )
        if index < len(PROTOCOL_SCHEMATIC_STEPS) - 1:
            axis.plot((x_position + 0.45, x_position + 0.8), (0.5, 0.5))
    axis.set_xlim(-0.5, (len(PROTOCOL_SCHEMATIC_STEPS) - 1) * 1.25 + 0.5)
    axis.set_ylim(0.0, 1.0)
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    return destination


def render_security_utility_tradeoff(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    destination: Path,
) -> Path:
    figure = Figure(figsize=(12, 4))
    metrics = (
        ComparisonMetric.TARGET_F1,
        ComparisonMetric.ATTACK_SUCCESS_RATE,
        ComparisonMetric.MALICIOUS_ADMISSION,
    )
    for plot_index, metric in enumerate(metrics, start=1):
        axis = figure.add_subplot(1, len(metrics), plot_index)
        labels: list[FigureLegendText] = []
        effects: list[MetricValue] = []
        lower_errors: list[MetricValue] = []
        upper_errors: list[MetricValue] = []
        for family in comparison_results:
            for comparison in family.comparisons:
                if comparison.definition.metric is not metric:
                    continue
                if comparison.mean_paired_difference is None:
                    continue
                if comparison.confidence_interval is None:
                    continue
                labels.append(comparison.definition.method)
                effects.append(comparison.mean_paired_difference)
                lower_errors.append(
                    comparison.mean_paired_difference - comparison.confidence_interval[0]
                )
                upper_errors.append(
                    comparison.confidence_interval[1] - comparison.mean_paired_difference
                )
        if not labels:
            raise ValueError(
                f"Primary Security-Utility Tradeoff: missing comparison evidence for {metric}"
            )
        positions = tuple(range(len(labels)))
        axis.errorbar(
            effects,
            positions,
            xerr=(tuple(lower_errors), tuple(upper_errors)),
            fmt="o",
        )
        axis.set_yticks(positions, labels)
        axis.set_title(metric)
        axis.axvline(0.0)
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    return destination


def render_evidence_arrival_trajectory(
    state_fractions: tuple[EvidenceStateFraction, ...],
    destination: Path,
) -> Path:
    if not state_fractions:
        raise ValueError("Evidence-Arrival State Trajectory: missing state evidence")
    schedules = tuple(sorted(frozenset(observation.condition for observation in state_fractions)))
    states = (
        AdmissionState.DORMANT,
        AdmissionState.VERIFICATION_PENDING,
        AdmissionState.ADMITTED,
        AdmissionState.EXPIRED,
    )
    figure = Figure(figsize=(5 * len(schedules), 4))
    first_axis = None
    for index, schedule in enumerate(schedules, start=1):
        axis = figure.add_subplot(1, len(schedules), index)
        if first_axis is None:
            first_axis = axis
        cycles = tuple(
            sorted(
                frozenset(
                    observation.cycle
                    for observation in state_fractions
                    if observation.condition == schedule
                )
            )
        )
        for state in states:
            fractions = tuple(
                state_fraction(state_fractions, schedule, cycle, state) for cycle in cycles
            )
            axis.step(cycles, fractions, where="post", marker="o", label=state)
        axis.set_title(schedule)
        axis.set_xlabel(FigureAxisName.LOGICAL_EVIDENCE_CYCLE)
        axis.set_ylim(0.0, 1.0)
    if first_axis is not None:
        first_axis.set_ylabel(FigureAxisName.FRACTION_OF_SEED_INSTANCES)
        first_axis.legend()
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    return destination


EFFICIENCY_PROFILE_METRICS: tuple[MetricName, ...] = (
    DescriptiveScientificMetric.WALL_CLOCK_SECONDS,
    DescriptiveScientificMetric.COMMUNICATION_BYTES,
    DescriptiveScientificMetric.PEAK_GPU_MEMORY_BYTES,
)


def render_efficiency_profile(
    metric_values: tuple[EfficiencyMetricObservation, ...],
    destination: Path,
) -> Path:
    if not metric_values:
        raise ValueError("Efficiency Profile: missing timing and resource telemetry")
    missing = tuple(
        metric
        for metric in EFFICIENCY_PROFILE_METRICS
        if not any(observation.metric == metric for observation in metric_values)
    )
    if missing:
        raise ValueError(f"Efficiency Profile: missing telemetry for {', '.join(missing)}")
    metrics = EFFICIENCY_PROFILE_METRICS
    figure = Figure(figsize=(5 * len(metrics), 5))
    for index, selected_metric in enumerate(metrics, start=1):
        axis = figure.add_subplot(1, len(metrics), index)
        methods = tuple(
            sorted(
                frozenset(
                    observation.method
                    for observation in metric_values
                    if observation.metric == selected_metric
                )
            )
        )
        observations = tuple(
            efficiency_observation(metric_values, method, selected_metric) for method in methods
        )
        medians = tuple(observation.median for observation in observations)
        lower_errors = tuple(
            observation.median - observation.first_quartile for observation in observations
        )
        upper_errors = tuple(
            observation.third_quartile - observation.median for observation in observations
        )
        axis.bar(methods, medians, yerr=(lower_errors, upper_errors), capsize=4)
        axis.set_ylabel(f"{selected_metric} (median; IQR bars)")
        axis.set_title(selected_metric)
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    return destination


def _render_experiment_effects(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    destination: Path,
    title: FigureName,
    xlabel: FigureAxisName,
    ylabel: FigureAxisName,
    experiments: tuple[ExperimentName, ...],
    metrics: tuple[ComparisonMetric, ...] | None = None,
    annotation: FigureAnnotationText | None = None,
) -> Path:
    figure = Figure(figsize=(8, 5))
    axis = figure.add_subplot(1, 1, 1)
    labels: list[FigureLegendText] = []
    effects: list[MetricValue] = []
    lower_errors: list[MetricValue] = []
    upper_errors: list[MetricValue] = []
    annotations: list[FigureAnnotationText] = []
    for family in comparison_results:
        for comparison in family.comparisons:
            if comparison.definition.experiment not in experiments:
                continue
            if metrics is not None and comparison.definition.metric not in metrics:
                continue
            effect = comparison.mean_paired_difference
            interval = comparison.confidence_interval
            if effect is None or interval is None:
                continue
            labels.append(f"{comparison.definition.method}: {comparison.definition.metric}")
            effects.append(effect)
            lower_errors.append(effect - interval[0])
            upper_errors.append(interval[1] - effect)
            adjusted_p = (
                "p=NA"
                if comparison.adjusted_p_value is None
                else f"p={comparison.adjusted_p_value:.4g}"
            )
            annotations.append(adjusted_p)
    if not effects:
        raise ValueError(f"{title}: missing completed comparison evidence")
    positions = tuple(range(len(effects)))
    axis.errorbar(
        effects,
        positions,
        xerr=(tuple(lower_errors), tuple(upper_errors)),
        fmt="o",
    )
    axis.set_yticks(positions, labels)
    axis.axvline(0.0)
    for position, effect, label in zip(positions, effects, annotations, strict=True):
        axis.annotate(label, (effect, position), xytext=(5, 4), textcoords="offset points")
    axis.set_title(title)
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    if annotation is not None:
        axis.text(
            FIGURE_ANNOTATION_INSET,
            FIGURE_ANNOTATION_INSET,
            annotation,
            transform=axis.transAxes,
            va="bottom",
        )
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    return destination


def _completed_metric_values(
    outcomes: tuple[CellExecutionOutcome, ...],
    method: MethodName,
    metric: MetricName,
) -> tuple[MetricValue, ...]:
    return tuple(
        value
        for outcome in sorted(outcomes, key=lambda item: item.cell.master_seed)
        if (
            outcome.completed
            and outcome.cell.experiment == SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME
            and outcome.cell.condition == PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT
            and outcome.cell.method == method
        )
        for metric_name, value in outcome.metrics
        if metric_name == metric and value is not None
    )


def _summary_interval(values: tuple[MetricValue, ...]) -> tuple[MetricValue, MetricValue] | None:
    config = current_application_context().scientific_config
    return bootstrap_percentile_confidence_interval(
        values,
        config.metrics_and_statistics.bootstrap,
        config.seeds_and_determinism.analysis_seed,
    )


def render_useful_backdoored_source(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    destination: Path,
    outcomes: tuple[CellExecutionOutcome, ...],
) -> Path:
    del comparison_results
    figure = Figure(figsize=(8, 5))
    axis = figure.add_subplot(1, 1, 1)
    methods = tuple(
        sorted(
            frozenset(
                outcome.cell.method
                for outcome in outcomes
                if (
                    outcome.completed
                    and outcome.cell.experiment == SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME
                    and outcome.cell.condition == PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT
                )
            )
        )
    )
    plotted = False
    for method in methods:
        asr_values = _completed_metric_values(
            outcomes,
            method,
            ComparisonMetric.ATTACK_SUCCESS_RATE,
        )
        target_f1_values = _completed_metric_values(outcomes, method, ComparisonMetric.TARGET_F1)
        if not asr_values or not target_f1_values:
            continue
        asr_interval = _summary_interval(asr_values)
        target_f1_interval = _summary_interval(target_f1_values)
        mean_asr = sum(asr_values) / len(asr_values)
        mean_target_f1 = sum(target_f1_values) / len(target_f1_values)
        x_error = (
            None
            if asr_interval is None
            else ((mean_asr - asr_interval[0],), (asr_interval[1] - mean_asr,))
        )
        y_error = (
            None
            if target_f1_interval is None
            else (
                (mean_target_f1 - target_f1_interval[0],),
                (target_f1_interval[1] - mean_target_f1,),
            )
        )
        axis.errorbar(
            mean_asr,
            mean_target_f1,
            xerr=x_error,
            yerr=y_error,
            fmt="o",
            label=method,
        )
        plotted = True
    if plotted:
        capability_threshold = (
            current_application_context().scientific_config.capability_contract.target_f1_minimum
        )
        axis.axhline(
            capability_threshold,
            color="black",
            linestyle="--",
            label=FigureLegendLabel.TARGET_F1_THRESHOLD,
        )
        axis.legend()
    else:
        raise ValueError("Useful Backdoored Source: missing completed source-exclusion evidence")
    axis.set_title(FigureName.USEFUL_BACKDOORED_SOURCE)
    axis.set_xlabel(FigureAxisName.POST_PRODUCTION_ASR)
    axis.set_ylabel(FigureAxisName.TARGET_F1)
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    return destination


def render_collapse_decision_effects(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    destination: Path,
) -> Path:
    figure = Figure(figsize=(8, 5))
    axis = figure.add_subplot(1, 1, 1)
    labels: list[ExperimentName] = []
    normalized_effects: list[MetricValue] = []
    lower_errors: list[MetricValue] = []
    upper_errors: list[MetricValue] = []
    annotations: list[FigureAnnotationText] = []
    for experiment in COLLAPSE_EXPERIMENT_NAMES:
        matching = tuple(
            comparison
            for family in comparison_results
            for comparison in family.comparisons
            if (
                comparison.definition.experiment == experiment
                and comparison.mean_paired_difference is not None
                and comparison.definition.material_threshold is not None
                and comparison.definition.material_threshold > 0.0
                and comparison.confidence_interval is not None
            )
        )
        if not matching:
            continue
        comparison = matching[0]
        threshold = comparison.definition.material_threshold
        effect = comparison.mean_paired_difference
        interval = comparison.confidence_interval
        if threshold is None or threshold <= 0.0 or effect is None or interval is None:
            continue
        labels.append(experiment)
        normalized_effects.append(effect / threshold)
        lower_errors.append((effect - interval[0]) / threshold)
        upper_errors.append((interval[1] - effect) / threshold)
        adjusted_p = (
            ReportCellLiteral.NOT_AVAILABLE
            if comparison.adjusted_p_value is None
            else f"p={comparison.adjusted_p_value:.4g}"
        )
        annotations.append(f"{adjusted_p}; {comparison.comparison_state}")
    if normalized_effects:
        positions = tuple(range(len(normalized_effects)))
        axis.errorbar(
            normalized_effects,
            positions,
            xerr=(tuple(lower_errors), tuple(upper_errors)),
            fmt="o",
        )
        axis.set_yticks(positions, labels)
        for position, effect, annotation in zip(
            positions, normalized_effects, annotations, strict=True
        ):
            axis.annotate(annotation, (effect, position), xytext=(5, 4), textcoords="offset points")
        axis.axvline(1.0, color="black", linestyle="--")
    else:
        raise ValueError("Collapse Decision Effects: missing completed collapse evidence")
    axis.set_title(FigureName.COLLAPSE_DECISION_EFFECTS)
    axis.set_xlabel(FigureAxisName.PRIMARY_MATERIAL_EFFECT_OVER_THRESHOLD)
    axis.set_ylabel(FigureAxisName.MECHANISM)
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    return destination


def _outcome_metric_mean(
    outcomes: tuple[CellExecutionOutcome, ...],
    experiment: ExperimentName,
    method: MethodName,
    condition: ScenarioName,
    metric: MetricName,
) -> MetricValue | None:
    values = tuple(
        value
        for outcome in outcomes
        if (
            outcome.completed
            and outcome.cell.experiment == experiment
            and outcome.cell.method == method
            and outcome.cell.condition == condition
        )
        for recorded_metric, value in outcome.metrics
        if recorded_metric == metric and value is not None
    )
    return None if not values else sum(values) / len(values)


def _paired_comparison(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    experiment: ExperimentName,
    condition: ScenarioName,
    metric: ComparisonMetric,
) -> ComparisonResult | None:
    for family in comparison_results:
        for comparison in family.comparisons:
            definition = comparison.definition
            if (
                definition.experiment == experiment
                and definition.scientific_scenario == condition
                and definition.metric is metric
            ):
                return comparison
    return None


def _completed_outcomes(
    outcomes: tuple[CellExecutionOutcome, ...],
    experiment: ExperimentName,
) -> tuple[CellExecutionOutcome, ...]:
    return tuple(
        outcome
        for outcome in outcomes
        if outcome.completed and outcome.cell.experiment == experiment
    )


def _experiment_methods(
    outcomes: tuple[CellExecutionOutcome, ...],
    experiment: ExperimentName,
) -> tuple[MethodName, ...]:
    return tuple(
        sorted(
            frozenset(outcome.cell.method for outcome in _completed_outcomes(outcomes, experiment))
        )
    )


def _condition_compromised_count(condition: ScenarioName) -> ScientificCellCount:
    if condition.startswith("Two"):
        return 2
    if condition.startswith("One"):
        return 1
    return 0


def _series_panel(
    axis: Axes,
    series: BoundarySeries,
    xlabel: FigureAxisName,
    ylabel: FigureAxisName,
    title: FigureName | FigurePanelTitle,
) -> None:
    plotted = False
    for label, x_values, y_values in series:
        if not any(value is not None for value in y_values):
            continue
        axis.plot(
            x_values,
            tuple(float("nan") if value is None else value for value in y_values),
            marker="o",
            label=label,
        )
        plotted = True
    if not plotted:
        raise ValueError(f"{title}: missing completed source evidence")
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    axis.set_title(title)
    axis.legend()


def _grouped_panel(
    axis: Axes,
    x_labels: tuple[FigureAxisLabel, ...],
    groups: tuple[FigureLegendText, ...],
    values: tuple[tuple[MetricValue | None, ...], ...],
    xlabel: FigureAxisName,
    ylabel: FigureAxisName,
    title: FigureName | FigurePanelTitle,
) -> None:
    if not any(value is not None for row in values for value in row):
        raise ValueError(f"{title}: missing completed source evidence")
    positions = tuple(range(len(x_labels)))
    width = 0.8 / max(len(groups), 1)
    for index, group in enumerate(groups):
        offsets = tuple(position + index * width for position in positions)
        axis.bar(
            offsets,
            tuple(float("nan") if value is None else value for value in values[index]),
            width=width,
            label=group,
        )
    centre_offset = (len(groups) - 1) * width / 2
    axis.set_xticks(
        tuple(position + centre_offset for position in positions),
        x_labels,
        rotation=15,
        ha="right",
    )
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    axis.set_title(title)
    axis.legend()


def _single_panel_figure(
    destination: Path,
    panels: tuple[tuple[FigureName | FigurePanelTitle, AxisDraw], ...],
) -> Path:
    figure = Figure(figsize=(6 * len(panels), 5))
    for index, (_title, draw) in enumerate(panels, start=1):
        draw(figure.add_subplot(1, len(panels), index))
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    return destination


def maximum_byzantine_reproduction_rows() -> ReproductionRowCount:
    config = current_application_context().scientific_config
    return config.protocol.synthesis.maximum_byzantine_reproduction_rows


def render_compromised_reproducer_boundary(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    destination: Path,
    outcomes: tuple[CellExecutionOutcome, ...],
) -> Path:
    del comparison_results
    completed = _completed_outcomes(outcomes, COMPROMISED_REPRODUCER_ROBUSTNESS_NAME)
    if not completed:
        raise ValueError("Compromised-Reproducer Boundary: missing completed source evidence")
    conditions = tuple(sorted(frozenset(outcome.cell.condition for outcome in completed)))
    counts = tuple(_condition_compromised_count(condition) for condition in conditions)
    series = tuple(
        (
            method,
            counts,
            tuple(
                _outcome_metric_mean(
                    outcomes,
                    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
                    method,
                    condition,
                    ComparisonMetric.MALICIOUS_ADMISSION,
                )
                for condition in conditions
            ),
        )
        for method in _experiment_methods(outcomes, COMPROMISED_REPRODUCER_ROBUSTNESS_NAME)
    )

    def draw_mar(axis: Axes) -> None:
        _series_panel(
            axis,
            series,
            FigureAxisName.COMPROMISED_REPRODUCER_COUNT,
            FigureAxisName.MALICIOUS_ADMISSION_RATE,
            FigureName.COMPROMISED_REPRODUCER_BOUNDARY,
        )
        annotation_value = maximum_byzantine_reproduction_rows()
        axis.axvline(annotation_value, color="black", linestyle="--")

    def draw_asr(axis: Axes) -> None:
        _series_panel(
            axis,
            tuple(
                (
                    method,
                    counts,
                    tuple(
                        _outcome_metric_mean(
                            outcomes,
                            COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
                            method,
                            condition,
                            ComparisonMetric.ATTACK_SUCCESS_RATE,
                        )
                        for condition in conditions
                    ),
                )
                for method in _experiment_methods(outcomes, COMPROMISED_REPRODUCER_ROBUSTNESS_NAME)
            ),
            FigureAxisName.COMPROMISED_REPRODUCER_COUNT,
            FigureAxisName.ATTACK_SUCCESS_RATE,
            FigurePanelTitle.COMPROMISED_REPRODUCER_BOUNDARY_ASR,
        )

    return _single_panel_figure(
        destination,
        (
            (FigurePanelTitle.MALICIOUS_ADMISSION, draw_mar),
            (FigurePanelTitle.ATTACK_SUCCESS_RATE, draw_asr),
        ),
    )


def render_compromised_verifier_boundary(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    destination: Path,
    outcomes: tuple[CellExecutionOutcome, ...],
) -> Path:
    del comparison_results
    completed = _completed_outcomes(outcomes, COMPROMISED_VERIFIER_ROBUSTNESS_NAME)
    if not completed:
        raise ValueError("Compromised-Verifier Boundary: missing completed source evidence")
    false_positive_conditions = (
        VerifierCondition.ALL_HONEST,
        VerifierCondition.ONE_FALSE_POSITIVE,
        VerifierCondition.TWO_FALSE_POSITIVES,
    )
    false_negative_conditions = (
        VerifierCondition.ALL_HONEST,
        VerifierCondition.ONE_FALSE_NEGATIVE,
        VerifierCondition.TWO_FALSE_NEGATIVES,
    )
    counts = tuple(
        _condition_compromised_count(condition) for condition in false_positive_conditions
    )

    def series_for(
        conditions: tuple[ScenarioName, ...],
        metric: ComparisonMetric,
    ) -> BoundarySeries:
        return tuple(
            (
                profile,
                counts,
                tuple(
                    _outcome_metric_mean(
                        outcomes,
                        COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
                        profile,
                        condition,
                        metric,
                    )
                    for condition in conditions
                ),
            )
            for profile in _experiment_methods(outcomes, COMPROMISED_VERIFIER_ROBUSTNESS_NAME)
        )

    def draw_false_positive(axis: Axes) -> None:
        _series_panel(
            axis,
            series_for(false_positive_conditions, ComparisonMetric.MALICIOUS_ADMISSION),
            FigureAxisName.COMPROMISED_VERIFIER_COUNT,
            FigureAxisName.MALICIOUS_ADMISSION_RATE,
            FigurePanelTitle.COMPROMISED_VERIFIER_BOUNDARY_FALSE_POSITIVE_MODE,
        )
        axis.axvline(
            current_application_context().scientific_config.protocol.verification.maximum_byzantine_verifiers_per_panel,
            color="black",
            linestyle="--",
        )

    def draw_false_negative(axis: Axes) -> None:
        _series_panel(
            axis,
            series_for(false_negative_conditions, ComparisonMetric.LEGITIMATE_ADMISSION),
            FigureAxisName.COMPROMISED_VERIFIER_COUNT,
            FigureAxisName.LEGITIMATE_ADMISSION_RATE,
            FigurePanelTitle.COMPROMISED_VERIFIER_BOUNDARY_FALSE_NEGATIVE_MODE,
        )
        axis.axvline(
            current_application_context().scientific_config.protocol.verification.maximum_byzantine_verifiers_per_panel,
            color="black",
            linestyle="--",
        )

    return _single_panel_figure(
        destination,
        (
            (FigurePanelTitle.FALSE_POSITIVE, draw_false_positive),
            (FigurePanelTitle.FALSE_NEGATIVE, draw_false_negative),
        ),
    )


def render_shared_epistemic_failure(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    destination: Path,
    outcomes: tuple[CellExecutionOutcome, ...],
) -> Path:
    if not outcomes:
        raise ValueError("Shared Epistemic Failure: missing completed source evidence")
    failure_types = tuple(EpistemicFailureType)

    def strengths_for(failure_type: EpistemicFailureType) -> tuple[AttackStrength, ...]:
        return tuple(
            sorted(
                frozenset(
                    float(outcome.cell.condition.rsplit("|", 1)[1])
                    for outcome in outcomes
                    if outcome.completed
                    and outcome.cell.experiment == SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME
                    and outcome.cell.condition.startswith(f"{failure_type}|")
                )
            )
        )

    def clean_oracle_series() -> BoundarySeries:
        series: list[
            tuple[FigureLegendText, tuple[ScientificCellCount, ...], tuple[MetricValue | None, ...]]
        ] = []
        for failure_type in failure_types:
            strengths = strengths_for(failure_type)
            if not strengths:
                continue
            differences: list[MetricValue | None] = []
            for strength in strengths:
                condition = f"{failure_type}|{strength:.2f}"
                comparison = _paired_comparison(
                    comparison_results,
                    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
                    condition,
                    ComparisonMetric.TARGET_F1,
                )
                differences.append(
                    None if comparison is None else comparison.mean_paired_difference
                )
            series.append(
                (
                    failure_type,
                    tuple(int(value) for value in strengths),
                    tuple(differences),
                )
            )
        return tuple(series)

    def admission_series() -> BoundarySeries:
        series: list[
            tuple[FigureLegendText, tuple[ScientificCellCount, ...], tuple[MetricValue | None, ...]]
        ] = []
        for failure_type in failure_types:
            strengths = strengths_for(failure_type)
            if not strengths:
                continue
            values = tuple(
                _outcome_metric_mean(
                    outcomes,
                    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
                    CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
                    f"{failure_type}|{strength:.2f}",
                    ComparisonMetric.LEGITIMATE_ADMISSION,
                )
                for strength in strengths
            )
            series.append((failure_type, tuple(int(value) for value in strengths), values))
        return tuple(series)

    def draw_clean_oracle(axis: Axes) -> None:
        _series_panel(
            axis,
            clean_oracle_series(),
            FigureAxisName.CORRUPTION_CONFOUND_STRENGTH,
            FigureAxisName.CLEAN_ORACLE_TARGET_F1_DIFFERENCE,
            FigurePanelTitle.SHARED_EPISTEMIC_FAILURE_CLEAN_ORACLE,
        )
        axis.axhline(0.0)

    def draw_admission(axis: Axes) -> None:
        _series_panel(
            axis,
            admission_series(),
            FigureAxisName.CORRUPTION_CONFOUND_STRENGTH,
            FigureAxisName.ADMISSION_RATE_UNDER_CORRUPTED_EVIDENCE,
            FigurePanelTitle.SHARED_EPISTEMIC_FAILURE_ADMISSION,
        )

    return _single_panel_figure(
        destination,
        (
            (FigurePanelTitle.CLEAN_ORACLE, draw_clean_oracle),
            (FigurePanelTitle.ADMISSION, draw_admission),
        ),
    )


def render_capability_granularity_boundary(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    destination: Path,
    outcomes: tuple[CellExecutionOutcome, ...],
) -> Path:
    del comparison_results
    completed = _completed_outcomes(outcomes, CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME)
    if not completed:
        raise ValueError("Capability-Granularity Boundary: missing completed source evidence")
    granularities = tuple(
        scope
        for scope in CapabilityContractScope
        if any(outcome.cell.method == scope for outcome in completed)
    )
    mixtures = tuple(
        mixture
        for mixture in RootCauseMixture
        if any(outcome.cell.condition == mixture for outcome in completed)
    )

    def values_for(metric: MetricName) -> tuple[tuple[MetricValue | None, ...], ...]:
        return tuple(
            tuple(
                _outcome_metric_mean(
                    outcomes,
                    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
                    granularity,
                    mixture,
                    metric,
                )
                for granularity in granularities
            )
            for mixture in mixtures
        )

    def draw_false_equivalence(axis: Axes) -> None:
        _grouped_panel(
            axis,
            granularities,
            mixtures,
            values_for(ComparisonMetric.FALSE_SAME_CAPABILITY_CERTIFICATION_RATE),
            FigureAxisName.CAPABILITY_CONTRACT_GRANULARITY,
            FigureAxisName.FALSE_SAME_CAPABILITY_CERTIFICATION_RATE,
            FigurePanelTitle.CAPABILITY_GRANULARITY_BOUNDARY_FALSE_EQUIVALENCE,
        )

    def draw_root_cause(axis: Axes) -> None:
        _grouped_panel(
            axis,
            granularities,
            tuple(f"{mixture}: root cause A" for mixture in mixtures)
            + tuple(f"{mixture}: root cause B" for mixture in mixtures),
            values_for(MetricObservationKey.ROOT_CAUSE_A_TARGET_F1)
            + values_for(MetricObservationKey.ROOT_CAUSE_B_TARGET_F1),
            FigureAxisName.CAPABILITY_CONTRACT_GRANULARITY,
            FigureAxisName.TARGET_F1,
            FigurePanelTitle.CAPABILITY_GRANULARITY_BOUNDARY_ROOT_CAUSE_TARGET_F1,
        )

    return _single_panel_figure(
        destination,
        (
            (FigurePanelTitle.FALSE_EQUIVALENCE, draw_false_equivalence),
            (FigurePanelTitle.ROOT_CAUSE, draw_root_cause),
        ),
    )


def render_heterogeneity_synthesis_boundary(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    destination: Path,
    outcomes: tuple[CellExecutionOutcome, ...],
) -> Path:
    del comparison_results
    completed = _completed_outcomes(outcomes, HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME)
    if not completed:
        raise ValueError("Heterogeneity Synthesis Boundary: missing completed source evidence")
    regimes = tuple(
        regime
        for regime in HeterogeneityRegime
        if any(outcome.cell.condition == regime for outcome in completed)
    )
    methods = _experiment_methods(outcomes, HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME)
    positions = tuple(range(len(regimes)))

    def values_for(metric: MetricName) -> tuple[tuple[MetricValue | None, ...], ...]:
        return tuple(
            tuple(
                _outcome_metric_mean(
                    outcomes,
                    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
                    method,
                    regime,
                    metric,
                )
                for regime in regimes
            )
            for method in methods
        )

    def draw_admission(axis: Axes) -> None:
        _grouped_panel(
            axis,
            regimes,
            methods,
            values_for(ComparisonMetric.LEGITIMATE_ADMISSION),
            FigureAxisName.HETEROGENEITY_REGIME,
            FigureAxisName.LEGITIMATE_ADMISSION_RATE,
            FigurePanelTitle.HETEROGENEITY_SYNTHESIS_BOUNDARY_LEGITIMATE_ADMISSION,
        )

    def draw_worst_domain(axis: Axes) -> None:
        _grouped_panel(
            axis,
            regimes,
            methods,
            values_for(ComparisonMetric.WORST_DOMAIN_TARGET_F1),
            FigureAxisName.HETEROGENEITY_REGIME,
            FigureAxisName.WORST_DOMAIN_TARGET_F1,
            FigurePanelTitle.HETEROGENEITY_SYNTHESIS_BOUNDARY_WORST_DOMAIN_TARGET_F1,
        )

    del positions
    return _single_panel_figure(
        destination,
        (
            (FigurePanelTitle.LEGITIMATE_ADMISSION, draw_admission),
            (FigurePanelTitle.WORST_DOMAIN_TARGET_F1, draw_worst_domain),
        ),
    )


def render_admission_delay_decomposition(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    destination: Path,
    outcomes: tuple[CellExecutionOutcome, ...],
) -> Path:
    delay_outcomes = _completed_outcomes(outcomes, ADMISSION_DELAY_DECOMPOSITION_NAME)
    if not delay_outcomes:
        raise ValueError("Admission-Delay Decomposition: missing completed source evidence")
    figure = Figure(figsize=(12, 5))
    axis = figure.add_subplot(1, 1, 1)
    cells = tuple(
        sorted(
            frozenset((outcome.cell.method, outcome.cell.condition) for outcome in delay_outcomes)
        )
    )
    phases: tuple[tuple[MetricName, FigureLegendLabel], ...] = (
        (DelayPhaseMetric.ASSIGNMENT_SECONDS, FigureLegendLabel.ASSIGNMENT),
        (DelayPhaseMetric.REPRODUCE_SECONDS, FigureLegendLabel.REPRODUCE),
        (DelayPhaseMetric.VERIFY_SECONDS, FigureLegendLabel.VERIFY),
        (DelayPhaseMetric.SYNTHESIZE_SECONDS, FigureLegendLabel.SYNTHESIZE),
    )
    bottoms = [0.0] * len(cells)
    for metric, label in phases:
        values = tuple(
            _outcome_metric_mean(
                outcomes,
                ADMISSION_DELAY_DECOMPOSITION_NAME,
                method,
                condition,
                metric,
            )
            or 0.0
            for method, condition in cells
        )
        axis.bar(range(len(cells)), values, bottom=bottoms, label=label)
        bottoms = [bottom + value for bottom, value in zip(bottoms, values, strict=True)]
    t_evidence = tuple(
        _outcome_metric_mean(
            outcomes,
            ADMISSION_DELAY_DECOMPOSITION_NAME,
            method,
            condition,
            DescriptiveScientificMetric.T_EVIDENCE,
        )
        for method, condition in cells
    )
    if not any(value is not None for value in t_evidence):
        raise ValueError("Admission-Delay Decomposition: missing T_evidence logical cycles")
    for index, value in enumerate(t_evidence):
        axis.annotate(
            f"T_evidence={0 if value is None else int(value)} cycles",
            (index, 0.0),
            xytext=(0, 6),
            textcoords="offset points",
            ha="center",
            fontsize=7,
        )
    labels = tuple(f"{method}\n{condition}" for method, condition in cells)
    axis.set_xticks(range(len(cells)), labels, rotation=25, ha="right")
    axis.set_ylabel(FigureAxisName.POST_EVIDENCE_WALL_CLOCK_SECONDS)
    axis.set_title(FigureName.ADMISSION_DELAY_DECOMPOSITION)
    axis.legend()
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    return destination


def render_secondary_generalization(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    destination: Path,
) -> Path:
    return _render_experiment_effects(
        comparison_results,
        destination,
        FigureName.SECONDARY_GENERALIZATION,
        FigureAxisName.TARGET_F1_PAIRED_EFFECT_VS_COMPARATOR,
        FigureAxisName.METHOD_PER_SECONDARY_SCENARIO,
        (SECONDARY_DATASET_GENERALIZATION_NAME,),
        metrics=(ComparisonMetric.TARGET_F1,),
        annotation="Synthetic-domain limitation: data/attack generalization only.",
    )


def render_mandatory_figures(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    figures_root: Path,
    evidence_trajectory: tuple[EvidenceStateFraction, ...],
    telemetry: tuple[EfficiencyMetricObservation, ...],
    outcomes: tuple[CellExecutionOutcome, ...],
) -> tuple[Path, ...]:
    schematic = figures_root / f"{PROTOCOL_SCHEMATIC_FIGURE_NAME}.png"
    render_protocol_schematic(schematic)
    tradeoff = figures_root / f"{PRIMARY_SECURITY_UTILITY_TRADEOFF_FIGURE_NAME}.png"
    render_security_utility_tradeoff(comparison_results, tradeoff)
    trajectory = figures_root / f"{EVIDENCE_ARRIVAL_STATE_TRAJECTORY_FIGURE_NAME}.png"
    render_evidence_arrival_trajectory(evidence_trajectory, trajectory)
    efficiency = figures_root / f"{EFFICIENCY_PROFILE_FIGURE_NAME}.png"
    render_efficiency_profile(telemetry, efficiency)
    return (
        schematic,
        tradeoff,
        render_useful_backdoored_source(
            comparison_results,
            figures_root / f"{USEFUL_BACKDOORED_SOURCE_FIGURE_NAME}.png",
            outcomes,
        ),
        render_collapse_decision_effects(
            comparison_results, figures_root / f"{COLLAPSE_DECISION_EFFECTS_FIGURE_NAME}.png"
        ),
        render_compromised_reproducer_boundary(
            comparison_results,
            figures_root / f"{COMPROMISED_REPRODUCER_BOUNDARY_FIGURE_NAME}.png",
            outcomes,
        ),
        render_compromised_verifier_boundary(
            comparison_results,
            figures_root / f"{COMPROMISED_VERIFIER_BOUNDARY_FIGURE_NAME}.png",
            outcomes,
        ),
        trajectory,
        render_shared_epistemic_failure(
            comparison_results,
            figures_root / f"{SHARED_EPISTEMIC_FAILURE_FIGURE_NAME}.png",
            outcomes,
        ),
        render_capability_granularity_boundary(
            comparison_results,
            figures_root / f"{CAPABILITY_GRANULARITY_BOUNDARY_FIGURE_NAME}.png",
            outcomes,
        ),
        render_heterogeneity_synthesis_boundary(
            comparison_results,
            figures_root / f"{HETEROGENEITY_SYNTHESIS_BOUNDARY_FIGURE_NAME}.png",
            outcomes,
        ),
        render_admission_delay_decomposition(
            comparison_results,
            figures_root / f"{ADMISSION_DELAY_DECOMPOSITION_FIGURE_NAME}.png",
            outcomes,
        ),
        efficiency,
        render_secondary_generalization(
            comparison_results, figures_root / f"{SECONDARY_GENERALIZATION_FIGURE_NAME}.png"
        ),
    )


def _render_specialized_figure(
    result: ExperimentExecutionResult,
    figures_root: Path,
) -> Path | None:
    figure: Path | None = None
    if result.experiment == COMPROMISED_REPRODUCER_ROBUSTNESS_NAME:
        figure = render_compromised_reproducer_boundary(
            result.comparison_results,
            figures_root / f"{COMPROMISED_REPRODUCER_BOUNDARY_FIGURE_NAME}.png",
            result.outcomes,
        )
    elif result.experiment == COMPROMISED_VERIFIER_ROBUSTNESS_NAME:
        figure = render_compromised_verifier_boundary(
            result.comparison_results,
            figures_root / f"{COMPROMISED_VERIFIER_BOUNDARY_FIGURE_NAME}.png",
            result.outcomes,
        )
    elif result.experiment == SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME:
        figure = render_shared_epistemic_failure(
            result.comparison_results,
            figures_root / f"{SHARED_EPISTEMIC_FAILURE_FIGURE_NAME}.png",
            result.outcomes,
        )
    elif result.experiment == CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME:
        figure = render_capability_granularity_boundary(
            result.comparison_results,
            figures_root / f"{CAPABILITY_GRANULARITY_BOUNDARY_FIGURE_NAME}.png",
            result.outcomes,
        )
    elif result.experiment == HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME:
        figure = render_heterogeneity_synthesis_boundary(
            result.comparison_results,
            figures_root / f"{HETEROGENEITY_SYNTHESIS_BOUNDARY_FIGURE_NAME}.png",
            result.outcomes,
        )
    elif result.experiment == ADMISSION_DELAY_DECOMPOSITION_NAME:
        figure = render_admission_delay_decomposition(
            result.comparison_results,
            figures_root / f"{ADMISSION_DELAY_DECOMPOSITION_FIGURE_NAME}.png",
            result.outcomes,
        )
    elif result.experiment == SECONDARY_DATASET_GENERALIZATION_NAME:
        figure = render_secondary_generalization(
            result.comparison_results,
            figures_root / f"{SECONDARY_GENERALIZATION_FIGURE_NAME}.png",
        )
    return figure


def render_experiment_figures(
    result: ExperimentExecutionResult,
    figures_root: Path,
    state_trajectory: tuple[EvidenceStateFraction, ...],
    telemetry: tuple[EfficiencyMetricObservation, ...],
) -> tuple[Path, ...]:
    figures: list[Path] = [
        render_protocol_schematic(figures_root / f"{PROTOCOL_SCHEMATIC_FIGURE_NAME}.png")
    ]
    if result.experiment == PRIMARY_CONFIRMATORY_EVALUATION_NAME:
        figures.append(
            render_security_utility_tradeoff(
                result.comparison_results,
                figures_root / f"{PRIMARY_SECURITY_UTILITY_TRADEOFF_FIGURE_NAME}.png",
            )
        )
    elif result.experiment == SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME:
        figures.append(
            render_useful_backdoored_source(
                result.comparison_results,
                figures_root / f"{USEFUL_BACKDOORED_SOURCE_FIGURE_NAME}.png",
                result.outcomes,
            )
        )
        figures.append(
            render_collapse_decision_effects(
                result.comparison_results,
                figures_root / f"{COLLAPSE_DECISION_EFFECTS_FIGURE_NAME}.png",
            )
        )
    elif result.experiment in COLLAPSE_EXPERIMENT_NAMES:
        figures.append(
            render_collapse_decision_effects(
                result.comparison_results,
                figures_root / f"{COLLAPSE_DECISION_EFFECTS_FIGURE_NAME}.png",
            )
        )
    elif result.experiment == EFFICIENCY_MEASUREMENT_NAME:
        figures.append(
            render_efficiency_profile(
                telemetry,
                figures_root / f"{EFFICIENCY_PROFILE_FIGURE_NAME}.png",
            )
        )
    elif result.experiment == EVIDENCE_SCARCITY_AND_DORMANCY_NAME:
        figures.append(
            render_evidence_arrival_trajectory(
                state_trajectory,
                figures_root / f"{EVIDENCE_ARRIVAL_STATE_TRAJECTORY_FIGURE_NAME}.png",
            )
        )
    else:
        specialized = _render_specialized_figure(result, figures_root)
        if specialized is not None:
            figures.append(specialized)
    return tuple(figures)


def efficiency_telemetry(
    outcomes: tuple[CellExecutionOutcome, ...],
) -> tuple[EfficiencyMetricObservation, ...]:
    metric_names: tuple[MetricName, ...] = (
        DescriptiveScientificMetric.WALL_CLOCK_SECONDS,
        DescriptiveScientificMetric.COMMUNICATION_BYTES,
        DescriptiveScientificMetric.PEAK_GPU_MEMORY_BYTES,
    )
    methods = tuple(sorted(frozenset(outcome.cell.method for outcome in outcomes)))
    observations: list[EfficiencyMetricObservation] = []
    for metric_name in metric_names:
        for method in methods:
            seed_medians = tuple(
                float(numpy.median(values))
                for seed in frozenset(outcome.cell.master_seed for outcome in outcomes)
                if (
                    values := tuple(
                        value
                        for outcome in outcomes
                        if (
                            outcome.completed
                            and outcome.cell.experiment == EFFICIENCY_MEASUREMENT_NAME
                            and outcome.cell.repetition is not None
                            and outcome.cell.method == method
                            and outcome.cell.master_seed == seed
                        )
                        for recorded_metric, value in outcome.metrics
                        if recorded_metric == metric_name and value is not None
                    )
                )
            )
            if seed_medians:
                observations.append(
                    EfficiencyMetricObservation(
                        method=method,
                        metric=metric_name,
                        median=float(numpy.median(seed_medians)),
                        first_quartile=float(numpy.quantile(seed_medians, 0.25, method="linear")),
                        third_quartile=float(numpy.quantile(seed_medians, 0.75, method="linear")),
                        seed_count=len(seed_medians),
                    )
                )
    return tuple(observations)


def evidence_trajectory(
    store: ExecutionRecordStore,
) -> tuple[EvidenceStateFraction, ...]:
    records = tuple(
        record
        for record in store.read_all_outcomes(EVIDENCE_SCARCITY_AND_DORMANCY_NAME)
        if record.terminal_state is ExperimentLifecycleState.COMPLETED
    )
    if not records:
        return ()
    if any(not record.state_trajectory for record in records):
        raise ValueError("Evidence Scarcity and Dormancy record lacks its state trajectory")
    resource_horizon = current_application_context().scientific_config.protocol.resource_horizon
    horizon = resource_horizon.maximum_logical_evidence_cycles
    result: list[EvidenceStateFraction] = []
    states = (
        AdmissionState.DORMANT,
        AdmissionState.VERIFICATION_PENDING,
        AdmissionState.ADMITTED,
        AdmissionState.EXPIRED,
    )
    for schedule in sorted(frozenset(record.condition for record in records)):
        schedule_records = tuple(record for record in records if record.condition == schedule)
        for cycle in range(horizon + 1):
            for state in states:
                count = sum(
                    1
                    for record in schedule_records
                    if next(
                        (
                            observation.state
                            for observation in record.state_trajectory
                            if observation.cycle == cycle
                        ),
                        None,
                    )
                    is state
                )
                if count:
                    result.append(
                        EvidenceStateFraction(
                            condition=schedule,
                            cycle=cycle,
                            state=state,
                            fraction=count / len(schedule_records),
                        )
                    )
    return tuple(result)


def outcome_evidence_trajectory(
    outcomes: tuple[CellExecutionOutcome, ...],
) -> tuple[EvidenceStateFraction, ...]:
    completed = tuple(outcome for outcome in outcomes if outcome.completed)
    if not completed:
        raise ValueError("Evidence Scarcity and Dormancy has no completed state evidence")
    scientific_config = current_application_context().scientific_config
    horizon = scientific_config.protocol.resource_horizon.maximum_logical_evidence_cycles
    if any(not outcome.state_trajectory for outcome in completed):
        raise ValueError("Evidence Scarcity and Dormancy outcome lacks its state trajectory")
    expected_cycles = frozenset(range(horizon + 1))
    for outcome in completed:
        observed_cycles = frozenset(observation.cycle for observation in outcome.state_trajectory)
        if observed_cycles != expected_cycles:
            raise ValueError(
                "Evidence Scarcity and Dormancy state trajectory does not cover every "
                f"logical cycle for {outcome.cell.semantic_key}: "
                f"missing {sorted(expected_cycles - observed_cycles)}"
            )
    result: list[EvidenceStateFraction] = []
    states = (
        AdmissionState.DORMANT,
        AdmissionState.VERIFICATION_PENDING,
        AdmissionState.ADMITTED,
        AdmissionState.EXPIRED,
    )
    for schedule in sorted(frozenset(outcome.cell.condition for outcome in completed)):
        schedule_outcomes = tuple(
            outcome for outcome in completed if outcome.cell.condition == schedule
        )
        for cycle in range(horizon + 1):
            for state in states:
                count = sum(
                    1
                    for outcome in schedule_outcomes
                    if next(
                        (
                            observation.state
                            for observation in outcome.state_trajectory
                            if observation.cycle == cycle
                        ),
                        None,
                    )
                    is state
                )
                if count:
                    result.append(
                        EvidenceStateFraction(
                            condition=schedule,
                            cycle=cycle,
                            state=state,
                            fraction=count / len(schedule_outcomes),
                        )
                    )
    return tuple(result)


def project_result_evidence(
    plan: ExperimentPlan,
    load_result: Callable[[ExperimentName], ExperimentExecutionResult],
) -> tuple[tuple[ComparisonFamilyResult, ...], tuple[CellExecutionOutcome, ...]]:
    results = tuple(load_result(planned.definition.name) for planned in plan.experiments)
    return (
        tuple(comparison for result in results for comparison in result.comparison_results),
        tuple(outcome for result in results for outcome in result.outcomes),
    )
