from pathlib import Path

import pytest
import torch

from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER
from fedsira.domain.enums import TernaryOutcome
from fedsira.protocol.capability_contract import validate_source_excluded_production_weight
from fedsira.protocol.rules import minimum_honest_positive_count
from fedsira.protocol.synthesis import (
    CertifiedReproductionRow,
    krum_input_excludes_source,
    require_source_identity_excluded_from_synthesis,
    select_krum_update,
)
from fedsira.protocol.verification import reproduction_row_is_certified
from fedsira.runtime import current_application_context

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_source_excluded_production_weight_is_zero() -> None:
    validate_source_excluded_production_weight(0.0)


def test_krum_input_rejects_source_row_identity() -> None:
    assert krum_input_excludes_source(("reproducer-a", "reproducer-b"), None)
    assert krum_input_excludes_source(("reproducer-a", "reproducer-b"), "reproducer-c")
    assert not krum_input_excludes_source(("reproducer-a", "reproducer-b"), "reproducer-a")


def test_synthesis_guard_rejects_a_missing_or_present_source_identity() -> None:
    require_source_identity_excluded_from_synthesis(("reproducer-a",), "reproducer-b")
    with pytest.raises(ValueError, match="source identity is absent"):
        require_source_identity_excluded_from_synthesis(("reproducer-a",), None)
    with pytest.raises(ValueError, match="source identity entered the synthesis committee"):
        require_source_identity_excluded_from_synthesis(("reproducer-a",), "reproducer-a")


def test_source_exclusion_cell_checks_the_rows_just_synthesized() -> None:
    source = (REPO_ROOT / "src/fedsira/experiments/handlers.py").read_text(encoding="utf-8")
    assert "require_source_identity_excluded_from_synthesis" in source
    assert "_last_synthesis_row_ids" in source
    assert "source_row_id=None" not in source


def test_configured_quorum_rejects_a_lone_positive_and_survives_one_dissent() -> None:
    verification = current_application_context().scientific_config.protocol.verification
    panel_size = verification.panel_size
    required = verification.required_positive_reports
    byzantine_budget = verification.maximum_byzantine_verifiers_per_panel
    assert required == byzantine_budget + 1
    assert required < panel_size
    assert minimum_honest_positive_count(required, byzantine_budget) == 1
    dissent = (TernaryOutcome.POSITIVE, TernaryOutcome.POSITIVE, TernaryOutcome.NEGATIVE)
    lone = (TernaryOutcome.POSITIVE, TernaryOutcome.NEGATIVE, TernaryOutcome.NEGATIVE)
    assert reproduction_row_is_certified(dissent, panel_size, required)
    assert not reproduction_row_is_certified(lone, panel_size, required)


def _vector_row(index: int, value: float) -> CertifiedReproductionRow:
    return CertifiedReproductionRow(
        reproducer_domain=NBAIOT_DOMAIN_ORDER[index],
        update_vector=torch.tensor([value], dtype=torch.float64),
    )


def test_krum_rejects_an_outlier_and_can_select_an_in_ball_non_source_payload() -> None:
    outlier = (
        _vector_row(0, 0.0),
        _vector_row(1, 0.1),
        _vector_row(2, 0.2),
        _vector_row(3, 0.15),
        _vector_row(4, 50.0),
    )
    assert select_krum_update(outlier, 1).reproducer_domain != NBAIOT_DOMAIN_ORDER[4]
    in_ball = (
        _vector_row(0, 0.0),
        _vector_row(1, 3.0),
        _vector_row(2, 6.0),
        _vector_row(3, 9.0),
        _vector_row(4, 4.5),
    )
    selected = select_krum_update(in_ball, 1)
    assert selected.reproducer_domain == NBAIOT_DOMAIN_ORDER[4]
    assert krum_input_excludes_source(
        tuple(row.reproducer_domain for row in in_ball),
        NBAIOT_DOMAIN_ORDER[5],
    )
    assert not krum_input_excludes_source(
        tuple(row.reproducer_domain for row in in_ball),
        selected.reproducer_domain,
    )
