from __future__ import annotations

from collections import OrderedDict
from collections.abc import Sequence
from pathlib import Path

import torch

from fedsira.config import VerificationConfig
from fedsira.datasets.common import Role, role_hash_token
from fedsira.datasets.nbaiot.evaluation.domain import evaluate_domain, non_source_domains
from fedsira.datasets.nbaiot.evaluation.report_summary import (
    RealReportSummary,
    compute_real_report_summary,
)
from fedsira.datasets.nbaiot.learning.post_reference_training import (
    certified_domain_delta_committee,
    train_domain_reproduction_delta,
    train_source_candidate_delta,
)
from fedsira.datasets.nbaiot.scenarios import reproducer_order
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_CLASS_ORDER,
    NBAIOT_DOMAIN_ORDER,
    NBaiotClass,
    NBaiotDomain,
)
from fedsira.datasets.nbaiot.workflow import (
    BackdoorScope,
    HeterogeneityScope,
    RealAnchor,
    load_prepared_rows,
)
from fedsira.domain.enums import (
    AdmissionOpeningMode,
    AdmissionState,
    CoreMethodIdentity,
    TernaryOutcome,
)
from fedsira.domain.models import (
    CommunicationMessageType,
    MetricResult,
)
from fedsira.domain.types import (
    AdequateFinalGateDomainCount,
    AllowSourceAsVerifier,
    ArtifactDigest,
    BooleanValue,
    ByzantineDomainCount,
    CapabilityContractSatisfied,
    CapabilityIdentity,
    CommunicationMessageCount,
    CompromisedReproducerCount,
    ConditionName,
    ExampleCount,
    FrozenDomainModel,
    MasterSeed,
    RequiredReproductionRowCount,
)
from fedsira.evaluation.metrics import supported_macro_f1_harm, target_capability_gain
from fedsira.evaluation.summaries import (
    equal_weight_domain_mean,
    worst_domain_target_f1,
)
from fedsira.experiments.collapse import ResolvedCore
from fedsira.experiments.definitions import (
    MECHANISM_ABLATION_NAME,
    AblationVariant,
    ExternalVerificationCondition,
    OpeningMode,
    PluralityCondition,
    ProposalEpisode,
    ReproducerCondition,
    SecondaryScenario,
    VerifierCondition,
)
from fedsira.experiments.planning import ScientificCell
from fedsira.experiments.prerequisites import PreparedEvidenceCounts
from fedsira.protocol.admission import (
    apply_production_update,
    final_gate_predicates_pass,
    median_domain_target_f1,
    resolve_production_update,
    validate_admission_requires_final_gate,
    validate_production_checkpoint_excludes_source,
)
from fedsira.protocol.attacks.source import (
    scale_model_replacement_delta,
)
from fedsira.protocol.baselines.registry import (
    BaselineIdentity,
    first_eligible_non_source_reproducer,
    single_fresh_verifier_domain,
    single_fresh_verifier_outcome,
)
from fedsira.protocol.baselines.robust_aggregation import coordinate_wise_median_synthesis
from fedsira.protocol.capability_contract import (
    CapabilityContract,
    build_capability_contract,
    capability_contract_passes,
    compute_capability_identity,
    reproduction_evidence_is_adequate,
    verification_evidence_is_adequate,
)
from fedsira.protocol.proposal import (
    select_source_domain,
    source_selection_order,
)
from fedsira.protocol.reproduction import (
    ReproductionAttempt,
    compute_reproduction_commitment_hash,
    consumed_domains,
    handle_adequate_domain_trained,
    handle_inadequate_domain,
    handle_no_adequate_unconsumed_domain,
    next_reproducer_domain,
    validate_commitment_exists_before_verifier_assignment,
    validate_reproduction_start_checkpoint,
    validate_reproduction_starts_from_anchor,
)
from fedsira.protocol.specification import (
    reproduction_update_vector,
    validate_exactly_one_source_domain,
)
from fedsira.protocol.state_machine import resolve_ternary_outcome
from fedsira.protocol.synthesis import (
    CertifiedReproductionRow,
    select_krum_update,
    synthesis_pending_transition,
)
from fedsira.protocol.verification import (
    deterministic_verifier_panel,
    verifier_assignment_seed_for_row,
    verifier_assignment_timestamp_is_valid,
    verifier_is_eligible,
)
from fedsira.runtime import (
    current_application_context,
    derive_uint32,
)

