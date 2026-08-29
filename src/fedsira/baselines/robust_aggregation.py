import torch

from fedsira.config.schema import BaselinesConfig, ThreeRowCoordinateMedianConfig
from fedsira.datasets.nbaiot.schema import NBaiotDomain, deterministic_domain_order
from fedsira.domain.enums import SeedNamespace
from fedsira.domain.records import BooleanValue, DerivedSeed, MasterSeed, PositiveInt, RoundIndex
from fedsira.protocol.synthesis import CertifiedReproductionRow
from fedsira.runtime.determinism import derive_uint32

CLIENT_SAMPLING_SEPARATOR = SeedNamespace.CLIENT_SAMPLING.value


def direct_krum_committee_rows(
    committed_rows: tuple[CertifiedReproductionRow, ...],
    is_non_abstaining: tuple[BooleanValue, ...],
    committee_size: PositiveInt,
) -> tuple[CertifiedReproductionRow, ...] | None:
    if len(committed_rows) != len(is_non_abstaining):
        raise ValueError("committed rows and abstention states must have equal length")
    eligible = tuple(
        row
        for row, non_abstaining in zip(committed_rows, is_non_abstaining, strict=True)
        if non_abstaining
    )
    if len(eligible) < committee_size:
        return None
    return eligible[:committee_size]


def validate_three_row_coordinate_median_committee_size(
    committee_size: PositiveInt,
    config: ThreeRowCoordinateMedianConfig,
) -> None:
    if committee_size != config.row_count:
        raise ValueError(
            f"Three-Row Coordinate-Median Alternative requires exactly {config.row_count} rows, "
            f"got {committee_size}"
        )


def coordinate_wise_median_synthesis(
    update_vectors: tuple[torch.Tensor, ...],
) -> torch.Tensor:
    if not update_vectors:
        raise ValueError("coordinate-wise median requires at least one update")
    stacked = torch.stack(update_vectors, dim=0)
    return torch.median(stacked, dim=0).values


def krum_reference_post_reference_rounds(baselines_config: BaselinesConfig) -> PositiveInt:
    return baselines_config.krum_robust_aggregation_post_reference_rounds


def client_sampling_round_seed(master_seed: MasterSeed, round_index: RoundIndex) -> DerivedSeed:
    return derive_uint32(CLIENT_SAMPLING_SEPARATOR, master_seed, round_index)


def client_sampling_round_order(
    eligible_domains: tuple[NBaiotDomain, ...],
    master_seed: MasterSeed,
    round_index: RoundIndex,
) -> tuple[NBaiotDomain, ...]:
    round_seed = client_sampling_round_seed(master_seed, round_index)
    return deterministic_domain_order(eligible_domains, CLIENT_SAMPLING_SEPARATOR, round_seed)


def krum_reference_round_participants(
    round_order: tuple[NBaiotDomain, ...],
    compromised_domain: NBaiotDomain | None,
    participant_count: PositiveInt,
) -> tuple[NBaiotDomain, ...] | None:
    if compromised_domain is None:
        selected = round_order[:participant_count]
    else:
        remaining = tuple(domain for domain in round_order if domain is not compromised_domain)
        selected = (compromised_domain, *remaining[: participant_count - 1])
    if len(selected) < participant_count:
        return None
    return selected
