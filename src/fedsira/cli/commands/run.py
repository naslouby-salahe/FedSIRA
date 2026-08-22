from fedsira.cli.commands import ScientificPipelineNotImplementedError


def execute(name: str, overwrite: bool) -> None:
    raise ScientificPipelineNotImplementedError(
        f"fedsira run {name!r} is not implemented until the experiment-execution milestone"
    )
