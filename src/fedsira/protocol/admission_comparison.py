from __future__ import annotations

from enum import StrEnum

import torch

from fedsira.config import (
    AdmissionOpeningConfig,
    CapabilityContractConfig,
    FinalGateConfig,
    LeaveFaultCertificateConfig,
)
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER
from fedsira.domain.enums import (
    AdmissionDecisionMethod,
    AdmissionOpeningMode,
    AdmissionState,
    ControlledAdmissionWorld,
)
from fedsira.domain.types import (
    BooleanValue,
    DomainCount,
    DomainId,
    FrozenDomainModel,
    MasterSeed,
    MaximumByzantineReproductionRows,
    NamespaceSeed,
    NumericalEpsilon,
    Probability,
    ProductionWeight,
    ProposalClaim,
    StandardizedValue,
    SupportedMacroF1Drop,
    TargetF1,
)
from fedsira.evaluation.statistics import quantile_type7
from fedsira.protocol.baselines.defenses import coordinate_wise_median_synthesis
from fedsira.protocol.leave_fault_certificate import (
    LeaveFaultAdmissionInput,
    LeaveFaultDecision,
    LeaveFaultEvidence,
    decide_leave_fault_certificate,
    lower_median_value,
    production_matches,
    upper_median_value,
)
from fedsira.protocol.proposal import (
    ScreenDomainResult,
    candidate_screen_transition,
    screen_domain_order,
)
from fedsira.protocol.rules import krum_committee_is_admissible
from fedsira.protocol.synthesis import (
    CertifiedReproductionRow,
    krum_neighbor_count,
    krum_score,
    select_krum_update,
)

_PROPOSAL_CLAIM: ProposalClaim = "post-reference-capability"
_LOW_UTILITY: TargetF1 = 0.1
_GAP_LOW: TargetF1 = 0.75
_GAP_HIGH: TargetF1 = 1.0
_MEDIAN_PROBABILITY: Probability = 0.5
_ZERO_HARM: SupportedMacroF1Drop = 0.0
_NORTH: tuple[StandardizedValue, ...] = (0.0, 1.0)
_SOUTH: tuple[StandardizedValue, ...] = (0.0, -1.0)
_EAST: tuple[StandardizedValue, ...] = (1.0, 0.0)
_WEST: tuple[StandardizedValue, ...] = (-1.0, 0.0)
_MID: tuple[StandardizedValue, ...] = (0.5, 0.5)
_MID_SOUTH: tuple[StandardizedValue, ...] = (0.5, -0.5)
_UNIT: tuple[StandardizedValue, ...] = (1.0, 1.0)
_OUTLIER: tuple[StandardizedValue, ...] = (8.0, 8.0)
_OUTLIER_NEG: tuple[StandardizedValue, ...] = (-8.0, -8.0)
_MALICIOUS: tuple[StandardizedValue, ...] = (0.1, 0.0)
_FAR: tuple[StandardizedValue, ...] = (10.0, 10.0)
_PERTURBED: tuple[StandardizedValue, ...] = (8.0, 8.0)
_COPIED: tuple[StandardizedValue, ...] = (10.0, 10.0)
_HONEST: tuple[tuple[StandardizedValue, ...], ...] = (
    _NORTH,
    _SOUTH,
    _EAST,
    _WEST,
    _MID,
    _MID_SOUTH,
    _UNIT,
)
_KRUM: tuple[tuple[StandardizedValue, ...], ...] = (
    _NORTH,
    _SOUTH,
    _EAST,
    _WEST,
    _OUTLIER,
    _OUTLIER_NEG,
    _MALICIOUS,
)
_FAULT: tuple[tuple[StandardizedValue, ...], ...] = (
    _NORTH,
    _SOUTH,
    _EAST,
    _WEST,
    _MID,
    _MID_SOUTH,
    _MALICIOUS,
)
_GAP_UTILITIES: tuple[TargetF1, ...] = (_GAP_LOW, _GAP_LOW, _GAP_HIGH, _GAP_HIGH, _GAP_HIGH)
_CERTIFICATE_METHODS: tuple[AdmissionDecisionMethod, ...] = (
    AdmissionDecisionMethod.LEAVE_FAULT_CERTIFICATE,
    AdmissionDecisionMethod.WITHOUT_SOURCE_EXCLUSION,
    AdmissionDecisionMethod.WITHOUT_WORST_CASE,
    AdmissionDecisionMethod.WITHOUT_GEOMETRIC_MEDIAN,
    AdmissionDecisionMethod.WITHOUT_LOWER_MEDIAN,
)


