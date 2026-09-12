from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import cast

import pandas

from fedsira.artifacts.store import ArtifactManifest, InvalidArtifactReport
from fedsira.domain.enums import (
    AdmissionState,
    ArtifactDependencyKind,
    ArtifactLifecycleState,
    ExperimentLifecycleState,
)
from fedsira.domain.types import (
    ArtifactDigest,
    BooleanValue,
    CheckpointIdentity,
    ConditionName,
    DatasetColumnName,
    ExperimentName,
    FrozenDomainModel,
    RelativePathText,
    ReportVerificationFailure,
    ScientificCellCount,
    TableName,
    TextValue,
    VerificationPassed,
)
from fedsira.evaluation.comparison_evidence import comparison_evidence_failures
from fedsira.evaluation.comparisons import ComparisonMetric
from fedsira.experiments.definitions import (
    AGGREGATE_METRICS_PARQUET_NAME,
    BYZANTINE_BOUND_VIOLATION_NAME,
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    SECONDARY_DATASET_GENERALIZATION_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    STATE_TRAJECTORY_PARQUET_NAME,
    BoundCondition,
    DescriptiveScientificMetric,
    VerifierCondition,
)
from fedsira.experiments.engine import (
    TERMINAL_EXPERIMENT_STATES,
    CellExecutionOutcome,
    ExecutionRecordStore,
    ExperimentExecutionResult,
    PersistedExecutionRecord,
)
from fedsira.experiments.planning import ExperimentPlan, PlannedExperiment
from fedsira.reporting.figures import (
    EfficiencyMetricObservation,
    EvidenceStateFraction,
)
from fedsira.reporting.publication import read_table_figure_export
from fedsira.runtime import current_application_context


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


BOUND_WITHIN_CONDITIONS: tuple[ConditionName, ...] = (
    BoundCondition.ONE_BYZANTINE_REPRODUCER_WITHIN_BOUND.value,
    BoundCondition.ONE_BYZANTINE_VERIFIER_WITHIN_BOUND.value,
)


def verify_safe_dormancy(
    records: tuple[PersistedExecutionRecord, ...],
) -> CompletenessVerificationResult:
    thresholds = current_application_context().scientific_config.evidence_thresholds.safe_dormancy
    allowed = thresholds.maximum_permanent_singleton_admissions
    observed: list[CheckpointIdentity] = []
    for record in records:
        if record.experiment != EVIDENCE_SCARCITY_AND_DORMANCY_NAME:
            continue
        if record.terminal_state is not ExperimentLifecycleState.COMPLETED:
            continue
        for metric_name, metric_value in record.metrics:
            if metric_name != str(DescriptiveScientificMetric.PERMANENT_SINGLETON_ADMISSION):
                continue
            if metric_value == 1.0:  # TODO: should be constant
                observed.append(f"{record.semantic_key}: permanent singleton admission")
    if len(observed) > allowed:
        return CompletenessVerificationResult(passed=False, failures=tuple(observed))
    return CompletenessVerificationResult(passed=True, failures=())


def verify_report_export_currency(
    experiment: ExperimentName,
    source_data_identity: ArtifactDigest,
    experiment_root: Path,
    exported_paths: tuple[RelativePathText, ...],
) -> tuple[ReportVerificationFailure, ...]:
    payload = read_table_figure_export(experiment)
    if payload is None:
        return (f"{experiment}: report export artifact is absent",)
    failures: list[ReportVerificationFailure] = []
    if payload.source_data_identity != source_data_identity:
        failures.append(f"{experiment}: report export artifact is stale for its source data")
    if payload.exported_paths != exported_paths:
        failures.append(f"{experiment}: report export artifact does not name its own products")
    for relative in payload.exported_paths:
        if not (experiment_root / relative).is_file():
            failures.append(f"{experiment}: exported report product is missing: {relative}")
    return tuple(failures)


def verify_comparison_evidence_current(
    experiment_names: tuple[ExperimentName, ...],
    store: ExecutionRecordStore,
) -> CompletenessVerificationResult:
    failures: list[ReportVerificationFailure] = []
    for experiment in experiment_names:
        failures.extend(
            comparison_evidence_failures(experiment, store.read_all_outcomes(experiment))
        )
    return CompletenessVerificationResult(passed=not failures, failures=tuple(failures))


