from fedsira.protocol.theory import krum_committee_is_admissible
from fedsira.runtime.state import current_application_context


def test_primary_krum_committee_is_admissible_for_one_byzantine_row() -> None:
    synthesis = current_application_context().scientific_config.protocol.synthesis
    assert krum_committee_is_admissible(
        synthesis.committee_size,
        synthesis.maximum_byzantine_reproduction_rows,
    )
