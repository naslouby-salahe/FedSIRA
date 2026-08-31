from fedsira.protocol.claim_contract import validate_source_excluded_production_weight
from fedsira.protocol.synthesis import krum_input_excludes_source


def test_source_excluded_production_weight_is_zero() -> None:
    validate_source_excluded_production_weight(0.0)


def test_krum_input_rejects_source_row_identity() -> None:
    krum_input_excludes_source(
        candidate_row_ids=("reproducer-a", "reproducer-b"),
        source_row_id=None,
    )
