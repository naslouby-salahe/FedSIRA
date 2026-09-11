from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.evaluation.domain import evaluate_domain, non_source_domains
from fedsira.datasets.nbaiot.learning.post_reference_training import train_domain_reproduction_delta
from fedsira.datasets.nbaiot.schema import NBaiotDomain
from fedsira.datasets.nbaiot.workflow import RealAnchor, RootCauseScope
from fedsira.domain.enums import CapabilityContractScope
from fedsira.domain.models import MetricResult
from fedsira.domain.types import DomainCount, MasterSeed
from fedsira.evaluation.metrics import supported_macro_f1_harm
from fedsira.evaluation.summaries import equal_weight_domain_mean


@dataclass(frozen=True)
class CapabilityUnderSpecificationSummary:
    defined_domain_count: DomainCount
    aggregate_target_f1: MetricResult
    target_f1_gain: MetricResult
    supported_macro_f1_drop: MetricResult
    benign_far_increase: MetricResult
    root_cause_a_target_f1: MetricResult
    root_cause_b_target_f1: MetricResult


def _root_cause_scoped_scope(
    root_cause_scope: RootCauseScope,
    contract_scope: CapabilityContractScope,
) -> RootCauseScope:
    return replace(root_cause_scope, contract_scope=contract_scope)


def compute_capability_under_specification_summary(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
    root_cause_scope: RootCauseScope,
) -> CapabilityUnderSpecificationSummary:
    target_f1_values: list[MetricResult] = []
    anchor_target_f1_values: list[MetricResult] = []
    supported_f1_harms: list[MetricResult] = []
    benign_far_increases: list[MetricResult] = []
    root_cause_a_target_f1_values: list[MetricResult] = []
    root_cause_b_target_f1_values: list[MetricResult] = []
    a_scoped_scope = _root_cause_scoped_scope(
        root_cause_scope, CapabilityContractScope.ROOT_CAUSE_A_SCOPED
    )
    b_scoped_scope = _root_cause_scoped_scope(
        root_cause_scope, CapabilityContractScope.ROOT_CAUSE_B_SCOPED
    )
    for domain in non_source_domains(source_domain):
        delta = train_domain_reproduction_delta(
            prepared_root, master_seed, anchor, domain, root_cause_scope
        )
        if delta is None:
            continue
        production_flat = anchor.flat_parameters + delta
        anchor_metrics = evaluate_domain(
            prepared_root,
            anchor,
            anchor.flat_parameters,
            domain,
            Role.REPORT_TEST,
            root_cause_scope=root_cause_scope,
        )
        scoped_metrics = evaluate_domain(
            prepared_root,
            anchor,
            production_flat,
            domain,
            Role.REPORT_TEST,
            root_cause_scope=root_cause_scope,
        )
        if anchor_metrics is None or scoped_metrics is None:
            continue
        target_f1_values.append(scoped_metrics.target_f1)
        anchor_target_f1_values.append(anchor_metrics.target_f1)
        supported_f1_harms.append(
            supported_macro_f1_harm(
                anchor_metrics.supported_macro_f1, scoped_metrics.supported_macro_f1
            )
        )
        if anchor_metrics.benign_far.value is None or scoped_metrics.benign_far.value is None:
            benign_far_increases.append(MetricResult(value=None, denominator=0))
        else:
            benign_far_increases.append(
                MetricResult(
                    value=scoped_metrics.benign_far.value - anchor_metrics.benign_far.value,
                    denominator=1,
                )
            )
        a_scoped_metrics = evaluate_domain(
            prepared_root,
            anchor,
            production_flat,
            domain,
            Role.REPORT_TEST,
            root_cause_scope=a_scoped_scope,
        )
        b_scoped_metrics = evaluate_domain(
            prepared_root,
            anchor,
            production_flat,
            domain,
            Role.REPORT_TEST,
            root_cause_scope=b_scoped_scope,
        )
        if a_scoped_metrics is not None:
            root_cause_a_target_f1_values.append(a_scoped_metrics.target_f1)
        if b_scoped_metrics is not None:
            root_cause_b_target_f1_values.append(b_scoped_metrics.target_f1)
    aggregate_target_f1 = equal_weight_domain_mean(tuple(target_f1_values), 1)
    anchor_target_f1 = equal_weight_domain_mean(tuple(anchor_target_f1_values), 1)
    target_f1_gain = (
        MetricResult(value=aggregate_target_f1.value - anchor_target_f1.value, denominator=1)
        if aggregate_target_f1.value is not None and anchor_target_f1.value is not None
        else MetricResult(value=None, denominator=0)
    )
    return CapabilityUnderSpecificationSummary(
        defined_domain_count=len(target_f1_values),
        aggregate_target_f1=aggregate_target_f1,
        target_f1_gain=target_f1_gain,
        supported_macro_f1_drop=equal_weight_domain_mean(tuple(supported_f1_harms), 1),
        benign_far_increase=equal_weight_domain_mean(tuple(benign_far_increases), 1),
        root_cause_a_target_f1=equal_weight_domain_mean(tuple(root_cause_a_target_f1_values), 1),
        root_cause_b_target_f1=equal_weight_domain_mean(tuple(root_cause_b_target_f1_values), 1),
    )
