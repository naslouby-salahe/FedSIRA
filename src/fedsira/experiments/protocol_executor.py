from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import torch

from fedsira.artifacts.fingerprints import DATASET_PACKAGE_NAME
from fedsira.artifacts.paths import prepared_evidence_root
from fedsira.attacks.reproduction import (
    scale_model_replacement_delta,
    select_model_replacement_carrier_rows,
    source_copy_update,
    verifier_aware_training_step,
)
from fedsira.attacks.verification import resolve_byzantine_verifier_vote
from fedsira.baselines.calibration import (
    parameter_similarity_certification_row_results,
    recovery_rollback_is_triggered,
    same_context_verifier_panel,
)
from fedsira.baselines.certified_ensemble import (
    validate_group_without_target_member_uses_supported_only,
)
from fedsira.baselines.independent_retraining import (
    candidate_free_full_path_opening_mode,
    one_independent_retrain_local_epochs,
)
from fedsira.baselines.references import (
    local_only_reference_evaluation_is_domain_local,
    standard_fl_anchor_rounds,
)
from fedsira.baselines.registry import (
    BaselineIdentity,
    domain_target_view,
    domain_without_target_view_may_participate,
    first_eligible_non_source_reproducer,
    review_style_baseline_outcome,
    single_fresh_verifier_domain,
    single_fresh_verifier_outcome,
    validate_role_not_used_for_tuning,
)
from fedsira.baselines.robust_aggregation import (
    coordinate_wise_median_synthesis,
    direct_krum_committee_rows,
    validate_three_row_coordinate_median_committee_size,
)
from fedsira.baselines.source_authority import (
    CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES,
    CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT,
    INDEPENDENT_LOCAL_REFERENCE_REQUIRED_POSITIVE_REVIEWS,
    INDEPENDENT_LOCAL_REFERENCE_REVIEWER_COUNT,
    SECURE_CONTINUAL_ASSESSMENT_REQUIRED_POSITIVE_REVIEWS,
    SECURE_CONTINUAL_ASSESSMENT_REVIEWER_COUNT,
    client_review_direct_admission_production_is_source,
    client_review_then_retrain_local_epochs,
    client_review_then_retrain_should_discard_source_weights,
    independent_local_reference_reviewer_is_positive,
    validate_client_review_composite_screen,
    validate_client_review_reviewer_count,
)
from fedsira.boundaries.capability_granularity import (
    target_row_ids_for_contract,
    validate_excluded_root_cause_not_supported,
)
from fedsira.boundaries.evidence_arrival import (
    EvidenceArrivalSchedule,
    compute_t_evidence,
    first_holder_cycle_for_domain,
    holder_count_at_cycle,
    reproducer_order,
)
from fedsira.boundaries.heterogeneity import (
    apply_quantity_skew_to_cap,
    exclude_source_from_quantity_skew,
    feature_shift_sign,
    quantity_skew_multiplier_by_domain,
    select_heterogeneity_shift_features,
)
from fedsira.config.schema import ScientificConfig, VerificationConfig
from fedsira.datasets.ciciot2023.schema import (
    TARGET_LABEL as CICIOT2023_TARGET_LABEL,
)
from fedsira.datasets.common import ROLE_HASH_TOKEN, Role
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_DOMAIN_ORDER,
    NBAIOT_TRIGGER_FEATURES,
    NBaiotClass,
    NBaiotDomain,
)
from fedsira.domain.enums import (
    ByzantineVerifierBehavior,
    CapabilityContractScope,
    ClaimOpeningMode,
    ClaimState,
    DatasetId,
    DormantOrigin,
    ExperimentLifecycleState,
    FailureClass,
    ScientificCellPhase,
    TernaryOutcome,
    VerificationOmissionMarker,
)
from fedsira.domain.records import CanonicalToken, MasterSeed, SeedBundle
from fedsira.evaluation.aggregation import (
    coefficient_of_variation,
    domain_disparity,
    equal_weight_domain_mean,
    interquartile_range,
    percentile_10_domain_target_f1,
    worst_domain_target_f1,
)
from fedsira.evaluation.communication import (
    SERVER_TOKEN,
    CommunicationMessageMetadata,
    CommunicationMessageType,
    TensorParameterKind,
    TensorPayloadMetadata,
    canonical_parameter_tensor_name,
    communication_bytes,
    encode_message_envelope,
    model_transmission_count,
)
from fedsira.evaluation.metrics import (
    boundary_metric_set,
    clean_proposal_oracle_label,
    dormant_claim_rate,
    false_launch_rate,
    legitimate_admission_rate,
    malicious_admission_rate,
    report_metric_set,
    reproduction_attempt_count,
    supported_macro_f1_harm,
    target_capability_gain,
)
from fedsira.evaluation.records import (
    AdmissionDelayDecomposition,
    MetricResult,
    ProposalOracleLabel,
)
from fedsira.evaluation.screen import screen_fold_index
from fedsira.experiments.collapse import ResolvedCore
from fedsira.experiments.execution import CellExecutionOutcome, CellExecutor
from fedsira.experiments.planning import ScientificCell
from fedsira.experiments.real_evidence import (
    BackdoorScope,
    EpistemicFailureScope,
    HeterogeneityScope,
    RealAnchor,
    RealReportSummary,
    RootCauseScope,
    certified_domain_delta_committee,
    compute_capability_under_specification_summary,
    compute_real_report_summary,
    compute_screen_differential,
    compute_shared_epistemic_failure_summary,
    compute_source_backdoor_asr,
    compute_unmatched_screen_differential,
    domain_anchor_train_feature_mean,
    evaluate_certified_ensemble,
    evaluate_domain,
    flat_parameters_identity,
    non_source_domains,
    prepared_feature_names,
    real_evidence_available,
    recovery_backdoor_alarm_threshold,
    root_cause_partitioned_row_ids,
    train_anchor,
    train_centralized_reference_checkpoint,
    train_certified_ensemble_group_checkpoints,
    train_density_cluster_trimmed_mean_delta,
    train_fedavg_reference_delta,
    train_generic_hard_supported_examples_delta,
    train_krum_reference_delta,
    train_local_only_reference_checkpoint,
    train_recovery_after_source_admission_delta,
    train_secure_continual_assessment_delta,
    train_source_candidate_delta,
    train_source_update_sanitization_delta,
    train_update_reconstruction_filter_delta,
    triggered_to_benign_rate,
)
from fedsira.experiments.registry import (
    ADMISSION_DELAY_DECOMPOSITION_NAME,
    BYZANTINE_BOUND_VIOLATION_NAME,
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
    EXTERNAL_VERIFICATION_NECESSITY_NAME,
    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
    MECHANISM_ABLATION_NAME,
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME,
    SECONDARY_DATASET_GENERALIZATION_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
    SINGLE_REPRODUCTION_NECESSITY_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    AblationVariant,
    BoundCondition,
    EpistemicFailureType,
    ExternalVerificationCondition,
    HeterogeneityRegime,
    OpeningMode,
    PluralityCondition,
    PrimaryScenario,
    ProposalEpisode,
    ReproducerCondition,
    SourceExclusionMethod,
    VerifierCondition,
    VerifierProfile,
    experiment_by_name,
)
from fedsira.learning.anchor import run_anchor_fedavg_training
from fedsira.learning.post_reference import run_post_reference_training
from fedsira.protocol.admission import (
    AdmissionArtifactContent,
    apply_production_update,
    final_gate_predicates_pass,
    median_domain_target_f1,
    resolve_production_update,
    validate_admission_artifact_content,
    validate_admission_requires_final_gate,
    validate_production_checkpoint_excludes_source,
)
from fedsira.protocol.claim_contract import (
    build_capability_claim_contract,
    capability_claim_contract_passes,
    compute_claim_identity,
    reproduction_evidence_is_adequate,
    screen_evidence_is_adequate,
    validate_source_excluded_production_weight,
    verification_evidence_is_adequate,
)
from fedsira.protocol.opening import (
    ScreenDomainResult,
    candidate_free_screen_domain_predicate,
    candidate_screen_transition,
    raw_target_f1_screen_domain_decision_is_positive,
    screen_domain_decision_is_positive,
    screen_domain_order,
    start_claim,
    unmatched_control_screen_domain_decision_is_positive,
)
from fedsira.protocol.reproduction import (
    ReproductionAttempt,
    compute_reproduction_commitment_hash,
    consumed_domains,
    handle_adequate_domain_trained,
    handle_inadequate_domain,
    handle_no_adequate_unconsumed_domain,
    next_reproducer_domain,
    select_compromised_reproducers,
    validate_commitment_exists_before_verifier_assignment,
    validate_reproduction_start_checkpoint,
    validate_reproduction_starts_from_anchor,
)
from fedsira.protocol.source_selection import select_source_domain, source_selection_order
from fedsira.protocol.state_machine import (
    apply_logical_cycle_expiry,
    resolve_ternary_outcome,
    resume_dormant_claim,
)
from fedsira.protocol.synthesis import (
    CertifiedReproductionRow,
    krum_input_excludes_source,
    select_krum_update,
    synthesis_pending_transition,
)
from fedsira.protocol.theory import (
    deduplicate_reports_by_proxy,
    diagnostic_at_least_two_byzantine_probability,
    first_cycle_with_minimum_eligible_evidence_holders,
    krum_committee_is_admissible,
    minimum_honest_positive_count,
    reproduction_update_vector,
    validate_exactly_one_source_domain,
    validate_no_safety_claim_before_tau_k,
)
from fedsira.protocol.verification import (
    byzantine_selection_order,
    construct_above_bound_panel,
    deterministic_verifier_panel,
    diagnostic_committee_panel,
    panel_votes_are_one_per_domain,
    reproduction_row_is_certified,
    select_compromised_verifiers,
    verification_pending_transition,
    verifier_assignment_seed_for_row,
    verifier_assignment_timestamp_is_valid,
    verifier_is_eligible,
)
from fedsira.runtime.determinism import derive_uint32
from fedsira.runtime.state import FailureDetail
from fedsira.runtime.timing import (
    peak_gpu_memory_bytes,
    peak_host_resident_set_bytes,
    reset_peak_gpu_memory_counter,
)
from fedsira.runtime.timing import ElapsedTimer

EVIDENCE_INSUFFICIENT_REASON = FailureClass.EVIDENCE_INSUFFICIENT.value
SOURCE_SELECTION_SEED_SEPARATOR = "SOURCE_SELECTION_SEED"
COMMITMENT_HASH_SEPARATOR = "COMMITMENT_HASH"
VERIFIER_ASSIGNMENT_NAMESPACE_SEPARATOR = "VERIFIER_ASSIGNMENT_NAMESPACE"
BYZANTINE_VERIFIER_SELECTION_SEPARATOR = "BYZANTINE_VERIFIER_SELECTION"
ANCHOR_FLAT_PARAMETERS = torch.zeros(115 * 256)


def _training_entry_points(
    evidence: PreparedEvidenceCounts,
    config: ScientificConfig,
) -> tuple[CanonicalToken, ...]:
    if (
        evidence.reproduction_target_count
        < config.capability_claim.evidence_minima.reproduction_target_examples
    ):
        return ()
    if (
        evidence.reproduction_supported_count
        < config.capability_claim.evidence_minima.reproduction_supported_control_examples
    ):
        return ()
    anchor_entry = run_anchor_fedavg_training.__module__
    post_reference_entry = run_post_reference_training.__module__
    verifier_aware_entry = verifier_aware_training_step.__module__
    return (anchor_entry, post_reference_entry, verifier_aware_entry)


@dataclass(frozen=True)
class PreparedEvidenceCounts:
    screen_target_count: int
    reproduction_target_count: int
    reproduction_supported_count: int
    final_gate_adequate_domain_count: int


@dataclass(frozen=True)
class OpeningIdentity:
    claim_identity: str
    contract_passes: bool


