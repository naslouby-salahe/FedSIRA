from collections.abc import Iterator
from pathlib import Path

import pytest

from fedsira.domain.enums import (
    ArtifactFamily,
    ArtifactInstanceLabel,
    BaselineIdentity,
    ComparisonMetric,
    ExperimentLifecycleState,
    ExperimentName,
)
from fedsira.evaluation.comparison_evidence import (
    COMPARISON_EVIDENCE_SCHEMA_VERSION,
    PersistedComparisonEvidence,
    comparison_evidence_failures,
    comparison_evidence_slot,
    current_comparison_evidence,
    metric_evidence_digest,
    publish_comparison_evidence,
)
from fedsira.experiments.engine import (
    EXECUTION_RECORD_SCHEMA_VERSION,
    ExecutionProvenance,
    PersistedExecutionRecord,
)
from fedsira.runtime import (
    ApplicationContext,
    bound_application_context,
    current_application_context,
)

METHOD = BaselineIdentity.FEDAVG_REFERENCE


@pytest.fixture
def isolated_repository(tmp_path: Path) -> Iterator[Path]:
    context: ApplicationContext = current_application_context().model_copy(
        update={"repository_root": tmp_path}
    )
    with bound_application_context(context):
        yield tmp_path


def _record(metric_value: float | None) -> PersistedExecutionRecord:
    return PersistedExecutionRecord(
        schema_version=EXECUTION_RECORD_SCHEMA_VERSION,
        semantic_key=f"{ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION}|'''{METHOD}'''|Scenario|1103",
        experiment=ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION,
        method=METHOD,
        condition="Scenario",
        master_seed=1103,
        terminal_state=ExperimentLifecycleState.COMPLETED,
        metrics=((ComparisonMetric.TARGET_F1, metric_value),),
        failure=None,
    )


def test_metric_evidence_digest_tracks_metric_values() -> None:
    assert metric_evidence_digest((_record(0.5),)) == metric_evidence_digest((_record(0.5),))
    assert metric_evidence_digest((_record(0.5),)) != metric_evidence_digest((_record(0.6),))


def test_metric_evidence_digest_tracks_provenance_and_scoring_artifacts() -> None:
    record = _record(0.5)
    identified = record.model_copy(
        update={
            "provenance": ExecutionProvenance(
                configuration_digest="a" * 64,
                code_revision=None,
                dataset_manifest_hash="b" * 64,
            ),
            "scoring_artifact_ids": ("c" * 64,),
        }
    )
    assert metric_evidence_digest((record,)) != metric_evidence_digest((identified,))
    assert metric_evidence_digest((identified,)) != metric_evidence_digest(
        (identified.model_copy(update={"scoring_artifact_ids": ("d" * 64,)}),)
    )


def test_metric_evidence_digest_distinguishes_undefined_from_zero() -> None:
    assert metric_evidence_digest((_record(0.0),)) != metric_evidence_digest((_record(None),))


def test_metric_evidence_digest_is_independent_of_record_order() -> None:
    first = _record(0.5)
    second = _record(0.6).model_copy(update={"semantic_key": "Experiment|Method|Scenario|1217"})
    assert metric_evidence_digest((first, second)) == metric_evidence_digest((second, first))


def test_comparison_evidence_slot_is_per_experiment_and_uses_the_family() -> None:
    slot = comparison_evidence_slot(ExperimentName.MECHANISM_ABLATION)
    assert slot.family is ArtifactFamily.STATISTICAL_COMPARISON_ARTIFACT
    assert slot.instance == ArtifactInstanceLabel.COMPARISONS
    assert slot.experiment == ExperimentName.MECHANISM_ABLATION
    assert slot != comparison_evidence_slot(ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION)


def test_persisted_comparison_evidence_round_trips_its_fields() -> None:
    evidence = PersistedComparisonEvidence(
        schema_version=COMPARISON_EVIDENCE_SCHEMA_VERSION,
        experiment=ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION,
        metric_evidence_digest="a" * 64,
        families=(),
    )
    restored = PersistedComparisonEvidence.model_validate_json(evidence.model_dump_json())
    assert restored == evidence


