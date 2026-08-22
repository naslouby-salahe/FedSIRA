import typer
from rich.console import Console

from fedsira.cli.commands import ScientificPipelineNotImplementedError
from fedsira.cli.commands import doctor as doctor_command
from fedsira.cli.commands import plan as plan_command
from fedsira.cli.commands import preprocess as preprocess_command
from fedsira.cli.commands import report as report_command
from fedsira.cli.commands import run as run_command
from fedsira.cli.commands import smoke as smoke_command
from fedsira.domain.enums import DatasetId

app = typer.Typer(name="fedsira", no_args_is_help=True)
console = Console()


@app.command()
def doctor() -> None:
    report = doctor_command.diagnose()
    doctor_command.render(report, console)
    if not report.is_deterministic_execution_ready:
        raise typer.Exit(code=1)


@app.command()
def preprocess(
    dataset: DatasetId | None = typer.Argument(None),
    overwrite: bool = typer.Option(False, "--overwrite"),
) -> None:
    try:
        preprocess_command.execute(dataset, overwrite)
    except ScientificPipelineNotImplementedError as error:
        console.print(str(error))
        raise typer.Exit(code=1) from error


@app.command()
def plan() -> None:
    try:
        plan_command.execute()
    except ScientificPipelineNotImplementedError as error:
        console.print(str(error))
        raise typer.Exit(code=1) from error


@app.command()
def smoke(overwrite: bool = typer.Option(False, "--overwrite")) -> None:
    try:
        smoke_command.execute(overwrite)
    except ScientificPipelineNotImplementedError as error:
        console.print(str(error))
        raise typer.Exit(code=1) from error


@app.command(name="run")
def run_experiment(
    name: str = typer.Argument(...),
    overwrite: bool = typer.Option(False, "--overwrite"),
) -> None:
    try:
        run_command.execute(name, overwrite)
    except ScientificPipelineNotImplementedError as error:
        console.print(str(error))
        raise typer.Exit(code=1) from error


@app.command()
def report(
    name: str | None = typer.Argument(None),
    overwrite: bool = typer.Option(False, "--overwrite"),
) -> None:
    try:
        report_command.execute(name, overwrite)
    except ScientificPipelineNotImplementedError as error:
        console.print(str(error))
        raise typer.Exit(code=1) from error


if __name__ == "__main__":
    app()
