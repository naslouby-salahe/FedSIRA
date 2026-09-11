from __future__ import annotations

from pathlib import Path

from rich.console import Console

from fedsira.artifacts.paths import (
    manuscript_tables_root,
    prepared_evidence_root,
    project_summary_root,
    smoke_record_path,
    workspace_root_for_family,
)
from fedsira.datasets.nbaiot.executor import (
    ProtocolCellExecutor,
)
from fedsira.datasets.nbaiot.validation import PersistedSmokeRecord
from fedsira.datasets.preprocess import execute_preprocess
from fedsira.datasets.specification import dataset_specification
from fedsira.domain.enums import ArtifactFamily, DatasetId, ExperimentLifecycleState, ProjectStage
from fedsira.domain.types import (
    ApplicationExitCode,
    BooleanValue,
    ConfigurationLoadable,
    DeterministicExecutionReady,
    DoctorArtifactSummary,
    DoctorExperimentSummary,
    ExperimentName,
    FailureMessage,
    FrozenDomainModel,
    NextValidAction,
    OverwriteExisting,
    ProjectProgressDescription,
    ResolvedCoreComplete,
    RunRenderText,
)
from fedsira.evaluation.service import comparison_results_for_experiment
from fedsira.experiments.collapse import (
    CollapseDecision,
    collapse_decision_from_comparison_families,
    collapse_evaluation_from_records,
    materialize_resolved_core,
    publish_resolved_core,
    read_resolved_core,
)
from fedsira.experiments.definitions import (
    ADMISSION_DELAY_DECOMPOSITION_NAME,
    BASELINE_IMPLEMENTATION_VALIDATION_NAME,
    BYZANTINE_BOUND_VIOLATION_NAME,
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    COLLAPSE_EXPERIMENT_NAMES,
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
    MECHANISM_ABLATION_NAME,
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    SECONDARY_DATASET_GENERALIZATION_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
    ComparisonFamily,
    experiment_by_name,
)
from fedsira.experiments.execution import (
    CellExecutionOutcome,
    ExecutionRecordStore,
    ExperimentExecutionResult,
    derive_experiment_lifecycle,
    execute_experiment,
    execute_smoke,
    execute_status,
)
from fedsira.experiments.planning import ExperimentPlan, ScientificCell, build_plan, execute_plan
from fedsira.reporting.export import execute_report, export_experiment_report
from fedsira.runtime import (
    REPOSITORY_ROOT,
    ApplicationContext,
    EnvironmentMismatch,
    bound_application_context,
    collect_environment_mismatches,
    configure_deterministic_backend,
    current_application_context,
    get_structured_logger,
)

_LOGGER = get_structured_logger("doctor")
_RESOLVED_CORE_DIRECTORY = workspace_root_for_family(ArtifactFamily.FIXED_PROTOCOL_CONFIGURATION)
_BOUNDARY_EXPERIMENT_NAMES: tuple[ExperimentName, ...] = (
    EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
)
_BYZANTINE_EXPERIMENT_NAMES: tuple[ExperimentName, ...] = (
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
    BYZANTINE_BOUND_VIOLATION_NAME,
)
_DELAY_EXPERIMENT_NAMES: tuple[ExperimentName, ...] = (
    ADMISSION_DELAY_DECOMPOSITION_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
)


class DoctorReport(FrozenDomainModel):
    environment_mismatches: tuple[EnvironmentMismatch, ...]
    configuration_loadable: ConfigurationLoadable
    configuration_error: FailureMessage | None
    dataset_readiness: ExperimentLifecycleState
    artifact_validity_summary: DoctorArtifactSummary
    experiment_summary: DoctorExperimentSummary
    project_stage: ProjectStage
    project_progress: ProjectProgressDescription
    next_valid_action: NextValidAction

    @property
    def is_deterministic_execution_ready(self) -> DeterministicExecutionReady:
        return len(self.environment_mismatches) == 0 and self.configuration_loadable


