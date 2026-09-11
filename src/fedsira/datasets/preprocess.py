from fedsira.artifacts.paths import (
    artifact_staging_root,
    prepared_evidence_root,
    prepared_feature_root,
    preprocessing_extraction_cache_root,
    preprocessing_log_path,
    preprocessing_metadata_root,
    workspace_root_for_family,
)
from fedsira.artifacts.provenance import (
    CICIoT2023DatasetManifestPayload,
    DatasetManifestPayload,
    NBaiotDatasetManifestPayload,
)
from fedsira.artifacts.storage import compute_checksum, publish_or_reuse_artifact_payload
from fedsira.datasets.ciciot2023.prepare import (
    discover_secondary_csv_files,
    materialize_ciciot2023_prepared_views,
)
from fedsira.datasets.ciciot2023.schema import (
    OFFICIAL_EXPECTED_PREDICTOR_COUNT,
    PSEUDO_DOMAIN_COUNT,
)
from fedsira.datasets.common import DatasetPreparationLogFields
from fedsira.datasets.nbaiot.prepare import (
    classes_structurally_unavailable,
    compute_dataset_manifest_hash,
    discover_primary_csv_files,
    materialize_nbaiot_prepared_views,
    validate_target_holder_feasibility,
)
from fedsira.datasets.specification import dataset_specification
from fedsira.domain.enums import ArtifactFamily, DatasetId
from fedsira.domain.types import (
    ArtifactDigest,
    ArtifactReuseDecision,
    DatasetClassToken,
    OverwriteExisting,
    Probability,
)
from fedsira.runtime import (
    REPOSITORY_ROOT,
    ApplicationContext,
    bound_application_context,
    configure_structured_file_logging,
    current_application_context,
    get_structured_logger,
    log_structured_event,
    mirror_structured_logging_to_console,
)

PREPROCESSING_LOGGER = get_structured_logger("preprocessing")


def _publish_dataset_manifest(payload: DatasetManifestPayload) -> ArtifactReuseDecision:
    serialized_payload = payload.model_dump_json().encode("utf-8")
    identity: ArtifactDigest = compute_checksum(serialized_payload)
    _, reused = publish_or_reuse_artifact_payload(
        family=ArtifactFamily.DATASET_MANIFEST,
        identity=identity,
        payload=serialized_payload,
        published_directory=REPOSITORY_ROOT
        / workspace_root_for_family(ArtifactFamily.DATASET_MANIFEST),
        staging_root=REPOSITORY_ROOT / artifact_staging_root(),
    )
    return reused


def _preprocess_nbaiot(overwrite: OverwriteExisting) -> None:
    config = current_application_context().scientific_config
    raw_root = (
        REPOSITORY_ROOT
        / config.execution.repository_layout.raw_data
        / dataset_specification(DatasetId.N_BAIOT).raw_data_relative
    )
    extraction_cache_root = preprocessing_extraction_cache_root(
        REPOSITORY_ROOT / config.execution.repository_layout.execution_workspace
    )
    log_structured_event(
        PREPROCESSING_LOGGER,
        "dataset.preprocessing.started",
        DatasetPreparationLogFields(dataset=DatasetId.N_BAIOT),
    )
    discovered = discover_primary_csv_files(raw_root, extraction_cache_root)
    validate_target_holder_feasibility(
        discovered,
        minimum_target_holding_domains=config.datasets.primary.minimum_target_holding_domains,
    )
    manifest_hash = compute_dataset_manifest_hash(discovered)
    unavailable_classes: tuple[DatasetClassToken, ...] = tuple(
        class_id for class_id in classes_structurally_unavailable(discovered)
    )
    reused = _publish_dataset_manifest(
        NBaiotDatasetManifestPayload(
            dataset_file_manifest_hash=manifest_hash,
            structurally_unavailable_classes=unavailable_classes,
        ),
    )
    prepared_root = REPOSITORY_ROOT / prepared_evidence_root(DatasetId.N_BAIOT)
    _views, moments = materialize_nbaiot_prepared_views(
        discovered,
        prepared_root,
        REPOSITORY_ROOT / prepared_feature_root(),
        overwrite,
        retain_materialized_views=False,
    )
    log_structured_event(
        PREPROCESSING_LOGGER,
        "dataset.preprocessing.completed",
        DatasetPreparationLogFields(
            dataset=DatasetId.N_BAIOT,
            dataset_file_manifest_hash=manifest_hash,
            structurally_unavailable_classes=unavailable_classes,
            prepared_views=len(tuple(prepared_root.glob("*.json"))),
            training_rows=moments.training_row_count,
            dataset_manifest_reused=reused,
        ),
    )


