from fedsira.analysis.comparisons import (
    ComparisonTestKind,
    apply_holm_adjustment,
    build_comparison_registry,
    comparison_canonical_name,
    evaluate_comparison,
)
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.experiments.registry import ClaimFamily

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)

REGISTRY = build_comparison_registry(
    CONFIG.metrics_and_statistics.materiality,
    CONFIG.claim_support_thresholds.capability_granularity_boundary.false_same_capability_certification_rate_minimum,
)


def test_registry_has_all_ten_claim_families() -> None:
    families = {definition.family for definition in REGISTRY}
    assert families == set(ClaimFamily)


def test_registry_has_unique_canonical_names() -> None:
    names = [definition.canonical_name for definition in REGISTRY]
    assert len(names) == len(set(names))


def test_canonical_name_follows_section_18_9_pattern() -> None:
    name = comparison_canonical_name(
        ClaimFamily.PLURALITY_NECESSITY,
        "Single-Reproduction Necessity",
        "One Byzantine Source-Copy Reproducer",
        "Full Plurality Path",
        "One Independent Retrain",
        "malicious-admission",
        ComparisonTestKind.SUPERIORITY,
    )
    assert name == (
        "plurality necessity|Single-Reproduction Necessity|"
        "One Byzantine Source-Copy Reproducer|"
        "Full Plurality Path__vs__One Independent Retrain|"
        "malicious-admission|superiority"
    )


def test_evaluate_comparison_zero_pairs_is_undefined() -> None:
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    definition = REGISTRY[0]
    result = evaluate_comparison(
        definition,
        [],
        config.metrics_and_statistics.multiplicity,
        config.metrics_and_statistics.bootstrap,
        config.seeds_and_determinism.analysis_seed,
    )
    assert result.comparison_state == "Undefined"
    assert result.mean_paired_difference is None
    assert result.raw_p_value is None


def test_evaluate_comparison_strong_consistent_effect() -> None:
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    definition = REGISTRY[0]
    result = evaluate_comparison(
        definition,
        [1.0] * 10,
        config.metrics_and_statistics.multiplicity,
        config.metrics_and_statistics.bootstrap,
        config.seeds_and_determinism.analysis_seed,
    )
    assert result.complete_seed_count == 10
    assert result.mean_paired_difference == 1.0
    assert result.raw_p_value is not None
    assert result.raw_p_value < 0.05


def test_holm_adjustment_marks_passed_and_failed() -> None:
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    passing = evaluate_comparison(
        REGISTRY[0],
        [1.0] * 10,
        config.metrics_and_statistics.multiplicity,
        config.metrics_and_statistics.bootstrap,
        config.seeds_and_determinism.analysis_seed,
    )
    failing = evaluate_comparison(
        REGISTRY[1],
        [0.0] * 10,
        config.metrics_and_statistics.multiplicity,
        config.metrics_and_statistics.bootstrap,
        config.seeds_and_determinism.analysis_seed,
    )
    from fedsira.analysis.comparisons import ComparisonFamilyResult

    family_result = ComparisonFamilyResult(
        ClaimFamily.PROPOSAL_SCREEN_NECESSITY, (passing, failing)
    )
    adjusted = apply_holm_adjustment(family_result, config.metrics_and_statistics.multiplicity)
    by_name = {result.definition.canonical_name: result for result in adjusted.comparisons}
    assert by_name[passing.definition.canonical_name].comparison_state == "Passed"
    assert by_name[failing.definition.canonical_name].comparison_state == "Failed"
