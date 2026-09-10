from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch

from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.schema import NBaiotDomain
from fedsira.domain.models import MetricResult
from fedsira.evaluation.domain import evaluate_domain, non_source_domains
from fedsira.evaluation.metrics import supported_macro_f1_harm
from fedsira.evaluation.summaries import (
    coefficient_of_variation,
    domain_disparity,
    equal_weight_domain_mean,
    interquartile_range,
    percentile_10_domain_target_f1,
    worst_domain_target_f1,
)
from fedsira.experiments.workflow import RealAnchor


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
