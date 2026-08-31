from pathlib import Path

import pytest

from fedsira.domain.enums import ExperimentLifecycleState
from fedsira.experiments.definitions import (
    BASELINE_IMPLEMENTATION_VALIDATION_NAME,
    DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,
    PROTOCOL_INVARIANT_VALIDATION_NAME,
)
from fedsira.experiments.planning import ScientificCell
from fedsira.experiments.runner import (
    PreparedEvidenceCounts,
    ProtocolCellExecutor,
)
from fedsira.experiments.validation import run_data_and_domain_evidence_validation


def test_protocol_invariant_validation_cell_executes_smoke_invariants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "fedsira.experiments.validation.smoke_record_path", lambda: tmp_path / "smoke.json"
    )
    executor = ProtocolCellExecutor()
    cell = ScientificCell(
        experiment=PROTOCOL_INVARIANT_VALIDATION_NAME,
        method=PROTOCOL_INVARIANT_VALIDATION_NAME,
        condition="aggregate",
        master_seed=900001,
    )
    outcome = executor.execute_cell(cell)
    assert outcome.terminal_state is ExperimentLifecycleState.COMPLETED
    metrics = dict(outcome.metrics)
    assert metrics["terminal-state"] == 1.0


def test_data_and_domain_evidence_validation_cell_is_invalid_without_prepared_evidence(
    tmp_path: Path,
) -> None:
    executor = ProtocolCellExecutor(primary_prepared_root=tmp_path / "missing")
    cell = ScientificCell(
        experiment=DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,
        method=DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,
        condition="primary",
        master_seed=900001,
    )
    outcome = executor.execute_cell(cell)
    assert outcome.terminal_state is ExperimentLifecycleState.INVALID


def test_data_and_domain_evidence_validation_rejects_insufficient_counts() -> None:
    with pytest.raises(ValueError, match="reproduction-target evidence"):
        run_data_and_domain_evidence_validation(0, 0, 0)


def test_baseline_implementation_validation_dispatches_to_baseline_cell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[str] = []

    def fake_baseline(
        self: ProtocolCellExecutor,
        cell: ScientificCell,
        evidence: PreparedEvidenceCounts,
    ) -> tuple[object, tuple[object, ...]]:
        called.append(cell.method)
        from fedsira.domain.enums import ClaimState

        return ClaimState.ADMITTED, ()

    monkeypatch.setattr(ProtocolCellExecutor, "_execute_baseline_cell", fake_baseline)
    evidence = PreparedEvidenceCounts(
        screen_target_count=1,
        reproduction_target_count=2000,
        reproduction_supported_count=2000,
        final_gate_adequate_domain_count=6,
    )

    def _prepared_counts(prepared_root: Path, target_class_token: str) -> PreparedEvidenceCounts:
        return evidence

    monkeypatch.setattr(
        "fedsira.experiments.runner.load_prepared_evidence_counts",
        _prepared_counts,
    )
    executor = ProtocolCellExecutor()
    cell = ScientificCell(
        experiment=BASELINE_IMPLEMENTATION_VALIDATION_NAME,
        method="Local-Only Reference",
        condition="Legitimate Target Capability",
        master_seed=900001,
    )
    outcome = executor.execute_cell(cell)
    assert called == ["Local-Only Reference"]
    assert outcome.terminal_state is ExperimentLifecycleState.COMPLETED
