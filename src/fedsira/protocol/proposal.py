import hashlib
from collections import OrderedDict
from collections.abc import Mapping, Sequence

from fedsira.config import (
    AdmissionOpeningConfig,
    CapabilityContractConfig,
    ProposalScreenConfig,
)
from fedsira.datasets.common import (
    DatasetAdapter,
    Role,
)
from fedsira.domain.enums import (
    AdmissionOpeningMode,
    AdmissionState,
    ProposalEpisode,
    SeedNamespace,
)
from fedsira.domain.models import MetricResult, ScientificCell
from fedsira.domain.types import (
    ArtifactDigest,
    AttackCarrierRequired,
    BooleanValue,
    CapabilityContractSatisfied,
    CapabilityIdentity,
    DatasetClassToken,
    DerivedSeed,
    DomainId,
    EvidenceAdequate,
    ExampleCount,
    FoldCount,
    FoldIndex,
    FrozenDomainModel,
    NamespaceSeed,
    OpeningPredicateSatisfied,
    ProductionWeight,
    SampleId,
    ScreenDifferential,
    ScreenDomainCount,
    ScreenDomainDecision,
    ScreenLoss,
    SourceCommitted,
)
from fedsira.evaluation.statistics import match_nearest_within_decile
from fedsira.protocol.capability_contract import (
    capability_contract_for_digest,
    compute_capability_identity,
)
from fedsira.protocol.rules import validate_exactly_one_source_domain
from fedsira.runtime import derive_uint32, deterministic_order, framed_bytes

SCREEN_DOMAIN_ORDER_SEPARATOR = SeedNamespace.SCREEN_DOMAIN_ORDER.value
SCREEN_FOLD_SEPARATOR = SeedNamespace.SCREEN_FOLD.value
SOURCE_SELECTION_SEPARATOR = SeedNamespace.SOURCE_SELECTION.value


class AdmissionOpeningEntry(FrozenDomainModel):
    state: AdmissionState
    source_committed: SourceCommitted
    direct_production_weight: ProductionWeight


def start_admission(opening_mode: AdmissionOpeningMode) -> AdmissionOpeningEntry:
    return AdmissionOpeningEntry(
        state=AdmissionState.CANDIDATE_SCREEN,
        source_committed=opening_mode is AdmissionOpeningMode.PROPOSAL_ASSISTED,
        direct_production_weight=0.0,
    )


class ScreenDomainResult(FrozenDomainModel):
    domain: DomainId
    is_evidence_adequate: EvidenceAdequate
    meets_opening_predicate: OpeningPredicateSatisfied


class ScreenLossObservation(FrozenDomainModel):
    sample_id: SampleId
    anchor_loss: ScreenLoss
    source_loss: ScreenLoss


def source_selection_order(
    eligible_domains: Sequence[DomainId],
    source_selection_namespace_seed: NamespaceSeed,
) -> tuple[DomainId, ...]:
    return deterministic_order(
        tuple(eligible_domains),
        SOURCE_SELECTION_SEPARATOR,
        source_selection_namespace_seed,
    )


def select_source_domain(
    source_order: Sequence[DomainId],
    domains_with_target_stream: frozenset[DomainId],
    requires_attack_carrier: AttackCarrierRequired,
    domains_with_attack_carrier: frozenset[DomainId],
) -> DomainId | None:
    for domain in source_order:
        if domain not in domains_with_target_stream:
            continue
        if requires_attack_carrier and domain not in domains_with_attack_carrier:
            continue
        return domain
    return None


def screen_domain_order(
    eligible_non_source_domains: Sequence[DomainId],
    screen_domain_order_namespace_seed: NamespaceSeed,
    screen_domain_count: ScreenDomainCount,
) -> tuple[DomainId, ...]:
    ordered = deterministic_order(
        tuple(eligible_non_source_domains),
        SCREEN_DOMAIN_ORDER_SEPARATOR,
        screen_domain_order_namespace_seed,
    )
    return ordered[:screen_domain_count]


def screen_fold_index(
    sample_id: SampleId,
    screen_fold_seed: DerivedSeed,
    fold_count: FoldCount,
) -> FoldIndex:
    digest = hashlib.sha256(
        framed_bytes(SCREEN_FOLD_SEPARATOR, screen_fold_seed, sample_id)
    ).digest()
    return int.from_bytes(digest[0:8], byteorder="big", signed=False) % fold_count


