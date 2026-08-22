from fedsira.cli.commands import ScientificPipelineNotImplementedError


def execute(name: str | None, overwrite: bool) -> None:
    raise ScientificPipelineNotImplementedError(
        "fedsira report is not implemented until the reporting milestone"
    )
