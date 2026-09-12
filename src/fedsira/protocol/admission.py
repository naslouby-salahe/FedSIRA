from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping, Sequence

import torch

from fedsira.config import FinalGateConfig
from fedsira.datasets.common import (
    DatasetAdapter,
    HeterogeneityScope,
    RealAnchor,
    Role,
)
from fedsira.domain.enums import AdmissionState
from fedsira.domain.models import MetricResult, PreparedEvidenceCounts
from fedsira.domain.types import (
    AdequateFinalGateDomainCount,
    BooleanValue,
    DomainId,
    FinalGateArtifactValid,
    FinalGatePredicatesPass,
    InvariantChecksPassed,
    MasterSeed,
    PluralityActive,
)
from fedsira.evaluation.metrics import (
    RealReportSummary,
    compute_real_report_summary,
    evaluate_domain,
    non_source_domains,
    supported_macro_f1_harm,
)
from fedsira.evaluation.statistics import (
    equal_weight_domain_mean,
    quantile_type7,
    worst_domain_target_f1,
)
from fedsira.learning.post_reference import (
    certified_domain_delta_committee,
    train_source_candidate_delta,
)
from fedsira.protocol.baselines.defenses import coordinate_wise_median_synthesis
from fedsira.protocol.synthesis import (
    CertifiedReproductionRow,
    select_krum_update,
    synthesis_pending_transition,
)
from fedsira.runtime import current_application_context


def validate_admission_requires_final_gate(
    state: AdmissionState, final_gate_artifact_is_valid: FinalGateArtifactValid
) -> None:
    if state is AdmissionState.ADMITTED and not final_gate_artifact_is_valid:
        raise ValueError("Admitted state requires a valid final-gate artifact")


def apply_production_update(
    anchor_flat_parameters: torch.Tensor, production_update: torch.Tensor
) -> torch.Tensor:
    return anchor_flat_parameters + production_update


def production_committee(
    committee_deltas: Mapping[DomainId, torch.Tensor],
    reproducer_order: Sequence[DomainId],
) -> tuple[CertifiedReproductionRow, ...]:
    return tuple(
        CertifiedReproductionRow(
            reproducer_domain=domain,
            update_vector=committee_deltas[domain],
        )
        for domain in reproducer_order
        if domain in committee_deltas
    )


