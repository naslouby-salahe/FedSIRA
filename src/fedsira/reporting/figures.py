from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as pyplot

from fedsira.analysis.comparisons import ComparisonFamilyResult
from fedsira.domain.records import CanonicalToken

MANDATORY_FIGURE_NAMES: tuple[CanonicalToken, ...] = (
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

_REFERENCE_LINE_WIDTH = 1


def validate_mandatory_figures_covered(
    rendered_figures: Sequence[Path],
) -> tuple[CanonicalToken, ...]:
    rendered_names = {path.stem for path in rendered_figures}
    missing = [name for name in MANDATORY_FIGURE_NAMES if name not in rendered_names]
    return tuple(missing)


def render_protocol_schematic(destination: Path) -> Path:
    figure, axis = pyplot.subplots(figsize=(10, 2.5))
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
        axis.text(
            index * 1.25,
            0.5,
            step,
            ha="center",
            va="center",
            bbox={"boxstyle": "round", "facecolor": "lightgray"},
        )
        if index < len(steps) - 1:
            axis.annotate(
                "",
                xy=((index + 1) * 1.25 - 0.5, 0.5),
                xytext=(index * 1.25 + 0.5, 0.5),
                arrowprops={"arrowstyle": "->"},
            )
    axis.set_xlim(-0.5, (len(steps) - 1) * 1.25 + 0.5)
    axis.set_ylim(0, 1)
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    pyplot.close(figure)
    return destination


def render_security_utility_tradeoff(
    comparison_results: Sequence[ComparisonFamilyResult],
    destination: Path,
) -> Path:
    figure, axes = pyplot.subplots(1, 3, figsize=(4 * 3, 4))
    metrics = ("target-f1", "asr", "malicious-admission")
    for axis, metric in zip(axes, metrics, strict=True):
        labels: list[str] = []
        effects: list[float] = []
        errors: list[float] = []
        for family in comparison_results:
            for comparison in family.comparisons:
                if comparison.definition.metric != metric:
                    continue
                if comparison.mean_paired_difference is None:
                    continue
                labels.append(comparison.definition.reference)
                effects.append(comparison.mean_paired_difference)
                if comparison.confidence_interval is None:
                    errors.append(0.0)
                else:
                    _lower, upper = comparison.confidence_interval
                    errors.append(max(upper - comparison.mean_paired_difference, 0.0))
        if not labels:
            axis.text(0.5, 0.5, "no evidence", ha="center", va="center")
            axis.set_title(metric)
            continue
        axis.errorbar(
            effects,
            range(len(labels)),
            xerr=errors,
            fmt="o",
        )
        axis.set_yticks(range(len(labels)), labels)
        axis.set_title(metric)
        axis.axvline(0.0, color="black", linewidth=_REFERENCE_LINE_WIDTH)
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    pyplot.close(figure)
    return destination


def render_evidence_arrival_trajectory(
    state_fractions_by_cycle: Mapping[int, Mapping[CanonicalToken, float]],
    destination: Path,
) -> Path:
    figure, axis = pyplot.subplots(figsize=(8, 5))
    cycles = sorted(state_fractions_by_cycle)
    states = ("Dormant", "Verification Pending", "Admitted", "Expired")
    for state in states:
        axis.plot(
            cycles,
            [state_fractions_by_cycle[cycle].get(state, 0.0) for cycle in cycles],
            marker="o",
            label=state,
        )
    axis.set_xlabel("logical evidence cycle")
    axis.set_ylabel("fraction of seed instances")
    axis.legend()
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    pyplot.close(figure)
    return destination


def render_efficiency_profile(
    metric_values: Mapping[CanonicalToken, Mapping[CanonicalToken, float]],
    metric: CanonicalToken,
    destination: Path,
) -> Path:
    figure, axis = pyplot.subplots(figsize=(8, 5))
    methods = list(metric_values)
    values = [metric_values[method].get(metric, 0.0) for method in methods]
    axis.bar(methods, values)
    axis.set_ylabel(metric)
    axis.set_title(metric)
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    pyplot.close(figure)
    return destination
