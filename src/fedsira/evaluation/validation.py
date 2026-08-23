from __future__ import annotations

from collections.abc import Sequence

from fedsira.domain.records import CanonicalToken


class EvaluationValidationError(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def validate_metric_class_membership(
    class_tokens: Sequence[CanonicalToken],
    target_class_token: CanonicalToken,
    benign_class_token: CanonicalToken,
    supported_class_tokens: Sequence[CanonicalToken],
) -> None:
    vocabulary = frozenset(class_tokens)
    if target_class_token not in vocabulary:
        raise EvaluationValidationError(
            f"target class {target_class_token!r} is outside the metric class vocabulary"
        )
    if benign_class_token not in vocabulary:
        raise EvaluationValidationError(
            f"benign class {benign_class_token!r} is outside the metric class vocabulary"
        )
    for supported in supported_class_tokens:
        if supported not in vocabulary:
            raise EvaluationValidationError(
                f"supported class {supported!r} is outside the metric class vocabulary"
            )
