import itertools
from collections.abc import Sequence

from fedsira.domain.records import CanonicalToken, NonNegativeInt, PositiveFloat, Probability


def enumerate_sign_flip_assignments(sample_count: NonNegativeInt) -> tuple[tuple[float, ...], ...]:
    return tuple(itertools.product((1.0, -1.0), repeat=sample_count))


def _signed_mean(signs: Sequence[float], differences: Sequence[float]) -> float:
    paired = zip(signs, differences, strict=True)
    return sum(sign * difference for sign, difference in paired) / len(differences)


def exact_sign_flip_two_sided_p_value(paired_differences: Sequence[float]) -> Probability:
    sample_count = len(paired_differences)
    observed_absolute_mean = abs(sum(paired_differences) / sample_count)
    assignments = enumerate_sign_flip_assignments(sample_count)
    extreme_count = sum(
        1
        for signs in assignments
        if abs(_signed_mean(signs, paired_differences)) >= observed_absolute_mean
    )
    return extreme_count / len(assignments)


def exact_sign_flip_non_inferiority_p_value(
    paired_differences: Sequence[float], margin: PositiveFloat
) -> Probability:
    shifted_differences = [difference + margin for difference in paired_differences]
    sample_count = len(shifted_differences)
    observed_mean = sum(shifted_differences) / sample_count
    assignments = enumerate_sign_flip_assignments(sample_count)
    extreme_count = sum(
        1 for signs in assignments if _signed_mean(signs, shifted_differences) >= observed_mean
    )
    return extreme_count / len(assignments)


def holm_adjusted_p_values(
    named_raw_p_values: Sequence[tuple[CanonicalToken, Probability]],
) -> tuple[tuple[CanonicalToken, Probability], ...]:
    ordered = sorted(named_raw_p_values, key=lambda item: (item[1], item[0]))
    comparison_count = len(ordered)
    adjusted_p_values: list[Probability] = []
    running_maximum = 0.0
    for rank, (_, raw_p_value) in enumerate(ordered):
        candidate = min((comparison_count - rank) * raw_p_value, 1.0)
        running_maximum = max(running_maximum, candidate)
        adjusted_p_values.append(running_maximum)
    paired = zip(ordered, adjusted_p_values, strict=True)
    return tuple((name, adjusted_p_value) for (name, _), adjusted_p_value in paired)
