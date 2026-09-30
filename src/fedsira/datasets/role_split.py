import hashlib

from fedsira.artifacts.paths import (
    artifact_slot_directory,
    artifact_staging_root,
    current_repository_root,
)
from fedsira.artifacts.store import (
    ArtifactConfigurationComponent,
    ArtifactConfigurationScope,
    ArtifactDependency,
    ArtifactManifest,
    ArtifactReuseDecision,
    ArtifactSlot,
    artifact_identity,
    configuration_scope_dependency,
    publish_artifact,
    read_current_artifact,
)
from fedsira.config import RoleIntervals, SamplingCapsPerDomain
from fedsira.domain.enums import (
    ArtifactDependencyKind,
    ArtifactDependencyLabel,
    ArtifactFamily,
    ArtifactInstanceLabel,
    ArtifactProducer,
    DatasetId,
    Role,
)
from fedsira.domain.types import (
    ArtifactDigest,
    DatasetClassToken,
    DatasetManifestDigest,
    DomainId,
    FrozenDomainModel,
    ProcedureIdentity,
    RowCount,
    SchemaVersion,
)
from fedsira.runtime import current_application_context, framed_bytes

ROLE_SPLIT_SAMPLE_MANIFEST_SCHEMA_VERSION: SchemaVersion = "fedsira|role_split_sample_manifest|1"
ROLE_SPLIT_SAMPLE_MANIFEST_PROCEDURE_IDENTITY: ProcedureIdentity = (
    "fedsira|role_split_sample_manifest|2"
)


def dataset_preprocessing_configuration(dataset: DatasetId) -> ArtifactConfigurationScope:
    datasets = current_application_context().scientific_config.datasets
    if dataset is DatasetId.N_BAIOT:
        return ArtifactConfigurationScope(
            scope="dataset-preprocessing",
            components=(
                ArtifactConfigurationComponent(
                    name=ArtifactDependencyLabel.DATASET_PREPROCESSING,
                    configuration=datasets.primary.model_dump_json(by_alias=True),
                ),
            ),
        )
    return ArtifactConfigurationScope(
        scope="dataset-preprocessing",
        components=(
            ArtifactConfigurationComponent(
                name=ArtifactDependencyLabel.PRIMARY_ROLE_INTERVALS,
                configuration=datasets.primary.role_intervals.model_dump_json(by_alias=True),
            ),
            ArtifactConfigurationComponent(
                name=ArtifactDependencyLabel.PRIMARY_SAMPLING_CAPS,
                configuration=datasets.primary.sampling_caps_per_domain.model_dump_json(
                    by_alias=True
                ),
            ),
            ArtifactConfigurationComponent(
                name=ArtifactDependencyLabel.SECONDARY_DATASET,
                configuration=datasets.secondary.model_dump_json(by_alias=True),
            ),
        ),
    )


def prepared_view_cache_identity(
    dataset: DatasetId,
    dataset_manifest_hash: DatasetManifestDigest,
) -> ArtifactDigest:
    configuration = dataset_preprocessing_configuration(dataset)
    return hashlib.sha256(
        framed_bytes(
            "fedsira|prepared_view_cache|2",
            dataset,
            dataset_manifest_hash,
            configuration.model_dump_json(),
        )
    ).hexdigest()


class RoleSplitViewCount(FrozenDomainModel):
    domain: DomainId
    class_id: DatasetClassToken
    role: Role
    row_count: RowCount


class RoleSplitSampleManifestPayload(FrozenDomainModel):
    schema_version: SchemaVersion
    dataset: DatasetId
    dataset_manifest_hash: DatasetManifestDigest
    target_class: DatasetClassToken
    class_tokens: tuple[DatasetClassToken, ...]
    domain_ids: tuple[DomainId, ...]
    role_intervals: RoleIntervals
    sampling_caps_per_domain: SamplingCapsPerDomain
    counts: tuple[RoleSplitViewCount, ...]


def role_split_sample_manifest_slot(dataset: DatasetId) -> ArtifactSlot:
    return ArtifactSlot(
        family=ArtifactFamily.ROLE_SPLIT_SAMPLE_MANIFEST,
        instance=f"{ArtifactInstanceLabel.ROLE_SPLIT}-{dataset}",
    )


