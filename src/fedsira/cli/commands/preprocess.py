import json
from collections.abc import Mapping
from pathlib import Path

from fedsira.artifacts.fingerprints import (
    DATASET_PACKAGE_NAME,
    PRODUCER_RELEVANT_EXTERNAL_IMPORT_NAMES,
    compute_artifact_dependency_fingerprint,
    compute_external_dependency_fingerprint,
    compute_producer_component_fingerprint,
    raw_schema_exclusion_manifest_entry_modules,
)
from fedsira.artifacts.paths import (
    prepared_evidence_root,
    prepared_feature_root,
    preprocessing_metadata_root,
    workspace_root_for_family,
)
from fedsira.artifacts.records import ArtifactManifest
from fedsira.artifacts.storage import (
    compute_checksum,
    is_artifact_complete_and_valid,
    publish_artifact_to_disk,
    read_published_manifest,
    stage_payload,
)
from fedsira.cli.commands import REPOSITORY_ROOT
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
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
from fedsira.domain.enums import (
    ArtifactFamily,
    ArtifactLifecycleState,
    DatasetId,
    ProducerFingerprintFamily,
)
from fedsira.domain.records import ArtifactDigest, CanonicalToken


def _publish_or_reuse_canonical_dataset_manifest(
    dataset: DatasetId,
    config: ScientificConfig,
    dataset_split_view_identities: CanonicalToken,
    payload_fields: Mapping[str, object],
) -> tuple[ArtifactManifest, bool]:
    entry_modules = raw_schema_exclusion_manifest_entry_modules(dataset)
    producer_fingerprint = compute_producer_component_fingerprint(entry_modules, schema_version="1")
    external_fingerprint = compute_external_dependency_fingerprint(
        entry_modules,
        PRODUCER_RELEVANT_EXTERNAL_IMPORT_NAMES[
            ProducerFingerprintFamily.RAW_SCHEMA_EXCLUSION_MANIFEST
        ],
    )
    identity: ArtifactDigest = compute_artifact_dependency_fingerprint(
        schema_version="1",
        scientific_configuration_subset=dataset.value,
        dataset_split_view_identities=dataset_split_view_identities,
        semantic_coordinates_and_seed_namespaces=dataset.value,
        upstream_artifact_identities=(),
        producer_component_fingerprint=producer_fingerprint,
        external_dependency_fingerprint=external_fingerprint,
    )
    canonical_directory: Path = REPOSITORY_ROOT / workspace_root_for_family(
        ArtifactFamily.CANONICAL_DATASET_MANIFEST
    )

    if is_artifact_complete_and_valid(canonical_directory, identity):
        reused_manifest = read_published_manifest(canonical_directory, identity)
        if reused_manifest is not None:
            return reused_manifest, True

    payload = json.dumps(payload_fields, sort_keys=True, default=str).encode("utf-8")
    staged_manifest = ArtifactManifest(
        family=ArtifactFamily.CANONICAL_DATASET_MANIFEST,
        identity=identity,
        checksum=compute_checksum(payload),
        lifecycle_state=ArtifactLifecycleState.STAGING,
        upstream_identities=(),
    )
    staging_root = (
        REPOSITORY_ROOT / config.runtime.repository_layout.execution_workspace / "cache" / "staging"
    )
    staged_path = stage_payload(staging_root, payload)
    published = publish_artifact_to_disk(staged_path, canonical_directory, staged_manifest, payload)
    return published, False


