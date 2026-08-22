from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from fedsira.domain.records import NonNegativeFloat, NonNegativeInt


@dataclass(frozen=True)
class MetricResult:
    value: float | None
    denominator: NonNegativeInt


@dataclass(frozen=True)
class ConfusionCounts:
    true_positive: NonNegativeInt
    false_positive: NonNegativeInt
    false_negative: NonNegativeInt
    true_negative: NonNegativeInt


class FalseSameCapabilityReason(StrEnum):
    NO_CROSS_ROOT_CAUSE_EQUIVALENCE_ASSERTION = "No Cross-Root-Cause Equivalence Assertion"


@dataclass(frozen=True)
class AdmissionDelayDecomposition:
    logical_information_arrival_cycles: NonNegativeInt
    assignment_seconds: NonNegativeFloat
    reproduce_seconds: NonNegativeFloat
    verify_seconds: NonNegativeFloat
    synthesize_seconds: NonNegativeFloat

    @property
    def post_evidence_wall_clock_seconds(self) -> NonNegativeFloat:
        return (
            self.assignment_seconds
            + self.reproduce_seconds
            + self.verify_seconds
            + self.synthesize_seconds
        )
