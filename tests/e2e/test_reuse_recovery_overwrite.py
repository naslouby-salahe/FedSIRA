from typer.testing import CliRunner

from fedsira.cli.main import app

runner = CliRunner()


def test_mutating_commands_expose_overwrite_and_not_scientific_overrides() -> None:
    for command in ("preprocess", "smoke", "run", "report"):
        result = runner.invoke(app, [command, "--help"])
        assert "--overwrite" in result.stdout
        lowered = result.stdout.lower()
        for forbidden in ("--seed", "--method", "--baseline", "--attack", "--phase"):
            assert forbidden not in lowered