def diagnose(config_path: Path | None = None) -> DoctorReport:
    try:
        context = ApplicationContext.load(REPOSITORY_ROOT, config_path)
    except ValueError as error:
        _LOGGER.info("configuration load failed")
        return DoctorReport(
            environment_mismatches=(),
            configuration_loadable=False,
            configuration_error=str(error),
            dataset_readiness=ExperimentLifecycleState.NOT_STARTED,
            artifact_validity_summary="artifacts not inspected because configuration is invalid",
            experiment_summary="experiments not inspected because configuration is invalid",
            project_stage=ProjectStage.DOCTOR_READINESS,
            project_progress="doctor blocked by invalid configuration",
            next_valid_action="fix configs/fedsira.yaml until validation succeeds",
        )
    raw_data_root = REPOSITORY_ROOT / context.scientific_config.execution.repository_layout.raw_data
    rar_archives_present = raw_data_root.exists() and any(raw_data_root.rglob("*.rar"))
    with bound_application_context(context):
        environment_mismatches = collect_environment_mismatches(rar_archives_present)
        return _diagnose_bound(context, environment_mismatches)


def _diagnose_bound(
    context: ApplicationContext,
    environment_mismatches: tuple[EnvironmentMismatch, ...],
) -> DoctorReport:
    raw_root = REPOSITORY_ROOT / context.scientific_config.execution.repository_layout.raw_data
    workspace = (
        REPOSITORY_ROOT / context.scientific_config.execution.repository_layout.execution_workspace
    )
    store = ExecutionRecordStore(workspace)
    resolved_core = read_resolved_core(REPOSITORY_ROOT / _RESOLVED_CORE_DIRECTORY)
    plan = build_plan(
        resolved_core_complete=resolved_core is not None,
        master_seeds=context.scientific_config.seeds_and_determinism.master_seeds,
        smoke_seed=context.scientific_config.seeds_and_determinism.smoke_seed,
    )
    dataset_readiness = _dataset_readiness(raw_root)
    artifact_summary = _artifact_summary(dataset_readiness, resolved_core is not None)
    experiment_summary = _experiment_summary(plan, store)
    project_stage = _project_stage(
        environment_mismatches=environment_mismatches,
        dataset_readiness=dataset_readiness,
        plan=plan,
        store=store,
        resolved_core_present=resolved_core is not None,
    )
    project_progress, next_valid_action = _progress_and_action(
        environment_mismatches,
        project_stage,
    )
    _LOGGER.info("doctor diagnosis complete")
    return DoctorReport(
        environment_mismatches=environment_mismatches,
        configuration_loadable=True,
        configuration_error=None,
        dataset_readiness=dataset_readiness,
        artifact_validity_summary=artifact_summary,
        experiment_summary=experiment_summary,
        project_stage=project_stage,
        project_progress=project_progress,
        next_valid_action=next_valid_action,
    )


def _raw_present(raw_root: Path, dataset: DatasetId) -> BooleanValue:
    return (raw_root / dataset_specification(dataset).raw_data_relative).is_dir()


def _prepared_present(dataset: DatasetId) -> BooleanValue:
    prepared = REPOSITORY_ROOT / prepared_evidence_root(dataset)
    return prepared.is_dir() and any(prepared.rglob("*.parquet"))


def _dataset_readiness(raw_root: Path) -> ExperimentLifecycleState:
    raw_ready = all(_raw_present(raw_root, dataset) for dataset in DatasetId)
    prepared_ready = all(_prepared_present(dataset) for dataset in DatasetId)
    if prepared_ready:
        return ExperimentLifecycleState.COMPLETED
    if raw_ready:
        return ExperimentLifecycleState.READY
    if any(_raw_present(raw_root, dataset) for dataset in DatasetId):
        return ExperimentLifecycleState.RUNNING
    return ExperimentLifecycleState.NOT_STARTED


def _artifact_summary(
    dataset_readiness: ExperimentLifecycleState,
    resolved_core_present: ResolvedCoreComplete,
) -> DoctorArtifactSummary:
    prepared_parts: list[str] = []
    for dataset in DatasetId:
        status = "prepared" if _prepared_present(dataset) else "missing prepared views"
        prepared_parts.append(f"{dataset.value} {status}")
    core_status = "present" if resolved_core_present else "absent"
    return (
        f"{'; '.join(prepared_parts)}; "
        f"dataset readiness {dataset_readiness.value}; "
        f"resolved core {core_status}"
    )


