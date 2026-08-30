import pytest

from fedsira.datasets.nbaiot.schema import NBaiotClass
from fedsira.evaluation.metrics import report_metric_set
from fedsira.evaluation.validation import (
    EvaluationValidationError,
    validate_metric_class_membership,
)


def test_metric_class_membership_accepts_valid_configuration() -> None:
    validate_metric_class_membership(
        (NBaiotClass.BENIGN.value, NBaiotClass.GAFGYT_COMBO.value, NBaiotClass.GAFGYT_UDP.value),
        NBaiotClass.GAFGYT_COMBO.value,
        NBaiotClass.BENIGN.value,
        (NBaiotClass.BENIGN.value, NBaiotClass.GAFGYT_UDP.value),
    )


def test_metric_class_membership_rejects_target_outside_vocabulary() -> None:
    with pytest.raises(EvaluationValidationError):
        validate_metric_class_membership(
            (NBaiotClass.BENIGN.value,),
            NBaiotClass.GAFGYT_COMBO.value,
            NBaiotClass.BENIGN.value,
            (),
        )


def test_metric_class_membership_rejects_benign_outside_vocabulary() -> None:
    with pytest.raises(EvaluationValidationError):
        validate_metric_class_membership(
            (NBaiotClass.GAFGYT_COMBO.value,),
            NBaiotClass.GAFGYT_COMBO.value,
            NBaiotClass.BENIGN.value,
            (),
        )


def test_metric_class_membership_rejects_supported_outside_vocabulary() -> None:
    with pytest.raises(EvaluationValidationError):
        validate_metric_class_membership(
            (NBaiotClass.BENIGN.value, NBaiotClass.GAFGYT_COMBO.value),
            NBaiotClass.GAFGYT_COMBO.value,
            NBaiotClass.BENIGN.value,
            (NBaiotClass.MIRAI_SCAN.value,),
        )


def test_report_metric_set_rejects_inconsistent_target() -> None:
    with pytest.raises(EvaluationValidationError):
        report_metric_set(
            true_labels=(),
            predicted_labels=(),
            class_tokens=(NBaiotClass.BENIGN.value,),
            target_class_token=NBaiotClass.GAFGYT_COMBO.value,
            benign_class_token=NBaiotClass.BENIGN.value,
            supported_class_tokens=(),
        )


def test_report_metric_set_accepts_consistent_tokens() -> None:
    result = report_metric_set(
        true_labels=(),
        predicted_labels=(),
        class_tokens=(NBaiotClass.BENIGN.value, NBaiotClass.GAFGYT_COMBO.value),
        target_class_token=NBaiotClass.GAFGYT_COMBO.value,
        benign_class_token=NBaiotClass.BENIGN.value,
        supported_class_tokens=(NBaiotClass.BENIGN.value,),
    )
    assert "target-f1" in dict(result)
