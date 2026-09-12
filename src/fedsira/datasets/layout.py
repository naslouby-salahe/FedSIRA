from pathlib import Path

from fedsira.artifacts.paths import prepared_evidence_root
from fedsira.datasets.common import dataset_specification
from fedsira.domain.enums import DatasetId, ExperimentLifecycleState
from fedsira.domain.types import BooleanValue, FailureMessage
from fedsira.runtime import REPOSITORY_ROOT, current_application_context


def raw_dataset_root(dataset: DatasetId) -> Path | None:
    layout = current_application_context().scientific_config.execution.repository_layout
    relative = dataset_specification(dataset).raw_data_relative
    repository_root = current_application_context().repository_root
    for candidate in (
        repository_root / layout.raw_data / relative,
        Path(layout.external_data) / relative,
    ):
        if candidate.exists():
            return candidate
    return None


def required_raw_dataset_root(dataset: DatasetId) -> Path:
    root = raw_dataset_root(dataset)
    if root is None:
        raise ValueError(f"raw data for {dataset.value} is present under no configured root")
    return root


def validate_repository_layout() -> tuple[FailureMessage, ...]:
    layout = current_application_context().scientific_config.execution.repository_layout
    repository_root = current_application_context().repository_root
    failures: list[FailureMessage] = []
    if not (repository_root / layout.source).is_dir():
        failures.append(f"configured source root is missing: {layout.source}")
    if not (repository_root / layout.tests).is_dir():
        failures.append(f"configured tests root is missing: {layout.tests}")
    if not (repository_root / layout.raw_data).exists():
        failures.append(f"configured raw data root is missing: {layout.raw_data}")
    if not (repository_root / layout.manuscript_results).exists():
        failures.append(
            f"configured manuscript results root is missing: {layout.manuscript_results}"
        )
    return tuple(failures)


def raw_dataset_present(dataset: DatasetId) -> BooleanValue:
    return raw_dataset_root(dataset) is not None


def prepared_dataset_present(dataset: DatasetId) -> BooleanValue:
    prepared = REPOSITORY_ROOT / prepared_evidence_root(dataset)
    return prepared.is_dir() and any(prepared.rglob("*.parquet"))


def rar_archives_present(raw_data_root: Path) -> BooleanValue:
    return raw_data_root.exists() and any(raw_data_root.rglob("*.rar"))


def dataset_readiness() -> ExperimentLifecycleState:
    if all(prepared_dataset_present(dataset) for dataset in DatasetId):
        return ExperimentLifecycleState.COMPLETED
    if all(raw_dataset_present(dataset) for dataset in DatasetId):
        return ExperimentLifecycleState.READY
    if any(raw_dataset_present(dataset) for dataset in DatasetId):
        return ExperimentLifecycleState.RUNNING
    return ExperimentLifecycleState.NOT_STARTED
