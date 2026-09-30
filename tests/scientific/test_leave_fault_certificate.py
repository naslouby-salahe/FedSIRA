import itertools

from fedsira.domain.enums import AdmissionDecisionMethod, AdmissionState, ControlledAdmissionWorld
from fedsira.domain.types import DomainId, MasterSeed, StandardizedValue, TargetF1
from fedsira.experiments.leave_fault_validation import comparison_context_for_seed
from fedsira.protocol.admission_comparison import (
    AdmissionComparisonContext,
    AdmissionComparisonResult,
    controlled_admission_case,
    execute_admission_case,
    execute_recorded_case,
)
from fedsira.protocol.leave_fault_certificate import (
    LeaveFaultAdmissionInput,
    LeaveFaultEvidence,
    decide_leave_fault_certificate,
    lower_median_value,
    production_matches,
)
from fedsira.runtime import current_application_context


def _seed() -> MasterSeed:
    return current_application_context().scientific_config.seeds_and_determinism.smoke_seed


def _context() -> AdmissionComparisonContext:
    return comparison_context_for_seed(_seed())


def _decision(
    world: ControlledAdmissionWorld, method: AdmissionDecisionMethod
) -> AdmissionComparisonResult:
    return execute_admission_case(method, world, _seed(), _context())


def _certificate(world: ControlledAdmissionWorld) -> AdmissionComparisonResult:
    return _decision(world, AdmissionDecisionMethod.LEAVE_FAULT_CERTIFICATE)


def test_loaded_certificate_matches_lifecycle_safeguards() -> None:
    protocol = current_application_context().scientific_config.protocol
    certificate = protocol.leave_fault_certificate
    assert certificate.utility_floor == protocol.final_gate.median_target_f1_minimum
    assert certificate.harm_ceiling == protocol.final_gate.supported_macro_f1_drop_maximum
    assert certificate.fault_bound == protocol.synthesis.maximum_byzantine_reproduction_rows
    assert certificate.minimum_support >= 2 * certificate.fault_bound + 1


def test_fixed_inputs_are_deterministic() -> None:
    context = _context()
    case = execute_admission_case(
        AdmissionDecisionMethod.LEAVE_FAULT_CERTIFICATE,
        ControlledAdmissionWorld.ALL_HONEST,
        _seed(),
        context,
    )
    repeated = decide_leave_fault_certificate(
        case.admission_input,
        AdmissionDecisionMethod.LEAVE_FAULT_CERTIFICATE,
        context.certificate_config,
    )
    direct = decide_leave_fault_certificate(
        case.admission_input,
        AdmissionDecisionMethod.LEAVE_FAULT_CERTIFICATE,
        context.certificate_config,
    )
    assert direct == repeated
    assert direct.state is case.state
    assert direct.source_production_weight == case.source_production_weight


def test_evidence_order_does_not_change_the_certificate() -> None:
    context = _context()
    case = execute_admission_case(
        AdmissionDecisionMethod.LEAVE_FAULT_CERTIFICATE,
        ControlledAdmissionWorld.KRUM_IN_GEOMETRY,
        _seed(),
        context,
    )
    original = decide_leave_fault_certificate(
        case.admission_input,
        AdmissionDecisionMethod.LEAVE_FAULT_CERTIFICATE,
        context.certificate_config,
    )
    rotated = case.admission_input.model_copy(
        update={"evidence": case.admission_input.evidence[1:] + case.admission_input.evidence[:1]}
    )
    rotated_decision = decide_leave_fault_certificate(
        rotated,
        AdmissionDecisionMethod.LEAVE_FAULT_CERTIFICATE,
        context.certificate_config,
    )
    assert rotated_decision.state is original.state
    assert rotated_decision.certificate_utility == original.certificate_utility
    assert rotated_decision.production_update == original.production_update
    assert rotated_decision.source_production_weight == original.source_production_weight


