from fedsira.evaluation.statistics import exact_sign_flip_two_sided_p_value

SIGN_FLIP_CHECK_SAMPLE_COUNT = 10
SIGN_FLIP_CHECK_EXPECTED_P_VALUE = 0.001953125


def test_sign_flip_fixture_matches_independent_expected_value() -> None:
    observed = exact_sign_flip_two_sided_p_value((1.0,) * SIGN_FLIP_CHECK_SAMPLE_COUNT)
    assert observed == SIGN_FLIP_CHECK_EXPECTED_P_VALUE
