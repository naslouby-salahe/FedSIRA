from __future__ import annotations

from rich.console import Console

from fedsira.domain.enums import DatasetId
from fedsira.domain.types import ApplicationExitCode, ExperimentName, OverwriteExisting
from fedsira.workflows import doctor as doctor_command
from fedsira.workflows import plan as plan_command
from fedsira.workflows import preprocess as preprocess_command
from fedsira.workflows import report as report_command
from fedsira.workflows import run as run_command
from fedsira.workflows import smoke as smoke_command


class FedSIRAApplication:
    def doctor(self, console: Console) -> ApplicationExitCode:
        report = doctor_command.diagnose()
        doctor_command.render(report, console)
        return 0 if report.is_deterministic_execution_ready else 1

    def preprocess(
        self, dataset: DatasetId | None, overwrite: OverwriteExisting
    ) -> ApplicationExitCode:
        preprocess_command.execute(dataset, overwrite)
        return 0

    def plan(self) -> ApplicationExitCode:
        plan_command.execute()
        return 0

    def smoke(self, overwrite: OverwriteExisting) -> ApplicationExitCode:
        smoke_command.execute(overwrite)
        return 0

    def run(self, name: ExperimentName, overwrite: OverwriteExisting) -> ApplicationExitCode:
        run_command.execute(name, overwrite)
        return 0

    def report(
        self, name: ExperimentName | None, overwrite: OverwriteExisting
    ) -> ApplicationExitCode:
        report_command.execute(name, overwrite)
        return 0