def test_source_update_does_not_change_honest_production() -> None:
    context = _context()
    honest = execute_admission_case(
        AdmissionDecisionMethod.LEAVE_FAULT_CERTIFICATE,
        ControlledAdmissionWorld.ALL_HONEST,
        _seed(),
        context,
    )
    changed = honest.admission_input.model_copy(
        update={"source_update": _shifted_source(honest.admission_input)}
    )
    changed_decision = decide_leave_fault_certificate(
        changed,
        AdmissionDecisionMethod.LEAVE_FAULT_CERTIFICATE,
        context.certificate_config,
    )
    assert honest.source_production_weight == 0.0
    assert changed_decision.source_production_weight == 0.0
    assert changed_decision.production_update == honest.production_update
    assert changed_decision.state is honest.state


def test_removing_source_exclusion_lets_the_source_move_production() -> None:
    context = _context()
    included = execute_admission_case(
        AdmissionDecisionMethod.WITHOUT_SOURCE_EXCLUSION,
        ControlledAdmissionWorld.ALL_HONEST,
        _seed(),
        context,
    )
    changed = included.admission_input.model_copy(
        update={"source_update": _shifted_source(included.admission_input)}
    )
    changed_decision = decide_leave_fault_certificate(
        changed,
        AdmissionDecisionMethod.WITHOUT_SOURCE_EXCLUSION,
        context.certificate_config,
    )
    assert included.source_production_weight > 0.0
    assert changed_decision.production_update != included.production_update


def test_source_weight_stays_zero_on_every_controlled_world() -> None:
    for world in ControlledAdmissionWorld:
        decision = _certificate(world)
        assert decision.source_production_weight == 0.0


def test_certificate_utility_is_the_worst_leave_fault_lower_median() -> None:
    context = _context()
    decision = _certificate(ControlledAdmissionWorld.CONFLICTING_EVIDENCE)
    expected = _worst_leave_fault_lower_median(
        decision.admission_input, int(context.certificate_config.fault_bound)
    )
    assert decision.certificate_utility == expected


def test_zero_fault_bound_reduces_to_the_non_source_mean_gate() -> None:
    context = _context()
    case = execute_admission_case(
        AdmissionDecisionMethod.LEAVE_FAULT_CERTIFICATE,
        ControlledAdmissionWorld.ALL_HONEST,
        _seed(),
        context,
    )
    unlimited = context.certificate_config.model_copy(update={"fault_bound": 0})
    decision = decide_leave_fault_certificate(
        case.admission_input,
        AdmissionDecisionMethod.LEAVE_FAULT_CERTIFICATE,
        unlimited,
    )
    mean_update = _mean_update(case.admission_input)
    assert production_matches(decision.production_update, mean_update, unlimited.weiszfeld_epsilon)
    assert decision.certificate_utility == lower_median_value(
        tuple(item.utility for item in case.admission_input.evidence)
    )
    assert decision.source_production_weight == 0.0


def test_insufficient_evidence_stays_dormant() -> None:
    decision = _certificate(ControlledAdmissionWorld.INSUFFICIENT_EVIDENCE)
    assert decision.state is AdmissionState.DORMANT
    assert decision.production_update is None
    assert decision.source_production_weight == 0.0


def test_conflicting_evidence_is_rejected_by_the_worst_coalition() -> None:
    context = _context()
    decision = _certificate(ControlledAdmissionWorld.CONFLICTING_EVIDENCE)
    assert decision.state is AdmissionState.REJECTED
    assert decision.certificate_utility is not None
    assert decision.certificate_utility < context.certificate_config.utility_floor
    assert decision.source_production_weight == 0.0


def test_in_geometry_attacker_is_not_the_production_update() -> None:
    certificate = _certificate(ControlledAdmissionWorld.KRUM_IN_GEOMETRY)
    lifecycle = _decision(
        ControlledAdmissionWorld.KRUM_IN_GEOMETRY, AdmissionDecisionMethod.LIFECYCLE
    )
    krum = _decision(
        ControlledAdmissionWorld.KRUM_IN_GEOMETRY, AdmissionDecisionMethod.KRUM_SELECTION
    )
    without_median = _decision(
        ControlledAdmissionWorld.KRUM_IN_GEOMETRY,
        AdmissionDecisionMethod.WITHOUT_GEOMETRIC_MEDIAN,
    )
    assert lifecycle.state is AdmissionState.ADMITTED
    assert lifecycle.production_equals_malicious
    assert krum.state is AdmissionState.ADMITTED
    assert krum.production_equals_malicious
    assert certificate.state is AdmissionState.ADMITTED
    assert not certificate.production_equals_malicious
    assert certificate.source_production_weight == 0.0
    assert without_median.production_equals_malicious


