from __future__ import annotations

from pathlib import Path

from matplotlib.figure import Figure

from fedsira.domain.enums import AdmissionState, RootCauseMixture
from fedsira.domain.types import (
    EvidenceCycleIndex,
    ExperimentName,
    FigureName,
    FrozenDomainModel,
    MethodName,
    MetricName,
    MetricValue,
    Probability,
    TextValue,
)
from fedsira.evaluation.comparisons import ComparisonFamilyResult, ComparisonMetric
from fedsira.evaluation.summaries import bootstrap_percentile_confidence_interval
from fedsira.experiments.definitions import (
    ADMISSION_DELAY_DECOMPOSITION_NAME,
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    COLLAPSE_EXPERIMENT_NAMES,
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
    SECONDARY_DATASET_GENERALIZATION_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    HeterogeneityRegime,
    PrimaryScenario,
    ReproducerCondition,
    VerifierCondition,
)
from fedsira.experiments.executor import CellExecutionOutcome
from fedsira.runtime import current_application_context

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
    cycle: EvidenceCycleIndex
    state: AdmissionState
    fraction: Probability


class EfficiencyMetricObservation(FrozenDomainModel):
    method: MethodName
    metric: MetricName
    value: MetricValue


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
            axis.text(0.5, 0.5, "no evidence", ha="center", va="center")
            axis.set_title(metric.value)
            continue
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
    cycle: EvidenceCycleIndex,
    state: AdmissionState,
) -> Probability:
    for observation in observations:
        if observation.cycle == cycle and observation.state is state:
            return observation.fraction
    return 0.0


def render_evidence_arrival_trajectory(
    state_fractions: tuple[EvidenceStateFraction, ...],
    destination: Path,
) -> Path:
    figure = Figure(figsize=(8, 5))
    axis = figure.add_subplot(1, 1, 1)
    cycles = tuple(sorted(frozenset(observation.cycle for observation in state_fractions)))
    states = (
        AdmissionState.DORMANT,
        AdmissionState.VERIFICATION_PENDING,
        AdmissionState.ADMITTED,
        AdmissionState.EXPIRED,
    )
    if not cycles:
        axis.text(0.5, 0.5, "no evidence", ha="center", va="center")
    else:
        for state in states:
            fractions = tuple(_state_fraction(state_fractions, cycle, state) for cycle in cycles)
            axis.plot(cycles, fractions, marker="o", label=state.value)
        axis.legend()
    axis.set_xlabel("logical evidence cycle")
    axis.set_ylabel("fraction of seed instances")
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    return destination


def _efficiency_value(
    observations: tuple[EfficiencyMetricObservation, ...],
    method: MethodName,
    metric: MetricName,
) -> MetricValue:
    for observation in observations:
        if observation.method == method and observation.metric == metric:
            return observation.value
    return 0.0


