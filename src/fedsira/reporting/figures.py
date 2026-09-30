from __future__ import annotations

import math
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import TypeAlias

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from fedsira.artifacts.paths import experiment_metric_evidence_root
from fedsira.domain.enums import (
    AdmissionState,
    CoreMethodIdentity,
    DelayPhaseMetric,
    DescriptiveScientificMetric,
    EvidenceArrivalSchedule,
    ExperimentName,
    FigureAxisName,
    FigureLegendLabel,
    FigureName,
    FigurePanelTitle,
    MetricObservationKey,
    PrimaryScenario,
    ProtocolSchematicStage,
    ReportCellLiteral,
    ReproducerCondition,
    VerifierCondition,
)
from fedsira.domain.types import (
    AttackStrength,
    EvidenceCycleIndex,
    FigureAnnotationText,
    FigureAxisLabel,
    FigureLegendText,
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
    ComparisonDefinition,
    ComparisonFamily,
    ComparisonFamilyResult,
    ComparisonMetric,
    ComparisonResult,
    build_comparison_registry,
)
from fedsira.experiments.byzantine import random_verifier_contamination_probability
from fedsira.experiments.definitions import (
    ADMISSION_DELAY_DECOMPOSITION_FIGURE_NAME,
    ADMISSION_DELAY_DECOMPOSITION_NAME,
    AGGREGATE_METRICS_PARQUET_NAME,
    CAPABILITY_GRANULARITY_BOUNDARY_FIGURE_NAME,
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    COLLAPSE_DECISION_EFFECTS_FIGURE_NAME,
    COLLAPSE_EXPERIMENT_NAMES,
    COMPROMISED_REPRODUCER_BOUNDARY_FIGURE_NAME,
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_FALSE_NEGATIVE_BOUNDARY_FIGURE_NAME,
    COMPROMISED_VERIFIER_FALSE_POSITIVE_BOUNDARY_FIGURE_NAME,
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
    STATE_TRAJECTORY_FRACTIONS_PARQUET_NAME,
    USEFUL_BACKDOORED_SOURCE_FIGURE_NAME,
    EpistemicFailureType,
    epistemic_strength_tokens,
    experiment_by_name,
)
from fedsira.experiments.engine import (
    CellExecutionOutcome,
    ExperimentExecutionResult,
)
from fedsira.experiments.planning import ExperimentPlan
from fedsira.reporting.aggregate import (
    AggregateMetricEvidenceRow,
    read_aggregate_metric_evidence,
)
from fedsira.reporting.state_trajectory import (
    EVIDENCE_TRAJECTORY_STATE_VOCABULARY,
    EvidenceStateFraction,
    read_state_trajectory_fractions,
)
from fedsira.reporting.telemetry import EfficiencyMetricObservation
from fedsira.runtime import current_application_context

BoundarySeries: TypeAlias = tuple[
    tuple[FigureLegendText, tuple[ScientificCellCount, ...], tuple[MetricValue | None, ...]],
    ...,
]
AxisDraw: TypeAlias = Callable[[Axes], None]