def test_one_low_report_does_not_reject_a_useful_capability() -> None:
    context = _context()
    certificate = _certificate(ControlledAdmissionWorld.BYZANTINE_LOW_REPORT)
    lifecycle = _decision(
        ControlledAdmissionWorld.BYZANTINE_LOW_REPORT, AdmissionDecisionMethod.LIFECYCLE
    )
    floor = context.certificate_config.utility_floor
    fault_bound = int(context.certificate_config.fault_bound)
    evidence = _sorted_evidence(certificate.admission_input)
    low_domains = _domains_below(evidence, floor)
    index = _lower_median_index(len(evidence) - fault_bound)
    kept = _lower_medians_keeping(evidence, fault_bound, low_domains)
    assert lifecycle.state is AdmissionState.REJECTED
    assert len(low_domains) == 1
    assert len(low_domains) <= index
    assert kept
    assert all(value == floor for value in kept)
    assert certificate.state is AdmissionState.ADMITTED
    assert certificate.certificate_utility == floor
    assert certificate.certificate_utility == _worst_leave_fault_lower_median(
        certificate.admission_input, fault_bound
    )
    assert certificate.source_production_weight == 0.0
    assert not certificate.production_equals_malicious


def test_two_low_reports_remain_above_the_lower_median_index() -> None:
    context = _context()
    certificate = _certificate(ControlledAdmissionWorld.QUORUM_FALSE_REJECTION)
    lifecycle = _decision(
        ControlledAdmissionWorld.QUORUM_FALSE_REJECTION, AdmissionDecisionMethod.LIFECYCLE
    )
    floor = context.certificate_config.utility_floor
    fault_bound = int(context.certificate_config.fault_bound)
    evidence = _sorted_evidence(certificate.admission_input)
    low_domains = _domains_below(evidence, floor)
    coalition_size = len(evidence) - fault_bound
    index = _lower_median_index(coalition_size)
    kept = _lower_medians_keeping(evidence, fault_bound, low_domains)
    assert lifecycle.state is AdmissionState.REJECTED
    assert len(evidence) == 7
    assert fault_bound == 1
    assert coalition_size == 6
    assert index == 2
    assert len(low_domains) == 2
    assert len(low_domains) <= index
    assert kept
    assert all(value == floor for value in kept)
    assert certificate.state is AdmissionState.ADMITTED
    assert certificate.certificate_utility == floor
    assert certificate.certificate_utility == _worst_leave_fault_lower_median(
        certificate.admission_input, fault_bound
    )
    assert certificate.source_production_weight == 0.0


def test_quorum_false_admission_stays_rejected() -> None:
    certificate = _certificate(ControlledAdmissionWorld.QUORUM_FALSE_ADMISSION)
    quorum = _decision(
        ControlledAdmissionWorld.QUORUM_FALSE_ADMISSION, AdmissionDecisionMethod.QUORUM
    )
    assert quorum.state is AdmissionState.ADMITTED
    assert certificate.state is AdmissionState.REJECTED


def test_coordinate_median_can_emit_the_fault_bound_attacker() -> None:
    certificate = _certificate(ControlledAdmissionWorld.FAULT_AT_BOUND)
    median = _decision(
        ControlledAdmissionWorld.FAULT_AT_BOUND, AdmissionDecisionMethod.COORDINATE_MEDIAN
    )
    assert median.production_equals_malicious
    assert certificate.state is AdmissionState.ADMITTED
    assert not certificate.production_equals_malicious
    assert certificate.source_production_weight == 0.0


