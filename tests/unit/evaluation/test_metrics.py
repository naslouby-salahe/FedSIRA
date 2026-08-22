from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.evaluation.metrics import (
    accuracy,
    attack_success_rate_within_domain,
    auprc_one_vs_rest,
    auroc_one_vs_rest,
    balanced_accuracy,
    benign_false_alarm_rate,
    benign_false_alarm_rate_increase,
    clean_proposal_oracle_label,
    compute_confusion_counts,
    compute_confusion_counts_by_class,
    dormant_claim_rate,
    f1_for_class,
    false_launch_rate,
    false_negative_rate_for_class,
    false_positive_rate_for_class,
    false_same_capability_certification_rate,
    is_false_same_capability_certification,
    legitimate_admission_rate,
    macro_f1,
    malicious_admission_rate,
    precision_for_class,
    recall_for_class,
    reproduction_abstention_rate,
    reproduction_attempt_count,
    supported_macro_f1_harm,
    target_capability_gain,
    target_f1,
    true_negative_rate_for_class,
    verifier_abstention_rate,
    weighted_f1,
)
from fedsira.evaluation.records import FalseSameCapabilityReason, MetricResult, ProposalOracleLabel

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)


def test_confusion_counts_partition_all_examples() -> None:
    true_labels = ["A", "A", "B", "B", "A"]
    predicted_labels = ["A", "B", "B", "A", "A"]
    counts = compute_confusion_counts(true_labels, predicted_labels, "A")
    assert counts.true_positive == 2
    assert counts.false_positive == 1
    assert counts.false_negative == 1
    assert counts.true_negative == 1


def test_precision_recall_f1_are_na_on_zero_denominator() -> None:
    counts_by_class = compute_confusion_counts_by_class(["B"], ["B"], ["A"])
    counts = counts_by_class["A"]
    assert precision_for_class(counts).value is None
    assert recall_for_class(counts).value is None
    assert f1_for_class(counts).value is None


def test_precision_recall_f1_numeric_values() -> None:
    true_labels = ["A", "A", "B", "B"]
    predicted_labels = ["A", "B", "B", "B"]
    counts = compute_confusion_counts(true_labels, predicted_labels, "A")
    assert precision_for_class(counts).value == 1.0
    assert recall_for_class(counts).value == 0.5
    assert f1_for_class(counts).value == 2 / 3


def test_false_positive_negative_true_negative_rate() -> None:
    true_labels = ["A", "A", "B", "B"]
    predicted_labels = ["A", "B", "A", "B"]
    counts = compute_confusion_counts(true_labels, predicted_labels, "A")
    assert false_positive_rate_for_class(counts).value == 0.5
    assert false_negative_rate_for_class(counts).value == 0.5
    assert true_negative_rate_for_class(counts).value == 0.5


def test_accuracy_zero_samples_is_na() -> None:
    assert accuracy({}, 0).value is None


def test_accuracy_matches_expected_fraction() -> None:
    true_labels = ["A", "A", "B", "B"]
    predicted_labels = ["A", "B", "B", "B"]
    counts_by_class = compute_confusion_counts_by_class(true_labels, predicted_labels, ["A", "B"])
    assert accuracy(counts_by_class, 4).value == 0.75


def test_macro_f1_excludes_undefined_classes() -> None:
    true_labels = ["A", "A"]
    predicted_labels = ["A", "A"]
    counts_by_class = compute_confusion_counts_by_class(true_labels, predicted_labels, ["A", "B"])
    f1_by_class = {token: f1_for_class(counts) for token, counts in counts_by_class.items()}
    result = macro_f1(f1_by_class)
    assert result.value == 1.0
    assert result.denominator == 1


def test_weighted_f1_uses_support_weighting() -> None:
    true_labels = ["A", "A", "A", "B"]
    predicted_labels = ["A", "A", "B", "B"]
    counts_by_class = compute_confusion_counts_by_class(true_labels, predicted_labels, ["A", "B"])
    f1_by_class = {token: f1_for_class(counts) for token, counts in counts_by_class.items()}
    support_by_class = {"A": 3, "B": 1}
    result = weighted_f1(f1_by_class, support_by_class)
    assert result.value is not None
    assert result.denominator == 4


