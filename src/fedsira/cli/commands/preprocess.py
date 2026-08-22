from fedsira.cli.commands import REPOSITORY_ROOT, ScientificPipelineNotImplementedError
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.nbaiot.acquisition import (
    compute_dataset_manifest_hash,
    discover_primary_csv_files,
)
from fedsira.datasets.nbaiot.validation import (
    classes_structurally_unavailable,
    validate_target_holder_feasibility,
)
from fedsira.domain.enums import DatasetId


def _validate_nbaiot_raw_data() -> tuple[str, tuple[str, ...]]:
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    raw_root = REPOSITORY_ROOT / config.runtime.repository_layout.raw_data / "N-BaIoT"
    extraction_cache_root = (
        REPOSITORY_ROOT
        / config.runtime.repository_layout.execution_workspace
        / "cache"
        / "preprocessing"
    )
    discovered = discover_primary_csv_files(raw_root, extraction_cache_root)
    validate_target_holder_feasibility(
        discovered,
        minimum_target_holding_domains=config.datasets.primary.minimum_target_holding_domains,
    )
    manifest_hash = compute_dataset_manifest_hash(discovered)
    unavailable_classes = tuple(
        class_id.value for class_id in classes_structurally_unavailable(discovered)
    )
    return manifest_hash, unavailable_classes


def execute(dataset: DatasetId | None, overwrite: bool) -> None:
    if dataset is DatasetId.N_BAIOT:
        manifest_hash, unavailable_classes = _validate_nbaiot_raw_data()
        raise ScientificPipelineNotImplementedError(
            "N-BaIoT raw data discovered and validated "
            f"(dataset_file_manifest_hash={manifest_hash}, "
            f"structurally_unavailable_classes={list(unavailable_classes)}); "
            "role/split/sample/scaler materialization is not implemented until M02 — I10"
        )
    raise ScientificPipelineNotImplementedError(
        "fedsira preprocess is not implemented until the M02 dataset-preparation milestone"
    )
