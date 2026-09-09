from collections.abc import Sequence

import torch

from fedsira.config import FinalGateConfig
from fedsira.domain.enums import AdmissionState
from fedsira.domain.models import MetricResult
from fedsira.domain.types import (
    FinalGateArtifactValid,
    FinalGatePredicatesPass,
    InvariantChecksPassed,
    PluralityActive,
)
from fedsira.evaluation.summaries import quantile_type7


def validate_admission_requires_final_gate(
    state: AdmissionState, final_gate_artifact_is_valid: FinalGateArtifactValid
) -> None:
    if state is AdmissionState.ADMITTED and not final_gate_artifact_is_valid:
        raise ValueError("Admitted state requires a valid final-gate artifact")


def apply_production_update(
    anchor_flat_parameters: torch.Tensor, production_update: torch.Tensor
) -> torch.Tensor:
    return anchor_flat_parameters + production_update


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
