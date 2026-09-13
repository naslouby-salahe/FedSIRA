from __future__ import annotations

import inspect
import json
from collections import OrderedDict
from pathlib import Path

import numpy
import torch

from fedsira.artifacts.paths import (
    artifact_log_path,
    artifact_slot_directory,
    artifact_staging_root,
    experiment_log_path,
    prepared_evidence_root,
    smoke_record_path,
    workspace_root_for_family,
)
from fedsira.artifacts.store import (
    ArtifactDependency,
    configuration_digest,
    configure_artifact_logging,
    publish_artifact,
    read_current_artifact,
    repository_revision,
)
from fedsira.datasets.common import (
    SUPPORTED_ROLE_ORDER,
    Role,
    dataset_manifest_hash,
)
from fedsira.datasets.nbaiot.prepare import assign_stream_roles_and_sample_ids
from fedsira.datasets.nbaiot.schema import (
    NBaiotClass,
    NBaiotDomain,
)
from fedsira.domain.enums import (
    AblationVariant,
    AdmissionState,
    ArtifactDependencyKind,
    ArtifactDependencyLabel,
    ArtifactFamily,
    ArtifactProducer,
    BoundCondition,
    CapabilityContractScope,
    EpistemicFailureType,
    ExperimentLifecycleState,
    ExperimentName,
    LogEvent,
    ReportCellLiteral,
    RootCauseMixture,
    ScientificCellPhase,
    SmokeCheckName,
    TernaryOutcome,
)
from fedsira.domain.models import (
    AdmissionDelayDecomposition,
    ScientificCell,
)
from fedsira.domain.types import (
    AdequateFinalGateDomainCount,
    ComparisonName,
    DatasetClassToken,
    DomainId,
    ExampleCount,
    FrozenDomainModel,
    MasterSeed,
    MethodName,
    MetricValue,
    ModelInputWidth,
    ModelOutputWidth,
    OverwriteExisting,
    PreparedReproductionTargetCount,
    PreparedSupportedReplayCount,
    Probability,
    ProductionWeight,
    PValue,
    RelativePathText,
    ResolvedCoreComplete,
    ScenarioName,
    SchemaVersion,
    ScientificCellSemanticKey,
    SmokeRenderText,
    StatusRenderText,
    WallClockSeconds,
)
from fedsira.evaluation.comparison_evidence import publish_comparison_evidence
from fedsira.evaluation.metrics import (
    accuracy,
    compute_confusion_counts,
)
from fedsira.evaluation.statistics import (
    bootstrap_percentile_confidence_interval,
    exact_sign_flip_two_sided_p_value,
    holm_adjusted_p_values,
    quantile_type7,
)
from fedsira.experiments.artifact_invariants import artifact_invariants
from fedsira.experiments.byzantine import validate_byzantine_vocabulary
from fedsira.experiments.collapse import resolve_all_eight_cases
from fedsira.experiments.definitions import (
    MECHANISM_ABLATION_NAME,
    epistemic_strength_tokens,
    experiment_by_name,
)
from fedsira.experiments.engine import (
    ABLATION_REFERENCE_PROCEDURE_IDENTITY,
    ABLATION_REFERENCE_SCHEMA_VERSION,
    EXECUTION_LOGGER,
    CellExecutionOutcome,
    CellExecutor,
    ComparisonResultBuilder,
    ExecutionLogFields,
    ExecutionProvenance,
    ExecutionRecordStore,
    ExperimentExecutionResult,
    PersistedAblationReference,
    ablation_reference_slot,
    derive_experiment_lifecycle,
    execute_cell_with_retry,
    log_execution_event,
    prerequisite_states_from_store,
)
from fedsira.experiments.planning import ExperimentPlan, PlannedExperiment, build_plan
from fedsira.experiments.smoke_records import (
    PersistedSmokeRecord,
    SmokeCheckResult,
    SmokeSuiteResult,
)
from fedsira.learning.model import (
    FedSIRAClassifier,
    flatten_trainable_parameters,
    trainable_parameter_count,
)
from fedsira.learning.post_reference import (
    compute_stability_kl,
    post_reference_training_step,
    run_post_reference_training,
)
from fedsira.learning.training import (
    ModelParameter,
    ModelState,
    WeightedModelState,
    build_loss_function,
    build_optimizer,
    federated_averaging,
)
from fedsira.protocol.admission import validate_admission_requires_final_gate
from fedsira.protocol.baselines.registry import validate_role_not_used_for_tuning
from fedsira.protocol.capability_contract import (
    SOURCE_DIRECT_PRODUCTION_WEIGHT,
    validate_source_excluded_production_weight,
)
from fedsira.protocol.reproduction import validate_commitment_exists_before_verifier_assignment
from fedsira.protocol.rules import (
    diagnostic_at_least_two_byzantine_probability,
    krum_committee_is_admissible,
    minimum_honest_positive_count,
)
from fedsira.protocol.synthesis import select_krum_update
from fedsira.protocol.verification import (
    reproduction_row_is_certified,
    verifier_is_eligible,
)
from fedsira.runtime import (
    REPOSITORY_ROOT,
    ApplicationContext,
    ElapsedTimer,
    bound_application_context,
    configure_deterministic_backend,
    configure_structured_file_logging,
    current_application_context,
)


def ablation_reference_cell(
    scientific_scenario: ScenarioName, master_seed: MasterSeed
) -> ScientificCell:
    return ScientificCell(
        experiment=MECHANISM_ABLATION_NAME,
        method=AblationVariant.FULL_FEDSIRA,
        condition=scientific_scenario,
        master_seed=master_seed,
    )


