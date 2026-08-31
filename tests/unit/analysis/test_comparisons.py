from fedsira.analysis.comparisons import (
    ComparisonFamilyResult,
    ComparisonMetric,
    ComparisonOrientation,
    ComparisonState,
    ComparisonTestKind,
    apply_holm_adjustment,
    build_comparison_name,
    build_comparison_registry,
    evaluate_comparison,
)
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.experiments.registry import (
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
    AblationVariant,
    ClaimFamily,
    PrimaryScenario,
    ReproducerCondition,
)

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)


def test_registry_has_all_ten_claim_families() -> None:
    families = frozenset(definition.family for definition in build_comparison_registry())
    assert families == frozenset(ClaimFamily)


def test_registry_has_unique_comparison_names() -> None:
    names = tuple(definition.comparison_name for definition in build_comparison_registry())
    assert len(names) == len(frozenset(names))


def test_comparison_name_follows_section_18_9_pattern() -> None:
    name = build_comparison_name(
        ClaimFamily.PLURALITY_NECESSITY,
        "Single-Reproduction Necessity",
        "One Byzantine Source-Copy Reproducer",
        "Full Plurality Path",
        "One Independent Retrain",
        ComparisonMetric.MALICIOUS_ADMISSION,
        ComparisonTestKind.SUPERIORITY,
    )
    assert name == (
        "plurality necessity|Single-Reproduction Necessity|"
        "One Byzantine Source-Copy Reproducer|"
        "Full Plurality Path__vs__One Independent Retrain|"
        "malicious-admission|superiority"
    )


def test_source_exclusion_family_has_only_asr_superiority() -> None:
    definitions = tuple(
        definition
        for definition in build_comparison_registry()
        if definition.family is ClaimFamily.SOURCE_EXCLUSION_CENTRAL_CLAIM
    )
    assert len(definitions) == 1
    assert definitions[0].metric is ComparisonMetric.ATTACK_SUCCESS_RATE
    assert definitions[0].test_kind is ComparisonTestKind.SUPERIORITY


def test_primary_family_contains_only_structurally_applicable_metrics() -> None:
    definitions = tuple(
        definition
        for definition in build_comparison_registry()
        if definition.family is ClaimFamily.PRIMARY_BASELINE_SUPERIORITY
    )
    legitimate = tuple(
        definition
        for definition in definitions
        if definition.scientific_scenario == PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value
    )
    malicious = tuple(
        definition
        for definition in definitions
        if definition.scientific_scenario
        in (
            PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,
            PrimaryScenario.ONE_BYZANTINE_POST_REFERENCE_PARTICIPANT.value,
        )
    )
    assert len(definitions) == 208
    assert all(
        definition.metric
        not in (ComparisonMetric.MALICIOUS_ADMISSION, ComparisonMetric.ATTACK_SUCCESS_RATE)
        for definition in legitimate
    )
    assert all(
        any(
            candidate.metric is ComparisonMetric.MALICIOUS_ADMISSION
            and candidate.reference_method == definition.reference_method
            and candidate.scientific_scenario == definition.scientific_scenario
            for candidate in malicious
        )
        for definition in malicious
        if definition.metric is ComparisonMetric.TARGET_F1
    )
    assert all(
        any(
            candidate.metric is ComparisonMetric.ATTACK_SUCCESS_RATE
            and candidate.reference_method == definition.reference_method
            and candidate.scientific_scenario == definition.scientific_scenario
            for candidate in malicious
        )
        for definition in malicious
        if definition.metric is ComparisonMetric.TARGET_F1
    )


def test_model_replacement_reproducer_conditions_include_asr() -> None:
    definitions = tuple(
        definition
        for definition in build_comparison_registry()
        if definition.family is ClaimFamily.REPRODUCER_ROBUSTNESS
        and definition.scientific_scenario
        in (
            ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR.value,
            ReproducerCondition.TWO_MODEL_REPLACEMENT_BACKDOORS.value,
        )
    )
    assert definitions
    references = frozenset(definition.reference_method for definition in definitions)
    asr_references = frozenset(
        definition.reference_method
        for definition in definitions
        if definition.metric is ComparisonMetric.ATTACK_SUCCESS_RATE
    )
    assert asr_references == references


def test_shared_epistemic_comparisons_use_primary_clean_reference() -> None:
    definitions = tuple(
        definition
        for definition in build_comparison_registry()
        if definition.experiment == SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME
    )
    assert definitions
    assert all(
        definition.reference_experiment == PRIMARY_CONFIRMATORY_EVALUATION_NAME
        and definition.reference_scenario == PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value
        for definition in definitions
    )


def test_capability_granularity_ablation_treats_false_certification_as_harm() -> None:
    definition = next(
        definition
        for definition in build_comparison_registry()
        if definition.family is ClaimFamily.MECHANISM_ABLATION
        and definition.method == AblationVariant.CAPABILITY_CONTRACT_GRANULARITY.value
    )
    assert definition.metric is ComparisonMetric.FALSE_SAME_CAPABILITY_CERTIFICATION_RATE
    assert definition.orientation is ComparisonOrientation.LOWER_IS_BETTER


def test_evaluate_comparison_zero_pairs_is_undefined() -> None:
    result = evaluate_comparison(
        build_comparison_registry()[0],
        (),
        CONFIG.metrics_and_statistics.bootstrap,
        CONFIG.seeds_and_determinism.analysis_seed,
    )
    assert result.comparison_state is ComparisonState.UNDEFINED
    assert result.mean_paired_difference is None
    assert result.raw_p_value is None


def test_evaluate_comparison_strong_consistent_effect() -> None:
    result = evaluate_comparison(
        build_comparison_registry()[0],
        (1.0,) * 10,
        CONFIG.metrics_and_statistics.bootstrap,
        CONFIG.seeds_and_determinism.analysis_seed,
    )
    assert result.complete_seed_count == 10
    assert result.mean_paired_difference == 1.0
    assert result.raw_p_value is not None
    assert result.raw_p_value < 0.05


def test_holm_adjustment_marks_passed_and_failed() -> None:
    passing = evaluate_comparison(
        build_comparison_registry()[0],
        (1.0,) * 10,
        CONFIG.metrics_and_statistics.bootstrap,
        CONFIG.seeds_and_determinism.analysis_seed,
    )
    failing = evaluate_comparison(
        build_comparison_registry()[1],
        (0.0,) * 10,
        CONFIG.metrics_and_statistics.bootstrap,
        CONFIG.seeds_and_determinism.analysis_seed,
    )
    adjusted = apply_holm_adjustment(
        ComparisonFamilyResult(
            family=ClaimFamily.PROPOSAL_SCREEN_NECESSITY,
            comparisons=(passing, failing),
        ),
        CONFIG.metrics_and_statistics.multiplicity,
    )
    passing_result = next(
        result
        for result in adjusted.comparisons
        if result.definition.comparison_name == passing.definition.comparison_name
    )
    failing_result = next(
        result
        for result in adjusted.comparisons
        if result.definition.comparison_name == failing.definition.comparison_name
    )
    assert passing_result.comparison_state is ComparisonState.PASSED
    assert failing_result.comparison_state is ComparisonState.FAILED
