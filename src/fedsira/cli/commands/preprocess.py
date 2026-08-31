from fedsira.artifacts.fingerprints import (
    compute_artifact_dependency_fingerprint,
    compute_external_dependency_fingerprint,
    compute_producer_component_fingerprint,
    producer_fingerprint_specification,
    raw_schema_exclusion_manifest_entry_modules,
)
from fedsira.artifacts.paths import (
    prepared_evidence_root,
    prepared_feature_root,
    preprocessing_metadata_root,
    workspace_root_for_family,
)
from fedsira.artifacts.records import (
    CICIoT2023DatasetManifestPayload,
    DatasetManifestPayload,
    NBaiotDatasetManifestPayload,
)
from fedsira.artifacts.storage import publish_or_reuse_artifact_payload
from fedsira.cli.commands import REPOSITORY_ROOT
from fedsira.config.schema import ScientificConfig
from fedsira.datasets.ciciot2023.acquisition import discover_secondary_csv_files
from fedsira.datasets.ciciot2023.preprocessing import materialize_ciciot2023_prepared_views
from fedsira.datasets.ciciot2023.schema import (
    OFFICIAL_EXPECTED_PREDICTOR_COUNT,
    PSEUDO_DOMAIN_COUNT,
)
from fedsira.datasets.nbaiot.acquisition import (
    compute_dataset_manifest_hash,
    discover_primary_csv_files,
)
from fedsira.datasets.nbaiot.preprocessing import (
    materialize_nbaiot_prepared_views,
    read_predictor_header,
    validate_all_predictors_finite,
    validate_consistent_predictor_schema,
    validate_predictor_schema,
)
from fedsira.datasets.nbaiot.validation import (
    classes_structurally_unavailable,
    validate_target_holder_feasibility,
)
from fedsira.domain.enums import ArtifactFamily, DatasetId, ProducerFingerprintFamily
from fedsira.domain.records import (
    ArtifactDigest,
    ArtifactReuseDecision,
    DatasetClassToken,
    DatasetManifestDigest,
    FingerprintPayload,
    OverwriteExisting,
    Probability,
    SchemaVersion,
)
from fedsira.runtime.state import (
    ApplicationContext,
    bound_application_context,
    current_application_context,
)

DATASET_MANIFEST_SCHEMA_VERSION: SchemaVersion = "1"


def _publish_dataset_manifest(
    dataset: DatasetId,
    config: ScientificConfig,
    dataset_split_view_identities: DatasetManifestDigest,
    payload: DatasetManifestPayload,
) -> ArtifactReuseDecision:
    entry_modules = raw_schema_exclusion_manifest_entry_modules(dataset)
    specification = producer_fingerprint_specification(
        ProducerFingerprintFamily.RAW_SCHEMA_EXCLUSION_MANIFEST
    )
    producer_fingerprint = compute_producer_component_fingerprint(
        entry_modules, schema_version=DATASET_MANIFEST_SCHEMA_VERSION
    )
    external_fingerprint = compute_external_dependency_fingerprint(
        entry_modules, specification.relevant_external_import_names
    )
    fingerprint_payload: FingerprintPayload = dataset.value
    identity: ArtifactDigest = compute_artifact_dependency_fingerprint(
        schema_version=DATASET_MANIFEST_SCHEMA_VERSION,
        scientific_configuration_subset=fingerprint_payload,
        dataset_split_view_identities=dataset_split_view_identities,
        semantic_coordinates_and_seed_namespaces=fingerprint_payload,
        upstream_artifact_identities=(),
        producer_component_fingerprint=producer_fingerprint,
        external_dependency_fingerprint=external_fingerprint,
    )
    _, reused = publish_or_reuse_artifact_payload(
        family=ArtifactFamily.DATASET_MANIFEST,
        identity=identity,
        payload=payload.model_dump_json().encode("utf-8"),
        published_directory=REPOSITORY_ROOT
        / workspace_root_for_family(ArtifactFamily.DATASET_MANIFEST),
        staging_root=REPOSITORY_ROOT
        / config.runtime.repository_layout.execution_workspace
        / "cache"
        / "staging",
    )
    return reused


