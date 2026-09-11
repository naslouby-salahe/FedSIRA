from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TypeAlias

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from fedsira.domain.enums import (
    AdmissionState,
    CapabilityContractScope,
    CoreMethodIdentity,
    RootCauseMixture,
)
from fedsira.domain.types import (
    AttackStrength,
    EvidenceCycleIndex,
    ExperimentName,
    FigureName,
    FrozenDomainModel,
    MethodName,
    MetricName,
    MetricValue,
    Probability,
    ReproductionRowCount,
    ScenarioName,
    ScientificCellCount,
    TextValue,
)
from fedsira.evaluation.comparisons import (
    ComparisonFamilyResult,
    ComparisonMetric,
    ComparisonResult,
)
from fedsira.evaluation.summaries import bootstrap_percentile_confidence_interval
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
    DescriptiveScientificMetric,
    EpistemicFailureType,
    HeterogeneityRegime,
    PrimaryScenario,
    VerifierCondition,
)
from fedsira.experiments.execution import CellExecutionOutcome, ExperimentExecutionResult
from fedsira.runtime import current_application_context

BoundarySeries: TypeAlias = tuple[
    tuple[TextValue, tuple[ScientificCellCount, ...], tuple[MetricValue | None, ...]],
    ...,
]
AxisDraw: TypeAlias = Callable[[Axes], None]


MANDATORY_FIGURE_NAMES: tuple[FigureName, ...] = (
    "FedSIRA Protocol Schematic",
    "Primary Security-Utility Tradeoff",
    "Useful Backdoored Source",
    "Collapse Decision Effects",
    "Compromised-Reproducer Boundary",
    "Compromised-Verifier Boundary",
    "Evidence-Arrival State Trajectory",
    "Shared Epistemic Failure",
    "Capability-Granularity Boundary",
    "Heterogeneity Synthesis Boundary",
    "Admission-Delay Decomposition",
    "Efficiency Profile",
    "Secondary Generalization",
)
FIGURE_ANNOTATION_INSET: Probability = 1 / 100


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


def validate_mandatory_figures_covered(
    rendered_figures: tuple[Path, ...],
) -> tuple[FigureName, ...]:
    rendered_names = frozenset(path.stem for path in rendered_figures)
    return tuple(name for name in MANDATORY_FIGURE_NAMES if name not in rendered_names)


def render_protocol_schematic(destination: Path) -> Path:
    figure = Figure(figsize=(10, 2.5))
    axis = figure.add_subplot(1, 1, 1)
    axis.axis("off")
    steps = (
        "source commitment\n(zero direct weight)",
        "fixed Capability\nContract",
        "non-source\nreproduction",
        "post-commitment\nverifier panels",
        "five-row external\nreproduction verification",
        "Krum",
        "final\nfresh gate",
        "admission /\ndormancy / rejection",
    )
    for index, step in enumerate(steps):
        x_position = index * 1.25
        axis.text(x_position, 0.5, step, ha="center", va="center")
        if index < len(steps) - 1:
            axis.plot((x_position + 0.45, x_position + 0.8), (0.5, 0.5))
    axis.set_xlim(-0.5, (len(steps) - 1) * 1.25 + 0.5)
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
        labels: list[MethodName] = []
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
                f"Primary Security-Utility Tradeoff: missing comparison evidence for {metric.value}"
            )
        positions = tuple(range(len(labels)))
        axis.errorbar(
            effects,
            positions,
            xerr=(tuple(lower_errors), tuple(upper_errors)),
            fmt="o",
        )
        axis.set_yticks(positions, labels)
        axis.set_title(metric.value)
        axis.axvline(0.0)
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    return destination


def _state_fraction(
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
    for index, schedule in enumerate(schedules, start=1):
        axis = figure.add_subplot(1, len(schedules), index)
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
                _state_fraction(state_fractions, schedule, cycle, state) for cycle in cycles
            )
            axis.step(cycles, fractions, where="post", marker="o", label=state.value)
        axis.set_title(schedule)
        axis.set_xlabel("logical evidence cycle")
        axis.set_ylim(0.0, 1.0)
    figure.axes[0].set_ylabel("fraction of seed instances")
    figure.axes[0].legend()
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    return destination