def materialize_ablation_references(
    planned: PlannedExperiment,
    executor: CellExecutor,
    master_seeds: tuple[MasterSeed, ...],
) -> tuple[PersistedAblationReference, ...]:
    references: list[PersistedAblationReference] = []
    scenarios: list[ScenarioName] = []
    for cell in planned.cells:
        if cell.condition not in scenarios:
            scenarios.append(cell.condition)
    for scientific_scenario in scenarios:
        for master_seed in master_seeds:
            slot = ablation_reference_slot(scientific_scenario, master_seed)
            slot_directory = REPOSITORY_ROOT / artifact_slot_directory(slot)
            current = read_current_artifact(slot_directory)
            if current is not None:
                _manifest, payload = current
                references.append(PersistedAblationReference.model_validate_json(payload))
                log_execution_event(
                    LogEvent.ABLATION_REFERENCE_REUSED,
                    ExecutionLogFields(
                        experiment=MECHANISM_ABLATION_NAME,
                        condition=scientific_scenario,
                        master_seed=master_seed,
                    ),
                )
                continue
            reference_cell = ablation_reference_cell(scientific_scenario, master_seed)
            outcome = execute_cell_with_retry(reference_cell, executor)
            reference = PersistedAblationReference(
                schema_version=ABLATION_REFERENCE_SCHEMA_VERSION,
                scientific_scenario=scientific_scenario,
                master_seed=master_seed,
                metrics=outcome.metrics,
                state_trajectory=outcome.state_trajectory,
            )
            payload = reference.model_dump_json().encode("utf-8")
            prepared_evidence = dataset_manifest_hash(
                REPOSITORY_ROOT / prepared_evidence_root(planned.definition.dataset)
            )
            publish_artifact(
                slot=slot,
                producer=ArtifactProducer.EVALUATION_PRODUCER,
                payload=payload,
                dependencies=(
                    ArtifactDependency(
                        kind=ArtifactDependencyKind.CONTENT,
                        dependency=ArtifactDependencyLabel.PREPARED_EVIDENCE,
                        digest=prepared_evidence,
                    ),
                ),
                procedure_identity=ABLATION_REFERENCE_PROCEDURE_IDENTITY,
                slot_directory=slot_directory,
                staging_root=REPOSITORY_ROOT / artifact_staging_root(),
            )
            references.append(reference)
            log_execution_event(
                LogEvent.ABLATION_REFERENCE_PUBLISHED,
                ExecutionLogFields(
                    experiment=MECHANISM_ABLATION_NAME,
                    condition=scientific_scenario,
                    master_seed=master_seed,
                ),
            )
    return tuple(references)


def execute_experiment(
    experiment: ExperimentName,
    executor: CellExecutor,
    comparison_builder: ComparisonResultBuilder | None = None,
    *,
    overwrite: OverwriteExisting = False,
    resolved_core_complete: ResolvedCoreComplete = False,
    prerequisite_states: tuple[ExperimentPrerequisiteState, ...] | None = None,
) -> ExperimentExecutionResult:
    resolved_config = current_application_context().scientific_config
    configure_structured_file_logging(
        EXECUTION_LOGGER,
        current_application_context().repository_root / experiment_log_path(experiment),
    )
    configure_artifact_logging(current_application_context().repository_root / artifact_log_path())
    timer = ElapsedTimer()
    log_execution_event(
        LogEvent.EXPERIMENT_STARTED,
        ExecutionLogFields(experiment=experiment, overwrite=overwrite),
    )
    definition = experiment_by_name(experiment)
    log_execution_event(
        LogEvent.EXPERIMENT_CONFIGURATION_RESOLVED, ExecutionLogFields(experiment=experiment)
    )
    plan = build_plan(
        resolved_core_complete=resolved_core_complete,
        master_seeds=resolved_config.seeds_and_determinism.master_seeds,
        smoke_seed=resolved_config.seeds_and_determinism.smoke_seed,
    )
    validate_condition_vocabulary(plan)
    validate_no_duplicate_semantic_cells(plan)
    planned = plan.experiment(experiment)
    log_execution_event(
        LogEvent.EXPERIMENT_PLAN_CREATED,
        ExecutionLogFields(
            experiment=experiment,
            dataset=definition.dataset,
            total_cells=len(planned.cells),
        ),
    )
    if planned.lifecycle_state is ExperimentLifecycleState.BLOCKED:
        return ExperimentExecutionResult(
            experiment=experiment,
            lifecycle_state=ExperimentLifecycleState.BLOCKED,
            outcomes=(),
        )
    store = ExecutionRecordStore(
        Path(resolved_config.execution.repository_layout.execution_workspace)
    )
    states = prerequisite_states or prerequisite_states_from_store(plan, experiment, store)
    validate_experiment_prerequisites_met(experiment, states)
    if experiment == MECHANISM_ABLATION_NAME:
        references = materialize_ablation_references(
            planned,
            executor,
            resolved_config.seeds_and_determinism.master_seeds,
        )
        log_execution_event(
            LogEvent.ABLATION_REFERENCES_MATERIALIZED,
            ExecutionLogFields(experiment=experiment, total_cells=len(references)),
        )
    log_execution_event(
        LogEvent.EXPERIMENT_PREREQUISITES_VALIDATED, ExecutionLogFields(experiment=experiment)
    )
    provenance = ExecutionProvenance(
        configuration_digest=configuration_digest(),
        code_revision=repository_revision(),
        dataset_manifest_hash=dataset_manifest_hash(
            REPOSITORY_ROOT / prepared_evidence_root(definition.dataset)
        ),
    )
    outcomes: list[CellExecutionOutcome] = []
    for cell in planned.cells:
        fields = ExecutionLogFields(
            experiment=experiment,
            dataset=definition.dataset,
            cell=cell.semantic_key,
            method=cell.method,
            condition=cell.condition,
            master_seed=cell.master_seed,
            total_cells=len(planned.cells),
        )
        existing = (
            None if overwrite else store.reusable_outcome(experiment, cell.semantic_key, provenance)
        )
        if existing is not None:
            log_execution_event(
                LogEvent.CELL_REUSED,
                fields,
            )
            outcomes.append(
                CellExecutionOutcome(
                    cell=cell,
                    terminal_state=existing.terminal_state,
                    failure=None,
                    metrics=existing.metrics,
                    state_trajectory=existing.state_trajectory,
                )
            )
            continue
        log_execution_event(LogEvent.CELL_STARTED, fields)
        outcome = execute_cell_with_retry(cell, executor)
        store.write_outcome(outcome, provenance)
        completed_cells = len(outcomes) + 1
        completed_fields = fields.with_cell_terminal_state(outcome.terminal_state, completed_cells)
        log_execution_event(LogEvent.CELL_RECORD_PERSISTED, completed_fields)
        for metric_name, _metric_value in outcome.metrics:
            log_execution_event(
                LogEvent.CELL_METRIC_COMPUTED,
                completed_fields.with_metric(metric_name),
            )
        log_execution_event(LogEvent.CELL_COMPLETED, completed_fields)
        log_execution_event(LogEvent.EXPERIMENT_PROGRESS, completed_fields)
        outcomes.append(outcome)
    outcome_tuple = tuple(outcomes)
    lifecycle_state = derive_experiment_lifecycle(planned, store.read_planned_outcomes(planned))
    if comparison_builder is None:
        comparisons = ()
    else:
        log_execution_event(LogEvent.COMPARISON_STARTED, ExecutionLogFields(experiment=experiment))
        comparisons = comparison_builder(experiment, definition.dataset, outcome_tuple, store)
        log_execution_event(
            LogEvent.COMPARISON_COMPLETED, ExecutionLogFields(experiment=experiment)
        )
        if comparisons:
            publish_comparison_evidence(
                experiment,
                store.read_planned_outcomes(planned),
                comparisons,
            )
            log_execution_event(
                LogEvent.COMPARISON_EVIDENCE_PERSISTED, ExecutionLogFields(experiment=experiment)
            )
    result = ExperimentExecutionResult(
        experiment=experiment,
        lifecycle_state=lifecycle_state,
        outcomes=outcome_tuple,
        comparison_results=comparisons,
    )
    log_execution_event(
        LogEvent.EXPERIMENT_COMPLETED
        if lifecycle_state is ExperimentLifecycleState.COMPLETED
        else LogEvent.EXPERIMENT_FAILED,
        ExecutionLogFields(
            experiment=experiment,
            terminal_state=lifecycle_state,
            completed_cells=result.cell_completion_count,
            total_cells=len(planned.cells),
            elapsed_seconds=timer.elapsed_seconds(),
        ),
    )
    return result


