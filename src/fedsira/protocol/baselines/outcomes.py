from __future__ import annotations

from fedsira.datasets.common import Role, role_hash_token
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_CLASS_ORDER,
    NBAIOT_DOMAIN_ORDER,
    NBAIOT_TRIGGER_FEATURES,
    NBaiotClass,
    NBaiotDomain,
)
from fedsira.domain.enums import (
    AdmissionState,
    TernaryOutcome,
)
from fedsira.domain.models import (
    MetricResult,
)
from fedsira.evaluation.backdoor import (
    recovery_backdoor_alarm_threshold,
    triggered_to_benign_rate,
)
from fedsira.evaluation.domain import (
    evaluate_domain,
    non_source_domains,
)
from fedsira.evaluation.metrics import (
    supported_macro_f1_harm,
    target_capability_gain,
)
from fedsira.evaluation.summaries import (
    equal_weight_domain_mean,
    worst_domain_target_f1,
)
from fedsira.experiments.cell_support import (
    VERIFIER_ASSIGNMENT_NAMESPACE_SEPARATOR,
    _final_gate_decision_from_production_checkpoint,
    _source_domain_for_cell,
    _verifier_panel,
)
from fedsira.experiments.planning import (
    ScientificCell,
)
from fedsira.experiments.prerequisites import (
    PreparedEvidenceCounts,
)
from fedsira.experiments.workflow import (
    flat_parameters_identity,
)
from fedsira.learning.post_reference_training import (
    train_source_candidate_delta,
)
from fedsira.learning.reference import (
    train_centralized_reference_checkpoint,
    train_local_only_reference_checkpoint,
)
from fedsira.protocol.admission import (
    final_gate_predicates_pass,
    median_domain_target_f1,
)
from fedsira.protocol.baselines.calibration import (
    recovery_rollback_is_triggered,
)
from fedsira.protocol.baselines.certified_ensemble import (
    evaluate_certified_ensemble,
    train_certified_ensemble_group_checkpoints,
)
from fedsira.protocol.baselines.fedavg_training import (
    train_fedavg_reference_delta,
    train_recovery_after_source_admission_delta,
    train_secure_continual_assessment_delta,
)
from fedsira.protocol.baselines.reconstruction_training import (
    train_source_update_sanitization_delta,
    train_update_reconstruction_filter_delta,
)
from fedsira.protocol.baselines.references import (
    local_only_reference_evaluation_is_domain_local,
)
from fedsira.protocol.baselines.registry import (
    review_style_baseline_outcome,
)
from fedsira.protocol.baselines.robust_training import (
    train_density_cluster_trimmed_mean_delta,
    train_krum_reference_delta,
)
from fedsira.protocol.baselines.source_model import (
    CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT,
    INDEPENDENT_LOCAL_REFERENCE_REQUIRED_POSITIVE_REVIEWS,
    INDEPENDENT_LOCAL_REFERENCE_REVIEWER_COUNT,
    SECURE_CONTINUAL_ASSESSMENT_REQUIRED_POSITIVE_REVIEWS,
    SECURE_CONTINUAL_ASSESSMENT_REVIEWER_COUNT,
    independent_local_reference_reviewer_is_positive,
)
from fedsira.protocol.capability_contract import (
    build_capability_contract,
    capability_contract_passes,
)
from fedsira.protocol.state_machine import (
    resolve_ternary_outcome,
)
from fedsira.protocol.synthesis import (
    synthesis_pending_transition,
)
from fedsira.protocol.verification import (
    deterministic_verifier_panel,
    panel_votes_are_one_per_domain,
    verifier_assignment_seed_for_row,
    verifier_is_eligible,
)
from fedsira.runtime import (
    current_application_context,
    derive_uint32,
)


