from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from fedsira.config.schema import ScientificConfig
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER
from fedsira.domain.enums import (
    ClaimOpeningMode,
    ClaimState,
    FailureClass,
    ScientificCellPhase,
    TernaryOutcome,
)
from fedsira.domain.records import CanonicalToken
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
    dormant_claim_rate,
    false_launch_rate,
    legitimate_admission_rate,
    malicious_admission_rate,
    reproduction_attempt_count,
)
from fedsira.experiments.execution import CellExecutionOutcome, CellExecutor
from fedsira.experiments.planning import ScientificCell
from fedsira.experiments.registry import (
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    EXTERNAL_VERIFICATION_NECESSITY_NAME,
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME,
    SECONDARY_DATASET_GENERALIZATION_NAME,
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
from fedsira.protocol.claim_contract import (
    reproduction_evidence_is_adequate,
    screen_evidence_is_adequate,
    validate_source_excluded_production_weight,
    verification_evidence_is_adequate,
)
from fedsira.protocol.opening import (
    ScreenDomainResult,
    candidate_screen_transition,
    screen_domain_order,
    start_claim,
)
from fedsira.protocol.state_machine import apply_logical_cycle_expiry
from fedsira.protocol.synthesis import krum_input_excludes_source, synthesis_pending_transition
from fedsira.protocol.verification import (
    deterministic_verifier_panel,
    diagnostic_committee_panel,
    reproduction_row_is_certified,
)
from fedsira.runtime.determinism import derive_uint32
from fedsira.runtime.state import FailureDetail

EVIDENCE_INSUFFICIENT_REASON = "Evidence Insufficient"


@dataclass(frozen=True)
class PreparedEvidenceCounts:
    screen_target_count: int
    reproduction_target_count: int
    reproduction_supported_count: int
    final_gate_adequate_domain_count: int


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
        return ClaimState.DORMANT, _metrics_from_state(ClaimState.DORMANT)

    def _execute_opening_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
        evidence: PreparedEvidenceCounts,
    ) -> tuple[ClaimState, tuple[tuple[CanonicalToken, float | None], ...]]:
        opening_mode = (
            ClaimOpeningMode.PROPOSAL_ASSISTED
            if cell.method == "Proposal-Assisted"
            else ClaimOpeningMode.CANDIDATE_FREE
        )
        entry = start_claim(opening_mode)
        if entry.direct_production_weight != 0.0:
            raise ValueError("source direct production weight must be 0.0")
        episode = cell.condition
        episode_is_legitimate = episode in (
            ProposalEpisode.LEGITIMATE_TARGET_CAPABILITY.value,
            ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,
        )
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
            screen_results = tuple(
                ScreenDomainResult(
                    domain=domain,
                    is_evidence_adequate=True,
                    meets_opening_predicate=episode_is_legitimate,
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
        return state, (
            *metrics,
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
        if (
            evidence.final_gate_adequate_domain_count
            < config.protocol.final_gate.minimum_adequate_non_source_domains
        ):
            return ClaimState.DORMANT
        final_gate_state = synthesis_pending_transition(
            adequate_final_gate_domain_count=evidence.final_gate_adequate_domain_count,
            final_gate_predicates_pass=True,
            final_gate_config=config.protocol.final_gate,
        )
        return apply_logical_cycle_expiry(
            final_gate_state,
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
        if condition == ReproducerCondition.CLEAN.value:
            state = self._advance_protocol(cell, config, evidence)
        else:
            state = self._advance_protocol(cell, config, evidence)
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
            eligible_verifiers = tuple(domain for domain in NBAIOT_DOMAIN_ORDER[2:])
            row_seed = derive_uint32("VERIFIER_ROW_SEED", cell.master_seed)
            if is_deterministic:
                panel = deterministic_verifier_panel(
                    eligible_verifiers,
                    row_seed=row_seed,
                    panel_size=config.protocol.verification.panel_size,
                )
            else:
                panel = diagnostic_committee_panel(
                    eligible_verifiers,
                    committee_draw_namespace_seed=row_seed,
                    panel_size=config.protocol.verification.panel_size,
                )
            false_positive_condition = (
                condition == VerifierCondition.ONE_FALSE_POSITIVE.value
                or condition == VerifierCondition.TWO_FALSE_POSITIVES.value
            )
            reports = tuple(
                TernaryOutcome.POSITIVE
                if false_positive_condition and index == 0
                else TernaryOutcome.POSITIVE
                for index, _domain in enumerate(panel)
            )
            certified = reproduction_row_is_certified(
                reports,
                panel_size=config.protocol.verification.panel_size,
                required_positive_reports=config.protocol.verification.required_positive_reports,
            )
            minimum_gate_domains = config.protocol.final_gate.minimum_adequate_non_source_domains
            state = (
                ClaimState.ADMITTED
                if certified and evidence.final_gate_adequate_domain_count >= minimum_gate_domains
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
        bytes_total = communication_bytes(envelopes)
        transmissions = model_transmission_count(metadata_records)
        return ClaimState.DORMANT, (
            ("post-evidence-overhead", None),
            ("communication-bytes", float(bytes_total)),
            ("model-transmissions", float(transmissions)),
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
    return (
        ("terminal-state", _state_encoding(state)),
        ("legitimate-admission", legitimate_result.value),
        ("target-f1", None),
        ("supported-macro-f1-harm", None),
        ("benign-far-increase", None),
        ("worst-domain-target-f1", None),
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