def render_status() -> StatusRenderText:
    from fedsira.experiments.collapse import read_resolved_core

    config = current_application_context().scientific_config
    resolved_core = read_resolved_core(
        REPOSITORY_ROOT / workspace_root_for_family(ArtifactFamily.FIXED_PROTOCOL_CONFIGURATION)
    )
    plan = build_plan(resolved_core_complete=resolved_core is not None)
    store = ExecutionRecordStore(
        REPOSITORY_ROOT / Path(config.execution.repository_layout.execution_workspace)
    )
    lines: list[str] = ["FedSIRA experiment status", ""]
    for planned in plan.experiments:
        records = store.read_planned_outcomes(planned)
        state = derive_experiment_lifecycle(planned, records)
        completed = sum(
            record.terminal_state is ExperimentLifecycleState.COMPLETED for record in records
        )
        lines.append(
            f"{planned.definition.name:<55} {completed:>4}/{len(planned.cells):<4} {state}"
        )
    return "\n".join(lines)


def execute_status() -> None:
    context = ApplicationContext.load(REPOSITORY_ROOT)
    with bound_application_context(context):
        print(render_status())


def execute_smoke(overwrite: OverwriteExisting) -> None:
    context = ApplicationContext.load(REPOSITORY_ROOT)
    with bound_application_context(context):
        configure_deterministic_backend()
        result = run_smoke_suite(overwrite=overwrite)
    print(render_smoke(result))
    if not result.passed:
        raise SystemExit(1)


SMOKE_RECORD_SCHEMA_VERSION: SchemaVersion = "fedsira|smoke_record|2"

_DANMINI = NBaiotDomain.DANMINI_DOORBELL
_ENNIO = NBaiotDomain.ENNIO_DOORBELL
_DANMINI_HASH_TOKEN: DomainId = _DANMINI.name
_DANMINI_BENIGN_CSV_PATH: RelativePathText = f"{_DANMINI}/benign_traffic.csv"
_DANMINI_TARGET_CSV_PATH: RelativePathText = f"{_DANMINI}/{NBaiotClass.GAFGYT_COMBO.name}.csv"

REQUIRED_CELL_PHASES: frozenset[ScientificCellPhase] = frozenset(
    (
        ScientificCellPhase.PREPARE,
        ScientificCellPhase.TRAIN,
        ScientificCellPhase.SCORE,
        ScientificCellPhase.PROTOCOL_EVALUATION,
        ScientificCellPhase.METRIC_AGGREGATION,
        ScientificCellPhase.STATISTICAL_ANALYSIS,
    )
)
TERMINAL_CELL_STATES: frozenset[ExperimentLifecycleState] = frozenset(
    (
        ExperimentLifecycleState.COMPLETED,
        ExperimentLifecycleState.FAILED,
        ExperimentLifecycleState.INVALID,
    )
)

