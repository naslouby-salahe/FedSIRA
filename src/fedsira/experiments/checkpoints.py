import torch

from fedsira.artifacts.paths import artifact_slot_directory, artifact_staging_root
from fedsira.artifacts.store import (
    ArtifactDependency,
    ArtifactManifest,
    ArtifactReuseDecision,
    ArtifactSlot,
    publish_artifact,
)
from fedsira.datasets.common import RealAnchor, flat_parameters_identity
from fedsira.domain.enums import ArtifactDependencyKind, ArtifactFamily, ArtifactProducer, DatasetId
from fedsira.domain.types import (
    ArtifactDigest,
    ArtifactInstanceToken,
    DatasetManifestDigest,
    DomainId,
    FrozenDomainModel,
    MasterSeed,
    ModelInputWidth,
    ModelOutputWidth,
    ModelParameterValue,
    ProcedureIdentity,
    SchemaVersion,
    TextValue,
)
from fedsira.runtime import (
    NUMERICAL_RUNTIME_DEPENDENCY,
    REPOSITORY_ROOT,
    numerical_runtime_identity,
)

CHECKPOINT_SCHEMA_VERSION: SchemaVersion = "fedsira|checkpoint|1"

CHECKPOINT_PROCEDURE_IDENTITIES: tuple[tuple[ArtifactFamily, ProcedureIdentity], ...] = (
    (ArtifactFamily.ANCHOR_CHECKPOINT, "fedsira|anchor_checkpoint|1"),
    (ArtifactFamily.SOURCE_CANDIDATE_CHECKPOINT, "fedsira|source_candidate_checkpoint|1"),
    (ArtifactFamily.REPRODUCTION_CHECKPOINT, "fedsira|reproduction_checkpoint|1"),
    (ArtifactFamily.BASELINE_CHECKPOINT, "fedsira|baseline_checkpoint|1"),
)

CHECKPOINT_PRODUCERS: tuple[tuple[ArtifactFamily, ArtifactProducer], ...] = (
    (ArtifactFamily.ANCHOR_CHECKPOINT, ArtifactProducer.ANCHOR_TRAINING),
    (ArtifactFamily.SOURCE_CANDIDATE_CHECKPOINT, ArtifactProducer.SOURCE_TRAINING),
    (ArtifactFamily.REPRODUCTION_CHECKPOINT, ArtifactProducer.REPRODUCTION_PRODUCER),
    (ArtifactFamily.BASELINE_CHECKPOINT, ArtifactProducer.BASELINE_TRAINER),
)


class CheckpointPayload(FrozenDomainModel):
    schema_version: SchemaVersion
    dataset: DatasetId
    family: ArtifactFamily
    master_seed: MasterSeed
    stage_identity: TextValue
    dataset_manifest_hash: DatasetManifestDigest
    model_input_width: ModelInputWidth
    model_output_width: ModelOutputWidth
    flat_parameters_identity: ArtifactDigest
    parameters: tuple[ModelParameterValue, ...]


def publish_anchor_checkpoints(
    dataset: DatasetId,
    master_seed: MasterSeed,
    anchor: RealAnchor,
) -> tuple[ArtifactManifest, ...]:
    stages = (
        ("final", anchor.flat_parameters),
        *tuple(
            (f"round-start-{round_index:02d}", round_parameters)
            for round_index, round_parameters in enumerate(anchor.round_start_flat_parameters)
        ),
    )
    published: list[ArtifactManifest] = []
    for stage_identity, parameters in stages:
        detached = parameters.detach().cpu().reshape(-1)
        slot = checkpoint_slot(
            ArtifactFamily.ANCHOR_CHECKPOINT,
            checkpoint_stage_instance(master_seed, stage_identity),
        )
        payload = CheckpointPayload(
            schema_version=CHECKPOINT_SCHEMA_VERSION,
            dataset=dataset,
            family=ArtifactFamily.ANCHOR_CHECKPOINT,
            master_seed=master_seed,
            stage_identity=stage_identity,
            dataset_manifest_hash=anchor.dataset_manifest_hash,
            model_input_width=anchor.input_width,
            model_output_width=anchor.output_width,
            flat_parameters_identity=flat_parameters_identity(parameters),
            parameters=tuple(float(detached[index].item()) for index in range(detached.numel())),
        )
        manifest, _reused = publish_checkpoint(
            ArtifactFamily.ANCHOR_CHECKPOINT,
            slot,
            payload,
            (
                ArtifactDependency(
                    kind=ArtifactDependencyKind.CONTENT,
                    dependency="prepared-evidence",
                    digest=anchor.dataset_manifest_hash,
                ),
            ),
        )
        published.append(manifest)
    return tuple(published)


