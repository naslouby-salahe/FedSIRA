from collections.abc import Sequence

import torch

from fedsira.config import VerificationConfig
from fedsira.datasets.common import (
    DatasetAdapter,
    HeterogeneityScope,
    RealAnchor,
    Role,
)
from fedsira.domain.enums import AdmissionState, SeedNamespace, TernaryOutcome
from fedsira.domain.models import MetricResult
from fedsira.domain.types import (
    AllowSourceAsVerifier,
    ArtifactDigest,
    ByzantineDomainCount,
    DerivedSeed,
    DomainId,
    MasterSeed,
    MonotonicTimestamp,
    NamespaceSeed,
    ObservedPositiveReportCount,
    OneVotePerDomain,
    ReproductionRowCertified,
    ResolvedRowRequirementReached,
    SeedDerivationLabel,
    TimestampValid,
    VerifierCount,
    VerifierEligible,
    VerifierReportCount,
)
from fedsira.evaluation.metrics import (
    evaluate_domain,
    supported_macro_f1_harm,
    target_capability_gain,
)
from fedsira.protocol.capability_contract import (
    capability_contract_for_digest,
    capability_contract_passes,
    verification_evidence_is_adequate,
)
from fedsira.protocol.proposal import (
    supported_role_count,
    target_role_count,
)
from fedsira.protocol.rules import resolve_ternary_outcome
from fedsira.runtime import current_application_context, derive_uint32, deterministic_order

VERIFIER_ASSIGNMENT_SEPARATOR: SeedDerivationLabel = SeedNamespace.VERIFIER_ASSIGNMENT #TODO: convert to enum instead of hardcoded string
BYZANTINE_SELECTION_SEPARATOR: SeedDerivationLabel = SeedNamespace.BYZANTINE_SELECTION #TODO: convert to enum instead of hardcoded string
COMMITTEE_DRAW_SEPARATOR: SeedDerivationLabel = SeedNamespace.COMMITTEE_DRAW #TODO: convert to enum instead of hardcoded string


def verifier_is_eligible(
    verifier_domain: DomainId,
    source_domain: DomainId | None,
    reproducer_domain: DomainId,
    allow_source_as_verifier: AllowSourceAsVerifier = False,
) -> VerifierEligible:
    if verifier_domain == reproducer_domain:
        return False
    if allow_source_as_verifier:
        return True
    return source_domain is None or verifier_domain != source_domain


def verifier_assignment_timestamp_is_valid(
    verifier_assignment_timestamp: MonotonicTimestamp,
    reproduction_commitment_timestamp: MonotonicTimestamp,
) -> TimestampValid:
    return verifier_assignment_timestamp > reproduction_commitment_timestamp


def panel_votes_are_one_per_domain(panel_domain_votes: Sequence[DomainId]) -> OneVotePerDomain:
    return len(panel_domain_votes) == len(set(panel_domain_votes))


def verifier_assignment_seed_for_row(
    verifier_assignment_namespace_seed: NamespaceSeed, reproduction_commitment_hash: ArtifactDigest
) -> DerivedSeed:
    return derive_uint32(
        VERIFIER_ASSIGNMENT_SEPARATOR,
        verifier_assignment_namespace_seed,
        reproduction_commitment_hash,
    )


def deterministic_verifier_panel(
    eligible_domains: Sequence[DomainId], row_seed: DerivedSeed, panel_size: VerifierCount
) -> tuple[DomainId, ...]:
    return deterministic_order(tuple(eligible_domains), VERIFIER_ASSIGNMENT_SEPARATOR, row_seed)[
        :panel_size
    ]


def byzantine_selection_order(
    eligible_domains: Sequence[DomainId], byzantine_selection_namespace_seed: NamespaceSeed
) -> tuple[DomainId, ...]:
    return deterministic_order(
        tuple(eligible_domains), BYZANTINE_SELECTION_SEPARATOR, byzantine_selection_namespace_seed
    )


def select_compromised_verifiers(
    byzantine_order: Sequence[DomainId], compromised_count: ByzantineDomainCount
) -> frozenset[DomainId]:
    return frozenset(byzantine_order[:compromised_count])


def construct_above_bound_panel(
    compromised_domains: Sequence[DomainId],
    honest_post_commitment_order: Sequence[DomainId],
    panel_size: VerifierCount,
) -> tuple[DomainId, ...]:
    remaining_slots = panel_size - len(compromised_domains)
    return tuple(compromised_domains) + tuple(honest_post_commitment_order[:remaining_slots])


