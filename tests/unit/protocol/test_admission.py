import pytest
import torch

from fedsira.config import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import AdmissionState
from fedsira.domain.models import MetricResult
from fedsira.protocol.admission import (
    apply_production_update,
    final_gate_predicates_pass,
    median_domain_target_f1,
    resolve_production_update,
    validate_admission_requires_final_gate,
    validate_production_checkpoint_excludes_source,
)

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
FINAL_GATE_CONFIG = CONFIG.protocol.final_gate


def test_admitted_state_requires_valid_final_gate_artifact() -> None:
    validate_admission_requires_final_gate(AdmissionState.ADMITTED, True)
    with pytest.raises(ValueError, match="final-gate"):
        validate_admission_requires_final_gate(AdmissionState.ADMITTED, False)


def test_non_admitted_state_does_not_require_final_gate_artifact() -> None:
    validate_admission_requires_final_gate(AdmissionState.DORMANT, False)


def test_apply_production_update_is_anchor_plus_update() -> None:
    anchor = torch.tensor([1.0, 2.0, 3.0])
    update = torch.tensor([0.5, -0.5, 1.0])
    production_model = apply_production_update(anchor, update)
    assert torch.allclose(production_model, torch.tensor([1.5, 1.5, 4.0]))


def test_resolve_production_update_plurality_path_uses_krum_selection() -> None:
    krum_update = torch.tensor([1.0])
    result = resolve_production_update(True, krum_update, None)
    assert result is krum_update
    with pytest.raises(ValueError, match="plurality"):
        resolve_production_update(True, None, torch.tensor([2.0]))


def test_resolve_production_update_single_reproduction_path() -> None:
    single_update = torch.tensor([3.0])
    result = resolve_production_update(False, None, single_update)
    assert result is single_update
    with pytest.raises(ValueError, match="single-reproduction"):
        resolve_production_update(False, torch.tensor([1.0]), None)


def test_validate_production_checkpoint_excludes_source() -> None:
    production_update = torch.tensor([1.0, 2.0])
    validate_production_checkpoint_excludes_source(production_update, None)
    validate_production_checkpoint_excludes_source(production_update, torch.tensor([9.0, 9.0]))
    with pytest.raises(ValueError, match="source"):
        validate_production_checkpoint_excludes_source(production_update, production_update.clone())


def test_median_domain_target_f1_uses_type7_quantile() -> None:
    values = [MetricResult(value=v, denominator=10) for v in [0.6, 0.7, 0.8, 0.9]]
    result = median_domain_target_f1(values)
    assert result.value is not None
    assert abs(result.value - 0.75) < 1e-9


def test_median_domain_target_f1_na_when_nothing_defined() -> None:
    assert median_domain_target_f1([MetricResult(value=None, denominator=0)]).value is None


def test_final_gate_predicates_pass_requires_all_four_thresholds_and_no_invariant_failure() -> None:
    passing = final_gate_predicates_pass(
        MetricResult(value=FINAL_GATE_CONFIG.median_target_f1_minimum, denominator=8),
        MetricResult(value=FINAL_GATE_CONFIG.minimum_domain_target_f1, denominator=8),
        MetricResult(value=FINAL_GATE_CONFIG.supported_macro_f1_drop_maximum, denominator=8),
        MetricResult(
            value=FINAL_GATE_CONFIG.benign_false_alarm_rate_increase_maximum, denominator=8
        ),
        True,
        FINAL_GATE_CONFIG,
    )
    assert passing
    fails_on_invariant = final_gate_predicates_pass(
        MetricResult(value=1.0, denominator=8),
        MetricResult(value=1.0, denominator=8),
        MetricResult(value=0.0, denominator=8),
        MetricResult(value=0.0, denominator=8),
        False,
        FINAL_GATE_CONFIG,
    )
    assert not fails_on_invariant
    fails_on_na = final_gate_predicates_pass(
        MetricResult(value=None, denominator=0),
        MetricResult(value=1.0, denominator=8),
        MetricResult(value=0.0, denominator=8),
        MetricResult(value=0.0, denominator=8),
        True,
        FINAL_GATE_CONFIG,
    )
    assert not fails_on_na
