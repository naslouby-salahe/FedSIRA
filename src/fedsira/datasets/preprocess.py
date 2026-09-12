from pathlib import Path

from fedsira.artifacts.paths import (
    artifact_log_path,
    artifact_slot_directory,
    artifact_staging_root,
    prepared_evidence_root,
    prepared_feature_root,
    preprocessing_extraction_cache_root,
    preprocessing_log_path,
    preprocessing_metadata_root,
)
from fedsira.artifacts.store import (
    ArtifactDependency,
    ArtifactSlot,
    compute_checksum,
    configure_artifact_logging,
    publish_artifact,
)
from fedsira.datasets.ciciot2023.prepare import (
    compute_dataset_manifest_hash as compute_secondary_dataset_manifest_hash,
)
from fedsira.datasets.ciciot2023.prepare import (
    discover_secondary_csv_files,
    materialize_ciciot2023_prepared_views,
)
from fedsira.datasets.ciciot2023.schema import (
    OFFICIAL_EXPECTED_PREDICTOR_COUNT,
    PSEUDO_DOMAIN_COUNT,
    CICIoT2023DatasetManifestPayload,
    CICIoT2023TargetFamilyMember,
)
from fedsira.datasets.common import (
    PREPARED_ROLE_VIEW_SCHEMA_VERSION,
    SCALER_METADATA_SCHEMA_VERSION,
    DatasetPreparationLogFields,
    PreparedRoleViewManifest,
    RawDatasetFileIdentity,
    RawDatasetIdentityPayload,
    ScalerMetadata,
    prepared_feature_names,
    role_hash_token,
)
from fedsira.datasets.layout import required_raw_dataset_root
from fedsira.datasets.nbaiot.prepare import (
    classes_structurally_unavailable,
    compute_dataset_manifest_hash,
    discover_primary_csv_files,
    materialize_nbaiot_prepared_views,
    validate_target_holder_feasibility,
)
from fedsira.datasets.nbaiot.schema import NBaiotDatasetManifestPayload
from fedsira.datasets.role_split import (
    ROLE_SPLIT_SAMPLE_MANIFEST_DEPENDENCY,
    RoleSplitViewCount,
    publish_role_split_sample_manifest,
)
from fedsira.domain.enums import (
    ArtifactDependencyKind,
    ArtifactFamily,
    ArtifactProducer,
    DatasetId,
    Role,
)
from fedsira.domain.types import (
    ArtifactDependencyName,
    ArtifactDigest,
    ArtifactReuseDecision,
    DatasetClassToken,
    DatasetManifestDigest,
    DomainId,
    OverwriteExisting,
    PreparedViewKey,
    Probability,
    ProcedureIdentity,
    RowCount,
    SchemaVersion,
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
    run_bounded,
)

PREPROCESSING_LOGGER = get_structured_logger("preprocessing")

RAW_DATASET_IDENTITY_SCHEMA_VERSION: SchemaVersion = "fedsira|raw_dataset_identity|1"
RAW_DATASET_IDENTITY_PROCEDURE_IDENTITY: ProcedureIdentity = "fedsira|raw_dataset_identity|1"
SCALER_ARTIFACT_PROCEDURE_IDENTITY: ProcedureIdentity = "fedsira|scaler|1"
RAW_FILE_MANIFEST_DEPENDENCY: ArtifactDependencyName = "raw-file-manifest"
PREPARED_EVIDENCE_DEPENDENCY: ArtifactDependencyName = "prepared-evidence"

DatasetManifestPayload = NBaiotDatasetManifestPayload | CICIoT2023DatasetManifestPayload


DATASET_FILE_MANIFEST_DEPENDENCY: ArtifactDependencyName = "dataset-file-manifest"
DATASET_MANIFEST_PROCEDURE_IDENTITY: ProcedureIdentity = "fedsira|dataset_manifest|1"


def _publish_dataset_manifest(payload: DatasetManifestPayload) -> ArtifactReuseDecision:
    serialized_payload = payload.model_dump_json().encode("utf-8")
    _, reused = publish_artifact(
        slot=ArtifactSlot(
            family=ArtifactFamily.DATASET_MANIFEST,
            instance=payload.dataset_file_manifest_hash,
        ),
        producer=ArtifactProducer.DATASET_PREPARATION,
        payload=serialized_payload,
        dependencies=(
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=DATASET_FILE_MANIFEST_DEPENDENCY,
                digest=payload.dataset_file_manifest_hash,
            ),
        ),
        procedure_identity=DATASET_MANIFEST_PROCEDURE_IDENTITY,
        slot_directory=artifact_slot_directory(
            ArtifactSlot(
                family=ArtifactFamily.DATASET_MANIFEST,
                instance=payload.dataset_file_manifest_hash,
            )
        ),
        staging_root=REPOSITORY_ROOT / artifact_staging_root(),
    )
    return reused