MANDATORY_FIGURE_NAMES: tuple[FigureName, ...] = (
    FigureName.PROTOCOL_SCHEMATIC,
    FigureName.PRIMARY_SECURITY_UTILITY_TRADEOFF,
    FigureName.USEFUL_BACKDOORED_SOURCE,
    FigureName.COLLAPSE_DECISION_EFFECTS,
    FigureName.COMPROMISED_REPRODUCER_BOUNDARY,
    FigureName.COMPROMISED_VERIFIER_FALSE_POSITIVE_BOUNDARY,
    FigureName.COMPROMISED_VERIFIER_FALSE_NEGATIVE_BOUNDARY,
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
) -> EfficiencyMetricObservation | None:
    matches = tuple(
        observation
        for observation in observations
        if observation.method == method and observation.metric == metric
    )
    if len(matches) > 1:
        raise ValueError(f"duplicate efficiency telemetry for {method} / {metric}")
    return matches[0] if matches else None


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
    metrics = (
        ComparisonMetric.TARGET_F1,
        ComparisonMetric.ATTACK_SUCCESS_RATE,
        ComparisonMetric.MALICIOUS_ADMISSION,
    )
    expected_definitions = tuple(
        definition
        for definition in build_comparison_registry()
        if (
            definition.experiment == PRIMARY_CONFIRMATORY_EVALUATION_NAME
            and definition.family is ComparisonFamily.PRIMARY_BASELINE_SUPERIORITY
            and definition.metric in metrics
        )
    )
    observed: list[tuple[ComparisonDefinition, ComparisonResult]] = []
    for family in comparison_results:
        for comparison in family.comparisons:
            expected = next(
                (
                    definition
                    for definition in expected_definitions
                    if definition.comparison_name == comparison.definition.comparison_name
                ),
                None,
            )
            if expected is None:
                continue
            if expected != comparison.definition or family.family is not expected.family:
                raise ValueError("Primary Security-Utility Tradeoff: comparison identity mismatch")
            if any(
                definition.comparison_name == expected.comparison_name
                for definition, _result in observed
            ):
                raise ValueError("Primary Security-Utility Tradeoff: duplicate comparison evidence")
            observed.append((expected, comparison))
    if not observed:
        raise ValueError("Primary Security-Utility Tradeoff: missing comparison evidence")
    figure = Figure(figsize=(12, 4))
    for plot_index, metric in enumerate(metrics, start=1):
        axis = figure.add_subplot(1, len(metrics), plot_index)
        labels: list[FigureLegendText] = []
        effects: list[MetricValue] = []
        lower_errors: list[MetricValue] = []
        upper_errors: list[MetricValue] = []
        definitions = tuple(
            definition for definition in expected_definitions if definition.metric is metric
        )
        for definition in definitions:
            labels.append(
                f"{definition.scientific_scenario}\n"
                f"{definition.method} vs {definition.reference_method}"
            )
            comparison = next(
                (
                    result
                    for registered, result in observed
                    if registered.comparison_name == definition.comparison_name
                ),
                None,
            )
            effect = None if comparison is None else comparison.mean_paired_difference
            interval = None if comparison is None else comparison.confidence_interval
            if effect is None or interval is None:
                effects.append(float("nan"))
                lower_errors.append(float("nan"))
                upper_errors.append(float("nan"))
            else:
                effects.append(effect)
                lower_errors.append(effect - interval[0])
                upper_errors.append(interval[1] - effect)
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
        axis.tick_params(axis="y", labelsize=7)
        for position, effect in zip(positions, effects, strict=True):
            if math.isnan(effect):
                axis.annotate(
                    ReportCellLiteral.NOT_AVAILABLE,
                    (0.0, position),
                    xytext=(5, 4),
                    textcoords="offset points",
                    fontsize=7,
                )
        axis.set_title(metric)
        axis.axvline(0.0)
    maximum_label_count = max(len(axis.get_yticklabels()) for axis in figure.axes)
    figure.set_size_inches(15, max(5, maximum_label_count * 0.35))
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    return destination


