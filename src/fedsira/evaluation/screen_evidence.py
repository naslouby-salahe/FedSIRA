import torch

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
from fedsira.datasets.common import DatasetAdapter, RealAnchor, Role, flat_parameters_identity
from fedsira.domain.enums import (
    AdmissionOpeningMode,
    ArtifactDependencyKind,
    ArtifactFamily,
    ArtifactProducer,
    DatasetId,
)
from fedsira.domain.models import MetricResult
from fedsira.domain.types import (
    ArtifactDigest,
    DatasetManifestDigest,
    DomainId,
    EvidenceAdequate,
    FrozenDomainModel,
    MasterSeed,
    NamespaceSeed,
    OpeningPredicateSatisfied,
    ProcedureIdentity,
    SchemaVersion,
    ScientificCellCount,
    TextValue,
)
from fedsira.evaluation.metrics import (
    compute_screen_differential,
    compute_unmatched_screen_differential,
    evaluate_domain,
    supported_macro_f1_harm,
    target_capability_gain,
)
from fedsira.experiments.definitions import AblationVariant
from fedsira.protocol.capability_contract import screen_evidence_is_adequate
from fedsira.protocol.proposal import (
    ScreenDomainResult,
    candidate_free_screen_domain_predicate,
    raw_target_f1_screen_domain_decision_is_positive,
    screen_domain_decision_is_positive,
    unmatched_control_screen_domain_decision_is_positive,
)
from fedsira.runtime import REPOSITORY_ROOT, current_application_context, derive_uint32

SCREEN_MATCHING_SCHEMA_VERSION: SchemaVersion = "fedsira|screen_matching|1"
SCREEN_MATCHING_PROCEDURE_IDENTITY: ProcedureIdentity = "fedsira|screen_matching|1"
SCREEN_MATCHING_ANCHOR_MODEL_DEPENDENCY = "anchor-model"
SCREEN_MATCHING_CANDIDATE_MODEL_DEPENDENCY = "source-candidate-model"
SCREEN_MATCHING_PREPARED_EVIDENCE_DEPENDENCY = "prepared-evidence"
NO_CANDIDATE_MODEL_IDENTITY: ArtifactDigest = "0" * 64


class ScreenMatchingPayload(FrozenDomainModel):
    schema_version: SchemaVersion
    dataset: DatasetId
    domain: DomainId
    opening_mode: AdmissionOpeningMode
    screen_predicate_variant: TextValue | None
    is_evidence_adequate: EvidenceAdequate
    meets_opening_predicate: OpeningPredicateSatisfied
    anchor_model_identity: ArtifactDigest
    candidate_model_identity: ArtifactDigest
    dataset_manifest_hash: DatasetManifestDigest
    screen_fold_seed: NamespaceSeed
    screen_fold_count: ScientificCellCount
    target_f1_gain: MetricResult | None = None
    supported_macro_f1_harm: MetricResult | None = None
    benign_far_increase: MetricResult | None = None


def screen_matching_slot(
    dataset: DatasetId,
    domain: DomainId,
    anchor_model_identity: ArtifactDigest,
    candidate_model_identity: ArtifactDigest,
) -> ArtifactSlot:
    return ArtifactSlot(
        family=ArtifactFamily.SCREEN_MATCHING_ARTIFACT,
        instance=artifact_instance_token(
            f"screen-{domain}",
            dataset.value,
            anchor_model_identity,
            candidate_model_identity,
        ),
    )


def publish_screen_matching(
    payload: ScreenMatchingPayload,
) -> tuple[ArtifactManifest, ArtifactReuseDecision]:
    slot = screen_matching_slot(
        payload.dataset,
        payload.domain,
        payload.anchor_model_identity,
        payload.candidate_model_identity,
    )
    return publish_artifact(
        slot=slot,
        producer=ArtifactProducer.PROPOSAL_SCREEN_CALIBRATION,
        payload=payload.model_dump_json().encode("utf-8"),
        dependencies=(
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=SCREEN_MATCHING_ANCHOR_MODEL_DEPENDENCY,
                digest=payload.anchor_model_identity,
            ),
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=SCREEN_MATCHING_CANDIDATE_MODEL_DEPENDENCY,
                digest=payload.candidate_model_identity,
            ),
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=SCREEN_MATCHING_PREPARED_EVIDENCE_DEPENDENCY,
                digest=payload.dataset_manifest_hash,
            ),
        ),
        procedure_identity=SCREEN_MATCHING_PROCEDURE_IDENTITY,
        slot_directory=REPOSITORY_ROOT / artifact_slot_directory(slot),
        staging_root=REPOSITORY_ROOT / artifact_staging_root(),
    )


