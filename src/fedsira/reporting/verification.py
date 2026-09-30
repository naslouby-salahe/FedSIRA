from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import cast

import pandas

from fedsira.artifacts.store import ArtifactManifest, InvalidArtifactReport
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER
from fedsira.domain.enums import (
    AdmissionState,
    ArtifactDependencyKind,
    ArtifactLifecycleState,
    BoundCondition,
    CoreMethodIdentity,
    DescriptiveScientificMetric,
    EvidenceArrivalSchedule,
    ExperimentLifecycleState,
    ExperimentName,
    ReportCellLiteral,
    ReportColumnName,
    TableName,
    VerifierCondition,
)
from fedsira.domain.models import ScientificCell
from fedsira.domain.types import (
    ArtifactDigest,
    BooleanValue,
    CellIdentityMatches,
    CheckpointIdentity,
    EvidenceCycleIndex,
    FrozenDomainModel,
    RelativePathText,
    ReportColumnText,
    ReportRowIdentity,
    ReportVerificationFailure,
    ScenarioName,
    ScientificCellCount,
    ScientificCellSemanticKey,
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
    SEED_METRICS_PARQUET_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    STATE_TRAJECTORY_FRACTIONS_PARQUET_NAME,
    STATE_TRAJECTORY_PARQUET_NAME,
)
from fedsira.experiments.engine import (
    TERMINAL_EXPERIMENT_STATES,
    CellExecutionOutcome,
    ExecutionRecordStore,
    ExperimentExecutionResult,
    PersistedExecutionRecord,
)
from fedsira.experiments.observations import measurement_cycles
from fedsira.experiments.planning import ExperimentPlan, PlannedExperiment
from fedsira.protocol.rules import compute_t_evidence
from fedsira.reporting.figures import (
    EfficiencyMetricObservation,
)
from fedsira.reporting.publication import read_table_figure_export
from fedsira.reporting.state_trajectory import (
    EvidenceStateFraction,
    read_state_trajectory_fractions,
)
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


BOUND_WITHIN_CONDITIONS: tuple[ScenarioName, ...] = (
    BoundCondition.ONE_BYZANTINE_REPRODUCER_WITHIN_BOUND,
    BoundCondition.ONE_BYZANTINE_VERIFIER_WITHIN_BOUND,
)


def verify_safe_dormancy(
    planned: PlannedExperiment,
    records: tuple[PersistedExecutionRecord, ...],
) -> CompletenessVerificationResult:
    if planned.definition.name != EVIDENCE_SCARCITY_AND_DORMANCY_NAME:
        return CompletenessVerificationResult(
            passed=False,
            failures=("Safe dormancy: supplied plan is for a different experiment",),
        )
    thresholds = current_application_context().scientific_config.evidence_thresholds.safe_dormancy
    allowed = thresholds.maximum_permanent_singleton_admissions
    config = current_application_context().scientific_config
    cycles = measurement_cycles(config.protocol.resource_horizon)
    failures: list[ReportVerificationFailure] = []
    planned_cells = tuple((cell.semantic_key, cell) for cell in planned.cells)
    if len({semantic_key for semantic_key, _cell in planned_cells}) != len(planned.cells):
        failures.append("Safe dormancy: planned experiment contains duplicate semantic cells")

    singleton_admissions = 0
    for semantic_key, cell in planned_cells:
        matching = _records_for_semantic_key(
            records, EVIDENCE_SCARCITY_AND_DORMANCY_NAME, semantic_key
        )
        if len(matching) != 1:
            failures.append(
                f"{semantic_key}: expected exactly one current safe-dormancy record, "
                f"found {len(matching)}"
            )
            continue
        record = matching[0]
        if not _record_matches_cell(record, cell):
            failures.append(f"{semantic_key}: persisted safe-dormancy identity does not match plan")
            continue
        if record.terminal_state is not ExperimentLifecycleState.COMPLETED:
            failures.append(f"{semantic_key}: safe-dormancy outcome is not Completed")
            continue

        singleton_values = tuple(
            value
            for name, value in record.metrics
            if name == DescriptiveScientificMetric.PERMANENT_SINGLETON_ADMISSION
        )
        if len(singleton_values) != 1 or singleton_values[0] not in (0.0, 1.0):
            failures.append(f"{semantic_key}: missing or invalid permanent-singleton outcome")
        elif singleton_values[0] == 1.0:
            singleton_admissions += 1

        failures.extend(_safe_dormancy_trajectory_failures(cell, record, cycles))

    if allowed != 0:
        failures.append(
            "Safe dormancy: configured permanent-singleton admission maximum must be zero"
        )
    if singleton_admissions != 0:
        failures.append(
            f"Permanent Singleton: observed {singleton_admissions} admissions, expected zero"
        )
    return CompletenessVerificationResult(passed=not failures, failures=tuple(failures))