SOURCE_SELECTION_SEED_SEPARATOR = "SOURCE_SELECTION_SEED"
COMMITMENT_HASH_SEPARATOR = "COMMITMENT_HASH"
VERIFIER_ASSIGNMENT_NAMESPACE_SEPARATOR = "VERIFIER_ASSIGNMENT_NAMESPACE"
BYZANTINE_VERIFIER_SELECTION_SEPARATOR = "BYZANTINE_VERIFIER_SELECTION"
ANCHOR_CHECKPOINT_IDENTITY = "anchor-checkpoint"
SOURCE_CHECKPOINT_IDENTITY = "source-checkpoint"


class OpeningIdentity(FrozenDomainModel):
    capability_identity: CapabilityIdentity
    contract_passes: CapabilityContractSatisfied


def opening_mode_for_cell(
    cell: ScientificCell, resolved_core: ResolvedCore | None = None
) -> AdmissionOpeningMode:
    if cell.method == RESOLVED_FEDSIRA_CORE_METHOD and resolved_core is not None:
        return resolved_core.opening_mode
    if cell.method == OpeningMode.PROPOSAL_ASSISTED:
        return AdmissionOpeningMode.PROPOSAL_ASSISTED
    return AdmissionOpeningMode.CANDIDATE_FREE


def _target_role_count(prepared_root: Path, domain: NBaiotDomain, role: Role) -> ExampleCount:
    rows = load_prepared_rows(prepared_root, domain, NBaiotClass.GAFGYT_COMBO, role)
    return 0 if rows is None else rows.row_count


def first_target_sample_id(
    prepared_root: Path, domain: NBaiotDomain, role: Role
) -> ArtifactDigest | None:
    rows = load_prepared_rows(prepared_root, domain, NBaiotClass.GAFGYT_COMBO, role)
    if rows is None or not rows.sample_ids:
        return None
    return rows.sample_ids[0]


def _supported_role_count(prepared_root: Path, domain: NBaiotDomain, role: Role) -> ExampleCount:
    total: ExampleCount = 0
    for class_id in NBAIOT_CLASS_ORDER:
        if class_id is NBaiotClass.GAFGYT_COMBO:
            continue
        rows = load_prepared_rows(prepared_root, domain, class_id, role)
        if rows is not None:
            total += rows.row_count
    return total


def _domains_with_class(
    prepared_root: Path, class_id: NBaiotClass, role: Role
) -> frozenset[NBaiotDomain]:
    return frozenset(
        domain
        for domain in NBAIOT_DOMAIN_ORDER
        if load_prepared_rows(prepared_root, domain, class_id, role) is not None
    )


def _capability_contract_for_digest(dataset_manifest_hash: ArtifactDigest) -> CapabilityContract:
    config = current_application_context().scientific_config
    return build_capability_contract(
        dataset_manifest_hash,
        role_hash_token(Role.POST_REFERENCE_REPLAY),
        config.datasets.primary.name,
        len(NBAIOT_DOMAIN_ORDER),
        dataset_manifest_hash,
        NBaiotClass.GAFGYT_COMBO,
        len(NBAIOT_CLASS_ORDER) - 1,
        config.capability_contract,
    )


def opening_identity(dataset_manifest_hash: ArtifactDigest) -> OpeningIdentity:
    contract = _capability_contract_for_digest(dataset_manifest_hash)
    return OpeningIdentity(
        capability_identity=compute_capability_identity(contract),
        contract_passes=False,
    )


def _source_requires_attack_carrier(cell: ScientificCell) -> BooleanValue:
    return cell.condition == ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT


