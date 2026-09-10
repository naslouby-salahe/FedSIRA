from __future__ import annotations

import json
from pathlib import Path

from fedsira.datasets.common import Role
from fedsira.domain.types import (
    AdequateFinalGateDomainCount,
    ClassLabel,
    DatasetClassToken,
    DomainId,
    FrozenDomainModel,
    PreparedReproductionTargetCount,
    PreparedScreenTargetCount,
    PreparedSupportedReplayCount,
    RowCount,
    SchemaVersion,
)


class PreparedEvidenceCounts(FrozenDomainModel):
    screen_target_count: PreparedScreenTargetCount
    reproduction_target_count: PreparedReproductionTargetCount
    reproduction_supported_count: PreparedSupportedReplayCount
    final_gate_adequate_domain_count: AdequateFinalGateDomainCount


class PreparedViewSidecar(FrozenDomainModel):
    class_id: ClassLabel
    domain: DomainId
    role: Role
    row_count: RowCount
    schema_version: SchemaVersion


def load_prepared_evidence_counts(
    prepared_root: Path, target_class_token: DatasetClassToken
) -> PreparedEvidenceCounts | None:
    if not prepared_root.exists():
        return None
    screen_target_count = 0
    reproduction_target_count = 0
    reproduction_supported_count = 0
    final_gate_target_domains: set[DomainId] = set()
    for metadata_path in sorted(prepared_root.glob("*.json")):
        try:
            payload = PreparedViewSidecar.model_validate_json(metadata_path.read_text())
        except (ValueError, json.JSONDecodeError, OSError):
            continue
        if payload.role is Role.CANDIDATE_SCREEN and payload.class_id == target_class_token:
            screen_target_count += payload.row_count
        elif payload.role is Role.REPRODUCTION and payload.class_id == target_class_token:
            reproduction_target_count += payload.row_count
        elif payload.role is Role.POST_REFERENCE_REPLAY and payload.class_id != target_class_token:
            reproduction_supported_count += payload.row_count
        elif payload.role is Role.FINAL_GATE and payload.class_id == target_class_token:
            final_gate_target_domains.add(payload.domain)
    if screen_target_count == 0 and reproduction_target_count == 0:
        return None
    return PreparedEvidenceCounts(
        screen_target_count=screen_target_count,
        reproduction_target_count=reproduction_target_count,
        reproduction_supported_count=reproduction_supported_count,
        final_gate_adequate_domain_count=len(final_gate_target_domains),
    )