def _experiment_state(
    plan: ExperimentPlan, store: ExecutionRecordStore, name: ExperimentName
) -> ExperimentLifecycleState:
    planned = plan.experiment(name)
    records = store.read_all_outcomes(name)
    return derive_experiment_lifecycle(planned, records)


def _experiment_summary(
    plan: ExperimentPlan, store: ExecutionRecordStore
) -> DoctorExperimentSummary:
    completed = 0
    blocked = 0
    running = 0
    failed = 0
    ready = 0
    for planned in plan.experiments:
        state = _experiment_state(plan, store, planned.definition.name)
        if state is ExperimentLifecycleState.COMPLETED:
            completed += 1
        elif state is ExperimentLifecycleState.BLOCKED:
            blocked += 1
        elif state is ExperimentLifecycleState.RUNNING:
            running += 1
        elif state in (ExperimentLifecycleState.FAILED, ExperimentLifecycleState.INVALID):
            failed += 1
        else:
            ready += 1
    return (
        f"{completed} completed, {running} running, {ready} ready, "
        f"{blocked} blocked, {failed} failed/invalid of {len(plan.experiments)} experiments"
    )


def _smoke_complete() -> BooleanValue:
    record_path = REPOSITORY_ROOT / smoke_record_path()
    if not record_path.is_file():
        return False
    record = PersistedSmokeRecord.model_validate_json(record_path.read_text(encoding="utf-8"))
    return record.passed


def _all_complete(
    names: tuple[ExperimentName, ...],
    plan: ExperimentPlan,
    store: ExecutionRecordStore,
) -> BooleanValue:
    return all(
        _experiment_state(plan, store, name) is ExperimentLifecycleState.COMPLETED for name in names
    )


def _project_stage(
    environment_mismatches: tuple[EnvironmentMismatch, ...],
    dataset_readiness: ExperimentLifecycleState,
    plan: ExperimentPlan,
    store: ExecutionRecordStore,
    resolved_core_present: ResolvedCoreComplete,
) -> ProjectStage:
    if environment_mismatches:
        return ProjectStage.DOCTOR_READINESS
    if dataset_readiness is not ExperimentLifecycleState.COMPLETED:
        return ProjectStage.PREPROCESSING_AND_DATA_VALIDATION
    if not _smoke_complete():
        return ProjectStage.PROTOCOL_INVARIANT_SMOKE
    if _experiment_state(plan, store, BASELINE_IMPLEMENTATION_VALIDATION_NAME) is not (
        ExperimentLifecycleState.COMPLETED
    ):
        return ProjectStage.BASELINE_IMPLEMENTATION_VALIDATION
    if not _all_complete(COLLAPSE_EXPERIMENT_NAMES, plan, store):
        return ProjectStage.MECHANISM_COLLAPSE
    if not resolved_core_present:
        return ProjectStage.RESOLVED_CORE_DERIVATION
    if _experiment_state(plan, store, PRIMARY_CONFIRMATORY_EVALUATION_NAME) is not (
        ExperimentLifecycleState.COMPLETED
    ):
        return ProjectStage.PRIMARY_CONFIRMATORY_EVALUATION
    if (
        _experiment_state(plan, store, MECHANISM_ABLATION_NAME)
        is not ExperimentLifecycleState.COMPLETED
    ):
        return ProjectStage.MECHANISM_ABLATIONS
    if not _all_complete(_BYZANTINE_EXPERIMENT_NAMES, plan, store):
        return ProjectStage.BYZANTINE_ROBUSTNESS
    if not _all_complete(_BOUNDARY_EXPERIMENT_NAMES, plan, store):
        return ProjectStage.EVIDENCE_AND_FAILURE_BOUNDARIES
    if not _all_complete(_DELAY_EXPERIMENT_NAMES, plan, store):
        return ProjectStage.DELAY_AND_EFFICIENCY
    if _experiment_state(plan, store, SECONDARY_DATASET_GENERALIZATION_NAME) is not (
        ExperimentLifecycleState.COMPLETED
    ):
        return ProjectStage.SECONDARY_GENERALIZATION
    if not (REPOSITORY_ROOT / manuscript_tables_root(project_summary_root())).exists():
        return ProjectStage.STATISTICAL_EVIDENCE_COMPLETION
    return ProjectStage.REPORT_EXPORT


