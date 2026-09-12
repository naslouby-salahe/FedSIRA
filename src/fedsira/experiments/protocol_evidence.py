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
from fedsira.datasets.common import RealAnchor, flat_parameters_identity
from fedsira.domain.enums import (
    AdmissionState,
    ArtifactDependencyKind,
    ArtifactFamily,
    ArtifactProducer,
    TernaryOutcome,
)
from fedsira.domain.models import ScientificCell
from fedsira.domain.types import (
    ArtifactDigest,
    BooleanValue,
    DatasetManifestDigest,
    DomainId,
    ExperimentName,
    FrozenDomainModel,
    MasterSeed,
    MethodName,
    Percentile,
    ProcedureIdentity,
    ReproductionRowCount,
    SchemaVersion,
    ScientificCellCount,
    TextValue,
)
from fedsira.protocol.baselines.registry import BaselineIdentity
from fedsira.runtime import REPOSITORY_ROOT, current_application_context

PROTOCOL_EVIDENCE_SCHEMA_VERSION: SchemaVersion = "fedsira|protocol_evidence|1"  # TODO: should be enum

VERIFIER_ASSIGNMENT_PROCEDURE_IDENTITY: ProcedureIdentity = "fedsira|verifier_assignment_report|1"  # TODO: should be enum
REPRODUCTION_CERTIFICATE_PROCEDURE_IDENTITY: ProcedureIdentity = (
    "fedsira|reproduction_certificate|1"  # TODO: should be enum
)
KRUM_SYNTHESIS_PROCEDURE_IDENTITY: ProcedureIdentity = "fedsira|krum_synthesized_update|1"  # TODO: should be enum
FINAL_GATE_PROCEDURE_IDENTITY: ProcedureIdentity = "fedsira|final_gate_decision|1"  # TODO: should be enum
BASELINE_CALIBRATION_PROCEDURE_IDENTITY: ProcedureIdentity = "fedsira|baseline_calibration|1"  # TODO: should be enum

VERIFIER_ASSIGNMENT_DEPENDENCY = "commitment-identity"  # TODO: should be enum
REPRODUCTION_CERTIFICATE_DEPENDENCY = "certified-row-reports"  # TODO: should be enum
KRUM_SYNTHESIS_DEPENDENCY = "certified-reproduction-rows"  # TODO: should be enum
FINAL_GATE_DEPENDENCY = "production-model"  # TODO: should be enum
BASELINE_CALIBRATION_DEPENDENCY = "prepared-evidence"  # TODO: should be enum

CORRECTNESS_BY_REQUIRED_REPORTS_CERTIFICATE_RULE: TextValue = "required-positive-reports"  # TODO: should be enum


class VerifierReportOutcome(FrozenDomainModel):
    verifier_domain: DomainId
    outcome: TernaryOutcome


class VerifierAssignmentReportPayload(FrozenDomainModel):
    schema_version: SchemaVersion
    experiment: ExperimentName
    master_seed: MasterSeed
    reproducer_domain: DomainId
    commitment_identity: ArtifactDigest
    panel: tuple[DomainId, ...]
    panel_size: ScientificCellCount
    required_positive_reports: ScientificCellCount
    reports: tuple[VerifierReportOutcome, ...]
    positive_report_count: ScientificCellCount
    certified: BooleanValue


class ReproductionCertificatePayload(FrozenDomainModel):
    schema_version: SchemaVersion
    experiment: ExperimentName
    master_seed: MasterSeed
    reproducer_domain: DomainId
    commitment_identity: ArtifactDigest
    certificate_rule: TextValue
    panel_size: ScientificCellCount
    required_positive_reports: ScientificCellCount
    certified_row_count: ReproductionRowCount
    required_row_count: ReproductionRowCount
    certified: BooleanValue


class KrumSynthesizedUpdatePayload(FrozenDomainModel):
    schema_version: SchemaVersion
    experiment: ExperimentName
    master_seed: MasterSeed
    committee_size: ScientificCellCount
    maximum_byzantine_reproduction_rows: ReproductionRowCount
    selected_flat_parameters_identity: ArtifactDigest
    selected_update_identity: ArtifactDigest


class FinalGateDecisionPayload(FrozenDomainModel):
    schema_version: SchemaVersion
    experiment: ExperimentName
    master_seed: MasterSeed
    production_model_identity: ArtifactDigest
    plurality_synthesis_active: BooleanValue
    decision: AdmissionState


class BaselineCalibrationPayload(FrozenDomainModel):
    schema_version: SchemaVersion
    experiment: ExperimentName
    master_seed: MasterSeed
    baseline: TextValue
    calibration_rule: TextValue
    calibration_population: ArtifactDigest
    anchor_model_identity: ArtifactDigest
    calibration_percentile: Percentile
    dataset_manifest_hash: DatasetManifestDigest


