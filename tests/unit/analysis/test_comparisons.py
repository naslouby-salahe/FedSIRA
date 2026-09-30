import pytest
from pydantic import ValidationError

from fedsira.config import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import (
    AblationVariant,
    ComparisonFamily,
    CoreMethodIdentity,
    ExperimentName,
    PrimaryScenario,
    ReproducerCondition,
)
from fedsira.evaluation.comparisons import (
    ComparisonDefinition,
    ComparisonFamilyResult,
    ComparisonMetric,
    ComparisonOrientation,
    ComparisonSidedness,
    ComparisonState,
    ComparisonTemplate,
    ComparisonTestKind,
    apply_holm_adjustment,
    build_comparison_name,
    build_comparison_registry,
    evaluate_comparison,
)
from fedsira.experiments.definitions import (
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
)

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)


def test_registry_has_all_ten_claim_families() -> None:
    families = frozenset(definition.family for definition in build_comparison_registry())
    assert families == frozenset(ComparisonFamily)


def test_registry_has_unique_comparison_names() -> None:
    names = tuple(definition.comparison_name for definition in build_comparison_registry())
    assert len(names) == len(frozenset(names))


def test_registry_comparisons_have_their_required_effect_thresholds() -> None:
    for definition in build_comparison_registry():
        if definition.test_kind is ComparisonTestKind.SUPERIORITY:
            assert definition.material_threshold is not None
        else:
            assert definition.margin is not None


def test_superiority_comparison_cannot_omit_materiality_threshold() -> None:
    with pytest.raises(ValidationError, match="requires a materiality threshold"):
        ComparisonTemplate(
            metric=ComparisonMetric.TARGET_F1,
            orientation=ComparisonOrientation.HIGHER_IS_BETTER,
            test_kind=ComparisonTestKind.SUPERIORITY,
        )


def test_superiority_definition_cannot_omit_materiality_threshold() -> None:
    definition = build_comparison_registry()[0]
    definition_data = definition.model_dump()
    definition_data["material_threshold"] = None

    with pytest.raises(ValidationError, match="requires a materiality threshold"):
        ComparisonDefinition.model_validate(definition_data)


def test_missing_superiority_threshold_cannot_pass_after_model_copy() -> None:
    definition = build_comparison_registry()[0]
    result = evaluate_comparison(
        definition,
        (1.0,) * 10,
        CONFIG.metrics_and_statistics.bootstrap,
        CONFIG.seeds_and_determinism.analysis_seed,
    )
    valid_adjusted = apply_holm_adjustment(
        ComparisonFamilyResult(family=definition.family, comparisons=(result,)),
        CONFIG.metrics_and_statistics.multiplicity,
    )
    assert valid_adjusted.comparisons[0].comparison_state is ComparisonState.PASSED

    invalid_definition = definition.model_copy(update={"material_threshold": None})
    invalid_result = result.model_copy(update={"definition": invalid_definition})
    with pytest.raises(ValidationError, match="requires a materiality threshold"):
        apply_holm_adjustment(
            ComparisonFamilyResult(family=definition.family, comparisons=(invalid_result,)),
            CONFIG.metrics_and_statistics.multiplicity,
        )


def test_noninferiority_margin_remains_the_materiality_gate() -> None:
    definition = next(
        item
        for item in build_comparison_registry()
        if item.test_kind is ComparisonTestKind.NON_INFERIORITY
    )
    result = evaluate_comparison(
        definition,
        (0.0,) * 10,
        CONFIG.metrics_and_statistics.bootstrap,
        CONFIG.seeds_and_determinism.analysis_seed,
    )
    adjusted = apply_holm_adjustment(
        ComparisonFamilyResult(family=definition.family, comparisons=(result,)),
        CONFIG.metrics_and_statistics.multiplicity,
    )

    assert adjusted.comparisons[0].comparison_state is ComparisonState.PASSED

    invalid_definition = definition.model_copy(update={"margin": None})
    invalid_result = result.model_copy(update={"definition": invalid_definition})
    with pytest.raises(ValidationError, match="requires a margin"):
        apply_holm_adjustment(
            ComparisonFamilyResult(family=definition.family, comparisons=(invalid_result,)),
            CONFIG.metrics_and_statistics.multiplicity,
        )