SIGN_FLIP_CHECK_SAMPLE_COUNT = 10
SIGN_FLIP_CHECK_EXPECTED_P_VALUE: PValue = 0.001953125
HOLM_CHECK_RAW_P_VALUES: tuple[tuple[ComparisonName, PValue], ...] = (
    ("c", 0.125),
    ("a", 0.375),
    ("b", 0.25),
)
HOLM_CHECK_ADJUSTED_P_VALUES: tuple[tuple[ComparisonName, PValue], ...] = (
    ("c", 0.375),
    ("b", 0.5),
    ("a", 0.5),
)
SMOKE_MODEL_INPUT_WIDTH: ModelInputWidth = 4
SMOKE_MODEL_OUTPUT_WIDTH: ModelOutputWidth = 2
SMOKE_BATCH_ROW_COUNT: ExampleCount = 2
SMOKE_FEDAVG_CLIENT_A_EXAMPLE_COUNT: ExampleCount = 1
SMOKE_FEDAVG_CLIENT_B_EXAMPLE_COUNT: ExampleCount = 3
SMOKE_FEDAVG_CLIENT_A_WEIGHTS: tuple[MetricValue, ...] = (0.0, 1.0)
SMOKE_FEDAVG_CLIENT_B_WEIGHTS: tuple[MetricValue, ...] = (4.0, 5.0)
SMOKE_QUANTILE_VALUES: tuple[MetricValue, ...] = (0.0, 1.0, 2.0, 3.0)
SMOKE_QUANTILE_PROBABILITY: Probability = 0.5
SMOKE_SAMPLE_SD_VALUES: tuple[MetricValue, ...] = (1.0, 2.0, 3.0)
SMOKE_DELAY_ASSIGNMENT_SECONDS: WallClockSeconds = 1.0
SMOKE_DELAY_REPRODUCE_SECONDS: WallClockSeconds = 2.0
SMOKE_DELAY_VERIFY_SECONDS: WallClockSeconds = 3.0
SMOKE_DELAY_SYNTHESIZE_SECONDS: WallClockSeconds = 4.0
SMOKE_BOOTSTRAP_VALUES: tuple[MetricValue, ...] = (1.0, 2.0, 3.0)
SMOKE_CONFUSION_TRUE_LABELS: tuple[DatasetClassToken, ...] = ("a", "b", "a", "a")
SMOKE_CONFUSION_PREDICTED_LABELS: tuple[DatasetClassToken, ...] = ("a", "a", "a", "b")
SMOKE_CONFUSION_CLASS_TOKEN: DatasetClassToken = "a"
SMOKE_CONFUSION_TRUE_POSITIVE = 2
SMOKE_CONFUSION_FALSE_POSITIVE = 1
SMOKE_CONFUSION_FALSE_NEGATIVE = 1
SMOKE_CONFUSION_TRUE_NEGATIVE = 0
SMOKE_NONZERO_PRODUCTION_WEIGHT: ProductionWeight = 1.0


class ExperimentPrerequisiteState(FrozenDomainModel):
    experiment: ExperimentName
    lifecycle_state: ExperimentLifecycleState


def _allowed_conditions(experiment: ExperimentName) -> frozenset[ScenarioName] | None:
    if experiment is ExperimentName.BYZANTINE_BOUND_VIOLATION:
        return frozenset(condition for condition in BoundCondition)
    if experiment is ExperimentName.SHARED_EPISTEMIC_FAILURE_BOUNDARY:
        return frozenset(
            f"{failure_type}|{strength}"
            for failure_type in EpistemicFailureType
            for strength in epistemic_strength_tokens(failure_type)
        )
    if experiment is ExperimentName.CAPABILITY_UNDER_SPECIFICATION_BOUNDARY:
        return frozenset(mixture for mixture in RootCauseMixture)
    return None


def _allowed_methods(experiment: ExperimentName) -> frozenset[MethodName] | None:
    if experiment is ExperimentName.CAPABILITY_UNDER_SPECIFICATION_BOUNDARY:
        return frozenset(granularity for granularity in CapabilityContractScope)
    if experiment is ExperimentName.MECHANISM_ABLATION:
        return frozenset(variant for variant in AblationVariant)
    return None


def validate_condition_vocabulary(plan: ExperimentPlan) -> None:
    validate_byzantine_vocabulary()
    for planned in plan.experiments:
        allowed = _allowed_conditions(planned.definition.name)
        if allowed is not None:
            for cell in planned.cells:
                if cell.condition not in allowed:
                    raise ValueError(
                        f"cell {cell.semantic_key} uses condition {cell.condition!r} "
                        f"outside the fixed {planned.definition.name} vocabulary"
                    )
        allowed_methods = _allowed_methods(planned.definition.name)
        if allowed_methods is not None:
            for cell in planned.cells:
                if cell.method not in allowed_methods:
                    raise ValueError(
                        f"cell {cell.semantic_key} uses method {cell.method!r} "
                        f"outside the fixed {planned.definition.name} vocabulary"
                    )


def validate_experiment_prerequisites_met(
    experiment: ExperimentName,
    prerequisite_states: tuple[ExperimentPrerequisiteState, ...],
) -> None:
    definition = experiment_by_name(experiment)
    for prerequisite in definition.prerequisites:
        state = next(
            (
                entry.lifecycle_state
                for entry in prerequisite_states
                if entry.experiment == prerequisite
            ),
            None,
        )
        if state is not ExperimentLifecycleState.COMPLETED:
            state_text = state if state is not None else ReportCellLiteral.UNKNOWN
            raise ValueError(
                f"experiment {experiment} requires prerequisite {prerequisite} "
                f"to be Completed, found {state_text}"
            )