def _source_domain_for_cell(
    cell: ScientificCell, prepared_root: Path | None = None
) -> NBaiotDomain | None:
    source_order = source_selection_order(
        NBAIOT_DOMAIN_ORDER, derive_uint32(SOURCE_SELECTION_SEED_SEPARATOR, cell.master_seed)
    )
    validate_exactly_one_source_domain((source_order[0],))
    if prepared_root is None:
        domains_with_target: frozenset[NBaiotDomain] = frozenset(NBAIOT_DOMAIN_ORDER)
        domains_with_carrier: frozenset[NBaiotDomain] = frozenset()
        requires_carrier = False
    else:
        domains_with_target = _domains_with_class(
            prepared_root, NBaiotClass.GAFGYT_COMBO, Role.SOURCE_PROPOSAL
        ) | _domains_with_class(prepared_root, NBaiotClass.GAFGYT_COMBO, Role.REPRODUCTION)
        domains_with_carrier = _domains_with_class(
            prepared_root, NBaiotClass.GAFGYT_UDP, Role.POST_REFERENCE_REPLAY
        )
        requires_carrier = _source_requires_attack_carrier(cell)
    selected = select_source_domain(
        source_order,
        domains_with_target,
        requires_attack_carrier=requires_carrier,
        domains_with_attack_carrier=domains_with_carrier,
    )
    return NBaiotDomain(selected) if selected is not None else None


def _reproducer_order(cell: ScientificCell) -> tuple[NBaiotDomain, ...]:
    return reproducer_order(
        NBAIOT_DOMAIN_ORDER, derive_uint32("REPRODUCER_ORDER_SEED", cell.master_seed)
    )


def row_requirement(
    cell: ScientificCell, resolved_core: ResolvedCore | None = None
) -> RequiredReproductionRowCount:
    config = current_application_context().scientific_config
    if cell.method == RESOLVED_FEDSIRA_CORE_METHOD and resolved_core is not None:
        return config.protocol.synthesis.committee_size if resolved_core.plurality_survives else 1
    if cell.method in (
        BaselineIdentity.ONE_INDEPENDENT_RETRAIN,
        BaselineIdentity.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN,
    ) or (
        cell.experiment == MECHANISM_ABLATION_NAME
        and cell.method == AblationVariant.ONE_INDEPENDENT_REPRODUCTION
    ):
        return 1
    if cell.method == BaselineIdentity.THREE_ROW_COORDINATE_MEDIAN_ALTERNATIVE or (
        cell.experiment == MECHANISM_ABLATION_NAME
        and cell.method == AblationVariant.GENERIC_THREE_ROW_THRESHOLD
    ):
        return config.baselines.three_row_coordinate_median.row_count
    return config.protocol.synthesis.committee_size


def _commitment_digest(
    reproducer_domain: NBaiotDomain,
    master_seed: MasterSeed,
    capability_identity: ArtifactDigest,
    reproduced_flat_parameters: torch.Tensor,
) -> ArtifactDigest:
    return compute_reproduction_commitment_hash(
        reproducer_domain,
        capability_identity,
        derive_uint32(COMMITMENT_HASH_SEPARATOR, master_seed),
        reproduced_flat_parameters,
    )


