from __future__ import annotations

import itertools
from collections.abc import Sequence

import torch

from fedsira.config import LeaveFaultCertificateConfig
from fedsira.domain.enums import AdmissionDecisionMethod, AdmissionState
from fedsira.domain.types import (
    BooleanValue,
    DomainId,
    EligibleEvidenceHolderCount,
    FrozenDomainModel,
    MaximumByzantineReproductionRows,
    NumericalEpsilon,
    ProductionWeight,
    ProposalClaim,
    StandardizedValue,
    SupportedMacroF1Drop,
    TargetF1,
    WeiszfeldIterationCount,
)
from fedsira.protocol.synthesis import CertifiedReproductionRow, select_krum_update


class LeaveFaultEvidence(FrozenDomainModel):
    domain: DomainId
    update_components: tuple[StandardizedValue, ...]
    utility: TargetF1
    harm: SupportedMacroF1Drop


class LeaveFaultAdmissionInput(FrozenDomainModel):
    source_domain: DomainId
    proposal_claim: ProposalClaim
    source_update: tuple[StandardizedValue, ...]
    source_utility: TargetF1
    source_harm: SupportedMacroF1Drop
    evidence: tuple[LeaveFaultEvidence, ...]


class LeaveFaultSwitches(FrozenDomainModel):
    exclude_source: BooleanValue
    use_worst_case: BooleanValue
    use_geometric_median: BooleanValue
    use_lower_median: BooleanValue


class LeaveFaultWeight(FrozenDomainModel):
    domain: DomainId
    weight: ProductionWeight


class LeaveFaultDecision(FrozenDomainModel):
    state: AdmissionState
    certificate_utility: TargetF1 | None
    certificate_harm: SupportedMacroF1Drop | None
    production_update: tuple[StandardizedValue, ...] | None
    source_production_weight: ProductionWeight
    participant_weights: tuple[LeaveFaultWeight, ...]


def switches_for(method: AdmissionDecisionMethod) -> LeaveFaultSwitches:
    if method is AdmissionDecisionMethod.LEAVE_FAULT_CERTIFICATE:
        return _full_switches()
    if method is AdmissionDecisionMethod.WITHOUT_SOURCE_EXCLUSION:
        return _switches(False, True, True, True)
    if method is AdmissionDecisionMethod.WITHOUT_WORST_CASE:
        return _switches(True, False, True, True)
    if method is AdmissionDecisionMethod.WITHOUT_GEOMETRIC_MEDIAN:
        return _switches(True, True, False, True)
    if method is AdmissionDecisionMethod.WITHOUT_LOWER_MEDIAN:
        return _switches(True, True, True, False)
    raise ValueError(f"{method} is not a leave-fault certificate mechanism")


def decide_leave_fault_certificate(
    admission_input: LeaveFaultAdmissionInput,
    method: AdmissionDecisionMethod,
    certificate_config: LeaveFaultCertificateConfig,
) -> LeaveFaultDecision:
    switches = switches_for(method)
    evidence = _ordered_evidence(_selected_evidence(admission_input, switches.exclude_source))
    _reject_duplicate_domains(evidence)
    _require_aligned_updates(evidence)
    fault_bound = _effective_fault_bound(certificate_config, switches.use_worst_case)
    if not _support_is_sufficient(len(evidence), certificate_config, fault_bound):
        return _closed_decision(AdmissionState.DORMANT, None, None)
    coalitions = _coalitions(evidence, fault_bound)
    means = tuple(_mean_update(evidence, coalition) for coalition in coalitions)
    utilities = tuple(
        _coalition_statistic(evidence, coalition, switches.use_lower_median, utility=True)
        for coalition in coalitions
    )
    harms = tuple(
        _coalition_statistic(evidence, coalition, True, utility=False) for coalition in coalitions
    )
    certificate_utility = min(utilities)
    certificate_harm = max(harms)
    if not _thresholds_pass(certificate_utility, certificate_harm, certificate_config):
        return _closed_decision(AdmissionState.REJECTED, certificate_utility, certificate_harm)
    production = _production_update(evidence, means, switches, certificate_config)
    if production is None:
        return _closed_decision(AdmissionState.DORMANT, certificate_utility, certificate_harm)
    weights = _participant_weights(
        evidence, coalitions, means, production, switches, certificate_config
    )
    return LeaveFaultDecision(
        state=AdmissionState.ADMITTED,
        certificate_utility=certificate_utility,
        certificate_harm=certificate_harm,
        production_update=_components(production),
        source_production_weight=_source_authority(
            switches.exclude_source, weights, admission_input.source_domain
        ),
        participant_weights=weights,
    )


def production_matches(
    production_update: tuple[StandardizedValue, ...] | None,
    reference_update: tuple[StandardizedValue, ...] | None,
    epsilon: NumericalEpsilon,
) -> BooleanValue:
    if production_update is None or reference_update is None:
        return False
    if len(production_update) != len(reference_update):
        return False
    distance = sum(
        (left - right) ** 2 for left, right in zip(production_update, reference_update, strict=True)
    )
    return distance <= epsilon