def _preprocess_nbaiot(overwrite: bool) -> None:
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
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
    unavailable_classes = tuple(
        class_id.value for class_id in classes_structurally_unavailable(discovered)
    )
    reference_file = discovered[0]
    reference_header = read_predictor_header(reference_file.absolute_path)
    validate_predictor_schema(reference_header)
    for item in discovered:
        observed_header = read_predictor_header(item.absolute_path)
        validate_consistent_predictor_schema(reference_header, observed_header)
        validate_all_predictors_finite(item.absolute_path, reference_header)

    _artifact_manifest, reused = _publish_or_reuse_canonical_dataset_manifest(
        DatasetId.N_BAIOT,
        config,
        manifest_hash,
        {
            "dataset_file_manifest_hash": manifest_hash,
            "structurally_unavailable_classes": list(unavailable_classes),
        },
    )

    prepared_root = REPOSITORY_ROOT / prepared_evidence_root(
        DATASET_PACKAGE_NAME[DatasetId.N_BAIOT]
    )
    scaler_root = REPOSITORY_ROOT / prepared_feature_root()
    views, moments = materialize_nbaiot_prepared_views(
        discovered, config, prepared_root, scaler_root, overwrite
    )
    role_counts: dict[str, int] = {}
    for view in views:
        role_counts[view.role.value] = role_counts.get(view.role.value, 0) + view.row_count
    print(
        "N-BaIoT preprocessing complete: "
        f"dataset_file_manifest_hash={manifest_hash}, "
        f"structurally_unavailable_classes={list(unavailable_classes)}, "
        f"prepared_views={len(views)}, "
        f"scaler_training_rows={moments.training_row_count}, "
        f"canonical_dataset_manifest_reused={reused}"
    )
    print(f"role row totals: {role_counts}")


def _preprocess_ciciot2023(overwrite: bool) -> None:
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    csv_root = (
        REPOSITORY_ROOT / config.runtime.repository_layout.raw_data / "CIC_IOT_Dataset2023" / "CSV"
    )
    discovered = discover_secondary_csv_files(csv_root)
    prepared_root = REPOSITORY_ROOT / prepared_evidence_root(
        DATASET_PACKAGE_NAME[DatasetId.CICIOT2023]
    )
    scaler_root = REPOSITORY_ROOT / prepared_feature_root()
    metadata_root = REPOSITORY_ROOT / preprocessing_metadata_root()
    cache_root = (
        REPOSITORY_ROOT
        / config.runtime.repository_layout.execution_workspace
        / "cache"
        / "preprocessing"
    )
    summary = materialize_ciciot2023_prepared_views(
        discovered,
        config,
        prepared_root,
        scaler_root,
        metadata_root,
        cache_root,
        overwrite,
    )
    _artifact_manifest, reused = _publish_or_reuse_canonical_dataset_manifest(
        DatasetId.CICIOT2023,
        config,
        summary.dataset_manifest_hash,
        {
            "dataset_file_manifest_hash": summary.dataset_manifest_hash,
            "file_count": len(discovered),
            "raw_row_count": summary.raw_row_count,
            "retained_row_count": summary.retained_row_count,
            "excluded_row_count": summary.excluded_row_count,
            "predictor_count": len(summary.predictor_columns),
            "official_expected_predictor_count": OFFICIAL_EXPECTED_PREDICTOR_COUNT,
            "predictor_count_matches_official": summary.predictor_count_matches_official,
            "class_registry": list(summary.class_registry),
            "pseudo_domain_count": PSEUDO_DOMAIN_COUNT,
        },
    )
    exclusion_rate = (
        summary.excluded_row_count / summary.raw_row_count if summary.raw_row_count else 0.0
    )
    role_counts: dict[str, int] = {}
    for view in summary.views:
        role_counts[view.role.value] = role_counts.get(view.role.value, 0) + view.row_count
    print(
        "CICIoT2023 preprocessing complete: "
        f"dataset_file_manifest_hash={summary.dataset_manifest_hash}, "
        f"files={len(discovered)}, raw_rows={summary.raw_row_count}, "
        f"retained_rows={summary.retained_row_count}, excluded_rows={summary.excluded_row_count}, "
        f"exclusion_rate={exclusion_rate:.8f}, predictor_count={len(summary.predictor_columns)}, "
        f"predictor_count_matches_official={summary.predictor_count_matches_official}, "
        f"class_count={len(summary.class_registry)}, prepared_views={len(summary.views)}, "
        f"scaler_training_rows={summary.scaler.training_row_count}, "
        f"canonical_dataset_manifest_reused={reused}"
    )
    print(f"role row totals: {role_counts}")


def execute(dataset: DatasetId | None, overwrite: bool) -> None:
    selected_datasets = tuple(DatasetId) if dataset is None else (dataset,)
    for selected_dataset in selected_datasets:
        if selected_dataset is DatasetId.N_BAIOT:
            _preprocess_nbaiot(overwrite)
        elif selected_dataset is DatasetId.CICIOT2023:
            _preprocess_ciciot2023(overwrite)
        else:
            raise ValueError(f"unsupported dataset identity: {selected_dataset}")
