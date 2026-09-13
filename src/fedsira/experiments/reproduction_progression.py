from __future__ import annotations

from collections import OrderedDict

import torch

from fedsira.datasets.common import BackdoorScope, DatasetAdapter, HeterogeneityScope, RealAnchor
from fedsira.datasets.nbaiot.schema import NBaiotDomain
from fedsira.domain.enums import (
    AblationReproducerStrategy,
    AdmissionState,
    ArtifactFamily,
    ArtifactFamilyDirectoryToken,
)
from fedsira.domain.types import (
    ArtifactDigest,
    BooleanValue,
    DomainId,
    RequiredReproductionRowCount,
)
from fedsira.experiments.cell_parameters import domain_is_reproduction_adequate
from fedsira.experiments.checkpoints import publish_trained_update, reproduction_stage_identity
from fedsira.experiments.definitions import (
    ExternalVerificationCondition,
    PluralityCondition,
    ReproducerCondition,
    SecondaryScenario,
)
from fedsira.experiments.engine import PreparedEvidenceCounts
from fedsira.experiments.planning import ScientificCell
from fedsira.learning.post_reference import (
    train_domain_reproduction_delta,
    train_verifier_aware_reproduction_delta,
)
from fedsira.protocol.attacks import scale_model_replacement_delta
from fedsira.protocol.capability_contract import (
    capability_contract_for_digest,
    compute_capability_identity,
)
from fedsira.protocol.proposal import source_domain_for_cell
from fedsira.protocol.reproduction import (
    ReproductionAttempt,
    commitment_digest,
    consumed_domains,
    handle_adequate_domain_trained,
    handle_inadequate_domain,
    handle_no_adequate_unconsumed_domain,
    next_reproducer_domain,
    validate_commitment_exists_before_verifier_assignment,
    validate_reproduction_start_checkpoint,
    validate_reproduction_starts_from_anchor,
)
from fedsira.protocol.rules import reproducer_order_for_cell, reproduction_update_vector
from fedsira.runtime import current_application_context

BYZANTINE_VERIFIER_SELECTION_SEPARATOR = "BYZANTINE_VERIFIER_SELECTION"
ANCHOR_CHECKPOINT_IDENTITY = ArtifactFamilyDirectoryToken.ANCHOR_CHECKPOINT
SOURCE_CHECKPOINT_IDENTITY = "source-checkpoint"