def validate_no_duplicate_semantic_cells(plan: ExperimentPlan) -> None:
    seen: set[ScientificCellSemanticKey] = set()
    for planned in plan.experiments:
        for cell in planned.cells:
            if cell.semantic_key in seen:
                raise ValueError(f"duplicate semantic cell {cell.semantic_key}")
            seen.add(cell.semantic_key)


def validate_cell_phase_sequence(phases: tuple[ScientificCellPhase, ...]) -> None:
    if len(phases) != len(set(phases)):
        raise ValueError("a cell phase may appear at most once in its execution sequence")
    for phase in phases:
        if phase not in REQUIRED_CELL_PHASES:
            raise ValueError(f"unknown scientific cell phase {phase}")


def validate_cell_terminal_record(
    cell: ScientificCell,
    terminal_state: ExperimentLifecycleState,
) -> None:
    if terminal_state not in TERMINAL_CELL_STATES:
        raise ValueError(
            f"cell {cell.semantic_key} terminal state {terminal_state} is not terminal"
        )


def _data_invariants() -> tuple[SmokeCheckResult, ...]:
    config = current_application_context().scientific_config
    role_intervals = config.datasets.primary.role_intervals
    sampling_caps = config.datasets.primary.sampling_caps_per_domain
    stream_row_count = sampling_caps.reproduction_target
    assignments = assign_stream_roles_and_sample_ids(
        dataset_file_sha256="a" * 64,
        domain_hash_token=_DANMINI_HASH_TOKEN,
        class_id=NBaiotClass.GAFGYT_COMBO,
        normalized_relative_csv_path=_DANMINI_TARGET_CSV_PATH,
        stream_row_count=stream_row_count,
        role_intervals=role_intervals,
        sampling_caps_per_domain=sampling_caps,
    )
    roles_seen = {assignment.role for assignment in assignments}
    no_target_in_anchor = (
        Role.ANCHOR_TRAIN not in roles_seen and Role.ANCHOR_VALIDATION not in roles_seen
    )
    supported_assignments = assign_stream_roles_and_sample_ids(
        dataset_file_sha256="a" * 64,
        domain_hash_token=_DANMINI_HASH_TOKEN,
        class_id=NBaiotClass.BENIGN,
        normalized_relative_csv_path=_DANMINI_BENIGN_CSV_PATH,
        stream_row_count=stream_row_count,
        role_intervals=role_intervals,
        sampling_caps_per_domain=sampling_caps,
    )
    row_indices = tuple(assignment.original_row_index for assignment in supported_assignments)
    no_overlap = len(row_indices) == len(set(row_indices))
    return (
        SmokeCheckResult(
            name=SmokeCheckName.NO_TARGET_SAMPLE_IN_ANCHOR_ROLES, passed=no_target_in_anchor
        ),
        SmokeCheckResult(name=SmokeCheckName.NO_CROSS_ROLE_SAMPLE_OVERLAP, passed=no_overlap),
    )


_REQUIRED_CELL_PHASE_SEQUENCE: tuple[ScientificCellPhase, ...] = (
    ScientificCellPhase.PREPARE,
    ScientificCellPhase.TRAIN,
    ScientificCellPhase.SCORE,
    ScientificCellPhase.PROTOCOL_EVALUATION,
    ScientificCellPhase.METRIC_AGGREGATION,
    ScientificCellPhase.STATISTICAL_ANALYSIS,
)


def _protocol_invariants() -> tuple[SmokeCheckResult, ...]:
    config = current_application_context().scientific_config
    source_not_verifier = not verifier_is_eligible(_DANMINI, _DANMINI, _ENNIO)
    required_phase_sequence_valid = False
    try:
        validate_cell_phase_sequence(_REQUIRED_CELL_PHASE_SEQUENCE)
        required_phase_sequence_valid = True
    except ValueError:
        required_phase_sequence_valid = False
    verification = config.protocol.verification
    synthesis = config.protocol.synthesis
    three_row = config.baselines.three_row_coordinate_median
    diagnostic = config.protocol.diagnostic_random_verifier_profile
    honest_positive_expected = (
        verification.required_positive_reports - verification.maximum_byzantine_verifiers_per_panel
    )
    honest_positive = (
        minimum_honest_positive_count(
            verification.required_positive_reports,
            verification.maximum_byzantine_verifiers_per_panel,
        )
        == honest_positive_expected
    )
    krum_admissible = krum_committee_is_admissible(
        synthesis.committee_size, synthesis.maximum_byzantine_reproduction_rows
    )
    krum_three_rejected = not krum_committee_is_admissible(
        three_row.row_count, three_row.assumed_byzantine_rows
    )
    commitment_rejected = False
    try:
        validate_commitment_exists_before_verifier_assignment(None)
    except ValueError:
        commitment_rejected = True
    eligible_pool_size = len(NBaiotDomain) - len((_DANMINI, _ENNIO))
    probability = diagnostic_at_least_two_byzantine_probability(
        eligible_pool_size, diagnostic.byzantine_domain_count, diagnostic.panel_size
    )
    tolerance = config.validation_tolerances.random_committee_probability_absolute
    expected_probability = 1 / eligible_pool_size
    probability_matches = abs(probability - expected_probability) < tolerance
    return (
        SmokeCheckResult(name=SmokeCheckName.SOURCE_CANNOT_BE_VERIFIER, passed=source_not_verifier),
        SmokeCheckResult(
            name=SmokeCheckName.CELL_PHASE_SEQUENCE_WELL_FORMED,
            passed=required_phase_sequence_valid,
        ),
        SmokeCheckResult(
            name=SmokeCheckName.PLURALITY_IMPLIES_HONEST_POSITIVE,
            passed=honest_positive,
        ),
        SmokeCheckResult(name=SmokeCheckName.KRUM_FIVE_ONE_ADMISSIBLE, passed=krum_admissible),
        SmokeCheckResult(name=SmokeCheckName.KRUM_THREE_ONE_REJECTED, passed=krum_three_rejected),
        SmokeCheckResult(
            name=SmokeCheckName.VERIFIER_ASSIGNMENT_BEFORE_COMMITMENT_THROWS,
            passed=commitment_rejected,
        ),
        SmokeCheckResult(
            name=SmokeCheckName.RANDOM_COMMITTEE_CONTAMINATION_PROBABILITY,
            passed=probability_matches,
            detail=f"observed {probability:.12f}",
        ),
    )


