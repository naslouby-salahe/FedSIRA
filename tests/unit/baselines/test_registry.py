import pytest

from fedsira.baselines.references import (
    fedavg_reference_post_reference_local_epochs,
    post_reference_retrain_maximum_local_epochs,
    standard_fl_anchor_rounds,
)
from fedsira.baselines.registry import (
    ORDINARY_POST_REFERENCE_DATA_ACCESS,
    domain_target_view,
    domain_without_target_view_may_participate,
    first_eligible_non_source_reproducer,
    review_style_baseline_outcome,
    single_fresh_verifier_domain,
    single_fresh_verifier_outcome,
    validate_role_not_used_for_tuning,
)
from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER
from fedsira.domain.enums import ClaimState, TernaryOutcome

SOURCE = NBAIOT_DOMAIN_ORDER[0]
NON_SOURCE = NBAIOT_DOMAIN_ORDER[1]


def test_standard_fl_baseline_budget_reads_yaml() -> None:
    from fedsira.runtime.state import current_application_context

    model = current_application_context().scientific_config.model
    assert standard_fl_anchor_rounds() == model.anchor_fedavg.rounds
    assert (
        fedavg_reference_post_reference_local_epochs() == model.anchor_fedavg.local_epochs_per_round
    )
    assert post_reference_retrain_maximum_local_epochs() == model.post_reference.local_epochs


def test_domain_target_view_uses_source_proposal_for_source_and_reproduction_otherwise() -> None:
    assert (
        domain_target_view(SOURCE, SOURCE, ORDINARY_POST_REFERENCE_DATA_ACCESS)
        is Role.SOURCE_PROPOSAL
    )
    assert (
        domain_target_view(NON_SOURCE, SOURCE, ORDINARY_POST_REFERENCE_DATA_ACCESS)
        is Role.REPRODUCTION
    )


def test_validate_role_not_used_for_tuning_rejects_report_test_and_final_gate() -> None:
    validate_role_not_used_for_tuning(Role.ANCHOR_VALIDATION)
    with pytest.raises(ValueError):
        validate_role_not_used_for_tuning(Role.REPORT_TEST)
    with pytest.raises(ValueError):
        validate_role_not_used_for_tuning(Role.FINAL_GATE)


def test_domain_without_target_view_may_participate_follows_contract_flag() -> None:
    assert domain_without_target_view_may_participate(True) is True
    assert domain_without_target_view_may_participate(False) is False


def test_first_eligible_non_source_reproducer_takes_first_in_order() -> None:
    order = NBAIOT_DOMAIN_ORDER
    eligible = frozenset(order[1:4])
    assert first_eligible_non_source_reproducer(order, eligible) == order[1]


def test_first_eligible_non_source_reproducer_none_when_no_eligible_domain() -> None:
    assert first_eligible_non_source_reproducer(NBAIOT_DOMAIN_ORDER, frozenset()) is None


def test_single_fresh_verifier_domain_excludes_source_and_reproducer() -> None:
    order = NBAIOT_DOMAIN_ORDER
    reproducer = order[1]
    eligible = frozenset(order)
    verifier = single_fresh_verifier_domain(order, frozenset({SOURCE, reproducer}), eligible)
    assert verifier is not None
    assert verifier not in {SOURCE, reproducer}
    assert verifier == order[2]


def test_single_fresh_verifier_outcome_dormant_when_no_verifier() -> None:
    assert single_fresh_verifier_outcome(None, None) is ClaimState.DORMANT


def test_single_fresh_verifier_outcome_admitted_only_on_positive_vote() -> None:
    assert single_fresh_verifier_outcome(NON_SOURCE, TernaryOutcome.POSITIVE) is ClaimState.ADMITTED
    assert (
        single_fresh_verifier_outcome(NON_SOURCE, TernaryOutcome.NEGATIVE)
        is ClaimState.REJECTED_CLAIM
    )
    assert (
        single_fresh_verifier_outcome(NON_SOURCE, TernaryOutcome.ABSTAIN)
        is ClaimState.REJECTED_CLAIM
    )


def test_review_style_baseline_outcome_dormant_below_panel_size() -> None:
    assert review_style_baseline_outcome(2, 2, 3, 2) is ClaimState.DORMANT


def test_review_style_baseline_outcome_admitted_at_required_positives() -> None:
    assert review_style_baseline_outcome(3, 2, 3, 2) is ClaimState.ADMITTED


def test_review_style_baseline_outcome_rejected_below_required_positives() -> None:
    assert review_style_baseline_outcome(3, 1, 3, 2) is ClaimState.REJECTED_CLAIM