def _preprocess_nbaiot(overwrite: OverwriteExisting) -> None:
    config = current_application_context().scientific_config
    raw_root = REPOSITORY_ROOT / config.runtime.repository_layout.raw_data / DatasetId.N_BAIOT.value
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
    unavailable_classes: tuple[DatasetClassToken, ...] = tuple(
        class_id.value for class_id in classes_structurally_unavailable(discovered)
    )
    reference_header = read_predictor_header(discovered[0].absolute_path)
    validate_predictor_schema(reference_header)
    for item in discovered:
        observed_header = read_predictor_header(item.absolute_path)
        validate_consistent_predictor_schema(reference_header, observed_header)
        validate_all_predictors_finite(item.absolute_path, reference_header)
    reused = _publish_dataset_manifest(
        DatasetId.N_BAIOT,
        config,
        manifest_hash,
        NBaiotDatasetManifestPayload(
            dataset_file_manifest_hash=manifest_hash,
            structurally_unavailable_classes=unavailable_classes,
        ),
    )
    views, moments = materialize_nbaiot_prepared_views(
        discovered,
        REPOSITORY_ROOT / prepared_evidence_root(DatasetId.N_BAIOT),
        REPOSITORY_ROOT / prepared_feature_root(),
        overwrite,
    )
    print(
        "N-BaIoT preprocessing complete: "
        f"dataset_file_manifest_hash={manifest_hash}, "
        f"structurally_unavailable_classes={list(unavailable_classes)}, "
        f"prepared_views={len(views)}, "
        f"scaler_training_rows={moments.training_row_count}, "
        f"dataset_manifest_reused={reused}"
    )


def _preprocess_ciciot2023(overwrite: OverwriteExisting) -> None:
    config = current_application_context().scientific_config
    csv_root = (
        REPOSITORY_ROOT / config.runtime.repository_layout.raw_data / "CIC_IOT_Dataset2023" / "CSV"
    )
    discovered = discover_secondary_csv_files(csv_root)
    cache_root = (
        REPOSITORY_ROOT
        / config.runtime.repository_layout.execution_workspace
        / "cache"
        / "preprocessing"
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
        DatasetId.CICIOT2023,
        config,
        summary.dataset_manifest_hash,
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
    print(
        "CICIoT2023 preprocessing complete: "
        f"dataset_file_manifest_hash={summary.dataset_manifest_hash}, "
        f"files={len(discovered)}, raw_rows={summary.raw_row_count}, "
        f"retained_rows={summary.retained_row_count}, "
        f"excluded_rows={summary.excluded_row_count}, "
        f"exclusion_rate={exclusion_rate:.8f}, "
        f"predictor_count={len(summary.predictor_columns)}, "
        f"predictor_count_matches_official={summary.predictor_count_matches_official}, "
        f"class_count={len(summary.class_registry)}, "
        f"prepared_views={len(summary.views)}, "
        f"scaler_training_rows={summary.scaler.training_row_count}, "
        f"dataset_manifest_reused={reused}"
    )


def execute(dataset: DatasetId | None, overwrite: OverwriteExisting) -> None:
    context = ApplicationContext.load(REPOSITORY_ROOT)
    with bound_application_context(context):
        _execute_bound(dataset, overwrite)


def _execute_bound(dataset: DatasetId | None, overwrite: OverwriteExisting) -> None:
    selected_datasets = tuple(DatasetId) if dataset is None else (dataset,)
    for selected_dataset in selected_datasets:
        if selected_dataset is DatasetId.N_BAIOT:
            _preprocess_nbaiot(overwrite)
        elif selected_dataset is DatasetId.CICIOT2023:
            _preprocess_ciciot2023(overwrite)
        else:
            raise ValueError(f"unsupported dataset identity: {selected_dataset}")