def _publish(
    family: ArtifactFamily,
    instance: ArtifactDigest | TextValue,
    experiment: ExperimentName,
    producer: ArtifactProducer,
    payload: FrozenDomainModel,
    dependencies: tuple[ArtifactDependency, ...],
    procedure_identity: ProcedureIdentity,
) -> tuple[ArtifactManifest, ArtifactReuseDecision]:
    slot = ArtifactSlot(
        family=family,
        instance=artifact_instance_token(str(instance), experiment),
        experiment=experiment,
    )
    return publish_artifact(
        slot=slot,
        producer=producer,
        payload=payload.model_dump_json().encode("utf-8"),
        dependencies=dependencies,
        procedure_identity=procedure_identity,
        slot_directory=REPOSITORY_ROOT / artifact_slot_directory(slot),
        staging_root=REPOSITORY_ROOT / artifact_staging_root(),
    )


def publish_verifier_assignment_report(
    payload: VerifierAssignmentReportPayload,
) -> tuple[ArtifactManifest, ArtifactReuseDecision]:
    return _publish(
        ArtifactFamily.VERIFIER_ASSIGNMENT_REPORT,
        payload.commitment_identity,
        payload.experiment,
        ArtifactProducer.EXTERNAL_VERIFICATION,
        payload,
        (
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=VERIFIER_ASSIGNMENT_DEPENDENCY,
                digest=payload.commitment_identity,
            ),
        ),
        VERIFIER_ASSIGNMENT_PROCEDURE_IDENTITY,
    )


def publish_reproduction_certificate(
    payload: ReproductionCertificatePayload,
) -> tuple[ArtifactManifest, ArtifactReuseDecision]:
    return _publish(
        ArtifactFamily.REPRODUCTION_CERTIFICATE,
        payload.commitment_identity,
        payload.experiment,
        ArtifactProducer.CERTIFICATE_PRODUCER,
        payload,
        (
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=REPRODUCTION_CERTIFICATE_DEPENDENCY,
                digest=payload.commitment_identity,
            ),
        ),
        REPRODUCTION_CERTIFICATE_PROCEDURE_IDENTITY,
    )


def publish_krum_synthesized_update(
    payload: KrumSynthesizedUpdatePayload,
) -> tuple[ArtifactManifest, ArtifactReuseDecision]:
    return _publish(
        ArtifactFamily.KRUM_SYNTHESIZED_UPDATE,
        payload.selected_flat_parameters_identity,
        payload.experiment,
        ArtifactProducer.SYNTHESIS_PRODUCER,
        payload,
        (
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=KRUM_SYNTHESIS_DEPENDENCY,
                digest=payload.selected_update_identity,
            ),
        ),
        KRUM_SYNTHESIS_PROCEDURE_IDENTITY,
    )


def publish_final_gate_decision(
    payload: FinalGateDecisionPayload,
) -> tuple[ArtifactManifest, ArtifactReuseDecision]:
    return _publish(
        ArtifactFamily.FINAL_GATE_DECISION,
        payload.production_model_identity,
        payload.experiment,
        ArtifactProducer.FINAL_GATE_EVALUATOR,
        payload,
        (
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=FINAL_GATE_DEPENDENCY,
                digest=payload.production_model_identity,
            ),
        ),
        FINAL_GATE_PROCEDURE_IDENTITY,
    )


def publish_baseline_calibration(
    payload: BaselineCalibrationPayload,
) -> tuple[ArtifactManifest, ArtifactReuseDecision]:
    return _publish(
        ArtifactFamily.BASELINE_CALIBRATION_ARTIFACT,
        payload.baseline,
        payload.experiment,
        ArtifactProducer.BASELINE_CALIBRATION,
        payload,
        (
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=BASELINE_CALIBRATION_DEPENDENCY,
                digest=payload.dataset_manifest_hash,
            ),
        ),
        BASELINE_CALIBRATION_PROCEDURE_IDENTITY,
    )


CALIBRATED_BASELINE_METHODS: tuple[BaselineIdentity, ...] = (
    BaselineIdentity.UPDATE_RECONSTRUCTION_FILTER,
    BaselineIdentity.SOURCE_UPDATE_SANITIZATION_REFERENCE,
    BaselineIdentity.RECOVERY_AFTER_SOURCE_ADMISSION,
)