def render_evidence_arrival_trajectory(
    state_fractions: tuple[EvidenceStateFraction, ...],
    destination: Path,
) -> Path:
    if not state_fractions:
        raise ValueError("Evidence-Arrival State Trajectory: missing state evidence")
    expected_schedules = frozenset(EvidenceArrivalSchedule)
    observed_schedules = frozenset(observation.condition for observation in state_fractions)
    if observed_schedules != expected_schedules:
        raise ValueError("Evidence-Arrival State Trajectory: schedule grid is incomplete")
    keys = tuple(
        (observation.condition, observation.cycle, observation.state)
        for observation in state_fractions
    )
    if len(keys) != len(set(keys)):
        raise ValueError("Evidence-Arrival State Trajectory: duplicate state evidence")
    cycles = tuple(sorted(frozenset(observation.cycle for observation in state_fractions)))
    resource_horizon = current_application_context().scientific_config.protocol.resource_horizon
    horizon = resource_horizon.maximum_logical_evidence_cycles
    expected_cycles = tuple(range(horizon + 1))
    if cycles != expected_cycles:
        raise ValueError("Evidence-Arrival State Trajectory: cycle grid is incomplete")
    expected_keys = {
        (schedule, cycle, state)
        for schedule in expected_schedules
        for cycle in cycles
        for state in EVIDENCE_TRAJECTORY_STATE_VOCABULARY
    }
    if set(keys) != expected_keys:
        raise ValueError("Evidence-Arrival State Trajectory: cycle/state grid is incomplete")
    for schedule in expected_schedules:
        for cycle in cycles:
            observations = tuple(
                observation
                for observation in state_fractions
                if observation.condition == schedule and observation.cycle == cycle
            )
            denominators = frozenset(item.instance_total for item in observations)
            if len(denominators) != 1 or not next(iter(denominators)):
                raise ValueError("Evidence-Arrival State Trajectory: seed denominator is invalid")
            denominator = next(iter(denominators))
            if (
                any(
                    item.fraction != item.instance_count / item.instance_total
                    for item in observations
                )
                or sum(item.instance_count for item in observations) != denominator
            ):
                raise ValueError(
                    "Evidence-Arrival State Trajectory: state fractions do not partition seeds"
                )
    schedules = tuple(sorted(expected_schedules))
    states = EVIDENCE_TRAJECTORY_STATE_VOCABULARY
    figure = Figure(figsize=(5 * len(schedules), 4))
    first_axis = None
    for index, schedule in enumerate(schedules, start=1):
        axis = figure.add_subplot(1, len(schedules), index)
        if first_axis is None:
            first_axis = axis
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
    metrics = EFFICIENCY_PROFILE_METRICS
    methods = experiment_by_name(EFFICIENCY_MEASUREMENT_NAME).methods
    figure = Figure(figsize=(5 * len(metrics), 5))
    for index, selected_metric in enumerate(metrics, start=1):
        axis = figure.add_subplot(1, len(metrics), index)
        observations = tuple(
            efficiency_observation(metric_values, method, selected_metric) for method in methods
        )
        medians = tuple(
            float("nan") if observation is None else observation.median
            for observation in observations
        )
        lower_errors = tuple(
            float("nan") if observation is None else observation.median - observation.first_quartile
            for observation in observations
        )
        upper_errors = tuple(
            float("nan") if observation is None else observation.third_quartile - observation.median
            for observation in observations
        )
        axis.bar(methods, medians, yerr=(lower_errors, upper_errors), capsize=4)
        for method_index, observation in enumerate(observations):
            if observation is None:
                axis.annotate(
                    ReportCellLiteral.NOT_AVAILABLE,
                    (method_index, 0.0),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha="center",
                    fontsize=7,
                )
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
    expected_definitions = tuple(
        definition
        for definition in build_comparison_registry()
        if definition.experiment in experiments
        and (metrics is None or definition.metric in metrics)
    )
    if not expected_definitions:
        raise ValueError(f"{title}: no registered comparisons exist")
    observed: list[tuple[ComparisonDefinition, ComparisonResult]] = []
    for family in comparison_results:
        for comparison in family.comparisons:
            expected = next(
                (
                    definition
                    for definition in expected_definitions
                    if definition.comparison_name == comparison.definition.comparison_name
                ),
                None,
            )
            if expected is None:
                continue
            if expected != comparison.definition or family.family is not expected.family:
                raise ValueError(f"{title}: comparison identity does not match its registry")
            if any(
                definition.comparison_name == expected.comparison_name
                for definition, _comparison in observed
            ):
                raise ValueError(f"{title}: duplicate registered comparison evidence")
            observed.append((expected, comparison))
    for definition in expected_definitions:
        labels.append(
            f"{definition.scientific_scenario}\n"
            f"{definition.method} vs {definition.reference_method}"
        )
        comparison = next(
            (
                result
                for registered, result in observed
                if registered.comparison_name == definition.comparison_name
            ),
            None,
        )
        effect = None if comparison is None else comparison.mean_paired_difference
        interval = None if comparison is None else comparison.confidence_interval
        if effect is None or interval is None:
            effects.append(float("nan"))
            lower_errors.append(float("nan"))
            upper_errors.append(float("nan"))
            annotations.append(ReportCellLiteral.NOT_AVAILABLE)
            continue
        effects.append(effect)
        lower_errors.append(effect - interval[0])
        upper_errors.append(interval[1] - effect)
        adjusted_p = (
            "p=NA"
            if comparison is None or comparison.adjusted_p_value is None
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
        axis.annotate(
            label,
            (0.0 if math.isnan(effect) else effect, position),
            xytext=(5, 4),
            textcoords="offset points",
        )
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
    outcomes: tuple[CellExecutionOutcome, ...],
    experiment: ExperimentName,
    method: MethodName,
    scenario: ScenarioName,
    metric: MetricName,
) -> MetricValue | None:
    del outcomes
    row = _aggregate_metric_row(experiment, method, scenario, metric)
    return None if row is None else row.mean_value


