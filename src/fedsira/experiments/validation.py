from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from fedsira.analysis.statistics import exact_sign_flip_two_sided_p_value, holm_adjusted_p_values
from fedsira.artifacts.paths import smoke_record_path
from fedsira.config.loading import (
    PRODUCTION_CONFIG_PATH,
    TEST_FIXTURE_CONFIG_PATH,
    load_scientific_config,
    load_test_fixture_config,
)
from fedsira.config.schema import ScientificConfig, TestFixtureConfig
from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.preprocessing import assign_stream_roles_and_sample_ids
from fedsira.datasets.nbaiot.schema import NBaiotClass, NBaiotDomain
from fedsira.domain.enums import CellPhaseState, ExperimentLifecycleState, ScientificCellPhase
from fedsira.domain.records import BooleanFlag, CanonicalToken, FrozenDomainModel
from fedsira.experiments.planning import ExperimentPlan, ScientificCell
from fedsira.experiments.registry import (
    AblationVariant,
    BoundCondition,
    CapabilityContractGranularity,
    EpistemicFailureType,
    RootCauseMixture,
    experiment_by_name,
)
from fedsira.protocol.reproduction import validate_commitment_exists_before_verifier_assignment
from fedsira.protocol.theory import (
    diagnostic_at_least_two_byzantine_probability,
    krum_committee_is_admissible,
    minimum_honest_positive_count,
)
from fedsira.protocol.verification import verifier_is_eligible

SMOKE_RECORD_SCHEMA_VERSION: CanonicalToken = "fedsira|smoke_record|1"

_DANMINI = NBaiotDomain.DANMINI_DOORBELL
_ENNIO = NBaiotDomain.ENNIO_DOORBELL

REQUIRED_CELL_PHASES: frozenset[ScientificCellPhase] = frozenset(
    {
        ScientificCellPhase.PREPARE,
        ScientificCellPhase.TRAIN,
        ScientificCellPhase.SCORE,
        ScientificCellPhase.PROTOCOL_EVALUATION,
        ScientificCellPhase.METRIC_AGGREGATION,
        ScientificCellPhase.STATISTICAL_ANALYSIS,
    }
)

TERMINAL_CELL_STATES: frozenset[CellPhaseState] = frozenset(
    {CellPhaseState.COMPLETED, CellPhaseState.FAILED, CellPhaseState.INVALID}
)

_EPISTEMIC_STRENGTHS: dict[EpistemicFailureType, tuple[str, ...]] = {
    EpistemicFailureType.SHARED_LABEL_ERROR: ("0.05", "0.10", "0.20"),
    EpistemicFailureType.SHARED_SPURIOUS_FEATURE: ("0.25", "0.50", "1.00"),
    EpistemicFailureType.ATTACKER_INDUCED_COMMON_CONTEXT: ("0.25", "0.50", "1.00"),
}

_CONDITION_VOCABULARY: dict[CanonicalToken, frozenset[str]] = {
    "Byzantine-Bound Violation": frozenset(condition.value for condition in BoundCondition),
    "Shared Epistemic-Failure Boundary": frozenset(
        f"{failure_type.value}|{strength}"
        for failure_type in EpistemicFailureType
        for strength in _EPISTEMIC_STRENGTHS[failure_type]
    ),
    "Capability Under-Specification Boundary": frozenset(
        mixture.value for mixture in RootCauseMixture
    ),
}

_METHOD_VOCABULARY: dict[CanonicalToken, frozenset[str]] = {
    "Capability Under-Specification Boundary": frozenset(
        granularity.value for granularity in CapabilityContractGranularity
    ),
    "Mechanism Ablation": frozenset(variant.value for variant in AblationVariant),
}


class SmokeCheckResult(FrozenDomainModel):
    name: CanonicalToken
    passed: BooleanFlag
    detail: CanonicalToken | None = None


class SmokeSuiteResult(FrozenDomainModel):
    checks: tuple[SmokeCheckResult, ...]

    @property
    def passed(self) -> BooleanFlag:
        return all(check.passed for check in self.checks)


def validate_experiment_name_is_registered(experiment: CanonicalToken) -> None:
    experiment_by_name(experiment)


