from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch

from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.evaluation.domain import evaluate_domain, non_source_domains
from fedsira.datasets.nbaiot.schema import NBaiotDomain
from fedsira.datasets.nbaiot.workflow import RealAnchor
from fedsira.domain.enums import AdmissionState
from fedsira.domain.models import MetricResult
from fedsira.domain.types import MetricObservation, MetricValue
from fedsira.evaluation.comparisons import ComparisonMetric
from fedsira.evaluation.metrics import (
    dormant_admission_rate,
    legitimate_admission_rate,
    supported_macro_f1_harm,
)
from fedsira.evaluation.summaries import (
    coefficient_of_variation,
    domain_disparity,
    equal_weight_domain_mean,
    interquartile_range,
    percentile_10_domain_target_f1,
    worst_domain_target_f1,
)
from fedsira.experiments.definitions import DescriptiveScientificMetric


@dataclass(frozen=True)
class RealReportSummary:
    target_f1: MetricResult
    worst_domain_target_f1: MetricResult
    p10_domain_target_f1: MetricResult
    domain_disparity: MetricResult
    domain_iqr: MetricResult
    coefficient_of_variation: MetricResult
    supported_macro_f1_harm: MetricResult
    benign_far_increase: MetricResult


def compute_real_report_summary(
    prepared_root: Path,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
    production_checkpoint: torch.Tensor,
) -> RealReportSummary | None:
    target_f1_values: list[MetricResult] = []
    supported_f1_harms: list[MetricResult] = []
    benign_far_increases: list[MetricResult] = []
    for domain in non_source_domains(source_domain):
        anchor_metrics = evaluate_domain(
            prepared_root, anchor, anchor.flat_parameters, domain, Role.REPORT_TEST
        )
        production_metrics = evaluate_domain(
            prepared_root, anchor, production_checkpoint, domain, Role.REPORT_TEST
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
    if not target_f1_values:
        return None
    target_f1_tuple = tuple(target_f1_values)
    return RealReportSummary(
        target_f1=equal_weight_domain_mean(target_f1_tuple, 1),
        worst_domain_target_f1=worst_domain_target_f1(target_f1_tuple),
        p10_domain_target_f1=percentile_10_domain_target_f1(target_f1_tuple),
        domain_disparity=domain_disparity(target_f1_tuple),
        domain_iqr=interquartile_range(target_f1_tuple),
        coefficient_of_variation=coefficient_of_variation(
            tuple(result.value for result in target_f1_tuple if result.value is not None)
        ),
        supported_macro_f1_harm=equal_weight_domain_mean(tuple(supported_f1_harms), 1),
        benign_far_increase=equal_weight_domain_mean(tuple(benign_far_increases), 1),
    )


def undefined_metric() -> MetricResult:
    return MetricResult(value=None, denominator=0)


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


def metrics_from_state(
    state: AdmissionState,
    real_report: RealReportSummary | None = None,
    attack_success_rate: MetricResult | None = None,
) -> tuple[MetricObservation, ...]:
    is_admitted = state is AdmissionState.ADMITTED
    is_dormant = state is AdmissionState.DORMANT
    undefined = undefined_metric()
    asr = attack_success_rate if attack_success_rate is not None else undefined
    if real_report is None:
        target_f1 = undefined
        supported_macro_f1_harm_value = undefined
        benign_far_increase_value = undefined
        worst_domain = undefined
        p10_domain = undefined
        disparity = undefined
        iqr = undefined
        cv = undefined
        equal_weight_mean = undefined
    else:
        target_f1 = real_report.target_f1
        supported_macro_f1_harm_value = real_report.supported_macro_f1_harm
        benign_far_increase_value = real_report.benign_far_increase
        worst_domain = real_report.worst_domain_target_f1
        p10_domain = real_report.p10_domain_target_f1
        disparity = real_report.domain_disparity
        iqr = real_report.domain_iqr
        cv = real_report.coefficient_of_variation
        equal_weight_mean = real_report.target_f1
    return (
        ("terminal-state", _state_encoding(state)),
        (ComparisonMetric.LEGITIMATE_ADMISSION, legitimate_admission_rate([is_admitted]).value),
        (ComparisonMetric.TARGET_F1, target_f1.value),
        ("target-f1-gain", undefined.value),
        (ComparisonMetric.SUPPORTED_MACRO_F1_HARM, supported_macro_f1_harm_value.value),
        (ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE, benign_far_increase_value.value),
        (ComparisonMetric.ATTACK_SUCCESS_RATE, asr.value),
        ("accuracy", undefined.value),
        ("macro-f1", undefined.value),
        ("weighted-f1", undefined.value),
        ("balanced-accuracy", undefined.value),
        ("verifier-abstention-rate", undefined.value),
        ("reproduction-abstention-rate", undefined.value),
        (ComparisonMetric.WORST_DOMAIN_TARGET_F1, worst_domain.value),
        ("p10-domain-target-f1", p10_domain.value),
        ("domain-disparity", disparity.value),
        ("domain-iqr", iqr.value),
        ("coefficient-of-variation", cv.value),
        ("equal-weight-domain-mean-target-f1", equal_weight_mean.value),
        (ComparisonMetric.REPRODUCTION_ATTEMPTS, undefined.value),
        (ComparisonMetric.FALSE_LAUNCH, undefined.value),
        (ComparisonMetric.POST_EVIDENCE_OVERHEAD, undefined.value),
        (
            DescriptiveScientificMetric.DORMANT_ADMISSION_RATE.value,
            dormant_admission_rate(
                dormant_admission_count=1 if is_dormant else 0, eligible_admission_count=1
            ).value,
        ),
    )