def publish_raw_dataset_identity(
    dataset: DatasetId,
    files: tuple[RawDatasetFileIdentity, ...],
    manifest_hash: DatasetManifestDigest,
) -> ArtifactReuseDecision:
    slot = ArtifactSlot(family=ArtifactFamily.RAW_DATASET_IDENTITY, instance=dataset)
    payload = (
        RawDatasetIdentityPayload(
            schema_version=RAW_DATASET_IDENTITY_SCHEMA_VERSION,
            dataset=dataset,
            files=files,
        )
        .model_dump_json()
        .encode("utf-8")
    )
    _, reused = publish_artifact(
        slot=slot,
        producer=ArtifactProducer.RAW_ACQUISITION,
        payload=payload,
        dependencies=(
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=RAW_FILE_MANIFEST_DEPENDENCY,
                digest=manifest_hash,
            ),
        ),
        procedure_identity=RAW_DATASET_IDENTITY_PROCEDURE_IDENTITY,
        slot_directory=REPOSITORY_ROOT / artifact_slot_directory(slot),
        staging_root=REPOSITORY_ROOT / artifact_staging_root(),
    )
    return reused


def publish_scaler(
    dataset: DatasetId,
    scaler: ScalerMetadata,
    manifest_hash: DatasetManifestDigest,
) -> ArtifactReuseDecision:
    slot = ArtifactSlot(family=ArtifactFamily.SCALER, instance=dataset)
    payload = scaler.model_dump_json().encode("utf-8")
    _, reused = publish_artifact(
        slot=slot,
        producer=ArtifactProducer.PREPROCESSING,
        payload=payload,
        dependencies=(
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=RAW_FILE_MANIFEST_DEPENDENCY,
                digest=manifest_hash,
            ),
        ),
        procedure_identity=SCALER_ARTIFACT_PROCEDURE_IDENTITY,
        slot_directory=REPOSITORY_ROOT / artifact_slot_directory(slot),
        staging_root=REPOSITORY_ROOT / artifact_staging_root(),
    )
    return reused


PREPARED_ROLE_VIEW_PROCEDURE_IDENTITY: ProcedureIdentity = "fedsira|prepared_role_view|1"


def publish_prepared_role_view(
    dataset: DatasetId,
    role_split_manifest_identity: ArtifactDigest,
    view_key: PreparedViewKey,
    role: Role,
    class_token: DatasetClassToken,
    domain_token: DomainId,
    row_count: RowCount,
    parquet_path: Path,
) -> ArtifactReuseDecision:
    parquet_payload = parquet_path.read_bytes()
    slot = ArtifactSlot(family=ArtifactFamily.PREPARED_ROLE_VIEW, instance=view_key)
    payload = (
        PreparedRoleViewManifest(
            schema_version=PREPARED_ROLE_VIEW_SCHEMA_VERSION,
            dataset=dataset,
            view_key=view_key,
            role=role,
            class_token=class_token,
            domain_token=domain_token,
            row_count=row_count,
            parquet_sha256=compute_checksum(parquet_payload),
            parquet_bytes=len(parquet_payload),
        )
        .model_dump_json()
        .encode("utf-8")
    )
    _, reused = publish_artifact(
        slot=slot,
        producer=ArtifactProducer.PREPROCESSING,
        payload=payload,
        dependencies=(
            ArtifactDependency(
                kind=ArtifactDependencyKind.ARTIFACT,
                dependency=ROLE_SPLIT_SAMPLE_MANIFEST_DEPENDENCY,
                digest=role_split_manifest_identity,
            ),
        ),
        procedure_identity=PREPARED_ROLE_VIEW_PROCEDURE_IDENTITY,
        slot_directory=REPOSITORY_ROOT / artifact_slot_directory(slot),
        staging_root=REPOSITORY_ROOT / artifact_staging_root(),
    )
    return reused