def _mathematical_invariants() -> tuple[SmokeCheckResult, ...]:
    sample_count = SIGN_FLIP_CHECK_SAMPLE_COUNT
    sign_flip = exact_sign_flip_two_sided_p_value((1.0,) * sample_count)
    sign_flip_matches = sign_flip == SIGN_FLIP_CHECK_EXPECTED_P_VALUE
    holm = holm_adjusted_p_values(HOLM_CHECK_RAW_P_VALUES)
    holm_matches = holm == HOLM_CHECK_ADJUSTED_P_VALUES
    return (
        SmokeCheckResult(
            name=SmokeCheckName.EXACT_SIGN_FLIP_TEST_ENUMERATES_ASSIGNMENTS,
            passed=sign_flip_matches,
            detail=f"p={sign_flip:.10f}",
        ),
        SmokeCheckResult(name=SmokeCheckName.HOLM_ADJUSTMENT_MATCHES_FIXTURE, passed=holm_matches),
    )


def _model_invariants() -> tuple[SmokeCheckResult, ...]:
    config = current_application_context().scientific_config
    input_width = SMOKE_MODEL_INPUT_WIDTH
    output_width = SMOKE_MODEL_OUTPUT_WIDTH
    batch_rows = SMOKE_BATCH_ROW_COUNT
    model = FedSIRAClassifier(input_width, output_width)
    features = torch.ones((batch_rows, input_width))
    labels = torch.zeros((batch_rows,), dtype=torch.long)
    logits = model(features)
    loss = build_loss_function()(logits, labels)
    loss.backward()
    finite = bool(torch.isfinite(logits).all()) and bool(torch.isfinite(loss))
    first = ModelState(
        parameters=(
            ModelParameter(
                name="w",
                value=torch.tensor(SMOKE_FEDAVG_CLIENT_A_WEIGHTS),
            ),
        )
    )
    second = ModelState(
        parameters=(
            ModelParameter(
                name="w",
                value=torch.tensor(SMOKE_FEDAVG_CLIENT_B_WEIGHTS),
            ),
        )
    )
    count_a = SMOKE_FEDAVG_CLIENT_A_EXAMPLE_COUNT
    count_b = SMOKE_FEDAVG_CLIENT_B_EXAMPLE_COUNT
    averaged = federated_averaging(
        (
            WeightedModelState(state=first, example_count=count_a),
            WeightedModelState(state=second, example_count=count_b),
        )
    )
    total = count_a + count_b
    expected = torch.tensor(
        tuple(
            (left * count_a + right * count_b) / total
            for left, right in zip(
                SMOKE_FEDAVG_CLIENT_A_WEIGHTS,
                SMOKE_FEDAVG_CLIENT_B_WEIGHTS,
                strict=True,
            )
        )
    )
    fedavg_matches = torch.allclose(averaged.parameters[0].value, expected)
    model.eval()
    restored = FedSIRAClassifier(input_width, output_width)
    restored.load_state_dict(model.state_dict())
    restored.eval()
    with torch.no_grad():
        original_logits = model(features)
        restored_logits = restored(features)
        delta = (restored_logits - original_logits).abs().max()
    restore_matches = float(delta) <= config.execution.same_environment_absolute_metric_tolerance
    report_test_rejected = False
    try:
        validate_role_not_used_for_tuning(Role.REPORT_TEST)
    except ValueError:
        report_test_rejected = True
    anchor = FedSIRAClassifier(input_width, output_width)
    current = FedSIRAClassifier(input_width, output_width)
    current.load_state_dict(anchor.state_dict())
    optimizer = build_optimizer(
        current, config.model.optimizer.post_reference_learning_rate, config.model.optimizer
    )
    unsupported = torch.zeros((batch_rows,), dtype=torch.bool)
    post_reference_training_step(
        anchor,
        current,
        optimizer,
        build_loss_function(),
        config.model.training,
        config.model.post_reference,
        features,
        labels,
        unsupported,
        flatten_trainable_parameters(anchor).detach(),
        trainable_parameter_count(current),
    )
    temperature = config.model.post_reference.stability_kl_temperature
    identical = torch.ones((batch_rows, output_width))
    kl_zero = float(compute_stability_kl(identical, identical, temperature)) >= 0.0
    constructor_has_no_source = not any(
        "source" in name for name in inspect.signature(run_post_reference_training).parameters
    )
    return (
        SmokeCheckResult(name=SmokeCheckName.ONE_BATCH_FORWARD_BACKWARD_FINITE, passed=finite),
        SmokeCheckResult(
            name=SmokeCheckName.ONE_ROUND_FEDAVG_MATCHES_FIXTURE,
            passed=fedavg_matches,
        ),
        SmokeCheckResult(
            name=SmokeCheckName.CHECKPOINT_RESTORE_REPRODUCES_PREDICTIONS,
            passed=restore_matches,
        ),
        SmokeCheckResult(
            name=SmokeCheckName.REPORT_TEST_LOADER_NOT_REQUESTED_BY_TRAINING,
            passed=report_test_rejected,
        ),
        SmokeCheckResult(
            name=SmokeCheckName.POST_REFERENCE_MINIBATCH_KEEPS_KL_DEFINED,
            passed=kl_zero,
        ),
        SmokeCheckResult(
            name=SmokeCheckName.HONEST_REPRODUCTION_HAS_NO_SOURCE_ARTIFACT,
            passed=constructor_has_no_source,
        ),
    )


