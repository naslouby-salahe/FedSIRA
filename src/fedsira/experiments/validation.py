from __future__ import annotations

from fedsira.analysis.statistics import exact_sign_flip_two_sided_p_value, holm_adjusted_p_values
from fedsira.artifacts.paths import smoke_record_path
from fedsira.config.loading import (
    TEST_FIXTURE_CONFIG_PATH,
    load_test_fixture_config,
)
from fedsira.config.schema import TestFixtureConfig
from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.preprocessing import assign_stream_roles_and_sample_ids
from fedsira.datasets.nbaiot.schema import NBaiotClass, NBaiotDomain
from fedsira.domain.enums import ExperimentLifecycleState, ScientificCellPhase
from fedsira.domain.records import (
    BooleanValue,
    ExperimentName,
    FrozenDomainModel,
    OverwriteExisting,
    ScenarioName,
    SchemaVersion,
    ScientificCellSemanticKey,
    TextValue,
)
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
from fedsira.runtime.state import current_application_context

SmokeCheckName = TextValue
SmokeCheckDetail = TextValue
SmokeRenderText = TextValue
SMOKE_RECORD_SCHEMA_VERSION: SchemaVersion = "fedsira|smoke_record|1"

_DANMINI = NBaiotDomain.DANMINI_DOORBELL
_ENNIO = NBaiotDomain.ENNIO_DOORBELL

REQUIRED_CELL_PHASES: frozenset[ScientificCellPhase] = frozenset(
    (
        ScientificCellPhase.PREPARE,
        ScientificCellPhase.TRAIN,
        ScientificCellPhase.SCORE,
        ScientificCellPhase.PROTOCOL_EVALUATION,
        ScientificCellPhase.METRIC_AGGREGATION,
        ScientificCellPhase.STATISTICAL_ANALYSIS,
    )
)
TERMINAL_CELL_STATES: frozenset[ExperimentLifecycleState] = frozenset(
    (
        ExperimentLifecycleState.COMPLETED,
        ExperimentLifecycleState.FAILED,
        ExperimentLifecycleState.INVALID,
    )
)


class SmokeCheckResult(FrozenDomainModel):
    name: SmokeCheckName
    passed: BooleanValue
    detail: SmokeCheckDetail | None = None


class SmokeSuiteResult(FrozenDomainModel):
    checks: tuple[SmokeCheckResult, ...]

    @property
    def passed(self) -> BooleanValue:
        return all(check.passed for check in self.checks)


class PersistedSmokeRecord(FrozenDomainModel):
    schema_version: SchemaVersion
    passed: BooleanValue
    checks: tuple[SmokeCheckResult, ...]


class ExperimentPrerequisiteState(FrozenDomainModel):
    experiment: ExperimentName
    lifecycle_state: ExperimentLifecycleState


def _epistemic_strengths(
    failure_type: EpistemicFailureType,
) -> tuple[ScenarioName, ...]:
    if failure_type is EpistemicFailureType.SHARED_LABEL_ERROR:
        return ("0.05", "0.10", "0.20")
    if failure_type in (
        EpistemicFailureType.SHARED_SPURIOUS_FEATURE,
        EpistemicFailureType.ATTACKER_INDUCED_COMMON_CONTEXT,
    ):
        return ("0.25", "0.50", "1.00")
    raise ValueError(f"unsupported epistemic failure type: {failure_type.value}")


def _allowed_conditions(experiment: ExperimentName) -> frozenset[ScenarioName] | None:
    if experiment == "Byzantine-Bound Violation":
        return frozenset(condition.value for condition in BoundCondition)
    if experiment == "Shared Epistemic-Failure Boundary":
        return frozenset(
            f"{failure_type.value}|{strength}"
            for failure_type in EpistemicFailureType
            for strength in _epistemic_strengths(failure_type)
        )
    if experiment == "Capability Under-Specification Boundary":
        return frozenset(mixture.value for mixture in RootCauseMixture)
    return None


def _allowed_methods(experiment: ExperimentName) -> frozenset[TextValue] | None:
    if experiment == "Capability Under-Specification Boundary":
        return frozenset(granularity.value for granularity in CapabilityContractGranularity)
    if experiment == "Mechanism Ablation":
        return frozenset(variant.value for variant in AblationVariant)
    return None


def validate_condition_vocabulary(plan: ExperimentPlan) -> None:
    for planned in plan.experiments:
        allowed = _allowed_conditions(planned.definition.name)
        if allowed is not None:
            for cell in planned.cells:
                if cell.condition not in allowed:
                    raise ValueError(
                        f"cell {cell.semantic_key} uses condition {cell.condition!r} "
                        f"outside the fixed {planned.definition.name} vocabulary"
                    )
        allowed_methods = _allowed_methods(planned.definition.name)
        if allowed_methods is not None:
            for cell in planned.cells:
                if cell.method not in allowed_methods:
                    raise ValueError(
                        f"cell {cell.semantic_key} uses method {cell.method!r} "
                        f"outside the fixed {planned.definition.name} vocabulary"
                    )