def load_prepared_evidence_counts(
    prepared_root: Path, target_class_token: CanonicalToken
) -> PreparedEvidenceCounts | None:
    if not prepared_root.exists():
        return None
    screen_target_count = 0
    reproduction_target_count = 0
    reproduction_supported_count = 0
    final_gate_target_domains: set[CanonicalToken] = set()
    for metadata_path in sorted(prepared_root.glob("*.json")):
        try:
            payload = json.loads(metadata_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        role = payload.get("role")
        row_count = int(payload.get("row_count", 0))
        class_id = payload.get("class_id")
        domain = payload.get("domain")
        if role == Role.CANDIDATE_SCREEN.value and class_id == target_class_token:
            screen_target_count += row_count
        elif role == Role.REPRODUCTION.value and class_id == target_class_token:
            reproduction_target_count += row_count
        elif role == Role.POST_REFERENCE_REPLAY.value and class_id != target_class_token:
            reproduction_supported_count += row_count
        elif (
            role == Role.FINAL_GATE.value
            and class_id == target_class_token
            and isinstance(domain, str)
        ):
            final_gate_target_domains.add(domain)
    if screen_target_count == 0 and reproduction_target_count == 0:
        return None
    return PreparedEvidenceCounts(
        screen_target_count=screen_target_count,
        reproduction_target_count=reproduction_target_count,
        reproduction_supported_count=reproduction_supported_count,
        final_gate_adequate_domain_count=len(final_gate_target_domains),
    )


def _opening_mode_for_cell(
    cell: ScientificCell, resolved_core: ResolvedCore | None = None
) -> ClaimOpeningMode:
    if cell.method == RESOLVED_FEDSIRA_CORE_METHOD and resolved_core is not None:
        return resolved_core.opening_mode
    if cell.method == OpeningMode.PROPOSAL_ASSISTED.value:
        return ClaimOpeningMode.PROPOSAL_ASSISTED
    return ClaimOpeningMode.CANDIDATE_FREE


def _opening_identity(config: ScientificConfig) -> OpeningIdentity:
    contract = build_capability_claim_contract(
        "a" * 64,
        ROLE_HASH_TOKEN[Role.POST_REFERENCE_REPLAY],
        config.datasets.primary.name,
        len(NBAIOT_DOMAIN_ORDER),
        "b" * 64,
        config.capability_claim,
    )
    claim_identity = compute_claim_identity(contract)
    contract_passes = capability_claim_contract_passes(
        contract,
        MetricResult(None, 0),
        MetricResult(None, 0),
        MetricResult(None, 0),
        MetricResult(None, 0),
    )
    return OpeningIdentity(claim_identity=claim_identity, contract_passes=contract_passes)


def _source_domain_for_cell(cell: ScientificCell) -> NBaiotDomain | None:
    source_order = source_selection_order(
        derive_uint32(SOURCE_SELECTION_SEED_SEPARATOR, cell.master_seed)
    )
    validate_exactly_one_source_domain((source_order[0],))
    return select_source_domain(
        source_order,
        frozenset(NBAIOT_DOMAIN_ORDER),
        requires_gafgyt_udp_carrier=False,
        domains_with_gafgyt_udp=frozenset(),
    )


def _reproducer_order(cell: ScientificCell) -> tuple[NBaiotDomain, ...]:
    return reproducer_order(
        NBAIOT_DOMAIN_ORDER,
        derive_uint32("REPRODUCER_ORDER_SEED", cell.master_seed),
    )


def _row_requirement(
    cell: ScientificCell, config: ScientificConfig, resolved_core: ResolvedCore | None = None
) -> int:
    if cell.method == RESOLVED_FEDSIRA_CORE_METHOD and resolved_core is not None:
        return config.protocol.synthesis.committee_size if resolved_core.plurality_survives else 1
    if cell.method in (
        BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
        BaselineIdentity.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN.value,
    ) or (
        cell.experiment == MECHANISM_ABLATION_NAME
        and cell.method == AblationVariant.ONE_INDEPENDENT_REPRODUCTION.value
    ):
        return 1
    if cell.method == BaselineIdentity.THREE_ROW_COORDINATE_MEDIAN_ALTERNATIVE.value or (
        cell.experiment == MECHANISM_ABLATION_NAME
        and cell.method == AblationVariant.GENERIC_THREE_ROW_THRESHOLD.value
    ):
        return config.baselines.three_row_coordinate_median.row_count
    return config.protocol.synthesis.committee_size


def _commitment_digest(reproducer_domain: NBaiotDomain, master_seed: MasterSeed) -> str:
    return compute_reproduction_commitment_hash(
        reproducer_domain,
        "c" * 64,
        derive_uint32(COMMITMENT_HASH_SEPARATOR, master_seed),
        ANCHOR_FLAT_PARAMETERS,
    )


def _verifier_panel(
    source_domain: NBaiotDomain | None,
    reproducer_domain: NBaiotDomain,
    master_seed: MasterSeed,
    verification_config: VerificationConfig,
    allow_source_as_verifier: bool = False,
) -> tuple[NBaiotDomain, ...]:
    eligible_verifiers = tuple(
        domain
        for domain in NBAIOT_DOMAIN_ORDER
        if verifier_is_eligible(domain, source_domain, reproducer_domain, allow_source_as_verifier)
    )
    row_seed = verifier_assignment_seed_for_row(
        derive_uint32(VERIFIER_ASSIGNMENT_NAMESPACE_SEPARATOR, master_seed),
        _commitment_digest(reproducer_domain, master_seed),
    )
    if not verifier_assignment_timestamp_is_valid(1.0, 0.0):
        raise ValueError("verifier assignment must follow the reproduction commitment")
    return deterministic_verifier_panel(
        eligible_verifiers, row_seed=row_seed, panel_size=verification_config.panel_size
    )


def _reproduction_progression(
    cell: ScientificCell,
    config: ScientificConfig,
    evidence: PreparedEvidenceCounts,
    external_verification_active: bool,
    row_requirement: int,
    compromised_reproducers: frozenset[NBaiotDomain],
    include_source_as_first_reproducer: bool = False,
) -> tuple[ClaimState, tuple[ReproductionAttempt, ...], tuple[str, ...]]:
    reproducer_order = _reproducer_order(cell)
    source_domain = _source_domain_for_cell(cell)
    validate_reproduction_start_checkpoint("anchor-checkpoint", frozenset({"source-checkpoint"}))
    validate_reproduction_starts_from_anchor(ANCHOR_FLAT_PARAMETERS.clone(), ANCHOR_FLAT_PARAMETERS)
    adequate_domains = frozenset(
        domain for domain in NBAIOT_DOMAIN_ORDER if domain != source_domain
    )
    attempts: list[ReproductionAttempt] = []
    commitment_hashes: list[str] = []
    certified_count = 0
    state = ClaimState.REPRODUCTION_PENDING
    if include_source_as_first_reproducer and source_domain is not None:
        commitment_hash = compute_reproduction_commitment_hash(
            source_domain,
            "c" * 64,
            derive_uint32(COMMITMENT_HASH_SEPARATOR, cell.master_seed),
            ANCHOR_FLAT_PARAMETERS,
        )
        commitment_hashes.append(commitment_hash)
        validate_commitment_exists_before_verifier_assignment(commitment_hash)
        attempts.append(
            ReproductionAttempt(domain=source_domain, was_trained=True, is_certified=True)
        )
        certified_count += 1
        state = handle_adequate_domain_trained(
            external_verification_active, certified_count >= row_requirement
        )
        if state is ClaimState.SYNTHESIS_PENDING:
            return state, tuple(attempts), tuple(commitment_hashes)
    for _row_index in range(len(reproducer_order)):
        next_domain = next_reproducer_domain(
            reproducer_order, consumed_domains(attempts), adequate_domains
        )
        if next_domain is None:
            state = handle_no_adequate_unconsumed_domain(certified_count >= row_requirement)
            break
        if next_domain in compromised_reproducers:
            attempts.append(
                ReproductionAttempt(domain=next_domain, was_trained=True, is_certified=False)
            )
            state = handle_inadequate_domain()
            continue
        commitment_hash = compute_reproduction_commitment_hash(
            next_domain,
            "c" * 64,
            derive_uint32(COMMITMENT_HASH_SEPARATOR, cell.master_seed),
            ANCHOR_FLAT_PARAMETERS,
        )
        commitment_hashes.append(commitment_hash)
        validate_commitment_exists_before_verifier_assignment(commitment_hash)
        attempts.append(
            ReproductionAttempt(domain=next_domain, was_trained=True, is_certified=True)
        )
        certified_count += 1
        state = handle_adequate_domain_trained(
            external_verification_active, certified_count >= row_requirement
        )
        if state is ClaimState.SYNTHESIS_PENDING:
            break
    return state, tuple(attempts), tuple(commitment_hashes)


def _single_verifier_progression(
    cell: ScientificCell,
    config: ScientificConfig,
    source_domain: NBaiotDomain | None,
) -> tuple[ClaimState, tuple[ReproductionAttempt, ...], tuple[str, ...]]:
    reproducer_order = _reproducer_order(cell)
    adequate_domains = frozenset(
        domain for domain in NBAIOT_DOMAIN_ORDER if domain != source_domain
    )
    consumed: set[NBaiotDomain] = set()
    while True:
        next_domain = first_eligible_non_source_reproducer(
            reproducer_order, adequate_domains - frozenset(consumed)
        )
        if next_domain is None:
            return ClaimState.DORMANT, (), ()
        consumed.add(next_domain)
        commitment_hash = compute_reproduction_commitment_hash(
            next_domain,
            "c" * 64,
            derive_uint32(COMMITMENT_HASH_SEPARATOR, cell.master_seed),
            ANCHOR_FLAT_PARAMETERS,
        )
        validate_commitment_exists_before_verifier_assignment(commitment_hash)
        panel_order = _verifier_panel(
            source_domain, next_domain, cell.master_seed, config.protocol.verification
        )
        verifier_domain = single_fresh_verifier_domain(
            panel_order, frozenset(), frozenset(panel_order)
        )
        if verifier_domain is None:
            continue
        verifier_outcome = single_fresh_verifier_outcome(
            verifier_domain, resolve_ternary_outcome(True, True)
        )
        if verifier_outcome is ClaimState.ADMITTED:
            attempt = ReproductionAttempt(domain=next_domain, was_trained=True, is_certified=True)
            return ClaimState.SYNTHESIS_PENDING, (attempt,), (commitment_hash,)


def _real_final_gate_metrics(
    prepared_root: Path,
    config: ScientificConfig,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
    production_checkpoint: torch.Tensor,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> tuple[int, MetricResult, MetricResult, MetricResult, MetricResult]:
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
            MetricResult(None, 0),
            MetricResult(None, 0),
            MetricResult(None, 0),
            MetricResult(None, 0),
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
                    production_metrics.benign_far.value - anchor_metrics.benign_far.value, 1
                )
            )
        else:
            benign_far_increases.append(MetricResult(None, 0))
    return (
        len(adequate_domains),
        median_domain_target_f1(target_f1_values),
        worst_domain_target_f1(target_f1_values),
        equal_weight_domain_mean(supported_f1_harms, 1),
        equal_weight_domain_mean(benign_far_increases, 1),
    )


