import hashlib

from fedsira.artifacts.paths import (
    artifact_instance_token,
    artifact_slot_directory,
    artifact_staging_root,
)
from fedsira.artifacts.store import (
    ArtifactDependency,
    ArtifactManifest,
    ArtifactReuseDecision,
    ArtifactSlot,
    publish_artifact,
)
from fedsira.domain.enums import (
    ArtifactDependencyKind,
    ArtifactFamily,
    ArtifactProducer,
    DatasetId,
    Role,
)
from fedsira.domain.types import (
    ArtifactDigest,
    DatasetClassToken,
    DomainId,
    FrozenDomainModel,
    ProcedureIdentity,
    RowCount,
    SampleScoreSequence,
    SchemaVersion,
    TextValue,
)
from fedsira.runtime import REPOSITORY_ROOT, framed_bytes, numerical_runtime_identity

MODEL_SCORE_SCHEMA_VERSION: SchemaVersion = "fedsira|model_score|1"
MODEL_SCORE_PROCEDURE_IDENTITY: ProcedureIdentity = "fedsira|model_score|1"
MODEL_SCORE_MODEL_DEPENDENCY = "model-checkpoint"
MODEL_SCORE_VIEW_DEPENDENCY = "prepared-role-view"
MODEL_SCORE_CLASS_REGISTRY_DEPENDENCY = "output-class-registry"
MODEL_SCORE_TRANSFORM_DEPENDENCY = "scoring-transform"
MODEL_SCORE_RUNTIME_DEPENDENCY = "numerical-runtime"
DEFAULT_SCORING_TRANSFORM: TextValue = "argmax-logits"


class DomainClassScore(FrozenDomainModel):
    domain: DomainId
    class_id: DatasetClassToken
    role: Role
    sample_count: RowCount
    predicted_class_indices: SampleScoreSequence
    sample_ids_digest: ArtifactDigest


class ModelScorePayload(FrozenDomainModel):
    schema_version: SchemaVersion
    dataset: DatasetId
    model_identity: ArtifactDigest
    scoring_transform: TextValue
    class_tokens: tuple[DatasetClassToken, ...]
    shards: tuple[DomainClassScore, ...]


def sample_ids_digest(sample_ids: tuple[ArtifactDigest, ...]) -> ArtifactDigest:
    return hashlib.sha256(framed_bytes(*sample_ids)).hexdigest()


def class_registry_digest(class_tokens: tuple[DatasetClassToken, ...]) -> ArtifactDigest:
    return hashlib.sha256(framed_bytes(*class_tokens)).hexdigest()


def scoring_transform_digest(scoring_transform: TextValue) -> ArtifactDigest:
    return hashlib.sha256(framed_bytes(scoring_transform)).hexdigest()


def model_score_view_digest(shards: tuple[DomainClassScore, ...]) -> ArtifactDigest:
    return hashlib.sha256(
        framed_bytes(
            *(
                field
                for shard in sorted(
                    shards, key=lambda item: (item.domain, item.class_id, item.role.value)
                )
                for field in (
                    shard.domain,
                    shard.class_id,
                    shard.role.value,
                    str(shard.sample_count),
                    shard.sample_ids_digest,
                )
            )
        )
    ).hexdigest()


def model_score_slot(
    model_identity: ArtifactDigest,
    view_digest: ArtifactDigest,
) -> ArtifactSlot:
    return ArtifactSlot(
        family=ArtifactFamily.MODEL_SCORE_ARTIFACT,
        instance=artifact_instance_token("scores", model_identity, view_digest),
    )


def publish_model_score(
    dataset: DatasetId,
    model_identity: ArtifactDigest,
    scoring_transform: TextValue,
    class_tokens: tuple[DatasetClassToken, ...],
    shards: tuple[DomainClassScore, ...],
) -> tuple[ArtifactManifest, ArtifactReuseDecision]:
    view_digest = model_score_view_digest(shards)
    payload = ModelScorePayload(
        schema_version=MODEL_SCORE_SCHEMA_VERSION,
        dataset=dataset,
        model_identity=model_identity,
        scoring_transform=scoring_transform,
        class_tokens=class_tokens,
        shards=shards,
    )
    slot = model_score_slot(model_identity, view_digest)
    return publish_artifact(
        slot=slot,
        producer=ArtifactProducer.SCORING_PRODUCER,
        payload=payload.model_dump_json().encode("utf-8"),
        dependencies=(
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=MODEL_SCORE_MODEL_DEPENDENCY,
                digest=model_identity,
            ),
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=MODEL_SCORE_VIEW_DEPENDENCY,
                digest=view_digest,
            ),
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=MODEL_SCORE_CLASS_REGISTRY_DEPENDENCY,
                digest=class_registry_digest(class_tokens),
            ),
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=MODEL_SCORE_TRANSFORM_DEPENDENCY,
                digest=scoring_transform_digest(scoring_transform),
            ),
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=MODEL_SCORE_RUNTIME_DEPENDENCY,
                digest=numerical_runtime_identity(),
            ),
        ),
        procedure_identity=MODEL_SCORE_PROCEDURE_IDENTITY,
        slot_directory=REPOSITORY_ROOT / artifact_slot_directory(slot),
        staging_root=REPOSITORY_ROOT / artifact_staging_root(),
    )
