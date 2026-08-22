from collections.abc import Sequence
from dataclasses import dataclass

import torch

from fedsira.config.schema import FinalGateConfig
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_HASH_TOKEN, NBaiotDomain
from fedsira.domain.enums import ClaimState
from fedsira.domain.records import CanonicalToken, NonNegativeInt, PositiveInt
from fedsira.protocol.theory import krum_committee_is_admissible


def synthesis_pending_transition(
    adequate_final_gate_domain_count: NonNegativeInt,
    final_gate_predicates_pass: bool,
    final_gate_config: FinalGateConfig,
) -> ClaimState:
    if adequate_final_gate_domain_count < final_gate_config.minimum_adequate_non_source_domains:
        return ClaimState.DORMANT
    if final_gate_predicates_pass:
        return ClaimState.ADMITTED
    return ClaimState.REJECTED_CLAIM


def krum_input_excludes_source(
    candidate_row_ids: Sequence[CanonicalToken], source_row_id: CanonicalToken | None
) -> bool:
    if source_row_id is None:
        return True
    return source_row_id not in candidate_row_ids


@dataclass(frozen=True)
class CertifiedReproductionRow:
    reproducer_domain: NBaiotDomain
    update_vector: torch.Tensor


def krum_neighbor_count(
    committee_size: PositiveInt, maximum_byzantine_rows: NonNegativeInt
) -> PositiveInt:
    return committee_size - maximum_byzantine_rows - 2


def krum_score(
    row: CertifiedReproductionRow,
    committee: Sequence[CertifiedReproductionRow],
    neighbor_count: PositiveInt,
) -> float:
    distances = sorted(
        (
            float(torch.sum((row.update_vector - other.update_vector) ** 2)),
            NBAIOT_DOMAIN_HASH_TOKEN[other.reproducer_domain],
        )
        for other in committee
        if other.reproducer_domain != row.reproducer_domain
    )
    return sum(distance for distance, _ in distances[:neighbor_count])


def select_krum_update(
    committee: Sequence[CertifiedReproductionRow], maximum_byzantine_rows: NonNegativeInt
) -> CertifiedReproductionRow:
    if not krum_committee_is_admissible(len(committee), maximum_byzantine_rows):
        raise ValueError(
            f"Krum committee of size {len(committee)} is not admissible for "
            f"maximum_byzantine_rows={maximum_byzantine_rows}"
        )
    neighbor_count = krum_neighbor_count(len(committee), maximum_byzantine_rows)
    ranked = sorted(
        (
            krum_score(row, committee, neighbor_count),
            NBAIOT_DOMAIN_HASH_TOKEN[row.reproducer_domain],
            row,
        )
        for row in committee
    )
    return ranked[0][2]
