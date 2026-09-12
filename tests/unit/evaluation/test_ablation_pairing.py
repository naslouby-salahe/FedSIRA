from collections.abc import Iterator
from pathlib import Path

import pytest

from fedsira.artifacts.paths import artifact_slot_directory
from fedsira.artifacts.store import publish_artifact
from fedsira.domain.enums import (
    ArtifactFamily,
    ArtifactProducer,
    DatasetId,
    ExperimentLifecycleState,
)
from fedsira.domain.models import ScientificCell
from fedsira.evaluation.comparisons import ComparisonFamily, ComparisonState, ablation_metric
from fedsira.evaluation.service import comparison_results_for_experiment
from fedsira.experiments.definitions import (
    MECHANISM_ABLATION_NAME,
    AblationVariant,
    ablation_scenario_for_variant,
)
from fedsira.experiments.engine import (
    ABLATION_REFERENCE_PROCEDURE_IDENTITY,
    ABLATION_REFERENCE_SCHEMA_VERSION,
    CellExecutionOutcome,
    ExecutionRecordStore,
    PersistedAblationReference,
    ablation_reference_slot,
)
from fedsira.runtime import current_application_context

VARIANT = AblationVariant.NO_PROPOSAL_SCREEN


@pytest.fixture
def isolated_repository(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    monkeypatch.setattr("fedsira.evaluation.service.REPOSITORY_ROOT", tmp_path)
    yield tmp_path


def _master_seed() -> int:
    return current_application_context().scientific_config.seeds_and_determinism.master_seeds[0]


def _publish_reference(repository: Path, metric_value: float) -> None:
    scenario = ablation_scenario_for_variant(VARIANT)
    metric, _orientation = ablation_metric(VARIANT)
    seed = _master_seed()
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
        dependencies=(),
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
                method=VARIANT.value,
                condition=scenario.value,
                master_seed=_master_seed(),
            ),
            terminal_state=ExperimentLifecycleState.COMPLETED,
            failure=None,
            metrics=((metric.value, metric_value),),
        ),
    )


def _variant_comparison(repository: Path, metric_value: float):
    families = comparison_results_for_experiment(
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


def test_reference_slot_is_the_only_source_of_the_reference_row(isolated_repository: Path) -> None:
    scenario = ablation_scenario_for_variant(VARIANT)
    slot = ablation_reference_slot(scenario.value, _master_seed())
    assert slot.family is ArtifactFamily.DOMAIN_SEED_METRIC_ARTIFACT
    assert slot.experiment == MECHANISM_ABLATION_NAME
    assert not (isolated_repository / artifact_slot_directory(slot)).exists()
    _publish_reference(isolated_repository, 1.0)
    assert (isolated_repository / artifact_slot_directory(slot)).is_dir()
