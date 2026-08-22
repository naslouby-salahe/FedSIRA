from collections.abc import Sequence

import torch

from fedsira.config.schema import BaselinesConfig, ThreeRowCoordinateMedianConfig
from fedsira.datasets.nbaiot.schema import NBaiotDomain, deterministic_domain_order
from fedsira.domain.records import DerivedSeed, MasterSeed, PositiveInt, RoundIndex
from fedsira.protocol.synthesis import CertifiedReproductionRow
from fedsira.runtime.determinism import derive_uint32

CLIENT_SAMPLING_SEPARATOR = "CLIENT_SAMPLING"


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


def krum_reference_post_reference_rounds(baselines_config: BaselinesConfig) -> PositiveInt:
    return baselines_config.krum_robust_aggregation_post_reference_rounds


def client_sampling_round_seed(master_seed: MasterSeed, round_index: RoundIndex) -> DerivedSeed:
    return derive_uint32(CLIENT_SAMPLING_SEPARATOR, master_seed, round_index)


def client_sampling_round_order(
    eligible_domains: Sequence[NBaiotDomain], master_seed: MasterSeed, round_index: RoundIndex
) -> tuple[NBaiotDomain, ...]:
    round_seed = client_sampling_round_seed(master_seed, round_index)
    return deterministic_domain_order(eligible_domains, CLIENT_SAMPLING_SEPARATOR, round_seed)


def krum_reference_round_participants(
    round_order: Sequence[NBaiotDomain],
    compromised_domain: NBaiotDomain | None,
    participant_count: PositiveInt,
) -> tuple[NBaiotDomain, ...] | None:
    if compromised_domain is None:
        selected = list(round_order[:participant_count])
    else:
        remaining = [domain for domain in round_order if domain != compromised_domain]
        selected = [compromised_domain, *remaining[: participant_count - 1]]
    if len(selected) < participant_count:
        return None
    return tuple(selected)
