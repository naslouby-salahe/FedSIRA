from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import torch

from fedsira.artifacts.paths import prepared_evidence_root
from fedsira.datasets.ciciot2023.schema import TARGET_LABEL as CICIOT2023_TARGET_LABEL
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
    DatasetId,
    ExperimentLifecycleState,
    FailureClass,
    ScientificCellPhase,
)
from fedsira.domain.models import (
    MetricResult,
)
from fedsira.domain.types import (
    BooleanValue,
    MasterSeed,
    MetricObservation,
)
from fedsira.evaluation.domain import (
    evaluate_domain,
)
from fedsira.evaluation.metrics import (
    supported_macro_f1_harm,
    target_capability_gain,
)
from fedsira.evaluation.report_summary import RealReportSummary
from fedsira.experiments.cell_support import (
    _metrics_from_state,
)
from fedsira.experiments.cells import ProtocolCellDispatch
from fedsira.experiments.collapse import ResolvedCore
from fedsira.experiments.definitions import (
    ADMISSION_DELAY_DECOMPOSITION_NAME,
    BASELINE_IMPLEMENTATION_VALIDATION_NAME,
    BYZANTINE_BOUND_VIOLATION_NAME,
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
    DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
    EXTERNAL_VERIFICATION_NECESSITY_NAME,
    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
    MECHANISM_ABLATION_NAME,
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME,
    PROTOCOL_INVARIANT_VALIDATION_NAME,
    SECONDARY_DATASET_GENERALIZATION_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
    SINGLE_REPRODUCTION_NECESSITY_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    HeterogeneityRegime,
    ProposalEpisode,
    experiment_by_name,
)
from fedsira.experiments.execution import (
    CellExecutionOutcome,
    CellExecutor,
    ProtocolPhaseDurations,
)
from fedsira.experiments.planning import (
    ScientificCell,
)
from fedsira.experiments.prerequisites import (
    PreparedEvidenceCounts,
    load_prepared_evidence_counts,
)
from fedsira.experiments.scenarios import (
    select_heterogeneity_shift_features,
)
from fedsira.experiments.validation import (
    run_data_and_domain_evidence_validation,
    run_protocol_invariant_validation,
)
from fedsira.experiments.workflow import (
    BackdoorScope,
    HeterogeneityScope,
    RealAnchor,
    RootCauseScope,
    domain_anchor_train_feature_mean,
    prepared_feature_names,
    real_evidence_available,
)
from fedsira.learning.anchor_training import train_anchor
from fedsira.protocol.baselines.calibration import (
    DomainFeatureMean,
    same_context_verifier_panel,
)
from fedsira.protocol.baselines.outcomes import ProtocolBaselineOutcomes
from fedsira.protocol.capability_contract import (
    build_capability_contract,
    capability_contract_passes,
)
from fedsira.protocol.verification import (
    verifier_is_eligible,
)
from fedsira.runtime import (
    FailureDetail,
    current_application_context,
    derive_uint32,
)


