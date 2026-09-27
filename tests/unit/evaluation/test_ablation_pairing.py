import math
from collections.abc import Iterator
from pathlib import Path

import pytest

from fedsira.artifacts.paths import artifact_slot_directory
from fedsira.artifacts.store import publish_artifact
from fedsira.domain.enums import (
    AblationVariant,
    ArtifactFamily,
    ArtifactProducer,
    DatasetId,
    ExperimentLifecycleState,
)
from fedsira.domain.models import ScientificCell
from fedsira.evaluation.comparisons import (
    ComparisonFamily,
    ComparisonState,
    ablation_metric,
    paired_standardized_effect_size,
)
from fedsira.evaluation.service import build_comparison_results_for_experiment
from fedsira.experiments.definitions import MECHANISM_ABLATION_NAME, ablation_scenario_for_variant
from fedsira.experiments.engine import (
    ABLATION_REFERENCE_PROCEDURE_IDENTITY,
    ABLATION_REFERENCE_SCHEMA_VERSION,
    CellExecutionOutcome,
    ExecutionRecordStore,
    PersistedAblationReference,
    ablation_reference_dependencies,
    ablation_reference_slot,
)
from fedsira.runtime import bound_application_context, current_application_context

VARIANT = AblationVariant.NO_PROPOSAL_SCREEN


@pytest.fixture
def isolated_repository(tmp_path: Path) -> Iterator[Path]:
    context = current_application_context().model_copy(update={"repository_root": tmp_path})
    with bound_application_context(context):
        yield tmp_path


def _master_seed() -> int:
    return current_application_context().scientific_config.seeds_and_determinism.master_seeds[0]


def _publish_reference(repository: Path, metric_value: float, seed: int | None = None) -> None:
    scenario = ablation_scenario_for_variant(VARIANT)
    metric, _orientation = ablation_metric(VARIANT)
    seed = _master_seed() if seed is None else seed
    slot = ablation_reference_slot(scenario.value, seed)
    publish_artifact(
        slot=slot,
        producer=ArtifactProducer.EVALUATION_PRODUCER,
        payload=PersistedAblationReference(
            schema_version=ABLATION_REFERENCE_SCHEMA_VERSION,
            scientific_scenario=scenario.value,
            master_seed=seed,
            metrics=((metric.value, metric_value),),
        )
        .model_dump_json()
        .encode("utf-8"),
        dependencies=ablation_reference_dependencies(DatasetId.N_BAIOT),
        procedure_identity=ABLATION_REFERENCE_PROCEDURE_IDENTITY,
        slot_directory=repository / artifact_slot_directory(slot),
        staging_root=repository / "staging",
    )


def _variant_outcomes(metric_value: float) -> tuple[CellExecutionOutcome, ...]:
    scenario = ablation_scenario_for_variant(VARIANT)
    metric, _orientation = ablation_metric(VARIANT)
    return (
        CellExecutionOutcome(
            cell=ScientificCell(
                experiment=MECHANISM_ABLATION_NAME,
                method=VARIANT,
                condition=scenario,
                master_seed=_master_seed(),
            ),
            terminal_state=ExperimentLifecycleState.COMPLETED,
            failure=None,
            metrics=((metric.value, metric_value),),
        ),
    )


def _variant_comparison(repository: Path, metric_value: float):
    families = build_comparison_results_for_experiment(
        MECHANISM_ABLATION_NAME,
        DatasetId.N_BAIOT,
        _variant_outcomes(metric_value),
        ExecutionRecordStore(repository / "execution"),
    )
    family = next(item for item in families if item.family is ComparisonFamily.MECHANISM_ABLATION)
    return next(item for item in family.comparisons if item.definition.method == VARIANT.value)


def test_paired_comparison_is_defined_only_from_the_persisted_reference(
    isolated_repository: Path,
) -> None:
    without_reference = _variant_comparison(isolated_repository, 3.0)
    assert without_reference.complete_seed_count == 0
    assert without_reference.comparison_state is ComparisonState.UNDEFINED
    _publish_reference(isolated_repository, 1.0)
    with_reference = _variant_comparison(isolated_repository, 3.0)
    assert with_reference.complete_seed_count == 1
    assert with_reference.paired_differences == (-2.0,)
    assert with_reference.comparison_state is ComparisonState.INCONCLUSIVE_TECHNICAL
    assert with_reference.definition.reference_method == AblationVariant.FULL_FEDSIRA.value


def test_inference_requires_nine_of_ten_complete_seed_pairs(isolated_repository: Path) -> None:
    seeds = current_application_context().scientific_config.seeds_and_determinism.master_seeds
    scenario = ablation_scenario_for_variant(VARIANT)
    metric, _orientation = ablation_metric(VARIANT)
    outcomes = tuple(
        CellExecutionOutcome(
            cell=ScientificCell(
                experiment=MECHANISM_ABLATION_NAME,
                method=VARIANT,
                condition=scenario,
                master_seed=seed,
            ),
            terminal_state=ExperimentLifecycleState.COMPLETED,
            failure=None,
            metrics=((metric.value, 0.5),),
        )
        for seed in seeds
    )
    store = ExecutionRecordStore(isolated_repository / "execution")

    for complete_count in (8, 9, 10):
        _publish_reference(isolated_repository, 0.5, seed=seeds[complete_count - 1])
        if complete_count > 1:
            for seed in seeds[: complete_count - 1]:
                _publish_reference(isolated_repository, 0.5, seed=seed)
        family = next(
            item
            for item in build_comparison_results_for_experiment(
                MECHANISM_ABLATION_NAME, DatasetId.N_BAIOT, outcomes, store
            )
            if item.family is ComparisonFamily.MECHANISM_ABLATION
        )
        result = next(
            item for item in family.comparisons if item.definition.method == VARIANT.value
        )
        assert result.complete_seed_count == complete_count
        if complete_count == 8:
            assert result.comparison_state is ComparisonState.INCONCLUSIVE_TECHNICAL
        else:
            assert result.comparison_state is not ComparisonState.INCONCLUSIVE_TECHNICAL


def test_reference_slot_is_the_only_source_of_the_reference_row(isolated_repository: Path) -> None:
    scenario = ablation_scenario_for_variant(VARIANT)
    slot = ablation_reference_slot(scenario.value, _master_seed())
    assert slot.family is ArtifactFamily.DOMAIN_SEED_METRIC_ARTIFACT
    assert slot.experiment == MECHANISM_ABLATION_NAME
    assert not (isolated_repository / artifact_slot_directory(slot)).exists()
    _publish_reference(isolated_repository, 1.0)
    assert (isolated_repository / artifact_slot_directory(slot)).is_dir()


def test_paired_effect_size_uses_sample_standard_deviation_and_handles_zero_variance() -> None:
    effect = paired_standardized_effect_size((1.0, 3.0))
    assert effect is not None
    assert math.isclose(effect, math.sqrt(2.0))
    assert paired_standardized_effect_size((2.0, 2.0)) == math.inf
    assert paired_standardized_effect_size((-2.0, -2.0)) == -math.inf
    assert paired_standardized_effect_size((0.0, 0.0)) == 0.0
