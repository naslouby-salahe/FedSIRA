import torch

from fedsira.boundaries.epistemic_failure import (
    apply_attacker_induced_common_context,
    apply_shared_spurious_feature,
    diagnostic_marker_metric_or_insufficient,
    match_diagnostic_benign_report_test_rows,
    relabel_shared_label_error_rows,
    select_shared_label_error_rows,
    select_spurious_feature_rows,
)
from fedsira.datasets.nbaiot.schema import NBaiotClass
from fedsira.domain.enums import EvaluationInsufficiencyReason


def test_select_shared_label_error_rows_uses_configured_fraction() -> None:
    rows = [f"row-{i}" for i in range(20)]
    selected = select_shared_label_error_rows(rows, 0.05, 42)
    assert selected is not None
    assert len(selected) == 1


def test_relabel_shared_label_error_rows_targets_only_selected() -> None:
    labels = {"a": NBaiotClass.BENIGN, "b": NBaiotClass.BENIGN}
    relabeled = relabel_shared_label_error_rows(labels, ["a"])
    assert relabeled["a"] is NBaiotClass.GAFGYT_COMBO
    assert relabeled["b"] is NBaiotClass.BENIGN
    assert labels["a"] is NBaiotClass.BENIGN


def test_apply_shared_spurious_feature_sets_only_the_given_index() -> None:
    features = torch.zeros(2, 4)
    result = apply_shared_spurious_feature(features, 0, 6.0)
    assert torch.equal(result, torch.tensor([[6.0, 0.0, 0.0, 0.0]] * 2))


def test_apply_attacker_induced_common_context_sets_all_four_indices() -> None:
    features = torch.zeros(2, 4)
    result = apply_attacker_induced_common_context(features, [0, 1, 2, 3], 6.0)
    assert torch.equal(result, torch.full((2, 4), 6.0))


def test_match_diagnostic_benign_report_test_rows_matches_by_nearest_loss() -> None:
    targets = [("t1", 1.0)]
    benign_pool = [("b1", 0.9)] + [(f"b{i}", float(i)) for i in range(2, 11)]
    matched = match_diagnostic_benign_report_test_rows(targets, benign_pool)
    assert matched is not None
    assert matched[0] == ("t1", "b1")


def test_diagnostic_marker_metric_is_insufficient_when_no_match() -> None:
    result, reason = diagnostic_marker_metric_or_insufficient(None, 0.5)
    assert result.value is None
    assert reason is EvaluationInsufficiencyReason.INSUFFICIENT_MATCHED_BENIGN_REPORT_TEST_CONTROLS


def test_diagnostic_marker_metric_returns_value_when_matched() -> None:
    matched = (("t1", "b1"), ("t2", "b2"))
    result, reason = diagnostic_marker_metric_or_insufficient(matched, 0.75)
    assert result.value == 0.75
    assert result.denominator == 2
    assert reason is None


def test_select_spurious_feature_rows_evidence_insufficient_at_zero_count() -> None:
    rows = [f"row-{i}" for i in range(3)]
    assert select_spurious_feature_rows(rows, 0.25, 42) is None