def render_useful_backdoored_source(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    destination: Path,
    outcomes: tuple[CellExecutionOutcome, ...],
) -> Path:
    del comparison_results
    figure = Figure(figsize=(8, 5))
    axis = figure.add_subplot(1, 1, 1)
    scenario = PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT
    completed = tuple(
        outcome
        for outcome in outcomes
        if (
            outcome.completed
            and outcome.cell.experiment == SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME
            and outcome.cell.condition == scenario
        )
    )
    if not completed:
        raise ValueError("Useful Backdoored Source: missing completed source-exclusion evidence")
    methods = experiment_by_name(SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME).methods
    plotted = False
    for method in methods:
        asr = _aggregate_metric_row(
            SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
            method,
            scenario,
            ComparisonMetric.ATTACK_SUCCESS_RATE,
        )
        target_f1 = _aggregate_metric_row(
            SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
            method,
            scenario,
            ComparisonMetric.TARGET_F1,
        )
        mean_asr = None if asr is None else asr.mean_value
        mean_target_f1 = None if target_f1 is None else target_f1.mean_value
        asr_interval = (
            None
            if asr is None
            or asr.confidence_interval_lower is None
            or asr.confidence_interval_upper is None
            else (asr.confidence_interval_lower, asr.confidence_interval_upper)
        )
        target_f1_interval = (
            None
            if target_f1 is None
            or target_f1.confidence_interval_lower is None
            or target_f1.confidence_interval_upper is None
            else (target_f1.confidence_interval_lower, target_f1.confidence_interval_upper)
        )
        has_complete_estimate = (
            mean_asr is not None
            and mean_target_f1 is not None
            and asr_interval is not None
            and target_f1_interval is not None
        )
        if not has_complete_estimate:
            axis.errorbar(float("nan"), float("nan"), fmt="o", label=method)
            axis.annotate(
                ReportCellLiteral.NOT_AVAILABLE,
                (0.0, 0.0),
                xytext=(5, 4),
                textcoords="offset points",
                fontsize=7,
            )
            plotted = True
            continue
        if (
            mean_asr is None
            or mean_target_f1 is None
            or asr_interval is None
            or target_f1_interval is None
        ):
            raise ValueError("Useful Backdoored Source: incomplete aggregate estimate")
        x_error = (
            (mean_asr - asr_interval[0],),
            (asr_interval[1] - mean_asr,),
        )
        y_error = (
            (mean_target_f1 - target_f1_interval[0],),
            (target_f1_interval[1] - mean_target_f1,),
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
            if comparison.definition.experiment == experiment
        )
        comparison = next(
            (item for item in matching if item.definition.material_threshold is not None),
            None,
        )
        labels.append(experiment)
        if comparison is None:
            normalized_effects.append(float("nan"))
            lower_errors.append(float("nan"))
            upper_errors.append(float("nan"))
            annotations.append(ReportCellLiteral.NOT_AVAILABLE)
            continue
        threshold = comparison.definition.material_threshold
        effect = comparison.mean_paired_difference
        interval = comparison.confidence_interval
        if threshold is None or threshold <= 0.0:
            raise ValueError(f"{experiment}: collapse figure has an invalid material threshold")
        if effect is None or interval is None:
            normalized_effects.append(float("nan"))
            lower_errors.append(float("nan"))
            upper_errors.append(float("nan"))
            annotations.append(ReportCellLiteral.NOT_AVAILABLE)
            continue
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
            axis.annotate(
                annotation,
                (1.0 if math.isnan(effect) else effect, position),
                xytext=(5, 4),
                textcoords="offset points",
            )
        axis.axvline(1.0, color="black", linestyle="--")
    else:
        raise ValueError("Collapse Decision Effects: no preregistered collapse rows exist")
    axis.set_title(FigureName.COLLAPSE_DECISION_EFFECTS)
    axis.set_xlabel(FigureAxisName.PRIMARY_MATERIAL_EFFECT_OVER_THRESHOLD)
    axis.set_ylabel(FigureAxisName.MECHANISM)
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    return destination


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