class _EvidenceGeometry(StrEnum):
    HONEST = "honest-cluster"
    KRUM = "krum-outliers"
    FAULT = "fault-bound-vector"
    COPIED = "copied-vector"
    DISAGREEING = "disagreeing-vectors"
    CONSTANT = "constant-vector"


class _UtilityAssignment(StrEnum):
    HIGH = "all-high"
    ONE_SCREEN_LOW = "one-screen-low"
    TWO_SCREEN_LOW = "two-screen-low"
    OPENING = "opening-level"
    ONE_HIGH = "one-high"
    TWO_SCREEN_HIGH = "two-screen-high"
    ALTERNATING = "alternating-quality"
    GAP = "sharp-gap"
    CONFLICT = "conflict-pair"


class _SourcePlacement(StrEnum):
    FAR = "far-source"
    COPIED = "copied-source"
    PERTURBED = "perturbed-source"
    MALICIOUS = "malicious-source"


class _WorldSpec(FrozenDomainModel):
    world: ControlledAdmissionWorld
    domain_count: DomainCount
    geometry: _EvidenceGeometry
    utilities: _UtilityAssignment
    source: _SourcePlacement
    useful: BooleanValue


class AdmissionComparisonContext(FrozenDomainModel):
    certificate_config: LeaveFaultCertificateConfig
    opening_config: AdmissionOpeningConfig
    contract_config: CapabilityContractConfig
    final_gate: FinalGateConfig
    synthesis_fault_bound: MaximumByzantineReproductionRows
    screen_seed: NamespaceSeed


class ControlledAdmissionCase(FrozenDomainModel):
    world: ControlledAdmissionWorld
    master_seed: MasterSeed
    useful_capability: BooleanValue
    malicious_reference: tuple[StandardizedValue, ...]
    admission_input: LeaveFaultAdmissionInput


class AdmissionComparisonResult(FrozenDomainModel):
    method: AdmissionDecisionMethod
    world: ControlledAdmissionWorld
    useful_capability: BooleanValue
    state: AdmissionState
    certificate_utility: TargetF1 | None
    certificate_harm: SupportedMacroF1Drop | None
    production_update: tuple[StandardizedValue, ...] | None
    source_production_weight: ProductionWeight
    production_equals_malicious: BooleanValue
    admission_input: LeaveFaultAdmissionInput


def _spec(
    world: ControlledAdmissionWorld,
    domain_count: DomainCount,
    geometry: _EvidenceGeometry,
    utilities: _UtilityAssignment,
    source: _SourcePlacement,
    useful: BooleanValue,
) -> _WorldSpec:
    return _WorldSpec(
        world=world,
        domain_count=domain_count,
        geometry=geometry,
        utilities=utilities,
        source=source,
        useful=useful,
    )


