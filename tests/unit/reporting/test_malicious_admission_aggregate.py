from pathlib import Path

import pandas
import pytest

from fedsira.domain.enums import (
    ComparisonMetric,
    CoreMethodIdentity,
    ExperimentLifecycleState,
)
from fedsira.domain.models import ScientificCell
from fedsira.evaluation.metrics import malicious_admission_rate
from fedsira.experiments.definitions import PRIMARY_CONFIRMATORY_EVALUATION_NAME
from fedsira.experiments.engine import (
    CellExecutionOutcome,
    ExecutionProvenance,
    ExperimentExecutionResult,
)
from fedsira.reporting.export import materialize_experiment_evidence


def _result(values: tuple[float, ...]) -> ExperimentExecutionResult:
    seeds = (1103, 1217, 1321)
    outcomes = tuple(
        CellExecutionOutcome(
            cell=ScientificCell(
                experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
                condition="Legitimate Unsupported Capability",
                master_seed=seeds[index],
            ),
            terminal_state=ExperimentLifecycleState.COMPLETED,
            failure=None,
            metrics=((ComparisonMetric.MALICIOUS_ADMISSION, value),),
        )
        for index, value in enumerate(values)
    )
    return ExperimentExecutionResult(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        lifecycle_state=ExperimentLifecycleState.COMPLETED,
        outcomes=outcomes,
        provenance=ExecutionProvenance(
            configuration_digest="a" * 64,
            code_revision=None,
            dataset_manifest_hash="b" * 64,
        ),
    )


def test_aggregate_malicious_admission_matches_the_shipped_rate(tmp_path: Path) -> None:
    indicators = (True, False, True)
    materialized = materialize_experiment_evidence(
        _result(tuple(float(indicator) for indicator in indicators)),
        tmp_path / "metrics",
        tmp_path / "telemetry",
    )
    aggregate_rows = pandas.read_parquet(materialized.paths[2])
    rate = malicious_admission_rate(indicators).value
    assert aggregate_rows.loc[0, "mean_value"] == rate
    assert aggregate_rows.loc[0, "seed_count"] == len(indicators)


def test_aggregate_malicious_admission_rejects_a_fractional_indicator(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="binary admission-rate indicators"):
        materialize_experiment_evidence(
            _result((0.5,)),
            tmp_path / "metrics",
            tmp_path / "telemetry",
        )


def test_aggregate_malicious_admission_rejects_compensating_fractions(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="binary admission-rate indicators"):
        materialize_experiment_evidence(
            _result((0.5, 1.5)),
            tmp_path / "metrics",
            tmp_path / "telemetry",
        )