def baseline_calibration_rule(method: MethodName) -> tuple[TextValue, Percentile] | None:
    baselines = current_application_context().scientific_config.baselines
    if method is BaselineIdentity.UPDATE_RECONSTRUCTION_FILTER:
        return (
            "reconstruction-error-percentile",
            baselines.reconstruction_filter.calibration_percentile,
        )
    if method is BaselineIdentity.SOURCE_UPDATE_SANITIZATION_REFERENCE:
        return (
            "coordinate-absolute-deviation-percentile",
            baselines.source_update_sanitization.coordinate_bound_percentile,
        )
    if method is BaselineIdentity.RECOVERY_AFTER_SOURCE_ADMISSION:
        return (
            "triggered-to-benign-rate-percentile",
            baselines.recovery_after_source_admission.backdoor_alarm_percentile,
        )
    return None


def record_baseline_calibration(cell: ScientificCell, anchor: RealAnchor) -> None:
    calibration = baseline_calibration_rule(cell.method)
    if calibration is None:
        return
    rule, percentile = calibration
    anchor_model_identity = flat_parameters_identity(anchor.flat_parameters)
    publish_baseline_calibration(
        BaselineCalibrationPayload(
            schema_version=PROTOCOL_EVIDENCE_SCHEMA_VERSION,
            experiment=cell.experiment,
            master_seed=cell.master_seed,
            baseline=cell.method,
            calibration_rule=rule,
            calibration_population=anchor_model_identity,
            anchor_model_identity=anchor_model_identity,
            calibration_percentile=percentile,
            dataset_manifest_hash=anchor.dataset_manifest_hash,
        )
    )


def record_verification_evidence(
    *,
    cell: ScientificCell,
    reproducer_domain: DomainId,
    commitment_identity: ArtifactDigest,
    panel: tuple[DomainId, ...],
    reports: tuple[TernaryOutcome, ...],
    certificate_is_valid: BooleanValue,
    certified_row_count: ReproductionRowCount,
    required_row_count: ReproductionRowCount,
) -> None:
    verification = current_application_context().scientific_config.protocol.verification
    panel_size = verification.panel_size
    required_positive_reports = verification.required_positive_reports
    publish_verifier_assignment_report(
        VerifierAssignmentReportPayload(
            schema_version=PROTOCOL_EVIDENCE_SCHEMA_VERSION,
            experiment=cell.experiment,
            master_seed=cell.master_seed,
            reproducer_domain=reproducer_domain,
            commitment_identity=commitment_identity,
            panel=panel,
            panel_size=panel_size,
            required_positive_reports=required_positive_reports,
            reports=tuple(
                VerifierReportOutcome(verifier_domain=verifier_domain, outcome=outcome)
                for verifier_domain, outcome in zip(panel, reports, strict=True)
            ),
            positive_report_count=sum(
                1 for outcome in reports if outcome is TernaryOutcome.POSITIVE
            ),
            certified=certificate_is_valid,
        )
    )
    publish_reproduction_certificate(
        ReproductionCertificatePayload(
            schema_version=PROTOCOL_EVIDENCE_SCHEMA_VERSION,
            experiment=cell.experiment,
            master_seed=cell.master_seed,
            reproducer_domain=reproducer_domain,
            commitment_identity=commitment_identity,
            certificate_rule=CORRECTNESS_BY_REQUIRED_REPORTS_CERTIFICATE_RULE,
            panel_size=panel_size,
            required_positive_reports=required_positive_reports,
            certified_row_count=certified_row_count,
            required_row_count=required_row_count,
            certified=certificate_is_valid,
        )
    )


def record_production_evidence(
    *,
    cell: ScientificCell,
    production_checkpoint: torch.Tensor | None,
    krum_selected_update: torch.Tensor | None,
    plurality_synthesis_active: BooleanValue,
    reproduction_row_count: ReproductionRowCount,
    decision: AdmissionState,
) -> None:
    if production_checkpoint is None:
        return
    contract = current_application_context().scientific_config.protocol.synthesis
    production_identity = flat_parameters_identity(production_checkpoint)
    if krum_selected_update is not None:
        publish_krum_synthesized_update(
            KrumSynthesizedUpdatePayload(
                schema_version=PROTOCOL_EVIDENCE_SCHEMA_VERSION,
                experiment=cell.experiment,
                master_seed=cell.master_seed,
                committee_size=reproduction_row_count,
                maximum_byzantine_reproduction_rows=(contract.maximum_byzantine_reproduction_rows),
                selected_flat_parameters_identity=production_identity,
                selected_update_identity=flat_parameters_identity(krum_selected_update),
            )
        )
    publish_final_gate_decision(
        FinalGateDecisionPayload(
            schema_version=PROTOCOL_EVIDENCE_SCHEMA_VERSION,
            experiment=cell.experiment,
            master_seed=cell.master_seed,
            production_model_identity=production_identity,
            plurality_synthesis_active=plurality_synthesis_active,
            decision=decision,
        )
    )
