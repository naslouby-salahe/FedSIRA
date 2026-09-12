from fedsira.artifacts.store import ArtifactDependency, artifact_identity
from fedsira.domain.enums import AblationReproducerStrategy, ArtifactFamily
from fedsira.evaluation.comparisons import ComparisonMetric
from fedsira.experiments.definitions import (
    MECHANISM_ABLATION_NAME,
    AblationScenario,
    AblationVariant,
    HeterogeneityRegime,
    ablation_reproducer_strategy,
    feature_shift_magnitude,
)
from fedsira.experiments.engine import ablation_reference_slot


def test_ablation_reference_slot_is_deterministic_and_keyed_by_scenario_and_seed() -> None:
    scenario = AblationScenario.ONE_MALICIOUS_REPRODUCER
    first = ablation_reference_slot(scenario, 1103)
    assert first == ablation_reference_slot(scenario, 1103)
    assert first.family is ArtifactFamily.DOMAIN_SEED_METRIC_ARTIFACT
    assert first.experiment == MECHANISM_ABLATION_NAME
    assert first != ablation_reference_slot(scenario, 1217)
    assert first != ablation_reference_slot(AblationScenario.NATURAL, 1103)


def test_ablation_reference_instance_token_is_filesystem_safe() -> None:
    for scenario in AblationScenario:
        token = ablation_reference_slot(scenario, 1103).instance
        assert token == token.strip()
        assert "/" not in token
        assert " " not in token
        assert token[0].isalnum()


def test_every_ablation_variant_has_a_declared_claim_metric_except_the_reference() -> None:
    for variant in AblationVariant:
        scenario = AblationVariant(variant)
        assert scenario is variant
        assert (
            ablation_reproducer_strategy(AblationScenario.ONE_MALICIOUS_REPRODUCER)
            is AblationReproducerStrategy.MODEL_REPLACEMENT
        )
        assert (
            ablation_reproducer_strategy(AblationScenario.ONE_VERIFIER_AWARE_BACKDOOR_REPRODUCER)
            is AblationReproducerStrategy.VERIFIER_AWARE
        )
        assert (
            ablation_reproducer_strategy(AblationScenario.NATURAL)
            is AblationReproducerStrategy.NONE
        )


def test_feature_shift_magnitude_is_selected_by_condition_identity() -> None:
    assert feature_shift_magnitude(HeterogeneityRegime.NATURAL.value) is None
    half_shift = feature_shift_magnitude(HeterogeneityRegime.FEATURE_SHIFT_0_5.value)
    full_shift = feature_shift_magnitude(HeterogeneityRegime.FEATURE_SHIFT_1_0.value)
    assert half_shift is not None
    assert full_shift is not None
    assert half_shift < full_shift
    assert feature_shift_magnitude(
        AblationScenario.FEATURE_SHIFT_1_0.value
    ) == feature_shift_magnitude(HeterogeneityRegime.FEATURE_SHIFT_1_0.value)
    assert feature_shift_magnitude(
        AblationScenario.HONEST_SITE_SPECIFIC_FEATURE_SHIFT_1_0.value
    ) == feature_shift_magnitude(HeterogeneityRegime.FEATURE_SHIFT_1_0.value)


def test_artifact_identity_changes_when_a_declared_dependency_changes() -> None:
    slot = ablation_reference_slot(AblationScenario.NATURAL, 1103)
    first = artifact_identity(
        slot,
        (ArtifactDependency(dependency="prepared-evidence", digest="a" * 64),),
        "fedsira|ablation_reference|1",
    )
    second = artifact_identity(
        slot,
        (ArtifactDependency(dependency="prepared-evidence", digest="b" * 64),),
        "fedsira|ablation_reference|1",
    )
    assert first != second
    assert first == artifact_identity(
        slot,
        (ArtifactDependency(dependency="prepared-evidence", digest="a" * 64),),
        "fedsira|ablation_reference|1",
    )


def test_artifact_identity_changes_when_the_procedure_changes() -> None:
    slot = ablation_reference_slot(AblationScenario.NATURAL, 1103)
    dependencies = (ArtifactDependency(dependency="prepared-evidence", digest="a" * 64),)
    assert artifact_identity(
        slot, dependencies, "fedsira|ablation_reference|1"
    ) != artifact_identity(slot, dependencies, "fedsira|ablation_reference|2")


def test_artifact_identity_is_independent_of_dependency_declaration_order() -> None:
    slot = ablation_reference_slot(AblationScenario.NATURAL, 1103)
    first = ArtifactDependency(dependency="alpha", digest="a" * 64)
    second = ArtifactDependency(dependency="beta", digest="b" * 64)
    assert artifact_identity(
        slot, (first, second), "fedsira|ablation_reference|1"
    ) == artifact_identity(slot, (second, first), "fedsira|ablation_reference|1")


def test_comparison_metric_enum_carries_the_canonical_metric_names() -> None:
    assert ComparisonMetric.ATTACK_SUCCESS_RATE.value == "asr"
    assert (
        ComparisonMetric.FALSE_SAME_CAPABILITY_CERTIFICATION_RATE.value
        == "false-same-capability-certification-rate"
    )
    assert ComparisonMetric.MALICIOUS_ADMISSION.value == "malicious-admission"