def validate_condition_vocabulary(plan: ExperimentPlan) -> None:
    for planned in plan.experiments:
        allowed = _CONDITION_VOCABULARY.get(planned.definition.name)
        if allowed is not None:
            for cell in planned.cells:
                if cell.condition not in allowed:
                    raise ValueError(
                        f"cell {cell.semantic_key} uses condition {cell.condition!r} "
                        f"outside the fixed {planned.definition.name} vocabulary"
                    )
        allowed_methods = _METHOD_VOCABULARY.get(planned.definition.name)
        if allowed_methods is not None:
            for cell in planned.cells:
                if cell.method not in allowed_methods:
                    raise ValueError(
                        f"cell {cell.semantic_key} uses method {cell.method!r} "
                        f"outside the fixed {planned.definition.name} vocabulary"
                    )


def validate_experiment_prerequisites_met(
    experiment: CanonicalToken,
    prerequisite_states: Mapping[CanonicalToken, ExperimentLifecycleState],
) -> None:
    definition = experiment_by_name(experiment)
    for prerequisite in definition.prerequisites:
        state = prerequisite_states.get(prerequisite)
        if state is not ExperimentLifecycleState.COMPLETED:
            raise ValueError(
                f"experiment {experiment} requires prerequisite {prerequisite} "
                f"to be Completed, found {state.value if state is not None else 'unknown'}"
            )


def validate_no_duplicate_semantic_cells(plan: ExperimentPlan) -> None:
    seen: set[CanonicalToken] = set()
    for planned in plan.experiments:
        for cell in planned.cells:
            if cell.semantic_key in seen:
                raise ValueError(f"duplicate semantic cell {cell.semantic_key}")
            seen.add(cell.semantic_key)


def validate_cell_phase_sequence(phases: Sequence[ScientificCellPhase]) -> None:
    if len(phases) != len(set(phases)):
        raise ValueError("a cell phase may appear at most once in its execution sequence")
    for phase in phases:
        if phase not in REQUIRED_CELL_PHASES:
            raise ValueError(f"unknown scientific cell phase {phase.value}")


def validate_cell_terminal_record(cell: ScientificCell, terminal_state: CellPhaseState) -> None:
    if terminal_state not in TERMINAL_CELL_STATES:
        raise ValueError(
            f"cell {cell.semantic_key} terminal state {terminal_state.value} is not terminal"
        )


def _data_invariants(config: ScientificConfig) -> tuple[SmokeCheckResult, ...]:
    role_intervals = config.datasets.primary.role_intervals
    sampling_caps = config.datasets.primary.sampling_caps_per_domain
    stream_row_count = sampling_caps.reproduction_target

    assignments = assign_stream_roles_and_sample_ids(
        dataset_file_sha256="a" * 64,
        domain_hash_token="DANMINI_DOORBELL",
        class_id=NBaiotClass.GAFGYT_COMBO,
        normalized_relative_csv_path="Danmini Doorbell/combo.csv",
        stream_row_count=stream_row_count,
        role_intervals=role_intervals,
        sampling_caps_per_domain=sampling_caps,
    )
    roles_seen = {assignment.role for assignment in assignments}
    no_target_in_anchor = (
        Role.ANCHOR_TRAIN not in roles_seen and Role.ANCHOR_VALIDATION not in roles_seen
    )

    supported_assignments = assign_stream_roles_and_sample_ids(
        dataset_file_sha256="a" * 64,
        domain_hash_token="DANMINI_DOORBELL",
        class_id=NBaiotClass.BENIGN,
        normalized_relative_csv_path="Danmini Doorbell/benign_traffic.csv",
        stream_row_count=stream_row_count,
        role_intervals=role_intervals,
        sampling_caps_per_domain=sampling_caps,
    )
    row_to_roles: dict[int, set[Role]] = {}
    for assignment in supported_assignments:
        row_to_roles.setdefault(assignment.original_row_index, set()).add(assignment.role)
    no_overlap = all(len(roles) == 1 for roles in row_to_roles.values())

    return (
        SmokeCheckResult(name="no target sample in anchor roles", passed=no_target_in_anchor),
        SmokeCheckResult(name="no cross-role sample overlap", passed=no_overlap),
    )