def evaluate_screen_domain(
    adapter: DatasetAdapter,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_delta: torch.Tensor | None,
    domain: DomainId,
    opening_mode: AdmissionOpeningMode,
    screen_predicate_variant: AblationVariant | None,
) -> ScreenDomainResult:
    config = current_application_context().scientific_config
    dataset = adapter.specification.dataset
    fold_count = config.protocol.proposal_screen.fold_count
    fold_seed = derive_uint32("SCREEN_FOLD_SEED", master_seed)
    anchor_model_identity = flat_parameters_identity(anchor.flat_parameters)
    candidate_model_identity = (
        NO_CANDIDATE_MODEL_IDENTITY
        if source_delta is None
        else flat_parameters_identity(anchor.flat_parameters + source_delta)
    )

    def recorded(
        result: ScreenDomainResult,
        metrics: tuple[MetricResult | None, MetricResult | None, MetricResult | None] = (
            None,
            None,
            None,
        ),
    ) -> ScreenDomainResult:
        publish_screen_matching(
            ScreenMatchingPayload(
                schema_version=SCREEN_MATCHING_SCHEMA_VERSION,
                dataset=dataset,
                domain=domain,
                opening_mode=opening_mode,
                screen_predicate_variant=(
                    None if screen_predicate_variant is None else screen_predicate_variant.value
                ),
                is_evidence_adequate=result.is_evidence_adequate,
                meets_opening_predicate=result.meets_opening_predicate,
                anchor_model_identity=anchor_model_identity,
                candidate_model_identity=candidate_model_identity,
                dataset_manifest_hash=anchor.dataset_manifest_hash,
                screen_fold_seed=fold_seed,
                screen_fold_count=fold_count,
                target_f1_gain=metrics[0],
                supported_macro_f1_harm=metrics[1],
                benign_far_increase=metrics[2],
            )
        )
        return result

    target_rows = adapter.load_rows(domain, adapter.target_class_token, Role.CANDIDATE_SCREEN)
    target_count = 0 if target_rows is None else target_rows.row_count
    if not screen_evidence_is_adequate(target_count, config.capability_contract.evidence_minima):
        return recorded(
            ScreenDomainResult(
                domain=domain, is_evidence_adequate=False, meets_opening_predicate=False
            )
        )
    if opening_mode is AdmissionOpeningMode.CANDIDATE_FREE:
        anchor_screen = evaluate_domain(
            adapter,
            anchor,
            anchor.flat_parameters,
            domain,
            role=Role.POST_REFERENCE_REPLAY,
            target_role=Role.CANDIDATE_SCREEN,
        )
        anchor_target_f1 = (
            anchor_screen.target_f1
            if anchor_screen is not None
            else MetricResult(value=None, denominator=0)
        )
        predicate = candidate_free_screen_domain_predicate(
            anchor_target_f1,
            config.capability_contract,
        )
        return recorded(
            ScreenDomainResult(
                domain=domain, is_evidence_adequate=True, meets_opening_predicate=predicate
            ),
            (anchor_target_f1, None, None),
        )
    if source_delta is None:
        return recorded(
            ScreenDomainResult(
                domain=domain, is_evidence_adequate=True, meets_opening_predicate=False
            )
        )
    candidate_flat = anchor.flat_parameters + source_delta
    anchor_screen = evaluate_domain(
        adapter,
        anchor,
        anchor.flat_parameters,
        domain,
        role=Role.POST_REFERENCE_REPLAY,
        target_role=Role.CANDIDATE_SCREEN,
    )
    source_screen = evaluate_domain(
        adapter,
        anchor,
        candidate_flat,
        domain,
        role=Role.POST_REFERENCE_REPLAY,
        target_role=Role.CANDIDATE_SCREEN,
    )
    if anchor_screen is None or source_screen is None:
        return recorded(
            ScreenDomainResult(
                domain=domain, is_evidence_adequate=True, meets_opening_predicate=False
            )
        )
    target_f1_gain = target_capability_gain(source_screen.target_f1, anchor_screen.target_f1)
    supported_macro_f1_drop = supported_macro_f1_harm(
        anchor_screen.supported_macro_f1, source_screen.supported_macro_f1
    )
    benign_far_increase = (
        MetricResult(
            value=source_screen.benign_far.value - anchor_screen.benign_far.value,
            denominator=1,
        )
        if source_screen.benign_far.value is not None and anchor_screen.benign_far.value is not None
        else MetricResult(value=None, denominator=0)
    )
    if screen_predicate_variant is AblationVariant.RAW_TARGET_F1_SCREEN_ONLY:
        predicate = raw_target_f1_screen_domain_decision_is_positive(
            target_f1_gain,
            supported_macro_f1_drop,
            benign_far_increase,
            config.capability_contract,
        )
    elif screen_predicate_variant is AblationVariant.NO_MATCHED_CONTROL:
        unmatched_differential = compute_unmatched_screen_differential(
            adapter, anchor, source_delta, domain
        )
        predicate = unmatched_control_screen_domain_decision_is_positive(
            unmatched_differential,
            target_f1_gain,
            supported_macro_f1_drop,
            benign_far_increase,
            config.protocol.proposal_screen,
            config.capability_contract,
        )
    else:
        differential_a = compute_screen_differential(
            adapter, master_seed, anchor, source_delta, domain
        )
        predicate = screen_domain_decision_is_positive(
            differential_a,
            target_f1_gain,
            supported_macro_f1_drop,
            benign_far_increase,
            config.protocol.proposal_screen,
            config.capability_contract,
        )
    return recorded(
        ScreenDomainResult(
            domain=domain, is_evidence_adequate=True, meets_opening_predicate=predicate
        ),
        (target_f1_gain, supported_macro_f1_drop, benign_far_increase),
    )
