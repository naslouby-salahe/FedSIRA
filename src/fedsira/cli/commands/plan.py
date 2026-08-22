from fedsira.cli.commands import ScientificPipelineNotImplementedError


def execute() -> None:
    raise ScientificPipelineNotImplementedError(
        "fedsira plan is not yet implemented: the experiment registry is not available"
    )