def match_held_out_fold(
    held_out_targets: Sequence[ScreenLossObservation],
    held_out_controls: Sequence[ScreenLossObservation],
    other_fold_controls: Sequence[ScreenLossObservation],
) -> tuple[tuple[ScreenLossObservation, ScreenLossObservation], ...] | None:
    targets_by_id = OrderedDict(
        (observation.sample_id, observation) for observation in held_out_targets
    )
    controls_by_id = OrderedDict(
        (observation.sample_id, observation) for observation in held_out_controls
    )
    matched_ids = match_nearest_within_decile(
        tuple((observation.sample_id, observation.anchor_loss) for observation in held_out_targets),
        tuple(
            (observation.sample_id, observation.anchor_loss) for observation in held_out_controls
        ),
        tuple(observation.anchor_loss for observation in other_fold_controls),
    )
    if matched_ids is None:
        return None
    return tuple(
        (targets_by_id[target_id], controls_by_id[control_id])
        for target_id, control_id in matched_ids
    )


def proposal_screen_differential(
    matched_pairs: Sequence[tuple[ScreenLossObservation, ScreenLossObservation]],
) -> ScreenDifferential | None:
    if len(matched_pairs) == 0:
        return None
    target_deltas = [target.anchor_loss - target.source_loss for target, _ in matched_pairs]
    control_deltas = [control.anchor_loss - control.source_loss for _, control in matched_pairs]
    differential_target = sum(target_deltas) / len(target_deltas)
    differential_control = sum(control_deltas) / len(control_deltas)
    return differential_target - differential_control


def run_proposal_screen_for_domain(
    fold_assignment_by_sample_id: Mapping[SampleId, FoldIndex],
    target_observations: Sequence[ScreenLossObservation],
    control_observations: Sequence[ScreenLossObservation],
    fold_count: FoldCount,
) -> ScreenDifferential | None:
    all_matches: list[tuple[ScreenLossObservation, ScreenLossObservation]] = []
    for held_out_fold in range(fold_count):
        held_out_targets = [
            observation
            for observation in target_observations
            if fold_assignment_by_sample_id[observation.sample_id] == held_out_fold
        ]
        held_out_controls = [
            observation
            for observation in control_observations
            if fold_assignment_by_sample_id[observation.sample_id] == held_out_fold
        ]
        other_fold_controls = [
            observation
            for observation in control_observations
            if fold_assignment_by_sample_id[observation.sample_id] != held_out_fold
        ]
        fold_matches = match_held_out_fold(held_out_targets, held_out_controls, other_fold_controls)
        if fold_matches is None:
            return None
        all_matches.extend(fold_matches)
    return proposal_screen_differential(all_matches)


def screen_domain_decision_is_positive(
    differential_a: ScreenDifferential | None,
    target_f1_gain: MetricResult,
    supported_macro_f1_drop: MetricResult,
    benign_far_increase: MetricResult,
    proposal_screen_config: ProposalScreenConfig,
    capability_contract_config: CapabilityContractConfig,
) -> ScreenDomainDecision:
    if differential_a is None:
        return False
    if (
        target_f1_gain.value is None
        or supported_macro_f1_drop.value is None
        or benign_far_increase.value is None
    ):
        return False
    return (
        differential_a >= proposal_screen_config.differential_minimum_nats_per_example
        and target_f1_gain.value >= capability_contract_config.target_f1_gain_over_anchor_minimum
        and supported_macro_f1_drop.value
        <= capability_contract_config.supported_macro_f1_drop_maximum
        and benign_far_increase.value
        <= capability_contract_config.benign_false_alarm_rate_increase_maximum
    )


def raw_target_f1_screen_domain_decision_is_positive(
    target_f1_gain: MetricResult,
    supported_macro_f1_drop: MetricResult,
    benign_far_increase: MetricResult,
    capability_contract_config: CapabilityContractConfig,
) -> ScreenDomainDecision:
    if (
        target_f1_gain.value is None
        or supported_macro_f1_drop.value is None
        or benign_far_increase.value is None
    ):
        return False
    return (
        target_f1_gain.value >= capability_contract_config.target_f1_gain_over_anchor_minimum
        and supported_macro_f1_drop.value
        <= capability_contract_config.supported_macro_f1_drop_maximum
        and benign_far_increase.value
        <= capability_contract_config.benign_false_alarm_rate_increase_maximum
    )


