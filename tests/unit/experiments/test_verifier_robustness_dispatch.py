from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from fedsira.domain.enums import (
    AdmissionState,
    ComparisonMetric,
    DescriptiveScientificMetric,
    ExperimentLifecycleState,
    ProposalEpisode,
    ReproducerCondition,
    VerifierCondition,
    VerifierProfile,
)
from fedsira.domain.models import PreparedEvidenceCounts, ScientificCell
from fedsira.domain.types import DatasetClassToken, FeatureName
from fedsira.experiments.definitions import (
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
)
from fedsira.experiments.handlers import ProtocolCellExecutor
from fedsira.protocol.baselines.registry import BaselineIdentity


def test_verifier_robustness_uses_protocol_result_and_reports_attack_metrics(
    monkeypatch: MonkeyPatch,
) -> None:
    calls: list[ScientificCell] = []

    def fake_advance_protocol(
        executor: ProtocolCellExecutor,
        cell: ScientificCell,
        evidence: PreparedEvidenceCounts,
        *,
        verifier_condition_override: VerifierCondition | None = None,
    ) -> AdmissionState:
        del evidence
        calls.append(cell)
        assert verifier_condition_override is None
        vars(executor).update(
            {
                "_last_reproduction_attempts": 5,
                "_last_certified_attempts": 4,
                "_last_verifier_report_count": 15,
                "_last_verifier_abstention_count": 3,
            }
        )
        return AdmissionState.ADMITTED

    def fake_production_is_compromised(
        _executor: ProtocolCellExecutor, _cell: ScientificCell
    ) -> bool:
        return True

    def fake_prepared_evidence_counts(_root: Path, _target: str) -> PreparedEvidenceCounts:
        return evidence

    monkeypatch.setattr(ProtocolCellExecutor, "_advance_protocol", fake_advance_protocol)
    monkeypatch.setattr(
        ProtocolCellExecutor,
        "_ablation_production_is_compromised",
        fake_production_is_compromised,
    )
    evidence = PreparedEvidenceCounts(
        screen_target_count=0,
        reproduction_target_count=2000,
        reproduction_supported_count=2000,
        final_gate_adequate_domain_count=6,
    )
    monkeypatch.setattr(
        "fedsira.experiments.handlers.load_prepared_evidence_counts",
        fake_prepared_evidence_counts,
    )
    executor = ProtocolCellExecutor(primary_prepared_root=Path("prepared-fixture"))
    cell = ScientificCell(
        experiment=COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
        method=VerifierProfile.DETERMINISTIC_BOUND,
        condition=VerifierCondition.ONE_FALSE_POSITIVE,
        master_seed=1103,
    )

    outcome = executor.execute_cell(cell)
    metrics = dict(outcome.metrics)

    assert outcome.terminal_state is ExperimentLifecycleState.COMPLETED
    assert calls == [cell]
    assert metrics[ComparisonMetric.MALICIOUS_ADMISSION] == 1.0
    assert metrics[DescriptiveScientificMetric.CERTIFIED_ROW_YIELD] == 0.8
    assert metrics[DescriptiveScientificMetric.VERIFIER_ABSTENTION_RATE] == 0.2


def test_byzantine_bound_preserves_resolved_core_cell_for_verifier_attack(
    monkeypatch: MonkeyPatch,
) -> None:
    from fedsira.domain.enums import BoundCondition, CoreMethodIdentity
    from fedsira.experiments.definitions import BYZANTINE_BOUND_VIOLATION_NAME

    calls: list[tuple[ScientificCell, VerifierCondition | None]] = []

    def fake_verifier(
        _executor: ProtocolCellExecutor,
        cell: ScientificCell,
        _evidence: PreparedEvidenceCounts,
        condition_override: VerifierCondition | None = None,
    ) -> tuple[AdmissionState, tuple[tuple[ComparisonMetric, float | None], ...]]:
        calls.append((cell, condition_override))
        return AdmissionState.ADMITTED, ()

    monkeypatch.setattr(ProtocolCellExecutor, "_execute_verifier_robustness_cell", fake_verifier)
    evidence = PreparedEvidenceCounts(
        screen_target_count=0,
        reproduction_target_count=2000,
        reproduction_supported_count=2000,
        final_gate_adequate_domain_count=6,
    )

    def fake_load_counts(_root: Path, _target: DatasetClassToken) -> PreparedEvidenceCounts:
        return evidence

    monkeypatch.setattr(
        "fedsira.experiments.handlers.load_prepared_evidence_counts", fake_load_counts
    )
    executor = ProtocolCellExecutor(primary_prepared_root=Path("prepared-fixture"))
    cell = ScientificCell(
        experiment=BYZANTINE_BOUND_VIOLATION_NAME,
        method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
        condition=BoundCondition.ONE_BYZANTINE_VERIFIER_WITHIN_BOUND,
        master_seed=1103,
    )
    executor.execute_cell(cell)

    assert calls == [(cell, VerifierCondition.ONE_FALSE_POSITIVE)]


