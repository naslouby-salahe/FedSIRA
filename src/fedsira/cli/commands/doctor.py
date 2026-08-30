from pathlib import Path

from rich.console import Console

from fedsira.cli.commands import REPOSITORY_ROOT
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import ExperimentLifecycleState
from fedsira.domain.records import (
    ConfigurationLoadable,
    DeterministicExecutionReady,
    DoctorArtifactSummary,
    DoctorExperimentSummary,
    FailureMessage,
    FrozenDomainModel,
    NextValidAction,
    ProjectProgressDescription,
)
from fedsira.runtime.environment import EnvironmentMismatch, collect_environment_mismatches


class DoctorReport(FrozenDomainModel):
    environment_mismatches: tuple[EnvironmentMismatch, ...]
    configuration_loadable: ConfigurationLoadable
    configuration_error: FailureMessage | None
    dataset_readiness: ExperimentLifecycleState
    artifact_validity_summary: DoctorArtifactSummary
    experiment_summary: DoctorExperimentSummary
    project_progress: ProjectProgressDescription
    next_valid_action: NextValidAction

    @property
    def is_deterministic_execution_ready(self) -> DeterministicExecutionReady:
        return len(self.environment_mismatches) == 0 and self.configuration_loadable


def diagnose(config_path: Path = PRODUCTION_CONFIG_PATH) -> DoctorReport:
    raw_data_path = REPOSITORY_ROOT / "data" / "raw"
    rar_archives_present = raw_data_path.exists() and any(raw_data_path.rglob("*.rar"))
    environment_mismatches = collect_environment_mismatches(REPOSITORY_ROOT, rar_archives_present)
    configuration_loadable: ConfigurationLoadable = True
    configuration_error: FailureMessage | None = None
    try:
        load_scientific_config(config_path)
    except ValueError as error:
        configuration_loadable = False
        configuration_error = str(error)

    if not configuration_loadable:
        project_progress: ProjectProgressDescription = "doctor blocked by invalid configuration"
        next_valid_action: NextValidAction = "fix configs/fedsira.yaml until validation succeeds"
    elif environment_mismatches:
        project_progress = "doctor blocked by environment mismatch"
        next_valid_action = "resolve the reported environment mismatches"
    else:
        project_progress = "doctor readiness checks complete"
        next_valid_action = "run fedsira preprocess to prepare roadmap datasets"

    return DoctorReport(
        environment_mismatches=environment_mismatches,
        configuration_loadable=configuration_loadable,
        configuration_error=configuration_error,
        dataset_readiness=ExperimentLifecycleState.NOT_STARTED,
        artifact_validity_summary="no artifacts published yet",
        experiment_summary="no experiments started yet",
        project_progress=project_progress,
        next_valid_action=next_valid_action,
    )


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
    console.print(f"project progress: {report.project_progress}")
    console.print(f"next valid action: {report.next_valid_action}")
