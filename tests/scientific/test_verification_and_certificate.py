from fedsira.domain.enums import TernaryOutcome
from fedsira.protocol.verification import reproduction_row_is_certified
from fedsira.runtime.state import current_application_context


def test_primary_panel_requires_two_of_three_positive_reports() -> None:
    verification = current_application_context().scientific_config.protocol.verification
    assert reproduction_row_is_certified(
        (TernaryOutcome.POSITIVE, TernaryOutcome.POSITIVE, TernaryOutcome.NEGATIVE),
        verification.panel_size,
        verification.required_positive_reports,
    )
    assert not reproduction_row_is_certified(
        (TernaryOutcome.POSITIVE, TernaryOutcome.NEGATIVE, TernaryOutcome.ABSTAIN),
        verification.panel_size,
        verification.required_positive_reports,
    )