def role_split_sample_manifest(
    dataset: DatasetId,
    dataset_manifest_hash: DatasetManifestDigest,
    counts: tuple[RoleSplitViewCount, ...],
) -> RoleSplitSampleManifestPayload:
    primary = current_application_context().scientific_config.datasets.primary
    secondary = current_application_context().scientific_config.datasets.secondary
    return RoleSplitSampleManifestPayload(
        schema_version=ROLE_SPLIT_SAMPLE_MANIFEST_SCHEMA_VERSION,
        dataset=dataset,
        dataset_manifest_hash=dataset_manifest_hash,
        target_class=(
            secondary.target_class if dataset is DatasetId.CICIOT2023 else primary.target_class
        ),
        class_tokens=tuple(sorted({item.class_id for item in counts})),
        domain_ids=tuple(sorted({item.domain for item in counts})),
        role_intervals=primary.role_intervals,
        sampling_caps_per_domain=primary.sampling_caps_per_domain,
        counts=tuple(sorted(counts, key=lambda item: (item.domain, item.class_id, item.role))),
    )


def publish_role_split_sample_manifest(
    dataset: DatasetId,
    dataset_manifest_hash: DatasetManifestDigest,
    counts: tuple[RoleSplitViewCount, ...],
) -> tuple[ArtifactManifest, ArtifactReuseDecision]:
    payload = role_split_sample_manifest(dataset, dataset_manifest_hash, counts)
    slot = role_split_sample_manifest_slot(dataset)
    return publish_artifact(
        slot=slot,
        producer=ArtifactProducer.PREPROCESSING,
        payload=payload.model_dump_json(by_alias=True).encode("utf-8"),
        dependencies=(
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=ArtifactDependencyLabel.DATASET_MANIFEST,
                digest=dataset_manifest_hash,
            ),
            configuration_scope_dependency(
                ArtifactConfigurationScope(
                    scope=f"preprocessing:{dataset}",
                    components=dataset_preprocessing_configuration(dataset).components,
                )
            ),
        ),
        procedure_identity=ROLE_SPLIT_SAMPLE_MANIFEST_PROCEDURE_IDENTITY,
        slot_directory=current_repository_root() / artifact_slot_directory(slot),
        staging_root=current_repository_root() / artifact_staging_root(),
    )


def read_current_role_split_sample_manifest(
    dataset: DatasetId,
    dataset_manifest_hash: DatasetManifestDigest,
) -> tuple[ArtifactManifest, RoleSplitSampleManifestPayload] | None:
    slot = role_split_sample_manifest_slot(dataset)
    slot_directory = current_repository_root() / artifact_slot_directory(slot)
    current = read_current_artifact(slot_directory)
    if current is None:
        return None
    manifest, payload_bytes = current
    configuration = dataset_preprocessing_configuration(dataset)
    expected_dependencies = (
        ArtifactDependency(
            kind=ArtifactDependencyKind.CONTENT,
            dependency=ArtifactDependencyLabel.DATASET_MANIFEST,
            digest=dataset_manifest_hash,
        ),
        configuration_scope_dependency(
            ArtifactConfigurationScope(
                scope=f"preprocessing:{dataset}",
                components=configuration.components,
            )
        ),
    )
    expected_identity = artifact_identity(
        slot,
        expected_dependencies,
        ROLE_SPLIT_SAMPLE_MANIFEST_PROCEDURE_IDENTITY,
    )
    if (
        manifest.identity != expected_identity
        or manifest.dependencies != expected_dependencies
        or manifest.procedure_identity != ROLE_SPLIT_SAMPLE_MANIFEST_PROCEDURE_IDENTITY
    ):
        return None
    try:
        payload = RoleSplitSampleManifestPayload.model_validate_json(payload_bytes)
    except ValueError:
        return None
    if (
        payload.schema_version != ROLE_SPLIT_SAMPLE_MANIFEST_SCHEMA_VERSION
        or payload.dataset is not dataset
        or payload.dataset_manifest_hash != dataset_manifest_hash
        or payload.role_intervals
        != current_application_context().scientific_config.datasets.primary.role_intervals
        or payload.sampling_caps_per_domain
        != current_application_context().scientific_config.datasets.primary.sampling_caps_per_domain
        or not payload.counts
    ):
        return None
    keys = tuple((item.domain, item.class_id, item.role) for item in payload.counts)
    if len(keys) != len(set(keys)) or any(item.row_count <= 0 for item in payload.counts):
        return None
    return manifest, payload