def unmatched_control_screen_domain_decision_is_positive(
    unmatched_differential: ScreenDifferential | None,
    target_f1_gain: MetricResult,
    supported_macro_f1_drop: MetricResult,
    benign_far_increase: MetricResult,
    proposal_screen_config: ProposalScreenConfig,
    capability_contract_config: CapabilityContractConfig,
) -> ScreenDomainDecision:
    if unmatched_differential is None:
        return False
    if (
        target_f1_gain.value is None
        or supported_macro_f1_drop.value is None
        or benign_far_increase.value is None
    ):
        return False
    return (
        unmatched_differential >= proposal_screen_config.differential_minimum_nats_per_example
        and target_f1_gain.value >= capability_contract_config.target_f1_gain_over_anchor_minimum
        and supported_macro_f1_drop.value
        <= capability_contract_config.supported_macro_f1_drop_maximum
        and benign_far_increase.value
        <= capability_contract_config.benign_false_alarm_rate_increase_maximum
    )


def candidate_free_screen_domain_predicate(
    anchor_target_f1: MetricResult, capability_contract_config: CapabilityContractConfig
) -> ScreenDomainDecision:
    if anchor_target_f1.value is None:
        return False
    return (
        anchor_target_f1.value < capability_contract_config.candidate_free_anchor_target_f1_maximum
    )


def candidate_screen_transition(
    opening_mode: AdmissionOpeningMode,
    screen_results: Sequence[ScreenDomainResult],
    admission_opening_config: AdmissionOpeningConfig,
) -> AdmissionState:
    adequate_results = [result for result in screen_results if result.is_evidence_adequate]
    if len(adequate_results) < admission_opening_config.required_positive_screen_domains:
        return AdmissionState.DORMANT

    if opening_mode is AdmissionOpeningMode.PROPOSAL_ASSISTED:
        required_count = admission_opening_config.required_positive_screen_domains
    else:
        required_count = admission_opening_config.candidate_free_required_adequate_domains

    predicate_count = sum(1 for result in adequate_results if result.meets_opening_predicate)
    if predicate_count >= required_count:
        return AdmissionState.ADMISSION_OPEN
    return AdmissionState.REJECTED


SOURCE_SELECTION_SEED_SEPARATOR = "SOURCE_SELECTION_SEED"


class OpeningIdentity(FrozenDomainModel):
    capability_identity: CapabilityIdentity
    contract_passes: CapabilityContractSatisfied


def target_role_count(adapter: DatasetAdapter, domain: DomainId, role: Role) -> ExampleCount:
    rows = adapter.load_rows(domain, adapter.target_class_token, role)
    return 0 if rows is None else rows.row_count


def first_target_sample_id(
    adapter: DatasetAdapter, domain: DomainId, role: Role
) -> ArtifactDigest | None:
    rows = adapter.load_rows(domain, adapter.target_class_token, role)
    if rows is None or not rows.sample_ids:
        return None
    return rows.sample_ids[0]


def supported_role_count(adapter: DatasetAdapter, domain: DomainId, role: Role) -> ExampleCount:
    total: ExampleCount = 0
    for class_id in adapter.class_tokens:
        if class_id == adapter.target_class_token:
            continue
        rows = adapter.load_rows(domain, class_id, role)
        if rows is not None:
            total += rows.row_count
    return total


def domains_with_class(
    adapter: DatasetAdapter, class_id: DatasetClassToken, role: Role
) -> frozenset[DomainId]:
    return frozenset(
        domain
        for domain in adapter.domain_ids
        if adapter.load_rows(domain, class_id, role) is not None
    )


def opening_identity(
    adapter: DatasetAdapter, dataset_manifest_hash: ArtifactDigest
) -> OpeningIdentity:
    contract = capability_contract_for_digest(adapter, dataset_manifest_hash)
    return OpeningIdentity(
        capability_identity=compute_capability_identity(contract),
        contract_passes=False,
    )


def _source_requires_attack_carrier(cell: ScientificCell) -> BooleanValue:
    return cell.condition == ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT


def source_domain_for_cell(adapter: DatasetAdapter, cell: ScientificCell) -> DomainId | None:
    source_order = source_selection_order(
        adapter.domain_ids, derive_uint32(SOURCE_SELECTION_SEED_SEPARATOR, cell.master_seed)
    )
    validate_exactly_one_source_domain((source_order[0],))
    domains_with_target = domains_with_class(
        adapter, adapter.target_class_token, Role.SOURCE_PROPOSAL
    ) | domains_with_class(adapter, adapter.target_class_token, Role.REPRODUCTION)
    domains_with_carrier = domains_with_class(
        adapter, adapter.attack_carrier_class_token(), Role.POST_REFERENCE_REPLAY
    )
    requires_carrier = _source_requires_attack_carrier(cell)
    selected = select_source_domain(
        source_order,
        domains_with_target,
        requires_attack_carrier=requires_carrier,
        domains_with_attack_carrier=domains_with_carrier,
    )
    return selected if selected is not None else None