def _train_reproduction_update(
    adapter: DatasetAdapter,
    cell: ScientificCell,
    anchor: RealAnchor,
    domain: DomainId,
    source_delta: torch.Tensor | None,
    compromised_reproducers: frozenset[DomainId],
    heterogeneity_scope: HeterogeneityScope | None,
    backdoor_scope: BackdoorScope | None,
    strategy: AblationReproducerStrategy,
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    validate_reproduction_starts_from_anchor(anchor.flat_parameters, anchor.flat_parameters)
    if domain not in compromised_reproducers:
        return train_domain_reproduction_delta(
            adapter,
            cell.master_seed,
            anchor,
            domain,
            heterogeneity_scope=heterogeneity_scope,
        )
    if strategy is AblationReproducerStrategy.VERIFIER_AWARE:
        if backdoor_scope is None:
            return None
        return train_verifier_aware_reproduction_delta(
            adapter,
            cell.master_seed,
            anchor,
            domain,
            backdoor_scope,
            heterogeneity_scope,
        )
    if strategy is AblationReproducerStrategy.MODEL_REPLACEMENT:
        trained = train_domain_reproduction_delta(
            adapter,
            cell.master_seed,
            anchor,
            domain,
            heterogeneity_scope=heterogeneity_scope,
            backdoor_scope=backdoor_scope,
        )
        if trained is None:
            return None
        return scale_model_replacement_delta(
            trained,
            config.attacks_and_boundaries.byzantine_reproduction.model_replacement.delta_scale,
        )
    if cell.condition in (
        ReproducerCondition.ONE_SOURCE_COPY,
        ReproducerCondition.TWO_SOURCE_COPIES,
        PluralityCondition.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER,
        ExternalVerificationCondition.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER,
        SecondaryScenario.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER,
    ):
        if source_delta is None:
            return None
        return reproduction_update_vector(
            anchor.flat_parameters, anchor.flat_parameters + source_delta
        )
    trained = train_domain_reproduction_delta(
        adapter,
        cell.master_seed,
        anchor,
        domain,
        heterogeneity_scope=heterogeneity_scope,
        backdoor_scope=backdoor_scope,
    )
    if trained is None:
        return None
    if cell.condition in (
        ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR,
        ReproducerCondition.TWO_MODEL_REPLACEMENT_BACKDOORS,
    ):
        return scale_model_replacement_delta(
            trained,
            config.attacks_and_boundaries.byzantine_reproduction.model_replacement.delta_scale,
        )
    return trained


def reproduction_progression(
    cell: ScientificCell,
    evidence: PreparedEvidenceCounts,
    external_verification_active: BooleanValue,
    row_requirement: RequiredReproductionRowCount,
    compromised_reproducers: frozenset[DomainId],
    adapter: DatasetAdapter,
    anchor: RealAnchor | None,
    strategy: AblationReproducerStrategy = AblationReproducerStrategy.NONE,
    include_source_as_first_reproducer: BooleanValue = False,
    heterogeneity_scope: HeterogeneityScope | None = None,
    backdoor_scope: BackdoorScope | None = None,
    source_delta: torch.Tensor | None = None,
) -> tuple[
    AdmissionState,
    tuple[ReproductionAttempt, ...],
    tuple[ArtifactDigest, ...],
    OrderedDict[DomainId, torch.Tensor],
]:
    del evidence
    if anchor is None:
        return (AdmissionState.DORMANT, (), (), OrderedDict())
    reproducer_order = reproducer_order_for_cell(adapter, cell)
    source_domain = source_domain_for_cell(adapter, cell)
    validate_reproduction_start_checkpoint(
        ANCHOR_CHECKPOINT_IDENTITY, frozenset({SOURCE_CHECKPOINT_IDENTITY})
    )
    validate_reproduction_starts_from_anchor(anchor.flat_parameters, anchor.flat_parameters)
    capability_identity = compute_capability_identity(
        capability_contract_for_digest(adapter, anchor.dataset_manifest_hash)
    )
    adequate_domains = frozenset(
        domain
        for domain in adapter.domain_ids
        if domain != source_domain and domain_is_reproduction_adequate(adapter, domain)
    )
    attempts: list[ReproductionAttempt] = []
    commitment_hashes: list[ArtifactDigest] = []
    updates: OrderedDict[DomainId, torch.Tensor] = OrderedDict()
    certified_count = 0
    state = AdmissionState.REPRODUCTION_PENDING
    if (
        include_source_as_first_reproducer
        and source_domain is not None
        and source_delta is not None
    ):
        reproduced = anchor.flat_parameters + source_delta
        commitment_hash = commitment_digest(
            source_domain, cell.master_seed, capability_identity, reproduced
        )
        commitment_hashes.append(commitment_hash)
        validate_commitment_exists_before_verifier_assignment(commitment_hash)
        updates[source_domain] = source_delta
        attempts.append(
            ReproductionAttempt(domain=source_domain, was_trained=True, is_certified=True)
        )
        certified_count += 1
        state = handle_adequate_domain_trained(
            external_verification_active, certified_count >= row_requirement
        )
        if state is AdmissionState.SYNTHESIS_PENDING:
            return (state, tuple(attempts), tuple(commitment_hashes), updates)
    for _row_index in range(len(reproducer_order)):
        next_domain = next_reproducer_domain(
            reproducer_order, consumed_domains(attempts), adequate_domains
        )
        if next_domain is None:
            state = handle_no_adequate_unconsumed_domain(certified_count >= row_requirement)
            break
        domain = NBaiotDomain(next_domain)
        update = _train_reproduction_update(
            adapter,
            cell,
            anchor,
            domain,
            source_delta,
            compromised_reproducers,
            heterogeneity_scope,
            backdoor_scope,
            strategy,
        )
        if update is None:
            state = handle_inadequate_domain()
            continue
        reproduced = anchor.flat_parameters + update
        commitment_hash = commitment_digest(
            domain, cell.master_seed, capability_identity, reproduced
        )
        commitment_hashes.append(commitment_hash)
        validate_commitment_exists_before_verifier_assignment(commitment_hash)
        updates[domain] = update
        publish_trained_update(
            ArtifactFamily.REPRODUCTION_CHECKPOINT,
            adapter.dataset,
            cell.master_seed,
            reproduction_stage_identity(domain, cell.condition),
            anchor.dataset_manifest_hash,
            update,
            anchor.input_width,
            anchor.output_width,
        )
        is_certified = domain not in compromised_reproducers or not external_verification_active
        attempts.append(
            ReproductionAttempt(domain=domain, was_trained=True, is_certified=is_certified)
        )
        if is_certified:
            certified_count += 1
        state = handle_adequate_domain_trained(
            external_verification_active, certified_count >= row_requirement
        )
        if state is AdmissionState.SYNTHESIS_PENDING:
            break
    return (state, tuple(attempts), tuple(commitment_hashes), updates)
