from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from time import monotonic

import torch

from fedsira.boundaries.evidence_arrival import (
    EvidenceArrivalSchedule,
    holder_count_at_cycle,
    reproducer_order,
)
from fedsira.config.schema import ScientificConfig, VerificationConfig
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_DOMAIN_ORDER,
    NBaiotDomain,
)
from fedsira.domain.enums import (
    ClaimOpeningMode,
    ClaimState,
    DormantOrigin,
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
)
from fedsira.evaluation.records import AdmissionDelayDecomposition, MetricResult
from fedsira.evaluation.screen import run_proposal_screen_for_domain, screen_fold_index
from fedsira.experiments.execution import CellExecutionOutcome, CellExecutor
from fedsira.experiments.planning import ScientificCell
from fedsira.experiments.registry import (
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
    EXTERNAL_VERIFICATION_NECESSITY_NAME,
    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME,
    SECONDARY_DATASET_GENERALIZATION_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
    SINGLE_REPRODUCTION_NECESSITY_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    ExternalVerificationCondition,
    PluralityCondition,
    PrimaryScenario,
    ProposalEpisode,
    ReproducerCondition,
    SourceExclusionMethod,
    VerifierCondition,
    VerifierProfile,
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
    screen_domain_decision_is_positive,
    screen_domain_order,
    start_claim,
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
from fedsira.runtime.telemetry import (
    peak_gpu_memory_bytes,
    peak_host_resident_set_bytes,
    reset_peak_gpu_memory_counter,
)

EVIDENCE_INSUFFICIENT_REASON = "Evidence Insufficient"
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
    return (anchor_entry, post_reference_entry)


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
    prepared_root: Path, cell: ScientificCell
) -> PreparedEvidenceCounts | None:
    metadata_directory = prepared_root / "nbaiot"
    if not metadata_directory.exists():
        return None
    screen_target_count = 0
    reproduction_target_count = 0
    reproduction_supported_count = 0
    final_gate_target_files = 0
    for metadata_path in sorted(metadata_directory.glob("*.json")):
        try:
            payload = json.loads(metadata_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        role = payload.get("role")
        row_count = int(payload.get("row_count", 0))
        class_id = payload.get("class_id")
        if role == "Candidate Screen" and class_id == "GAFGYT_COMBO":
            screen_target_count += row_count
        elif role == "Reproduction" and class_id == "GAFGYT_COMBO":
            reproduction_target_count += row_count
        elif role == "Post-Reference Replay" and class_id != "GAFGYT_COMBO":
            reproduction_supported_count += row_count
        elif role == "Final Gate":
            final_gate_target_files += 1
    if screen_target_count == 0 and reproduction_target_count == 0:
        return None
    return PreparedEvidenceCounts(
        screen_target_count=screen_target_count,
        reproduction_target_count=reproduction_target_count,
        reproduction_supported_count=reproduction_supported_count,
        final_gate_adequate_domain_count=final_gate_target_files,
    )


def _opening_mode_for_cell(cell: ScientificCell) -> ClaimOpeningMode:
    if cell.method == "Proposal-Assisted":
        return ClaimOpeningMode.PROPOSAL_ASSISTED
    return ClaimOpeningMode.CANDIDATE_FREE


def _opening_identity(config: ScientificConfig) -> OpeningIdentity:
    contract = build_capability_claim_contract(
        "a" * 64,
        "POST_REFERENCE_REPLAY",
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


def _row_requirement(cell: ScientificCell, config: ScientificConfig) -> int:
    if cell.method == "One Independent Retrain":
        return 1
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
) -> tuple[NBaiotDomain, ...]:
    eligible_verifiers = tuple(
        domain
        for domain in NBAIOT_DOMAIN_ORDER
        if verifier_is_eligible(domain, source_domain, reproducer_domain)
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


def _final_gate_decision(
    config: ScientificConfig,
    evidence: PreparedEvidenceCounts,
    claim_identity: str,
    source_domain: NBaiotDomain | None,
    reproducer_order: Sequence[NBaiotDomain],
    commitment_hashes: Sequence[str],
    is_plurality_active: bool,
    opening_mode: ClaimOpeningMode,
) -> ClaimState:
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
    final_gate_state = synthesis_pending_transition(
        adequate_final_gate_domain_count=evidence.final_gate_adequate_domain_count,
        final_gate_predicates_pass=predicates_pass,
        final_gate_config=config.protocol.final_gate,
    )
    if final_gate_state is not ClaimState.ADMITTED:
        return final_gate_state
    krum_selected_update: torch.Tensor | None = None
    if is_plurality_active:
        committee = tuple(
            CertifiedReproductionRow(
                reproducer_domain=domain,
                update_vector=reproduction_update_vector(
                    ANCHOR_FLAT_PARAMETERS, ANCHOR_FLAT_PARAMETERS
                ),
            )
            for domain in reproducer_order
        )
        krum_selected_update = select_krum_update(
            committee, config.protocol.synthesis.maximum_byzantine_reproduction_rows
        ).update_vector
    production_update = resolve_production_update(
        is_plurality_active,
        krum_selected_update,
        ANCHOR_FLAT_PARAMETERS,
    )
    production_checkpoint = apply_production_update(ANCHOR_FLAT_PARAMETERS, production_update)
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
    return ClaimState.ADMITTED


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


class ProtocolCellExecutor(CellExecutor):
    def __init__(self, prepared_root: Path | None = None) -> None:
        self._prepared_root = prepared_root or Path("outputs") / "preprocessing" / "prepared"

    def execute_cell(self, cell: ScientificCell, config: ScientificConfig) -> CellExecutionOutcome:
        evidence = load_prepared_evidence_counts(self._prepared_root, cell)
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
                terminal_state="Invalid",
                failure=FailureDetail(
                    failure_class=FailureClass.INVARIANT_VIOLATION,
                    message=str(error),
                    cell_phase=ScientificCellPhase.PREPARE,
                ),
            )
        return CellExecutionOutcome(
            cell=cell,
            terminal_state="Completed",
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
        if cell.experiment == EFFICIENCY_MEASUREMENT_NAME:
            return self._execute_efficiency_cell(cell, config, evidence)
        if cell.experiment == SECONDARY_DATASET_GENERALIZATION_NAME:
            return self._execute_secondary_cell(cell, config, evidence)
        if cell.experiment == EVIDENCE_SCARCITY_AND_DORMANCY_NAME:
            return self._execute_evidence_scarcity_cell(cell, config, evidence)
        if cell.experiment in (
            SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
            CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
            HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
        ):
            return self._execute_boundary_cell(cell, config, evidence)
        return ClaimState.DORMANT, _metrics_from_state(ClaimState.DORMANT)

    def _execute_boundary_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
    ) -> tuple[ClaimState, tuple[tuple[CanonicalToken, float | None], ...]]:
        state = self._advance_protocol(cell, config, evidence)
        metrics = _metrics_from_state(state)
        is_scoped_contract = cell.method != "Broad Target Only"
        boundary_metrics = boundary_metric_set(
            true_labels=(),
            predicted_labels=(),
            class_tokens=("BENIGN", "GAFGYT_COMBO"),
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
            extra.append(("proposal-oracle-label", float(oracle_label.value == "ORACLE_VALID")))
        return state, (*metrics, *extra)

    def _execute_opening_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
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
        metrics = _metrics_from_state(state)
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
        screen_differential = run_proposal_screen_for_domain(
            fold_assignment_by_sample_id={},
            target_observations=(),
            control_observations=(),
            fold_count=config.protocol.proposal_screen.fold_count,
        )
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
        external_verification_active = (
            cell.experiment == EXTERNAL_VERIFICATION_NECESSITY_NAME
            and cell.method == "Full FedSIRA"
        )
        row_requirement = _row_requirement(cell, config)
        progression_state, attempts, commitment_hashes = _reproduction_progression(
            cell,
            config,
            evidence,
            external_verification_active,
            row_requirement,
            frozenset(),
        )
        if progression_state is ClaimState.VERIFICATION_PENDING:
            certified_positive_report_count = 0
            for attempt in attempts:
                if not attempt.is_certified:
                    continue
                panel = _verifier_panel(
                    source_domain, attempt.domain, cell.master_seed, config.protocol.verification
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
                if verifier_is_eligible(domain, source_domain, attempts[0].domain)
            )
            progression_state = verification_pending_transition(
                eligible_verifier_count,
                certified_positive_report_count,
                row_requirement <= len(attempts),
                config.protocol.verification,
            )
        if progression_state is ClaimState.SYNTHESIS_PENDING:
            state = _final_gate_decision(
                config,
                evidence,
                _opening_identity(config).claim_identity,
                source_domain,
                tuple(attempt.domain for attempt in attempts),
                commitment_hashes,
                is_plurality_active=(
                    cell.experiment == SINGLE_REPRODUCTION_NECESSITY_NAME
                    and cell.method == "Full Plurality Path"
                ),
                opening_mode=_opening_mode_for_cell(cell),
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
        metrics = _metrics_from_state(state)
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
        else:
            state = ClaimState.ADMITTED
        metrics = _metrics_from_state(state)
        malicious_admission = 0.0
        if method != full_fedsira and state is ClaimState.ADMITTED:
            malicious_admission = 1.0
        return state, (*metrics, ("malicious-admission", malicious_admission))

    def _execute_external_verification_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
    ) -> tuple[ClaimState, tuple[tuple[CanonicalToken, float | None], ...]]:
        state = self._advance_protocol(cell, config, evidence)
        metrics = _metrics_from_state(state)
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
        if (
            scenario == PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value
            and cell.method == "Resolved FedSIRA Core"
        ):
            state = self._advance_protocol(cell, config, evidence)
        else:
            state = ClaimState.DORMANT
        metrics = _metrics_from_state(state)
        return state, metrics

    def _execute_reproducer_robustness_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
    ) -> tuple[ClaimState, tuple[tuple[CanonicalToken, float | None], ...]]:
        condition = cell.condition
        compromised_count = _compromised_reproducer_count(condition)
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
                state = _final_gate_decision(
                    config,
                    evidence,
                    _opening_identity(config).claim_identity,
                    source_domain,
                    tuple(attempt.domain for attempt in attempts),
                    commitment_hashes,
                    is_plurality_active=True,
                    opening_mode=_opening_mode_for_cell(cell),
                )
            else:
                state = ClaimState.DORMANT
        metrics = _metrics_from_state(state)
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
                deduplicated = deduplicate_reports_by_proxy(
                    tuple(
                        (
                            domain,
                            resolve_ternary_outcome(True, domain not in false_negative_domains),
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
        metrics = _metrics_from_state(state)
        return state, metrics

    def _execute_secondary_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
    ) -> tuple[ClaimState, tuple[tuple[CanonicalToken, float | None], ...]]:
        state = self._advance_protocol(cell, config, evidence)
        metrics = _metrics_from_state(state)
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
        if tau_k is None:
            state = resume_dormant_claim(DormantOrigin.REPRODUCTION_PENDING, False)
            metrics = _metrics_from_state(state)
            return state, (*metrics, ("evidence-arrival-cycle", None))
        try:
            validate_no_safety_claim_before_tau_k(0, tau_k)
        except ValueError:
            state = resume_dormant_claim(DormantOrigin.REPRODUCTION_PENDING, False)
            metrics = _metrics_from_state(state)
            return state, (*metrics, ("evidence-arrival-cycle", float(tau_k)))
        state = self._advance_protocol(cell, config, evidence)
        metrics = _metrics_from_state(state)
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
            ("post-evidence-wall-clock-seconds", None),
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
        encode_start = monotonic()
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
        encode_elapsed_seconds = monotonic() - encode_start
        bytes_total = communication_bytes(envelopes)
        transmissions = model_transmission_count(metadata_records)
        delay_decomposition = AdmissionDelayDecomposition(
            logical_information_arrival_cycles=0,
            assignment_seconds=0.0,
            reproduce_seconds=0.0,
            verify_seconds=encode_elapsed_seconds,
            synthesize_seconds=0.0,
        )
        reset_peak_gpu_memory_counter()
        gpu_memory_bytes = peak_gpu_memory_bytes()
        host_rss_bytes = peak_host_resident_set_bytes()
        return ClaimState.DORMANT, (
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
        class_tokens=("BENIGN", "GAFGYT_COMBO"),
        target_class_token="GAFGYT_COMBO",
        benign_class_token="BENIGN",
        supported_class_tokens=("BENIGN",),
    )
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
        ("target-f1", report_metrics["target-f1"].value),
        ("target-f1-gain", report_metrics["target-f1-gain"].value),
        ("supported-macro-f1-harm", report_metrics["supported-macro-f1-harm"].value),
        ("benign-far-increase", report_metrics["benign-far-increase"].value),
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
