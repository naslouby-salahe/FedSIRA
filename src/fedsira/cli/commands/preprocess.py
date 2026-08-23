import hashlib
import json
from pathlib import Path

import pandas

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
    assign_group_local_roles,
    assign_pseudo_domains,
    compute_stable_row_id,
    order_group_by_stable_row_id,
    resolve_predictor_columns,
)
from fedsira.datasets.ciciot2023.schema import canonical_class_registry, canonicalize_label
from fedsira.datasets.ciciot2023.validation import (
    validate_label_collisions,
    validate_target_label_present,
)
from fedsira.datasets.nbaiot.acquisition import (
    compute_dataset_manifest_hash,
    discover_primary_csv_files,
)
from fedsira.datasets.nbaiot.preprocessing import (
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


def _validate_ciciot2023_raw_data() -> (
    tuple[
        NonNegativeInt, tuple[CanonicalToken, ...], NonNegativeInt, NonNegativeInt, NonNegativeInt
    ]
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
        label_frame: pandas.DataFrame = pandas.read_csv(path, usecols=[label_column])
        labels: pandas.Series[str] = label_frame[label_column]
        observed_raw_labels.update(str(label) for label in labels.unique())

    validate_label_collisions(frozenset(observed_raw_labels))
    canonical_labels = frozenset(canonicalize_label(label) for label in observed_raw_labels)
    validate_target_label_present(canonical_labels)
    registry = canonical_class_registry(canonical_labels)

    reference_path = discovered[0]
    reference_file_sha256 = compute_file_checksum(reference_path)
    reference_sample: pandas.DataFrame = pandas.read_csv(reference_path, nrows=1500)
    predictor_columns = resolve_predictor_columns(reference_header, label_column, reference_sample)
    dataset_manifest_hash = hashlib.sha256(
        canonical_bytes(reference_path.name, reference_file_sha256)
    ).hexdigest()
    reference_relative_path = reference_path.relative_to(csv_root).as_posix()

    rows_by_group: dict[tuple[CanonicalToken, NonNegativeInt], list[ArtifactDigest]] = {}
    for row_index in range(len(reference_sample)):
        stable_row_id = compute_stable_row_id(
            reference_relative_path, reference_file_sha256, row_index
        )
        label_column_series: pandas.Series[str] = reference_sample[label_column]
        canonical_label = canonicalize_label(str(label_column_series.iloc[row_index]))
        pseudo_domain = assign_pseudo_domains(
            dataset_manifest_hash,
            canonical_label,
            (stable_row_id,),
            config.datasets.secondary.pseudo_domain_partition_salt,
        )[0]
        rows_by_group.setdefault((canonical_label, pseudo_domain), []).append(stable_row_id)

    total_group_local_role_assignments = 0
    for (canonical_label, _pseudo_domain), stable_row_ids in rows_by_group.items():
        ordered = order_group_by_stable_row_id(tuple(stable_row_ids))
        roles = assign_group_local_roles(
            canonical_label, ordered, config.datasets.primary.role_intervals
        )
        total_group_local_role_assignments += sum(1 for role in roles if role is not None)

    return (
        len(discovered),
        registry,
        len(predictor_columns),
        len(rows_by_group),
        total_group_local_role_assignments,
    )


def execute(dataset: DatasetId | None, overwrite: bool) -> None:
    if dataset is DatasetId.N_BAIOT:
        config = load_scientific_config(PRODUCTION_CONFIG_PATH)
        raw_root = (
            REPOSITORY_ROOT / config.runtime.repository_layout.raw_data / DatasetId.N_BAIOT.value
        )
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
        for item in discovered:
            observed_header = read_predictor_header(item.absolute_path)
            validate_consistent_predictor_schema(reference_header, observed_header)

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
        from fedsira.datasets.nbaiot.materialization import materialize_nbaiot_prepared_views

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
        return
    if dataset is DatasetId.CICIOT2023:
        (
            file_count,
            class_registry,
            predictor_count,
            group_count,
            group_local_role_assignments,
        ) = _validate_ciciot2023_raw_data()
        print(
            "CICIoT2023 preprocessing complete: "
            f"files={file_count}, class_registry={list(class_registry)}, "
            f"predictor_count={predictor_count}, "
            f"reference_label_pseudo_domain_groups={group_count}, "
            f"reference_group_local_role_assignments={group_local_role_assignments}"
        )
        return
    raise ScientificPipelineNotImplementedError(
        f"fedsira preprocess is not implemented for dataset {dataset}"
    )