def _preprocess_ciciot2023(overwrite: OverwriteExisting) -> None:
    config = current_application_context().scientific_config
    csv_root = (
        REPOSITORY_ROOT
        / config.execution.repository_layout.raw_data
        / dataset_specification(DatasetId.CICIOT2023).raw_data_relative
    )
    log_structured_event(
        PREPROCESSING_LOGGER,
        "dataset.preprocessing.started",
        DatasetPreparationLogFields(dataset=DatasetId.CICIOT2023),
    )
    discovered = discover_secondary_csv_files(csv_root)
    cache_root = preprocessing_extraction_cache_root(
        REPOSITORY_ROOT / config.execution.repository_layout.execution_workspace
    )
    summary = materialize_ciciot2023_prepared_views(
        discovered,
        REPOSITORY_ROOT / prepared_evidence_root(DatasetId.CICIOT2023),
        REPOSITORY_ROOT / prepared_feature_root(),
        REPOSITORY_ROOT / preprocessing_metadata_root(),
        cache_root,
        overwrite,
    )
    reused = _publish_dataset_manifest(
        CICIoT2023DatasetManifestPayload(
            dataset_file_manifest_hash=summary.dataset_manifest_hash,
            file_count=len(discovered),
            raw_row_count=summary.raw_row_count,
            retained_row_count=summary.retained_row_count,
            excluded_row_count=summary.excluded_row_count,
            predictor_count=len(summary.predictor_columns),
            official_expected_predictor_count=OFFICIAL_EXPECTED_PREDICTOR_COUNT,
            predictor_count_matches_official=summary.predictor_count_matches_official,
            class_registry=summary.class_registry,
            pseudo_domain_count=PSEUDO_DOMAIN_COUNT,
        ),
    )
    exclusion_rate: Probability = (
        summary.excluded_row_count / summary.raw_row_count if summary.raw_row_count else 0.0
    )
    log_structured_event(
        PREPROCESSING_LOGGER,
        "dataset.preprocessing.completed",
        DatasetPreparationLogFields(
            dataset=DatasetId.CICIOT2023,
            dataset_file_manifest_hash=summary.dataset_manifest_hash,
            raw_rows=summary.raw_row_count,
            retained_rows=summary.retained_row_count,
            excluded_rows=summary.excluded_row_count,
            exclusion_rate=exclusion_rate,
            predictor_count=len(summary.predictor_columns),
            predictor_count_matches_official=summary.predictor_count_matches_official,
            class_count=len(summary.class_registry),
            prepared_views=len(summary.views),
            training_rows=summary.scaler.training_row_count,
            dataset_manifest_reused=reused,
        ),
    )


def execute_preprocess(dataset: DatasetId | None, overwrite: OverwriteExisting) -> None:
    context = ApplicationContext.load(REPOSITORY_ROOT)
    with bound_application_context(context):
        _execute_bound(dataset, overwrite)


def _execute_bound(dataset: DatasetId | None, overwrite: OverwriteExisting) -> None:
    configure_structured_file_logging(
        PREPROCESSING_LOGGER, REPOSITORY_ROOT / preprocessing_log_path()
    )
    mirror_structured_logging_to_console(PREPROCESSING_LOGGER)
    selected_datasets = tuple(DatasetId) if dataset is None else (dataset,)
    for selected_dataset in selected_datasets:
        if selected_dataset is DatasetId.N_BAIOT:
            _preprocess_nbaiot(overwrite)
        elif selected_dataset is DatasetId.CICIOT2023:
            _preprocess_ciciot2023(overwrite)
        else:
            raise ValueError(f"unsupported dataset identity: {selected_dataset}")
