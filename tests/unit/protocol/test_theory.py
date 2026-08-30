from fractions import Fraction

import pytest
import torch

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER
from fedsira.domain.enums import TernaryOutcome
from fedsira.protocol.theory import (
    deduplicate_reports_by_proxy,
    diagnostic_at_least_two_byzantine_probability,
    first_cycle_with_minimum_eligible_evidence_holders,
    krum_committee_is_admissible,
    krum_minimum_committee_size,
    minimum_honest_positive_count,
    reproduction_update_vector,
    validate_exactly_one_source_domain,
    validate_no_safety_claim_before_tau_k,
)

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
SYNTHESIS_CONFIG = CONFIG.protocol.synthesis
VERIFICATION_CONFIG = CONFIG.protocol.verification
DIAGNOSTIC_CONFIG = CONFIG.protocol.diagnostic_random_verifier_profile
DOMAIN_A, DOMAIN_B = NBAIOT_DOMAIN_ORDER[:2]


def test_primary_experimental_population_is_exactly_nine_domains() -> None:
    assert len(NBAIOT_DOMAIN_ORDER) == 9


def test_maximum_byzantine_reproduction_rows_is_one() -> None:
    assert SYNTHESIS_CONFIG.maximum_byzantine_reproduction_rows == 1


def test_maximum_byzantine_verifiers_per_panel_is_one() -> None:
    assert VERIFICATION_CONFIG.maximum_byzantine_verifiers_per_panel == 1


def test_required_positive_reports_is_two_of_three() -> None:
    assert VERIFICATION_CONFIG.panel_size == 3
    assert VERIFICATION_CONFIG.required_positive_reports == 2


def test_tolerated_diagnostic_contamination_risk_is_0_15() -> None:
    assert DIAGNOSTIC_CONFIG.tolerated_contamination_risk == 0.15


def test_minimum_honest_positive_count_bound() -> None:
    assert minimum_honest_positive_count(2, 1) == 1
    assert minimum_honest_positive_count(0, 1) == 0


def test_primary_verifier_profile_guarantees_at_least_one_honest_positive() -> None:
    guaranteed = minimum_honest_positive_count(
        VERIFICATION_CONFIG.required_positive_reports,
        VERIFICATION_CONFIG.maximum_byzantine_verifiers_per_panel,
    )
    assert guaranteed >= 1


def test_krum_minimum_committee_size_for_f_1_is_five() -> None:
    assert krum_minimum_committee_size(1) == 5


def test_krum_admissibility_accepts_five_row_committee_for_f_1() -> None:
    assert krum_committee_is_admissible(
        SYNTHESIS_CONFIG.committee_size, SYNTHESIS_CONFIG.maximum_byzantine_reproduction_rows
    )


def test_krum_admissibility_rejects_naive_three_row_2f_plus_1_committee() -> None:
    assert not krum_committee_is_admissible(3, 1)


def test_first_cycle_with_minimum_eligible_evidence_holders() -> None:
    counts = [0, 1, 1, 2, 3]
    assert first_cycle_with_minimum_eligible_evidence_holders(counts, 2) == 3
    assert first_cycle_with_minimum_eligible_evidence_holders(counts, 10) is None


def test_validate_no_safety_claim_before_tau_k_rejects_early_claim() -> None:
    with pytest.raises(ValueError, match="before"):
        validate_no_safety_claim_before_tau_k(2, 3)
    with pytest.raises(ValueError, match="before"):
        validate_no_safety_claim_before_tau_k(0, None)
    validate_no_safety_claim_before_tau_k(3, 3)


def test_deduplicate_reports_by_proxy_keeps_first_report_per_domain() -> None:
    reports = (
        (DOMAIN_A, TernaryOutcome.POSITIVE),
        (DOMAIN_A, TernaryOutcome.NEGATIVE),
        (DOMAIN_B, TernaryOutcome.ABSTAIN),
    )
    deduplicated = deduplicate_reports_by_proxy(reports)
    assert deduplicated == (
        (DOMAIN_A, TernaryOutcome.POSITIVE),
        (DOMAIN_B, TernaryOutcome.ABSTAIN),
    )


def test_validate_exactly_one_source_domain() -> None:
    validate_exactly_one_source_domain([DOMAIN_A])
    with pytest.raises(ValueError, match="exactly one"):
        validate_exactly_one_source_domain([])
    with pytest.raises(ValueError, match="exactly one"):
        validate_exactly_one_source_domain([DOMAIN_A, DOMAIN_B])


def test_diagnostic_at_least_two_byzantine_probability_matches_exact_fraction() -> None:
    probability = diagnostic_at_least_two_byzantine_probability(7, 2, 3)
    assert abs(probability - float(Fraction(1, 7))) < 1e-12


def test_diagnostic_probability_is_zero_for_zero_or_one_byzantine_domains() -> None:
    assert diagnostic_at_least_two_byzantine_probability(7, 0, 3) == 0.0
    assert diagnostic_at_least_two_byzantine_probability(7, 1, 3) == 0.0


def test_diagnostic_probability_uses_the_configured_profile_shape() -> None:
    probability = diagnostic_at_least_two_byzantine_probability(
        7, DIAGNOSTIC_CONFIG.byzantine_domain_count, DIAGNOSTIC_CONFIG.panel_size
    )
    assert probability <= DIAGNOSTIC_CONFIG.tolerated_contamination_risk


def test_reproduction_update_vector_is_the_delta_from_anchor() -> None:
    anchor = torch.tensor([1.0, 2.0, 3.0])
    reproduced = torch.tensor([1.5, 2.0, 4.0])
    delta = reproduction_update_vector(anchor, reproduced)
    assert torch.allclose(delta, torch.tensor([0.5, 0.0, 1.0]))