def verify_byzantine_operating_region(
    records: tuple[PersistedExecutionRecord, ...],
) -> CompletenessVerificationResult:
    evidence_thresholds = current_application_context().scientific_config.evidence_thresholds
    thresholds = evidence_thresholds.byzantine_operating_region
    max_admissions = thresholds.maximum_malicious_admissions_within_bound
    admissions: list[CheckpointIdentity] = []
    for record in records:
        if record.experiment != BYZANTINE_BOUND_VIOLATION_NAME:
            continue
        if record.condition not in BOUND_WITHIN_CONDITIONS:
            continue
        if record.terminal_state is not ExperimentLifecycleState.COMPLETED:
            continue
        for metric_name, metric_value in record.metrics:
            if metric_name != str(ComparisonMetric.MALICIOUS_ADMISSION):
                continue
            if metric_value == 1.0:  # TODO: should be constant
                admissions.append(f"{record.semantic_key}: malicious admission within bound")
    if len(admissions) > max_admissions:
        return CompletenessVerificationResult(passed=False, failures=tuple(admissions))
    return CompletenessVerificationResult(passed=True, failures=())


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
    invalid_manifests: tuple[InvalidArtifactReport, ...] = (),
) -> tuple[CheckpointIdentity, ...]:
    identities = frozenset(manifest.identity for manifest in manifests)
    unreadable = tuple(f"{report.manifest_path}: {report.failure}" for report in invalid_manifests)
    unresolved = tuple(
        f"{manifest.slot.family.value}/{manifest.slot.instance}: {manifest.identity} is "
        f"{manifest.lifecycle_state.value}"
        if manifest.lifecycle_state is not ArtifactLifecycleState.COMPLETE
        else f"{manifest.slot.family.value}/{manifest.slot.instance}: "
        f"{dependency.dependency} upstream {dependency.digest} is not a published artifact"
        for manifest in manifests
        for dependency in (
            tuple(manifest.dependencies)
            if manifest.lifecycle_state is not ArtifactLifecycleState.COMPLETE
            else tuple(
                item
                for item in manifest.dependencies
                if item.kind is ArtifactDependencyKind.ARTIFACT
            )
        )
        if manifest.lifecycle_state is not ArtifactLifecycleState.COMPLETE
        or dependency.digest not in identities
    )
    return (*unreadable, *unresolved)


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


def metric_artifact_is_semantically_complete(
    path: Path,
    result: ExperimentExecutionResult,
) -> BooleanValue:
    if not path.is_file():
        return False
    frame = pandas.read_parquet(path)
    if path.name == STATE_TRAJECTORY_PARQUET_NAME:
        required_columns = frozenset(
            (
                "experiment",
                "method",
                "condition",
                "master_seed",
                "logical_evidence_cycle",
                "admission_state",
            )
        )
        if not required_columns.issubset(frame.columns) or frame.empty:
            return False
        experiment_rows = frame[frame["experiment"] == result.experiment]
        expected_cells = frozenset(
            (outcome.cell.method, outcome.cell.condition, outcome.cell.master_seed)
            for outcome in result.outcomes
        )
        observed_cells = frozenset(
            (row.method, row.condition, row.master_seed) for row in experiment_rows.itertuples()
        )
        return expected_cells.issubset(observed_cells) and all(
            experiment_rows["admission_state"].notna().tolist()
        )
    required_columns = (
        frozenset(
            ("experiment", "method", "condition", "metric", "observation_count", "mean_value")
        )
        if path.name == AGGREGATE_METRICS_PARQUET_NAME
        else frozenset(("experiment", "method", "condition", "master_seed", "terminal_state"))
    )
    if not required_columns.issubset(frame.columns) or frame.empty:
        return False
    experiment_rows = frame[frame["experiment"] == result.experiment]
    if experiment_rows.empty:
        return False
    if path.name == AGGREGATE_METRICS_PARQUET_NAME:
        expected_conditions = frozenset(
            (outcome.cell.method, outcome.cell.condition) for outcome in result.outcomes
        )
        observed_conditions = frozenset(
            (row.method, row.condition) for row in experiment_rows.itertuples()
        )
        return expected_conditions.issubset(observed_conditions) and all(
            (experiment_rows["observation_count"] > 0).tolist()
        )
    terminal_state_values = cast(list[str], experiment_rows["terminal_state"].tolist())
    recorded_terminal_states = frozenset(
        ExperimentLifecycleState(state) for state in terminal_state_values
    )
    if recorded_terminal_states != frozenset((ExperimentLifecycleState.COMPLETED,)):
        return False
    expected_cells = frozenset(
        (outcome.cell.method, outcome.cell.condition, outcome.cell.master_seed)
        for outcome in result.outcomes
    )
    observed_cells = frozenset(
        (row.method, row.condition, row.master_seed) for row in experiment_rows.itertuples()
    )
    return expected_cells.issubset(observed_cells)