def render_efficiency_profile(
    metric_values: tuple[EfficiencyMetricObservation, ...],
    metric: MetricName | None,
    destination: Path,
    comparison_results: tuple[ComparisonFamilyResult, ...] = (),
) -> Path:
    if not metric_values:
        return _render_experiment_effects(
            comparison_results,
            destination,
            "Efficiency Profile",
            "paired post-evidence overhead",
            "method / metric",
            (EFFICIENCY_MEASUREMENT_NAME,),
        )
    metrics = (
        (metric,)
        if metric is not None
        else tuple(
            candidate
            for candidate in (
                "post-evidence-wall-clock-seconds",
                "communication-bytes",
                "peak-gpu-memory-bytes",
            )
            if any(observation.metric == candidate for observation in metric_values)
        )
    )
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
        values = tuple(
            _efficiency_value(metric_values, method, selected_metric) for method in methods
        )
        axis.bar(methods, values)
        axis.set_ylabel(selected_metric)
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
    if effects:
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
    else:
        axis.text(0.5, 0.5, "no completed comparison evidence", ha="center", va="center")
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
    outcomes: tuple[CellExecutionOutcome, ...] = (),
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
            else ((mean_asr - asr_interval[0], asr_interval[1] - mean_asr),)
        )
        y_error = (
            None
            if target_f1_interval is None
            else ((mean_target_f1 - target_f1_interval[0], target_f1_interval[1] - mean_target_f1),)
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
        axis.text(0.5, 0.5, "no completed source-exclusion evidence", ha="center", va="center")
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
        axis.text(0.5, 0.5, "no completed collapse evidence", ha="center", va="center")
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


def _render_outcome_condition_lines(
    outcomes: tuple[CellExecutionOutcome, ...],
    comparison_results: tuple[ComparisonFamilyResult, ...],
    destination: Path,
    title: FigureName,
    experiment: ExperimentName,
    conditions: tuple[TextValue, ...],
    metric: MetricName,
    ylabel: TextValue,
    fallback_xlabel: TextValue,
) -> Path:
    methods = tuple(
        sorted(
            frozenset(
                outcome.cell.method
                for outcome in outcomes
                if outcome.completed and outcome.cell.experiment == experiment
            )
        )
    )
    figure = Figure(figsize=(10, 5))
    axis = figure.add_subplot(1, 1, 1)
    plotted = False
    positions = tuple(range(len(conditions)))
    for method in methods:
        values = tuple(
            _outcome_metric_mean(outcomes, experiment, method, condition, metric)
            for condition in conditions
        )
        if not any(value is not None for value in values):
            continue
        axis.plot(
            positions,
            tuple(float("nan") if value is None else value for value in values),
            marker="o",
            label=method,
        )
        plotted = True
    if plotted:
        axis.set_xticks(positions, conditions, rotation=25, ha="right")
        axis.set_xlabel("condition")
        axis.set_ylabel(ylabel)
        axis.legend()
    else:
        figure.clear()
        return _render_experiment_effects(
            comparison_results,
            destination,
            title,
            fallback_xlabel,
            "method / metric",
            (experiment,),
        )
    axis.set_title(title)
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    return destination


def render_compromised_reproducer_boundary(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    destination: Path,
    outcomes: tuple[CellExecutionOutcome, ...] = (),
) -> Path:
    return _render_outcome_condition_lines(
        outcomes,
        comparison_results,
        destination,
        "Compromised-Reproducer Boundary",
        COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
        tuple(condition.value for condition in ReproducerCondition),
        ComparisonMetric.MALICIOUS_ADMISSION,
        "malicious admission rate",
        "paired effect",
    )


def render_compromised_verifier_boundary(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    destination: Path,
    outcomes: tuple[CellExecutionOutcome, ...] = (),
) -> Path:
    return _render_outcome_condition_lines(
        outcomes,
        comparison_results,
        destination,
        "Compromised-Verifier Boundary",
        COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
        tuple(condition.value for condition in VerifierCondition),
        ComparisonMetric.MALICIOUS_ADMISSION,
        "malicious admission rate",
        "paired effect",
    )


def render_shared_epistemic_failure(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    destination: Path,
    outcomes: tuple[CellExecutionOutcome, ...] = (),
) -> Path:
    conditions = tuple(
        outcome.cell.condition
        for outcome in outcomes
        if outcome.completed and outcome.cell.experiment == SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME
    )
    return _render_outcome_condition_lines(
        outcomes,
        comparison_results,
        destination,
        "Shared Epistemic Failure",
        SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
        tuple(sorted(frozenset(conditions))),
        "clean-oracle-material-degradation",
        "clean-oracle material-degradation rate",
        "paired effect",
    )


def render_capability_granularity_boundary(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    destination: Path,
    outcomes: tuple[CellExecutionOutcome, ...] = (),
) -> Path:
    return _render_outcome_condition_lines(
        outcomes,
        comparison_results,
        destination,
        "Capability-Granularity Boundary",
        CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
        tuple(condition.value for condition in RootCauseMixture),
        "false-same-capability-rate",
        "false same-capability certification rate",
        "paired effect",
    )


def render_heterogeneity_synthesis_boundary(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    destination: Path,
    outcomes: tuple[CellExecutionOutcome, ...] = (),
) -> Path:
    return _render_outcome_condition_lines(
        outcomes,
        comparison_results,
        destination,
        "Heterogeneity Synthesis Boundary",
        HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
        tuple(regime.value for regime in HeterogeneityRegime),
        ComparisonMetric.LEGITIMATE_ADMISSION,
        "legitimate admission rate",
        "paired effect",
    )


def render_admission_delay_decomposition(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    destination: Path,
    outcomes: tuple[CellExecutionOutcome, ...] = (),
) -> Path:
    delay_outcomes = tuple(
        outcome
        for outcome in outcomes
        if outcome.completed and outcome.cell.experiment == ADMISSION_DELAY_DECOMPOSITION_NAME
    )
    if delay_outcomes:
        figure = Figure(figsize=(12, 5))
        axis = figure.add_subplot(1, 1, 1)
        cells = tuple(
            sorted(
                frozenset(
                    (outcome.cell.method, outcome.cell.condition) for outcome in delay_outcomes
                )
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
        labels = tuple(f"{method}\n{condition}" for method, condition in cells)
        axis.set_xticks(range(len(cells)), labels, rotation=25, ha="right")
        axis.set_ylabel("post-evidence wall-clock seconds")
        axis.set_title("Admission-Delay Decomposition")
        axis.legend()
        figure.tight_layout()
        figure.savefig(destination, dpi=150)
        return destination
    return _render_experiment_effects(
        comparison_results,
        destination,
        "Admission-Delay Decomposition",
        "paired effect",
        "method / metric",
        (ADMISSION_DELAY_DECOMPOSITION_NAME,),
    )


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
    evidence_trajectory: tuple[EvidenceStateFraction, ...] | None = None,
    telemetry: tuple[EfficiencyMetricObservation, ...] | None = None,
    outcomes: tuple[CellExecutionOutcome, ...] = (),
) -> tuple[Path, ...]:
    schematic = figures_root / "FedSIRA Protocol Schematic.png"
    render_protocol_schematic(schematic)
    tradeoff = figures_root / "Primary Security-Utility Tradeoff.png"
    render_security_utility_tradeoff(comparison_results, tradeoff)
    trajectory = figures_root / "Evidence-Arrival State Trajectory.png"
    render_evidence_arrival_trajectory(evidence_trajectory or (), trajectory)
    efficiency = figures_root / "Efficiency Profile.png"
    render_efficiency_profile(
        telemetry or (),
        None,
        efficiency,
        comparison_results,
    )
    return (
        schematic,
        tradeoff,
        render_useful_backdoored_source(
            comparison_results,
            figures_root / "Useful Backdoored Source.png",
            outcomes,
        ),
        render_collapse_decision_effects(
            comparison_results, figures_root / "Collapse Decision Effects.png"
        ),
        render_compromised_reproducer_boundary(
            comparison_results, figures_root / "Compromised-Reproducer Boundary.png", outcomes
        ),
        render_compromised_verifier_boundary(
            comparison_results, figures_root / "Compromised-Verifier Boundary.png", outcomes
        ),
        trajectory,
        render_shared_epistemic_failure(
            comparison_results, figures_root / "Shared Epistemic Failure.png", outcomes
        ),
        render_capability_granularity_boundary(
            comparison_results, figures_root / "Capability-Granularity Boundary.png", outcomes
        ),
        render_heterogeneity_synthesis_boundary(
            comparison_results, figures_root / "Heterogeneity Synthesis Boundary.png", outcomes
        ),
        render_admission_delay_decomposition(
            comparison_results, figures_root / "Admission-Delay Decomposition.png", outcomes
        ),
        efficiency,
        render_secondary_generalization(
            comparison_results, figures_root / "Secondary Generalization.png"
        ),
    )