class StageGuidance(FrozenDomainModel):
    stage: ProjectStage
    progress: ProjectProgressDescription
    action: NextValidAction


STAGE_GUIDANCE: tuple[StageGuidance, ...] = (
    StageGuidance(
        stage=ProjectStage.DOCTOR_READINESS,
        progress="doctor readiness checks complete",
        action="run fedsira preprocess to prepare roadmap datasets",
    ),
    StageGuidance(
        stage=ProjectStage.PREPROCESSING_AND_DATA_VALIDATION,
        progress="raw inputs identified; preprocessing is incomplete",
        action="run fedsira preprocess to prepare roadmap datasets",
    ),
    StageGuidance(
        stage=ProjectStage.PROTOCOL_INVARIANT_SMOKE,
        progress="preprocessing artifacts are present; protocol smoke has not completed",
        action="run fedsira smoke",
    ),
    StageGuidance(
        stage=ProjectStage.BASELINE_IMPLEMENTATION_VALIDATION,
        progress="smoke evidence exists; baseline implementation validation is incomplete",
        action="run fedsira run 'Baseline Implementation Validation'",
    ),
    StageGuidance(
        stage=ProjectStage.MECHANISM_COLLAPSE,
        progress="baseline validation is complete; collapse experiments are incomplete",
        action="run the four collapse experiments in Section 29 order",
    ),
    StageGuidance(
        stage=ProjectStage.RESOLVED_CORE_DERIVATION,
        progress="collapse experiments are complete; resolved core artifact is absent",
        action=(
            "run fedsira run on a completed collapse experiment to materialize the resolved core"
        ),
    ),
    StageGuidance(
        stage=ProjectStage.PRIMARY_CONFIRMATORY_EVALUATION,
        progress="resolved core is present; primary confirmatory evaluation is incomplete",
        action="run fedsira run 'Primary Confirmatory Evaluation'",
    ),
    StageGuidance(
        stage=ProjectStage.MECHANISM_ABLATIONS,
        progress="primary confirmatory evaluation is complete; mechanism ablations are incomplete",
        action="run fedsira run 'Mechanism Ablation'",
    ),
    StageGuidance(
        stage=ProjectStage.BYZANTINE_ROBUSTNESS,
        progress=(
            "mechanism ablations are complete; Byzantine robustness experiments are incomplete"
        ),
        action="run the Byzantine robustness experiments",
    ),
    StageGuidance(
        stage=ProjectStage.EVIDENCE_AND_FAILURE_BOUNDARIES,
        progress="Byzantine robustness is complete; scientific boundary experiments are incomplete",
        action="run the evidence and failure-boundary experiments",
    ),
    StageGuidance(
        stage=ProjectStage.DELAY_AND_EFFICIENCY,
        progress=(
            "boundary experiments are complete; delay and efficiency measurements are incomplete"
        ),
        action="run fedsira run 'Admission-Delay Decomposition'",
    ),
    StageGuidance(
        stage=ProjectStage.SECONDARY_GENERALIZATION,
        progress=(
            "delay and efficiency measurements are complete; secondary generalization is incomplete"
        ),
        action="run fedsira run 'Secondary-Dataset Generalization'",
    ),
    StageGuidance(
        stage=ProjectStage.STATISTICAL_EVIDENCE_COMPLETION,
        progress=(
            "scientific experiments have terminal records; manuscript evidence export is incomplete"
        ),
        action="run fedsira report",
    ),
    StageGuidance(
        stage=ProjectStage.REPORT_EXPORT,
        progress="project summary export artifacts exist",
        action="run fedsira report to refresh verified manuscript-facing evidence",
    ),
)


def _progress_and_action(
    environment_mismatches: tuple[EnvironmentMismatch, ...],
    project_stage: ProjectStage,
) -> tuple[ProjectProgressDescription, NextValidAction]:
    if environment_mismatches:
        return (
            "doctor blocked by environment mismatch",
            "resolve the reported environment mismatches",
        )
    for guidance in STAGE_GUIDANCE:
        if guidance.stage is project_stage:
            return guidance.progress, guidance.action
    raise ValueError(f"unmapped project stage: {project_stage.value}")


