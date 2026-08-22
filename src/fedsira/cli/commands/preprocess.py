from fedsira.cli.commands import REPOSITORY_ROOT, ScientificPipelineNotImplementedError
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.config.schema import ScientificConfig
from fedsira.datasets.nbaiot.acquisition import (
    DiscoveredCsvFile,
    compute_dataset_manifest_hash,
    discover_primary_csv_files,
)
from fedsira.datasets.nbaiot.preprocessing import (
    RoleAssignment,
    assign_stream_roles_and_sample_ids,
    count_csv_data_rows,
    read_predictor_header,
    validate_all_predictors_finite,
    validate_consistent_predictor_schema,
    validate_predictor_schema,
)
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_HASH_TOKEN
from fedsira.datasets.nbaiot.validation import (
    classes_structurally_unavailable,
    validate_target_holder_feasibility,
)
from fedsira.domain.enums import DatasetId
from fedsira.domain.records import NonNegativeInt


def _validate_nbaiot_raw_data() -> tuple[str, tuple[str, ...], NonNegativeInt]:
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

    reference_file = discovered[0]
    reference_header = read_predictor_header(reference_file.absolute_path)
    validate_predictor_schema(reference_header)
    validate_all_predictors_finite(reference_file.absolute_path, reference_header)

    total_role_assignments = 0
    for item in discovered:
        observed_header = read_predictor_header(item.absolute_path)
        validate_consistent_predictor_schema(reference_header, observed_header)
        total_role_assignments += len(_assign_roles_for_stream(item, config))

    return manifest_hash, unavailable_classes, total_role_assignments


def _assign_roles_for_stream(
    item: DiscoveredCsvFile, config: ScientificConfig
) -> tuple[RoleAssignment, ...]:
    row_count = count_csv_data_rows(item.absolute_path)
    return assign_stream_roles_and_sample_ids(
        dataset_file_sha256=item.file_sha256,
        domain_hash_token=NBAIOT_DOMAIN_HASH_TOKEN[item.domain],
        class_id=item.class_id,
        normalized_relative_csv_path=f"{item.domain.value}/{item.relative_path}",
        stream_row_count=row_count,
        role_intervals=config.datasets.primary.role_intervals,
        sampling_caps_per_domain=config.datasets.primary.sampling_caps_per_domain,
    )


def execute(dataset: DatasetId | None, overwrite: bool) -> None:
    if dataset is DatasetId.N_BAIOT:
        manifest_hash, unavailable_classes, total_role_assignments = _validate_nbaiot_raw_data()
        raise ScientificPipelineNotImplementedError(
            "N-BaIoT raw data discovered and validated "
            f"(dataset_file_manifest_hash={manifest_hash}, "
            f"structurally_unavailable_classes={list(unavailable_classes)}, "
            f"total_role_assignments={total_role_assignments}); "
            "prepared-view/scaler artifact publication is not implemented until M02 — I10"
        )
    raise ScientificPipelineNotImplementedError(
        "fedsira preprocess is not implemented until the M02 dataset-preparation milestone"
    )
