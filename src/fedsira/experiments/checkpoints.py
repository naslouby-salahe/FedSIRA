from __future__ import annotations

import re

import torch

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
    configuration_scope_dependency,
    publish_artifact,
)
from fedsira.datasets.common import RealAnchor, flat_parameters_identity
from fedsira.domain.enums import (
    ArtifactDependencyKind,
    ArtifactDependencyLabel,
    ArtifactFamily,
    ArtifactProducer,
    DatasetId,
    ExperimentName,
    ProposalEpisode,
)
from fedsira.domain.types import (
    ArtifactDigest,
    ArtifactInstanceToken,
    CheckpointStageIdentity,
    ConditionName,
    DatasetClassToken,
    DatasetManifestDigest,
    DomainId,
    FrozenDomainModel,
    MasterSeed,
    ModelInputWidth,
    ModelOutputWidth,
    ModelParameterValue,
    ProcedureIdentity,
    SchemaVersion,
)
from fedsira.runtime import (
    current_application_context,
    numerical_runtime_identity,
)

CHECKPOINT_SCHEMA_VERSION: SchemaVersion = "fedsira|checkpoint|2"

NON_SLUG_CHARACTER_RUN = re.compile(r"[^A-Za-z0-9]+")

CHECKPOINT_PROCEDURE_IDENTITIES: tuple[tuple[ArtifactFamily, ProcedureIdentity], ...] = (
    (ArtifactFamily.ANCHOR_CHECKPOINT, "fedsira|anchor_checkpoint|2"),
    (ArtifactFamily.SOURCE_CANDIDATE_CHECKPOINT, "fedsira|source_candidate_checkpoint|2"),
    (ArtifactFamily.REPRODUCTION_CHECKPOINT, "fedsira|reproduction_checkpoint|2"),
    (ArtifactFamily.BASELINE_CHECKPOINT, "fedsira|baseline_checkpoint|2"),
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
    stage_identity: CheckpointStageIdentity
    dataset_manifest_hash: DatasetManifestDigest
    model_input_width: ModelInputWidth
    model_output_width: ModelOutputWidth
    class_vocabulary: tuple[DatasetClassToken, ...]
    flat_parameters_identity: ArtifactDigest
    parameters: tuple[ModelParameterValue, ...]


def publish_anchor_checkpoints(
    dataset: DatasetId,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    class_vocabulary: tuple[DatasetClassToken, ...],
) -> tuple[ArtifactManifest, ...]:
    stages: tuple[tuple[CheckpointStageIdentity, torch.Tensor], ...] = (
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
            checkpoint_stage_instance(dataset, master_seed, stage_identity),
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
            class_vocabulary=class_vocabulary,
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
                    dependency=ArtifactDependencyLabel.PREPARED_EVIDENCE,
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
    stage_identity: CheckpointStageIdentity,
    dataset_manifest_hash: DatasetManifestDigest,
    update: torch.Tensor,
    input_width: ModelInputWidth,
    output_width: ModelOutputWidth,
    class_vocabulary: tuple[DatasetClassToken, ...],
) -> ArtifactManifest:
    detached = update.detach().cpu().reshape(-1)
    slot = checkpoint_slot(family, checkpoint_stage_instance(dataset, master_seed, stage_identity))
    payload = CheckpointPayload(
        schema_version=CHECKPOINT_SCHEMA_VERSION,
        dataset=dataset,
        family=family,
        master_seed=master_seed,
        stage_identity=stage_identity,
        dataset_manifest_hash=dataset_manifest_hash,
        model_input_width=input_width,
        model_output_width=output_width,
        class_vocabulary=class_vocabulary,
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
                dependency=ArtifactDependencyLabel.PREPARED_EVIDENCE,
                digest=dataset_manifest_hash,
            ),
        ),
    )
    return manifest


def source_candidate_stage_identity(
    episode: ProposalEpisode, source_domain: DomainId
) -> CheckpointStageIdentity:
    return f"source-candidate-{episode}-{source_domain}"


def reproduction_stage_identity(
    domain: DomainId, condition: ConditionName
) -> CheckpointStageIdentity:
    return f"reproduction-{domain}-{condition}"


def checkpoint_procedure_identity(family: ArtifactFamily) -> ProcedureIdentity:
    for candidate, identity in CHECKPOINT_PROCEDURE_IDENTITIES:
        if candidate is family:
            return identity
    raise ValueError(f"artifact family is not a checkpoint family: {family}")


def checkpoint_producer(family: ArtifactFamily) -> ArtifactProducer:
    for candidate, producer in CHECKPOINT_PRODUCERS:
        if candidate is family:
            return producer
    raise ValueError(f"artifact family is not a checkpoint family: {family}")