def render(report: DoctorReport, console: Console) -> None:
    console.print("FedSIRA doctor")
    if report.configuration_loadable:
        console.print("configuration: valid")
    else:
        console.print(f"configuration: INVALID ({report.configuration_error})")
    if report.environment_mismatches:
        console.print("environment: mismatches found")
        for mismatch in report.environment_mismatches:
            console.print(
                f"  {mismatch.component}: expected {mismatch.expected}, found {mismatch.actual}"
            )
    else:
        console.print("environment: matches the reference environment")
    console.print(f"dataset readiness: {report.dataset_readiness.value}")
    console.print(f"artifacts: {report.artifact_validity_summary}")
    console.print(f"experiments: {report.experiment_summary}")
    console.print(f"project stage: {report.project_stage.value}")
    console.print(f"project progress: {report.project_progress}")
    console.print(f"next valid action: {report.next_valid_action}")


RESOLVED_CORE_PUBLISHED_DIRECTORY = workspace_root_for_family(
    ArtifactFamily.FIXED_PROTOCOL_CONFIGURATION
)
_COLLAPSE_FAMILIES: tuple[ComparisonFamily, ...] = (
    ComparisonFamily.PROPOSAL_SCREEN_NECESSITY,
    ComparisonFamily.PLURALITY_NECESSITY,
    ComparisonFamily.SOURCE_EXCLUSION_CENTRAL_EFFECT,
    ComparisonFamily.EXTERNAL_VERIFICATION_NECESSITY,
)


def render_result(result: ExperimentExecutionResult) -> RunRenderText:
    lines: list[RunRenderText] = [
        f"FedSIRA run: {result.experiment}",
        f"experiment state: {result.lifecycle_state.value}",
        f"cells: {result.cell_completion_count}/{len(result.outcomes)} completed",
    ]
    for outcome in result.outcomes:
        lines.append(
            f"  {outcome.cell.method:<45} {outcome.cell.condition:<40} "
            f"seed={outcome.cell.master_seed:>5} -> {outcome.terminal_state.value}"
        )
    if result.comparison_results:
        lines.extend(("", "comparisons:"))
        for family in result.comparison_results:
            lines.append(f"  family: {family.family.value}")
            for comparison in family.comparisons:
                p_value = (
                    f"p={comparison.adjusted_p_value:.4f}"
                    if comparison.adjusted_p_value is not None
                    else "p=NA"
                )
                lines.append(
                    f"    {comparison.definition.comparison_name:<110} "
                    f"{comparison.comparison_state.value:<22} {p_value}"
                )
    return "\n".join(lines)


def _collapse_family_for_experiment(experiment: ExperimentName) -> ComparisonFamily | None:
    definition = experiment_by_name(experiment)
    if definition.comparison_family not in _COLLAPSE_FAMILIES:
        return None
    return definition.comparison_family


def _collapse_experiment_completed(
    experiment: ExperimentName, store: ExecutionRecordStore
) -> BooleanValue:
    config = current_application_context().scientific_config
    definition = experiment_by_name(experiment)
    planned = build_plan(
        resolved_core_complete=False,
        master_seeds=config.seeds_and_determinism.master_seeds,
        smoke_seed=config.seeds_and_determinism.smoke_seed,
    ).experiment(experiment)
    lifecycle = derive_experiment_lifecycle(planned, store.read_planned_outcomes(planned))
    return (
        lifecycle is ExperimentLifecycleState.COMPLETED
        and len(store.read_all_outcomes(experiment)) == definition.nominal_cell_count
    )


