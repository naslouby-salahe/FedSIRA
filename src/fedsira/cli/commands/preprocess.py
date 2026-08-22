import hashlib
import json
from pathlib import Path

import pandas

from fedsira.artifacts.fingerprints import (
    PRODUCER_RELEVANT_EXTERNAL_IMPORT_NAMES,
    compute_artifact_dependency_fingerprint,
    compute_external_dependency_fingerprint,
    compute_producer_component_fingerprint,
    raw_schema_exclusion_manifest_entry_modules,
)
from fedsira.artifacts.paths import workspace_root_for_family
from fedsira.artifacts.records import ArtifactManifest
from fedsira.artifacts.storage import (
    compute_checksum,
    is_artifact_complete_and_valid,
    publish_artifact_to_disk,
    read_published_manifest,
    stage_payload,
)
from fedsira.cli.commands import REPOSITORY_ROOT, ScientificPipelineNotImplementedError
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.config.schema import ScientificConfig
from fedsira.datasets.ciciot2023.acquisition import (
    compute_file_checksum,
    discover_secondary_csv_files,
    read_csv_header,
    resolve_label_column,
    validate_consistent_header,
)
from fedsira.datasets.ciciot2023.preprocessing import (
    assign_pseudo_domains,
    compute_stable_row_id,
    resolve_predictor_columns,
)
from fedsira.datasets.ciciot2023.schema import canonical_class_registry, canonicalize_label
from fedsira.datasets.ciciot2023.validation import (
    validate_label_collisions,
    validate_target_label_present,
)
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
from fedsira.domain.enums import (
    ArtifactFamily,
    ArtifactLifecycleState,
    DatasetId,
    ProducerFingerprintFamily,
)
from fedsira.domain.records import ArtifactDigest, CanonicalToken, NonNegativeInt
from fedsira.runtime.determinism import canonical_bytes


def _publish_or_reuse_canonical_dataset_manifest(
    dataset: DatasetId,
    config: ScientificConfig,
    dataset_split_view_identities: CanonicalToken,
    payload_fields: dict[str, CanonicalToken | list[CanonicalToken]],
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


def _validate_nbaiot_raw_data() -> tuple[str, tuple[str, ...], NonNegativeInt, bool]:
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

    _artifact_manifest, reused = _publish_or_reuse_canonical_dataset_manifest(
        DatasetId.N_BAIOT,
        config,
        manifest_hash,
        {
            "dataset_file_manifest_hash": manifest_hash,
            "structurally_unavailable_classes": list(unavailable_classes),
        },
    )

    return manifest_hash, unavailable_classes, total_role_assignments, reused


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


def _validate_ciciot2023_raw_data() -> (
    tuple[NonNegativeInt, tuple[CanonicalToken, ...], NonNegativeInt, NonNegativeInt]
):
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    csv_root = (
        REPOSITORY_ROOT
        / config.runtime.repository_layout.raw_data
        / "CIC_IOT_Dataset2023"
        / "CSV"
        / "MERGED_CSV"
    )
    discovered = discover_secondary_csv_files(csv_root)
    reference_header = read_csv_header(discovered[0])
    label_column = resolve_label_column(reference_header)

    observed_raw_labels: set[str] = set()
    for path in discovered:
        observed_header = read_csv_header(path)
        validate_consistent_header(reference_header, observed_header)
        labels = pandas.read_csv(path, usecols=[label_column])[label_column]
        observed_raw_labels.update(str(label) for label in labels.unique())

    validate_label_collisions(frozenset(observed_raw_labels))
    canonical_labels = frozenset(canonicalize_label(label) for label in observed_raw_labels)
    validate_target_label_present(canonical_labels)
    registry = canonical_class_registry(canonical_labels)

    reference_path = discovered[0]
    reference_file_sha256 = compute_file_checksum(reference_path)
    reference_sample = pandas.read_csv(reference_path, nrows=1500)
    predictor_columns = resolve_predictor_columns(reference_header, label_column, reference_sample)
    dataset_manifest_hash = hashlib.sha256(
        canonical_bytes(reference_path.name, reference_file_sha256)
    ).hexdigest()
    reference_relative_path = reference_path.relative_to(csv_root).as_posix()
    stable_row_ids = tuple(
        compute_stable_row_id(reference_relative_path, reference_file_sha256, row_index)
        for row_index in range(len(reference_sample))
    )
    pseudo_domains = assign_pseudo_domains(
        dataset_manifest_hash,
        canonicalize_label(str(reference_sample[label_column].iloc[0])),
        stable_row_ids,
        config.datasets.secondary.pseudo_domain_partition_salt,
    )

    return len(discovered), registry, len(predictor_columns), len(set(pseudo_domains))


def execute(dataset: DatasetId | None, overwrite: bool) -> None:
    if dataset is DatasetId.N_BAIOT:
        manifest_hash, unavailable_classes, total_role_assignments, reused = (
            _validate_nbaiot_raw_data()
        )
        raise ScientificPipelineNotImplementedError(
            "N-BaIoT raw data discovered and validated "
            f"(dataset_file_manifest_hash={manifest_hash}, "
            f"structurally_unavailable_classes={list(unavailable_classes)}, "
            f"total_role_assignments={total_role_assignments}, "
            f"canonical_dataset_manifest_reused={reused}); "
            "prepared-view/scaler artifact publication is not implemented until M02 — I10"
        )
    if dataset is DatasetId.CICIOT2023:
        file_count, class_registry, predictor_count, pseudo_domain_count = (
            _validate_ciciot2023_raw_data()
        )
        raise ScientificPipelineNotImplementedError(
            f"CICIoT2023 raw data discovered and validated (files={file_count}, "
            f"class_registry={list(class_registry)}, predictor_count={predictor_count}, "
            f"reference_pseudo_domains_observed={pseudo_domain_count}); role/scaler "
            "materialization is not implemented until M02 — I12"
        )
    raise ScientificPipelineNotImplementedError(
        "fedsira preprocess is not implemented until the M02 dataset-preparation milestone"
    )
