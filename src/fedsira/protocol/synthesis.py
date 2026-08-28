from collections.abc import Sequence

import torch

from fedsira.config.schema import FinalGateConfig
from fedsira.domain.enums import ClaimState
from fedsira.domain.records import (
    AdequateFinalGateDomainCount,
    CommitteeSize,
    DomainId,
    FinalGatePredicatesPass,
    KrumNeighborCount,
    KrumScore,
    MaximumByzantineReproductionRows,
    ReproductionRowId,
    SourceExcludedFromKrum,
    TensorDomainModel,
)
from fedsira.protocol.theory import krum_committee_is_admissible


def synthesis_pending_transition(
    adequate_final_gate_domain_count: AdequateFinalGateDomainCount,
    final_gate_predicates_pass: FinalGatePredicatesPass,
    final_gate_config: FinalGateConfig,
) -> ClaimState:
    if adequate_final_gate_domain_count < final_gate_config.minimum_adequate_non_source_domains:
        return ClaimState.DORMANT
    if final_gate_predicates_pass:
        return ClaimState.ADMITTED
    return ClaimState.REJECTED_CLAIM


def krum_input_excludes_source(
    candidate_row_ids: Sequence[ReproductionRowId],
    source_row_id: ReproductionRowId | None,
) -> SourceExcludedFromKrum:
    if source_row_id is None:
        return True
    return source_row_id not in candidate_row_ids


class CertifiedReproductionRow(TensorDomainModel):
    reproducer_domain: DomainId
    update_vector: torch.Tensor


def krum_neighbor_count(
    committee_size: CommitteeSize,
    maximum_byzantine_rows: MaximumByzantineReproductionRows,
) -> KrumNeighborCount:
    return committee_size - maximum_byzantine_rows - 2


def krum_score(
    row: CertifiedReproductionRow,
    committee: Sequence[CertifiedReproductionRow],
    neighbor_count: KrumNeighborCount,
) -> KrumScore:
    distances = sorted(
        (
            float(torch.sum((row.update_vector - other.update_vector) ** 2)),
            other.reproducer_domain,
        )
        for other in committee
        if other.reproducer_domain != row.reproducer_domain
    )
    return sum(distance for distance, _ in distances[:neighbor_count])


def select_krum_update(
    committee: Sequence[CertifiedReproductionRow],
    maximum_byzantine_rows: MaximumByzantineReproductionRows,
) -> CertifiedReproductionRow:
    committee_size = len(committee)
    if not krum_committee_is_admissible(committee_size, maximum_byzantine_rows):
        raise ValueError(
            f"Krum committee of size {committee_size} is not admissible for "
            f"maximum_byzantine_rows={maximum_byzantine_rows}"
        )
    neighbor_count = krum_neighbor_count(committee_size, maximum_byzantine_rows)
    ranked = sorted(
        (
            krum_score(row, committee, neighbor_count),
            row.reproducer_domain,
            row,
        )
        for row in committee
    )
    return ranked[0][2]
