import itertools
from collections.abc import Callable
from typing import TypeAlias, cast

from statsmodels.stats.multitest import (
    multipletests as _multipletests,
)

from fedsira.domain.types import (
    ComparisonMargin,
    ComparisonName,
    PairedDifference,
    PValue,
    Sign,
    SignFlipSampleCount,
)

SignFlipSign: TypeAlias = Sign
SignFlipAssignment: TypeAlias = tuple[SignFlipSign, ...]
NamedPValue: TypeAlias = tuple[ComparisonName, PValue]
_multipletests_typed = cast(
    Callable[..., tuple[tuple[bool, ...], tuple[float, ...], float, float]],
    _multipletests,
)


def enumerate_sign_flip_assignments(
    sample_count: SignFlipSampleCount,
) -> tuple[SignFlipAssignment, ...]:
    return tuple(itertools.product((1, -1), repeat=sample_count))


def _signed_mean(
    signs: SignFlipAssignment,
    differences: tuple[PairedDifference, ...],
) -> PairedDifference:
    paired = zip(signs, differences, strict=True)
    return sum(sign * difference for sign, difference in paired) / len(differences)


def exact_sign_flip_two_sided_p_value(
    paired_differences: tuple[PairedDifference, ...],
) -> PValue:
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
    paired_differences: tuple[PairedDifference, ...],
    margin: ComparisonMargin,
) -> PValue:
    shifted_differences = tuple(difference + margin for difference in paired_differences)
    sample_count = len(shifted_differences)
    observed_mean = sum(shifted_differences) / sample_count
    assignments = enumerate_sign_flip_assignments(sample_count)
    extreme_count = sum(
        1 for signs in assignments if _signed_mean(signs, shifted_differences) >= observed_mean
    )
    return extreme_count / len(assignments)


def holm_adjusted_p_values(
    named_raw_p_values: tuple[NamedPValue, ...],
) -> tuple[NamedPValue, ...]:
    ordered = sorted(named_raw_p_values, key=lambda item: (item[1], item[0]))
    if not ordered:
        return ()
    _rejected, adjusted_p_values, _sidak, _bonferroni = _multipletests_typed(
        tuple(raw_p_value for _name, raw_p_value in ordered),
        method="holm",
    )
    return tuple(
        (name, float(adjusted))
        for (name, _), adjusted in zip(ordered, adjusted_p_values, strict=True)
    )
