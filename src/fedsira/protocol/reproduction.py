import hashlib
import struct
from collections.abc import Sequence
from typing import Protocol, cast

import torch

from fedsira.domain.enums import ClaimState
from fedsira.domain.types import (
    ArtifactDigest,
    CheckpointIdentity,
    CompromisedReproducerCount,
    DerivedSeed,
    DomainId,
    ExternalVerificationActive,
    FiniteFloat,
    FrozenDomainModel,
    ReproductionCertified,
    ReproductionWasTrained,
    ResolvedRowRequirementReached,
    SeedDerivationLabel,
)
from fedsira.runtime.determinism import framed_bytes

REPRODUCTION_COMMITMENT_SEPARATOR: SeedDerivationLabel = "REPRODUCTION_COMMITMENT"


class _ListConvertibleTensor(Protocol):
    def tolist(self) -> list[FiniteFloat]: ...


class ReproductionAttempt(FrozenDomainModel):
    domain: DomainId
    was_trained: ReproductionWasTrained
    is_certified: ReproductionCertified


def consumed_domains(attempts: Sequence[ReproductionAttempt]) -> frozenset[DomainId]:
    return frozenset(attempt.domain for attempt in attempts if attempt.was_trained)


def next_reproducer_domain(
    reproducer_order: Sequence[DomainId],
    consumed: frozenset[DomainId],
    adequate_domains: frozenset[DomainId],
) -> DomainId | None:
    for domain in reproducer_order:
        if domain not in consumed and domain in adequate_domains:
            return domain
    return None


def handle_inadequate_domain() -> ClaimState:
    return ClaimState.REPRODUCTION_PENDING


def handle_adequate_domain_trained(
    external_verification_active: ExternalVerificationActive,
    resolved_row_requirement_reached: ResolvedRowRequirementReached,
) -> ClaimState:
    if external_verification_active:
        return ClaimState.VERIFICATION_PENDING
    if resolved_row_requirement_reached:
        return ClaimState.SYNTHESIS_PENDING
    return ClaimState.REPRODUCTION_PENDING


def handle_no_adequate_unconsumed_domain(
    resolved_row_requirement_reached: ResolvedRowRequirementReached,
) -> ClaimState:
    if resolved_row_requirement_reached:
        return ClaimState.SYNTHESIS_PENDING
    return ClaimState.DORMANT


def validate_reproduction_start_checkpoint(
    start_checkpoint_id: CheckpointIdentity,
    source_checkpoint_ids: frozenset[CheckpointIdentity],
) -> None:
    if start_checkpoint_id in source_checkpoint_ids:
        raise ValueError(
            "honest reproduction must not start from the source or a source-derived checkpoint"
        )


def validate_reproduction_starts_from_anchor(
    start_flat_parameters: torch.Tensor, anchor_flat_parameters: torch.Tensor
) -> None:
    if not torch.equal(start_flat_parameters, anchor_flat_parameters):
        raise ValueError("honest reproduction must start from the anchor checkpoint w_a")


def compute_reproduction_commitment_hash(
    reproducer_domain: DomainId,
    claim_identity: ArtifactDigest,
    training_seed: DerivedSeed,
    reproduced_flat_parameters: torch.Tensor,
) -> ArtifactDigest:
    flat_values = cast(
        _ListConvertibleTensor, reproduced_flat_parameters.detach().to(torch.float64)
    ).tolist()
    parameter_bytes = struct.pack(f">{len(flat_values)}d", *flat_values)
    header = framed_bytes(
        REPRODUCTION_COMMITMENT_SEPARATOR,
        reproducer_domain,
        claim_identity,
        training_seed,
    )
    return hashlib.sha256(header + parameter_bytes).hexdigest()


def validate_commitment_exists_before_verifier_assignment(
    commitment_hash: ArtifactDigest | None,
) -> None:
    if commitment_hash is None:
        raise ValueError("verifier assignment requires an existing reproduction commitment")


def select_compromised_reproducers(
    reproducer_order: Sequence[DomainId],
    attack_feasible_domains: frozenset[DomainId],
    requested_compromised_count: CompromisedReproducerCount,
) -> tuple[DomainId, ...] | None:
    feasible_in_order = [domain for domain in reproducer_order if domain in attack_feasible_domains]
    if len(feasible_in_order) < requested_compromised_count:
        return None
    return tuple(feasible_in_order[:requested_compromised_count])