def resolve_production_update(
    is_plurality_active: PluralityActive,
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
    defined_values = tuple(
        sorted(result.value for result in domain_target_f1 if result.value is not None)
    )
    if len(defined_values) == 0:
        return MetricResult(value=None, denominator=0)
    return MetricResult(value=quantile_type7(defined_values, 0.5), denominator=len(defined_values))


def final_gate_predicates_pass(
    median_target_f1: MetricResult,
    minimum_target_f1: MetricResult,
    pooled_supported_macro_f1_drop: MetricResult,
    pooled_benign_far_increase: MetricResult,
    no_invariant_failure: InvariantChecksPassed,
    final_gate_config: FinalGateConfig,
) -> FinalGatePredicatesPass:
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


def real_final_gate_metrics(
    adapter: DatasetAdapter,
    anchor: RealAnchor,
    source_domain: DomainId | None,
    production_checkpoint: torch.Tensor,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> tuple[AdequateFinalGateDomainCount, MetricResult, MetricResult, MetricResult, MetricResult]:
    candidate_domains = non_source_domains(adapter, source_domain)
    adequate_domains = tuple(
        domain
        for domain in candidate_domains
        if evaluate_domain(
            adapter,
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
            adapter,
            anchor,
            anchor.flat_parameters,
            domain,
            Role.FINAL_GATE,
            heterogeneity_scope=heterogeneity_scope,
        )
        production_metrics = evaluate_domain(
            adapter,
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
    source_domain: DomainId | None,
    reproducer_order: Sequence[DomainId],
    is_plurality_active: BooleanValue,
    adapter: DatasetAdapter,
    master_seed: MasterSeed,
    anchor: RealAnchor | None,
    coordinate_median_active: BooleanValue,
    no_final_synthesis_gate_active: BooleanValue,
    use_source_delta_for_source_domain: BooleanValue,
    force_first_row_to_source_delta: BooleanValue,
    heterogeneity_scope: HeterogeneityScope | None = None,
    precomputed_updates: OrderedDict[DomainId, torch.Tensor] | None = None,
) -> tuple[AdmissionState, RealReportSummary | None, torch.Tensor | None, torch.Tensor | None]:
    if anchor is None:
        return (AdmissionState.DORMANT, None, None, None)
    config = current_application_context().scientific_config
    base_flat_parameters = anchor.flat_parameters
    committee_deltas: OrderedDict[DomainId, torch.Tensor] = (
        OrderedDict(precomputed_updates)
        if precomputed_updates is not None
        else certified_domain_delta_committee(
            adapter,
            master_seed,
            anchor,
            reproducer_order,
            heterogeneity_scope=heterogeneity_scope,
        )
    )
    if use_source_delta_for_source_domain and source_domain is not None:
        source_delta = train_source_candidate_delta(adapter, master_seed, anchor, source_domain)
        if source_delta is not None:
            committee_deltas[source_domain] = source_delta
    if force_first_row_to_source_delta and source_domain is not None and reproducer_order:
        source_delta = train_source_candidate_delta(adapter, master_seed, anchor, source_domain)
        if source_delta is not None:
            committee_deltas[reproducer_order[0]] = source_delta
    available_updates = tuple(
        committee_deltas[domain] for domain in reproducer_order if domain in committee_deltas
    )
    if coordinate_median_active:
        if not available_updates:
            return (AdmissionState.DORMANT, None, None, None)
        production_update = coordinate_wise_median_synthesis(available_updates)
        production_checkpoint = apply_production_update(base_flat_parameters, production_update)
        median_state, median_report = final_gate_decision_from_production_checkpoint(
            evidence,
            source_domain,
            adapter,
            anchor,
            production_checkpoint,
            no_final_synthesis_gate_active,
            heterogeneity_scope=heterogeneity_scope,
        )
        return (median_state, median_report, production_checkpoint, None)
    krum_selected_update: torch.Tensor | None = None
    if is_plurality_active:
        committee = production_committee(committee_deltas, reproducer_order)
        if not committee:
            return (AdmissionState.DORMANT, None, None, None)
        krum_selected_update = select_krum_update(
            committee, config.protocol.synthesis.maximum_byzantine_reproduction_rows
        ).update_vector
    first_domain = next((domain for domain in reproducer_order if domain in committee_deltas), None)
    if first_domain is None and not is_plurality_active:
        return (AdmissionState.DORMANT, None, None, None)
    single_reproduction_update = (
        committee_deltas[first_domain] if first_domain is not None else None
    )
    production_update = resolve_production_update(
        is_plurality_active, krum_selected_update, single_reproduction_update
    )
    production_checkpoint = apply_production_update(base_flat_parameters, production_update)
    synthesis_state, synthesis_report = final_gate_decision_from_production_checkpoint(
        evidence,
        source_domain,
        adapter,
        anchor,
        production_checkpoint,
        no_final_synthesis_gate_active,
        heterogeneity_scope=heterogeneity_scope,
    )
    return (synthesis_state, synthesis_report, production_checkpoint, krum_selected_update)


def final_gate_decision_from_production_checkpoint(
    evidence: PreparedEvidenceCounts,
    source_domain: DomainId | None,
    adapter: DatasetAdapter,
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
    ) = real_final_gate_metrics(
        adapter,
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
        adapter, anchor, source_domain, production_checkpoint
    )
    if final_gate_state is not AdmissionState.ADMITTED:
        return (final_gate_state, real_report_summary)
    validate_production_checkpoint_excludes_source(production_checkpoint, None)
    validate_admission_requires_final_gate(AdmissionState.ADMITTED, True)
    return (AdmissionState.ADMITTED, real_report_summary)