_WORLD_SPECS: tuple[_WorldSpec, ...] = (
    _spec(
        ControlledAdmissionWorld.ALL_HONEST,
        7,
        _EvidenceGeometry.HONEST,
        _UtilityAssignment.HIGH,
        _SourcePlacement.FAR,
        True,
    ),
    _spec(
        ControlledAdmissionWorld.KRUM_IN_GEOMETRY,
        7,
        _EvidenceGeometry.KRUM,
        _UtilityAssignment.HIGH,
        _SourcePlacement.FAR,
        True,
    ),
    _spec(
        ControlledAdmissionWorld.BYZANTINE_LOW_REPORT,
        7,
        _EvidenceGeometry.HONEST,
        _UtilityAssignment.ONE_SCREEN_LOW,
        _SourcePlacement.FAR,
        True,
    ),
    _spec(
        ControlledAdmissionWorld.QUORUM_FALSE_ADMISSION,
        7,
        _EvidenceGeometry.HONEST,
        _UtilityAssignment.OPENING,
        _SourcePlacement.FAR,
        False,
    ),
    _spec(
        ControlledAdmissionWorld.QUORUM_FALSE_REJECTION,
        7,
        _EvidenceGeometry.HONEST,
        _UtilityAssignment.TWO_SCREEN_LOW,
        _SourcePlacement.FAR,
        True,
    ),
    _spec(
        ControlledAdmissionWorld.INSUFFICIENT_EVIDENCE,
        2,
        _EvidenceGeometry.HONEST,
        _UtilityAssignment.HIGH,
        _SourcePlacement.FAR,
        False,
    ),
    _spec(
        ControlledAdmissionWorld.CONFLICTING_EVIDENCE,
        5,
        _EvidenceGeometry.CONSTANT,
        _UtilityAssignment.CONFLICT,
        _SourcePlacement.FAR,
        False,
    ),
    _spec(
        ControlledAdmissionWorld.SOURCE_COPIED,
        7,
        _EvidenceGeometry.COPIED,
        _UtilityAssignment.HIGH,
        _SourcePlacement.COPIED,
        True,
    ),
    _spec(
        ControlledAdmissionWorld.SOURCE_PERTURBED,
        7,
        _EvidenceGeometry.COPIED,
        _UtilityAssignment.HIGH,
        _SourcePlacement.PERTURBED,
        True,
    ),
    _spec(
        ControlledAdmissionWorld.DISAGREEING_SUPPORTERS,
        7,
        _EvidenceGeometry.DISAGREEING,
        _UtilityAssignment.ALTERNATING,
        _SourcePlacement.FAR,
        False,
    ),
    _spec(
        ControlledAdmissionWorld.SHARP_QUALITY_GAP,
        5,
        _EvidenceGeometry.CONSTANT,
        _UtilityAssignment.GAP,
        _SourcePlacement.FAR,
        False,
    ),
    _spec(
        ControlledAdmissionWorld.ONE_MALICIOUS_REVIEWER,
        7,
        _EvidenceGeometry.HONEST,
        _UtilityAssignment.ONE_HIGH,
        _SourcePlacement.FAR,
        False,
    ),
    _spec(
        ControlledAdmissionWorld.HONEST_MINORITY_STRONG,
        7,
        _EvidenceGeometry.HONEST,
        _UtilityAssignment.TWO_SCREEN_HIGH,
        _SourcePlacement.FAR,
        False,
    ),
    _spec(
        ControlledAdmissionWorld.FAULT_AT_BOUND,
        7,
        _EvidenceGeometry.FAULT,
        _UtilityAssignment.HIGH,
        _SourcePlacement.FAR,
        True,
    ),
    _spec(
        ControlledAdmissionWorld.BYZANTINE_SOURCE,
        7,
        _EvidenceGeometry.HONEST,
        _UtilityAssignment.HIGH,
        _SourcePlacement.MALICIOUS,
        True,
    ),
)


def controlled_admission_case(
    world: ControlledAdmissionWorld,
    master_seed: MasterSeed,
    context: AdmissionComparisonContext,
) -> ControlledAdmissionCase:
    spec = _spec_for(world)
    domains = tuple(NBAIOT_DOMAIN_ORDER[1 : spec.domain_count + 1])
    if len(domains) != spec.domain_count:
        raise ValueError("N-BaIoT domain order is shorter than the controlled case")
    vectors = _evidence_vectors(spec.geometry, spec.domain_count)
    screened = screen_domain_order(
        domains, context.screen_seed, context.opening_config.screen_domains
    )
    utilities = _utilities(
        spec.utilities,
        domains,
        screened,
        context.certificate_config.utility_floor,
        context.contract_config.target_f1_gain_over_anchor_minimum,
    )
    evidence = tuple(
        LeaveFaultEvidence(
            domain=domain,
            update_components=vector,
            utility=utility,
            harm=_ZERO_HARM,
        )
        for domain, vector, utility in zip(domains, vectors, utilities, strict=True)
    )
    return ControlledAdmissionCase(
        world=world,
        master_seed=master_seed,
        useful_capability=spec.useful,
        malicious_reference=_MALICIOUS,
        admission_input=LeaveFaultAdmissionInput(
            source_domain=NBAIOT_DOMAIN_ORDER[0],
            proposal_claim=_PROPOSAL_CLAIM,
            source_update=_source_vector(spec.source, vectors),
            source_utility=context.certificate_config.utility_floor,
            source_harm=_ZERO_HARM,
            evidence=evidence,
        ),
    )


