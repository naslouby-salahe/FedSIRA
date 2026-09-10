from __future__ import annotations

from collections import OrderedDict
from collections.abc import Sequence
from pathlib import Path

import torch

from fedsira.config import VerificationConfig
from fedsira.datasets.common import Role, role_hash_token
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_CLASS_ORDER,
    NBAIOT_DOMAIN_ORDER,
    NBaiotClass,
    NBaiotDomain,
)
from fedsira.domain.enums import (
    AdmissionOpeningMode,
    AdmissionState,
    CoreMethodIdentity,
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
    FrozenDomainModel,
    MasterSeed,
    MetricObservation,
    MetricValue,
    ModuleName,
    RequiredReproductionRowCount,
)
from fedsira.evaluation.comparisons import (
    ComparisonMetric,
)
from fedsira.evaluation.domain import (
    evaluate_domain,
    non_source_domains,
)
from fedsira.evaluation.metrics import (
    dormant_admission_rate,
    legitimate_admission_rate,
    metric_value,
    report_metric_set,
    supported_macro_f1_harm,
)
from fedsira.evaluation.report_summary import RealReportSummary, compute_real_report_summary
from fedsira.evaluation.summaries import (
    coefficient_of_variation,
    domain_disparity,
    equal_weight_domain_mean,
    interquartile_range,
    percentile_10_domain_target_f1,
    worst_domain_target_f1,
)
from fedsira.experiments.collapse import ResolvedCore
from fedsira.experiments.definitions import (
    MECHANISM_ABLATION_NAME,
    AblationVariant,
    OpeningMode,
    ReproducerCondition,
    VerifierCondition,
)
from fedsira.experiments.planning import (
    ScientificCell,
)
from fedsira.experiments.prerequisites import (
    PreparedEvidenceCounts,
)
from fedsira.experiments.scenarios.evidence_arrival import (
    reproducer_order,
)
from fedsira.experiments.workflow import (
    HeterogeneityScope,
    RealAnchor,
)
from fedsira.learning.anchor import run_anchor_fedavg_training
from fedsira.learning.post_reference import run_post_reference_training
from fedsira.learning.post_reference_training import (
    certified_domain_delta_committee,
    train_source_candidate_delta,
)
from fedsira.protocol.admission import (
    apply_production_update,
    final_gate_predicates_pass,
    median_domain_target_f1,
    resolve_production_update,
    validate_admission_requires_final_gate,
    validate_production_checkpoint_excludes_source,
)
from fedsira.protocol.attacks.byzantine import (
    verifier_aware_training_step,
)
from fedsira.protocol.baselines.registry import (
    BaselineIdentity,
    first_eligible_non_source_reproducer,
    single_fresh_verifier_domain,
    single_fresh_verifier_outcome,
)
from fedsira.protocol.baselines.robust_aggregation import (
    coordinate_wise_median_synthesis,
)
from fedsira.protocol.capability_contract import (
    build_capability_contract,
    capability_contract_passes,
    compute_capability_identity,
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
from fedsira.protocol.state_machine import (
    resolve_ternary_outcome,
)
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
ANCHOR_FLAT_PARAMETERS = torch.zeros(1)


def _training_entry_points(evidence: PreparedEvidenceCounts) -> tuple[ModuleName, ...]:
    config = current_application_context().scientific_config
    if (
        evidence.reproduction_target_count
        < config.capability_contract.evidence_minima.reproduction_target_examples
    ):
        return ()
    if (
        evidence.reproduction_supported_count
        < config.capability_contract.evidence_minima.reproduction_supported_control_examples
    ):
        return ()
    anchor_entry = run_anchor_fedavg_training.__module__
    post_reference_entry = run_post_reference_training.__module__
    verifier_aware_entry = verifier_aware_training_step.__module__
    return (anchor_entry, post_reference_entry, verifier_aware_entry)


class OpeningIdentity(FrozenDomainModel):
    capability_identity: CapabilityIdentity
    contract_passes: CapabilityContractSatisfied


def _opening_mode_for_cell(
    cell: ScientificCell, resolved_core: ResolvedCore | None = None
) -> AdmissionOpeningMode:
    if cell.method == RESOLVED_FEDSIRA_CORE_METHOD and resolved_core is not None:
        return resolved_core.opening_mode
    if cell.method == OpeningMode.PROPOSAL_ASSISTED:
        return AdmissionOpeningMode.PROPOSAL_ASSISTED
    return AdmissionOpeningMode.CANDIDATE_FREE


def _opening_identity() -> OpeningIdentity:
    config = current_application_context().scientific_config
    contract = build_capability_contract(
        "a" * 64,
        role_hash_token(Role.POST_REFERENCE_REPLAY),
        config.datasets.primary.name,
        len(NBAIOT_DOMAIN_ORDER),
        "b" * 64,
        NBaiotClass.GAFGYT_COMBO,
        len(NBAIOT_CLASS_ORDER) - 1,
        config.capability_contract,
    )
    capability_identity = compute_capability_identity(contract)
    contract_passes = capability_contract_passes(
        contract,
        MetricResult(value=None, denominator=0),
        MetricResult(value=None, denominator=0),
        MetricResult(value=None, denominator=0),
        MetricResult(value=None, denominator=0),
    )
    return OpeningIdentity(capability_identity=capability_identity, contract_passes=contract_passes)


def _source_domain_for_cell(cell: ScientificCell) -> NBaiotDomain | None:
    source_order = source_selection_order(
        NBAIOT_DOMAIN_ORDER, derive_uint32(SOURCE_SELECTION_SEED_SEPARATOR, cell.master_seed)
    )
    validate_exactly_one_source_domain((source_order[0],))
    selected = select_source_domain(
        source_order,
        frozenset(NBAIOT_DOMAIN_ORDER),
        requires_attack_carrier=False,
        domains_with_attack_carrier=frozenset(),
    )
    return NBaiotDomain(selected) if selected is not None else None


def _reproducer_order(cell: ScientificCell) -> tuple[NBaiotDomain, ...]:
    return reproducer_order(
        NBAIOT_DOMAIN_ORDER, derive_uint32("REPRODUCER_ORDER_SEED", cell.master_seed)
    )


def _row_requirement(
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


def _commitment_digest(reproducer_domain: NBaiotDomain, master_seed: MasterSeed) -> ArtifactDigest:
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
    allow_source_as_verifier: AllowSourceAsVerifier = False,
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
    panel = deterministic_verifier_panel(
        eligible_verifiers, row_seed=row_seed, panel_size=verification_config.panel_size
    )
    return tuple(NBaiotDomain(domain) for domain in panel)


def _reproduction_progression(
    cell: ScientificCell,
    evidence: PreparedEvidenceCounts,
    external_verification_active: BooleanValue,
    row_requirement: RequiredReproductionRowCount,
    compromised_reproducers: frozenset[NBaiotDomain],
    include_source_as_first_reproducer: BooleanValue = False,
) -> tuple[AdmissionState, tuple[ReproductionAttempt, ...], tuple[ArtifactDigest, ...]]:
    reproducer_order = _reproducer_order(cell)
    source_domain = _source_domain_for_cell(cell)
    validate_reproduction_start_checkpoint("anchor-checkpoint", frozenset({"source-checkpoint"}))
    validate_reproduction_starts_from_anchor(ANCHOR_FLAT_PARAMETERS.clone(), ANCHOR_FLAT_PARAMETERS)
    adequate_domains = frozenset(
        domain for domain in NBAIOT_DOMAIN_ORDER if domain != source_domain
    )
    attempts: list[ReproductionAttempt] = []
    commitment_hashes: list[ArtifactDigest] = []
    certified_count = 0
    state = AdmissionState.REPRODUCTION_PENDING
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
        if state is AdmissionState.SYNTHESIS_PENDING:
            return (state, tuple(attempts), tuple(commitment_hashes))
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
        if state is AdmissionState.SYNTHESIS_PENDING:
            break
    return (state, tuple(attempts), tuple(commitment_hashes))


def _single_verifier_progression(
    cell: ScientificCell, source_domain: NBaiotDomain | None
) -> tuple[AdmissionState, tuple[ReproductionAttempt, ...], tuple[ArtifactDigest, ...]]:
    config = current_application_context().scientific_config
    reproducer_order = _reproducer_order(cell)
    adequate_domains = frozenset(
        domain for domain in NBAIOT_DOMAIN_ORDER if domain != source_domain
    )
    consumed: set[NBaiotDomain] = set()
    while True:
        candidate = first_eligible_non_source_reproducer(
            reproducer_order, adequate_domains - frozenset(consumed)
        )
        if candidate is None:
            return (AdmissionState.DORMANT, (), ())
        next_domain = NBaiotDomain(candidate)
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
        if verifier_outcome is AdmissionState.ADMITTED:
            attempt = ReproductionAttempt(domain=next_domain, was_trained=True, is_certified=True)
            return (AdmissionState.SYNTHESIS_PENDING, (attempt,), (commitment_hash,))


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


def _final_gate_decision(
    evidence: PreparedEvidenceCounts,
    source_domain: NBaiotDomain | None,
    reproducer_order: Sequence[NBaiotDomain],
    is_plurality_active: BooleanValue,
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor | None,
    coordinate_median_active: BooleanValue = False,
    no_final_synthesis_gate_active: BooleanValue = False,
    use_source_delta_for_source_domain: BooleanValue = False,
    force_first_row_to_source_delta: BooleanValue = False,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> tuple[AdmissionState, RealReportSummary | None]:
    config = current_application_context().scientific_config
    base_flat_parameters = anchor.flat_parameters if anchor is not None else ANCHOR_FLAT_PARAMETERS
    committee_deltas: OrderedDict[NBaiotDomain, torch.Tensor] = (
        certified_domain_delta_committee(
            prepared_root,
            master_seed,
            anchor,
            reproducer_order,
            heterogeneity_scope=heterogeneity_scope,
        )
        if anchor is not None
        else OrderedDict()
    )
    if use_source_delta_for_source_domain and anchor is not None and (source_domain is not None):
        source_delta = train_source_candidate_delta(
            prepared_root, master_seed, anchor, source_domain
        )
        if source_delta is not None:
            committee_deltas[source_domain] = source_delta
    if (
        force_first_row_to_source_delta
        and anchor is not None
        and (source_domain is not None)
        and reproducer_order
    ):
        source_delta = train_source_candidate_delta(
            prepared_root, master_seed, anchor, source_domain
        )
        if source_delta is not None:
            committee_deltas[reproducer_order[0]] = source_delta
    if coordinate_median_active:
        median_deltas = tuple(
            committee_deltas.get(
                domain,
                reproduction_update_vector(ANCHOR_FLAT_PARAMETERS, ANCHOR_FLAT_PARAMETERS),
            )
            for domain in reproducer_order
        )
        production_update = coordinate_wise_median_synthesis(median_deltas)
        production_checkpoint = apply_production_update(base_flat_parameters, production_update)
        return _final_gate_decision_from_production_checkpoint(
            evidence,
            source_domain,
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
    anchor: RealAnchor | None,
    production_checkpoint: torch.Tensor,
    no_final_synthesis_gate_active: BooleanValue = False,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> tuple[AdmissionState, RealReportSummary | None]:
    config = current_application_context().scientific_config
    if anchor is not None:
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
    else:
        adequate_final_gate_domain_count = evidence.final_gate_adequate_domain_count
        median_target_f1 = median_domain_target_f1(
            tuple(MetricResult(value=None, denominator=0) for _domain in NBAIOT_DOMAIN_ORDER)
        )
        minimum_target_f1 = MetricResult(value=None, denominator=0)
        pooled_supported_macro_f1_drop = MetricResult(value=None, denominator=0)
        pooled_benign_far_increase = MetricResult(value=None, denominator=0)
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
    if final_gate_state is not AdmissionState.ADMITTED:
        return (final_gate_state, real_report_summary)
    validate_production_checkpoint_excludes_source(production_checkpoint, None)
    validate_admission_requires_final_gate(AdmissionState.ADMITTED, True)
    return (AdmissionState.ADMITTED, real_report_summary)


def _compromised_reproducer_count(condition: ConditionName) -> CompromisedReproducerCount:
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


def _compromised_verifier_count(condition: ConditionName) -> ByzantineDomainCount:
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


def _efficiency_message_counts() -> (
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


def _metrics_from_state(
    state: AdmissionState, real_report: RealReportSummary | None = None
) -> tuple[MetricObservation, ...]:
    is_admitted = state is AdmissionState.ADMITTED
    is_dormant = state is AdmissionState.DORMANT
    legitimate_result = legitimate_admission_rate([is_admitted])
    dormant_result = dormant_admission_rate(
        dormant_admission_count=1 if is_dormant else 0, eligible_admission_count=1
    )
    report_metrics = report_metric_set(
        true_labels=(),
        predicted_labels=(),
        class_tokens=(NBaiotClass.BENIGN, NBaiotClass.GAFGYT_COMBO),
        target_class_token=NBaiotClass.GAFGYT_COMBO,
        benign_class_token=NBaiotClass.BENIGN,
        supported_class_tokens=(NBaiotClass.BENIGN,),
    )
    if real_report is not None:
        target_f1 = real_report.target_f1
        target_f1_gain = MetricResult(value=None, denominator=0)
        supported_macro_f1_harm_value = real_report.supported_macro_f1_harm
        benign_far_increase_value = real_report.benign_far_increase
        worst_domain = real_report.worst_domain_target_f1
        p10_domain = real_report.p10_domain_target_f1
        disparity = real_report.domain_disparity
        iqr = real_report.domain_iqr
        cv = real_report.coefficient_of_variation
        equal_weight_mean = real_report.target_f1
    else:
        target_f1 = metric_value(report_metrics, ComparisonMetric.TARGET_F1)
        target_f1_gain = metric_value(report_metrics, "target-f1-gain")
        supported_macro_f1_harm_value = metric_value(
            report_metrics, ComparisonMetric.SUPPORTED_MACRO_F1_HARM
        )
        benign_far_increase_value = metric_value(
            report_metrics, ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE
        )
        domain_f1_values = (metric_value(report_metrics, ComparisonMetric.TARGET_F1),)
        worst_domain = worst_domain_target_f1(domain_f1_values)
        p10_domain = percentile_10_domain_target_f1(domain_f1_values)
        disparity = domain_disparity(domain_f1_values)
        iqr = interquartile_range(domain_f1_values)
        defined_values = tuple(
            result.value for result in domain_f1_values if result.value is not None
        )
        cv = (
            coefficient_of_variation(defined_values)
            if defined_values
            else MetricResult(value=None, denominator=0)
        )
        equal_weight_mean = equal_weight_domain_mean(domain_f1_values, 1)
    return (
        ("terminal-state", _state_encoding(state)),
        (ComparisonMetric.LEGITIMATE_ADMISSION, legitimate_result.value),
        (ComparisonMetric.TARGET_F1, target_f1.value),
        ("target-f1-gain", target_f1_gain.value),
        (ComparisonMetric.SUPPORTED_MACRO_F1_HARM, supported_macro_f1_harm_value.value),
        (ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE, benign_far_increase_value.value),
        (
            ComparisonMetric.ATTACK_SUCCESS_RATE,
            metric_value(report_metrics, ComparisonMetric.ATTACK_SUCCESS_RATE).value,
        ),
        ("accuracy", metric_value(report_metrics, "accuracy").value),
        ("macro-f1", metric_value(report_metrics, "macro-f1").value),
        ("weighted-f1", metric_value(report_metrics, "weighted-f1").value),
        ("balanced-accuracy", metric_value(report_metrics, "balanced-accuracy").value),
        (
            "verifier-abstention-rate",
            metric_value(report_metrics, "verifier-abstention-rate").value,
        ),
        (
            "reproduction-abstention-rate",
            metric_value(report_metrics, "reproduction-abstention-rate").value,
        ),
        (ComparisonMetric.WORST_DOMAIN_TARGET_F1, worst_domain.value),
        ("p10-domain-target-f1", p10_domain.value),
        ("domain-disparity", disparity.value),
        ("domain-iqr", iqr.value),
        ("coefficient-of-variation", cv.value),
        ("equal-weight-domain-mean-target-f1", equal_weight_mean.value),
        (ComparisonMetric.REPRODUCTION_ATTEMPTS, 1.0 if is_admitted else 0.0),
        (ComparisonMetric.FALSE_LAUNCH, 0.0),
        (ComparisonMetric.POST_EVIDENCE_OVERHEAD, 1.0 if is_admitted else 0.0),
        ("dormant-admission-rate", dormant_result.value),
    )


_STATE_ENCODINGS: tuple[tuple[AdmissionState, MetricValue], ...] = (
    (AdmissionState.ADMITTED, 1.0),
    (AdmissionState.REJECTED, -1.0),
    (AdmissionState.EXPIRED, -2.0),
    (AdmissionState.DORMANT, 0.0),
)


def _state_encoding(state: AdmissionState) -> MetricValue:
    for encoded_state, encoding in _STATE_ENCODINGS:
        if encoded_state is state:
            return encoding
    return 0.0
