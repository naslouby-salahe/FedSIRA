from fedsira.domain.enums import (
    ArtifactFamily,
    ArtifactInstanceLabel,
    BaselineIdentity,
    ComparisonMetric,
    ExperimentLifecycleState,
    ExperimentName,
)
from fedsira.evaluation.comparison_evidence import (
    PersistedComparisonEvidence,
    comparison_evidence_failures,
    comparison_evidence_slot,
    metric_evidence_digest,
    read_comparison_evidence,
)
from fedsira.experiments.engine import (
    EXECUTION_RECORD_SCHEMA_VERSION,
    PersistedExecutionRecord,
)

METHOD = BaselineIdentity.FEDAVG_REFERENCE


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
        schema_version="fedsira|comparison_evidence|1",
        experiment=ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION,
        metric_evidence_digest="a" * 64,
        families=(),
    )
    restored = PersistedComparisonEvidence.model_validate_json(evidence.model_dump_json())
    assert restored == evidence


def test_currency_check_is_silent_when_no_evidence_was_published() -> None:
    assert (
        comparison_evidence_failures(
            ExperimentName.SECONDARY_DATASET_GENERALIZATION, (_record(0.5),)
        )
        == ()
    )
    assert read_comparison_evidence(ExperimentName.SECONDARY_DATASET_GENERALIZATION) is None
