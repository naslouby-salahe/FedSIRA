from fedsira.cli.commands import ScientificPipelineNotImplementedError


def execute(overwrite: bool) -> None:
    raise ScientificPipelineNotImplementedError(
        "fedsira smoke is not implemented until the invariant-suite milestone"
    )
