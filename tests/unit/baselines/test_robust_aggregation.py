import pytest
import torch

from fedsira.baselines.robust_aggregation import (
    coordinate_wise_median_synthesis,
    direct_krum_committee_rows,
    validate_three_row_coordinate_median_committee_size,
)
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER
from fedsira.protocol.synthesis import CertifiedReproductionRow

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
THREE_ROW_CONFIG = CONFIG.baselines.three_row_coordinate_median


def test_direct_krum_committee_rows_filters_abstaining_and_requires_committee_size() -> None:
    rows = tuple(
        CertifiedReproductionRow(
            reproducer_domain=domain,
            update_vector=torch.zeros(2),
        )
        for domain in NBAIOT_DOMAIN_ORDER[:6]
    )
    flags = (True, False, True, True, True, True)
    committee = direct_krum_committee_rows(rows, flags, 5)
    assert committee is not None
    assert len(committee) == 5
    assert rows[1] not in committee


def test_direct_krum_committee_rows_none_when_insufficient_non_abstaining_rows() -> None:
    rows = tuple(
        CertifiedReproductionRow(
            reproducer_domain=domain,
            update_vector=torch.zeros(2),
        )
        for domain in NBAIOT_DOMAIN_ORDER[:4]
    )
    flags = (True, True, False, False)
    assert direct_krum_committee_rows(rows, flags, 5) is None


def test_validate_three_row_coordinate_median_committee_size_matches_config() -> None:
    validate_three_row_coordinate_median_committee_size(
        THREE_ROW_CONFIG.row_count, THREE_ROW_CONFIG
    )
    with pytest.raises(ValueError):
        validate_three_row_coordinate_median_committee_size(4, THREE_ROW_CONFIG)


def test_coordinate_wise_median_synthesis_is_coordinatewise_median_of_three_rows() -> None:
    rows = (
        torch.tensor([1.0, 5.0, -1.0]),
        torch.tensor([2.0, 0.0, 0.0]),
        torch.tensor([3.0, -5.0, 1.0]),
    )
    median = coordinate_wise_median_synthesis(rows)
    assert torch.equal(median, torch.tensor([2.0, 0.0, 0.0]))
