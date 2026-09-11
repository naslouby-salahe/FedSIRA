from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from fedsira.artifacts.provenance import ArtifactManifest
from fedsira.domain.enums import (
    AdmissionState,
    ArtifactLifecycleState,
    ExperimentLifecycleState,
)
from fedsira.domain.types import (
    CheckpointIdentity,
    DatasetColumnName,
    ExperimentName,
    FrozenDomainModel,
    ReportVerificationFailure,
    ScientificCellCount,
    TableName,
    TextValue,
    VerificationPassed,
)
from fedsira.experiments.definitions import (
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    SECONDARY_DATASET_GENERALIZATION_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    DescriptiveScientificMetric,
    VerifierCondition,
)
from fedsira.experiments.execution import (
    TERMINAL_EXPERIMENT_STATES,
    CellExecutionOutcome,
    ExperimentExecutionResult,
    PersistedExecutionRecord,
)
from fedsira.experiments.planning import ExperimentPlan, PlannedExperiment
from fedsira.reporting.figures import (
    EfficiencyMetricObservation,
    EvidenceStateFraction,
)


class ExperimentTerminalCount(FrozenDomainModel):
    experiment: ExperimentName
    count: ScientificCellCount


class ExperimentLifecycleRecord(FrozenDomainModel):
    experiment: ExperimentName
    state: ExperimentLifecycleState


class CompletenessVerificationResult(FrozenDomainModel):
    passed: VerificationPassed
    failures: tuple[ReportVerificationFailure, ...]


def terminal_count_for_planned_experiment(
    planned: PlannedExperiment,
    records: tuple[PersistedExecutionRecord, ...],
) -> ScientificCellCount:
    planned_keys = frozenset(cell.semantic_key for cell in planned.cells)
    return sum(record.semantic_key in planned_keys for record in records)


def _terminal_count(
    records: tuple[ExperimentTerminalCount, ...],
    experiment: ExperimentName,
) -> ScientificCellCount:
    for record in records:
        if record.experiment == experiment:
            return record.count
    return 0


def _lifecycle_state(
    records: tuple[ExperimentLifecycleRecord, ...],
    experiment: ExperimentName,
) -> ExperimentLifecycleState | None:
    for record in records:
        if record.experiment == experiment:
            return record.state
    return None


def verify_planned_cell_count_satisfied(
    plan: ExperimentPlan,
    terminal_record_counts: tuple[ExperimentTerminalCount, ...],
) -> CompletenessVerificationResult:
    failures: list[ReportVerificationFailure] = []
    for planned in plan.experiments:
        expected = len(planned.cells)
        observed = _terminal_count(terminal_record_counts, planned.definition.name)
        if observed != expected:
            failures.append(
                f"{planned.definition.name}: expected {expected} terminal cell records, "
                f"found {observed}"
            )
    return CompletenessVerificationResult(passed=not failures, failures=tuple(failures))


def verify_experiments_completed(
    lifecycle_states: tuple[ExperimentLifecycleRecord, ...],
    expected_experiments: tuple[ExperimentName, ...],
) -> CompletenessVerificationResult:
    failures: list[ReportVerificationFailure] = []
    for experiment in expected_experiments:
        state = _lifecycle_state(lifecycle_states, experiment)
        if state is not ExperimentLifecycleState.COMPLETED:
            failures.append(
                f"{experiment}: lifecycle state is "
                f"{state.value if state is not None else 'unknown'}, expected Completed"
            )
    return CompletenessVerificationResult(passed=not failures, failures=tuple(failures))


def verify_experiments_reached_terminal_state(
    lifecycle_states: tuple[ExperimentLifecycleRecord, ...],
    expected_experiments: tuple[ExperimentName, ...],
) -> CompletenessVerificationResult:
    failures: list[ReportVerificationFailure] = []
    for experiment in expected_experiments:
        state = _lifecycle_state(lifecycle_states, experiment)
        if state is None or state not in TERMINAL_EXPERIMENT_STATES:
            failures.append(
                f"{experiment}: lifecycle state is "
                f"{state.value if state is not None else 'unknown'}, not terminal"
            )
    return CompletenessVerificationResult(passed=not failures, failures=tuple(failures))


def verify_artifact_manifest_dependencies(
    invalid_artifact_identities: tuple[CheckpointIdentity, ...],
) -> CompletenessVerificationResult:
    return CompletenessVerificationResult(
        passed=not invalid_artifact_identities,
        failures=tuple(invalid_artifact_identities),
    )


def artifact_manifest_dependency_failures(
    manifests: tuple[ArtifactManifest, ...],
) -> tuple[CheckpointIdentity, ...]:
    identities = frozenset(manifest.identity for manifest in manifests)
    return tuple(
        manifest.identity
        for manifest in manifests
        if (
            manifest.lifecycle_state is not ArtifactLifecycleState.COMPLETE
            or any(upstream not in identities for upstream in manifest.upstream_identities)
        )
    )