class ProtocolCellExecutor(CellExecutor, ProtocolBaselineOutcomes, ProtocolCellDispatch):
    def __init__(
        self,
        primary_prepared_root: Path | None = None,
        secondary_prepared_root: Path | None = None,
        resolved_core: ResolvedCore | None = None,
    ) -> None:
        self._prepared_root = primary_prepared_root or prepared_evidence_root(DatasetId.N_BAIOT)
        self._secondary_prepared_root = secondary_prepared_root or prepared_evidence_root(
            DatasetId.CICIOT2023
        )
        self._resolved_core = resolved_core
        self._real_anchor_cache: OrderedDict[MasterSeed, RealAnchor | None] = OrderedDict()
        self._pending_real_report: RealReportSummary | None = None
        self._last_protocol_phase_durations = ProtocolPhaseDurations()

    def _real_anchor(self, master_seed: MasterSeed) -> RealAnchor | None:
        if master_seed not in self._real_anchor_cache:
            self._real_anchor_cache[master_seed] = (
                train_anchor(self._prepared_root, master_seed)
                if real_evidence_available(self._prepared_root)
                else None
            )
        return self._real_anchor_cache[master_seed]

    def _same_context_verifier_panel(
        self,
        source_domain: NBaiotDomain | None,
        reproducer_domain: NBaiotDomain,
    ) -> tuple[NBaiotDomain, ...]:
        config = current_application_context().scientific_config
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
                "same-context verification requires real anchor-train features for "
                f"{reproducer_domain}"
            )
        eligible_verifier_feature_means: list[DomainFeatureMean] = []
        for domain in eligible_verifiers:
            feature_mean = domain_anchor_train_feature_mean(self._prepared_root, domain)
            if feature_mean is None:
                raise ValueError(
                    f"same-context verification requires real anchor-train features for {domain}"
                )
            eligible_verifier_feature_means.append(
                DomainFeatureMean(domain=domain, feature_mean=feature_mean)
            )
        return same_context_verifier_panel(
            reproducer_feature_mean,
            tuple(eligible_verifier_feature_means),
            config.protocol.verification.panel_size,
        )

    def _candidate_capability_contract_passes(
        self,
        real_anchor: RealAnchor,
        source_domain: NBaiotDomain,
        candidate_flat_parameters: torch.Tensor,
    ) -> BooleanValue:
        config = current_application_context().scientific_config
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
        target_f1_gain = target_capability_gain(candidate_screen.target_f1, anchor_screen.target_f1)
        supported_macro_f1_drop = supported_macro_f1_harm(
            anchor_screen.supported_macro_f1, candidate_screen.supported_macro_f1
        )
        benign_far_increase = (
            MetricResult(
                value=candidate_screen.benign_far.value - anchor_screen.benign_far.value,
                denominator=1,
            )
            if candidate_screen.benign_far.value is not None
            and anchor_screen.benign_far.value is not None
            else MetricResult(value=None, denominator=0)
        )
        return capability_contract_passes(
            contract,
            candidate_screen.target_f1,
            target_f1_gain,
            supported_macro_f1_drop,
            benign_far_increase,
        )

    def _scoped_capability_contract_passes(
        self,
        real_anchor: RealAnchor,
        source_domain: NBaiotDomain,
        candidate_flat_parameters: torch.Tensor,
        root_cause_scope: RootCauseScope,
    ) -> BooleanValue:
        config = current_application_context().scientific_config
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
        target_f1_gain = target_capability_gain(candidate_screen.target_f1, anchor_screen.target_f1)
        supported_macro_f1_drop = supported_macro_f1_harm(
            anchor_screen.supported_macro_f1, candidate_screen.supported_macro_f1
        )
        benign_far_increase = (
            MetricResult(
                value=candidate_screen.benign_far.value - anchor_screen.benign_far.value,
                denominator=1,
            )
            if candidate_screen.benign_far.value is not None
            and anchor_screen.benign_far.value is not None
            else MetricResult(value=None, denominator=0)
        )
        return capability_contract_passes(
            contract,
            candidate_screen.target_f1,
            target_f1_gain,
            supported_macro_f1_drop,
            benign_far_increase,
        )

    def _backdoor_scope_for_cell(self, cell: ScientificCell) -> BackdoorScope | None:
        config = current_application_context().scientific_config
        if cell.condition != ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT:
            return None
        real_feature_names = prepared_feature_names(self._prepared_root)
        if real_feature_names is None:
            return None
        trigger_indices = tuple(real_feature_names.index(name) for name in NBAIOT_TRIGGER_FEATURES)
        return BackdoorScope(
            attack_generation_seed=derive_uint32("ATTACK_GENERATION_SEED", cell.master_seed),
            poison_fraction=config.attacks_and_boundaries.hidden_source_backdoor.confirmatory_poison_fraction,
            trigger_feature_indices=trigger_indices,
            trigger_value=config.attacks_and_boundaries.hidden_source_backdoor.trigger_value_after_standardization,
        )

    def _heterogeneity_scope_for_cell(self, cell: ScientificCell) -> HeterogeneityScope | None:
        config = current_application_context().scientific_config
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

    def execute_cell(self, cell: ScientificCell) -> CellExecutionOutcome:
        self._pending_real_report = None
        dataset = experiment_by_name(cell.experiment).dataset
        if dataset is DatasetId.CICIOT2023:
            prepared_root = self._secondary_prepared_root
            target_class_token = CICIOT2023_TARGET_LABEL
        else:
            prepared_root = self._prepared_root
            target_class_token = NBaiotClass.GAFGYT_COMBO
        if cell.experiment == PROTOCOL_INVARIANT_VALIDATION_NAME:
            evidence = PreparedEvidenceCounts(
                screen_target_count=0,
                reproduction_target_count=0,
                reproduction_supported_count=0,
                final_gate_adequate_domain_count=0,
            )
        else:
            evidence = load_prepared_evidence_counts(prepared_root, target_class_token)
            if evidence is None:
                return CellExecutionOutcome(
                    cell=cell,
                    terminal_state=ExperimentLifecycleState.INVALID,
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
            _state, metrics = self._execute_cell_protocol(cell, evidence)
        except ValueError as error:
            return CellExecutionOutcome(
                cell=cell,
                terminal_state=ExperimentLifecycleState.INVALID,
                failure=FailureDetail(
                    failure_class=FailureClass.INVARIANT_VIOLATION,
                    message=str(error),
                    cell_phase=ScientificCellPhase.PREPARE,
                ),
            )
        return CellExecutionOutcome(
            cell=cell,
            terminal_state=ExperimentLifecycleState.COMPLETED,
            failure=None,
            metrics=metrics,
        )

    def _execute_cell_protocol(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        if cell.experiment == PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME:
            return self._execute_opening_cell(cell, evidence)
        if cell.experiment == SINGLE_REPRODUCTION_NECESSITY_NAME:
            return self._execute_plurality_cell(cell, evidence)
        if cell.experiment == SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME:
            return self._execute_source_exclusion_cell(cell, evidence)
        if cell.experiment == EXTERNAL_VERIFICATION_NECESSITY_NAME:
            return self._execute_external_verification_cell(cell, evidence)
        if cell.experiment == PRIMARY_CONFIRMATORY_EVALUATION_NAME:
            return self._execute_primary_cell(cell, evidence)
        if cell.experiment == COMPROMISED_REPRODUCER_ROBUSTNESS_NAME:
            return self._execute_reproducer_robustness_cell(cell, evidence)
        if cell.experiment == COMPROMISED_VERIFIER_ROBUSTNESS_NAME:
            return self._execute_verifier_robustness_cell(cell, evidence)
        if cell.experiment == BYZANTINE_BOUND_VIOLATION_NAME:
            return self._execute_byzantine_bound_cell(cell, evidence)
        if cell.experiment == EFFICIENCY_MEASUREMENT_NAME:
            return self._execute_efficiency_cell(cell, evidence)
        if cell.experiment == SECONDARY_DATASET_GENERALIZATION_NAME:
            return self._execute_secondary_cell(cell, evidence)
        if cell.experiment == EVIDENCE_SCARCITY_AND_DORMANCY_NAME:
            return self._execute_evidence_scarcity_cell(cell, evidence)
        if cell.experiment == ADMISSION_DELAY_DECOMPOSITION_NAME:
            return self._execute_admission_delay_cell(cell, evidence)
        if cell.experiment in (
            SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
            CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
            HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
        ):
            return self._execute_boundary_cell(cell, evidence)
        if cell.experiment == MECHANISM_ABLATION_NAME:
            return self._execute_ablation_cell(cell, evidence)
        if cell.experiment == DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME:
            run_data_and_domain_evidence_validation(
                evidence.reproduction_target_count,
                evidence.reproduction_supported_count,
                evidence.final_gate_adequate_domain_count,
            )
            return (AdmissionState.ADMITTED, _metrics_from_state(AdmissionState.ADMITTED))
        if cell.experiment == PROTOCOL_INVARIANT_VALIDATION_NAME:
            run_protocol_invariant_validation()
            return (AdmissionState.ADMITTED, _metrics_from_state(AdmissionState.ADMITTED))
        if cell.experiment == BASELINE_IMPLEMENTATION_VALIDATION_NAME:
            return self._execute_baseline_cell(cell, evidence)
        raise ValueError(f"no protocol executor is defined for experiment {cell.experiment}")