def execute_recorded_case(
    method: AdmissionDecisionMethod,
    case: ControlledAdmissionCase,
    context: AdmissionComparisonContext,
) -> AdmissionComparisonResult:
    if method in _CERTIFICATE_METHODS:
        return _certificate_result(method, case, context)
    if method is AdmissionDecisionMethod.LIFECYCLE:
        return _krum_then_gate(case, context, method, True, True)
    if method is AdmissionDecisionMethod.KRUM_SELECTION:
        return _krum_then_gate(case, context, method, False, False)
    if method is AdmissionDecisionMethod.DIRECT_SOURCE:
        return _direct_source(case, context)
    if method is AdmissionDecisionMethod.QUORUM:
        return _quorum(case, context)
    if method is AdmissionDecisionMethod.COORDINATE_MEDIAN:
        return _coordinate_median(case, context)
    if method is AdmissionDecisionMethod.BULYAN:
        return _bulyan(case, context)
    raise ValueError(f"unmapped admission decision method {method}")


def execute_admission_case(
    method: AdmissionDecisionMethod,
    world: ControlledAdmissionWorld,
    master_seed: MasterSeed,
    context: AdmissionComparisonContext,
) -> AdmissionComparisonResult:
    case = controlled_admission_case(world, master_seed, context)
    return execute_recorded_case(method, case, context)


def admission_comparison_records(
    context: AdmissionComparisonContext,
    master_seed: MasterSeed,
) -> tuple[AdmissionComparisonResult, ...]:
    return tuple(
        execute_admission_case(method, world, master_seed, context)
        for method in AdmissionDecisionMethod
        for world in ControlledAdmissionWorld
    )


def _spec_for(world: ControlledAdmissionWorld) -> _WorldSpec:
    for spec in _WORLD_SPECS:
        if spec.world is world:
            return spec
    raise ValueError(f"unmapped controlled admission world {world}")


def _evidence_vectors(
    geometry: _EvidenceGeometry, count: DomainCount
) -> tuple[tuple[StandardizedValue, ...], ...]:
    pool = _geometry_pool(geometry, count)
    if len(pool) != count:
        raise ValueError("evidence geometry does not match the requested count")
    return pool


def _geometry_pool(
    geometry: _EvidenceGeometry, count: DomainCount
) -> tuple[tuple[StandardizedValue, ...], ...]:
    if geometry is _EvidenceGeometry.HONEST:
        return _HONEST[:count]
    if geometry is _EvidenceGeometry.KRUM:
        return _KRUM[:count]
    if geometry is _EvidenceGeometry.FAULT:
        return _FAULT[:count]
    if geometry is _EvidenceGeometry.COPIED:
        return tuple(_COPIED for _index in range(count))
    if geometry is _EvidenceGeometry.DISAGREEING:
        return tuple(_OUTLIER if index % 2 == 0 else _OUTLIER_NEG for index in range(count))
    if geometry is _EvidenceGeometry.CONSTANT:
        return tuple(_MID for _index in range(count))
    raise ValueError(f"unmapped evidence geometry {geometry}")


def _source_vector(
    placement: _SourcePlacement, evidence_vectors: tuple[tuple[StandardizedValue, ...], ...]
) -> tuple[StandardizedValue, ...]:
    if placement is _SourcePlacement.FAR:
        return _FAR
    if placement is _SourcePlacement.COPIED:
        return evidence_vectors[0]
    if placement is _SourcePlacement.PERTURBED:
        return _PERTURBED
    if placement is _SourcePlacement.MALICIOUS:
        return _MALICIOUS
    raise ValueError(f"unmapped source placement {placement}")


