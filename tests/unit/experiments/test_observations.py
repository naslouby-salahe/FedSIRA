from fedsira.domain.enums import (
    ComparisonMetric,
    CoreMethodIdentity,
    ExperimentLifecycleState,
    ExperimentName,
)
from fedsira.domain.models import ScientificCell
from fedsira.experiments.engine import CellExecutionOutcome
from fedsira.experiments.observations import outcome_metric_mean, outcome_metric_values


def _outcome(seed: int, state: ExperimentLifecycleState, value: float) -> CellExecutionOutcome:
    return CellExecutionOutcome(
        cell=ScientificCell(
            experiment=ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION,
            method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
            condition="Legitimate Unsupported Capability",
            master_seed=seed,
        ),
        terminal_state=state,
        failure=None,
        metrics=((ComparisonMetric.TARGET_F1, value),),
    )


def test_outcome_metric_summary_filters_failures_and_orders_by_seed() -> None:
    outcomes = (
        _outcome(3, ExperimentLifecycleState.COMPLETED, 0.8),
        _outcome(1, ExperimentLifecycleState.FAILED, 1.0),
        _outcome(2, ExperimentLifecycleState.COMPLETED, 0.4),
    )

    assert outcome_metric_values(
        outcomes,
        ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION,
        CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
        "Legitimate Unsupported Capability",
        ComparisonMetric.TARGET_F1,
    ) == (0.4, 0.8)
    mean = outcome_metric_mean(
        outcomes,
        ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION,
        CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
        "Legitimate Unsupported Capability",
        ComparisonMetric.TARGET_F1,
    )
    assert mean is not None
    assert abs(mean - 0.6) < 1e-12


def test_outcome_metric_summary_returns_none_without_completed_values() -> None:
    assert (
        outcome_metric_mean(
            (_outcome(1, ExperimentLifecycleState.FAILED, 0.8),),
            ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION,
            CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
            "Legitimate Unsupported Capability",
            ComparisonMetric.TARGET_F1,
        )
        is None
    )