def source_weight_in(
    participant_weights: tuple[LeaveFaultWeight, ...], source_domain: DomainId
) -> ProductionWeight:
    for item in participant_weights:
        if item.domain == source_domain:
            return item.weight
    return 0.0


def lower_median_value(values: tuple[TargetF1, ...]) -> TargetF1:
    ordered = tuple(sorted(values))
    return ordered[(len(ordered) - 1) // 2]


def upper_median_value(values: tuple[TargetF1, ...]) -> TargetF1:
    ordered = tuple(sorted(values))
    return ordered[len(ordered) // 2]


def _full_switches() -> LeaveFaultSwitches:
    return _switches(True, True, True, True)


def _switches(
    exclude_source: BooleanValue,
    use_worst_case: BooleanValue,
    use_geometric_median: BooleanValue,
    use_lower_median: BooleanValue,
) -> LeaveFaultSwitches:
    return LeaveFaultSwitches(
        exclude_source=exclude_source,
        use_worst_case=use_worst_case,
        use_geometric_median=use_geometric_median,
        use_lower_median=use_lower_median,
    )


def _selected_evidence(
    admission_input: LeaveFaultAdmissionInput, exclude_source: BooleanValue
) -> tuple[LeaveFaultEvidence, ...]:
    independent = tuple(
        item for item in admission_input.evidence if item.domain != admission_input.source_domain
    )
    if exclude_source:
        return independent
    source_row = LeaveFaultEvidence(
        domain=admission_input.source_domain,
        update_components=admission_input.source_update,
        utility=admission_input.source_utility,
        harm=admission_input.source_harm,
    )
    return independent + (source_row,)


def _ordered_evidence(
    evidence: tuple[LeaveFaultEvidence, ...],
) -> tuple[LeaveFaultEvidence, ...]:
    return tuple(sorted(evidence, key=lambda item: item.domain))


def _reject_duplicate_domains(evidence: tuple[LeaveFaultEvidence, ...]) -> None:
    domains = tuple(item.domain for item in evidence)
    if len(domains) != len(set(domains)):
        raise ValueError("leave-fault evidence repeats a domain")


def _require_aligned_updates(evidence: tuple[LeaveFaultEvidence, ...]) -> None:
    if not evidence:
        raise ValueError("leave-fault evidence is empty")
    width = len(evidence[0].update_components)
    if width == 0:
        raise ValueError("leave-fault update is empty")
    for item in evidence:
        if len(item.update_components) != width:
            raise ValueError("leave-fault evidence dimension mismatch")


def _effective_fault_bound(
    certificate_config: LeaveFaultCertificateConfig, use_worst_case: BooleanValue
) -> MaximumByzantineReproductionRows:
    if use_worst_case:
        return certificate_config.fault_bound
    return 0


def _support_is_sufficient(
    count: EligibleEvidenceHolderCount,
    certificate_config: LeaveFaultCertificateConfig,
    fault_bound: MaximumByzantineReproductionRows,
) -> BooleanValue:
    return count >= certificate_config.minimum_support and count >= 2 * fault_bound + 1


def _coalitions(
    evidence: tuple[LeaveFaultEvidence, ...],
    fault_bound: MaximumByzantineReproductionRows,
) -> tuple[tuple[DomainId, ...], ...]:
    domains = tuple(item.domain for item in evidence)
    if fault_bound == 0:
        return (domains,)
    removed = tuple(itertools.combinations(domains, fault_bound))
    return tuple(
        tuple(domain for domain in domains if domain not in fault_set) for fault_set in removed
    )


def _mean_update(
    evidence: tuple[LeaveFaultEvidence, ...], coalition: tuple[DomainId, ...]
) -> torch.Tensor:
    rows = _vectors_for(evidence, coalition)
    return torch.stack(rows, dim=0).mean(dim=0)


def _coalition_statistic(
    evidence: tuple[LeaveFaultEvidence, ...],
    coalition: tuple[DomainId, ...],
    use_lower_median: BooleanValue,
    *,
    utility: BooleanValue,
) -> TargetF1:
    values = tuple(
        item.utility if utility else item.harm for item in evidence if item.domain in coalition
    )
    if utility and not use_lower_median:
        return _arithmetic_mean(values)
    if utility:
        return lower_median_value(values)
    return upper_median_value(values)


def _arithmetic_mean(values: tuple[TargetF1, ...]) -> TargetF1:
    if all(value == values[0] for value in values):
        return values[0]
    return sum(values) / len(values)


def _thresholds_pass(
    certificate_utility: TargetF1,
    certificate_harm: SupportedMacroF1Drop,
    certificate_config: LeaveFaultCertificateConfig,
) -> BooleanValue:
    return (
        certificate_utility >= certificate_config.utility_floor
        and certificate_harm <= certificate_config.harm_ceiling
    )


def _production_update(
    evidence: tuple[LeaveFaultEvidence, ...],
    means: tuple[torch.Tensor, ...],
    switches: LeaveFaultSwitches,
    certificate_config: LeaveFaultCertificateConfig,
) -> torch.Tensor | None:
    if switches.use_geometric_median:
        return _geometric_median(
            means,
            certificate_config.weiszfeld_iterations,
            certificate_config.weiszfeld_epsilon,
        )
    rows = tuple(
        CertifiedReproductionRow(
            reproducer_domain=item.domain,
            update_vector=_as_tensor(item.update_components),
        )
        for item in evidence
    )
    try:
        selected = select_krum_update(rows, certificate_config.fault_bound)
    except ValueError:
        return None
    return selected.update_vector


def _geometric_median(
    points: tuple[torch.Tensor, ...],
    iterations: WeiszfeldIterationCount,
    epsilon: NumericalEpsilon,
) -> torch.Tensor:
    current = torch.median(torch.stack(points, dim=0), dim=0).values
    for _ in range(iterations):
        distances = tuple(_euclidean_distance(point, current) for point in points)
        if min(distances) <= epsilon:
            return _nearest_point(points, distances)
        current = _inverse_distance_mean(points, distances)
    return current


def _nearest_point(
    points: tuple[torch.Tensor, ...], distances: tuple[StandardizedValue, ...]
) -> torch.Tensor:
    nearest = min(range(len(distances)), key=lambda index: (distances[index], index))
    return points[nearest]


def _inverse_distance_mean(
    points: tuple[torch.Tensor, ...], distances: tuple[StandardizedValue, ...]
) -> torch.Tensor:
    total = 0.0
    accumulator = torch.zeros_like(points[0])
    for point, distance in zip(points, distances, strict=True):
        weight = 1.0 / distance
        accumulator = accumulator + point * weight
        total += weight
    return accumulator / total


def _participant_weights(
    evidence: tuple[LeaveFaultEvidence, ...],
    coalitions: tuple[tuple[DomainId, ...], ...],
    means: tuple[torch.Tensor, ...],
    production: torch.Tensor,
    switches: LeaveFaultSwitches,
    certificate_config: LeaveFaultCertificateConfig,
) -> tuple[LeaveFaultWeight, ...]:
    if not switches.use_geometric_median:
        return _one_hot_weights(evidence, production, certificate_config.weiszfeld_epsilon)
    betas = tuple(
        _coalition_beta(mean, production, certificate_config.weiszfeld_epsilon) for mean in means
    )
    if sum(betas) == 0:
        betas = tuple(1.0 for _beta in betas)
    domains = tuple(item.domain for item in evidence)
    raw = tuple(
        sum(beta for beta, coalition in zip(betas, coalitions, strict=True) if domain in coalition)
        for domain in domains
    )
    total = sum(raw)
    return tuple(
        LeaveFaultWeight(domain=domain, weight=weight / total)
        for domain, weight in zip(domains, raw, strict=True)
    )


def _one_hot_weights(
    evidence: tuple[LeaveFaultEvidence, ...],
    production: torch.Tensor,
    epsilon: NumericalEpsilon,
) -> tuple[LeaveFaultWeight, ...]:
    components = _components(production)
    assigned = False
    weights: list[LeaveFaultWeight] = []
    for item in evidence:
        selected = (not assigned) and production_matches(
            components, item.update_components, epsilon
        )
        if selected:
            assigned = True
        weight = 1.0 if selected else 0.0
        weights.append(LeaveFaultWeight(domain=item.domain, weight=weight))
    return tuple(weights)


def _coalition_beta(
    mean: torch.Tensor, production: torch.Tensor, epsilon: NumericalEpsilon
) -> ProductionWeight:
    distance = _euclidean_distance(mean, production)
    if distance <= epsilon:
        return 0.0
    return 1.0 / distance


def _closed_decision(
    state: AdmissionState,
    certificate_utility: TargetF1 | None,
    certificate_harm: SupportedMacroF1Drop | None,
) -> LeaveFaultDecision:
    return LeaveFaultDecision(
        state=state,
        certificate_utility=certificate_utility,
        certificate_harm=certificate_harm,
        production_update=None,
        source_production_weight=0.0,
        participant_weights=(),
    )


def _source_authority(
    exclude_source: BooleanValue,
    participant_weights: tuple[LeaveFaultWeight, ...],
    source_domain: DomainId,
) -> ProductionWeight:
    if exclude_source:
        return 0.0
    return source_weight_in(participant_weights, source_domain)


def _vectors_for(
    evidence: tuple[LeaveFaultEvidence, ...], coalition: tuple[DomainId, ...]
) -> tuple[torch.Tensor, ...]:
    return tuple(
        _as_tensor(item.update_components) for item in evidence if item.domain in coalition
    )


def _euclidean_distance(left: torch.Tensor, right: torch.Tensor) -> StandardizedValue:
    return float(torch.sqrt(torch.sum((left - right) ** 2)))


def _as_tensor(components: Sequence[StandardizedValue]) -> torch.Tensor:
    return torch.tensor(components, dtype=torch.float64)


def _components(production: torch.Tensor) -> tuple[StandardizedValue, ...]:
    return tuple(float(production[index].item()) for index in range(int(production.shape[0])))