def _extended_protocol_invariants() -> tuple[SmokeCheckResult, ...]:
    config = current_application_context().scientific_config
    source_weight_zero = True
    try:
        validate_source_excluded_production_weight(SOURCE_DIRECT_PRODUCTION_WEIGHT)
        validate_source_excluded_production_weight(SMOKE_NONZERO_PRODUCTION_WEIGHT)
        source_weight_zero = False
    except ValueError:
        source_weight_zero = True
    verification = config.protocol.verification
    abstain_panel = tuple(TernaryOutcome.ABSTAIN for _ in range(verification.panel_size))
    abstain_not_positive = not reproduction_row_is_certified(
        abstain_panel, verification.panel_size, verification.required_positive_reports
    )
    five_row_required = False
    try:
        select_krum_update((), config.protocol.synthesis.maximum_byzantine_reproduction_rows)
    except ValueError:
        five_row_required = True
    admission_requires_gate = False
    try:
        validate_admission_requires_final_gate(AdmissionState.ADMITTED, False)
    except ValueError:
        admission_requires_gate = True
    eight_cases = resolve_all_eight_cases()
    eight_resolved = len(eight_cases) == 2**3
    disjoint_roles = (
        frozenset(SUPPORTED_ROLE_ORDER).isdisjoint(
            frozenset((Role.SOURCE_PROPOSAL, Role.REPRODUCTION))
        )
        and Role.SOURCE_PROPOSAL not in SUPPORTED_ROLE_ORDER
    )
    return (
        SmokeCheckResult(
            name=SmokeCheckName.SOURCE_DIRECT_PRODUCTION_WEIGHT_ZERO,
            passed=source_weight_zero,
        ),
        SmokeCheckResult(
            name=SmokeCheckName.ABSTAIN_NOT_CASTABLE_TO_BOOLEAN_VOTE,
            passed=abstain_not_positive,
        ),
        SmokeCheckResult(
            name=SmokeCheckName.FEWER_THAN_FIVE_ROWS_CANNOT_SYNTHESIZE,
            passed=five_row_required,
        ),
        SmokeCheckResult(
            name=SmokeCheckName.FINAL_ADMISSION_REQUIRES_FINAL_GATE_ARTIFACT,
            passed=admission_requires_gate,
        ),
        SmokeCheckResult(
            name=SmokeCheckName.EIGHT_COLLAPSE_COMBINATIONS_RESOLVE,
            passed=eight_resolved,
        ),
        SmokeCheckResult(
            name=SmokeCheckName.ROLES_ARE_DISJOINT,
            passed=disjoint_roles,
        ),
    )


def _extended_mathematical_invariants() -> tuple[SmokeCheckResult, ...]:
    config = current_application_context().scientific_config
    diagnostic = config.protocol.diagnostic_random_verifier_profile
    pool = len(NBaiotDomain) - len((_DANMINI, _ENNIO))
    zero = diagnostic_at_least_two_byzantine_probability(pool, 0, diagnostic.panel_size)
    one = diagnostic_at_least_two_byzantine_probability(pool, 1, diagnostic.panel_size)
    tolerance = config.validation_tolerances.random_committee_probability_absolute
    delay = AdmissionDelayDecomposition(
        logical_information_arrival_cycles=1,
        assignment_seconds=SMOKE_DELAY_ASSIGNMENT_SECONDS,
        reproduce_seconds=SMOKE_DELAY_REPRODUCE_SECONDS,
        verify_seconds=SMOKE_DELAY_VERIFY_SECONDS,
        synthesize_seconds=SMOKE_DELAY_SYNTHESIZE_SECONDS,
    )
    delay_matches = (
        abs(
            delay.post_evidence_wall_clock_seconds
            - (
                delay.assignment_seconds
                + delay.reproduce_seconds
                + delay.verify_seconds
                + delay.synthesize_seconds
            )
        )
        < config.validation_tolerances.delay_component_sum_seconds_absolute
    )
    quantiles = quantile_type7(SMOKE_QUANTILE_VALUES, SMOKE_QUANTILE_PROBABILITY)
    numpy_matches = quantiles == float(
        numpy.quantile(SMOKE_QUANTILE_VALUES, SMOKE_QUANTILE_PROBABILITY, method="linear")
    )
    sample = numpy.array(SMOKE_SAMPLE_SD_VALUES)
    sd_matches = float(sample.std(ddof=1)) == float(numpy.std(sample, ddof=1))
    confusion = compute_confusion_counts(
        SMOKE_CONFUSION_TRUE_LABELS,
        SMOKE_CONFUSION_PREDICTED_LABELS,
        SMOKE_CONFUSION_CLASS_TOKEN,
    )
    confusion_matches = (
        confusion.true_positive == SMOKE_CONFUSION_TRUE_POSITIVE
        and confusion.false_positive == SMOKE_CONFUSION_FALSE_POSITIVE
        and confusion.false_negative == SMOKE_CONFUSION_FALSE_NEGATIVE
        and confusion.true_negative == SMOKE_CONFUSION_TRUE_NEGATIVE
    )
    zero_den = accuracy(OrderedDict(), 0)
    zero_is_na = zero_den.value is None and zero_den.denominator == 0
    bootstrap_config = config.metrics_and_statistics.bootstrap
    analysis_seed = config.seeds_and_determinism.analysis_seed
    first_interval = bootstrap_percentile_confidence_interval(
        SMOKE_BOOTSTRAP_VALUES, bootstrap_config, analysis_seed
    )
    second_interval = bootstrap_percentile_confidence_interval(
        SMOKE_BOOTSTRAP_VALUES, bootstrap_config, analysis_seed
    )
    bootstrap_deterministic = first_interval == second_interval
    return (
        SmokeCheckResult(
            name=SmokeCheckName.RANDOM_COMMITTEE_EXACT_PROBABILITY_ZERO,
            passed=abs(zero) < tolerance and abs(one) < tolerance,
        ),
        SmokeCheckResult(
            name=SmokeCheckName.POST_EVIDENCE_COMPONENTS_SUM_TO_TOTAL,
            passed=delay_matches,
        ),
        SmokeCheckResult(
            name=SmokeCheckName.TYPE_SEVEN_QUANTILES_MATCH_NUMPY, passed=numpy_matches
        ),
        SmokeCheckResult(name=SmokeCheckName.SAMPLE_SD_USES_DDOF_ONE, passed=sd_matches),
        SmokeCheckResult(
            name=SmokeCheckName.CONFUSION_METRICS_MATCH_HAND_CALCULATIONS,
            passed=confusion_matches,
        ),
        SmokeCheckResult(name=SmokeCheckName.ZERO_DENOMINATORS_RETURN_NA, passed=zero_is_na),
        SmokeCheckResult(
            name=SmokeCheckName.BOOTSTRAP_DRAWS_DETERMINISTIC,
            passed=bootstrap_deterministic,
        ),
    )