def test_lower_median_ablation_admits_the_sharp_quality_gap() -> None:
    full = _certificate(ControlledAdmissionWorld.SHARP_QUALITY_GAP)
    mean_rule = _decision(
        ControlledAdmissionWorld.SHARP_QUALITY_GAP,
        AdmissionDecisionMethod.WITHOUT_LOWER_MEDIAN,
    )
    assert full.state is AdmissionState.REJECTED
    assert mean_rule.state is AdmissionState.ADMITTED


def test_worst_case_ablation_admits_conflicting_evidence() -> None:
    full = _certificate(ControlledAdmissionWorld.CONFLICTING_EVIDENCE)
    average_case = _decision(
        ControlledAdmissionWorld.CONFLICTING_EVIDENCE,
        AdmissionDecisionMethod.WITHOUT_WORST_CASE,
    )
    assert full.state is AdmissionState.REJECTED
    assert average_case.state is AdmissionState.ADMITTED


def test_recorded_inputs_recompute_the_shipped_decision() -> None:
    context = _context()
    case = controlled_admission_case(ControlledAdmissionWorld.BYZANTINE_SOURCE, _seed(), context)
    recomputed = execute_recorded_case(
        AdmissionDecisionMethod.LEAVE_FAULT_CERTIFICATE,
        case,
        context,
    )
    direct = decide_leave_fault_certificate(
        case.admission_input,
        AdmissionDecisionMethod.LEAVE_FAULT_CERTIFICATE,
        context.certificate_config,
    )
    assert recomputed.state is direct.state
    assert recomputed.source_production_weight == 0.0
    assert direct.source_production_weight == 0.0
    direct_source = _decision(
        ControlledAdmissionWorld.BYZANTINE_SOURCE, AdmissionDecisionMethod.DIRECT_SOURCE
    )
    assert direct_source.production_equals_malicious
    assert direct_source.source_production_weight == 1.0
    assert not recomputed.production_equals_malicious


def _sorted_evidence(
    admission_input: LeaveFaultAdmissionInput,
) -> tuple[LeaveFaultEvidence, ...]:
    return tuple(sorted(admission_input.evidence, key=lambda item: item.domain))


def _domains_below(
    evidence: tuple[LeaveFaultEvidence, ...], floor: TargetF1
) -> tuple[DomainId, ...]:
    return tuple(item.domain for item in evidence if item.utility < floor)


def _lower_median_index(coalition_size: int) -> int:
    return (coalition_size - 1) // 2


def _lower_medians_keeping(
    evidence: tuple[LeaveFaultEvidence, ...],
    fault_bound: int,
    required_domains: tuple[DomainId, ...],
) -> tuple[TargetF1, ...]:
    retained: list[TargetF1] = []
    for fault_set in itertools.combinations(range(len(evidence)), fault_bound):
        coalition = tuple(item for index, item in enumerate(evidence) if index not in fault_set)
        present = {item.domain for item in coalition}
        if all(domain in present for domain in required_domains):
            retained.append(lower_median_value(tuple(item.utility for item in coalition)))
    return tuple(retained)


def _shifted_source(admission_input: LeaveFaultAdmissionInput) -> tuple[StandardizedValue, ...]:
    first = admission_input.evidence[0].update_components
    return tuple(component + 1.0 for component in first)


def _mean_update(admission_input: LeaveFaultAdmissionInput) -> tuple[StandardizedValue, ...]:
    evidence = admission_input.evidence
    width = len(evidence[0].update_components)
    totals = [0.0 for _index in range(width)]
    for item in evidence:
        for index, component in enumerate(item.update_components):
            totals[index] += float(component)
    count = len(evidence)
    return tuple(value / count for value in totals)


def _worst_leave_fault_lower_median(
    admission_input: LeaveFaultAdmissionInput, fault_bound: int
) -> TargetF1:
    evidence = tuple(sorted(admission_input.evidence, key=lambda item: item.domain))
    if fault_bound == 0:
        coalitions = (evidence,)
    else:
        removed = tuple(itertools.combinations(range(len(evidence)), fault_bound))
        coalitions = tuple(
            tuple(item for index, item in enumerate(evidence) if index not in fault_set)
            for fault_set in removed
        )
    return min(
        lower_median_value(tuple(item.utility for item in coalition)) for coalition in coalitions
    )