def test_byzantine_bound_routes_verifier_condition_through_direct_krum_reproducer(
    monkeypatch: MonkeyPatch,
) -> None:
    from fedsira.domain.enums import BoundCondition
    from fedsira.experiments.definitions import BYZANTINE_BOUND_VIOLATION_NAME

    calls: list[tuple[ScientificCell, ReproducerCondition | None]] = []

    def fake_reproducer(
        _executor: ProtocolCellExecutor,
        cell: ScientificCell,
        _evidence: PreparedEvidenceCounts,
        condition_override: ReproducerCondition | None = None,
    ) -> tuple[AdmissionState, tuple[tuple[ComparisonMetric, float | None], ...]]:
        calls.append((cell, condition_override))
        return AdmissionState.ADMITTED, ()

    monkeypatch.setattr(
        ProtocolCellExecutor, "_execute_reproducer_robustness_cell", fake_reproducer
    )
    evidence = PreparedEvidenceCounts(
        screen_target_count=0,
        reproduction_target_count=2000,
        reproduction_supported_count=2000,
        final_gate_adequate_domain_count=6,
    )

    def fake_load_counts(_root: Path, _target: DatasetClassToken) -> PreparedEvidenceCounts:
        return evidence

    monkeypatch.setattr(
        "fedsira.experiments.handlers.load_prepared_evidence_counts", fake_load_counts
    )
    executor = ProtocolCellExecutor(primary_prepared_root=Path("prepared-fixture"))
    cell = ScientificCell(
        experiment=BYZANTINE_BOUND_VIOLATION_NAME,
        method=BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM,
        condition=BoundCondition.TWO_BYZANTINE_VERIFIERS_ABOVE_BOUND,
        master_seed=1103,
    )
    executor.execute_cell(cell)

    assert calls == [(cell, ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR)]


def test_model_replacement_condition_resolves_attack_scope(monkeypatch: MonkeyPatch) -> None:
    from fedsira.datasets.nbaiot.schema import NBAIOT_TRIGGER_FEATURES

    def fake_feature_names(_root: Path) -> tuple[FeatureName, ...]:
        return tuple(NBAIOT_TRIGGER_FEATURES)

    monkeypatch.setattr(
        "fedsira.experiments.handlers.prepared_feature_names",
        fake_feature_names,
    )
    executor = ProtocolCellExecutor(primary_prepared_root=Path("prepared-fixture"))
    cell = ScientificCell(
        experiment=COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
        method=BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM,
        condition=ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR,
        master_seed=1103,
    )

    scope = executor.backdoor_scope_for_cell(cell)
    source_scope = executor.source_backdoor_scope_for_cell(cell)

    assert scope is not None
    assert scope.poison_fraction == 0.1
    assert scope.trigger_feature_indices == tuple(range(len(NBAIOT_TRIGGER_FEATURES)))
    assert source_scope is None


def test_source_backdoor_scope_is_separate_from_reproducer_attack_scope(
    monkeypatch: MonkeyPatch,
) -> None:
    from fedsira.datasets.nbaiot.schema import NBAIOT_TRIGGER_FEATURES

    def fake_feature_names(_root: Path) -> tuple[FeatureName, ...]:
        return tuple(NBAIOT_TRIGGER_FEATURES)

    monkeypatch.setattr(
        "fedsira.experiments.handlers.prepared_feature_names",
        fake_feature_names,
    )
    executor = ProtocolCellExecutor(primary_prepared_root=Path("prepared-fixture"))
    cell = ScientificCell(
        experiment=COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
        method=BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM,
        condition=ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
        master_seed=1103,
    )

    source_scope = executor.source_backdoor_scope_for_cell(cell)
    reproducer_scope = executor.backdoor_scope_for_cell(cell)

    assert source_scope is not None
    assert source_scope.poison_fraction == 0.05
    assert reproducer_scope == source_scope
