from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import ExperimentLifecycleState
from fedsira.domain.records import CanonicalToken
from fedsira.runtime.environment import EnvironmentMismatch, collect_environment_mismatches

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class DoctorReport:
    environment_mismatches: tuple[EnvironmentMismatch, ...]
    configuration_loadable: bool
    configuration_error: CanonicalToken | None
    dataset_readiness: ExperimentLifecycleState
    artifact_validity_summary: CanonicalToken
    experiment_summary: CanonicalToken
    project_stage: CanonicalToken
    next_valid_action: CanonicalToken

    @property
    def is_deterministic_execution_ready(self) -> bool:
        return len(self.environment_mismatches) == 0 and self.configuration_loadable


def diagnose(config_path: Path = PRODUCTION_CONFIG_PATH) -> DoctorReport:
    raw_data_path = REPOSITORY_ROOT / "data" / "raw"
    rar_archives_present = raw_data_path.exists() and any(raw_data_path.rglob("*.rar"))
    environment_mismatches = collect_environment_mismatches(REPOSITORY_ROOT, rar_archives_present)
    configuration_loadable = True
    configuration_error: CanonicalToken | None = None
    try:
        load_scientific_config(config_path)
    except ValueError as error:
        configuration_loadable = False
        configuration_error = str(error)

    if not configuration_loadable:
        project_stage = "blocked before Stage 1: doctor readiness diagnosis"
        next_valid_action = "fix configs/fedsira.yaml until it loads and validates"
    elif environment_mismatches:
        project_stage = "blocked before Stage 1: doctor readiness diagnosis"
        next_valid_action = "resolve the reported environment mismatches"
    else:
        project_stage = "Stage 1 complete: doctor readiness diagnosis"
        next_valid_action = "run fedsira preprocess to begin Stage 2 data/domain validation"

    return DoctorReport(
        environment_mismatches=environment_mismatches,
        configuration_loadable=configuration_loadable,
        configuration_error=configuration_error,
        dataset_readiness=ExperimentLifecycleState.NOT_STARTED,
        artifact_validity_summary="no artifacts published yet",
        experiment_summary="no experiments started yet",
        project_stage=project_stage,
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
    console.print(f"project stage: {report.project_stage}")
    console.print(f"next valid action: {report.next_valid_action}")