def run_data_and_domain_evidence_validation(
    reproduction_target_count: PreparedReproductionTargetCount,
    reproduction_supported_count: PreparedSupportedReplayCount,
    final_gate_adequate_domain_count: AdequateFinalGateDomainCount,
) -> None:
    config = current_application_context().scientific_config
    failed = tuple(check.name for check in _data_invariants() if not check.passed)
    if failed:
        raise ValueError(f"data and domain evidence validation failed: {', '.join(failed)}")
    minima = config.capability_contract.evidence_minima
    if reproduction_target_count < minima.reproduction_target_examples:
        raise ValueError(
            "reproduction-target evidence is below the configured minimum "
            f"{minima.reproduction_target_examples}"
        )
    if reproduction_supported_count < minima.reproduction_supported_control_examples:
        raise ValueError(
            "reproduction supported-control evidence is below the configured minimum "
            f"{minima.reproduction_supported_control_examples}"
        )
    required_final_gate_domains = config.protocol.final_gate.minimum_adequate_non_source_domains
    if final_gate_adequate_domain_count < required_final_gate_domains:
        raise ValueError(
            "final-gate adequate non-source domain count is below the configured minimum "
            f"{required_final_gate_domains}"
        )


def run_protocol_invariant_validation() -> None:
    result = run_smoke_suite(overwrite=False)
    if not result.passed:
        failed = tuple(check.name for check in result.checks if not check.passed)
        raise ValueError(f"protocol invariant validation failed: {', '.join(failed)}")


def _load_persisted_smoke_record() -> PersistedSmokeRecord | None:
    record_path = smoke_record_path()
    if not record_path.exists():
        return None
    try:
        return PersistedSmokeRecord.model_validate_json(record_path.read_text(encoding="utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None


def run_smoke_suite(overwrite: OverwriteExisting) -> SmokeSuiteResult:
    existing = None if overwrite else _load_persisted_smoke_record()
    current_digest = configuration_digest()
    current_revision = repository_revision()
    if (
        existing is not None
        and existing.passed
        and existing.configuration_digest == current_digest
        and existing.code_revision == current_revision
    ):
        return SmokeSuiteResult(checks=existing.checks)
    checks = (
        *_data_invariants(),
        *_model_invariants(),
        *_protocol_invariants(),
        *_extended_protocol_invariants(),
        *_mathematical_invariants(),
        *_extended_mathematical_invariants(),
        *artifact_invariants(),
    )
    result = SmokeSuiteResult(checks=checks)
    _persist_smoke_record(result, overwrite or existing is None or not existing.passed)
    return result


def _persist_smoke_record(result: SmokeSuiteResult, overwrite: OverwriteExisting) -> None:
    record_path = smoke_record_path()
    if record_path.exists() and not overwrite and result.passed:
        return
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record = PersistedSmokeRecord(
        schema_version=SMOKE_RECORD_SCHEMA_VERSION,
        configuration_digest=configuration_digest(),
        code_revision=repository_revision(),
        passed=result.passed,
        checks=result.checks,
    )
    record_path.write_text(record.model_dump_json(indent=2))


def render_smoke(result: SmokeSuiteResult) -> SmokeRenderText:
    lines = ["FedSIRA smoke suite"]
    for check in result.checks:
        marker = "PASS" if check.passed else "FAIL"
        detail = f" ({check.detail})" if check.detail else ""
        lines.append(f"  [{marker}] {check.name}{detail}")
    lines.append(f"result: {'PASSED' if result.passed else 'FAILED'}")
    return "\n".join(lines)