def test_balanced_accuracy_is_unweighted_recall_mean() -> None:
    true_labels = ["A", "A", "B"]
    predicted_labels = ["A", "B", "B"]
    counts_by_class = compute_confusion_counts_by_class(true_labels, predicted_labels, ["A", "B"])
    recall_by_class = {token: recall_for_class(counts) for token, counts in counts_by_class.items()}
    result = balanced_accuracy(recall_by_class)
    assert result.value == 0.75


def test_target_f1_selects_target_class() -> None:
    true_labels = ["GAFGYT_COMBO", "BENIGN"]
    predicted_labels = ["GAFGYT_COMBO", "BENIGN"]
    counts_by_class = compute_confusion_counts_by_class(
        true_labels, predicted_labels, ["GAFGYT_COMBO", "BENIGN"]
    )
    result = target_f1(counts_by_class, "GAFGYT_COMBO")
    assert result.value == 1.0


def test_target_capability_gain_is_na_when_either_side_undefined() -> None:
    assert target_capability_gain(MetricResult(None, 0), MetricResult(0.5, 10)).value is None
    result = target_capability_gain(MetricResult(0.8, 10), MetricResult(0.6, 10))
    assert result.value is not None
    assert abs(result.value - 0.2) < 1e-9


def test_supported_macro_f1_harm_direction() -> None:
    result = supported_macro_f1_harm(MetricResult(0.9, 10), MetricResult(0.85, 10))
    assert result.value is not None
    assert abs(result.value - 0.05) < 1e-9


def test_benign_false_alarm_rate_definition() -> None:
    true_labels = ["BENIGN", "BENIGN", "BENIGN", "A"]
    predicted_labels = ["BENIGN", "A", "A", "A"]
    result = benign_false_alarm_rate(true_labels, predicted_labels, "BENIGN")
    assert result.value == 2 / 3
    assert result.denominator == 3


def test_benign_false_alarm_rate_na_when_no_benign_examples() -> None:
    result = benign_false_alarm_rate(["A"], ["A"], "BENIGN")
    assert result.value is None


def test_benign_false_alarm_rate_increase() -> None:
    result = benign_false_alarm_rate_increase(MetricResult(0.05, 100), MetricResult(0.02, 100))
    assert result.value is not None
    assert abs(result.value - 0.03) < 1e-9


def test_attack_success_rate_within_domain_na_without_carrier() -> None:
    result = attack_success_rate_within_domain([], [], [], "GAFGYT_UDP", "BENIGN")
    assert result.value is None


def test_attack_success_rate_within_domain_counts_evasion() -> None:
    true_labels = ["GAFGYT_UDP", "GAFGYT_UDP", "GAFGYT_UDP"]
    predicted_labels = ["BENIGN", "GAFGYT_UDP", "BENIGN"]
    triggered_mask = [True, True, True]
    result = attack_success_rate_within_domain(
        true_labels, predicted_labels, triggered_mask, "GAFGYT_UDP", "BENIGN"
    )
    assert result.value == 2 / 3


def test_malicious_admission_rate_and_legitimate_admission_rate() -> None:
    assert malicious_admission_rate([]).value is None
    assert malicious_admission_rate([True, False, False, False]).value == 0.25
    assert legitimate_admission_rate([True, True, False]).value == 2 / 3


def test_verifier_and_reproduction_abstention_rates_and_dormant_claim_rate() -> None:
    assert verifier_abstention_rate(0, 0).value is None
    assert verifier_abstention_rate(1, 4).value == 0.25
    assert reproduction_abstention_rate(2, 5).value == 0.4
    assert dormant_claim_rate(3, 10).value == 0.3