def _safe_dormancy_trajectory_failures(
    cell: ScientificCell,
    record: PersistedExecutionRecord,
    cycles: tuple[EvidenceCycleIndex, ...],
) -> tuple[ReportVerificationFailure, ...]:
    protocol = current_application_context().scientific_config.protocol
    schedule = EvidenceArrivalSchedule(cell.condition)
    t_evidence = compute_t_evidence(
        schedule,
        tuple(NBAIOT_DOMAIN_ORDER[1:]),
        cycles,
        protocol.synthesis.committee_size,
        protocol.final_gate.minimum_adequate_non_source_domains,
    )
    if not record.state_trajectory:
        return (f"{cell.semantic_key}: missing admission-state trajectory",)
    admitted = tuple(
        item for item in record.state_trajectory if item.state is AdmissionState.ADMITTED
    )
    if schedule is EvidenceArrivalSchedule.PERMANENT_SINGLETON or t_evidence is None:
        return (
            (f"{cell.semantic_key}: admission occurred without sufficient evidence",)
            if admitted
            else ()
        )
    failures: list[ReportVerificationFailure] = []
    if any(item.cycle < t_evidence for item in admitted):
        failures.append(f"{cell.semantic_key}: admission occurred before T_evidence={t_evidence}")
    if schedule in (
        EvidenceArrivalSchedule.GRADUAL_TO_QUORUM,
        EvidenceArrivalSchedule.IMMEDIATE_QUORUM,
    ) and not any(item.cycle >= t_evidence for item in admitted):
        failures.append(
            f"{cell.semantic_key}: eligible evidence arrived at T_evidence={t_evidence} "
            "but the protocol never admitted"
        )
    return tuple(failures)


def verify_report_export_currency(
    experiment: ExperimentName | None,
    source_data_identity: ArtifactDigest,
    experiment_root: Path,
    exported_paths: tuple[RelativePathText, ...],
) -> tuple[ReportVerificationFailure, ...]:
    payload = read_table_figure_export(experiment)
    scope = experiment or "project summary"
    if payload is None:
        return (f"{scope}: report export artifact is absent",)
    failures: list[ReportVerificationFailure] = []
    if payload.source_data_identity != source_data_identity:
        failures.append(f"{scope}: report export artifact is stale for its source data")
    if payload.exported_paths != exported_paths:
        failures.append(f"{scope}: report export artifact does not name its own products")
    for relative in payload.exported_paths:
        candidate = (experiment_root / relative).resolve()
        if experiment_root.resolve() not in candidate.parents or not candidate.is_file():
            failures.append(
                f"{scope}: exported report product is missing or outside its root: {relative}"
            )
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
    planned: PlannedExperiment,
    records: tuple[PersistedExecutionRecord, ...],
) -> CompletenessVerificationResult:
    if planned.definition.name != BYZANTINE_BOUND_VIOLATION_NAME:
        return CompletenessVerificationResult(
            passed=False,
            failures=("Byzantine operating region: supplied plan is for a different experiment",),
        )
    scientific_config = current_application_context().scientific_config
    thresholds = scientific_config.evidence_thresholds.byzantine_operating_region
    technical_completion = scientific_config.metrics_and_statistics.technical_completion
    minimum_complete_seeds = technical_completion.minimum_complete_pairs_for_inference
    if thresholds.maximum_malicious_admissions_within_bound != 0:
        return CompletenessVerificationResult(
            passed=False,
            failures=(
                "Byzantine operating region: within-bound malicious admissions must be zero",
            ),
        )
    failures: list[ReportVerificationFailure] = []
    required_metrics = (
        ComparisonMetric.MALICIOUS_ADMISSION,
        ComparisonMetric.LEGITIMATE_ADMISSION,
        ComparisonMetric.ATTACK_SUCCESS_RATE,
        ComparisonMetric.TARGET_F1,
    )
    for condition in BOUND_WITHIN_CONDITIONS:
        cells = tuple(
            cell
            for cell in planned.cells
            if cell.method == CoreMethodIdentity.RESOLVED_FEDSIRA_CORE
            and cell.condition == condition
        )
        unique_cells = tuple((cell.semantic_key, cell) for cell in cells)
        if len({semantic_key for semantic_key, _cell in unique_cells}) != len(cells):
            failures.append(f"{condition}: plan contains duplicate resolved-core seed cells")
        complete_count = 0
        if len(unique_cells) < minimum_complete_seeds:
            failures.append(
                f"{condition}: plan has {len(unique_cells)} resolved-core seed cells; "
                f"at least {minimum_complete_seeds} required"
            )
        for semantic_key, cell in unique_cells:
            matching = _records_for_semantic_key(
                records, BYZANTINE_BOUND_VIOLATION_NAME, semantic_key
            )
            if len(matching) != 1:
                if len(matching) > 1:
                    failures.append(f"{cell.semantic_key}: duplicate Byzantine evidence records")
                continue
            failure = _byzantine_cell_evidence_failure(matching[0], cell, required_metrics)
            if failure is not None:
                failures.append(failure)
                continue
            complete_count += 1
            malicious_admission = next(
                value
                for name, value in matching[0].metrics
                if name == ComparisonMetric.MALICIOUS_ADMISSION
            )
            if malicious_admission != 0.0:
                failures.append(f"{cell.semantic_key}: malicious admission occurred within bound")
        if complete_count < minimum_complete_seeds:
            failures.append(
                f"{condition}: only {complete_count} complete resolved-core seed cells; "
                f"at least {minimum_complete_seeds} required"
            )
    return CompletenessVerificationResult(passed=not failures, failures=tuple(failures))