def _efficiency_observation(
    observations: tuple[EfficiencyMetricObservation, ...],
    method: MethodName,
    metric: MetricName,
) -> EfficiencyMetricObservation:
    for observation in observations:
        if observation.method == method and observation.metric == metric:
            return observation
    raise ValueError(f"missing efficiency telemetry for {method} / {metric}")


EFFICIENCY_PROFILE_METRICS: tuple[MetricName, ...] = (
    DescriptiveScientificMetric.WALL_CLOCK_SECONDS.value,
    DescriptiveScientificMetric.COMMUNICATION_BYTES.value,
    DescriptiveScientificMetric.PEAK_GPU_MEMORY_BYTES.value,
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
            _efficiency_observation(metric_values, method, selected_metric) for method in methods
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
    xlabel: TextValue,
    ylabel: TextValue,
    experiments: tuple[ExperimentName, ...],
    metrics: tuple[ComparisonMetric, ...] | None = None,
    annotation: TextValue | None = None,
) -> Path:
    figure = Figure(figsize=(8, 5))
    axis = figure.add_subplot(1, 1, 1)
    labels: list[MethodName] = []
    effects: list[MetricValue] = []
    lower_errors: list[MetricValue] = []
    upper_errors: list[MetricValue] = []
    annotations: list[TextValue] = []
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
            label="target-F1 threshold",
        )
        axis.legend()
    else:
        raise ValueError("Useful Backdoored Source: missing completed source-exclusion evidence")
    axis.set_title("Useful Backdoored Source")
    axis.set_xlabel("post-production ASR (lower is better)")
    axis.set_ylabel("target F1")
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
    annotations: list[TextValue] = []
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
            "NA" if comparison.adjusted_p_value is None else f"p={comparison.adjusted_p_value:.4g}"
        )
        annotations.append(f"{adjusted_p}; {comparison.comparison_state.value}")
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
    axis.set_title("Collapse Decision Effects")
    axis.set_xlabel("primary material effect / material threshold")
    axis.set_ylabel("mechanism")
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    return destination


