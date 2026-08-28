import re

from fedsira.datasets.ciciot2023.schema import TARGET_LABEL, normalize_label
from fedsira.domain.records import ClassLabel

_WHITESPACE_HYPHEN_UNDERSCORE = re.compile(r"[\s\-_]+")


def _differs_only_by_case_whitespace_hyphen_or_underscore(first: str, second: str) -> bool:
    def strip(value: str) -> str:
        return _WHITESPACE_HYPHEN_UNDERSCORE.sub("", value).lower()

    return strip(first) == strip(second)


def validate_label_collisions(raw_labels: frozenset[ClassLabel]) -> None:
    normalized_to_raw: dict[ClassLabel, set[ClassLabel]] = {}
    for raw in raw_labels:
        normalized = normalize_label(raw)
        normalized_to_raw.setdefault(normalized, set()).add(raw)
    for normalized, raws in normalized_to_raw.items():
        if len(raws) <= 1:
            continue
        reference = next(iter(raws))
        for other in raws - {reference}:
            if not _differs_only_by_case_whitespace_hyphen_or_underscore(reference, other):
                raise ValueError(
                    f"raw labels {sorted(raws)} collide on normalized label {normalized!r} but "
                    "differ by more than case/whitespace/hyphen/underscore"
                )


def validate_target_label_present(normalized_labels: frozenset[ClassLabel]) -> None:
    if TARGET_LABEL not in normalized_labels:
        raise ValueError(
            f"required target label {TARGET_LABEL} was not observed after normalization"
        )