def _byzantine_cell_evidence_failure(
    record: PersistedExecutionRecord,
    cell: ScientificCell,
    required_metrics: tuple[ComparisonMetric, ...],
) -> ReportVerificationFailure | None:
    if not _record_matches_cell(record, cell):
        return f"{cell.semantic_key}: persisted Byzantine identity does not match plan"
    if record.terminal_state is not ExperimentLifecycleState.COMPLETED:
        return f"{record.semantic_key}: Byzantine cell is not Completed"
    for metric in required_metrics:
        values = tuple(value for name, value in record.metrics if name == metric)
        if len(values) != 1 or values[0] is None or not 0.0 <= values[0] <= 1.0:
            return f"{record.semantic_key}: missing or invalid {metric} evidence"
    return None


def _record_matches_cell(
    record: PersistedExecutionRecord, cell: ScientificCell
) -> CellIdentityMatches:
    return (
        record.semantic_key == cell.semantic_key
        and record.experiment == cell.experiment
        and record.method == cell.method
        and record.condition == cell.condition
        and record.master_seed == cell.master_seed
        and record.repetition == cell.repetition
    )


def _records_for_semantic_key(
    records: tuple[PersistedExecutionRecord, ...],
    experiment: ExperimentName,
    semantic_key: ScientificCellSemanticKey,
) -> tuple[PersistedExecutionRecord, ...]:
    return tuple(
        record
        for record in records
        if record.experiment == experiment and record.semantic_key == semantic_key
    )


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
                f"{state if state is not None else ReportCellLiteral.UNKNOWN}, expected Completed"
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
                f"{state if state is not None else ReportCellLiteral.UNKNOWN}, not terminal"
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
    unresolved: list[CheckpointIdentity] = []
    for manifest in manifests:
        slot_identity = f"{manifest.slot.family.value}/{manifest.slot.instance}"
        if manifest.lifecycle_state is not ArtifactLifecycleState.COMPLETE:
            unresolved.append(
                f"{slot_identity}: {manifest.identity} is {manifest.lifecycle_state.value}"
            )
            continue
        unresolved.extend(
            f"{slot_identity}: {dependency.dependency} upstream {dependency.digest} "
            "is not a published artifact"
            for dependency in manifest.dependencies
            if dependency.kind is ArtifactDependencyKind.ARTIFACT
            and dependency.digest not in identities
        )
    return (*unreadable, *unresolved)