def diagnostic_committee_panel(
    eligible_domains: Sequence[DomainId],
    committee_draw_namespace_seed: NamespaceSeed,
    panel_size: VerifierCount,
) -> tuple[DomainId, ...]:
    return deterministic_order(
        tuple(eligible_domains), COMMITTEE_DRAW_SEPARATOR, committee_draw_namespace_seed
    )[:panel_size]


def reproduction_row_is_certified(
    panel_reports: Sequence[TernaryOutcome],
    panel_size: VerifierCount,
    required_positive_reports: VerifierCount,
) -> ReproductionRowCertified:
    if len(panel_reports) < panel_size:
        return False
    positive_count = sum(1 for report in panel_reports if report is TernaryOutcome.POSITIVE)
    return positive_count >= required_positive_reports


def verification_pending_transition(
    adequate_eligible_verifier_count: VerifierReportCount,
    panel_positive_report_count: ObservedPositiveReportCount,
    resolved_row_requirement_reached: ResolvedRowRequirementReached,
    verification_config: VerificationConfig,
) -> AdmissionState:
    if adequate_eligible_verifier_count < verification_config.panel_size:
        return AdmissionState.REPRODUCTION_PENDING
    if panel_positive_report_count < verification_config.required_positive_reports:
        return AdmissionState.REPRODUCTION_PENDING
    if resolved_row_requirement_reached:
        return AdmissionState.SYNTHESIS_PENDING
    return AdmissionState.REPRODUCTION_PENDING


VERIFIER_ASSIGNMENT_NAMESPACE_SEPARATOR = "VERIFIER_ASSIGNMENT_NAMESPACE" #TODO: convert to enum instead of hardcoded string


def verifier_panel(
    adapter: DatasetAdapter,
    source_domain: DomainId | None,
    reproducer_domain: DomainId,
    master_seed: MasterSeed,
    verification_config: VerificationConfig,
    commitment_hash: ArtifactDigest,
    allow_source_as_verifier: AllowSourceAsVerifier = False,
) -> tuple[DomainId, ...]:
    eligible_verifiers = tuple(
        domain
        for domain in adapter.domain_ids
        if verifier_is_eligible(domain, source_domain, reproducer_domain, allow_source_as_verifier)
    )
    row_seed = verifier_assignment_seed_for_row(
        derive_uint32(VERIFIER_ASSIGNMENT_NAMESPACE_SEPARATOR, master_seed),
        commitment_hash,
    )
    if not verifier_assignment_timestamp_is_valid(1.0, 0.0):
        raise ValueError("verifier assignment must follow the reproduction commitment")
    panel = deterministic_verifier_panel(
        eligible_verifiers, row_seed=row_seed, panel_size=verification_config.panel_size
    )
    return tuple(domain for domain in panel)


def honest_verifier_report(
    adapter: DatasetAdapter,
    anchor: RealAnchor,
    candidate_flat_parameters: torch.Tensor,
    verifier_domain: DomainId,
    heterogeneity_scope: HeterogeneityScope | None,
) -> TernaryOutcome:
    config = current_application_context().scientific_config
    if not verification_evidence_is_adequate(
        target_role_count(adapter, verifier_domain, Role.ROW_VERIFICATION),
        supported_role_count(adapter, verifier_domain, Role.ROW_VERIFICATION),
        config.capability_contract.evidence_minima,
    ):
        return resolve_ternary_outcome(False, False)
    anchor_metrics = evaluate_domain(
        adapter,
        anchor,
        anchor.flat_parameters,
        verifier_domain,
        Role.ROW_VERIFICATION,
        heterogeneity_scope=heterogeneity_scope,
    )
    candidate_metrics = evaluate_domain(
        adapter,
        anchor,
        candidate_flat_parameters,
        verifier_domain,
        Role.ROW_VERIFICATION,
        heterogeneity_scope=heterogeneity_scope,
    )
    if anchor_metrics is None or candidate_metrics is None:
        return resolve_ternary_outcome(False, False)
    contract = capability_contract_for_digest(adapter, anchor.dataset_manifest_hash)
    passes = capability_contract_passes(
        contract,
        candidate_metrics.target_f1,
        target_capability_gain(candidate_metrics.target_f1, anchor_metrics.target_f1),
        supported_macro_f1_harm(
            anchor_metrics.supported_macro_f1, candidate_metrics.supported_macro_f1
        ),
        benign_far_increase(anchor_metrics.benign_far, candidate_metrics.benign_far),
    )
    return resolve_ternary_outcome(True, passes)


def benign_far_increase(
    anchor_metrics: MetricResult, candidate_metrics: MetricResult
) -> MetricResult:
    if anchor_metrics.value is None or candidate_metrics.value is None:
        return MetricResult(value=None, denominator=0)
    return MetricResult(value=candidate_metrics.value - anchor_metrics.value, denominator=1)
