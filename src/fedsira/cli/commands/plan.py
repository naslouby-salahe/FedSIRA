from fedsira.cli.commands import ScientificPipelineNotImplementedError


def execute() -> None:
    raise ScientificPipelineNotImplementedError(
        "fedsira plan is not implemented until the M04 experiment-registry milestone"
    )