COMPROMISED_CONDITION_COUNTS: tuple[
    tuple[ReproducerCondition | VerifierCondition, ScientificCellCount], ...
] = (
    (ReproducerCondition.CLEAN, 0),
    (ReproducerCondition.ONE_SOURCE_COPY, 1),
    (ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR, 1),
    (ReproducerCondition.ONE_VERIFIER_AWARE_BACKDOOR, 1),
    (ReproducerCondition.TWO_SOURCE_COPIES, 2),
    (ReproducerCondition.TWO_MODEL_REPLACEMENT_BACKDOORS, 2),
    (ReproducerCondition.TWO_VERIFIER_AWARE_BACKDOORS, 2),
    (VerifierCondition.ALL_HONEST, 0),
    (VerifierCondition.ONE_FALSE_POSITIVE, 1),
    (VerifierCondition.TWO_FALSE_POSITIVES, 2),
    (VerifierCondition.ONE_FALSE_NEGATIVE, 1),
    (VerifierCondition.TWO_FALSE_NEGATIVES, 2),
)
REPRODUCER_STRATEGY_CONDITIONS: tuple[
    tuple[FigureLegendText, ReproducerCondition, ReproducerCondition], ...
] = (
    (
        "Source Copy",
        ReproducerCondition.ONE_SOURCE_COPY,
        ReproducerCondition.TWO_SOURCE_COPIES,
    ),
    (
        "Model Replacement Backdoor",
        ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR,
        ReproducerCondition.TWO_MODEL_REPLACEMENT_BACKDOORS,
    ),
    (
        "Verifier-Aware Backdoor",
        ReproducerCondition.ONE_VERIFIER_AWARE_BACKDOOR,
        ReproducerCondition.TWO_VERIFIER_AWARE_BACKDOORS,
    ),
)


def _condition_compromised_count(
    condition: ReproducerCondition | VerifierCondition,
) -> ScientificCellCount:
    for registered_condition, compromised_count in COMPROMISED_CONDITION_COUNTS:
        if condition is registered_condition:
            return compromised_count
    raise ValueError(f"condition has no registered compromised count: {condition}")


