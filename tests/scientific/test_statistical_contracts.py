from fedsira.config.loading import load_test_fixture_config
from fedsira.evaluation.statistics import exact_sign_flip_two_sided_p_value


def test_sign_flip_fixture_matches_authoritative_test_configuration() -> None:
    fixture = load_test_fixture_config()
    observed = exact_sign_flip_two_sided_p_value((1.0,) * fixture.sign_flip_sample_count)
    assert observed == fixture.sign_flip_expected_p_value
