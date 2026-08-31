from fedsira.analysis.claims import CLAIM_DEFINITIONS, FinalClaimState, derive_claim_states
from fedsira.runtime.state import current_application_context


def test_claim_states_are_not_tested_without_evidence() -> None:
    config = current_application_context().scientific_config
    states = derive_claim_states(
        (),
        config.claim_support_thresholds,
        config.metrics_and_statistics.technical_completion.minimum_complete_pairs_for_claim_support,
        config.metrics_and_statistics.multiplicity.family_wise_alpha,
    )
    assert len(states) == len(CLAIM_DEFINITIONS)
    assert all(state.state is FinalClaimState.NOT_TESTED for state in states)