def checkpoint_slot(
    family: ArtifactFamily,
    instance: ArtifactInstanceToken,
    experiment: ExperimentName | None = None,
) -> ArtifactSlot:
    return ArtifactSlot(family=family, instance=instance, experiment=experiment)


def checkpoint_stage_instance(
    dataset: DatasetId, master_seed: MasterSeed, stage_identity: CheckpointStageIdentity
) -> ArtifactInstanceToken:
    slug = NON_SLUG_CHARACTER_RUN.sub("-", stage_identity).strip("-").lower()
    return f"{dataset.value}-seed-{master_seed}-{slug}"


def publish_checkpoint(
    family: ArtifactFamily,
    slot: ArtifactSlot,
    payload: CheckpointPayload,
    dependencies: tuple[ArtifactDependency, ...],
) -> tuple[ArtifactManifest, ArtifactReuseDecision]:
    config = current_application_context().scientific_config
    model = config.model
    if family is ArtifactFamily.ANCHOR_CHECKPOINT:
        training_configuration = (
            ArtifactConfigurationComponent(
                name=ArtifactDependencyLabel.OPTIMIZER_CONFIGURATION,
                configuration=model.optimizer.model_dump_json(),
            ),
            ArtifactConfigurationComponent(
                name=ArtifactDependencyLabel.TRAINING_CONFIGURATION,
                configuration=model.training.model_dump_json(),
            ),
            ArtifactConfigurationComponent(
                name=ArtifactDependencyLabel.ANCHOR_FEDAVG_CONFIGURATION,
                configuration=model.anchor_fedavg.model_dump_json(),
            ),
            ArtifactConfigurationComponent(
                name=ArtifactDependencyLabel.DATA_LOADER,
                configuration=config.execution.data_loader.model_dump_json(),
            ),
        )
    elif family is ArtifactFamily.BASELINE_CHECKPOINT:
        training_configuration = (
            ArtifactConfigurationComponent(
                name=ArtifactDependencyLabel.OPTIMIZER_CONFIGURATION,
                configuration=model.optimizer.model_dump_json(),
            ),
            ArtifactConfigurationComponent(
                name=ArtifactDependencyLabel.TRAINING_CONFIGURATION,
                configuration=model.training.model_dump_json(),
            ),
            ArtifactConfigurationComponent(
                name=ArtifactDependencyLabel.ANCHOR_FEDAVG_CONFIGURATION,
                configuration=model.anchor_fedavg.model_dump_json(),
            ),
            ArtifactConfigurationComponent(
                name=ArtifactDependencyLabel.BASELINE_CONFIGURATION,
                configuration=config.baselines.model_dump_json(),
            ),
            ArtifactConfigurationComponent(
                name=ArtifactDependencyLabel.ATTACK_CONFIGURATION,
                configuration=config.attacks_and_boundaries.model_dump_json(),
            ),
            ArtifactConfigurationComponent(
                name=ArtifactDependencyLabel.DATA_LOADER,
                configuration=config.execution.data_loader.model_dump_json(),
            ),
        )
    else:
        training_configuration = (
            ArtifactConfigurationComponent(
                name=ArtifactDependencyLabel.OPTIMIZER_CONFIGURATION,
                configuration=model.optimizer.model_dump_json(),
            ),
            ArtifactConfigurationComponent(
                name=ArtifactDependencyLabel.TRAINING_CONFIGURATION,
                configuration=model.training.model_dump_json(),
            ),
            ArtifactConfigurationComponent(
                name=ArtifactDependencyLabel.POST_REFERENCE_CONFIGURATION,
                configuration=model.post_reference.model_dump_json(),
            ),
            ArtifactConfigurationComponent(
                name=ArtifactDependencyLabel.VERIFIER_AWARE_OVERRIDE,
                configuration=model.verifier_aware_backdoor_override.model_dump_json(),
            ),
            ArtifactConfigurationComponent(
                name=ArtifactDependencyLabel.ATTACK_CONFIGURATION,
                configuration=config.attacks_and_boundaries.model_dump_json(),
            ),
            ArtifactConfigurationComponent(
                name=ArtifactDependencyLabel.DATA_LOADER,
                configuration=config.execution.data_loader.model_dump_json(),
            ),
        )
    return publish_artifact(
        slot=slot,
        producer=checkpoint_producer(family),
        payload=payload.model_dump_json().encode("utf-8"),
        dependencies=(
            *dependencies,
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=ArtifactDependencyLabel.NUMERICAL_RUNTIME,
                digest=numerical_runtime_identity(),
            ),
            configuration_scope_dependency(
                ArtifactConfigurationScope(
                    scope=f"training:{family}",
                    components=training_configuration,
                )
            ),
        ),
        procedure_identity=checkpoint_procedure_identity(family),
        slot_directory=current_repository_root() / artifact_slot_directory(slot),
        staging_root=current_repository_root() / artifact_staging_root(),
    )