def _outcome_metric_mean(
    outcomes: tuple[CellExecutionOutcome, ...],
    experiment: ExperimentName,
    method: MethodName,
    condition: TextValue,
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


def _condition_compromised_count(condition: TextValue) -> ScientificCellCount:
    if condition.startswith("Two"):
        return 2
    if condition.startswith("One"):
        return 1
    return 0


def _series_panel(
    axis: Axes,
    series: BoundarySeries,
    xlabel: TextValue,
    ylabel: TextValue,
    title: FigureName,
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
    x_labels: tuple[TextValue, ...],
    groups: tuple[TextValue, ...],
    values: tuple[tuple[MetricValue | None, ...], ...],
    xlabel: TextValue,
    ylabel: TextValue,
    title: FigureName,
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
    panels: tuple[tuple[TextValue, AxisDraw], ...],
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
            "compromised reproducer count",
            "malicious admission rate",
            "Compromised-Reproducer Boundary",
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
            "compromised reproducer count",
            "attack success rate",
            "Compromised-Reproducer Boundary — ASR",
        )

    return _single_panel_figure(
        destination,
        (
            ("malicious admission", draw_mar),
            ("attack success rate", draw_asr),
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
        VerifierCondition.ALL_HONEST.value,
        VerifierCondition.ONE_FALSE_POSITIVE.value,
        VerifierCondition.TWO_FALSE_POSITIVES.value,
    )
    false_negative_conditions = (
        VerifierCondition.ALL_HONEST.value,
        VerifierCondition.ONE_FALSE_NEGATIVE.value,
        VerifierCondition.TWO_FALSE_NEGATIVES.value,
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
            "compromised verifier count",
            "malicious admission rate",
            "Compromised-Verifier Boundary — false-positive mode",
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
            "compromised verifier count",
            "legitimate admission rate",
            "Compromised-Verifier Boundary — false-negative mode",
        )
        axis.axvline(
            current_application_context().scientific_config.protocol.verification.maximum_byzantine_verifiers_per_panel,
            color="black",
            linestyle="--",
        )

    return _single_panel_figure(
        destination,
        (
            ("false positive", draw_false_positive),
            ("false negative", draw_false_negative),
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
                    and outcome.cell.condition.startswith(f"{failure_type.value}|")
                )
            )
        )

    def clean_oracle_series() -> BoundarySeries:
        series: list[
            tuple[TextValue, tuple[ScientificCellCount, ...], tuple[MetricValue | None, ...]]
        ] = []
        for failure_type in failure_types:
            strengths = strengths_for(failure_type)
            if not strengths:
                continue
            differences: list[MetricValue | None] = []
            for strength in strengths:
                condition = f"{failure_type.value}|{strength:.2f}"
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
                    failure_type.value,
                    tuple(int(value) for value in strengths),
                    tuple(differences),
                )
            )
        return tuple(series)

    def admission_series() -> BoundarySeries:
        series: list[
            tuple[TextValue, tuple[ScientificCellCount, ...], tuple[MetricValue | None, ...]]
        ] = []
        for failure_type in failure_types:
            strengths = strengths_for(failure_type)
            if not strengths:
                continue
            values = tuple(
                _outcome_metric_mean(
                    outcomes,
                    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
                    CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
                    f"{failure_type.value}|{strength:.2f}",
                    ComparisonMetric.LEGITIMATE_ADMISSION,
                )
                for strength in strengths
            )
            series.append((failure_type.value, tuple(int(value) for value in strengths), values))
        return tuple(series)

    def draw_clean_oracle(axis: Axes) -> None:
        _series_panel(
            axis,
            clean_oracle_series(),
            "corruption/confound strength",
            "clean-oracle target-F1 difference",
            "Shared Epistemic Failure — clean oracle",
        )
        axis.axhline(0.0)

    def draw_admission(axis: Axes) -> None:
        _series_panel(
            axis,
            admission_series(),
            "corruption/confound strength",
            "admission rate under corrupted operational evidence",
            "Shared Epistemic Failure — admission",
        )

    return _single_panel_figure(
        destination,
        (
            ("clean oracle", draw_clean_oracle),
            ("admission", draw_admission),
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
        scope.value
        for scope in CapabilityContractScope
        if any(outcome.cell.method == scope.value for outcome in completed)
    )
    mixtures = tuple(
        mixture.value
        for mixture in RootCauseMixture
        if any(outcome.cell.condition == mixture.value for outcome in completed)
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
            values_for("false-same-capability-rate"),
            "Capability Contract granularity",
            "false same-capability certification rate",
            "Capability-Granularity Boundary — false equivalence",
        )

    def draw_root_cause(axis: Axes) -> None:
        _grouped_panel(
            axis,
            granularities,
            tuple(f"{mixture}: root cause A" for mixture in mixtures)
            + tuple(f"{mixture}: root cause B" for mixture in mixtures),
            values_for("root-cause-a-target-f1") + values_for("root-cause-b-target-f1"),
            "Capability Contract granularity",
            "target F1",
            "Capability-Granularity Boundary — per-root-cause target F1",
        )

    return _single_panel_figure(
        destination,
        (
            ("false equivalence", draw_false_equivalence),
            ("root cause", draw_root_cause),
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
        regime.value
        for regime in HeterogeneityRegime
        if any(outcome.cell.condition == regime.value for outcome in completed)
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
            "heterogeneity regime",
            "legitimate admission rate",
            "Heterogeneity Synthesis Boundary — legitimate admission",
        )

    def draw_worst_domain(axis: Axes) -> None:
        _grouped_panel(
            axis,
            regimes,
            methods,
            values_for(ComparisonMetric.WORST_DOMAIN_TARGET_F1),
            "heterogeneity regime",
            "worst-domain target F1",
            "Heterogeneity Synthesis Boundary — worst-domain target F1",
        )

    del positions
    return _single_panel_figure(
        destination,
        (
            ("legitimate admission", draw_admission),
            ("worst-domain target F1", draw_worst_domain),
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
    phases: tuple[tuple[MetricName, TextValue], ...] = (
        ("assignment-seconds", "assignment"),
        ("reproduce-seconds", "reproduce"),
        ("verify-seconds", "verify"),
        ("synthesize-seconds", "synthesize"),
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
            DescriptiveScientificMetric.T_EVIDENCE.value,
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
    axis.set_ylabel("post-evidence wall-clock seconds")
    axis.set_title("Admission-Delay Decomposition")
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
        "Secondary Generalization",
        "target-F1 paired effect vs predeclared comparator",
        "method / secondary scenario",
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
