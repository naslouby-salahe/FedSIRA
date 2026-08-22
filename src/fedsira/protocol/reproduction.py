import hashlib
from collections.abc import Sequence
from dataclasses import dataclass

import torch

from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_HASH_TOKEN, NBaiotDomain
from fedsira.domain.enums import ClaimState
from fedsira.domain.records import ArtifactDigest, CanonicalToken, DerivedSeed
from fedsira.runtime.determinism import canonical_bytes

REPRODUCTION_COMMITMENT_SEPARATOR = "REPRODUCTION_COMMITMENT"


@dataclass(frozen=True)
class ReproductionAttempt:
    domain: NBaiotDomain
    was_trained: bool
    is_certified: bool


def consumed_domains(attempts: Sequence[ReproductionAttempt]) -> frozenset[NBaiotDomain]:
    return frozenset(attempt.domain for attempt in attempts if attempt.was_trained)


def next_reproducer_domain(
    reproducer_order: Sequence[NBaiotDomain],
    consumed: frozenset[NBaiotDomain],
    adequate_domains: frozenset[NBaiotDomain],
) -> NBaiotDomain | None:
    for domain in reproducer_order:
        if domain not in consumed and domain in adequate_domains:
            return domain
    return None


def handle_inadequate_domain() -> ClaimState:
    return ClaimState.REPRODUCTION_PENDING


def handle_adequate_domain_trained(
    external_verification_active: bool, resolved_row_requirement_reached: bool
) -> ClaimState:
    if external_verification_active:
        return ClaimState.VERIFICATION_PENDING
    if resolved_row_requirement_reached:
        return ClaimState.SYNTHESIS_PENDING
    return ClaimState.REPRODUCTION_PENDING


def handle_no_adequate_unconsumed_domain(resolved_row_requirement_reached: bool) -> ClaimState:
    if resolved_row_requirement_reached:
        return ClaimState.SYNTHESIS_PENDING
    return ClaimState.DORMANT


def validate_reproduction_start_checkpoint(
    start_checkpoint_id: CanonicalToken, source_checkpoint_ids: frozenset[CanonicalToken]
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
    reproducer_domain: NBaiotDomain,
    claim_identity: ArtifactDigest,
    training_seed: DerivedSeed,
    reproduced_flat_parameters: torch.Tensor,
) -> ArtifactDigest:
    parameter_bytes = (
        reproduced_flat_parameters.detach().to(torch.float32).contiguous().numpy().tobytes()
    )
    header = canonical_bytes(
        REPRODUCTION_COMMITMENT_SEPARATOR,
        NBAIOT_DOMAIN_HASH_TOKEN[reproducer_domain],
        claim_identity,
        training_seed,
    )
    return hashlib.sha256(header + parameter_bytes).hexdigest()


def validate_commitment_exists_before_verifier_assignment(
    commitment_hash: ArtifactDigest | None,
) -> None:
    if commitment_hash is None:
        raise ValueError("verifier assignment requires an existing reproduction commitment")
