from pathlib import Path

from pytest import MonkeyPatch

from fedsira.domain.enums import (
    AdmissionState,
    ComparisonMetric,
    ProposalEpisode,
    SourceExclusionMethod,
)
from fedsira.domain.models import PreparedEvidenceCounts, ScientificCell
from fedsira.domain.types import MetricObservation
from fedsira.evaluation.metrics import (
    malicious_admission_from_ancestry,
    production_depends_on_compromised_contributor,
)
from fedsira.experiments.definitions import SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME
from fedsira.experiments.handlers import ProtocolCellExecutor


def test_malicious_admission_follows_production_ancestry_not_method_identity() -> None:
    assert production_depends_on_compromised_contributor(("honest",), ("source",)) is False
    assert production_depends_on_compromised_contributor(("source", "honest"), ("source",)) is True
    assert (
        malicious_admission_from_ancestry(
            admitted=True,
            malicious_authority_fixture_present=True,
            depends_on_compromised_contributor=False,
        )
        == 0.0
    )
    assert (
        malicious_admission_from_ancestry(
            admitted=True,
            malicious_authority_fixture_present=True,
            depends_on_compromised_contributor=True,
        )
        == 1.0
    )
    assert (
        malicious_admission_from_ancestry(
            admitted=False,
            malicious_authority_fixture_present=True,
            depends_on_compromised_contributor=True,
        )
        == 0.0
    )
    assert (
        malicious_admission_from_ancestry(
            admitted=True,
            malicious_authority_fixture_present=False,
            depends_on_compromised_contributor=True,
        )
        is None
    )


def _cell(method: SourceExclusionMethod) -> ScientificCell:
    return ScientificCell(
        experiment=SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
        method=method,
        condition=ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
        master_seed=1103,
    )


def _evidence() -> PreparedEvidenceCounts:
    return PreparedEvidenceCounts(
        screen_target_count=0,
        reproduction_target_count=2000,
        reproduction_supported_count=2000,
        final_gate_adequate_domain_count=6,
    )


class _SourceExclusionProbe(ProtocolCellExecutor):
    def score(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        return self._execute_source_exclusion_cell(cell, evidence)

    def remember_honest(
        self,
        _cell: ScientificCell,
        _evidence: PreparedEvidenceCounts,
        opening_resolved: bool = False,
        verifier_condition_override: object = None,
    ) -> AdmissionState:
        del opening_resolved, verifier_condition_override
        self._last_production_contributor_ids = ("honest-device",)
        self._last_synthesis_row_ids = ("honest-device",)
        self._last_compromised_reproducers = frozenset()
        return AdmissionState.ADMITTED

    def remember_direct_source(self, _cell: ScientificCell) -> AdmissionState:
        return AdmissionState.ADMITTED

    def remember_sanitized_source(
        self, _cell: ScientificCell, _evidence: PreparedEvidenceCounts
    ) -> AdmissionState:
        self._last_production_contributor_ids = ("source-device",)
        return AdmissionState.ADMITTED

    def remember_recovered_without_source(
        self, _cell: ScientificCell, _evidence: PreparedEvidenceCounts
    ) -> AdmissionState:
        self._last_production_contributor_ids = ()
        return AdmissionState.ADMITTED


def _named_source(_adapter: object, _cell: object) -> str:
    return "source-device"


def test_source_exclusion_cell_scores_the_admitted_object(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "fedsira.experiments.handlers.source_domain_for_cell",
        _named_source,
    )
    monkeypatch.setattr(
        ProtocolCellExecutor, "_advance_protocol", _SourceExclusionProbe.remember_honest
    )
    monkeypatch.setattr(
        ProtocolCellExecutor, "client_review_outcome", _SourceExclusionProbe.remember_direct_source
    )
    monkeypatch.setattr(
        ProtocolCellExecutor,
        "_source_update_sanitization_outcome",
        _SourceExclusionProbe.remember_sanitized_source,
    )
    monkeypatch.setattr(
        ProtocolCellExecutor,
        "_recovery_after_source_admission_outcome",
        _SourceExclusionProbe.remember_recovered_without_source,
    )
    executor = _SourceExclusionProbe(primary_prepared_root=Path("prepared-fixture"))
    evidence = _evidence()

    full_state, full_metrics = executor.score(_cell(SourceExclusionMethod.FULL_FEDSIRA), evidence)
    retrain_state, retrain_metrics = executor.score(
        _cell(SourceExclusionMethod.ONE_INDEPENDENT_RETRAIN),
        evidence,
    )
    review_state, review_metrics = executor.score(
        _cell(SourceExclusionMethod.CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION),
        evidence,
    )
    sanitized_state, sanitized_metrics = executor.score(
        _cell(SourceExclusionMethod.SOURCE_UPDATE_SANITIZATION_REFERENCE),
        evidence,
    )
    recovered_state, recovered_metrics = executor.score(
        _cell(SourceExclusionMethod.RECOVERY_AFTER_SOURCE_ADMISSION),
        evidence,
    )

    assert full_state is AdmissionState.ADMITTED
    assert retrain_state is AdmissionState.ADMITTED
    assert review_state is AdmissionState.ADMITTED
    assert sanitized_state is AdmissionState.ADMITTED
    assert recovered_state is AdmissionState.ADMITTED
    assert dict(full_metrics)[ComparisonMetric.MALICIOUS_ADMISSION] == 0.0
    assert dict(retrain_metrics)[ComparisonMetric.MALICIOUS_ADMISSION] == 0.0
    assert dict(review_metrics)[ComparisonMetric.MALICIOUS_ADMISSION] == 1.0
    assert dict(sanitized_metrics)[ComparisonMetric.MALICIOUS_ADMISSION] == 1.0
    assert dict(recovered_metrics)[ComparisonMetric.MALICIOUS_ADMISSION] == 0.0