def _materialize_core_if_complete(experiment: ExperimentName) -> None:
    if experiment not in COLLAPSE_EXPERIMENT_NAMES:
        return
    config = current_application_context().scientific_config
    store = ExecutionRecordStore(
        REPOSITORY_ROOT / Path(config.execution.repository_layout.execution_workspace)
    )
    for collapse_experiment in COLLAPSE_EXPERIMENT_NAMES:
        if not _collapse_experiment_completed(collapse_experiment, store):
            return
    decisions: list[CollapseDecision] = []
    for collapse_experiment in COLLAPSE_EXPERIMENT_NAMES:
        records = store.read_all_outcomes(collapse_experiment)
        outcomes = tuple(
            CellExecutionOutcome(
                cell=ScientificCell(
                    experiment=record.experiment,
                    method=record.method,
                    condition=record.condition,
                    master_seed=record.master_seed,
                ),
                terminal_state=record.terminal_state,
                failure=None,
                metrics=record.metrics,
            )
            for record in records
        )
        definition = experiment_by_name(collapse_experiment)
        comparison_results = comparison_results_for_experiment(
            collapse_experiment, definition.dataset, outcomes, store
        )
        family = _collapse_family_for_experiment(collapse_experiment)
        if family is None:
            return
        evaluation = collapse_evaluation_from_records(collapse_experiment, records)
        if evaluation is None:
            return
        decisions.append(
            collapse_decision_from_comparison_families(
                family,
                comparison_results,
                evaluation=evaluation,
                materiality_config=config.metrics_and_statistics.materiality,
            )
        )
    if len(decisions) != len(COLLAPSE_EXPERIMENT_NAMES):
        return
    core = materialize_resolved_core(tuple(decisions))
    publish_resolved_core(REPOSITORY_ROOT / RESOLVED_CORE_PUBLISHED_DIRECTORY, core)
    print(f"Resolved FedSIRA Core materialized: {core.decision_identity}")


def _export_completed_experiment(result: ExperimentExecutionResult) -> None:
    if result.lifecycle_state is not ExperimentLifecycleState.COMPLETED:
        return
    experiment_root = REPOSITORY_ROOT / workspace_root_for_family(
        ArtifactFamily.TABLE_FIGURE_SOURCE_DATA,
        result.experiment,
    )
    export = export_experiment_report(result, experiment_root)
    if not export.verification.passed:
        raise RuntimeError(
            f"completed experiment report export failed: {', '.join(export.verification.failures)}"
        )
    for path in export.exported_paths:
        print(f"exported {path}")


def execute_run(name: ExperimentName, overwrite: OverwriteExisting) -> None:
    context = ApplicationContext.load(REPOSITORY_ROOT)
    with bound_application_context(context):
        configure_deterministic_backend()
        _execute_bound(name, overwrite)


def _execute_bound(name: ExperimentName, overwrite: OverwriteExisting) -> None:
    resolved_core = read_resolved_core(REPOSITORY_ROOT / RESOLVED_CORE_PUBLISHED_DIRECTORY)
    result = execute_experiment(
        name,
        ProtocolCellExecutor(resolved_core=resolved_core),
        comparison_results_for_experiment,
        overwrite=overwrite,
        resolved_core_complete=resolved_core is not None,
    )
    print(render_result(result))
    _export_completed_experiment(result)
    if (
        result.lifecycle_state is ExperimentLifecycleState.COMPLETED
        and (not overwrite)
        and result.execution_digest
    ):
        print(f"already-completed: execution digest {result.execution_digest}")
    if result.lifecycle_state is ExperimentLifecycleState.COMPLETED:
        _materialize_core_if_complete(name)
    if result.lifecycle_state in (
        ExperimentLifecycleState.FAILED,
        ExperimentLifecycleState.INVALID,
        ExperimentLifecycleState.BLOCKED,
    ):
        raise SystemExit(1)


class FedSIRAApplication:
    def doctor(self, console: Console) -> ApplicationExitCode:
        report = diagnose()
        render(report, console)
        return 0 if report.is_deterministic_execution_ready else 1

    def preprocess(
        self, dataset: DatasetId | None, overwrite: OverwriteExisting
    ) -> ApplicationExitCode:
        execute_preprocess(dataset, overwrite)
        return 0

    def plan(self) -> ApplicationExitCode:
        execute_plan()
        return 0

    def smoke(self, overwrite: OverwriteExisting) -> ApplicationExitCode:
        execute_smoke(overwrite)
        return 0

    def run(self, name: ExperimentName, overwrite: OverwriteExisting) -> ApplicationExitCode:
        execute_run(name, overwrite)
        return 0

    def status(self) -> ApplicationExitCode:
        execute_status()
        return 0

    def report(
        self, name: ExperimentName | None, overwrite: OverwriteExisting
    ) -> ApplicationExitCode:
        execute_report(name, overwrite)
        return 0
