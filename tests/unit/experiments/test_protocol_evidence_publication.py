from pathlib import Path

import pytest

from fedsira.artifacts.paths import artifact_slot_directory
from fedsira.artifacts.store import (
    read_current_artifact,
    validate_artifact_lifecycle_readable,
)
from fedsira.domain.enums import (
    AdmissionState,
    ArtifactDependencyKind,
    ArtifactFamily,
    ArtifactLifecycleState,
    ExperimentName,
    TernaryOutcome,
)
from fedsira.experiments.protocol_evidence import (
    PROTOCOL_EVIDENCE_SCHEMA_VERSION,
    FinalGateDecisionPayload,
    KrumSynthesizedUpdatePayload,
    ReproductionCertificatePayload,
    VerifierAssignmentReportPayload,
    VerifierReportOutcome,
    publish_final_gate_decision,
    publish_krum_synthesized_update,
    publish_reproduction_certificate,
    publish_verifier_assignment_report,
)
from fedsira.reporting.verification import artifact_manifest_dependency_failures

EXPERIMENT = ExperimentName.MECHANISM_ABLATION


@pytest.fixture
def isolated_repository(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr("fedsira.experiments.protocol_evidence.REPOSITORY_ROOT", tmp_path)
    return tmp_path


def _verifier_report(commitment: str) -> VerifierAssignmentReportPayload:
    return VerifierAssignmentReportPayload(
        schema_version=PROTOCOL_EVIDENCE_SCHEMA_VERSION,
        experiment=EXPERIMENT,
        master_seed=1103,
        reproducer_domain="Danmini Doorbell",
        commitment_identity=commitment,
        panel=("Ennio Doorbell", "Ecobee Thermostat", "Philips B120N10"),
        panel_size=3,
        required_positive_reports=2,
        reports=(
            VerifierReportOutcome(
                verifier_domain="Ennio Doorbell", outcome=TernaryOutcome.POSITIVE
            ),
            VerifierReportOutcome(
                verifier_domain="Ecobee Thermostat", outcome=TernaryOutcome.POSITIVE
            ),
            VerifierReportOutcome(
                verifier_domain="Philips B120N10", outcome=TernaryOutcome.NEGATIVE
            ),
        ),
        positive_report_count=2,
        certified=True,
    )


def test_verifier_report_is_keyed_by_commitment_identity(isolated_repository: Path) -> None:
    first, reused = publish_verifier_assignment_report(_verifier_report("a" * 64))
    assert reused is False
    assert first.family is ArtifactFamily.VERIFIER_ASSIGNMENT_REPORT
    assert first.dependencies[0].digest == "a" * 64
    repeated, reused_again = publish_verifier_assignment_report(_verifier_report("a" * 64))
    assert reused_again is True
    assert repeated.identity == first.identity
    other, _reused = publish_verifier_assignment_report(_verifier_report("b" * 64))
    assert other.identity != first.identity


def test_certificate_round_trips_through_the_slot(isolated_repository: Path) -> None:
    manifest, _reused = publish_reproduction_certificate(
        ReproductionCertificatePayload(
            schema_version=PROTOCOL_EVIDENCE_SCHEMA_VERSION,
            experiment=EXPERIMENT,
            master_seed=1103,
            reproducer_domain="Danmini Doorbell",
            commitment_identity="c" * 64,
            certificate_rule="required-positive-reports",
            panel_size=3,
            required_positive_reports=2,
            certified_row_count=1,
            required_row_count=1,
            certified=True,
        )
    )
    current = read_current_artifact(isolated_repository / artifact_slot_directory(manifest.slot))
    assert current is not None
    _stored, payload = current
    restored = ReproductionCertificatePayload.model_validate_json(payload)
    assert restored.commitment_identity == "c" * 64
    assert restored.certified is True
    assert restored.required_row_count == 1


def test_final_gate_and_krum_declare_their_production_model(isolated_repository: Path) -> None:
    gate, _reused = publish_final_gate_decision(
        FinalGateDecisionPayload(
            schema_version=PROTOCOL_EVIDENCE_SCHEMA_VERSION,
            experiment=EXPERIMENT,
            master_seed=1103,
            production_model_identity="d" * 64,
            plurality_synthesis_active=True,
            decision=AdmissionState.ADMITTED,
        )
    )
    assert gate.family is ArtifactFamily.FINAL_GATE_DECISION
    assert gate.dependencies[0].digest == "d" * 64
    krum, _reused_krum = publish_krum_synthesized_update(
        KrumSynthesizedUpdatePayload(
            schema_version=PROTOCOL_EVIDENCE_SCHEMA_VERSION,
            experiment=EXPERIMENT,
            master_seed=1103,
            committee_size=5,
            maximum_byzantine_reproduction_rows=1,
            selected_flat_parameters_identity="d" * 64,
            selected_update_identity="e" * 64,
        )
    )
    assert krum.family is ArtifactFamily.KRUM_SYNTHESIZED_UPDATE
    assert krum.dependencies[0].digest == "e" * 64
    assert krum.identity != gate.identity


def test_content_digest_dependencies_are_identity_material_not_artifact_edges(
    isolated_repository: Path,
) -> None:
    upstream, _reused = publish_verifier_assignment_report(_verifier_report("a" * 64))
    downstream, _reused_downstream = publish_krum_synthesized_update(
        KrumSynthesizedUpdatePayload(
            schema_version=PROTOCOL_EVIDENCE_SCHEMA_VERSION,
            experiment=EXPERIMENT,
            master_seed=1103,
            committee_size=5,
            maximum_byzantine_reproduction_rows=1,
            selected_flat_parameters_identity="d" * 64,
            selected_update_identity=upstream.identity,
        )
    )
    assert downstream.dependencies[0].kind is ArtifactDependencyKind.CONTENT
    assert artifact_manifest_dependency_failures((downstream,)) == ()
    assert artifact_manifest_dependency_failures((upstream, downstream)) == ()


def test_incomplete_manifest_is_never_valid_evidence(isolated_repository: Path) -> None:
    manifest, _reused = publish_final_gate_decision(
        FinalGateDecisionPayload(
            schema_version=PROTOCOL_EVIDENCE_SCHEMA_VERSION,
            experiment=EXPERIMENT,
            master_seed=1103,
            production_model_identity="f" * 64,
            plurality_synthesis_active=False,
            decision=AdmissionState.DORMANT,
        )
    )
    assert manifest.lifecycle_state is ArtifactLifecycleState.COMPLETE
    staged = manifest.with_lifecycle_state(ArtifactLifecycleState.STAGING)
    assert artifact_manifest_dependency_failures((staged,)) == (
        f"{staged.slot.family.value}/{staged.slot.instance}: {staged.identity} is Staging",
    )
    with pytest.raises(ValueError, match="not Complete"):
        validate_artifact_lifecycle_readable(staged)