def publish_trained_update(
    family: ArtifactFamily,
    dataset: DatasetId,
    master_seed: MasterSeed,
    stage_identity: TextValue,
    dataset_manifest_hash: DatasetManifestDigest,
    update: torch.Tensor,
    input_width: ModelInputWidth,
    output_width: ModelOutputWidth,
) -> ArtifactManifest:
    detached = update.detach().cpu().reshape(-1)
    slot = checkpoint_slot(family, checkpoint_stage_instance(master_seed, stage_identity))
    payload = CheckpointPayload(
        schema_version=CHECKPOINT_SCHEMA_VERSION,
        dataset=dataset,
        family=family,
        master_seed=master_seed,
        stage_identity=stage_identity,
        dataset_manifest_hash=dataset_manifest_hash,
        model_input_width=input_width,
        model_output_width=output_width,
        flat_parameters_identity=flat_parameters_identity(update),
        parameters=tuple(float(detached[index].item()) for index in range(detached.numel())),
    )
    manifest, _reused = publish_checkpoint(
        family,
        slot,
        payload,
        (
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency="prepared-evidence",
                digest=dataset_manifest_hash,
            ),
        ),
    )
    return manifest


def source_candidate_stage_identity(episode: TextValue, source_domain: DomainId) -> TextValue:
    return f"source-candidate-{episode}-{source_domain}"


def reproduction_stage_identity(domain: DomainId, condition: TextValue) -> TextValue:
    return f"reproduction-{domain}-{condition}"


def checkpoint_procedure_identity(family: ArtifactFamily) -> ProcedureIdentity:
    for candidate, identity in CHECKPOINT_PROCEDURE_IDENTITIES:
        if candidate is family:
            return identity
    raise ValueError(f"artifact family is not a checkpoint family: {family.value}")


def checkpoint_producer(family: ArtifactFamily) -> ArtifactProducer:
    for candidate, producer in CHECKPOINT_PRODUCERS:
        if candidate is family:
            return producer
    raise ValueError(f"artifact family is not a checkpoint family: {family.value}")


def checkpoint_slot(
    family: ArtifactFamily,
    instance: ArtifactInstanceToken,
    experiment: TextValue | None = None,
) -> ArtifactSlot:
    return ArtifactSlot(family=family, instance=instance, experiment=experiment)


def checkpoint_stage_instance(
    master_seed: MasterSeed, stage_identity: TextValue
) -> ArtifactInstanceToken:
    return f"seed-{master_seed}-{stage_identity}"


def publish_checkpoint(
    family: ArtifactFamily,
    slot: ArtifactSlot,
    payload: CheckpointPayload,
    dependencies: tuple[ArtifactDependency, ...],
) -> tuple[ArtifactManifest, ArtifactReuseDecision]:
    return publish_artifact(
        slot=slot,
        producer=checkpoint_producer(family),
        payload=payload.model_dump_json().encode("utf-8"),
        dependencies=(
            *dependencies,
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=NUMERICAL_RUNTIME_DEPENDENCY,
                digest=numerical_runtime_identity(),
            ),
        ),
        procedure_identity=checkpoint_procedure_identity(family),
        slot_directory=REPOSITORY_ROOT / artifact_slot_directory(slot),
        staging_root=REPOSITORY_ROOT / artifact_staging_root(),
    )
