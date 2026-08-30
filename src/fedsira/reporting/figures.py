from __future__ import annotations

from pathlib import Path

from matplotlib.figure import Figure

from fedsira.analysis.comparisons import ComparisonFamilyResult, ComparisonMetric
from fedsira.domain.enums import ClaimState
from fedsira.domain.records import (
    EvidenceCycleIndex,
    FigureName,
    FrozenDomainModel,
    MethodName,
    MetricName,
    MetricValue,
    Probability,
)

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


class EvidenceStateFraction(FrozenDomainModel):
    cycle: EvidenceCycleIndex
    state: ClaimState
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
        "fixed Capability\nClaim Contract",
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
        for family in comparison_results:
            for comparison in family.comparisons:
                if comparison.definition.metric is not metric:
                    continue
                if comparison.mean_paired_difference is None:
                    continue
                labels.append(comparison.definition.reference_method)
                effects.append(comparison.mean_paired_difference)
        if not labels:
            axis.text(0.5, 0.5, "no evidence", ha="center", va="center")
            axis.set_title(metric.value)
            continue
        positions = tuple(range(len(labels)))
        axis.scatter(effects, positions)
        axis.set_yticks(positions, labels)
        axis.set_title(metric.value)
        axis.axvline(0.0)
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    return destination


def _state_fraction(
    observations: tuple[EvidenceStateFraction, ...],
    cycle: EvidenceCycleIndex,
    state: ClaimState,
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
        ClaimState.DORMANT,
        ClaimState.VERIFICATION_PENDING,
        ClaimState.ADMITTED,
        ClaimState.EXPIRED,
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
    metric: MetricName,
    destination: Path,
) -> Path:
    figure = Figure(figsize=(8, 5))
    axis = figure.add_subplot(1, 1, 1)
    methods = tuple(
        sorted(
            frozenset(
                observation.method for observation in metric_values if observation.metric == metric
            )
        )
    )
    values = tuple(_efficiency_value(metric_values, method, metric) for method in methods)
    axis.bar(methods, values)
    axis.set_ylabel(metric)
    axis.set_title(metric)
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    return destination