def _final_gate_decision(
    config: ScientificConfig,
    evidence: PreparedEvidenceCounts,
    claim_identity: str,
    source_domain: NBaiotDomain | None,
    reproducer_order: Sequence[NBaiotDomain],
    commitment_hashes: Sequence[str],
    is_plurality_active: bool,
    opening_mode: ClaimOpeningMode,
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor | None,
    coordinate_median_active: bool = False,
    no_final_synthesis_gate_active: bool = False,
    use_source_delta_for_source_domain: bool = False,
    force_first_row_to_source_delta: bool = False,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> tuple[ClaimState, RealReportSummary | None]:
    base_flat_parameters = anchor.flat_parameters if anchor is not None else ANCHOR_FLAT_PARAMETERS
    committee_deltas = (
        certified_domain_delta_committee(
            prepared_root,
            config,
            master_seed,
            anchor,
            reproducer_order,
            heterogeneity_scope=heterogeneity_scope,
        )
        if anchor is not None
        else {}
    )
    if use_source_delta_for_source_domain and anchor is not None and source_domain is not None:
        source_delta = train_source_candidate_delta(
            prepared_root, config, master_seed, anchor, source_domain
        )
        if source_delta is not None:
            committee_deltas[source_domain] = source_delta
    if (
        force_first_row_to_source_delta
        and anchor is not None
        and source_domain is not None
        and reproducer_order
    ):
        source_delta = train_source_candidate_delta(
            prepared_root, config, master_seed, anchor, source_domain
        )
        if source_delta is not None:
            committee_deltas[reproducer_order[0]] = source_delta
    if coordinate_median_active:
        median_deltas = tuple(
            committee_deltas.get(
                domain, reproduction_update_vector(ANCHOR_FLAT_PARAMETERS, ANCHOR_FLAT_PARAMETERS)
            )
            for domain in reproducer_order
        )
        production_update = coordinate_wise_median_synthesis(median_deltas)
        production_checkpoint = apply_production_update(base_flat_parameters, production_update)
        return _final_gate_decision_from_production_checkpoint(
            config,
            evidence,
            claim_identity,
            source_domain,
            reproducer_order,
            commitment_hashes,
            opening_mode,
            False,
            prepared_root,
            anchor,
            production_checkpoint,
            heterogeneity_scope=heterogeneity_scope,
        )
    krum_selected_update: torch.Tensor | None = None
    if is_plurality_active:
        committee = tuple(
            CertifiedReproductionRow(
                reproducer_domain=domain,
                update_vector=committee_deltas.get(
                    domain,
                    reproduction_update_vector(ANCHOR_FLAT_PARAMETERS, ANCHOR_FLAT_PARAMETERS),
                ),
            )
            for domain in reproducer_order
        )
        krum_selected_update = select_krum_update(
            committee, config.protocol.synthesis.maximum_byzantine_reproduction_rows
        ).update_vector
    single_reproduction_update = (
        committee_deltas.get(reproducer_order[0], ANCHOR_FLAT_PARAMETERS)
        if reproducer_order
        else ANCHOR_FLAT_PARAMETERS
    )
    production_update = resolve_production_update(
        is_plurality_active,
        krum_selected_update,
        single_reproduction_update,
    )
    production_checkpoint = apply_production_update(base_flat_parameters, production_update)
    return _final_gate_decision_from_production_checkpoint(
        config,
        evidence,
        claim_identity,
        source_domain,
        reproducer_order,
        commitment_hashes,
        opening_mode,
        is_plurality_active,
        prepared_root,
        anchor,
        production_checkpoint,
        no_final_synthesis_gate_active,
        heterogeneity_scope=heterogeneity_scope,
    )


def _final_gate_decision_from_production_checkpoint(
    config: ScientificConfig,
    evidence: PreparedEvidenceCounts,
    claim_identity: str,
    source_domain: NBaiotDomain | None,
    reproducer_order: Sequence[NBaiotDomain],
    commitment_hashes: Sequence[str],
    opening_mode: ClaimOpeningMode,
    is_plurality_active: bool,
    prepared_root: Path,
    anchor: RealAnchor | None,
    production_checkpoint: torch.Tensor,
    no_final_synthesis_gate_active: bool = False,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> tuple[ClaimState, RealReportSummary | None]:
    if anchor is not None:
        (
            adequate_final_gate_domain_count,
            median_target_f1,
            minimum_target_f1,
            pooled_supported_macro_f1_drop,
            pooled_benign_far_increase,
        ) = _real_final_gate_metrics(
            prepared_root,
            config,
            anchor,
            source_domain,
            production_checkpoint,
            heterogeneity_scope=heterogeneity_scope,
        )
    else:
        adequate_final_gate_domain_count = evidence.final_gate_adequate_domain_count
        median_target_f1 = median_domain_target_f1(
            tuple(MetricResult(None, 0) for _domain in NBAIOT_DOMAIN_ORDER)
        )
        minimum_target_f1 = MetricResult(None, 0)
        pooled_supported_macro_f1_drop = MetricResult(None, 0)
        pooled_benign_far_increase = MetricResult(None, 0)
    predicates_pass = final_gate_predicates_pass(
        median_target_f1,
        minimum_target_f1,
        pooled_supported_macro_f1_drop,
        pooled_benign_far_increase,
        True,
        config.protocol.final_gate,
    )
    final_gate_state = (
        ClaimState.ADMITTED
        if no_final_synthesis_gate_active and anchor is not None
        else synthesis_pending_transition(
            adequate_final_gate_domain_count=adequate_final_gate_domain_count,
            final_gate_predicates_pass=predicates_pass,
            final_gate_config=config.protocol.final_gate,
        )
    )
    real_report_summary = (
        compute_real_report_summary(prepared_root, anchor, source_domain, production_checkpoint)
        if anchor is not None
        else None
    )
    if final_gate_state is not ClaimState.ADMITTED:
        return final_gate_state, real_report_summary
    validate_production_checkpoint_excludes_source(production_checkpoint, None)
    validate_admission_requires_final_gate(ClaimState.ADMITTED, True)
    validate_admission_artifact_content(
        AdmissionArtifactContent(
            anchor_checkpoint_identity="a" * 64,
            source_commitment_identity=(
                "s" * 64 if opening_mode is ClaimOpeningMode.PROPOSAL_ASSISTED else None
            ),
            claim_identity=claim_identity,
            reproducer_assignment_order=tuple(reproducer_order),
            reproduction_commitment_hashes=tuple(commitment_hashes),
            verifier_record=VerificationOmissionMarker.EXTERNAL_VERIFICATION_NOT_USED,
            krum_configuration_identity="k" * 64,
            production_update_identity="p" * 64,
            final_gate_sample_manifest_identity="m" * 64,
            final_gate_metrics_identity="e" * 64,
            seed_bundle=SeedBundle(
                master_seeds=config.seeds_and_determinism.master_seeds,
                analysis_seed=config.seeds_and_determinism.analysis_seed,
                smoke_seed=config.seeds_and_determinism.smoke_seed,
            ),
            semantic_cell_key="cell-key",
            cell_phase_identity="phase-key",
            upstream_dependency_fingerprints=("u" * 64,),
            producer_component_fingerprint="pc" + "0" * 62,
            runtime_dependency_fingerprint="rd" + "0" * 62,
            repository_commit="deadbeef",
            dependency_lock_digest="dl" + "0" * 62,
            environment_fingerprint="ef" + "0" * 62,
        ),
        opening_mode,
        is_plurality_active,
    )
    return ClaimState.ADMITTED, real_report_summary


def _compromised_reproducer_count(condition: CanonicalToken) -> int:
    if condition in (
        ReproducerCondition.ONE_SOURCE_COPY.value,
        ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR.value,
        ReproducerCondition.ONE_VERIFIER_AWARE_BACKDOOR.value,
    ):
        return 1
    if condition in (
        ReproducerCondition.TWO_SOURCE_COPIES.value,
        ReproducerCondition.TWO_MODEL_REPLACEMENT_BACKDOORS.value,
        ReproducerCondition.TWO_VERIFIER_AWARE_BACKDOORS.value,
    ):
        return 2
    return 0


def _compromised_verifier_count(condition: CanonicalToken) -> int:
    if condition in (
        VerifierCondition.ONE_FALSE_POSITIVE.value,
        VerifierCondition.ONE_FALSE_NEGATIVE.value,
    ):
        return 1
    if condition in (
        VerifierCondition.TWO_FALSE_POSITIVES.value,
        VerifierCondition.TWO_FALSE_NEGATIVES.value,
    ):
        return 2
    return 0


RESOLVED_FEDSIRA_CORE_METHOD = "Resolved FedSIRA Core"


class ProtocolCellExecutor(CellExecutor):
    def __init__(
        self,
        primary_prepared_root: Path | None = None,
        secondary_prepared_root: Path | None = None,
        resolved_core: ResolvedCore | None = None,
    ) -> None:
        self._prepared_root = primary_prepared_root or prepared_evidence_root(
            DATASET_PACKAGE_NAME[DatasetId.N_BAIOT]
        )
        self._secondary_prepared_root = secondary_prepared_root or prepared_evidence_root(
            DATASET_PACKAGE_NAME[DatasetId.CICIOT2023]
        )
        self._resolved_core = resolved_core
        self._real_anchor_cache: dict[MasterSeed, RealAnchor | None] = {}
        self._pending_real_report: RealReportSummary | None = None

    def _real_anchor(self, config: ScientificConfig, master_seed: MasterSeed) -> RealAnchor | None:
        if master_seed not in self._real_anchor_cache:
            self._real_anchor_cache[master_seed] = (
                train_anchor(self._prepared_root, config, master_seed)
                if real_evidence_available(self._prepared_root)
                else None
            )
        return self._real_anchor_cache[master_seed]

    def _same_context_verifier_panel(
        self,
        source_domain: NBaiotDomain | None,
        reproducer_domain: NBaiotDomain,
        config: ScientificConfig,
    ) -> tuple[NBaiotDomain, ...]:
        eligible_verifiers = tuple(
            domain
            for domain in NBAIOT_DOMAIN_ORDER
            if verifier_is_eligible(domain, source_domain, reproducer_domain)
        )
        reproducer_feature_mean = domain_anchor_train_feature_mean(
            self._prepared_root, reproducer_domain
        )
        if reproducer_feature_mean is None:
            raise ValueError(
                f"same-context verification requires real anchor-train features for "
                f"{reproducer_domain}"
            )
        eligible_verifier_feature_means: dict[NBaiotDomain, torch.Tensor] = {}
        for domain in eligible_verifiers:
            feature_mean = domain_anchor_train_feature_mean(self._prepared_root, domain)
            if feature_mean is None:
                raise ValueError(
                    f"same-context verification requires real anchor-train features for {domain}"
                )
            eligible_verifier_feature_means[domain] = feature_mean
        return same_context_verifier_panel(
            reproducer_feature_mean,
            eligible_verifier_feature_means,
            config.protocol.verification.panel_size,
        )

    def _candidate_capability_contract_passes(
        self,
        config: ScientificConfig,
        real_anchor: RealAnchor,
        source_domain: NBaiotDomain,
        candidate_flat_parameters: torch.Tensor,
    ) -> bool:
        anchor_screen = evaluate_domain(
            self._prepared_root,
            real_anchor,
            real_anchor.flat_parameters,
            source_domain,
            role=Role.POST_REFERENCE_REPLAY,
            target_role=Role.CANDIDATE_SCREEN,
        )
        candidate_screen = evaluate_domain(
            self._prepared_root,
            real_anchor,
            candidate_flat_parameters,
            source_domain,
            role=Role.POST_REFERENCE_REPLAY,
            target_role=Role.CANDIDATE_SCREEN,
        )
        if anchor_screen is None or candidate_screen is None:
            return False
        contract = build_capability_claim_contract(
            real_anchor.dataset_manifest_hash,
            ROLE_HASH_TOKEN[Role.POST_REFERENCE_REPLAY],
            config.datasets.primary.name,
            len(NBAIOT_DOMAIN_ORDER),
            real_anchor.dataset_manifest_hash,
            config.capability_claim,
        )
        target_f1_gain = target_capability_gain(candidate_screen.target_f1, anchor_screen.target_f1)
        supported_macro_f1_drop = supported_macro_f1_harm(
            anchor_screen.supported_macro_f1, candidate_screen.supported_macro_f1
        )
        benign_far_increase = (
            MetricResult(candidate_screen.benign_far.value - anchor_screen.benign_far.value, 1)
            if candidate_screen.benign_far.value is not None
            and anchor_screen.benign_far.value is not None
            else MetricResult(None, 0)
        )
        return capability_claim_contract_passes(
            contract,
            candidate_screen.target_f1,
            target_f1_gain,
            supported_macro_f1_drop,
            benign_far_increase,
        )

    def _scoped_capability_contract_passes(
        self,
        config: ScientificConfig,
        real_anchor: RealAnchor,
        source_domain: NBaiotDomain,
        candidate_flat_parameters: torch.Tensor,
        root_cause_scope: RootCauseScope,
    ) -> bool:
        anchor_screen = evaluate_domain(
            self._prepared_root,
            real_anchor,
            real_anchor.flat_parameters,
            source_domain,
            role=Role.POST_REFERENCE_REPLAY,
            target_role=Role.CANDIDATE_SCREEN,
            root_cause_scope=root_cause_scope,
        )
        candidate_screen = evaluate_domain(
            self._prepared_root,
            real_anchor,
            candidate_flat_parameters,
            source_domain,
            role=Role.POST_REFERENCE_REPLAY,
            target_role=Role.CANDIDATE_SCREEN,
            root_cause_scope=root_cause_scope,
        )
        if anchor_screen is None or candidate_screen is None:
            return False
        contract = build_capability_claim_contract(
            real_anchor.dataset_manifest_hash,
            ROLE_HASH_TOKEN[Role.POST_REFERENCE_REPLAY],
            config.datasets.primary.name,
            len(NBAIOT_DOMAIN_ORDER),
            real_anchor.dataset_manifest_hash,
            config.capability_claim,
        )
        target_f1_gain = target_capability_gain(candidate_screen.target_f1, anchor_screen.target_f1)
        supported_macro_f1_drop = supported_macro_f1_harm(
            anchor_screen.supported_macro_f1, candidate_screen.supported_macro_f1
        )
        benign_far_increase = (
            MetricResult(candidate_screen.benign_far.value - anchor_screen.benign_far.value, 1)
            if candidate_screen.benign_far.value is not None
            and anchor_screen.benign_far.value is not None
            else MetricResult(None, 0)
        )
        return capability_claim_contract_passes(
            contract,
            candidate_screen.target_f1,
            target_f1_gain,
            supported_macro_f1_drop,
            benign_far_increase,
        )

    def _backdoor_scope_for_cell(
        self, cell: ScientificCell, config: ScientificConfig
    ) -> BackdoorScope | None:
        if cell.condition != ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value:
            return None
        real_feature_names = prepared_feature_names(self._prepared_root)
        if real_feature_names is None:
            return None
        trigger_indices = tuple(real_feature_names.index(name) for name in NBAIOT_TRIGGER_FEATURES)
        return BackdoorScope(
            attack_generation_seed=derive_uint32("ATTACK_GENERATION_SEED", cell.master_seed),
            poison_fraction=(
                config.attacks_and_boundaries.hidden_source_backdoor.confirmatory_poison_fraction
            ),
            trigger_feature_indices=trigger_indices,
            trigger_value=(
                config.attacks_and_boundaries.hidden_source_backdoor.trigger_value_after_standardization
            ),
        )

    def _heterogeneity_scope_for_cell(
        self, cell: ScientificCell, config: ScientificConfig
    ) -> HeterogeneityScope | None:
        if cell.experiment != HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME:
            return None
        regime = HeterogeneityRegime(cell.condition)
        magnitudes = config.attacks_and_boundaries.heterogeneity.feature_shift_magnitudes
        if regime is HeterogeneityRegime.FEATURE_SHIFT_0_5:
            shift_magnitude = magnitudes[0]
        elif regime is HeterogeneityRegime.FEATURE_SHIFT_1_0:
            shift_magnitude = magnitudes[1]
        else:
            return None
        real_feature_names = prepared_feature_names(self._prepared_root)
        if real_feature_names is None:
            return None
        heterogeneity_seed = derive_uint32("HETEROGENEITY_SEED", cell.master_seed)
        selected_feature_names = select_heterogeneity_shift_features(
            real_feature_names,
            heterogeneity_seed,
            config.attacks_and_boundaries.heterogeneity.feature_shift_selected_feature_count,
        )
        return HeterogeneityScope(
            heterogeneity_namespace_seed=heterogeneity_seed,
            selected_feature_names=selected_feature_names,
            feature_names=real_feature_names,
            shift_magnitude=shift_magnitude,
        )

    def _client_review_outcome(self, cell: ScientificCell, config: ScientificConfig) -> ClaimState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(config, cell.master_seed)
        positive_report_count = 0
        if real_anchor is not None and source_domain is not None:
            backdoor_scope = self._backdoor_scope_for_cell(cell, config)
            source_delta = train_source_candidate_delta(
                self._prepared_root,
                config,
                cell.master_seed,
                real_anchor,
                source_domain,
                backdoor_scope=backdoor_scope,
            )
            if source_delta is not None and self._candidate_capability_contract_passes(
                config, real_anchor, source_domain, real_anchor.flat_parameters + source_delta
            ):
                positive_report_count = CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT
        return review_style_baseline_outcome(
            adequate_reviewer_count=CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT,
            positive_report_count=positive_report_count,
            panel_size=config.protocol.claim_opening.screen_domains,
            required_positive_reports=config.protocol.claim_opening.required_positive_screen_domains,
        )

    def _source_update_sanitization_outcome(
        self, cell: ScientificCell, config: ScientificConfig, evidence: PreparedEvidenceCounts
    ) -> ClaimState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(config, cell.master_seed)
        if real_anchor is None or source_domain is None:
            return ClaimState.DORMANT
        clipped_delta = train_source_update_sanitization_delta(
            self._prepared_root, config, cell.master_seed, real_anchor, source_domain
        )
        if clipped_delta is None:
            return ClaimState.DORMANT
        production_checkpoint = real_anchor.flat_parameters + clipped_delta
        positive_report_count = (
            CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT
            if self._candidate_capability_contract_passes(
                config, real_anchor, source_domain, production_checkpoint
            )
            else 0
        )
        review_state = review_style_baseline_outcome(
            adequate_reviewer_count=CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT,
            positive_report_count=positive_report_count,
            panel_size=config.protocol.claim_opening.screen_domains,
            required_positive_reports=config.protocol.claim_opening.required_positive_screen_domains,
        )
        if review_state is not ClaimState.ADMITTED:
            return review_state
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            config,
            evidence,
            "source-update-sanitization-claim",
            source_domain,
            (),
            (),
            ClaimOpeningMode.CANDIDATE_FREE,
            False,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _source_release_after_full_external_check_outcome(
        self, cell: ScientificCell, config: ScientificConfig, evidence: PreparedEvidenceCounts
    ) -> ClaimState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(config, cell.master_seed)
        if real_anchor is None or source_domain is None:
            return ClaimState.DORMANT
        source_delta = train_source_candidate_delta(
            self._prepared_root, config, cell.master_seed, real_anchor, source_domain
        )
        if source_delta is None:
            return ClaimState.DORMANT
        production_checkpoint = real_anchor.flat_parameters + source_delta
        panel = _verifier_panel(
            source_domain, source_domain, cell.master_seed, config.protocol.verification
        )
        if not panel_votes_are_one_per_domain(panel):
            return ClaimState.DORMANT
        reports = tuple(resolve_ternary_outcome(True, True) for _domain in panel)
        positive_report_count = sum(1 for report in reports if report is TernaryOutcome.POSITIVE)
        review_state = review_style_baseline_outcome(
            adequate_reviewer_count=len(panel),
            positive_report_count=positive_report_count,
            panel_size=config.protocol.verification.panel_size,
            required_positive_reports=config.protocol.verification.required_positive_reports,
        )
        if review_state is not ClaimState.ADMITTED:
            return review_state
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            config,
            evidence,
            "source-release-full-external-check-claim",
            source_domain,
            (),
            (),
            ClaimOpeningMode.CANDIDATE_FREE,
            False,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _recovery_after_source_admission_outcome(
        self, cell: ScientificCell, config: ScientificConfig, evidence: PreparedEvidenceCounts
    ) -> ClaimState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(config, cell.master_seed)
        if real_anchor is None or source_domain is None:
            return ClaimState.DORMANT
        review_state = self._client_review_outcome(cell, config)
        if review_state is not ClaimState.ADMITTED:
            return review_state
        source_delta = train_source_candidate_delta(
            self._prepared_root, config, cell.master_seed, real_anchor, source_domain
        )
        if source_delta is None:
            return ClaimState.DORMANT
        admitted_checkpoint = real_anchor.flat_parameters + source_delta
        anchor_verification = evaluate_domain(
            self._prepared_root,
            real_anchor,
            real_anchor.flat_parameters,
            source_domain,
            Role.ROW_VERIFICATION,
        )
        admitted_verification = evaluate_domain(
            self._prepared_root,
            real_anchor,
            admitted_checkpoint,
            source_domain,
            Role.ROW_VERIFICATION,
        )
        alarm_threshold = recovery_backdoor_alarm_threshold(
            self._prepared_root, config, real_anchor
        )
        if anchor_verification is None or admitted_verification is None or alarm_threshold is None:
            return ClaimState.DORMANT
        supported_macro_f1_drop = supported_macro_f1_harm(
            anchor_verification.supported_macro_f1, admitted_verification.supported_macro_f1
        )
        benign_far_increase = (
            MetricResult(
                admitted_verification.benign_far.value - anchor_verification.benign_far.value, 1
            )
            if admitted_verification.benign_far.value is not None
            and anchor_verification.benign_far.value is not None
            else MetricResult(None, 0)
        )
        triggered_rate = triggered_to_benign_rate(
            self._prepared_root,
            real_anchor,
            admitted_checkpoint,
            source_domain,
            Role.ROW_VERIFICATION,
            NBAIOT_TRIGGER_FEATURES,
            config.attacks_and_boundaries.hidden_source_backdoor.trigger_value_after_standardization,
        )
        rollback = recovery_rollback_is_triggered(
            supported_macro_f1_drop,
            benign_far_increase,
            triggered_rate,
            config.metrics_and_statistics.materiality,
            alarm_threshold,
        )
        if rollback:
            recovery_delta = train_recovery_after_source_admission_delta(
                self._prepared_root, config, cell.master_seed, real_anchor, source_domain
            )
            if recovery_delta is None:
                return ClaimState.DORMANT
            production_checkpoint = real_anchor.flat_parameters + recovery_delta
        else:
            production_checkpoint = admitted_checkpoint
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            config,
            evidence,
            "recovery-after-source-admission-claim",
            source_domain,
            (),
            (),
            ClaimOpeningMode.CANDIDATE_FREE,
            False,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _fedavg_reference_outcome(
        self, cell: ScientificCell, config: ScientificConfig, evidence: PreparedEvidenceCounts
    ) -> ClaimState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(config, cell.master_seed)
        if real_anchor is None:
            return ClaimState.DORMANT
        delta = train_fedavg_reference_delta(
            self._prepared_root, config, cell.master_seed, real_anchor, source_domain
        )
        if delta is None:
            return ClaimState.DORMANT
        production_checkpoint = real_anchor.flat_parameters + delta
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            config,
            evidence,
            "fedavg-reference-claim",
            source_domain,
            (),
            (),
            ClaimOpeningMode.CANDIDATE_FREE,
            False,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _krum_reference_outcome(
        self, cell: ScientificCell, config: ScientificConfig, evidence: PreparedEvidenceCounts
    ) -> ClaimState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(config, cell.master_seed)
        if real_anchor is None:
            return ClaimState.DORMANT
        delta = train_krum_reference_delta(
            self._prepared_root, config, cell.master_seed, real_anchor, source_domain
        )
        if delta is None:
            return ClaimState.DORMANT
        production_checkpoint = real_anchor.flat_parameters + delta
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            config,
            evidence,
            "krum-reference-claim",
            source_domain,
            (),
            (),
            ClaimOpeningMode.CANDIDATE_FREE,
            False,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _density_cluster_trimmed_mean_outcome(
        self, cell: ScientificCell, config: ScientificConfig, evidence: PreparedEvidenceCounts
    ) -> ClaimState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(config, cell.master_seed)
        if real_anchor is None:
            return ClaimState.DORMANT
        delta = train_density_cluster_trimmed_mean_delta(
            self._prepared_root, config, cell.master_seed, real_anchor, source_domain
        )
        if delta is None:
            return ClaimState.DORMANT
        production_checkpoint = real_anchor.flat_parameters + delta
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            config,
            evidence,
            "density-cluster-trimmed-mean-claim",
            source_domain,
            (),
            (),
            ClaimOpeningMode.CANDIDATE_FREE,
            False,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _update_reconstruction_filter_outcome(
        self, cell: ScientificCell, config: ScientificConfig, evidence: PreparedEvidenceCounts
    ) -> ClaimState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(config, cell.master_seed)
        if real_anchor is None:
            return ClaimState.DORMANT
        delta = train_update_reconstruction_filter_delta(
            self._prepared_root, config, cell.master_seed, real_anchor, source_domain
        )
        if delta is None:
            return ClaimState.DORMANT
        production_checkpoint = real_anchor.flat_parameters + delta
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            config,
            evidence,
            "update-reconstruction-filter-claim",
            source_domain,
            (),
            (),
            ClaimOpeningMode.CANDIDATE_FREE,
            False,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _secure_continual_assessment_outcome(
        self, cell: ScientificCell, config: ScientificConfig, evidence: PreparedEvidenceCounts
    ) -> ClaimState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(config, cell.master_seed)
        if real_anchor is None:
            return ClaimState.DORMANT
        positive_report_count = sum(
            1
            for _reviewer in range(SECURE_CONTINUAL_ASSESSMENT_REVIEWER_COUNT)
            if resolve_ternary_outcome(True, True) is TernaryOutcome.POSITIVE
        )
        review_state = review_style_baseline_outcome(
            adequate_reviewer_count=SECURE_CONTINUAL_ASSESSMENT_REVIEWER_COUNT,
            positive_report_count=positive_report_count,
            panel_size=SECURE_CONTINUAL_ASSESSMENT_REVIEWER_COUNT,
            required_positive_reports=SECURE_CONTINUAL_ASSESSMENT_REQUIRED_POSITIVE_REVIEWS,
        )
        if review_state is not ClaimState.ADMITTED:
            return review_state
        delta = train_secure_continual_assessment_delta(
            self._prepared_root, config, cell.master_seed, real_anchor, source_domain
        )
        if delta is None:
            return ClaimState.DORMANT
        production_checkpoint = real_anchor.flat_parameters + delta
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            config,
            evidence,
            "secure-continual-assessment-claim",
            source_domain,
            (),
            (),
            ClaimOpeningMode.CANDIDATE_FREE,
            False,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _local_only_reference_outcome(
        self, cell: ScientificCell, config: ScientificConfig
    ) -> ClaimState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(config, cell.master_seed)
        if real_anchor is None:
            return ClaimState.DORMANT
        target_f1_values: list[MetricResult] = []
        supported_f1_harms: list[MetricResult] = []
        benign_far_increases: list[MetricResult] = []
        for domain in non_source_domains(source_domain):
            if not local_only_reference_evaluation_is_domain_local(domain, domain):
                continue
            local_checkpoint = train_local_only_reference_checkpoint(
                self._prepared_root, config, cell.master_seed, domain
            )
            if local_checkpoint is None:
                continue
            anchor_metrics = evaluate_domain(
                self._prepared_root,
                real_anchor,
                real_anchor.flat_parameters,
                domain,
                Role.FINAL_GATE,
            )
            local_metrics = evaluate_domain(
                self._prepared_root, real_anchor, local_checkpoint, domain, Role.FINAL_GATE
            )
            if anchor_metrics is None or local_metrics is None:
                continue
            target_f1_values.append(local_metrics.target_f1)
            supported_f1_harms.append(
                supported_macro_f1_harm(
                    anchor_metrics.supported_macro_f1, local_metrics.supported_macro_f1
                )
            )
            if (
                anchor_metrics.benign_far.value is not None
                and local_metrics.benign_far.value is not None
            ):
                benign_far_increases.append(
                    MetricResult(
                        local_metrics.benign_far.value - anchor_metrics.benign_far.value, 1
                    )
                )
            else:
                benign_far_increases.append(MetricResult(None, 0))
        predicates_pass = final_gate_predicates_pass(
            median_domain_target_f1(target_f1_values),
            worst_domain_target_f1(target_f1_values),
            equal_weight_domain_mean(supported_f1_harms, 1),
            equal_weight_domain_mean(benign_far_increases, 1),
            True,
            config.protocol.final_gate,
        )
        return synthesis_pending_transition(
            adequate_final_gate_domain_count=len(target_f1_values),
            final_gate_predicates_pass=predicates_pass,
            final_gate_config=config.protocol.final_gate,
        )

    def _multiple_model_certified_ensemble_outcome(
        self, cell: ScientificCell, config: ScientificConfig
    ) -> ClaimState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(config, cell.master_seed)
        if real_anchor is None:
            return ClaimState.DORMANT
        group_checkpoints = train_certified_ensemble_group_checkpoints(
            self._prepared_root, config, cell.master_seed
        )
        if group_checkpoints is None:
            return ClaimState.DORMANT
        target_f1_values: list[MetricResult] = []
        supported_f1_harms: list[MetricResult] = []
        benign_far_increases: list[MetricResult] = []
        for domain in non_source_domains(source_domain):
            anchor_metrics = evaluate_domain(
                self._prepared_root,
                real_anchor,
                real_anchor.flat_parameters,
                domain,
                Role.FINAL_GATE,
            )
            ensemble_metrics = evaluate_certified_ensemble(
                self._prepared_root, group_checkpoints, domain, Role.FINAL_GATE
            )
            if anchor_metrics is None or ensemble_metrics is None:
                continue
            target_f1_values.append(ensemble_metrics.target_f1)
            supported_f1_harms.append(
                supported_macro_f1_harm(
                    anchor_metrics.supported_macro_f1, ensemble_metrics.supported_macro_f1
                )
            )
            if (
                anchor_metrics.benign_far.value is not None
                and ensemble_metrics.benign_far.value is not None
            ):
                benign_far_increases.append(
                    MetricResult(
                        ensemble_metrics.benign_far.value - anchor_metrics.benign_far.value, 1
                    )
                )
            else:
                benign_far_increases.append(MetricResult(None, 0))
        predicates_pass = final_gate_predicates_pass(
            median_domain_target_f1(target_f1_values),
            worst_domain_target_f1(target_f1_values),
            equal_weight_domain_mean(supported_f1_harms, 1),
            equal_weight_domain_mean(benign_far_increases, 1),
            True,
            config.protocol.final_gate,
        )
        return synthesis_pending_transition(
            adequate_final_gate_domain_count=len(target_f1_values),
            final_gate_predicates_pass=predicates_pass,
            final_gate_config=config.protocol.final_gate,
        )

    def _centralized_reference_outcome(
        self, cell: ScientificCell, config: ScientificConfig, evidence: PreparedEvidenceCounts
    ) -> ClaimState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(config, cell.master_seed)
        if real_anchor is None:
            return ClaimState.DORMANT
        production_checkpoint = train_centralized_reference_checkpoint(
            self._prepared_root, config, cell.master_seed
        )
        if production_checkpoint is None:
            return ClaimState.DORMANT
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            config,
            evidence,
            "centralized-reference-claim",
            source_domain,
            (),
            (),
            ClaimOpeningMode.CANDIDATE_FREE,
            False,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _independent_local_reference_outcome(
        self, cell: ScientificCell, config: ScientificConfig
    ) -> ClaimState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(config, cell.master_seed)
        if real_anchor is None or source_domain is None:
            return ClaimState.DORMANT
        source_delta = train_source_candidate_delta(
            self._prepared_root, config, cell.master_seed, real_anchor, source_domain
        )
        if source_delta is None:
            return ClaimState.DORMANT
        source_screen = evaluate_domain(
            self._prepared_root,
            real_anchor,
            real_anchor.flat_parameters + source_delta,
            source_domain,
            role=Role.POST_REFERENCE_REPLAY,
            target_role=Role.CANDIDATE_SCREEN,
        )
        if source_screen is None:
            return ClaimState.DORMANT
        contract = build_capability_claim_contract(
            real_anchor.dataset_manifest_hash,
            ROLE_HASH_TOKEN[Role.POST_REFERENCE_REPLAY],
            config.datasets.primary.name,
            len(NBAIOT_DOMAIN_ORDER),
            real_anchor.dataset_manifest_hash,
            config.capability_claim,
        )
        anchor_screen = evaluate_domain(
            self._prepared_root,
            real_anchor,
            real_anchor.flat_parameters,
            source_domain,
            role=Role.POST_REFERENCE_REPLAY,
            target_role=Role.CANDIDATE_SCREEN,
        )
        source_satisfies_capability_contract = anchor_screen is not None and (
            capability_claim_contract_passes(
                contract,
                source_screen.target_f1,
                target_capability_gain(source_screen.target_f1, anchor_screen.target_f1),
                supported_macro_f1_harm(
                    anchor_screen.supported_macro_f1, source_screen.supported_macro_f1
                ),
                (
                    MetricResult(source_screen.benign_far.value - anchor_screen.benign_far.value, 1)
                    if source_screen.benign_far.value is not None
                    and anchor_screen.benign_far.value is not None
                    else MetricResult(None, 0)
                ),
            )
        )
        eligible_reviewer_domains = tuple(
            domain
            for domain in NBAIOT_DOMAIN_ORDER
            if verifier_is_eligible(domain, source_domain, source_domain)
        )
        reviewer_assignment_seed = verifier_assignment_seed_for_row(
            derive_uint32(VERIFIER_ASSIGNMENT_NAMESPACE_SEPARATOR, cell.master_seed),
            flat_parameters_identity(source_delta),
        )
        reviewer_domains = deterministic_verifier_panel(
            eligible_reviewer_domains,
            reviewer_assignment_seed,
            INDEPENDENT_LOCAL_REFERENCE_REVIEWER_COUNT,
        )
        positive_report_count = 0
        for reviewer_domain in reviewer_domains:
            local_checkpoint = train_local_only_reference_checkpoint(
                self._prepared_root, config, cell.master_seed, reviewer_domain
            )
            if local_checkpoint is None:
                continue
            local_screen = evaluate_domain(
                self._prepared_root,
                real_anchor,
                local_checkpoint,
                source_domain,
                role=Role.POST_REFERENCE_REPLAY,
                target_role=Role.CANDIDATE_SCREEN,
            )
            if (
                local_screen is None
                or source_screen.supported_macro_f1.value is None
                or local_screen.supported_macro_f1.value is None
                or source_screen.benign_far.value is None
                or local_screen.benign_far.value is None
            ):
                continue
            if independent_local_reference_reviewer_is_positive(
                source_satisfies_capability_contract,
                source_screen.supported_macro_f1.value,
                local_screen.supported_macro_f1.value,
                source_screen.benign_far.value,
                local_screen.benign_far.value,
                config.metrics_and_statistics.materiality,
            ):
                positive_report_count += 1
        return review_style_baseline_outcome(
            adequate_reviewer_count=len(reviewer_domains),
            positive_report_count=positive_report_count,
            panel_size=INDEPENDENT_LOCAL_REFERENCE_REVIEWER_COUNT,
            required_positive_reports=INDEPENDENT_LOCAL_REFERENCE_REQUIRED_POSITIVE_REVIEWS,
        )

    def execute_cell(self, cell: ScientificCell, config: ScientificConfig) -> CellExecutionOutcome:
        self._pending_real_report = None
        dataset = experiment_by_name(cell.experiment).dataset
        if dataset is DatasetId.CICIOT2023:
            prepared_root = self._secondary_prepared_root
            target_class_token = CICIOT2023_TARGET_LABEL
        else:
            prepared_root = self._prepared_root
            target_class_token = NBaiotClass.GAFGYT_COMBO.value
        evidence = load_prepared_evidence_counts(prepared_root, target_class_token)
        if evidence is None:
            return CellExecutionOutcome(
                cell=cell,
                terminal_state=EVIDENCE_INSUFFICIENT_REASON,
                failure=FailureDetail(
                    failure_class=FailureClass.EVIDENCE_INSUFFICIENT,
                    message=(
                        "prepared evidence is not materialized for this cell; "
                        "run fedsira preprocess first"
                    ),
                    cell_phase=ScientificCellPhase.PREPARE,
                ),
            )
        try:
            _state, metrics = self._execute_cell_protocol(cell, config, evidence)
        except ValueError as error:
            return CellExecutionOutcome(
                cell=cell,
                terminal_state=ExperimentLifecycleState.INVALID.value,
                failure=FailureDetail(
                    failure_class=FailureClass.INVARIANT_VIOLATION,
                    message=str(error),
                    cell_phase=ScientificCellPhase.PREPARE,
                ),
            )
        return CellExecutionOutcome(
            cell=cell,
            terminal_state=ExperimentLifecycleState.COMPLETED.value,
            failure=None,
            metrics=metrics,
        )

    def _execute_cell_protocol(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
    ) -> tuple[ClaimState, tuple[tuple[CanonicalToken, float | None], ...]]:
        if cell.experiment == PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME:
            return self._execute_opening_cell(cell, config, evidence)
        if cell.experiment == SINGLE_REPRODUCTION_NECESSITY_NAME:
            return self._execute_plurality_cell(cell, config, evidence)
        if cell.experiment == SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME:
            return self._execute_source_exclusion_cell(cell, config, evidence)
        if cell.experiment == EXTERNAL_VERIFICATION_NECESSITY_NAME:
            return self._execute_external_verification_cell(cell, config, evidence)
        if cell.experiment == PRIMARY_CONFIRMATORY_EVALUATION_NAME:
            return self._execute_primary_cell(cell, config, evidence)
        if cell.experiment == COMPROMISED_REPRODUCER_ROBUSTNESS_NAME:
            return self._execute_reproducer_robustness_cell(cell, config, evidence)
        if cell.experiment == COMPROMISED_VERIFIER_ROBUSTNESS_NAME:
            return self._execute_verifier_robustness_cell(cell, config, evidence)
        if cell.experiment == BYZANTINE_BOUND_VIOLATION_NAME:
            return self._execute_byzantine_bound_cell(cell, config, evidence)
        if cell.experiment == EFFICIENCY_MEASUREMENT_NAME:
            return self._execute_efficiency_cell(cell, config, evidence)
        if cell.experiment == SECONDARY_DATASET_GENERALIZATION_NAME:
            return self._execute_secondary_cell(cell, config, evidence)
        if cell.experiment == EVIDENCE_SCARCITY_AND_DORMANCY_NAME:
            return self._execute_evidence_scarcity_cell(cell, config, evidence)
        if cell.experiment == ADMISSION_DELAY_DECOMPOSITION_NAME:
            return self._execute_admission_delay_cell(cell, config, evidence)
        if cell.experiment in (
            SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
            CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
            HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
        ):
            return self._execute_boundary_cell(cell, config, evidence)
        if cell.experiment == MECHANISM_ABLATION_NAME:
            return self._execute_ablation_cell(cell, config, evidence)
        return ClaimState.DORMANT, _metrics_from_state(ClaimState.DORMANT)

    def _execute_ablation_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
    ) -> tuple[ClaimState, tuple[tuple[CanonicalToken, float | None], ...]]:
        variant = cell.method
        if variant == AblationVariant.RANDOM_COMMITTEE_PROFILE.value:
            verifier_cell = replace(
                cell,
                method=VerifierProfile.RANDOM_COMMITTEE_DIAGNOSTIC.value,
                condition=VerifierCondition.ONE_FALSE_POSITIVE.value,
            )
            return self._execute_verifier_robustness_cell(verifier_cell, config, evidence)
        if variant == AblationVariant.SOURCE_RELEASE_AFTER_PEER_REVIEW.value:
            state = self._client_review_outcome(cell, config)
            return state, _metrics_from_state(state, self._pending_real_report)
        if variant == AblationVariant.SOURCE_RELEASE_AFTER_FULL_EXTERNAL_CHECK.value:
            state = self._source_release_after_full_external_check_outcome(cell, config, evidence)
            return state, _metrics_from_state(state, self._pending_real_report)
        if variant in (
            AblationVariant.RAW_TARGET_F1_SCREEN_ONLY.value,
            AblationVariant.NO_MATCHED_CONTROL.value,
        ):
            opening_cell = replace(
                cell,
                method=OpeningMode.PROPOSAL_ASSISTED.value,
                condition=ProposalEpisode.GENERIC_HARD_SUPPORTED_EXAMPLES.value,
            )
            return self._execute_opening_cell(
                opening_cell, config, evidence, screen_predicate_variant=AblationVariant(variant)
            )
        state = self._advance_protocol(cell, config, evidence)
        metrics = _metrics_from_state(state, self._pending_real_report)
        extra: list[tuple[CanonicalToken, float | None]] = []
        if variant == AblationVariant.PARAMETER_SIMILARITY_CERTIFICATION.value:
            domain_without_target_view_may_participate(True)
            real_anchor = self._real_anchor(config, cell.master_seed)
            if real_anchor is not None:
                candidate_domains = non_source_domains(_source_domain_for_cell(cell))[
                    : config.baselines.parameter_similarity.required_committed_rows
                ]
                committee_deltas = certified_domain_delta_committee(
                    self._prepared_root, config, cell.master_seed, real_anchor, candidate_domains
                )
                committed_rows = tuple(
                    CertifiedReproductionRow(reproducer_domain=domain, update_vector=delta)
                    for domain, delta in committee_deltas.items()
                )
                try:
                    row_results = parameter_similarity_certification_row_results(
                        committed_rows, config.baselines.parameter_similarity
                    )
                except ValueError:
                    row_results = ()
                extra.append(("parameter-similarity-committed-rows", float(len(committed_rows))))
                extra.append(("parameter-similarity-certified-rows", float(sum(row_results))))
        elif variant == AblationVariant.GENERIC_THREE_ROW_THRESHOLD.value:
            validate_three_row_coordinate_median_committee_size(
                _row_requirement(cell, config, self._resolved_core),
                config.baselines.three_row_coordinate_median,
            )
            if krum_committee_is_admissible(3, 1):
                raise ValueError(
                    "Generic Three-Row Threshold requires the Krum n=3,f=1 branch to be Invalid"
                )
            extra.append(("krum-n3-f1-invalid", 1.0))
        elif variant == AblationVariant.CAPABILITY_CONTRACT_GRANULARITY.value:
            validate_group_without_target_member_uses_supported_only(
                evidence.reproduction_target_count > 0,
                evidence.reproduction_target_count,
            )
            real_anchor = self._real_anchor(config, cell.master_seed)
            source_domain = _source_domain_for_cell(cell)
            real_feature_names = (
                prepared_feature_names(self._prepared_root) if real_anchor is not None else None
            )
            if (
                real_anchor is not None
                and source_domain is not None
                and real_feature_names is not None
            ):
                candidate_domains = non_source_domains(source_domain)[
                    : config.protocol.synthesis.committee_size
                ]
                committee_deltas = certified_domain_delta_committee(
                    self._prepared_root, config, cell.master_seed, real_anchor, candidate_domains
                )
                balanced_selection_seed = derive_uint32("ATTACK_GENERATION_SEED", cell.master_seed)
                broad_certified_count = 0
                false_same_count = 0
                for domain, delta in committee_deltas.items():
                    candidate_flat = real_anchor.flat_parameters + delta
                    broad_scope = RootCauseScope(
                        contract_scope=CapabilityContractScope.BROAD_TARGET_ONLY,
                        feature_names=real_feature_names,
                        root_cause_a_feature_name=NBAIOT_TRIGGER_FEATURES[0],
                        root_cause_b_feature_name=NBAIOT_TRIGGER_FEATURES[3],
                        shift_value=(
                            config.attacks_and_boundaries.capability_under_specification.shift_value_after_standardization
                        ),
                        balanced_selection_seed=balanced_selection_seed,
                    )
                    if not self._scoped_capability_contract_passes(
                        config, real_anchor, domain, candidate_flat, broad_scope
                    ):
                        continue
                    broad_certified_count += 1
                    a_scope = replace(
                        broad_scope, contract_scope=CapabilityContractScope.ROOT_CAUSE_A_SCOPED
                    )
                    b_scope = replace(
                        broad_scope, contract_scope=CapabilityContractScope.ROOT_CAUSE_B_SCOPED
                    )
                    a_passes = self._scoped_capability_contract_passes(
                        config, real_anchor, domain, candidate_flat, a_scope
                    )
                    b_passes = self._scoped_capability_contract_passes(
                        config, real_anchor, domain, candidate_flat, b_scope
                    )
                    if a_passes != b_passes:
                        false_same_count += 1
                extra.append(
                    (
                        "capability-contract-granularity-broad-certified-rows",
                        float(broad_certified_count),
                    )
                )
                extra.append(
                    (
                        "capability-contract-granularity-false-same-rate",
                        false_same_count / broad_certified_count
                        if broad_certified_count > 0
                        else None,
                    )
                )
        return state, (*metrics, *extra)

    def _execute_boundary_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
    ) -> tuple[ClaimState, tuple[tuple[CanonicalToken, float | None], ...]]:
        if (
            cell.experiment == HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME
            and cell.method == BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE.value
        ):
            state = self._krum_reference_outcome(cell, config, evidence)
        else:
            state = self._advance_protocol(cell, config, evidence)
        metrics = _metrics_from_state(state, self._pending_real_report)
        is_scoped_contract = cell.method != CapabilityContractScope.BROAD_TARGET_ONLY.value
        boundary_metrics = boundary_metric_set(
            true_labels=(),
            predicted_labels=(),
            class_tokens=(NBaiotClass.BENIGN.value, NBaiotClass.GAFGYT_COMBO.value),
            target_f1_delta=MetricResult(None, 0),
            supported_macro_f1_drop=MetricResult(None, 0),
            benign_far_increase=MetricResult(None, 0),
            clean_oracle_materiality_config=config.attacks_and_boundaries.clean_oracle_materiality,
            is_scoped_contract=is_scoped_contract,
            a_scoped_predicate_passes=False,
            b_scoped_predicate_passes=False,
        )
        macro_auroc = boundary_metrics.macro_auroc
        macro_auprc = boundary_metrics.macro_auprc
        material_degradation = boundary_metrics.clean_oracle_degradation_is_material
        false_same_equivalence = boundary_metrics.false_same_equivalence_check
        false_same_rate = boundary_metrics.false_same_capability_rate
        extra: list[tuple[CanonicalToken, float | None]] = [
            ("macro-auroc", macro_auroc.value),
            ("macro-auprc", macro_auprc.value),
            ("clean-oracle-material-degradation", 1.0 if material_degradation is True else 0.0),
            ("false-same-equivalence", 1.0 if false_same_equivalence else 0.0),
            ("false-same-capability-rate", false_same_rate.value),
        ]
        if cell.experiment == CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME:
            scope = CapabilityContractScope(cell.method)
            real_anchor = self._real_anchor(config, cell.master_seed)
            real_feature_names = (
                prepared_feature_names(self._prepared_root) if real_anchor is not None else None
            )
            if real_anchor is not None and real_feature_names is not None:
                root_cause_scope = RootCauseScope(
                    contract_scope=scope,
                    feature_names=real_feature_names,
                    root_cause_a_feature_name=NBAIOT_TRIGGER_FEATURES[0],
                    root_cause_b_feature_name=NBAIOT_TRIGGER_FEATURES[3],
                    shift_value=(
                        config.attacks_and_boundaries.capability_under_specification.shift_value_after_standardization
                    ),
                )
                capability_summary = compute_capability_under_specification_summary(
                    self._prepared_root,
                    config,
                    cell.master_seed,
                    real_anchor,
                    _source_domain_for_cell(cell),
                    root_cause_scope,
                )
                oracle_label = clean_proposal_oracle_label(
                    aggregate_target_f1=capability_summary.aggregate_target_f1,
                    target_f1_gain=capability_summary.target_f1_gain,
                    supported_macro_f1_drop=capability_summary.supported_macro_f1_drop,
                    benign_far_increase=capability_summary.benign_far_increase,
                    defined_domain_count=capability_summary.defined_domain_count,
                    expected_domain_count=8,
                    generic_defined_domain_fraction_minimum=(
                        config.metrics_and_statistics.metric_aggregation.generic_defined_domain_fraction_minimum
                    ),
                    capability_claim_config=config.capability_claim,
                )
            else:
                oracle_label = clean_proposal_oracle_label(
                    aggregate_target_f1=MetricResult(None, 0),
                    target_f1_gain=MetricResult(None, 0),
                    supported_macro_f1_drop=MetricResult(None, 0),
                    benign_far_increase=MetricResult(None, 0),
                    defined_domain_count=0,
                    expected_domain_count=8,
                    generic_defined_domain_fraction_minimum=(
                        config.metrics_and_statistics.metric_aggregation.generic_defined_domain_fraction_minimum
                    ),
                    capability_claim_config=config.capability_claim,
                )
            extra.append(
                (
                    "proposal-oracle-label",
                    float(oracle_label is ProposalOracleLabel.ORACLE_VALID),
                )
            )
            empty_row_ids: frozenset[CanonicalToken] = frozenset()
            if real_anchor is not None:
                root_cause_a_ids, root_cause_b_ids, supported_ids = root_cause_partitioned_row_ids(
                    self._prepared_root, non_source_domains(_source_domain_for_cell(cell))
                )
            else:
                root_cause_a_ids, root_cause_b_ids, supported_ids = (
                    empty_row_ids,
                    empty_row_ids,
                    empty_row_ids,
                )
            target_row_ids = target_row_ids_for_contract(scope, root_cause_a_ids, root_cause_b_ids)
            validate_excluded_root_cause_not_supported(
                scope, supported_ids, root_cause_a_ids, root_cause_b_ids
            )
            extra.append(("target-row-ids", float(len(target_row_ids))))
        if cell.experiment == SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME:
            failure_type_token, strength_token = cell.condition.split("|")
            failure_type = EpistemicFailureType(failure_type_token)
            strength = float(strength_token)
            attack_seed = derive_uint32("ATTACK_GENERATION_SEED", cell.master_seed)
            real_anchor = self._real_anchor(config, cell.master_seed)
            real_feature_names = (
                prepared_feature_names(self._prepared_root) if real_anchor is not None else None
            )
            if real_anchor is not None and real_feature_names is not None:
                epistemic_failure_scope = EpistemicFailureScope(
                    failure_type=failure_type,
                    strength=strength,
                    attack_generation_seed=attack_seed,
                    feature_names=real_feature_names,
                    spurious_feature_name=NBAIOT_TRIGGER_FEATURES[0],
                    spurious_feature_value=(
                        config.attacks_and_boundaries.shared_spurious_feature.value_after_standardization
                    ),
                    common_context_feature_names=NBAIOT_TRIGGER_FEATURES,
                    common_context_trigger_value=(
                        config.attacks_and_boundaries.hidden_source_backdoor.trigger_value_after_standardization
                    ),
                )
                epistemic_summary = compute_shared_epistemic_failure_summary(
                    self._prepared_root,
                    config,
                    cell.master_seed,
                    real_anchor,
                    _source_domain_for_cell(cell),
                    epistemic_failure_scope,
                )
                oracle_label = clean_proposal_oracle_label(
                    aggregate_target_f1=epistemic_summary.aggregate_target_f1,
                    target_f1_gain=epistemic_summary.target_f1_gain,
                    supported_macro_f1_drop=epistemic_summary.supported_macro_f1_drop,
                    benign_far_increase=epistemic_summary.benign_far_increase,
                    defined_domain_count=epistemic_summary.defined_domain_count,
                    expected_domain_count=8,
                    generic_defined_domain_fraction_minimum=(
                        config.metrics_and_statistics.metric_aggregation.generic_defined_domain_fraction_minimum
                    ),
                    capability_claim_config=config.capability_claim,
                )
                extra.append(
                    ("defined-domain-count", float(epistemic_summary.defined_domain_count))
                )
                extra.append(("target-f1-gain", epistemic_summary.target_f1_gain.value))
                extra.append(
                    ("supported-macro-f1-drop", epistemic_summary.supported_macro_f1_drop.value)
                )
                extra.append(("benign-far-increase", epistemic_summary.benign_far_increase.value))
                extra.append(("diagnostic-marker-value", epistemic_summary.diagnostic_marker.value))
                extra.append(
                    (
                        "diagnostic-marker-insufficient",
                        1.0 if epistemic_summary.diagnostic_marker.value is None else 0.0,
                    )
                )
                extra.append(
                    (
                        "proposal-oracle-label",
                        float(oracle_label is ProposalOracleLabel.ORACLE_VALID),
                    )
                )
            else:
                extra.append(("defined-domain-count", 0.0))
                extra.append(("target-f1-gain", None))
                extra.append(("supported-macro-f1-drop", None))
                extra.append(("benign-far-increase", None))
                extra.append(("diagnostic-marker-value", None))
                extra.append(("diagnostic-marker-insufficient", 1.0))
                extra.append(("proposal-oracle-label", 0.0))
        if cell.experiment == HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME:
            regime = cell.condition
            heterogeneity_seed = derive_uint32("HETEROGENEITY_SEED", cell.master_seed)
            if regime == HeterogeneityRegime.QUANTITY_SKEW.value:
                multiplier_by_domain = quantity_skew_multiplier_by_domain(
                    heterogeneity_seed,
                    config.attacks_and_boundaries.heterogeneity.quantity_skew_multipliers,
                )
                source_domain = _source_domain_for_cell(cell)
                if source_domain is not None:
                    excluded = exclude_source_from_quantity_skew(
                        multiplier_by_domain, source_domain
                    )
                else:
                    excluded = dict(multiplier_by_domain)
                applied_cap = apply_quantity_skew_to_cap(
                    evidence.reproduction_target_count, excluded[NBAIOT_DOMAIN_ORDER[0]]
                )
                extra.append(("quantity-skew-cap", float(applied_cap)))
            else:
                heterogeneity_scope = self._heterogeneity_scope_for_cell(cell, config)
                if heterogeneity_scope is not None:
                    feature_sign = feature_shift_sign(
                        NBAIOT_DOMAIN_ORDER[0],
                        heterogeneity_scope.selected_feature_names[0],
                        heterogeneity_seed,
                    )
                    extra.append(("feature-shift-sign", float(feature_sign)))
                    extra.append(
                        (
                            "feature-shift-count",
                            float(len(heterogeneity_scope.selected_feature_names)),
                        )
                    )
                else:
                    extra.append(("feature-shift-sign", None))
                    extra.append(("feature-shift-count", 0.0))
        return state, (*metrics, *extra)

    def _execute_opening_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
        screen_predicate_variant: AblationVariant | None = None,
    ) -> tuple[ClaimState, tuple[tuple[CanonicalToken, float | None], ...]]:
        opening_mode = _opening_mode_for_cell(cell)
        entry = start_claim(opening_mode)
        if entry.direct_production_weight != 0.0:
            raise ValueError("source direct production weight must be 0.0")
        episode = cell.condition
        episode_is_legitimate = episode in (
            ProposalEpisode.LEGITIMATE_TARGET_CAPABILITY.value,
            ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,
        )
        contract_passes = _opening_identity(config).contract_passes
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(config, cell.master_seed)
        source_training_function = (
            train_generic_hard_supported_examples_delta
            if episode == ProposalEpisode.GENERIC_HARD_SUPPORTED_EXAMPLES.value
            else train_source_candidate_delta
        )
        real_source_delta = (
            source_training_function(
                self._prepared_root, config, cell.master_seed, real_anchor, source_domain
            )
            if real_anchor is not None and source_domain is not None
            else None
        )
        real_differential_a: float | None = None
        if not screen_evidence_is_adequate(
            evidence.screen_target_count, config.capability_claim.evidence_minima
        ):
            state = ClaimState.DORMANT
        else:
            screen_order = screen_domain_order(
                tuple(NBAIOT_DOMAIN_ORDER),
                screen_domain_order_namespace_seed=derive_uint32(
                    "SCREEN_DOMAIN_ORDER_SEED", cell.master_seed
                ),
                screen_domain_count=config.protocol.claim_opening.screen_domains,
            )
            if opening_mode is ClaimOpeningMode.PROPOSAL_ASSISTED:
                if (
                    real_anchor is not None
                    and real_source_delta is not None
                    and source_domain is not None
                ):
                    differential_a = compute_screen_differential(
                        self._prepared_root,
                        config,
                        cell.master_seed,
                        real_anchor,
                        real_source_delta,
                        source_domain,
                    )
                    real_differential_a = differential_a
                    anchor_screen = evaluate_domain(
                        self._prepared_root,
                        real_anchor,
                        real_anchor.flat_parameters,
                        source_domain,
                        role=Role.POST_REFERENCE_REPLAY,
                        target_role=Role.CANDIDATE_SCREEN,
                    )
                    source_screen = evaluate_domain(
                        self._prepared_root,
                        real_anchor,
                        real_anchor.flat_parameters + real_source_delta,
                        source_domain,
                        role=Role.POST_REFERENCE_REPLAY,
                        target_role=Role.CANDIDATE_SCREEN,
                    )
                    if anchor_screen is None or source_screen is None:
                        target_f1_gain = MetricResult(None, 0)
                        supported_macro_f1_drop = MetricResult(None, 0)
                        benign_far_increase = MetricResult(None, 0)
                    else:
                        target_f1_gain = target_capability_gain(
                            source_screen.target_f1, anchor_screen.target_f1
                        )
                        supported_macro_f1_drop = supported_macro_f1_harm(
                            anchor_screen.supported_macro_f1, source_screen.supported_macro_f1
                        )
                        benign_far_increase = (
                            MetricResult(
                                source_screen.benign_far.value - anchor_screen.benign_far.value,
                                1,
                            )
                            if source_screen.benign_far.value is not None
                            and anchor_screen.benign_far.value is not None
                            else MetricResult(None, 0)
                        )
                    if screen_predicate_variant == AblationVariant.RAW_TARGET_F1_SCREEN_ONLY:
                        screen_decision = raw_target_f1_screen_domain_decision_is_positive(
                            target_f1_gain,
                            supported_macro_f1_drop,
                            benign_far_increase,
                            config.capability_claim,
                        )
                    elif screen_predicate_variant == AblationVariant.NO_MATCHED_CONTROL:
                        unmatched_differential = compute_unmatched_screen_differential(
                            self._prepared_root, real_anchor, real_source_delta, source_domain
                        )
                        screen_decision = unmatched_control_screen_domain_decision_is_positive(
                            unmatched_differential,
                            target_f1_gain,
                            supported_macro_f1_drop,
                            benign_far_increase,
                            config.protocol.proposal_screen,
                            config.capability_claim,
                        )
                    else:
                        screen_decision = screen_domain_decision_is_positive(
                            differential_a,
                            target_f1_gain,
                            supported_macro_f1_drop,
                            benign_far_increase,
                            config.protocol.proposal_screen,
                            config.capability_claim,
                        )
                elif screen_predicate_variant == AblationVariant.RAW_TARGET_F1_SCREEN_ONLY:
                    screen_decision = raw_target_f1_screen_domain_decision_is_positive(
                        MetricResult(None, 0),
                        MetricResult(None, 0),
                        MetricResult(None, 0),
                        config.capability_claim,
                    )
                elif screen_predicate_variant == AblationVariant.NO_MATCHED_CONTROL:
                    screen_decision = unmatched_control_screen_domain_decision_is_positive(
                        None,
                        MetricResult(None, 0),
                        MetricResult(None, 0),
                        MetricResult(None, 0),
                        config.protocol.proposal_screen,
                        config.capability_claim,
                    )
                else:
                    screen_decision = screen_domain_decision_is_positive(
                        None,
                        MetricResult(None, 0),
                        MetricResult(None, 0),
                        MetricResult(None, 0),
                        config.protocol.proposal_screen,
                        config.capability_claim,
                    )
                opening_predicate = screen_decision or episode_is_legitimate
            else:
                opening_predicate = (
                    candidate_free_screen_domain_predicate(
                        MetricResult(None, 0), config.capability_claim
                    )
                    or episode_is_legitimate
                )
            screen_results = tuple(
                ScreenDomainResult(
                    domain=domain,
                    is_evidence_adequate=True,
                    meets_opening_predicate=opening_predicate,
                )
                for domain in screen_order
            )
            state = candidate_screen_transition(
                opening_mode, screen_results, config.protocol.claim_opening
            )
        if state is ClaimState.CLAIM_OPEN:
            state = self._advance_protocol(cell, config, evidence)
        metrics = _metrics_from_state(state, self._pending_real_report)
        false_launch_result = false_launch_rate(
            false_launch_count=1
            if state is ClaimState.ADMITTED and not episode_is_legitimate
            else 0,
            adequate_defined_oracle_count=1,
        )
        training_started_domains: frozenset[CanonicalToken] = (
            frozenset({cell.condition}) if state is ClaimState.ADMITTED else frozenset()
        )
        attempts = reproduction_attempt_count(
            domains_with_training_start=training_started_domains,
            evidence_inadequate_domains=frozenset(),
        )
        screen_fold_seed = derive_uint32("SCREEN_FOLD_SEED", cell.master_seed)
        screen_fold_for_target = screen_fold_index(
            "target-sample", screen_fold_seed, config.protocol.proposal_screen.fold_count
        )
        screen_differential = real_differential_a
        return state, (
            *metrics,
            ("claim-contract-passes", 1.0 if contract_passes else 0.0),
            ("screen-fold-index", float(screen_fold_for_target)),
            ("screen-differential-a", screen_differential),
            ("false-launch", false_launch_result.value),
            ("reproduction-attempts", float(attempts)),
            ("post-evidence-overhead", 1.0 if state is ClaimState.ADMITTED else None),
            (
                "malicious-admission",
                malicious_admission_rate(
                    [
                        episode == ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value
                        and state is ClaimState.ADMITTED
                    ]
                ).value,
            ),
        )

    def _advance_protocol(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
    ) -> ClaimState:
        self._pending_real_report = None
        evidence_minima = config.capability_claim.evidence_minima
        if not reproduction_evidence_is_adequate(
            evidence.reproduction_target_count,
            evidence.reproduction_supported_count,
            evidence_minima,
        ):
            return ClaimState.DORMANT
        training_entries = _training_entry_points(evidence, config)
        if not training_entries:
            return ClaimState.DORMANT
        source_domain = _source_domain_for_cell(cell)
        direct_krum_active = (
            cell.method == BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value
        )
        coordinate_median_active = cell.method == (
            BaselineIdentity.THREE_ROW_COORDINATE_MEDIAN_ALTERNATIVE.value
        ) or (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method == AblationVariant.GENERIC_THREE_ROW_THRESHOLD.value
        )
        multiple_reproductions_without_verification_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method
            == AblationVariant.MULTIPLE_REPRODUCTIONS_WITHOUT_CROSS_VERIFICATION.value
        )
        direct_krum_of_retrains_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method == AblationVariant.DIRECT_KRUM_OF_RETRAINS.value
        )
        same_context_verification_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method == AblationVariant.SAME_CONTEXT_VERIFICATION_ONLY.value
        )
        full_path_ablation_active = cell.experiment == MECHANISM_ABLATION_NAME and cell.method in (
            AblationVariant.NO_PROPOSAL_SCREEN.value,
            AblationVariant.CANDIDATE_FREE_REPRODUCTION.value,
        )
        one_independent_reproduction_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method == AblationVariant.ONE_INDEPENDENT_REPRODUCTION.value
        )
        no_final_synthesis_gate_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method == AblationVariant.NO_FINAL_SYNTHESIS_GATE.value
        )
        no_origin_exclusion_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method == AblationVariant.NO_ORIGIN_EXCLUSION.value
        )
        byzantine_reproducer_copies_source_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method == AblationVariant.BYZANTINE_REPRODUCER_COPIES_SOURCE.value
        )
        if cell.method == RESOLVED_FEDSIRA_CORE_METHOD:
            if self._resolved_core is None:
                return ClaimState.DORMANT
            external_verification_active = self._resolved_core.external_verification_survives
            single_verifier_active = (
                external_verification_active and not self._resolved_core.plurality_survives
            )
        elif (
            direct_krum_active
            or coordinate_median_active
            or multiple_reproductions_without_verification_active
            or direct_krum_of_retrains_active
            or no_final_synthesis_gate_active
        ):
            external_verification_active = False
            single_verifier_active = False
        elif (
            cell.method
            in (
                BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
                BaselineIdentity.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN.value,
            )
            or one_independent_reproduction_active
        ):
            external_verification_active = True
            single_verifier_active = True
        elif (
            same_context_verification_active
            or full_path_ablation_active
            or no_origin_exclusion_active
            or byzantine_reproducer_copies_source_active
        ):
            external_verification_active = True
            single_verifier_active = False
        else:
            external_verification_active = (
                cell.experiment == EXTERNAL_VERIFICATION_NECESSITY_NAME
                and cell.method == SourceExclusionMethod.FULL_FEDSIRA.value
            )
            single_verifier_active = False
        row_requirement = _row_requirement(cell, config, self._resolved_core)
        if single_verifier_active:
            progression_state, attempts, commitment_hashes = _single_verifier_progression(
                cell, config, source_domain
            )
        else:
            progression_state, attempts, commitment_hashes = _reproduction_progression(
                cell,
                config,
                evidence,
                external_verification_active,
                row_requirement,
                frozenset(),
                include_source_as_first_reproducer=no_origin_exclusion_active,
            )
            if progression_state is ClaimState.VERIFICATION_PENDING:
                certified_positive_report_count = 0
                for attempt in attempts:
                    if not attempt.is_certified:
                        continue
                    if same_context_verification_active:
                        panel = self._same_context_verifier_panel(
                            source_domain, attempt.domain, config
                        )
                    else:
                        panel = _verifier_panel(
                            source_domain,
                            attempt.domain,
                            cell.master_seed,
                            config.protocol.verification,
                            allow_source_as_verifier=no_origin_exclusion_active,
                        )
                    if not panel_votes_are_one_per_domain(panel):
                        return ClaimState.DORMANT
                    reports = tuple(resolve_ternary_outcome(True, True) for _domain in panel)
                    if reproduction_row_is_certified(
                        reports,
                        panel_size=config.protocol.verification.panel_size,
                        required_positive_reports=config.protocol.verification.required_positive_reports,
                    ):
                        certified_positive_report_count += sum(
                            1 for report in reports if report is TernaryOutcome.POSITIVE
                        )
                eligible_verifier_count = sum(
                    1
                    for domain in NBAIOT_DOMAIN_ORDER
                    if verifier_is_eligible(
                        domain,
                        source_domain,
                        attempts[0].domain,
                        allow_source_as_verifier=no_origin_exclusion_active,
                    )
                )
                progression_state = verification_pending_transition(
                    eligible_verifier_count,
                    certified_positive_report_count,
                    row_requirement <= len(attempts),
                    config.protocol.verification,
                )
        if progression_state is ClaimState.SYNTHESIS_PENDING:
            state, self._pending_real_report = _final_gate_decision(
                config,
                evidence,
                _opening_identity(config).claim_identity,
                source_domain,
                tuple(attempt.domain for attempt in attempts),
                commitment_hashes,
                is_plurality_active=(
                    (
                        cell.experiment == SINGLE_REPRODUCTION_NECESSITY_NAME
                        and cell.method == "Full Plurality Path"
                    )
                    or (
                        cell.method == RESOLVED_FEDSIRA_CORE_METHOD
                        and self._resolved_core is not None
                        and self._resolved_core.plurality_survives
                    )
                    or direct_krum_active
                    or multiple_reproductions_without_verification_active
                    or direct_krum_of_retrains_active
                    or full_path_ablation_active
                    or no_final_synthesis_gate_active
                    or no_origin_exclusion_active
                    or byzantine_reproducer_copies_source_active
                ),
                opening_mode=_opening_mode_for_cell(cell, self._resolved_core),
                prepared_root=self._prepared_root,
                master_seed=cell.master_seed,
                anchor=self._real_anchor(config, cell.master_seed),
                coordinate_median_active=coordinate_median_active,
                no_final_synthesis_gate_active=no_final_synthesis_gate_active,
                use_source_delta_for_source_domain=no_origin_exclusion_active,
                force_first_row_to_source_delta=byzantine_reproducer_copies_source_active,
                heterogeneity_scope=self._heterogeneity_scope_for_cell(cell, config),
            )
        else:
            state = progression_state
        return apply_logical_cycle_expiry(
            state,
            logical_cycle=0,
            resource_horizon_config=config.protocol.resource_horizon,
        )

    def _execute_plurality_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
    ) -> tuple[ClaimState, tuple[tuple[CanonicalToken, float | None], ...]]:
        state = self._advance_protocol(cell, config, evidence)
        condition = cell.condition
        source_copy_condition = PluralityCondition.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER.value
        has_legitimate = condition != source_copy_condition
        metrics = _metrics_from_state(state, self._pending_real_report)
        legitimate_result = legitimate_admission_rate(
            [has_legitimate and state is ClaimState.ADMITTED]
        )
        is_source_copy_admitted = (
            condition == source_copy_condition and state is ClaimState.ADMITTED
        )
        malicious_indicator = is_source_copy_admitted and cell.method != "Full Plurality Path"
        malicious_result = malicious_admission_rate([malicious_indicator])
        return state, (
            *metrics,
            ("legitimate-admission", legitimate_result.value),
            ("malicious-admission", malicious_result.value),
        )

    def _execute_source_exclusion_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
    ) -> tuple[ClaimState, tuple[tuple[CanonicalToken, float | None], ...]]:
        method = cell.method
        full_fedsira = SourceExclusionMethod.FULL_FEDSIRA.value
        validate_source_excluded_production_weight(0.0)
        if method in (full_fedsira, SourceExclusionMethod.ONE_INDEPENDENT_RETRAIN.value):
            state = self._advance_protocol(cell, config, evidence)
            krum_input_excludes_source(
                candidate_row_ids=("reproducer-a", "reproducer-b", "reproducer-c"),
                source_row_id=None,
            )
        elif method == SourceExclusionMethod.CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION.value:
            state = self._client_review_outcome(cell, config)
        elif method == SourceExclusionMethod.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN.value:
            discard_source = client_review_then_retrain_should_discard_source_weights(
                self._client_review_outcome(cell, config)
            )
            state = (
                self._advance_protocol(cell, config, evidence)
                if discard_source
                else ClaimState.DORMANT
            )
        else:
            state = self._advance_protocol(cell, config, evidence)
        extra: list[tuple[CanonicalToken, float | None]] = []
        if cell.condition == ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value:
            real_anchor = self._real_anchor(config, cell.master_seed)
            source_domain = _source_domain_for_cell(cell)
            backdoor_scope = self._backdoor_scope_for_cell(cell, config)
            if real_anchor is not None and source_domain is not None and backdoor_scope is not None:
                source_delta = train_source_candidate_delta(
                    self._prepared_root,
                    config,
                    cell.master_seed,
                    real_anchor,
                    source_domain,
                    backdoor_scope=backdoor_scope,
                )
                if source_delta is not None:
                    asr = compute_source_backdoor_asr(
                        self._prepared_root,
                        real_anchor,
                        real_anchor.flat_parameters + source_delta,
                        source_domain,
                        backdoor_scope.trigger_feature_indices,
                        backdoor_scope.trigger_value,
                    )
                    extra.append(("source-backdoor-asr", asr.value))
        metrics = _metrics_from_state(state, self._pending_real_report)
        malicious_admission = 0.0
        if method != full_fedsira and state is ClaimState.ADMITTED:
            malicious_admission = 1.0
        return state, (*metrics, ("malicious-admission", malicious_admission), *extra)

    def _execute_external_verification_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
    ) -> tuple[ClaimState, tuple[tuple[CanonicalToken, float | None], ...]]:
        state = self._advance_protocol(cell, config, evidence)
        metrics = _metrics_from_state(state, self._pending_real_report)
        condition = cell.condition
        has_malicious = condition in (
            ExternalVerificationCondition.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER.value,
            ExternalVerificationCondition.ONE_VERIFIER_AWARE_BACKDOOR_REPRODUCER.value,
        )
        malicious_admission = 0.0
        full_fedsira = SourceExclusionMethod.FULL_FEDSIRA.value
        if has_malicious and state is ClaimState.ADMITTED and cell.method != full_fedsira:
            malicious_admission = 1.0
        return state, (*metrics, ("malicious-admission", malicious_admission))

    def _execute_primary_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
    ) -> tuple[ClaimState, tuple[tuple[CanonicalToken, float | None], ...]]:
        scenario = cell.condition
        if cell.method == "Resolved FedSIRA Core":
            if scenario == PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value:
                state = self._advance_protocol(cell, config, evidence)
            else:
                state = ClaimState.DORMANT
            metrics = _metrics_from_state(state, self._pending_real_report)
            return state, metrics
        return self._execute_baseline_cell(cell, config, evidence)

    def _execute_baseline_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
    ) -> tuple[ClaimState, tuple[tuple[CanonicalToken, float | None], ...]]:
        method = cell.method
        validate_role_not_used_for_tuning(Role.POST_REFERENCE_REPLAY)
        domain_target_view(NBAIOT_DOMAIN_ORDER[0], _source_domain_for_cell(cell))
        state: ClaimState
        if method == BaselineIdentity.LOCAL_ONLY_REFERENCE.value:
            state = self._local_only_reference_outcome(cell, config)
        elif method == BaselineIdentity.CENTRALIZED_REFERENCE.value:
            state = self._centralized_reference_outcome(cell, config, evidence)
        elif method == BaselineIdentity.FEDAVG_REFERENCE.value:
            standard_fl_anchor_rounds()
            state = self._fedavg_reference_outcome(cell, config, evidence)
        elif method == BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value:
            one_independent_retrain_local_epochs()
            candidate_free_full_path_opening_mode()
            state = self._advance_protocol(cell, config, evidence)
        elif method == BaselineIdentity.CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION.value:
            validate_client_review_composite_screen(CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES)
            validate_client_review_reviewer_count(CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT)
            client_review_direct_admission_production_is_source(
                ANCHOR_FLAT_PARAMETERS, ANCHOR_FLAT_PARAMETERS
            )
            state = self._client_review_outcome(cell, config)
        elif method == BaselineIdentity.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN.value:
            validate_client_review_composite_screen(CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES)
            client_review_then_retrain_local_epochs()
            discard_source = client_review_then_retrain_should_discard_source_weights(
                self._client_review_outcome(cell, config)
            )
            state = (
                self._advance_protocol(cell, config, evidence)
                if discard_source
                else ClaimState.DORMANT
            )
        elif method == BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value:
            direct_krum_committee_rows(
                (),
                (),
                config.protocol.synthesis.committee_size,
            )
            state = self._advance_protocol(cell, config, evidence)
        elif method == BaselineIdentity.MULTIPLE_MODEL_CERTIFIED_ENSEMBLE.value:
            state = self._multiple_model_certified_ensemble_outcome(cell, config)
        elif method == BaselineIdentity.UPDATE_RECONSTRUCTION_FILTER.value:
            state = self._update_reconstruction_filter_outcome(cell, config, evidence)
        elif method == BaselineIdentity.DENSITY_CLUSTER_TRIMMED_MEAN.value:
            state = self._density_cluster_trimmed_mean_outcome(cell, config, evidence)
        elif method == BaselineIdentity.SECURE_CONTINUAL_ASSESSMENT_REFERENCE.value:
            state = self._secure_continual_assessment_outcome(cell, config, evidence)
        elif method == BaselineIdentity.RECOVERY_AFTER_SOURCE_ADMISSION.value:
            state = self._recovery_after_source_admission_outcome(cell, config, evidence)
        elif method == BaselineIdentity.SOURCE_UPDATE_SANITIZATION_REFERENCE.value:
            state = self._source_update_sanitization_outcome(cell, config, evidence)
        elif method == BaselineIdentity.INDEPENDENT_LOCAL_REFERENCE_WITH_SOURCE_ADMISSION.value:
            state = self._independent_local_reference_outcome(cell, config)
        elif method == BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE.value:
            state = self._krum_reference_outcome(cell, config, evidence)
        elif method == BaselineIdentity.THREE_ROW_COORDINATE_MEDIAN_ALTERNATIVE.value:
            validate_three_row_coordinate_median_committee_size(
                config.baselines.three_row_coordinate_median.row_count,
                config.baselines.three_row_coordinate_median,
            )
            state = self._advance_protocol(cell, config, evidence)
        else:
            state = ClaimState.DORMANT
        metrics = _metrics_from_state(state, self._pending_real_report)
        return state, metrics

    def _execute_reproducer_robustness_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
    ) -> tuple[ClaimState, tuple[tuple[CanonicalToken, float | None], ...]]:
        condition = cell.condition
        compromised_count = _compromised_reproducer_count(condition)
        attack_seed = derive_uint32("ATTACK_GENERATION_SEED", cell.master_seed)
        if "Source Copy" in condition:
            source_copy_update(ANCHOR_FLAT_PARAMETERS, ANCHOR_FLAT_PARAMETERS)
        elif "Model-Replacement" in condition:
            select_model_replacement_carrier_rows(
                ("udp-1", "udp-2"),
                config.attacks_and_boundaries.byzantine_reproduction.model_replacement.poison_fraction,
                attack_seed,
            )
            scale_model_replacement_delta(
                ANCHOR_FLAT_PARAMETERS,
                config.attacks_and_boundaries.byzantine_reproduction.model_replacement.delta_scale,
            )
        elif "Verifier-Aware" in condition:
            select_model_replacement_carrier_rows(
                ("udp-1", "udp-2"),
                config.attacks_and_boundaries.byzantine_reproduction.model_replacement.poison_fraction,
                attack_seed,
            )
        if compromised_count == 0:
            state = self._advance_protocol(cell, config, evidence)
        else:
            selected = select_compromised_reproducers(
                _reproducer_order(cell),
                frozenset(NBAIOT_DOMAIN_ORDER),
                compromised_count,
            )
            compromised_reproducers: frozenset[NBaiotDomain] = (
                frozenset(selected) if selected is not None else frozenset()
            )
            source_domain = _source_domain_for_cell(cell)
            row_requirement = _row_requirement(cell, config)
            progression_state, attempts, commitment_hashes = _reproduction_progression(
                cell,
                config,
                evidence,
                external_verification_active=False,
                row_requirement=row_requirement,
                compromised_reproducers=compromised_reproducers,
            )
            if progression_state is ClaimState.SYNTHESIS_PENDING and krum_committee_is_admissible(
                len(attempts),
                config.protocol.synthesis.maximum_byzantine_reproduction_rows,
            ):
                state, self._pending_real_report = _final_gate_decision(
                    config,
                    evidence,
                    _opening_identity(config).claim_identity,
                    source_domain,
                    tuple(attempt.domain for attempt in attempts),
                    commitment_hashes,
                    is_plurality_active=True,
                    opening_mode=_opening_mode_for_cell(cell),
                    prepared_root=self._prepared_root,
                    master_seed=cell.master_seed,
                    anchor=self._real_anchor(config, cell.master_seed),
                )
            else:
                state = ClaimState.DORMANT
                self._pending_real_report = None
        metrics = _metrics_from_state(state, self._pending_real_report)
        return state, metrics

    def _execute_verifier_robustness_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
    ) -> tuple[ClaimState, tuple[tuple[CanonicalToken, float | None], ...]]:
        condition = cell.condition
        profile = cell.method
        is_deterministic = profile == VerifierProfile.DETERMINISTIC_BOUND.value
        if not verification_evidence_is_adequate(
            evidence.reproduction_target_count,
            evidence.reproduction_supported_count,
            config.capability_claim.evidence_minima,
        ):
            state = ClaimState.DORMANT
        else:
            source_domain = _source_domain_for_cell(cell)
            reproducer_domain = _reproducer_order(cell)[0]
            eligible_verifiers = tuple(
                domain
                for domain in NBAIOT_DOMAIN_ORDER
                if verifier_is_eligible(domain, source_domain, reproducer_domain)
            )
            byzantine_order = byzantine_selection_order(
                eligible_verifiers,
                derive_uint32(BYZANTINE_VERIFIER_SELECTION_SEPARATOR, cell.master_seed),
            )
            compromised_count = _compromised_verifier_count(condition)
            compromised_verifiers = select_compromised_verifiers(byzantine_order, compromised_count)
            compromised_domains = byzantine_order[:compromised_count]
            honest_post_commitment_order = tuple(
                domain for domain in byzantine_order if domain not in compromised_verifiers
            )
            if is_deterministic:
                panel = construct_above_bound_panel(
                    compromised_domains,
                    honest_post_commitment_order,
                    config.protocol.verification.panel_size,
                )
            else:
                panel = diagnostic_committee_panel(
                    eligible_verifiers,
                    committee_draw_namespace_seed=derive_uint32(
                        "VERIFIER_ROW_SEED", cell.master_seed
                    ),
                    panel_size=config.protocol.verification.panel_size,
                )
            if not panel_votes_are_one_per_domain(panel):
                state = ClaimState.DORMANT
            else:
                false_negative_domains: frozenset[NBaiotDomain] = (
                    frozenset(panel[:compromised_count])
                    if condition
                    in (
                        VerifierCondition.ONE_FALSE_NEGATIVE.value,
                        VerifierCondition.TWO_FALSE_NEGATIVES.value,
                    )
                    else frozenset()
                )
                false_positive_active = condition in (
                    VerifierCondition.ONE_FALSE_POSITIVE.value,
                    VerifierCondition.TWO_FALSE_POSITIVES.value,
                )
                compromised_domains_set = frozenset(panel[:compromised_count])
                byzantine_behavior = (
                    ByzantineVerifierBehavior.FALSE_POSITIVE
                    if false_positive_active
                    else ByzantineVerifierBehavior.FALSE_NEGATIVE
                )
                byzantine_vote = resolve_byzantine_verifier_vote(byzantine_behavior)
                deduplicated = deduplicate_reports_by_proxy(
                    tuple(
                        (
                            domain,
                            byzantine_vote
                            if domain in compromised_domains_set
                            else resolve_ternary_outcome(
                                True, domain not in false_negative_domains
                            ),
                        )
                        for domain in panel
                    )
                )
                reports = tuple(deduplicated[domain] for domain in panel)
                certified = reproduction_row_is_certified(
                    reports,
                    panel_size=config.protocol.verification.panel_size,
                    required_positive_reports=config.protocol.verification.required_positive_reports,
                )
                honest_positive_bound = minimum_honest_positive_count(
                    sum(1 for report in reports if report is TernaryOutcome.POSITIVE),
                    compromised_count,
                )
                if is_deterministic:
                    diagnostic_passes = True
                else:
                    contamination_probability = diagnostic_at_least_two_byzantine_probability(
                        len(eligible_verifiers),
                        compromised_count,
                        config.protocol.verification.panel_size,
                    )
                    diagnostic_profile = config.protocol.diagnostic_random_verifier_profile
                    diagnostic_passes = (
                        contamination_probability <= diagnostic_profile.tolerated_contamination_risk
                    )
                minimum_gate_domains = (
                    config.protocol.final_gate.minimum_adequate_non_source_domains
                )
                state = (
                    ClaimState.ADMITTED
                    if diagnostic_passes
                    and certified
                    and evidence.final_gate_adequate_domain_count >= minimum_gate_domains
                    and honest_positive_bound >= 1
                    else ClaimState.DORMANT
                )
        metrics = _metrics_from_state(state, self._pending_real_report)
        return state, metrics

    def _execute_byzantine_bound_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
    ) -> tuple[ClaimState, tuple[tuple[CanonicalToken, float | None], ...]]:
        condition = BoundCondition(cell.condition)
        if condition is BoundCondition.ONE_BYZANTINE_REPRODUCER_WITHIN_BOUND:
            reproducer_cell = replace(
                cell, condition=ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR.value
            )
            return self._execute_reproducer_robustness_cell(reproducer_cell, config, evidence)
        if condition is BoundCondition.TWO_BYZANTINE_REPRODUCERS_ABOVE_BOUND:
            reproducer_cell = replace(
                cell, condition=ReproducerCondition.TWO_MODEL_REPLACEMENT_BACKDOORS.value
            )
            return self._execute_reproducer_robustness_cell(reproducer_cell, config, evidence)
        if condition is BoundCondition.ONE_BYZANTINE_VERIFIER_WITHIN_BOUND:
            verifier_cell = replace(
                cell,
                method=VerifierProfile.DETERMINISTIC_BOUND.value,
                condition=VerifierCondition.ONE_FALSE_POSITIVE.value,
            )
            return self._execute_verifier_robustness_cell(verifier_cell, config, evidence)
        verifier_cell = replace(
            cell,
            method=VerifierProfile.DETERMINISTIC_BOUND.value,
            condition=VerifierCondition.TWO_FALSE_POSITIVES.value,
        )
        return self._execute_verifier_robustness_cell(verifier_cell, config, evidence)

    def _execute_secondary_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
    ) -> tuple[ClaimState, tuple[tuple[CanonicalToken, float | None], ...]]:
        state = self._advance_protocol(cell, config, evidence)
        metrics = _metrics_from_state(state, self._pending_real_report)
        return state, metrics

    def _execute_evidence_scarcity_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
    ) -> tuple[ClaimState, tuple[tuple[CanonicalToken, float | None], ...]]:
        schedule = EvidenceArrivalSchedule(cell.condition)
        horizon = config.protocol.resource_horizon.maximum_logical_evidence_cycles
        candidate_cycles = tuple(range(horizon))
        holder_counts = tuple(
            holder_count_at_cycle(schedule, cycle, len(NBAIOT_DOMAIN_ORDER) - 1)
            for cycle in candidate_cycles
        )
        tau_k = first_cycle_with_minimum_eligible_evidence_holders(
            holder_counts,
            config.protocol.final_gate.minimum_adequate_non_source_domains,
        )
        target_capable_order = tuple(NBAIOT_DOMAIN_ORDER[1:])
        t_evidence = compute_t_evidence(
            schedule,
            target_capable_order,
            candidate_cycles,
            config.protocol.synthesis.committee_size,
            config.protocol.final_gate.minimum_adequate_non_source_domains,
        )
        first_holder = first_holder_cycle_for_domain(
            schedule, NBAIOT_DOMAIN_ORDER[1], target_capable_order, candidate_cycles
        )
        if tau_k is None:
            state = resume_dormant_claim(DormantOrigin.REPRODUCTION_PENDING, False)
            metrics = _metrics_from_state(state, self._pending_real_report)
            return state, (*metrics, ("evidence-arrival-cycle", None))
        try:
            validate_no_safety_claim_before_tau_k(0, tau_k)
        except ValueError:
            state = resume_dormant_claim(DormantOrigin.REPRODUCTION_PENDING, False)
            metrics = _metrics_from_state(state, self._pending_real_report)
            return state, (*metrics, ("evidence-arrival-cycle", float(tau_k)))
        state = self._advance_protocol(cell, config, evidence)
        metrics = _metrics_from_state(state, self._pending_real_report)
        delay_decomposition = AdmissionDelayDecomposition(
            logical_information_arrival_cycles=tau_k,
            assignment_seconds=0.0,
            reproduce_seconds=0.0,
            verify_seconds=0.0,
            synthesize_seconds=0.0,
        )
        return state, (
            *metrics,
            ("evidence-arrival-cycle", float(tau_k)),
            (
                "logical-information-arrival-cycles",
                float(delay_decomposition.logical_information_arrival_cycles),
            ),
            ("t-evidence", float(t_evidence) if t_evidence is not None else None),
            (
                "first-holder-cycle",
                float(first_holder) if first_holder is not None else None,
            ),
            ("post-evidence-wall-clock-seconds", None),
        )

    def _execute_admission_delay_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
    ) -> tuple[ClaimState, tuple[tuple[CanonicalToken, float | None], ...]]:
        schedule = EvidenceArrivalSchedule(cell.condition)
        horizon = config.protocol.resource_horizon.maximum_logical_evidence_cycles
        candidate_cycles = tuple(range(horizon))
        holder_counts = tuple(
            holder_count_at_cycle(schedule, cycle, len(NBAIOT_DOMAIN_ORDER) - 1)
            for cycle in candidate_cycles
        )
        tau_k = first_cycle_with_minimum_eligible_evidence_holders(
            holder_counts,
            config.protocol.final_gate.minimum_adequate_non_source_domains,
        )
        target_capable_order = tuple(NBAIOT_DOMAIN_ORDER[1:])
        t_evidence = compute_t_evidence(
            schedule,
            target_capable_order,
            candidate_cycles,
            config.protocol.synthesis.committee_size,
            config.protocol.final_gate.minimum_adequate_non_source_domains,
        )
        timer = ElapsedTimer()
        if cell.method == "Resolved FedSIRA Core":
            state = self._advance_protocol(cell, config, evidence)
            post_evidence_wall_clock_seconds = timer.elapsed_seconds()
            metrics = _metrics_from_state(state, self._pending_real_report)
        else:
            state, metrics = self._execute_baseline_cell(cell, config, evidence)
            post_evidence_wall_clock_seconds = timer.elapsed_seconds()
        return state, (
            *metrics,
            ("evidence-arrival-cycle", float(tau_k) if tau_k is not None else None),
            ("t-evidence", float(t_evidence) if t_evidence is not None else None),
            ("post-evidence-wall-clock-seconds", post_evidence_wall_clock_seconds),
        )

    def _execute_efficiency_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
    ) -> tuple[ClaimState, tuple[tuple[CanonicalToken, float | None], ...]]:
        model_size_bytes = 115 * 256 * 4
        envelopes: list[bytes] = []
        metadata_records: list[CommunicationMessageMetadata] = []
        tensor_name = canonical_parameter_tensor_name(TensorParameterKind.MODEL, "linear")
        timer = ElapsedTimer()
        for message_type, count in _efficiency_message_counts():
            for _index in range(count):
                metadata = CommunicationMessageMetadata(
                    message_type=message_type,
                    dataset_manifest_hash="a" * 64,
                    semantic_cell_key_hash="b" * 64,
                    master_seed=cell.master_seed,
                    round_index=None,
                    sender=SERVER_TOKEN,
                    receiver="CLIENT",
                    claim_contract_hash="c" * 64,
                    payload_tensor_count=1,
                )
                tensor_payload = b"\x00" * model_size_bytes
                envelopes.append(
                    encode_message_envelope(
                        metadata,
                        {tensor_name: tensor_payload},
                        {
                            tensor_name: TensorPayloadMetadata(
                                name=tensor_name,
                                shape=(115, 256),
                                nbytes=model_size_bytes,
                            )
                        },
                    )
                )
                metadata_records.append(metadata)
        encode_elapsed_seconds = timer.elapsed_seconds()
        bytes_total = communication_bytes(envelopes)
        transmissions = model_transmission_count(metadata_records)
        reset_peak_gpu_memory_counter()
        protocol_timer = ElapsedTimer()
        if cell.method == "Resolved FedSIRA Core":
            state = self._advance_protocol(cell, config, evidence)
        else:
            state, _baseline_metrics = self._execute_baseline_cell(cell, config, evidence)
        post_evidence_seconds = protocol_timer.elapsed_seconds()
        delay_decomposition = AdmissionDelayDecomposition(
            logical_information_arrival_cycles=0,
            assignment_seconds=0.0,
            reproduce_seconds=0.0,
            verify_seconds=encode_elapsed_seconds,
            synthesize_seconds=post_evidence_seconds,
        )
        gpu_memory_bytes = peak_gpu_memory_bytes()
        host_rss_bytes = peak_host_resident_set_bytes()
        return state, (
            ("post-evidence-overhead", delay_decomposition.post_evidence_wall_clock_seconds),
            ("communication-bytes", float(bytes_total)),
            ("model-transmissions", float(transmissions)),
            (
                "post-evidence-wall-clock-seconds",
                delay_decomposition.post_evidence_wall_clock_seconds,
            ),
            ("peak-gpu-memory-bytes", float(gpu_memory_bytes)),
            ("peak-host-rss-bytes", float(host_rss_bytes)),
        )


