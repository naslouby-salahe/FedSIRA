from fedsira.domain.enums import (
    ArtifactFamily,
    ExperimentLifecycleState,
)
from fedsira.evaluation.comparison_evidence import (
    COMPARISON_EVIDENCE_INSTANCE,
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


def _record(metric_value: float | None) -> PersistedExecutionRecord:
    return PersistedExecutionRecord(
        schema_version=EXECUTION_RECORD_SCHEMA_VERSION,
        semantic_key="Experiment|Method|Scenario|1103",
        experiment="Experiment",
        method="Method",
        condition="Scenario",
        master_seed=1103,
        terminal_state=ExperimentLifecycleState.COMPLETED,
        metrics=(("target-f1", metric_value),),
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
    slot = comparison_evidence_slot("Mechanism Ablation")
    assert slot.family is ArtifactFamily.STATISTICAL_COMPARISON_ARTIFACT
    assert slot.instance == COMPARISON_EVIDENCE_INSTANCE
    assert slot.experiment == "Mechanism Ablation"
    assert slot != comparison_evidence_slot("Primary Confirmatory Evaluation")


def test_persisted_comparison_evidence_round_trips_its_fields() -> None:
    evidence = PersistedComparisonEvidence(
        schema_version="fedsira|comparison_evidence|1",
        experiment="Experiment",
        metric_evidence_digest="a" * 64,
        families=(),
    )
    restored = PersistedComparisonEvidence.model_validate_json(evidence.model_dump_json())
    assert restored == evidence


def test_currency_check_is_silent_when_no_evidence_was_published() -> None:
    assert comparison_evidence_failures("Unpublished-Experiment", (_record(0.5),)) == ()
    assert read_comparison_evidence("Unpublished-Experiment") is None