def test_auroc_one_vs_rest_perfect_separation() -> None:
    true_binary = [False, False, True, True]
    scores = [0.1, 0.2, 0.8, 0.9]
    result = auroc_one_vs_rest(true_binary, scores)
    assert result.value == 1.0


def test_auroc_one_vs_rest_na_without_both_classes() -> None:
    assert auroc_one_vs_rest([True, True], [0.1, 0.2]).value is None


def test_auprc_one_vs_rest_perfect_separation_is_one() -> None:
    true_binary = [False, False, True, True]
    scores = [0.1, 0.2, 0.8, 0.9]
    result = auprc_one_vs_rest(true_binary, scores)
    assert result.value is not None
    assert abs(result.value - 1.0) < 1e-9


def test_auprc_one_vs_rest_na_without_positives() -> None:
    assert auprc_one_vs_rest([False, False], [0.1, 0.2]).value is None


def test_false_same_capability_certification_rate_scoped_contract_returns_reason() -> None:
    result, reason = false_same_capability_certification_rate(0, 5, is_scoped_contract=True)
    assert result.value is None
    assert reason == FalseSameCapabilityReason.NO_CROSS_ROOT_CAUSE_EQUIVALENCE_ASSERTION


def test_false_same_capability_certification_rate_zero_certified_rows_is_na() -> None:
    result, reason = false_same_capability_certification_rate(0, 0, is_scoped_contract=False)
    assert result.value is None
    assert reason is None


def test_false_same_capability_certification_rate_numeric() -> None:
    result, reason = false_same_capability_certification_rate(2, 8, is_scoped_contract=False)
    assert result.value == 0.25
    assert reason is None


def test_clean_proposal_oracle_label_na_below_defined_domain_threshold() -> None:
    capability_claim_config = CONFIG.capability_claim
    label = clean_proposal_oracle_label(
        MetricResult(0.9, 10),
        MetricResult(0.3, 10),
        MetricResult(0.0, 10),
        MetricResult(0.0, 10),
        defined_domain_count=5,
        expected_domain_count=8,
        generic_defined_domain_fraction_minimum=0.8,
        capability_claim_config=capability_claim_config,
    )
    assert label == ProposalOracleLabel.NA


def test_clean_proposal_oracle_label_valid_when_all_thresholds_pass() -> None:
    capability_claim_config = CONFIG.capability_claim
    label = clean_proposal_oracle_label(
        MetricResult(0.85, 10),
        MetricResult(0.25, 10),
        MetricResult(0.01, 10),
        MetricResult(0.005, 10),
        defined_domain_count=7,
        expected_domain_count=8,
        generic_defined_domain_fraction_minimum=0.8,
        capability_claim_config=capability_claim_config,
    )
    assert label == ProposalOracleLabel.ORACLE_VALID


def test_clean_proposal_oracle_label_invalid_when_a_threshold_fails() -> None:
    capability_claim_config = CONFIG.capability_claim
    label = clean_proposal_oracle_label(
        MetricResult(0.5, 10),
        MetricResult(0.25, 10),
        MetricResult(0.01, 10),
        MetricResult(0.005, 10),
        defined_domain_count=7,
        expected_domain_count=8,
        generic_defined_domain_fraction_minimum=0.8,
        capability_claim_config=capability_claim_config,
    )
    assert label == ProposalOracleLabel.ORACLE_INVALID


def test_false_launch_rate() -> None:
    assert false_launch_rate(0, 0).value is None
    result = false_launch_rate(1, 4)
    assert result.value == 0.25


def test_reproduction_attempt_count_excludes_evidence_inadequate_domains() -> None:
    started = frozenset({"A", "B", "C"})
    inadequate = frozenset({"B"})
    assert reproduction_attempt_count(started, inadequate) == 2


def test_is_false_same_capability_certification_is_exclusive_or() -> None:
    assert is_false_same_capability_certification(True, False)
    assert is_false_same_capability_certification(False, True)
    assert not is_false_same_capability_certification(True, True)
    assert not is_false_same_capability_certification(False, False)