class ProtocolBaselineOutcomes:
    def _client_review_outcome(self, cell: ScientificCell) -> AdmissionState:
        config = current_application_context().scientific_config
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        positive_report_count = 0
        if real_anchor is not None and source_domain is not None:
            backdoor_scope = self._backdoor_scope_for_cell(cell)
            source_delta = train_source_candidate_delta(
                self._prepared_root,
                cell.master_seed,
                real_anchor,
                source_domain,
                backdoor_scope=backdoor_scope,
            )
            if source_delta is not None and self._candidate_capability_contract_passes(
                real_anchor, source_domain, real_anchor.flat_parameters + source_delta
            ):
                positive_report_count = CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT
        return review_style_baseline_outcome(
            adequate_reviewer_count=CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT,
            positive_report_count=positive_report_count,
            panel_size=config.protocol.admission_opening.screen_domains,
            required_positive_reports=config.protocol.admission_opening.required_positive_screen_domains,
        )

    def _source_update_sanitization_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> AdmissionState:
        config = current_application_context().scientific_config
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None or source_domain is None:
            return AdmissionState.DORMANT
        clipped_delta = train_source_update_sanitization_delta(
            self._prepared_root, cell.master_seed, real_anchor, source_domain
        )
        if clipped_delta is None:
            return AdmissionState.DORMANT
        production_checkpoint = real_anchor.flat_parameters + clipped_delta
        positive_report_count = (
            CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT
            if self._candidate_capability_contract_passes(
                real_anchor, source_domain, production_checkpoint
            )
            else 0
        )
        review_state = review_style_baseline_outcome(
            adequate_reviewer_count=CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT,
            positive_report_count=positive_report_count,
            panel_size=config.protocol.admission_opening.screen_domains,
            required_positive_reports=config.protocol.admission_opening.required_positive_screen_domains,
        )
        if review_state is not AdmissionState.ADMITTED:
            return review_state
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            evidence,
            source_domain,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _source_release_after_full_external_check_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> AdmissionState:
        config = current_application_context().scientific_config
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None or source_domain is None:
            return AdmissionState.DORMANT
        source_delta = train_source_candidate_delta(
            self._prepared_root, cell.master_seed, real_anchor, source_domain
        )
        if source_delta is None:
            return AdmissionState.DORMANT
        production_checkpoint = real_anchor.flat_parameters + source_delta
        panel = _verifier_panel(
            source_domain, source_domain, cell.master_seed, config.protocol.verification
        )
        if not panel_votes_are_one_per_domain(panel):
            return AdmissionState.DORMANT
        reports = tuple(resolve_ternary_outcome(True, True) for _domain in panel)
        positive_report_count = sum(1 for report in reports if report is TernaryOutcome.POSITIVE)
        review_state = review_style_baseline_outcome(
            adequate_reviewer_count=len(panel),
            positive_report_count=positive_report_count,
            panel_size=config.protocol.verification.panel_size,
            required_positive_reports=config.protocol.verification.required_positive_reports,
        )
        if review_state is not AdmissionState.ADMITTED:
            return review_state
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            evidence,
            source_domain,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _recovery_after_source_admission_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> AdmissionState:
        config = current_application_context().scientific_config
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None or source_domain is None:
            return AdmissionState.DORMANT
        review_state = self._client_review_outcome(cell)
        if review_state is not AdmissionState.ADMITTED:
            return review_state
        source_delta = train_source_candidate_delta(
            self._prepared_root, cell.master_seed, real_anchor, source_domain
        )
        if source_delta is None:
            return AdmissionState.DORMANT
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
        alarm_threshold = recovery_backdoor_alarm_threshold(self._prepared_root, real_anchor)
        if anchor_verification is None or admitted_verification is None or alarm_threshold is None:
            return AdmissionState.DORMANT
        supported_macro_f1_drop = supported_macro_f1_harm(
            anchor_verification.supported_macro_f1, admitted_verification.supported_macro_f1
        )
        benign_far_increase = (
            MetricResult(
                value=admitted_verification.benign_far.value - anchor_verification.benign_far.value,
                denominator=1,
            )
            if admitted_verification.benign_far.value is not None
            and anchor_verification.benign_far.value is not None
            else MetricResult(value=None, denominator=0)
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
                self._prepared_root, cell.master_seed, real_anchor, source_domain
            )
            if recovery_delta is None:
                return AdmissionState.DORMANT
            production_checkpoint = real_anchor.flat_parameters + recovery_delta
        else:
            production_checkpoint = admitted_checkpoint
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            evidence,
            source_domain,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _fedavg_reference_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> AdmissionState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None:
            return AdmissionState.DORMANT
        delta = train_fedavg_reference_delta(
            self._prepared_root, cell.master_seed, real_anchor, source_domain
        )
        if delta is None:
            return AdmissionState.DORMANT
        production_checkpoint = real_anchor.flat_parameters + delta
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            evidence,
            source_domain,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _krum_reference_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> AdmissionState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None:
            return AdmissionState.DORMANT
        delta = train_krum_reference_delta(
            self._prepared_root, cell.master_seed, real_anchor, source_domain
        )
        if delta is None:
            return AdmissionState.DORMANT
        production_checkpoint = real_anchor.flat_parameters + delta
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            evidence,
            source_domain,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _density_cluster_trimmed_mean_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> AdmissionState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None:
            return AdmissionState.DORMANT
        delta = train_density_cluster_trimmed_mean_delta(
            self._prepared_root, cell.master_seed, real_anchor, source_domain
        )
        if delta is None:
            return AdmissionState.DORMANT
        production_checkpoint = real_anchor.flat_parameters + delta
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            evidence,
            source_domain,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _update_reconstruction_filter_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> AdmissionState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None:
            return AdmissionState.DORMANT
        delta = train_update_reconstruction_filter_delta(
            self._prepared_root, cell.master_seed, real_anchor, source_domain
        )
        if delta is None:
            return AdmissionState.DORMANT
        production_checkpoint = real_anchor.flat_parameters + delta
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            evidence,
            source_domain,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _secure_continual_assessment_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> AdmissionState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None:
            return AdmissionState.DORMANT
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
        if review_state is not AdmissionState.ADMITTED:
            return review_state
        delta = train_secure_continual_assessment_delta(
            self._prepared_root, cell.master_seed, real_anchor, source_domain
        )
        if delta is None:
            return AdmissionState.DORMANT
        production_checkpoint = real_anchor.flat_parameters + delta
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            evidence,
            source_domain,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _local_only_reference_outcome(self, cell: ScientificCell) -> AdmissionState:
        config = current_application_context().scientific_config
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None:
            return AdmissionState.DORMANT
        target_f1_values: list[MetricResult] = []
        supported_f1_harms: list[MetricResult] = []
        benign_far_increases: list[MetricResult] = []
        for domain in non_source_domains(source_domain):
            if not local_only_reference_evaluation_is_domain_local(domain, domain):
                continue
            local_checkpoint = train_local_only_reference_checkpoint(
                self._prepared_root, cell.master_seed, domain
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
                        value=local_metrics.benign_far.value - anchor_metrics.benign_far.value,
                        denominator=1,
                    )
                )
            else:
                benign_far_increases.append(MetricResult(value=None, denominator=0))
        predicates_pass = final_gate_predicates_pass(
            median_domain_target_f1(target_f1_values),
            worst_domain_target_f1(tuple(target_f1_values)),
            equal_weight_domain_mean(tuple(supported_f1_harms), 1),
            equal_weight_domain_mean(tuple(benign_far_increases), 1),
            True,
            config.protocol.final_gate,
        )
        return synthesis_pending_transition(
            adequate_final_gate_domain_count=len(target_f1_values),
            final_gate_predicates_pass=predicates_pass,
            final_gate_config=config.protocol.final_gate,
        )

    def _multiple_model_certified_ensemble_outcome(self, cell: ScientificCell) -> AdmissionState:
        config = current_application_context().scientific_config
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None:
            return AdmissionState.DORMANT
        group_checkpoints = train_certified_ensemble_group_checkpoints(
            self._prepared_root, cell.master_seed
        )
        if group_checkpoints is None:
            return AdmissionState.DORMANT
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
                        value=ensemble_metrics.benign_far.value - anchor_metrics.benign_far.value,
                        denominator=1,
                    )
                )
            else:
                benign_far_increases.append(MetricResult(value=None, denominator=0))
        predicates_pass = final_gate_predicates_pass(
            median_domain_target_f1(target_f1_values),
            worst_domain_target_f1(tuple(target_f1_values)),
            equal_weight_domain_mean(tuple(supported_f1_harms), 1),
            equal_weight_domain_mean(tuple(benign_far_increases), 1),
            True,
            config.protocol.final_gate,
        )
        return synthesis_pending_transition(
            adequate_final_gate_domain_count=len(target_f1_values),
            final_gate_predicates_pass=predicates_pass,
            final_gate_config=config.protocol.final_gate,
        )

    def _centralized_reference_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> AdmissionState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None:
            return AdmissionState.DORMANT
        production_checkpoint = train_centralized_reference_checkpoint(
            self._prepared_root, cell.master_seed
        )
        if production_checkpoint is None:
            return AdmissionState.DORMANT
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            evidence,
            source_domain,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _independent_local_reference_outcome(self, cell: ScientificCell) -> AdmissionState:
        config = current_application_context().scientific_config
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None or source_domain is None:
            return AdmissionState.DORMANT
        source_delta = train_source_candidate_delta(
            self._prepared_root, cell.master_seed, real_anchor, source_domain
        )
        if source_delta is None:
            return AdmissionState.DORMANT
        source_screen = evaluate_domain(
            self._prepared_root,
            real_anchor,
            real_anchor.flat_parameters + source_delta,
            source_domain,
            role=Role.POST_REFERENCE_REPLAY,
            target_role=Role.CANDIDATE_SCREEN,
        )
        if source_screen is None:
            return AdmissionState.DORMANT
        contract = build_capability_contract(
            real_anchor.dataset_manifest_hash,
            role_hash_token(Role.POST_REFERENCE_REPLAY),
            config.datasets.primary.name,
            len(NBAIOT_DOMAIN_ORDER),
            real_anchor.dataset_manifest_hash,
            NBaiotClass.GAFGYT_COMBO,
            len(NBAIOT_CLASS_ORDER) - 1,
            config.capability_contract,
        )
        anchor_screen = evaluate_domain(
            self._prepared_root,
            real_anchor,
            real_anchor.flat_parameters,
            source_domain,
            role=Role.POST_REFERENCE_REPLAY,
            target_role=Role.CANDIDATE_SCREEN,
        )
        source_satisfies_capability_contract = (
            anchor_screen is not None
            and capability_contract_passes(
                contract,
                source_screen.target_f1,
                target_capability_gain(source_screen.target_f1, anchor_screen.target_f1),
                supported_macro_f1_harm(
                    anchor_screen.supported_macro_f1, source_screen.supported_macro_f1
                ),
                MetricResult(
                    value=source_screen.benign_far.value - anchor_screen.benign_far.value,
                    denominator=1,
                )
                if source_screen.benign_far.value is not None
                and anchor_screen.benign_far.value is not None
                else MetricResult(value=None, denominator=0),
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
        reviewer_domains = tuple(
            NBaiotDomain(domain)
            for domain in deterministic_verifier_panel(
                eligible_reviewer_domains,
                reviewer_assignment_seed,
                INDEPENDENT_LOCAL_REFERENCE_REVIEWER_COUNT,
            )
        )
        positive_report_count = 0
        for reviewer_domain in reviewer_domains:
            local_checkpoint = train_local_only_reference_checkpoint(
                self._prepared_root, cell.master_seed, reviewer_domain
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
                or (source_screen.benign_far.value is None)
                or (local_screen.benign_far.value is None)
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