def test_currency_check_is_silent_when_no_evidence_was_published() -> None:
    assert (
        comparison_evidence_failures(
            ExperimentName.DATA_AND_DOMAIN_EVIDENCE_VALIDATION, (_record(0.5),)
        )
        == ()
    )
    assert (
        current_comparison_evidence(
            ExperimentName.DATA_AND_DOMAIN_EVIDENCE_VALIDATION, (_record(0.5),)
        )
        is None
    )


def test_current_comparison_evidence_is_required_for_registered_comparisons(
    isolated_repository: Path,
) -> None:
    failures = comparison_evidence_failures(
        ExperimentName.SECONDARY_DATASET_GENERALIZATION,
        (_record(0.5),),
    )
    assert failures == (
        f"{ExperimentName.SECONDARY_DATASET_GENERALIZATION}: "
        "required comparison evidence is missing",
    )


def test_published_comparison_evidence_is_reused_only_for_exact_metric_lineage(
    isolated_repository: Path,
) -> None:
    del isolated_repository
    experiment = ExperimentName.SECONDARY_DATASET_GENERALIZATION
    record = _record(0.5).model_copy(
        update={
            "experiment": experiment,
            "semantic_key": f"{experiment}|{METHOD}|Scenario|1103",
            "provenance": ExecutionProvenance(
                configuration_digest="a" * 64,
                code_revision=None,
                dataset_manifest_hash="b" * 64,
            ),
            "scoring_artifact_ids": ("c" * 64,),
        }
    )
    manifest, reused = publish_comparison_evidence(experiment, (record,), ())
    assert not reused
    current = current_comparison_evidence(experiment, (record,))
    assert current is not None
    assert current[0].identity == manifest.identity
    changed_lineage = record.model_copy(update={"scoring_artifact_ids": ("d" * 64,)})
    assert current_comparison_evidence(experiment, (changed_lineage,)) is None


def test_current_comparison_evidence_requires_the_complete_registered_family_set(
    isolated_repository: Path,
) -> None:
    experiment = ExperimentName.SECONDARY_DATASET_GENERALIZATION
    record = _record(0.5).model_copy(
        update={
            "experiment": experiment,
            "semantic_key": f"{experiment}|{METHOD}|Scenario|1103",
        }
    )
    publish_comparison_evidence(experiment, (record,), ())

    current = current_comparison_evidence(experiment, (record,))
    assert current is not None
    assert comparison_evidence_failures(experiment, (record,)) == (
        f"{experiment}: persisted comparison evidence does not contain "
        "the complete registered family set",
    )


def test_analysis_seed_is_part_of_comparison_artifact_currency(
    isolated_repository: Path,
) -> None:
    experiment = ExperimentName.SECONDARY_DATASET_GENERALIZATION
    record = _record(0.5).model_copy(
        update={
            "experiment": experiment,
            "semantic_key": f"{experiment}|{METHOD}|Scenario|1103",
        }
    )
    _manifest, _reused = publish_comparison_evidence(experiment, (record,), ())
    assert current_comparison_evidence(experiment, (record,)) is not None

    context = current_application_context()
    scientific_config = context.scientific_config
    seeds = scientific_config.seeds_and_determinism
    changed_seed = seeds.analysis_seed + 1
    if changed_seed in seeds.master_seeds or changed_seed == seeds.smoke_seed:
        changed_seed += 1
    changed_scientific_config = scientific_config.model_copy(
        update={"seeds_and_determinism": seeds.model_copy(update={"analysis_seed": changed_seed})}
    )
    changed_context = context.model_copy(update={"scientific_config": changed_scientific_config})
    with bound_application_context(changed_context):
        assert current_comparison_evidence(experiment, (record,)) is None
        failures = comparison_evidence_failures(experiment, (record,))

    assert failures == (
        f"{experiment}: persisted comparison evidence has stale statistical configuration",
    )
