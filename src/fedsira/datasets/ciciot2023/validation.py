import re

from fedsira.datasets.ciciot2023.schema import TARGET_LABEL, normalize_label
from fedsira.domain.types import BooleanValue, ClassLabel

_WHITESPACE_HYPHEN_UNDERSCORE = re.compile(r"[\s\-_]+")


def _comparison_token(value: ClassLabel) -> ClassLabel:
    return _WHITESPACE_HYPHEN_UNDERSCORE.sub("", value).lower()


def _differs_only_by_case_whitespace_hyphen_or_underscore(
    first: ClassLabel,
    second: ClassLabel,
) -> BooleanValue:
    return _comparison_token(first) == _comparison_token(second)


def validate_label_collisions(raw_labels: frozenset[ClassLabel]) -> None:
    ordered = tuple(sorted(raw_labels))
    for first_index, first in enumerate(ordered):
        for second in ordered[first_index + 1 :]:
            normalized = normalize_label(first)
            if normalize_label(second) != normalized:
                continue
            if not _differs_only_by_case_whitespace_hyphen_or_underscore(first, second):
                raise ValueError(
                    f"raw labels {first!r} and {second!r} collide on normalized label "
                    f"{normalized!r} but differ by more than case/whitespace/hyphen/underscore"
                )


def validate_target_label_present(normalized_labels: frozenset[ClassLabel]) -> None:
    if TARGET_LABEL not in normalized_labels:
        raise ValueError(
            f"required target label {TARGET_LABEL} was not observed after normalization"
        )