def _utilities(
    pattern: _UtilityAssignment,
    domains: tuple[DomainId, ...],
    screened: tuple[DomainId, ...],
    floor: TargetF1,
    opening: TargetF1,
) -> tuple[TargetF1, ...]:
    if pattern is _UtilityAssignment.HIGH:
        return _fill(domains, floor)
    if pattern is _UtilityAssignment.OPENING:
        return _fill(domains, opening)
    if pattern is _UtilityAssignment.ONE_SCREEN_LOW:
        return _mark(domains, screened[:1], _LOW_UTILITY, floor)
    if pattern is _UtilityAssignment.TWO_SCREEN_LOW:
        return _mark(domains, screened[:2], _LOW_UTILITY, floor)
    if pattern is _UtilityAssignment.TWO_SCREEN_HIGH:
        return _mark(domains, screened[:2], floor, _LOW_UTILITY)
    if pattern is _UtilityAssignment.ONE_HIGH:
        return _mark(domains, domains[:1], floor, _LOW_UTILITY)
    if pattern is _UtilityAssignment.ALTERNATING:
        return tuple(
            floor if index % 2 == 0 else _LOW_UTILITY for index, _domain in enumerate(domains)
        )
    if pattern is _UtilityAssignment.GAP:
        return _gap_utilities(len(domains))
    if pattern is _UtilityAssignment.CONFLICT:
        return _conflict_utilities(domains, screened, floor)
    raise ValueError(f"unmapped utility assignment {pattern}")


def _fill(domains: tuple[DomainId, ...], value: TargetF1) -> tuple[TargetF1, ...]:
    return tuple(value for _domain in domains)


def _mark(
    domains: tuple[DomainId, ...],
    marked: tuple[DomainId, ...],
    marked_value: TargetF1,
    default: TargetF1,
) -> tuple[TargetF1, ...]:
    return tuple(marked_value if domain in marked else default for domain in domains)


def _gap_utilities(count: DomainCount) -> tuple[TargetF1, ...]:
    if len(_GAP_UTILITIES) != count:
        raise ValueError("sharp quality gap requires its declared evidence count")
    return _GAP_UTILITIES


def _conflict_utilities(
    domains: tuple[DomainId, ...], screened: tuple[DomainId, ...], floor: TargetF1
) -> tuple[TargetF1, ...]:
    off_screen = tuple(domain for domain in domains if domain not in screened)
    return _mark(domains, off_screen, _LOW_UTILITY, floor)


def _certificate_result(
    method: AdmissionDecisionMethod,
    case: ControlledAdmissionCase,
    context: AdmissionComparisonContext,
) -> AdmissionComparisonResult:
    decision = decide_leave_fault_certificate(
        case.admission_input, method, context.certificate_config
    )
    return _from_decision(method, case, decision, context)


def _from_decision(
    method: AdmissionDecisionMethod,
    case: ControlledAdmissionCase,
    decision: LeaveFaultDecision,
    context: AdmissionComparisonContext,
) -> AdmissionComparisonResult:
    return _result(
        case,
        method,
        decision.state,
        decision.production_update,
        decision.source_production_weight,
        decision.certificate_utility,
        decision.certificate_harm,
        context.certificate_config.weiszfeld_epsilon,
    )


def _krum_then_gate(
    case: ControlledAdmissionCase,
    context: AdmissionComparisonContext,
    method: AdmissionDecisionMethod,
    require_opening: BooleanValue,
    require_domain_count: BooleanValue,
) -> AdmissionComparisonResult:
    if require_opening:
        opened = _opening_state(case, context)
        if opened is not AdmissionState.ADMISSION_OPEN:
            return _closed_result(case, context, method, opened)
    evidence = case.admission_input.evidence
    if (
        require_domain_count
        and len(evidence) < context.final_gate.minimum_adequate_non_source_domains
    ):
        return _closed_result(case, context, method, AdmissionState.DORMANT)
    selected = _selected_krum(evidence, context.synthesis_fault_bound)
    if selected is None:
        return _closed_result(case, context, method, AdmissionState.DORMANT)
    if not _lifecycle_gate(evidence, context.final_gate):
        return _closed_result(case, context, method, AdmissionState.REJECTED)
    return _result(
        case,
        method,
        AdmissionState.ADMITTED,
        _components(selected),
        0.0,
        None,
        None,
        context.certificate_config.weiszfeld_epsilon,
    )