def validate_experiment_prerequisites_met(
    experiment: ExperimentName,
    prerequisite_states: tuple[ExperimentPrerequisiteState, ...],
) -> None:
    definition = experiment_by_name(experiment)
    for prerequisite in definition.prerequisites:
        state = next(
            (
                entry.lifecycle_state
                for entry in prerequisite_states
                if entry.experiment == prerequisite
            ),
            None,
        )
        if state is not ExperimentLifecycleState.COMPLETED:
            state_text = state.value if state is not None else "unknown"
            raise ValueError(
                f"experiment {experiment} requires prerequisite {prerequisite} "
                f"to be Completed, found {state_text}"
            )


def validate_no_duplicate_semantic_cells(plan: ExperimentPlan) -> None:
    seen: set[ScientificCellSemanticKey] = set()
    for planned in plan.experiments:
        for cell in planned.cells:
            if cell.semantic_key in seen:
                raise ValueError(f"duplicate semantic cell {cell.semantic_key}")
            seen.add(cell.semantic_key)


def validate_cell_phase_sequence(phases: tuple[ScientificCellPhase, ...]) -> None:
    if len(phases) != len(set(phases)):
        raise ValueError("a cell phase may appear at most once in its execution sequence")
    for phase in phases:
        if phase not in REQUIRED_CELL_PHASES:
            raise ValueError(f"unknown scientific cell phase {phase.value}")


def validate_cell_terminal_record(
    cell: ScientificCell,
    terminal_state: ExperimentLifecycleState,
) -> None:
    if terminal_state not in TERMINAL_CELL_STATES:
        raise ValueError(
            f"cell {cell.semantic_key} terminal state {terminal_state.value} is not terminal"
        )


def _data_invariants() -> tuple[SmokeCheckResult, ...]:
    config = current_application_context().scientific_config
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
    row_indices = tuple(assignment.original_row_index for assignment in supported_assignments)
    no_overlap = len(row_indices) == len(set(row_indices))
    return (
        SmokeCheckResult(name="no target sample in anchor roles", passed=no_target_in_anchor),
        SmokeCheckResult(name="no cross-role sample overlap", passed=no_overlap),
    )


_REQUIRED_CELL_PHASE_SEQUENCE: tuple[ScientificCellPhase, ...] = (
    ScientificCellPhase.PREPARE,
    ScientificCellPhase.TRAIN,
    ScientificCellPhase.SCORE,
    ScientificCellPhase.PROTOCOL_EVALUATION,
    ScientificCellPhase.METRIC_AGGREGATION,
    ScientificCellPhase.STATISTICAL_ANALYSIS,
)


def _protocol_invariants() -> tuple[SmokeCheckResult, ...]:
    config = current_application_context().scientific_config
    source_not_verifier = not verifier_is_eligible(_DANMINI, _DANMINI, _ENNIO)
    required_phase_sequence_valid = False
    try:
        validate_cell_phase_sequence(_REQUIRED_CELL_PHASE_SEQUENCE)
        required_phase_sequence_valid = True
    except ValueError:
        required_phase_sequence_valid = False
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
            name="canonical cell phase sequence is well-formed",
            passed=required_phase_sequence_valid,
        ),
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
    sign_flip = exact_sign_flip_two_sided_p_value((1.0,) * sample_count)
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


def run_smoke_suite(overwrite: OverwriteExisting = False) -> SmokeSuiteResult:
    fixture_config = load_test_fixture_config(TEST_FIXTURE_CONFIG_PATH)
    checks = (
        *_data_invariants(),
        *_protocol_invariants(),
        *_mathematical_invariants(fixture_config),
    )
    result = SmokeSuiteResult(checks=checks)
    _persist_smoke_record(result, overwrite)
    return result


def _persist_smoke_record(result: SmokeSuiteResult, overwrite: OverwriteExisting) -> None:
    record_path = smoke_record_path()
    if record_path.exists() and not overwrite:
        return
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record = PersistedSmokeRecord(
        schema_version=SMOKE_RECORD_SCHEMA_VERSION,
        passed=result.passed,
        checks=result.checks,
    )
    record_path.write_text(record.model_dump_json(indent=2))


def render_smoke(result: SmokeSuiteResult) -> SmokeRenderText:
    lines = ["FedSIRA smoke suite"]
    for check in result.checks:
        marker = "PASS" if check.passed else "FAIL"
        detail = f" ({check.detail})" if check.detail else ""
        lines.append(f"  [{marker}] {check.name}{detail}")
    lines.append(f"result: {'PASSED' if result.passed else 'FAILED'}")
    return "\n".join(lines)
