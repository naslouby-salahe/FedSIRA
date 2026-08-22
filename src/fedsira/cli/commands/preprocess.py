from fedsira.cli.commands import ScientificPipelineNotImplementedError
from fedsira.domain.enums import DatasetId


def execute(dataset: DatasetId | None, overwrite: bool) -> None:
    raise ScientificPipelineNotImplementedError(
        "fedsira preprocess is not implemented until the M02 dataset-preparation milestone"
    )