TABLE_HEADERS: tuple[tuple[TableName, tuple[ReportColumnText, ...]], ...] = (
    (
        TableName.CELL_METRICS,
        (
            ReportColumnName.EXPERIMENT,
            ReportColumnName.METHOD,
            ReportColumnName.CONDITION,
            ReportColumnName.MASTER_SEED,
            ReportColumnName.REPETITION,
            ReportColumnName.TERMINAL_STATE,
            ReportColumnName.METRIC,
            ReportColumnName.VALUE,
        ),
    ),
    (
        TableName.STATISTICAL_SUMMARY,
        (
            ReportColumnName.COMPARISON_FAMILY,
            ReportColumnName.COMPARISON,
            ReportColumnName.METRIC,
            ReportColumnName.DIRECTION,
            ReportColumnName.TEST_KIND,
            ReportColumnName.MATERIALITY_DIRECTION,
            ReportColumnName.MARGIN,
            ReportColumnName.N_PAIRS,
            ReportColumnName.MEAN_DIFFERENCE,
            ReportColumnName.MEDIAN_DIFFERENCE,
            ReportColumnName.PAIRED_DZ,
            ReportColumnName.RAW_P,
            ReportColumnName.HOLM_P,
            ReportColumnName.CONFIDENCE_INTERVAL_95,
            ReportColumnName.MATERIALITY_THRESHOLD,
            ReportColumnName.STATISTICAL_PASS,
            ReportColumnName.MATERIALITY_PASS,
            ReportColumnName.FINAL_COMPARISON_STATE,
        ),
    ),
)


def table_header(name: TableName) -> tuple[ReportColumnText, ...]:
    for registered_name, header in TABLE_HEADERS:
        if registered_name == name:
            return header
    raise KeyError(f"no mandatory rendered-table schema is registered for {name!r}")


def _table_header(path: Path) -> tuple[ReportColumnText, ...] | None:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    rows = tuple(csv.reader(StringIO(text)))
    if not rows:
        return None
    return tuple(rows[0])