def _series_panel(
    axis: Axes,
    series: BoundarySeries,
    xlabel: FigureAxisName,
    ylabel: FigureAxisName,
    title: FigureName | FigurePanelTitle,
) -> None:
    plotted = False
    for label, x_values, y_values in series:
        axis.plot(
            x_values,
            tuple(float("nan") if value is None else value for value in y_values),
            marker="o",
            label=label,
        )
        for x_value, y_value in zip(x_values, y_values, strict=True):
            if y_value is None:
                axis.annotate(
                    ReportCellLiteral.NOT_AVAILABLE,
                    (x_value, 0.0),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha="center",
                    fontsize=7,
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
    if not x_labels or not groups or len(values) != len(groups):
        raise ValueError(f"{title}: missing completed source evidence")
    positions = tuple(range(len(x_labels)))
    width = 0.8 / max(len(groups), 1)
    for index, group in enumerate(groups):
        offsets = tuple(position + index * width for position in positions)
        row = values[index]
        if len(row) != len(x_labels):
            raise ValueError(f"{title}: grouped source evidence has an incomplete condition grid")
        axis.bar(
            offsets,
            tuple(float("nan") if value is None else value for value in row),
            width=width,
            label=group,
        )
        for offset, value in zip(offsets, row, strict=True):
            if value is None:
                axis.annotate(
                    ReportCellLiteral.NOT_AVAILABLE,
                    (offset, 0.0),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha="center",
                    fontsize=7,
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
    definition = experiment_by_name(COMPROMISED_REPRODUCER_ROBUSTNESS_NAME)
    registered_conditions = frozenset(definition.conditions)
    expected_conditions = frozenset(
        (
            ReproducerCondition.CLEAN,
            *(
                condition
                for _, one, two in REPRODUCER_STRATEGY_CONDITIONS
                for condition in (one, two)
            ),
        )
    )
    if registered_conditions != expected_conditions:
        raise ValueError(
            "Compromised-Reproducer Boundary: condition strategies do not cover design"
        )
    methods = definition.methods
    counts: tuple[ScientificCellCount, ...] = (0, 1, 2)

    def series_for(metric: ComparisonMetric) -> BoundarySeries:
        series: BoundarySeries = tuple(
            (
                f"{strategy}\n{method}",
                counts,
                tuple(
                    _aggregate_metric_mean(
                        outcomes,
                        COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
                        method,
                        condition,
                        metric,
                    )
                    for condition in (
                        ReproducerCondition.CLEAN,
                        one_condition,
                        two_condition,
                    )
                ),
            )
            for strategy, one_condition, two_condition in REPRODUCER_STRATEGY_CONDITIONS
            for method in methods
        )
        return series

    mar_series = series_for(ComparisonMetric.MALICIOUS_ADMISSION)
    asr_series = series_for(ComparisonMetric.ATTACK_SUCCESS_RATE)

    def draw_mar(axis: Axes) -> None:
        _series_panel(
            axis,
            mar_series,
            FigureAxisName.COMPROMISED_REPRODUCER_COUNT,
            FigureAxisName.MALICIOUS_ADMISSION_RATE,
            FigureName.COMPROMISED_REPRODUCER_BOUNDARY,
        )
        annotation_value = maximum_byzantine_reproduction_rows()
        axis.axvline(annotation_value, color="black", linestyle="--")

    def draw_asr(axis: Axes) -> None:
        _series_panel(
            axis,
            asr_series,
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
    false_positive_destination: Path,
    false_negative_destination: Path,
    outcomes: tuple[CellExecutionOutcome, ...],
) -> tuple[Path, Path]:
    del comparison_results
    completed = _completed_outcomes(outcomes, COMPROMISED_VERIFIER_ROBUSTNESS_NAME)
    if not completed:
        raise ValueError("Compromised-Verifier Boundary: missing completed source evidence")
    verifier_definition = experiment_by_name(COMPROMISED_VERIFIER_ROBUSTNESS_NAME)
    if frozenset(verifier_definition.conditions) != frozenset(VerifierCondition):
        raise ValueError("Compromised-Verifier Boundary: condition panels do not cover design")
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
                    _aggregate_metric_mean(
                        outcomes,
                        COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
                        profile,
                        condition,
                        metric,
                    )
                    for condition in conditions
                ),
            )
            for profile in verifier_definition.methods
        )

    def render_mode(
        destination: Path,
        conditions: tuple[VerifierCondition, ...],
        metric: ComparisonMetric,
        ylabel: FigureAxisName,
        title: FigureName,
    ) -> Path:
        figure = Figure(figsize=(8, 5))
        axis = figure.add_subplot(1, 1, 1)
        _series_panel(
            axis,
            series_for(conditions, metric),
            FigureAxisName.COMPROMISED_VERIFIER_COUNT,
            ylabel,
            title,
        )
        config = current_application_context().scientific_config.protocol
        axis.axvline(
            config.verification.maximum_byzantine_verifiers_per_panel,
            color="black",
            linestyle="--",
        )
        diagnostic = config.diagnostic_random_verifier_profile
        risk = random_verifier_contamination_probability(
            diagnostic.byzantine_domain_count,
            diagnostic.panel_size,
        )
        axis.text(
            FIGURE_ANNOTATION_INSET,
            1.0 - FIGURE_ANNOTATION_INSET,
            f"Random-profile exact P(K ≥ 2) = {risk:.6g}",
            transform=axis.transAxes,
            va="top",
        )
        figure.tight_layout()
        figure.savefig(destination, dpi=150)
        return destination

    false_positive_figure = render_mode(
        false_positive_destination,
        false_positive_conditions,
        ComparisonMetric.MALICIOUS_ADMISSION,
        FigureAxisName.MALICIOUS_ADMISSION_RATE,
        FigureName.COMPROMISED_VERIFIER_FALSE_POSITIVE_BOUNDARY,
    )
    false_negative_figure = render_mode(
        false_negative_destination,
        false_negative_conditions,
        ComparisonMetric.LEGITIMATE_ADMISSION,
        FigureAxisName.LEGITIMATE_ADMISSION_RATE,
        FigureName.COMPROMISED_VERIFIER_FALSE_NEGATIVE_BOUNDARY,
    )
    return false_positive_figure, false_negative_figure