def _direct_source(
    case: ControlledAdmissionCase, context: AdmissionComparisonContext
) -> AdmissionComparisonResult:
    source = case.admission_input
    admitted = (
        source.source_utility >= context.final_gate.median_target_f1_minimum
        and source.source_harm <= context.final_gate.supported_macro_f1_drop_maximum
    )
    if not admitted:
        return _closed_result(
            case, context, AdmissionDecisionMethod.DIRECT_SOURCE, AdmissionState.REJECTED
        )
    return _result(
        case,
        AdmissionDecisionMethod.DIRECT_SOURCE,
        AdmissionState.ADMITTED,
        source.source_update,
        1.0,
        source.source_utility,
        source.source_harm,
        context.certificate_config.weiszfeld_epsilon,
    )


def _quorum(
    case: ControlledAdmissionCase, context: AdmissionComparisonContext
) -> AdmissionComparisonResult:
    opened = _opening_state(case, context)
    if opened is AdmissionState.ADMISSION_OPEN:
        return _closed_result(
            case, context, AdmissionDecisionMethod.QUORUM, AdmissionState.ADMITTED
        )
    return _closed_result(case, context, AdmissionDecisionMethod.QUORUM, opened)


def _coordinate_median(
    case: ControlledAdmissionCase, context: AdmissionComparisonContext
) -> AdmissionComparisonResult:
    evidence = case.admission_input.evidence
    if not evidence:
        return _closed_result(
            case, context, AdmissionDecisionMethod.COORDINATE_MEDIAN, AdmissionState.DORMANT
        )
    production = coordinate_wise_median_synthesis(_tensors(evidence))
    return _full_set_admission(
        case, context, AdmissionDecisionMethod.COORDINATE_MEDIAN, _components(production)
    )


def _bulyan(
    case: ControlledAdmissionCase, context: AdmissionComparisonContext
) -> AdmissionComparisonResult:
    production = _bulyan_update(case.admission_input.evidence, context.synthesis_fault_bound)
    if production is None:
        return _closed_result(case, context, AdmissionDecisionMethod.BULYAN, AdmissionState.DORMANT)
    return _full_set_admission(
        case, context, AdmissionDecisionMethod.BULYAN, _components(production)
    )


def _full_set_admission(
    case: ControlledAdmissionCase,
    context: AdmissionComparisonContext,
    method: AdmissionDecisionMethod,
    production: tuple[StandardizedValue, ...],
) -> AdmissionComparisonResult:
    evidence = case.admission_input.evidence
    utilities = tuple(item.utility for item in evidence)
    harms = tuple(item.harm for item in evidence)
    utility = lower_median_value(utilities)
    harm = upper_median_value(harms)
    if (
        utility >= context.certificate_config.utility_floor
        and harm <= context.certificate_config.harm_ceiling
    ):
        return _result(
            case,
            method,
            AdmissionState.ADMITTED,
            production,
            0.0,
            utility,
            harm,
            context.certificate_config.weiszfeld_epsilon,
        )
    return _result(
        case,
        method,
        AdmissionState.REJECTED,
        None,
        0.0,
        utility,
        harm,
        context.certificate_config.weiszfeld_epsilon,
    )


def _opening_state(
    case: ControlledAdmissionCase, context: AdmissionComparisonContext
) -> AdmissionState:
    return candidate_screen_transition(
        AdmissionOpeningMode.PROPOSAL_ASSISTED,
        _screen_results(case, context),
        context.opening_config,
    )


def _screen_results(
    case: ControlledAdmissionCase, context: AdmissionComparisonContext
) -> tuple[ScreenDomainResult, ...]:
    evidence = case.admission_input.evidence
    screened = screen_domain_order(
        tuple(item.domain for item in evidence),
        context.screen_seed,
        context.opening_config.screen_domains,
    )
    return tuple(_screen_result(_evidence_for(evidence, domain), context) for domain in screened)


def _evidence_for(evidence: tuple[LeaveFaultEvidence, ...], domain: DomainId) -> LeaveFaultEvidence:
    for item in evidence:
        if item.domain == domain:
            return item
    raise ValueError("screen domain is not in the evidence")


