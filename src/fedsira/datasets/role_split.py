from fedsira.artifacts.paths import artifact_slot_directory, artifact_staging_root
from fedsira.artifacts.store import (
    ArtifactDependency,
    ArtifactManifest,
    ArtifactReuseDecision,
    ArtifactSlot,
    publish_artifact,
)
from fedsira.config import RoleIntervals, SamplingCapsPerDomain
from fedsira.domain.enums import (
    ArtifactDependencyKind,
    ArtifactFamily,
    ArtifactProducer,
    DatasetId,
    Role,
)
from fedsira.domain.types import (
    ArtifactInstanceToken,
    DatasetClassToken,
    DatasetManifestDigest,
    DomainId,
    FrozenDomainModel,
    ProcedureIdentity,
    RowCount,
    SchemaVersion,
)
from fedsira.runtime import REPOSITORY_ROOT, current_application_context

ROLE_SPLIT_SAMPLE_MANIFEST_SCHEMA_VERSION: SchemaVersion = "fedsira|role_split_sample_manifest|1"  # TODO: should be enum
ROLE_SPLIT_SAMPLE_MANIFEST_PROCEDURE_IDENTITY: ProcedureIdentity = (
    "fedsira|role_split_sample_manifest|1"  # TODO: should be enum
)
ROLE_SPLIT_SAMPLE_MANIFEST_DEPENDENCY = "role-split-manifest"  # TODO: should be enum
ROLE_SPLIT_MANIFEST_INSTANCE: ArtifactInstanceToken = "role-split"  # TODO: should be enum


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
        instance=f"{ROLE_SPLIT_MANIFEST_INSTANCE}-{dataset.value}",
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
        counts=tuple(
            sorted(counts, key=lambda item: (item.domain, item.class_id, item.role.value))
        ),
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
                dependency="dataset-manifest"  # TODO: should be enum
,
                digest=dataset_manifest_hash,
            ),
        ),
        procedure_identity=ROLE_SPLIT_SAMPLE_MANIFEST_PROCEDURE_IDENTITY,
        slot_directory=REPOSITORY_ROOT / artifact_slot_directory(slot),
        staging_root=REPOSITORY_ROOT / artifact_staging_root(),
    )
