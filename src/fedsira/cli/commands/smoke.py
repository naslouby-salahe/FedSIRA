from fedsira.cli.commands import ScientificPipelineNotImplementedError


def execute(overwrite: bool) -> None:
    raise ScientificPipelineNotImplementedError(
        "fedsira smoke is not yet implemented: the invariant suite is not available"
    )
