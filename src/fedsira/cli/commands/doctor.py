from pathlib import Path

from rich.console import Console

from fedsira.artifacts.provenance import classify_provenance_change, outcome_invalidates_artifact
from fedsira.cli.commands import REPOSITORY_ROOT
from fedsira.domain.enums import ArtifactFamily, DatasetId, ExperimentLifecycleState, ProjectStage
from fedsira.domain.types import (
    BooleanValue,
    ConfigurationLoadable,
    DeterministicExecutionReady,
    DoctorArtifactSummary,
    DoctorExperimentSummary,
    ExperimentName,
    FailureMessage,
    FrozenDomainModel,
    NextValidAction,
    ProjectProgressDescription,
    ResolvedCoreComplete,
)
from fedsira.experiments.collapse import read_resolved_core
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
)
from fedsira.experiments.planning import ExperimentPlan, build_plan
from fedsira.experiments.runner import ExecutionRecordStore, derive_experiment_lifecycle
from fedsira.io.paths import (
    prepared_evidence_root,
    smoke_record_path,
    workspace_root_for_family,
)
from fedsira.runtime.environment import EnvironmentMismatch, collect_environment_mismatches
from fedsira.runtime.logging import get_structured_logger
from fedsira.runtime.state import ApplicationContext, bound_application_context

_LOGGER = get_structured_logger("doctor")
_CICIOT2023_RAW_RELATIVE = Path("CIC_IOT_Dataset2023") / "CSV"
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
    raw_data_path = REPOSITORY_ROOT / "data" / "raw"
    rar_archives_present = raw_data_path.exists() and any(raw_data_path.rglob("*.rar"))
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
    with bound_application_context(context):
        environment_mismatches = collect_environment_mismatches(
            REPOSITORY_ROOT, rar_archives_present
        )
        return _diagnose_bound(context, environment_mismatches)


def _diagnose_bound(
    context: ApplicationContext,
    environment_mismatches: tuple[EnvironmentMismatch, ...],
) -> DoctorReport:
    raw_root = REPOSITORY_ROOT / context.scientific_config.runtime.repository_layout.raw_data
    workspace = (
        REPOSITORY_ROOT / context.scientific_config.runtime.repository_layout.execution_workspace
    )
    store = ExecutionRecordStore(workspace)
    resolved_core = read_resolved_core(REPOSITORY_ROOT / _RESOLVED_CORE_DIRECTORY)
    plan = build_plan(
        resolved_core_complete=resolved_core is not None,
        master_seeds=context.scientific_config.seeds_and_determinism.master_seeds,
        smoke_seed=context.scientific_config.seeds_and_determinism.smoke_seed,
    )
    if outcome_invalidates_artifact(classify_provenance_change(False, False, False, False)):
        raise RuntimeError("empty provenance change must remain non-material")
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
    if dataset is DatasetId.N_BAIOT:
        return (raw_root / dataset.value).is_dir()
    return (raw_root / _CICIOT2023_RAW_RELATIVE).is_dir()


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
    return record_path.is_file()


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
    results_root = REPOSITORY_ROOT / "results" / "project_summary"
    if not (results_root / "claim_registry").exists():
        return ProjectStage.STATISTICAL_CLAIM_COMPLETION
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
        stage=ProjectStage.STATISTICAL_CLAIM_COMPLETION,
        progress=(
            "scientific experiments have terminal records; manuscript claim export is incomplete"
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