def _verifier_panel(
    source_domain: NBaiotDomain | None,
    reproducer_domain: NBaiotDomain,
    master_seed: MasterSeed,
    verification_config: VerificationConfig,
    commitment_hash: ArtifactDigest,
    allow_source_as_verifier: AllowSourceAsVerifier = False,
) -> tuple[NBaiotDomain, ...]:
    eligible_verifiers = tuple(
        domain
        for domain in NBAIOT_DOMAIN_ORDER
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
    return tuple(NBaiotDomain(domain) for domain in panel)


def _domain_is_reproduction_adequate(prepared_root: Path, domain: NBaiotDomain) -> BooleanValue:
    config = current_application_context().scientific_config
    return reproduction_evidence_is_adequate(
        _target_role_count(prepared_root, domain, Role.REPRODUCTION),
        _supported_role_count(prepared_root, domain, Role.POST_REFERENCE_REPLAY),
        config.capability_contract.evidence_minima,
    )


def _benign_far_increase(
    anchor_metrics: MetricResult, candidate_metrics: MetricResult
) -> MetricResult:
    if anchor_metrics.value is None or candidate_metrics.value is None:
        return MetricResult(value=None, denominator=0)
    return MetricResult(value=candidate_metrics.value - anchor_metrics.value, denominator=1)


def _honest_verifier_report(
    prepared_root: Path,
    anchor: RealAnchor,
    candidate_flat_parameters: torch.Tensor,
    verifier_domain: NBaiotDomain,
    heterogeneity_scope: HeterogeneityScope | None,
) -> TernaryOutcome:
    config = current_application_context().scientific_config
    if not verification_evidence_is_adequate(
        _target_role_count(prepared_root, verifier_domain, Role.ROW_VERIFICATION),
        _supported_role_count(prepared_root, verifier_domain, Role.ROW_VERIFICATION),
        config.capability_contract.evidence_minima,
    ):
        return resolve_ternary_outcome(False, False)
    anchor_metrics = evaluate_domain(
        prepared_root,
        anchor,
        anchor.flat_parameters,
        verifier_domain,
        Role.ROW_VERIFICATION,
        heterogeneity_scope=heterogeneity_scope,
    )
    candidate_metrics = evaluate_domain(
        prepared_root,
        anchor,
        candidate_flat_parameters,
        verifier_domain,
        Role.ROW_VERIFICATION,
        heterogeneity_scope=heterogeneity_scope,
    )
    if anchor_metrics is None or candidate_metrics is None:
        return resolve_ternary_outcome(False, False)
    contract = _capability_contract_for_digest(anchor.dataset_manifest_hash)
    passes = capability_contract_passes(
        contract,
        candidate_metrics.target_f1,
        target_capability_gain(candidate_metrics.target_f1, anchor_metrics.target_f1),
        supported_macro_f1_harm(
            anchor_metrics.supported_macro_f1, candidate_metrics.supported_macro_f1
        ),
        _benign_far_increase(anchor_metrics.benign_far, candidate_metrics.benign_far),
    )
    return resolve_ternary_outcome(True, passes)


def _train_reproduction_update(
    prepared_root: Path,
    cell: ScientificCell,
    anchor: RealAnchor,
    domain: NBaiotDomain,
    source_delta: torch.Tensor | None,
    compromised_reproducers: frozenset[NBaiotDomain],
    heterogeneity_scope: HeterogeneityScope | None,
    backdoor_scope: BackdoorScope | None,
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    validate_reproduction_starts_from_anchor(anchor.flat_parameters, anchor.flat_parameters)
    if domain not in compromised_reproducers:
        return train_domain_reproduction_delta(
            prepared_root,
            cell.master_seed,
            anchor,
            domain,
            heterogeneity_scope=heterogeneity_scope,
        )
    condition = cell.condition
    if condition in (
        ReproducerCondition.ONE_SOURCE_COPY,
        ReproducerCondition.TWO_SOURCE_COPIES,
        PluralityCondition.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER,
        ExternalVerificationCondition.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER,
        SecondaryScenario.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER,
    ):
        if source_delta is None:
            return None
        return reproduction_update_vector(
            anchor.flat_parameters, anchor.flat_parameters + source_delta
        )
    trained = train_domain_reproduction_delta(
        prepared_root,
        cell.master_seed,
        anchor,
        domain,
        heterogeneity_scope=heterogeneity_scope,
        backdoor_scope=backdoor_scope,
    )
    if trained is None:
        return None
    if condition in (
        ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR,
        ReproducerCondition.TWO_MODEL_REPLACEMENT_BACKDOORS,
    ):
        return scale_model_replacement_delta(
            trained,
            config.attacks_and_boundaries.byzantine_reproduction.model_replacement.delta_scale,
        )
    return trained


def reproduction_progression(
    cell: ScientificCell,
    evidence: PreparedEvidenceCounts,
    external_verification_active: BooleanValue,
    row_requirement: RequiredReproductionRowCount,
    compromised_reproducers: frozenset[NBaiotDomain],
    prepared_root: Path,
    anchor: RealAnchor | None,
    include_source_as_first_reproducer: BooleanValue = False,
    heterogeneity_scope: HeterogeneityScope | None = None,
    backdoor_scope: BackdoorScope | None = None,
    source_delta: torch.Tensor | None = None,
) -> tuple[
    AdmissionState,
    tuple[ReproductionAttempt, ...],
    tuple[ArtifactDigest, ...],
    OrderedDict[NBaiotDomain, torch.Tensor],
]:
    del evidence
    if anchor is None:
        return (AdmissionState.DORMANT, (), (), OrderedDict())
    reproducer_order = _reproducer_order(cell)
    source_domain = _source_domain_for_cell(cell, prepared_root)
    validate_reproduction_start_checkpoint(
        ANCHOR_CHECKPOINT_IDENTITY, frozenset({SOURCE_CHECKPOINT_IDENTITY})
    )
    validate_reproduction_starts_from_anchor(anchor.flat_parameters, anchor.flat_parameters)
    capability_identity = compute_capability_identity(
        _capability_contract_for_digest(anchor.dataset_manifest_hash)
    )
    adequate_domains = frozenset(
        domain
        for domain in NBAIOT_DOMAIN_ORDER
        if domain != source_domain and _domain_is_reproduction_adequate(prepared_root, domain)
    )
    attempts: list[ReproductionAttempt] = []
    commitment_hashes: list[ArtifactDigest] = []
    updates: OrderedDict[NBaiotDomain, torch.Tensor] = OrderedDict()
    certified_count = 0
    state = AdmissionState.REPRODUCTION_PENDING
    if (
        include_source_as_first_reproducer
        and source_domain is not None
        and source_delta is not None
    ):
        reproduced = anchor.flat_parameters + source_delta
        commitment_hash = _commitment_digest(
            source_domain, cell.master_seed, capability_identity, reproduced
        )
        commitment_hashes.append(commitment_hash)
        validate_commitment_exists_before_verifier_assignment(commitment_hash)
        updates[source_domain] = source_delta
        attempts.append(
            ReproductionAttempt(domain=source_domain, was_trained=True, is_certified=True)
        )
        certified_count += 1
        state = handle_adequate_domain_trained(
            external_verification_active, certified_count >= row_requirement
        )
        if state is AdmissionState.SYNTHESIS_PENDING:
            return (state, tuple(attempts), tuple(commitment_hashes), updates)
    for _row_index in range(len(reproducer_order)):
        next_domain = next_reproducer_domain(
            reproducer_order, consumed_domains(attempts), adequate_domains
        )
        if next_domain is None:
            state = handle_no_adequate_unconsumed_domain(certified_count >= row_requirement)
            break
        domain = NBaiotDomain(next_domain)
        update = _train_reproduction_update(
            prepared_root,
            cell,
            anchor,
            domain,
            source_delta,
            compromised_reproducers,
            heterogeneity_scope,
            backdoor_scope,
        )
        if update is None:
            state = handle_inadequate_domain()
            continue
        reproduced = anchor.flat_parameters + update
        commitment_hash = _commitment_digest(
            domain, cell.master_seed, capability_identity, reproduced
        )
        commitment_hashes.append(commitment_hash)
        validate_commitment_exists_before_verifier_assignment(commitment_hash)
        updates[domain] = update
        is_certified = domain not in compromised_reproducers or not external_verification_active
        attempts.append(
            ReproductionAttempt(domain=domain, was_trained=True, is_certified=is_certified)
        )
        if is_certified:
            certified_count += 1
        state = handle_adequate_domain_trained(
            external_verification_active, certified_count >= row_requirement
        )
        if state is AdmissionState.SYNTHESIS_PENDING:
            break
    return (state, tuple(attempts), tuple(commitment_hashes), updates)


def single_verifier_progression(
    cell: ScientificCell,
    source_domain: NBaiotDomain | None,
    prepared_root: Path,
    anchor: RealAnchor | None,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> tuple[
    AdmissionState,
    tuple[ReproductionAttempt, ...],
    tuple[ArtifactDigest, ...],
    OrderedDict[NBaiotDomain, torch.Tensor],
]:
    if anchor is None:
        return (AdmissionState.DORMANT, (), (), OrderedDict())
    config = current_application_context().scientific_config
    reproducer_order = _reproducer_order(cell)
    adequate_domains = frozenset(
        domain
        for domain in NBAIOT_DOMAIN_ORDER
        if domain != source_domain and _domain_is_reproduction_adequate(prepared_root, domain)
    )
    capability_identity = compute_capability_identity(
        _capability_contract_for_digest(anchor.dataset_manifest_hash)
    )
    consumed: set[NBaiotDomain] = set()
    while True:
        candidate = first_eligible_non_source_reproducer(
            reproducer_order, adequate_domains - frozenset(consumed)
        )
        if candidate is None:
            return (AdmissionState.DORMANT, (), (), OrderedDict())
        next_domain = NBaiotDomain(candidate)
        consumed.add(next_domain)
        update = train_domain_reproduction_delta(
            prepared_root,
            cell.master_seed,
            anchor,
            next_domain,
            heterogeneity_scope=heterogeneity_scope,
        )
        if update is None:
            continue
        reproduced = anchor.flat_parameters + update
        commitment_hash = _commitment_digest(
            next_domain, cell.master_seed, capability_identity, reproduced
        )
        validate_commitment_exists_before_verifier_assignment(commitment_hash)
        panel_order = _verifier_panel(
            source_domain,
            next_domain,
            cell.master_seed,
            config.protocol.verification,
            commitment_hash,
        )
        verifier_domain = single_fresh_verifier_domain(
            panel_order, frozenset(), frozenset(panel_order)
        )
        if verifier_domain is None:
            continue
        report = _honest_verifier_report(
            prepared_root,
            anchor,
            reproduced,
            NBaiotDomain(verifier_domain),
            heterogeneity_scope,
        )
        verifier_outcome = single_fresh_verifier_outcome(verifier_domain, report)
        if verifier_outcome is AdmissionState.ADMITTED:
            attempt = ReproductionAttempt(domain=next_domain, was_trained=True, is_certified=True)
            return (
                AdmissionState.SYNTHESIS_PENDING,
                (attempt,),
                (commitment_hash,),
                OrderedDict(((next_domain, update),)),
            )
        if verifier_outcome is AdmissionState.REJECTED:
            continue


def _real_final_gate_metrics(
    prepared_root: Path,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
    production_checkpoint: torch.Tensor,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> tuple[AdequateFinalGateDomainCount, MetricResult, MetricResult, MetricResult, MetricResult]:
    candidate_domains = non_source_domains(source_domain)
    adequate_domains = tuple(
        domain
        for domain in candidate_domains
        if evaluate_domain(
            prepared_root,
            anchor,
            anchor.flat_parameters,
            domain,
            Role.FINAL_GATE,
            heterogeneity_scope=heterogeneity_scope,
        )
        is not None
    )
    if not adequate_domains:
        return (
            0,
            MetricResult(value=None, denominator=0),
            MetricResult(value=None, denominator=0),
            MetricResult(value=None, denominator=0),
            MetricResult(value=None, denominator=0),
        )
    target_f1_values: list[MetricResult] = []
    supported_f1_harms: list[MetricResult] = []
    benign_far_increases: list[MetricResult] = []
    for domain in adequate_domains:
        anchor_metrics = evaluate_domain(
            prepared_root,
            anchor,
            anchor.flat_parameters,
            domain,
            Role.FINAL_GATE,
            heterogeneity_scope=heterogeneity_scope,
        )
        production_metrics = evaluate_domain(
            prepared_root,
            anchor,
            production_checkpoint,
            domain,
            Role.FINAL_GATE,
            heterogeneity_scope=heterogeneity_scope,
        )
        if anchor_metrics is None or production_metrics is None:
            continue
        target_f1_values.append(production_metrics.target_f1)
        supported_f1_harms.append(
            supported_macro_f1_harm(
                anchor_metrics.supported_macro_f1, production_metrics.supported_macro_f1
            )
        )
        if (
            anchor_metrics.benign_far.value is not None
            and production_metrics.benign_far.value is not None
        ):
            benign_far_increases.append(
                MetricResult(
                    value=production_metrics.benign_far.value - anchor_metrics.benign_far.value,
                    denominator=1,
                )
            )
        else:
            benign_far_increases.append(MetricResult(value=None, denominator=0))
    return (
        len(adequate_domains),
        median_domain_target_f1(target_f1_values),
        worst_domain_target_f1(tuple(target_f1_values)),
        equal_weight_domain_mean(tuple(supported_f1_harms), 1),
        equal_weight_domain_mean(tuple(benign_far_increases), 1),
    )


def final_gate_decision(
    evidence: PreparedEvidenceCounts,
    source_domain: NBaiotDomain | None,
    reproducer_order: Sequence[NBaiotDomain],
    is_plurality_active: BooleanValue,
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor | None,
    coordinate_median_active: BooleanValue,
    no_final_synthesis_gate_active: BooleanValue,
    use_source_delta_for_source_domain: BooleanValue,
    force_first_row_to_source_delta: BooleanValue,
    heterogeneity_scope: HeterogeneityScope | None = None,
    precomputed_updates: OrderedDict[NBaiotDomain, torch.Tensor] | None = None,
) -> tuple[AdmissionState, RealReportSummary | None]:
    if anchor is None:
        return (AdmissionState.DORMANT, None)
    config = current_application_context().scientific_config
    base_flat_parameters = anchor.flat_parameters
    committee_deltas: OrderedDict[NBaiotDomain, torch.Tensor] = (
        OrderedDict(precomputed_updates)
        if precomputed_updates is not None
        else certified_domain_delta_committee(
            prepared_root,
            master_seed,
            anchor,
            reproducer_order,
            heterogeneity_scope=heterogeneity_scope,
        )
    )
    if use_source_delta_for_source_domain and source_domain is not None:
        source_delta = train_source_candidate_delta(
            prepared_root, master_seed, anchor, source_domain
        )
        if source_delta is not None:
            committee_deltas[source_domain] = source_delta
    if force_first_row_to_source_delta and source_domain is not None and reproducer_order:
        source_delta = train_source_candidate_delta(
            prepared_root, master_seed, anchor, source_domain
        )
        if source_delta is not None:
            committee_deltas[reproducer_order[0]] = source_delta
    available_updates = tuple(
        committee_deltas[domain] for domain in reproducer_order if domain in committee_deltas
    )
    if coordinate_median_active:
        if not available_updates:
            return (AdmissionState.DORMANT, None)
        production_update = coordinate_wise_median_synthesis(available_updates)
        production_checkpoint = apply_production_update(base_flat_parameters, production_update)
        return _final_gate_decision_from_production_checkpoint(
            evidence,
            source_domain,
            prepared_root,
            anchor,
            production_checkpoint,
            no_final_synthesis_gate_active,
            heterogeneity_scope=heterogeneity_scope,
        )
    krum_selected_update: torch.Tensor | None = None
    if is_plurality_active:
        committee = tuple(
            CertifiedReproductionRow(
                reproducer_domain=domain,
                update_vector=committee_deltas[domain],
            )
            for domain in reproducer_order
            if domain in committee_deltas
        )
        if not committee:
            return (AdmissionState.DORMANT, None)
        krum_selected_update = select_krum_update(
            committee, config.protocol.synthesis.maximum_byzantine_reproduction_rows
        ).update_vector
    first_domain = next((domain for domain in reproducer_order if domain in committee_deltas), None)
    if first_domain is None and not is_plurality_active:
        return (AdmissionState.DORMANT, None)
    single_reproduction_update = (
        committee_deltas[first_domain] if first_domain is not None else None
    )
    production_update = resolve_production_update(
        is_plurality_active, krum_selected_update, single_reproduction_update
    )
    production_checkpoint = apply_production_update(base_flat_parameters, production_update)
    return _final_gate_decision_from_production_checkpoint(
        evidence,
        source_domain,
        prepared_root,
        anchor,
        production_checkpoint,
        no_final_synthesis_gate_active,
        heterogeneity_scope=heterogeneity_scope,
    )


def _final_gate_decision_from_production_checkpoint(
    evidence: PreparedEvidenceCounts,
    source_domain: NBaiotDomain | None,
    prepared_root: Path,
    anchor: RealAnchor,
    production_checkpoint: torch.Tensor,
    no_final_synthesis_gate_active: BooleanValue,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> tuple[AdmissionState, RealReportSummary | None]:
    config = current_application_context().scientific_config
    (
        adequate_final_gate_domain_count,
        median_target_f1,
        minimum_target_f1,
        pooled_supported_macro_f1_drop,
        pooled_benign_far_increase,
    ) = _real_final_gate_metrics(
        prepared_root,
        anchor,
        source_domain,
        production_checkpoint,
        heterogeneity_scope=heterogeneity_scope,
    )
    predicates_pass = final_gate_predicates_pass(
        median_target_f1,
        minimum_target_f1,
        pooled_supported_macro_f1_drop,
        pooled_benign_far_increase,
        True,
        config.protocol.final_gate,
    )
    final_gate_state = (
        AdmissionState.ADMITTED
        if no_final_synthesis_gate_active
        else synthesis_pending_transition(
            adequate_final_gate_domain_count=adequate_final_gate_domain_count,
            final_gate_predicates_pass=predicates_pass,
            final_gate_config=config.protocol.final_gate,
        )
    )
    real_report_summary = compute_real_report_summary(
        prepared_root, anchor, source_domain, production_checkpoint
    )
    if final_gate_state is not AdmissionState.ADMITTED:
        return (final_gate_state, real_report_summary)
    validate_production_checkpoint_excludes_source(production_checkpoint, None)
    validate_admission_requires_final_gate(AdmissionState.ADMITTED, True)
    return (AdmissionState.ADMITTED, real_report_summary)


def compromised_reproducer_count(condition: ConditionName) -> CompromisedReproducerCount:
    if condition in (
        ReproducerCondition.ONE_SOURCE_COPY,
        ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR,
        ReproducerCondition.ONE_VERIFIER_AWARE_BACKDOOR,
    ):
        return 1
    if condition in (
        ReproducerCondition.TWO_SOURCE_COPIES,
        ReproducerCondition.TWO_MODEL_REPLACEMENT_BACKDOORS,
        ReproducerCondition.TWO_VERIFIER_AWARE_BACKDOORS,
    ):
        return 2
    return 0


def compromised_verifier_count(condition: ConditionName) -> ByzantineDomainCount:
    if condition in (
        VerifierCondition.ONE_FALSE_POSITIVE,
        VerifierCondition.ONE_FALSE_NEGATIVE,
    ):
        return 1
    if condition in (
        VerifierCondition.TWO_FALSE_POSITIVES,
        VerifierCondition.TWO_FALSE_NEGATIVES,
    ):
        return 2
    return 0


RESOLVED_FEDSIRA_CORE_METHOD = CoreMethodIdentity.RESOLVED_FEDSIRA_CORE


def efficiency_message_counts() -> (
    tuple[
        tuple[CommunicationMessageType, CommunicationMessageCount],
        ...,
    ]
):
    return (
        (CommunicationMessageType.SOURCE_COMMITMENT, 1),
        (CommunicationMessageType.MODEL_DISTRIBUTION, 8),
        (CommunicationMessageType.UPDATE_SUBMISSION, 8),
        (CommunicationMessageType.CAPABILITY_CONTRACT, 1),
        (CommunicationMessageType.REVIEW_ASSIGNMENT, 3),
        (CommunicationMessageType.REVIEW_REPORT, 3),
        (CommunicationMessageType.VERIFIER_ASSIGNMENT, 5),
        (CommunicationMessageType.VERIFIER_REPORT, 5),
        (CommunicationMessageType.FINAL_GATE_ASSIGNMENT, 6),
        (CommunicationMessageType.FINAL_GATE_REPORT, 6),
        (CommunicationMessageType.DECISION, 1),
    )
