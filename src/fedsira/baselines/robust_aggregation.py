from collections.abc import Sequence

import torch

from fedsira.config.schema import ThreeRowCoordinateMedianConfig
from fedsira.domain.records import PositiveInt
from fedsira.protocol.synthesis import CertifiedReproductionRow


def direct_krum_committee_rows(
    committed_rows: Sequence[CertifiedReproductionRow],
    is_non_abstaining: Sequence[bool],
    committee_size: PositiveInt,
) -> tuple[CertifiedReproductionRow, ...] | None:
    eligible = [
        row
        for row, non_abstaining in zip(committed_rows, is_non_abstaining, strict=True)
        if non_abstaining
    ]
    if len(eligible) < committee_size:
        return None
    return tuple(eligible[:committee_size])


def validate_three_row_coordinate_median_committee_size(
    committee_size: PositiveInt, config: ThreeRowCoordinateMedianConfig
) -> None:
    if committee_size != config.row_count:
        raise ValueError(
            f"Three-Row Coordinate-Median Alternative requires exactly {config.row_count} rows, "
            f"got {committee_size}"
        )


def coordinate_wise_median_synthesis(update_vectors: Sequence[torch.Tensor]) -> torch.Tensor:
    stacked = torch.stack(list(update_vectors), dim=0)
    return torch.median(stacked, dim=0).values