def _preprocess_nbaiot(overwrite: OverwriteExisting) -> None:
    config = current_application_context().scientific_config
    raw_root = required_raw_dataset_root(DatasetId.N_BAIOT)
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
    publish_raw_dataset_identity(
        DatasetId.N_BAIOT,
        tuple(
            RawDatasetFileIdentity(relative_path=item.relative_path, file_sha256=item.file_sha256)
            for item in discovered
        ),
        manifest_hash,
    )
    prepared_root = REPOSITORY_ROOT / prepared_evidence_root(DatasetId.N_BAIOT)
    nbaiot_views, moments = materialize_nbaiot_prepared_views(
        discovered,
        prepared_root,
        REPOSITORY_ROOT / prepared_feature_root(),
        overwrite,
        retain_materialized_views=False,
    )
    role_split_manifest, _role_split_reused = publish_role_split_sample_manifest(
        DatasetId.N_BAIOT,
        manifest_hash,
        tuple(
            RoleSplitViewCount(
                domain=view.domain.name,
                class_id=view.class_id.value,
                role=view.role,
                row_count=view.row_count,
            )
            for view in nbaiot_views
        ),
    )
    for view in nbaiot_views:
        publish_prepared_role_view(
            DatasetId.N_BAIOT,
            role_split_manifest.identity,
            f"{view.domain.name}_{view.class_id.name}_{role_hash_token(view.role)}",
            view.role,
            view.class_id,
            view.domain.name,
            view.row_count,
            view.parquet_path,
        )
    publish_scaler(
        DatasetId.N_BAIOT,
        ScalerMetadata(
            schema_version=SCALER_METADATA_SCHEMA_VERSION,
            feature_names=tuple(prepared_feature_names(prepared_root) or ()),
            means=moments.means,
            standard_deviations=moments.standard_deviations,
            training_row_count=moments.training_row_count,
        ),
        manifest_hash,
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
    csv_root = required_raw_dataset_root(DatasetId.CICIOT2023)
    log_structured_event(
        PREPROCESSING_LOGGER,
        "dataset.preprocessing.started",
        DatasetPreparationLogFields(dataset=DatasetId.CICIOT2023),
    )
    discovered = discover_secondary_csv_files(csv_root, config.datasets.secondary.acquisition)
    cache_root = preprocessing_extraction_cache_root(
        REPOSITORY_ROOT / config.execution.repository_layout.execution_workspace
    )
    publish_raw_dataset_identity(
        DatasetId.CICIOT2023,
        tuple(
            RawDatasetFileIdentity(relative_path=item.relative_path, file_sha256=item.file_sha256)
            for item in discovered
        ),
        compute_secondary_dataset_manifest_hash(discovered),
    )
    summary = materialize_ciciot2023_prepared_views(
        discovered,
        REPOSITORY_ROOT / prepared_evidence_root(DatasetId.CICIOT2023),
        REPOSITORY_ROOT / prepared_feature_root(),
        REPOSITORY_ROOT / preprocessing_metadata_root(),
        cache_root,
        overwrite,
    )
    role_split_manifest, _role_split_reused = publish_role_split_sample_manifest(
        DatasetId.CICIOT2023,
        summary.dataset_manifest_hash,
        tuple(
            RoleSplitViewCount(
                domain=view.pseudo_domain.display_token,
                class_id=view.normalized_label,
                role=view.role,
                row_count=view.row_count,
            )
            for view in summary.views
        ),
    )
    for view in summary.views:
        publish_prepared_role_view(
            DatasetId.CICIOT2023,
            role_split_manifest.identity,
            f"{view.pseudo_domain.display_token}_{view.normalized_label}_"
            f"{role_hash_token(view.role)}",
            view.role,
            view.normalized_label,
            view.pseudo_domain.display_token,
            view.row_count,
            view.parquet_path,
        )
    publish_scaler(
        DatasetId.CICIOT2023,
        ScalerMetadata(
            schema_version=SCALER_METADATA_SCHEMA_VERSION,
            feature_names=summary.predictor_columns,
            means=summary.scaler.means,
            standard_deviations=summary.scaler.standard_deviations,
            training_row_count=summary.scaler.training_row_count,
        ),
        summary.dataset_manifest_hash,
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
            target_family_members=tuple(member.value for member in CICIoT2023TargetFamilyMember),
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
        timeout = context.scientific_config.execution.timeouts_seconds.dataset_preprocessing
        run_bounded("preprocessing", timeout, lambda: _execute_bound(dataset, overwrite))


def _execute_bound(dataset: DatasetId | None, overwrite: OverwriteExisting) -> None:
    configure_structured_file_logging(
        PREPROCESSING_LOGGER, REPOSITORY_ROOT / preprocessing_log_path()
    )
    configure_artifact_logging(REPOSITORY_ROOT / artifact_log_path())
    mirror_structured_logging_to_console(PREPROCESSING_LOGGER)
    selected_datasets = tuple(DatasetId) if dataset is None else (dataset,)
    for selected_dataset in selected_datasets:
        if selected_dataset is DatasetId.N_BAIOT:
            _preprocess_nbaiot(overwrite)
        elif selected_dataset is DatasetId.CICIOT2023:
            _preprocess_ciciot2023(overwrite)
        else:
            raise ValueError(f"unsupported dataset identity: {selected_dataset}")
