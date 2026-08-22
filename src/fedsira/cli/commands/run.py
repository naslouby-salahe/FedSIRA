from fedsira.cli.commands import ScientificPipelineNotImplementedError


def execute(name: str, overwrite: bool) -> None:
    raise ScientificPipelineNotImplementedError(
        f"fedsira run {name!r} is not yet implemented: experiment execution is not available"
    )