def _screen_result(
    item: LeaveFaultEvidence, context: AdmissionComparisonContext
) -> ScreenDomainResult:
    contract = context.contract_config
    meets = (
        item.utility >= contract.target_f1_gain_over_anchor_minimum
        and item.harm <= contract.supported_macro_f1_drop_maximum
        and item.harm <= contract.benign_false_alarm_rate_increase_maximum
    )
    return ScreenDomainResult(
        domain=item.domain,
        is_evidence_adequate=True,
        meets_opening_predicate=meets,
    )


def _lifecycle_gate(
    evidence: tuple[LeaveFaultEvidence, ...], final_gate: FinalGateConfig
) -> BooleanValue:
    utilities = tuple(item.utility for item in evidence)
    harms = tuple(item.harm for item in evidence)
    median = quantile_type7(tuple(sorted(utilities)), _MEDIAN_PROBABILITY)
    harm_mean = sum(harms) / len(harms)
    return bool(
        median >= final_gate.median_target_f1_minimum
        and min(utilities) >= final_gate.minimum_domain_target_f1
        and harm_mean <= final_gate.supported_macro_f1_drop_maximum
    )


def _selected_krum(
    evidence: tuple[LeaveFaultEvidence, ...],
    fault_bound: MaximumByzantineReproductionRows,
) -> torch.Tensor | None:
    try:
        return select_krum_update(_rows(evidence), fault_bound).update_vector
    except ValueError:
        return None


def _bulyan_update(
    evidence: tuple[LeaveFaultEvidence, ...],
    fault_bound: MaximumByzantineReproductionRows,
) -> torch.Tensor | None:
    rows = _rows(evidence)
    size = len(rows)
    if not krum_committee_is_admissible(size, fault_bound):
        return None
    keep = size - 2 * fault_bound
    if keep < 1:
        return None
    neighbor_count = krum_neighbor_count(size, fault_bound)
    ranked = sorted(
        (krum_score(row, rows, neighbor_count), row.reproducer_domain, row.update_vector)
        for row in rows
    )
    selected = tuple(item[2] for item in ranked[:keep])
    return coordinate_wise_median_synthesis(selected)


def _rows(evidence: tuple[LeaveFaultEvidence, ...]) -> tuple[CertifiedReproductionRow, ...]:
    return tuple(
        CertifiedReproductionRow(
            reproducer_domain=item.domain,
            update_vector=_as_tensor(item.update_components),
        )
        for item in evidence
    )


def _tensors(evidence: tuple[LeaveFaultEvidence, ...]) -> tuple[torch.Tensor, ...]:
    return tuple(_as_tensor(item.update_components) for item in evidence)


def _as_tensor(components: tuple[StandardizedValue, ...]) -> torch.Tensor:
    return torch.tensor(components, dtype=torch.float64)


def _components(production: torch.Tensor) -> tuple[StandardizedValue, ...]:
    width = int(production.shape[0])
    return tuple(float(production[index].item()) for index in range(width))


def _closed_result(
    case: ControlledAdmissionCase,
    context: AdmissionComparisonContext,
    method: AdmissionDecisionMethod,
    state: AdmissionState,
) -> AdmissionComparisonResult:
    return _result(
        case,
        method,
        state,
        None,
        0.0,
        None,
        None,
        context.certificate_config.weiszfeld_epsilon,
    )


def _result(
    case: ControlledAdmissionCase,
    method: AdmissionDecisionMethod,
    state: AdmissionState,
    production_update: tuple[StandardizedValue, ...] | None,
    source_production_weight: ProductionWeight,
    certificate_utility: TargetF1 | None,
    certificate_harm: SupportedMacroF1Drop | None,
    epsilon: NumericalEpsilon,
) -> AdmissionComparisonResult:
    malicious = bool(
        state is AdmissionState.ADMITTED
        and production_matches(production_update, case.malicious_reference, epsilon)
    )
    return AdmissionComparisonResult(
        method=method,
        world=case.world,
        useful_capability=case.useful_capability,
        state=state,
        certificate_utility=certificate_utility,
        certificate_harm=certificate_harm,
        production_update=production_update,
        source_production_weight=source_production_weight,
        production_equals_malicious=malicious,
        admission_input=case.admission_input,
    )