def _protocol_invariants(config: ScientificConfig) -> tuple[SmokeCheckResult, ...]:
    source_not_verifier = not verifier_is_eligible(_DANMINI, _DANMINI, _ENNIO)
    honest_positive = minimum_honest_positive_count(2, 1) == 1
    krum_admissible = krum_committee_is_admissible(5, 1)
    krum_three_rejected = not krum_committee_is_admissible(3, 1)

    commitment_rejected = False
    try:
        validate_commitment_exists_before_verifier_assignment(None)
    except ValueError:
        commitment_rejected = True

    eligible_pool_size = len(NBaiotDomain) - 2
    probability = diagnostic_at_least_two_byzantine_probability(eligible_pool_size, 2, 3)
    tolerance = config.validation_tolerances.random_committee_probability_absolute
    expected_probability = 1 / eligible_pool_size
    probability_matches = abs(probability - expected_probability) < tolerance

    return (
        SmokeCheckResult(name="source cannot be verifier", passed=source_not_verifier),
        SmokeCheckResult(
            name="2 positives with f_V=1 implies at least one honest positive",
            passed=honest_positive,
        ),
        SmokeCheckResult(name="Krum n=5 f=1 admissible", passed=krum_admissible),
        SmokeCheckResult(name="Krum n=3 f=1 rejected", passed=krum_three_rejected),
        SmokeCheckResult(
            name="verifier assignment before commitment throws",
            passed=commitment_rejected,
        ),
        SmokeCheckResult(
            name="random committee contamination probability 1/7 for b=2",
            passed=probability_matches,
            detail=f"observed {probability:.12f}",
        ),
    )


def _mathematical_invariants(
    fixture_config: TestFixtureConfig,
) -> tuple[SmokeCheckResult, ...]:
    sample_count = fixture_config.sign_flip_sample_count
    sign_flip = exact_sign_flip_two_sided_p_value([1.0] * sample_count)
    sign_flip_matches = sign_flip == fixture_config.sign_flip_expected_p_value
    holm = holm_adjusted_p_values(fixture_config.holm_fixture_raw_p_values)
    holm_matches = holm == fixture_config.holm_fixture_adjusted_p_values
    return (
        SmokeCheckResult(
            name="exact sign-flip test enumerates all assignments",
            passed=sign_flip_matches,
            detail=f"p={sign_flip:.10f}",
        ),
        SmokeCheckResult(name="Holm adjustment matches hand fixture", passed=holm_matches),
    )


def run_smoke_suite(
    config_path: Path = PRODUCTION_CONFIG_PATH,
    overwrite: BooleanFlag = False,
) -> SmokeSuiteResult:
    config = load_scientific_config(config_path)
    fixture_config = load_test_fixture_config(TEST_FIXTURE_CONFIG_PATH)
    checks = (
        *_data_invariants(config),
        *_protocol_invariants(config),
        *_mathematical_invariants(fixture_config),
    )
    result = SmokeSuiteResult(checks=checks)
    _persist_smoke_record(result, overwrite)
    return result


def _persist_smoke_record(result: SmokeSuiteResult, overwrite: BooleanFlag) -> None:
    record_path = smoke_record_path()
    if record_path.exists() and not overwrite:
        return
    record_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SMOKE_RECORD_SCHEMA_VERSION,
        "passed": result.passed,
        "checks": [
            {"name": check.name, "passed": check.passed, "detail": check.detail}
            for check in result.checks
        ],
    }
    record_path.write_text(json.dumps(payload, sort_keys=True, indent=2))


def render_smoke(result: SmokeSuiteResult) -> str:
    lines = ["FedSIRA smoke suite"]
    for check in result.checks:
        marker = "PASS" if check.passed else "FAIL"
        detail = f" ({check.detail})" if check.detail else ""
        lines.append(f"  [{marker}] {check.name}{detail}")
    lines.append(f"result: {'PASSED' if result.passed else 'FAILED'}")
    return "\n".join(lines)