def verify_rendered_table(
    path: Path,
    expected_header: tuple[ReportColumnText, ...],
    required_row_identities: frozenset[ReportRowIdentity],
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
                DescriptiveScientificMetric.WALL_CLOCK_SECONDS,
                DescriptiveScientificMetric.COMMUNICATION_BYTES,
                DescriptiveScientificMetric.PEAK_GPU_MEMORY_BYTES,
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
                VerifierCondition.ONE_FALSE_POSITIVE,
                VerifierCondition.ONE_FALSE_NEGATIVE,
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
    if path.name == SEED_METRICS_PARQUET_NAME:
        required_columns = frozenset(
            (
                ReportColumnName.EXPERIMENT,
                ReportColumnName.DATASET,
                ReportColumnName.METHOD,
                ReportColumnName.CONDITION,
                ReportColumnName.MASTER_SEED,
                ReportColumnName.METRIC,
                ReportColumnName.VALUE,
                ReportColumnName.CONFIGURATION_DIGEST,
                ReportColumnName.DATASET_MANIFEST_HASH,
                ReportColumnName.SOURCE_OBSERVATION_IDS,
                ReportColumnName.SOURCE_CELL_SEMANTIC_KEYS,
            )
        )
        if not required_columns.issubset(frame.columns) or frame.empty:
            return False
        experiment_rows = frame[frame[ReportColumnName.EXPERIMENT] == result.experiment]
        expected = frozenset(
            (
                outcome.cell.method,
                outcome.cell.condition,
                outcome.cell.master_seed,
                metric,
            )
            for outcome in result.outcomes
            if outcome.completed
            for metric, value in outcome.metrics
            if value is not None
        )
        observed = frozenset(
            (row.method, row.condition, row.master_seed, row.metric)
            for row in experiment_rows.itertuples()
        )
        return (
            bool(expected)
            and expected == observed
            and all(experiment_rows[ReportColumnName.VALUE].notna().tolist())
        )
    if path.name == STATE_TRAJECTORY_PARQUET_NAME:
        required_columns = frozenset(
            (
                ReportColumnName.EXPERIMENT,
                ReportColumnName.METHOD,
                ReportColumnName.CONDITION,
                ReportColumnName.MASTER_SEED,
                ReportColumnName.LOGICAL_EVIDENCE_CYCLE,
                ReportColumnName.ADMISSION_STATE,
            )
        )
        if not required_columns.issubset(frame.columns) or frame.empty:
            return False
        experiment_rows = frame[frame[ReportColumnName.EXPERIMENT] == result.experiment]
        expected_cells = frozenset(
            (outcome.cell.method, outcome.cell.condition, outcome.cell.master_seed)
            for outcome in result.outcomes
        )
        observed_cells = frozenset(
            (row.method, row.condition, row.master_seed) for row in experiment_rows.itertuples()
        )
        return expected_cells.issubset(observed_cells) and all(
            experiment_rows[ReportColumnName.ADMISSION_STATE].notna().tolist()
        )
    if path.name == STATE_TRAJECTORY_FRACTIONS_PARQUET_NAME:
        try:
            fractions = read_state_trajectory_fractions(path, result.experiment)
        except (TypeError, ValueError):
            return False
        completed_conditions = frozenset(
            outcome.cell.condition for outcome in result.outcomes if outcome.completed
        )
        return bool(fractions) and completed_conditions == frozenset(
            observation.condition for observation in fractions
        )
    required_columns = (
        frozenset(
            (
                ReportColumnName.EXPERIMENT,
                ReportColumnName.METHOD,
                ReportColumnName.CONDITION,
                ReportColumnName.METRIC,
                ReportColumnName.OBSERVATION_COUNT,
                ReportColumnName.SEED_COUNT,
                ReportColumnName.MEAN_VALUE,
                ReportColumnName.SAMPLE_STANDARD_DEVIATION,
                ReportColumnName.MEDIAN_VALUE,
                ReportColumnName.FIRST_QUARTILE,
                ReportColumnName.THIRD_QUARTILE,
                ReportColumnName.CONFIDENCE_INTERVAL_LOWER,
                ReportColumnName.CONFIDENCE_INTERVAL_UPPER,
            )
        )
        if path.name == AGGREGATE_METRICS_PARQUET_NAME
        else frozenset(
            (
                ReportColumnName.EXPERIMENT,
                ReportColumnName.METHOD,
                ReportColumnName.CONDITION,
                ReportColumnName.MASTER_SEED,
                ReportColumnName.TERMINAL_STATE,
            )
        )
    )
    if not required_columns.issubset(frame.columns) or frame.empty:
        return False
    experiment_rows = frame[frame[ReportColumnName.EXPERIMENT] == result.experiment]
    if experiment_rows.empty:
        return False
    if path.name == AGGREGATE_METRICS_PARQUET_NAME:
        expected_conditions = frozenset(
            (outcome.cell.method, outcome.cell.condition) for outcome in result.outcomes
        )
        observed_conditions = frozenset(
            (row.method, row.condition) for row in experiment_rows.itertuples()
        )
        ci_lower = cast(
            "pandas.Series[float]",
            experiment_rows[ReportColumnName.CONFIDENCE_INTERVAL_LOWER],
        )
        ci_upper = cast(
            "pandas.Series[float]",
            experiment_rows[ReportColumnName.CONFIDENCE_INTERVAL_UPPER],
        )
        ci_pair_is_valid = (ci_lower.isna() & ci_upper.isna()) | (
            ci_lower.notna() & ci_upper.notna() & (ci_lower <= ci_upper)
        )
        source_exclusion_metrics = cast(
            "pandas.Series[str]",
            experiment_rows[ReportColumnName.METRIC],
        )
        required_interval_rows = experiment_rows[
            (
                (
                    experiment_rows[ReportColumnName.EXPERIMENT]
                    == PRIMARY_CONFIRMATORY_EVALUATION_NAME
                )
                & (experiment_rows[ReportColumnName.METRIC] == ComparisonMetric.TARGET_F1)
            )
            | (
                (
                    experiment_rows[ReportColumnName.EXPERIMENT]
                    == SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME
                )
                & (
                    (source_exclusion_metrics == ComparisonMetric.ATTACK_SUCCESS_RATE)
                    | (source_exclusion_metrics == ComparisonMetric.TARGET_F1)
                )
            )
        ]
        return (
            expected_conditions.issubset(observed_conditions)
            and all((experiment_rows[ReportColumnName.OBSERVATION_COUNT] > 0).tolist())
            and all((experiment_rows[ReportColumnName.SEED_COUNT] > 0).tolist())
            and all(experiment_rows[ReportColumnName.MEAN_VALUE].notna().tolist())
            and all((experiment_rows[ReportColumnName.SAMPLE_STANDARD_DEVIATION] >= 0).tolist())
            and all(ci_pair_is_valid.tolist())
            and all(required_interval_rows[ReportColumnName.CONFIDENCE_INTERVAL_LOWER].notna())
            and all(required_interval_rows[ReportColumnName.CONFIDENCE_INTERVAL_UPPER].notna())
        )
    terminal_state_values = cast(
        list[str], experiment_rows[ReportColumnName.TERMINAL_STATE].tolist()
    )
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
