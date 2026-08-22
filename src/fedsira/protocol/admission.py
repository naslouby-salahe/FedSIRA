from collections.abc import Sequence
from dataclasses import dataclass

import torch

from fedsira.config.schema import FinalGateConfig
from fedsira.datasets.nbaiot.schema import NBaiotDomain
from fedsira.domain.enums import ClaimOpeningMode, ClaimState, VerificationOmissionMarker
from fedsira.domain.records import ArtifactDigest, CanonicalToken, SeedBundle
from fedsira.evaluation.aggregation import quantile_type7
from fedsira.evaluation.records import MetricResult


def validate_admission_requires_final_gate(
    state: ClaimState, final_gate_artifact_is_valid: bool
) -> None:
    if state is ClaimState.ADMITTED and not final_gate_artifact_is_valid:
        raise ValueError("Admitted state requires a valid final-gate artifact")


def apply_production_update(
    anchor_flat_parameters: torch.Tensor, production_update: torch.Tensor
) -> torch.Tensor:
    return anchor_flat_parameters + production_update


def resolve_production_update(
    is_plurality_active: bool,
    krum_selected_update: torch.Tensor | None,
    single_reproduction_update: torch.Tensor | None,
) -> torch.Tensor:
    if is_plurality_active:
        if krum_selected_update is None:
            raise ValueError("plurality path requires a Krum-selected update")
        return krum_selected_update
    if single_reproduction_update is None:
        raise ValueError("single-reproduction path requires a selected reproduction update")
    return single_reproduction_update


def validate_production_checkpoint_excludes_source(
    production_update: torch.Tensor, source_update: torch.Tensor | None
) -> None:
    if source_update is not None and torch.equal(production_update, source_update):
        raise ValueError("source checkpoint must never become the production checkpoint")


def median_domain_target_f1(domain_target_f1: Sequence[MetricResult]) -> MetricResult:
    defined_values = sorted(result.value for result in domain_target_f1 if result.value is not None)
    if len(defined_values) == 0:
        return MetricResult(None, 0)
    return MetricResult(quantile_type7(defined_values, 0.5), len(defined_values))


def final_gate_predicates_pass(
    median_target_f1: MetricResult,
    minimum_target_f1: MetricResult,
    pooled_supported_macro_f1_drop: MetricResult,
    pooled_benign_far_increase: MetricResult,
    no_invariant_failure: bool,
    final_gate_config: FinalGateConfig,
) -> bool:
    if (
        median_target_f1.value is None
        or minimum_target_f1.value is None
        or pooled_supported_macro_f1_drop.value is None
        or pooled_benign_far_increase.value is None
    ):
        return False
    return (
        no_invariant_failure
        and median_target_f1.value >= final_gate_config.median_target_f1_minimum
        and minimum_target_f1.value >= final_gate_config.minimum_domain_target_f1
        and pooled_supported_macro_f1_drop.value
        <= final_gate_config.supported_macro_f1_drop_maximum
        and pooled_benign_far_increase.value
        <= final_gate_config.benign_false_alarm_rate_increase_maximum
    )


@dataclass(frozen=True)
class AdmissionArtifactContent:
    anchor_checkpoint_identity: ArtifactDigest
    source_commitment_identity: ArtifactDigest | None
    claim_identity: ArtifactDigest
    reproducer_assignment_order: tuple[NBaiotDomain, ...]
    reproduction_commitment_hashes: tuple[ArtifactDigest, ...]
    verifier_record: tuple[ArtifactDigest, ...] | VerificationOmissionMarker
    krum_configuration_identity: ArtifactDigest | None
    production_update_identity: ArtifactDigest
    final_gate_sample_manifest_identity: ArtifactDigest
    final_gate_metrics_identity: ArtifactDigest
    seed_bundle: SeedBundle
    semantic_cell_key: CanonicalToken
    cell_phase_identity: CanonicalToken
    upstream_dependency_fingerprints: tuple[ArtifactDigest, ...]
    producer_component_fingerprint: ArtifactDigest
    runtime_dependency_fingerprint: ArtifactDigest
    repository_commit: CanonicalToken
    dependency_lock_digest: ArtifactDigest
    environment_fingerprint: ArtifactDigest


def validate_admission_artifact_content(
    content: AdmissionArtifactContent,
    opening_mode: ClaimOpeningMode,
    is_plurality_active: bool,
) -> None:
    if (
        opening_mode is ClaimOpeningMode.PROPOSAL_ASSISTED
        and content.source_commitment_identity is None
    ):
        raise ValueError(
            "proposal-assisted admission artifact must record source commitment identity"
        )
    if is_plurality_active and content.krum_configuration_identity is None:
        raise ValueError(
            "plurality-path admission artifact must record Krum configuration identity"
        )
    if isinstance(content.verifier_record, tuple) and len(content.verifier_record) == 0:
        raise ValueError(
            "admission artifact must record verifier assignments/reports or an explicit "
            "External Verification Not Used marker, never an empty record"
        )
