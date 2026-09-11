from collections.abc import Callable, Sequence
from typing import cast

import numpy as np
from sklearn.metrics import (
    accuracy_score as _accuracy_score,
)
from sklearn.metrics import (
    balanced_accuracy_score as _balanced_accuracy_score,
)
from sklearn.metrics import (
    f1_score as _f1_score,
)

from fedsira.domain.models import ConfusionCounts, MetricResult
from fedsira.domain.types import DatasetClassToken

_accuracy_score_typed = cast(Callable[..., float], _accuracy_score)
_balanced_accuracy_score_typed = cast(Callable[..., float], _balanced_accuracy_score)
_f1_score_typed = cast(Callable[..., float], _f1_score)


def standard_classification_metrics(
    true_labels: Sequence[DatasetClassToken],
    predicted_labels: Sequence[DatasetClassToken],
    class_tokens: Sequence[DatasetClassToken],
) -> tuple[MetricResult, MetricResult, MetricResult, MetricResult]:
    if not true_labels:
        undefined = MetricResult(value=None, denominator=0)
        return undefined, undefined, undefined, undefined
    labels = tuple(class_tokens)
    counts = tuple(
        ConfusionCounts(
            true_positive=sum(
                true == token and predicted == token
                for true, predicted in zip(true_labels, predicted_labels, strict=True)
            ),
            false_positive=sum(
                true != token and predicted == token
                for true, predicted in zip(true_labels, predicted_labels, strict=True)
            ),
            false_negative=sum(
                true == token and predicted != token
                for true, predicted in zip(true_labels, predicted_labels, strict=True)
            ),
            true_negative=sum(
                true != token and predicted != token
                for true, predicted in zip(true_labels, predicted_labels, strict=True)
            ),
        )
        for token in labels
    )
    f1_denominator = sum(
        item.true_positive + item.false_positive + item.false_negative > 0 for item in counts
    )
    recall_denominator = sum(item.true_positive + item.false_negative > 0 for item in counts)
    macro = (
        None
        if f1_denominator == 0
        else _f1_score_typed(
            true_labels, predicted_labels, labels=labels, average="macro", zero_division=np.nan
        )
    )
    weighted = _f1_score_typed(
        true_labels, predicted_labels, labels=labels, average="weighted", zero_division=np.nan
    )
    balanced = (
        None
        if recall_denominator == 0
        else _balanced_accuracy_score_typed(true_labels, predicted_labels)
    )
    return (
        MetricResult(
            value=_accuracy_score_typed(true_labels, predicted_labels), denominator=len(true_labels)
        ),
        MetricResult(value=macro, denominator=f1_denominator),
        MetricResult(value=weighted, denominator=len(true_labels)),
        MetricResult(value=balanced, denominator=recall_denominator),
    )
