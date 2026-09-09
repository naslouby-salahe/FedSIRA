import typer
from rich.console import Console

from fedsira.application import FedSIRAApplication
from fedsira.domain.enums import DatasetId
from fedsira.domain.types import ExperimentName, OverwriteExisting

app = typer.Typer(name="fedsira", no_args_is_help=True)
console = Console()
application = FedSIRAApplication()


@app.command()
def doctor() -> None:
    raise typer.Exit(code=application.doctor(console))


@app.command()
def preprocess(
    dataset: DatasetId | None = typer.Argument(None),
    overwrite: OverwriteExisting = typer.Option(False, "--overwrite"),
) -> None:
    raise typer.Exit(code=application.preprocess(dataset, overwrite))


@app.command()
def plan() -> None:
    raise typer.Exit(code=application.plan())


@app.command()
def smoke(overwrite: OverwriteExisting = typer.Option(False, "--overwrite")) -> None:
    raise typer.Exit(code=application.smoke(overwrite))


@app.command(name="run")
def run_experiment(
    name: ExperimentName = typer.Argument(...),
    overwrite: OverwriteExisting = typer.Option(False, "--overwrite"),
) -> None:
    raise typer.Exit(code=application.run(name, overwrite))


@app.command()
def report(
    name: ExperimentName | None = typer.Argument(None),
    overwrite: OverwriteExisting = typer.Option(False, "--overwrite"),
) -> None:
    raise typer.Exit(code=application.report(name, overwrite))


if __name__ == "__main__":
    app()