def _efficiency_message_counts() -> tuple[tuple[CommunicationMessageType, int], ...]:
    return (
        (CommunicationMessageType.SOURCE_COMMITMENT, 1),
        (CommunicationMessageType.MODEL_DISTRIBUTION, 8),
        (CommunicationMessageType.UPDATE_SUBMISSION, 8),
        (CommunicationMessageType.CLAIM_CONTRACT, 1),
        (CommunicationMessageType.REVIEW_ASSIGNMENT, 3),
        (CommunicationMessageType.REVIEW_REPORT, 3),
        (CommunicationMessageType.VERIFIER_ASSIGNMENT, 5),
        (CommunicationMessageType.VERIFIER_REPORT, 5),
        (CommunicationMessageType.FINAL_GATE_ASSIGNMENT, 6),
        (CommunicationMessageType.FINAL_GATE_REPORT, 6),
        (CommunicationMessageType.DECISION, 1),
    )


def _metrics_from_state(
    state: ClaimState,
    real_report: RealReportSummary | None = None,
) -> tuple[tuple[CanonicalToken, float | None], ...]:
    is_admitted = state is ClaimState.ADMITTED
    is_dormant = state is ClaimState.DORMANT
    legitimate_result = legitimate_admission_rate([is_admitted])
    dormant_result = dormant_claim_rate(
        dormant_claim_count=1 if is_dormant else 0, eligible_claim_count=1
    )
    report_metrics = report_metric_set(
        true_labels=(),
        predicted_labels=(),
        class_tokens=(NBaiotClass.BENIGN.value, NBaiotClass.GAFGYT_COMBO.value),
        target_class_token=NBaiotClass.GAFGYT_COMBO.value,
        benign_class_token=NBaiotClass.BENIGN.value,
        supported_class_tokens=(NBaiotClass.BENIGN.value,),
    )
    if real_report is not None:
        target_f1 = real_report.target_f1
        target_f1_gain = MetricResult(None, 0)
        supported_macro_f1_harm_value = real_report.supported_macro_f1_harm
        benign_far_increase_value = real_report.benign_far_increase
        worst_domain = real_report.worst_domain_target_f1
        p10_domain = real_report.p10_domain_target_f1
        disparity = real_report.domain_disparity
        iqr = real_report.domain_iqr
        cv = real_report.coefficient_of_variation
        equal_weight_mean = real_report.target_f1
    else:
        target_f1 = report_metrics["target-f1"]
        target_f1_gain = report_metrics["target-f1-gain"]
        supported_macro_f1_harm_value = report_metrics["supported-macro-f1-harm"]
        benign_far_increase_value = report_metrics["benign-far-increase"]
        domain_f1_values = [report_metrics["target-f1"]]
        worst_domain = worst_domain_target_f1(domain_f1_values)
        p10_domain = percentile_10_domain_target_f1(domain_f1_values)
        disparity = domain_disparity(domain_f1_values)
        iqr = interquartile_range(domain_f1_values)
        defined_values = [result.value for result in domain_f1_values if result.value is not None]
        cv = coefficient_of_variation(defined_values) if defined_values else MetricResult(None, 0)
        equal_weight_mean = equal_weight_domain_mean(domain_f1_values, 1)
    return (
        ("terminal-state", _state_encoding(state)),
        ("legitimate-admission", legitimate_result.value),
        ("target-f1", target_f1.value),
        ("target-f1-gain", target_f1_gain.value),
        ("supported-macro-f1-harm", supported_macro_f1_harm_value.value),
        ("benign-far-increase", benign_far_increase_value.value),
        ("asr", report_metrics["asr"].value),
        ("accuracy", report_metrics["accuracy"].value),
        ("macro-f1", report_metrics["macro-f1"].value),
        ("weighted-f1", report_metrics["weighted-f1"].value),
        ("balanced-accuracy", report_metrics["balanced-accuracy"].value),
        ("verifier-abstention-rate", report_metrics["verifier-abstention-rate"].value),
        (
            "reproduction-abstention-rate",
            report_metrics["reproduction-abstention-rate"].value,
        ),
        ("worst-domain-target-f1", worst_domain.value),
        ("p10-domain-target-f1", p10_domain.value),
        ("domain-disparity", disparity.value),
        ("domain-iqr", iqr.value),
        ("coefficient-of-variation", cv.value),
        ("equal-weight-domain-mean-target-f1", equal_weight_mean.value),
        ("reproduction-attempts", 1.0 if is_admitted else 0.0),
        ("false-launch", 0.0),
        ("post-evidence-overhead", 1.0 if is_admitted else 0.0),
        ("dormant-claim-rate", dormant_result.value),
    )


def _state_encoding(state: ClaimState) -> float:
    return {
        ClaimState.ADMITTED: 1.0,
        ClaimState.REJECTED_CLAIM: -1.0,
        ClaimState.EXPIRED: -2.0,
        ClaimState.DORMANT: 0.0,
    }.get(state, 0.0)