TABLE_HEADERS: tuple[tuple[TableName, tuple[DatasetColumnName, ...]], ...] = (
    (
        "Cell Metrics",
        (
            "experiment",
            "method",
            "condition",
            "master_seed",
            "repetition",
            "terminal_state",
            "metric",
            "value",
        ),
    ),
    (
        "Statistical Summary",
        (
            "comparison_family",
            "comparison",
            "metric",
            "direction",
            "test_kind",
            "materiality_direction",
            "margin",
            "n_pairs",
            "mean_difference",
            "median_difference",
            "paired_dz",
            "raw_p",
            "holm_p",
            "confidence_interval_95",
            "materiality_threshold",
            "statistical_pass",
            "materiality_pass",
            "final_comparison_state",
        ),
    ),
)


def table_header(name: TableName) -> tuple[DatasetColumnName, ...]:
    for registered_name, header in TABLE_HEADERS:
        if registered_name == name:
            return header
    raise KeyError(f"no mandatory rendered-table schema is registered for {name!r}")


def _table_header(path: Path) -> tuple[DatasetColumnName, ...] | None:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    rows = tuple(csv.reader(StringIO(text)))
    if not rows:
        return None
    return tuple(rows[0])


def verify_rendered_table(
    path: Path,
    expected_header: tuple[DatasetColumnName, ...],
    required_row_identities: frozenset[tuple[TextValue, ...]],
) -> tuple[ReportVerificationFailure, ...]:
    name = path.stem
    if not path.is_file():
        return (f"{name}: rendered table is missing",)
    header = _table_header(path)
    if header is None:
        return (f"{name}: rendered table is empty",)
    if header != expected_header:
        return (f"{name}: rendered table header does not match the mandatory schema",)
    body = tuple(csv.reader(StringIO(path.read_text(encoding="utf-8").strip())))[1:]
    if not body:
        return (f"{name}: rendered table has no evidence rows",)
    identity_column_count = (
        len(next(iter(required_row_identities))) if required_row_identities else 0
    )
    observed_identities = frozenset(
        tuple(row[:identity_column_count]) for row in body if len(row) >= identity_column_count
    )
    missing = tuple(sorted(required_row_identities - observed_identities))
    if missing:
        return (f"{name}: rendered table omits required evidence rows {list(missing)}",)
    return ()


def verify_mandatory_figure_source_data(
    result: ExperimentExecutionResult,
    evidence_trajectory: tuple[EvidenceStateFraction, ...],
    telemetry: tuple[EfficiencyMetricObservation, ...],
    outcomes: tuple[CellExecutionOutcome, ...],
) -> tuple[ReportVerificationFailure, ...]:
    failures: list[ReportVerificationFailure] = []
    completed = tuple(outcome for outcome in outcomes if outcome.completed)
    if result.experiment == EVIDENCE_SCARCITY_AND_DORMANCY_NAME:
        schedules = frozenset(outcome.cell.condition for outcome in completed)
        covered = frozenset(observation.condition for observation in evidence_trajectory)
        if not schedules or not schedules.issubset(covered):
            failures.append(
                f"{result.experiment}: Evidence-Arrival State Trajectory source data is "
                "missing seed schedules"
            )
        elif not any(
            observation.state is AdmissionState.VERIFICATION_PENDING
            for observation in evidence_trajectory
        ):
            failures.append(
                f"{result.experiment}: Evidence-Arrival State Trajectory omits "
                "verification-pending behaviour"
            )
    if result.experiment == EFFICIENCY_MEASUREMENT_NAME:
        expected_metrics = frozenset(
            (
                DescriptiveScientificMetric.WALL_CLOCK_SECONDS.value,
                DescriptiveScientificMetric.COMMUNICATION_BYTES.value,
                DescriptiveScientificMetric.PEAK_GPU_MEMORY_BYTES.value,
            )
        )
        observed_metrics = frozenset(observation.metric for observation in telemetry)
        missing_metrics = tuple(
            sorted(metric for metric in expected_metrics if metric not in observed_metrics)
        )
        if missing_metrics:
            failures.append(
                f"{result.experiment}: Efficiency Profile source data omits {list(missing_metrics)}"
            )
        if not any(outcome.cell.repetition is not None for outcome in completed):
            failures.append(
                f"{result.experiment}: Efficiency Profile has no repetition-owned measurements"
            )
    if result.experiment == COMPROMISED_VERIFIER_ROBUSTNESS_NAME:
        conditions = frozenset(outcome.cell.condition for outcome in completed)
        required = frozenset(
            (
                VerifierCondition.ONE_FALSE_POSITIVE.value,
                VerifierCondition.ONE_FALSE_NEGATIVE.value,
            )
        )
        if not required.issubset(conditions):
            failures.append(
                f"{result.experiment}: Compromised-Verifier Boundary omits false-positive or "
                "false-negative source conditions"
            )
    if result.experiment == COMPROMISED_REPRODUCER_ROBUSTNESS_NAME and not completed:
        failures.append(
            f"{result.experiment}: Compromised-Reproducer Boundary has no completed source data"
        )
    if result.experiment == PRIMARY_CONFIRMATORY_EVALUATION_NAME and not result.comparison_results:
        failures.append(
            f"{result.experiment}: Primary Security-Utility Tradeoff has no paired evidence"
        )
    if result.experiment == SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME and not completed:
        failures.append(
            f"{result.experiment}: Useful Backdoored Source has no completed source data"
        )
    if result.experiment == SECONDARY_DATASET_GENERALIZATION_NAME and not result.comparison_results:
        failures.append(f"{result.experiment}: Secondary Generalization has no paired evidence")
    return tuple(failures)