def render_shared_epistemic_failure(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    destination: Path,
    outcomes: tuple[CellExecutionOutcome, ...],
) -> Path:
    if not outcomes:
        raise ValueError("Shared Epistemic Failure: missing completed source evidence")
    failure_types = tuple(EpistemicFailureType)

    def strengths_for(failure_type: EpistemicFailureType) -> tuple[AttackStrength, ...]:
        return tuple(float(token) for token in epistemic_strength_tokens(failure_type))

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
                _aggregate_metric_mean(
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
    definition = experiment_by_name(CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME)
    granularities = definition.methods
    mixtures = definition.conditions

    def values_for(metric: MetricName) -> tuple[tuple[MetricValue | None, ...], ...]:
        return tuple(
            tuple(
                _aggregate_metric_mean(
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
    definition = experiment_by_name(HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME)
    regimes = definition.conditions
    methods = definition.methods
    positions = tuple(range(len(regimes)))

    def values_for(metric: MetricName) -> tuple[tuple[MetricValue | None, ...], ...]:
        return tuple(
            tuple(
                _aggregate_metric_mean(
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
    definition = experiment_by_name(ADMISSION_DELAY_DECOMPOSITION_NAME)
    cells = tuple(
        (method, condition) for method in definition.methods for condition in definition.conditions
    )
    phases: tuple[tuple[MetricName, FigureLegendLabel], ...] = (
        (DelayPhaseMetric.ASSIGNMENT_SECONDS, FigureLegendLabel.ASSIGNMENT),
        (DelayPhaseMetric.REPRODUCE_SECONDS, FigureLegendLabel.REPRODUCE),
        (DelayPhaseMetric.VERIFY_SECONDS, FigureLegendLabel.VERIFY),
        (DelayPhaseMetric.SYNTHESIZE_SECONDS, FigureLegendLabel.SYNTHESIZE),
    )
    phase_values = tuple(
        tuple(
            _aggregate_metric_mean(
                outcomes,
                ADMISSION_DELAY_DECOMPOSITION_NAME,
                method,
                condition,
                metric,
            )
            for method, condition in cells
        )
        for metric, _label in phases
    )
    complete_cells = tuple(
        all(phase[index] is not None for phase in phase_values) for index in range(len(cells))
    )
    bottoms = [0.0] * len(cells)
    for phase, (_metric, label) in zip(phase_values, phases, strict=True):
        values = tuple(
            0.0 if not complete_cells[index] else (0.0 if value is None else value)
            for index, value in enumerate(phase)
        )
        axis.bar(range(len(cells)), values, bottom=bottoms, label=label)
        bottoms = [bottom + value for bottom, value in zip(bottoms, values, strict=True)]
    for index, is_complete in enumerate(complete_cells):
        if not is_complete:
            axis.annotate(
                ReportCellLiteral.NOT_AVAILABLE,
                (index, 0.0),
                xytext=(0, 6),
                textcoords="offset points",
                ha="center",
                fontsize=7,
            )
    t_evidence = tuple(
        _aggregate_metric_mean(
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
        *render_compromised_verifier_boundary(
            comparison_results,
            figures_root / f"{COMPROMISED_VERIFIER_FALSE_POSITIVE_BOUNDARY_FIGURE_NAME}.png",
            figures_root / f"{COMPROMISED_VERIFIER_FALSE_NEGATIVE_BOUNDARY_FIGURE_NAME}.png",
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
) -> tuple[Path, ...] | None:
    figure: Path | None = None
    if result.experiment == COMPROMISED_REPRODUCER_ROBUSTNESS_NAME:
        figure = render_compromised_reproducer_boundary(
            result.comparison_results,
            figures_root / f"{COMPROMISED_REPRODUCER_BOUNDARY_FIGURE_NAME}.png",
            result.outcomes,
        )
    elif result.experiment == COMPROMISED_VERIFIER_ROBUSTNESS_NAME:
        return render_compromised_verifier_boundary(
            result.comparison_results,
            figures_root / f"{COMPROMISED_VERIFIER_FALSE_POSITIVE_BOUNDARY_FIGURE_NAME}.png",
            figures_root / f"{COMPROMISED_VERIFIER_FALSE_NEGATIVE_BOUNDARY_FIGURE_NAME}.png",
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
    return None if figure is None else (figure,)


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
            figures.extend(specialized)
    return tuple(figures)


def evidence_trajectory() -> tuple[EvidenceStateFraction, ...]:
    path = (
        experiment_metric_evidence_root(EVIDENCE_SCARCITY_AND_DORMANCY_NAME)
        / STATE_TRAJECTORY_FRACTIONS_PARQUET_NAME
    )
    return read_state_trajectory_fractions(path, EVIDENCE_SCARCITY_AND_DORMANCY_NAME)


def project_result_evidence(
    plan: ExperimentPlan,
    load_result: Callable[[ExperimentName], ExperimentExecutionResult],
) -> tuple[tuple[ComparisonFamilyResult, ...], tuple[CellExecutionOutcome, ...]]:
    results = tuple(load_result(planned.definition.name) for planned in plan.experiments)
    return (
        tuple(comparison for result in results for comparison in result.comparison_results),
        tuple(outcome for result in results for outcome in result.outcomes),
    )