def test_noninferiority_margin_change_cannot_reuse_a_stale_p_value() -> None:
    definition = next(
        item
        for item in build_comparison_registry()
        if item.test_kind is ComparisonTestKind.NON_INFERIORITY
    )
    result = evaluate_comparison(
        definition,
        (0.2, 0.1, -0.05, -0.2),
        CONFIG.metrics_and_statistics.bootstrap,
        CONFIG.seeds_and_determinism.analysis_seed,
    )
    altered_p_value = result.model_copy(update={"raw_p_value": 0.0})
    with pytest.raises(ValueError, match="raw p-value does not match"):
        apply_holm_adjustment(
            ComparisonFamilyResult(
                family=definition.family,
                comparisons=(altered_p_value,),
            ),
            CONFIG.metrics_and_statistics.multiplicity,
        )

    changed_margin = definition.model_copy(update={"margin": 0.5})
    stale_margin_result = result.model_copy(update={"definition": changed_margin})
    with pytest.raises(ValueError, match="does not match its registered definition"):
        apply_holm_adjustment(
            ComparisonFamilyResult(
                family=definition.family,
                comparisons=(stale_margin_result,),
            ),
            CONFIG.metrics_and_statistics.multiplicity,
        )

    changed_orientation = definition.model_copy(
        update={"orientation": ComparisonOrientation.LOWER_IS_BETTER}
    )
    orientation_result = result.model_copy(update={"definition": changed_orientation})
    with pytest.raises(ValueError, match="does not match its registered definition"):
        apply_holm_adjustment(
            ComparisonFamilyResult(
                family=definition.family,
                comparisons=(orientation_result,),
            ),
            CONFIG.metrics_and_statistics.multiplicity,
        )

    wrong_sidedness = definition.model_copy(update={"sidedness": ComparisonSidedness.TWO_SIDED})
    invalid_sidedness_result = result.model_copy(update={"definition": wrong_sidedness})
    with pytest.raises(ValidationError, match="requires one-sided sidedness"):
        apply_holm_adjustment(
            ComparisonFamilyResult(
                family=definition.family,
                comparisons=(invalid_sidedness_result,),
            ),
            CONFIG.metrics_and_statistics.multiplicity,
        )


def test_holm_adjustment_rejects_a_comparison_from_another_family() -> None:
    definition = build_comparison_registry()[0]
    result = evaluate_comparison(
        definition,
        (1.0,) * 10,
        CONFIG.metrics_and_statistics.bootstrap,
        CONFIG.seeds_and_determinism.analysis_seed,
    )
    other_family = next(family for family in ComparisonFamily if family is not definition.family)

    with pytest.raises(ValueError, match="different comparison family"):
        apply_holm_adjustment(
            ComparisonFamilyResult(family=other_family, comparisons=(result,)),
            CONFIG.metrics_and_statistics.multiplicity,
        )

    duplicate_result = ComparisonFamilyResult(
        family=definition.family,
        comparisons=(result, result),
    )
    with pytest.raises(ValueError, match="duplicate comparison names"):
        apply_holm_adjustment(duplicate_result, CONFIG.metrics_and_statistics.multiplicity)


def test_comparison_name_follows_section_18_9_pattern() -> None:
    name = build_comparison_name(
        ComparisonFamily.PLURALITY_NECESSITY,
        ExperimentName.SINGLE_REPRODUCTION_NECESSITY,
        "One Byzantine Source-Copy Reproducer",
        CoreMethodIdentity.FULL_PLURALITY_PATH,
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


def test_source_exclusion_family_covers_security_superiority_and_utility_noninferiority() -> None:
    definitions = tuple(
        definition
        for definition in build_comparison_registry()
        if definition.family is ComparisonFamily.SOURCE_EXCLUSION_CENTRAL_EFFECT
    )
    assert len(definitions) == 2
    assert {(definition.metric, definition.test_kind) for definition in definitions} == {
        (ComparisonMetric.ATTACK_SUCCESS_RATE, ComparisonTestKind.SUPERIORITY),
        (ComparisonMetric.TARGET_F1, ComparisonTestKind.NON_INFERIORITY),
    }


def test_primary_family_contains_only_structurally_applicable_metrics() -> None:
    definitions = tuple(
        definition
        for definition in build_comparison_registry()
        if definition.family is ComparisonFamily.PRIMARY_BASELINE_SUPERIORITY
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
        if definition.family is ComparisonFamily.REPRODUCER_ROBUSTNESS
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
        if definition.family is ComparisonFamily.MECHANISM_ABLATION
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
            family=ComparisonFamily.PROPOSAL_SCREEN_NECESSITY,
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
