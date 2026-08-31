from __future__ import annotations

import inspect
from collections import OrderedDict

import numpy
import torch

from fedsira.artifacts.graph import ArtifactGraph
from fedsira.artifacts.records import ArtifactManifest
from fedsira.baselines.registry import validate_role_not_used_for_tuning
from fedsira.config.loading import (
    TEST_FIXTURE_CONFIG_PATH,
    load_test_fixture_config,
)
from fedsira.datasets.common import SUPPORTED_ROLE_ORDER, Role
from fedsira.datasets.nbaiot.preprocessing import assign_stream_roles_and_sample_ids
from fedsira.datasets.nbaiot.schema import NBaiotClass, NBaiotDomain
from fedsira.domain.enums import (
    ArtifactFamily,
    ArtifactLifecycleState,
    ClaimState,
    ExperimentLifecycleState,
    ScientificCellPhase,
    TernaryOutcome,
)
from fedsira.domain.models import AdmissionDelayDecomposition
from fedsira.domain.types import (
    AdequateFinalGateDomainCount,
    ExperimentName,
    FrozenDomainModel,
    InvariantChecksPassed,
    OverwriteExisting,
    PreparedReproductionTargetCount,
    PreparedSupportedReplayCount,
    ScenarioName,
    SchemaVersion,
    ScientificCellSemanticKey,
    TextValue,
)
from fedsira.evaluation.metrics import accuracy, compute_confusion_counts
from fedsira.evaluation.statistics import exact_sign_flip_two_sided_p_value, holm_adjusted_p_values
from fedsira.evaluation.summaries import (
    bootstrap_percentile_confidence_interval,
    quantile_type7,
)
from fedsira.experiments.collapse import resolve_all_eight_cases
from fedsira.experiments.definitions import (
    AblationVariant,
    BoundCondition,
    CapabilityContractGranularity,
    EpistemicFailureType,
    RootCauseMixture,
    experiment_by_name,
)
from fedsira.experiments.planning import ExperimentPlan, ScientificCell
from fedsira.io.paths import smoke_record_path
from fedsira.learning.aggregation import (
    ModelParameter,
    ModelState,
    WeightedModelState,
    federated_averaging,
)
from fedsira.learning.model import (
    FedSIRAClassifier,
    flatten_trainable_parameters,
    trainable_parameter_count,
)
from fedsira.learning.post_reference import (
    compute_stability_kl,
    post_reference_training_step,
    run_post_reference_training,
)
from fedsira.learning.training import build_loss_function, build_optimizer
from fedsira.protocol.admission import validate_admission_requires_final_gate
from fedsira.protocol.claim_contract import (
    SOURCE_DIRECT_PRODUCTION_WEIGHT,
    validate_source_excluded_production_weight,
)
from fedsira.protocol.reproduction import validate_commitment_exists_before_verifier_assignment
from fedsira.protocol.specification import (
    diagnostic_at_least_two_byzantine_probability,
    krum_committee_is_admissible,
    minimum_honest_positive_count,
)
from fedsira.protocol.synthesis import select_krum_update
from fedsira.protocol.verification import reproduction_row_is_certified, verifier_is_eligible
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
    passed: InvariantChecksPassed
    detail: SmokeCheckDetail | None = None


class SmokeSuiteResult(FrozenDomainModel):
    checks: tuple[SmokeCheckResult, ...]

    @property
    def passed(self) -> InvariantChecksPassed:
        return all(check.passed for check in self.checks)


class PersistedSmokeRecord(FrozenDomainModel):
    schema_version: SchemaVersion
    passed: InvariantChecksPassed
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
    verification = config.protocol.verification
    synthesis = config.protocol.synthesis
    three_row = config.baselines.three_row_coordinate_median
    diagnostic = config.protocol.diagnostic_random_verifier_profile
    honest_positive_expected = (
        verification.required_positive_reports - verification.maximum_byzantine_verifiers_per_panel
    )
    honest_positive = (
        minimum_honest_positive_count(
            verification.required_positive_reports,
            verification.maximum_byzantine_verifiers_per_panel,
        )
        == honest_positive_expected
    )
    krum_admissible = krum_committee_is_admissible(
        synthesis.committee_size, synthesis.maximum_byzantine_reproduction_rows
    )
    krum_three_rejected = not krum_committee_is_admissible(
        three_row.row_count, three_row.assumed_byzantine_rows
    )
    commitment_rejected = False
    try:
        validate_commitment_exists_before_verifier_assignment(None)
    except ValueError:
        commitment_rejected = True
    eligible_pool_size = len(NBaiotDomain) - len((_DANMINI, _ENNIO))
    probability = diagnostic_at_least_two_byzantine_probability(
        eligible_pool_size, diagnostic.byzantine_domain_count, diagnostic.panel_size
    )
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


def _mathematical_invariants() -> tuple[SmokeCheckResult, ...]:
    fixture_config = load_test_fixture_config(TEST_FIXTURE_CONFIG_PATH)
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


def _model_invariants() -> tuple[SmokeCheckResult, ...]:
    config = current_application_context().scientific_config
    fixture = load_test_fixture_config(TEST_FIXTURE_CONFIG_PATH)
    input_width = fixture.smoke_model_input_width
    output_width = fixture.smoke_model_output_width
    batch_rows = fixture.smoke_batch_row_count
    model = FedSIRAClassifier(input_width, output_width)
    features = torch.ones((batch_rows, input_width))
    labels = torch.zeros((batch_rows,), dtype=torch.long)
    logits = model(features)
    loss = build_loss_function()(logits, labels)
    loss.backward()
    finite = bool(torch.isfinite(logits).all()) and bool(torch.isfinite(loss))
    first = ModelState(
        parameters=(
            ModelParameter(
                name="w",
                value=torch.tensor(fixture.smoke_fedavg_client_a_weights),
            ),
        )
    )
    second = ModelState(
        parameters=(
            ModelParameter(
                name="w",
                value=torch.tensor(fixture.smoke_fedavg_client_b_weights),
            ),
        )
    )
    count_a = fixture.smoke_fedavg_client_a_example_count
    count_b = fixture.smoke_fedavg_client_b_example_count
    averaged = federated_averaging(
        (
            WeightedModelState(state=first, example_count=count_a),
            WeightedModelState(state=second, example_count=count_b),
        )
    )
    total = count_a + count_b
    expected = torch.tensor(
        tuple(
            (left * count_a + right * count_b) / total
            for left, right in zip(
                fixture.smoke_fedavg_client_a_weights,
                fixture.smoke_fedavg_client_b_weights,
                strict=True,
            )
        )
    )
    fedavg_matches = bool(torch.allclose(averaged.parameters[0].value, expected))
    model.eval()
    restored = FedSIRAClassifier(input_width, output_width)
    restored.load_state_dict(model.state_dict())
    restored.eval()
    with torch.no_grad():
        original_logits = model(features)
        restored_logits = restored(features)
        delta = (restored_logits - original_logits).abs().max()
    restore_matches = float(delta) <= config.runtime.same_environment_absolute_metric_tolerance
    report_test_rejected = False
    try:
        validate_role_not_used_for_tuning(Role.REPORT_TEST)
    except ValueError:
        report_test_rejected = True
    anchor = FedSIRAClassifier(input_width, output_width)
    current = FedSIRAClassifier(input_width, output_width)
    current.load_state_dict(anchor.state_dict())
    optimizer = build_optimizer(
        current, config.model.optimizer.post_reference_learning_rate, config.model.optimizer
    )
    unsupported = torch.zeros((batch_rows,), dtype=torch.bool)
    post_reference_training_step(
        anchor,
        current,
        optimizer,
        build_loss_function(),
        config.model.training,
        config.model.post_reference,
        features,
        labels,
        unsupported,
        flatten_trainable_parameters(anchor).detach(),
        trainable_parameter_count(current),
    )
    temperature = config.model.post_reference.stability_kl_temperature
    identical = torch.ones((batch_rows, output_width))
    kl_zero = float(compute_stability_kl(identical, identical, temperature)) >= 0.0
    constructor_has_no_source = not any(
        "source" in name for name in inspect.signature(run_post_reference_training).parameters
    )
    return (
        SmokeCheckResult(name="one-batch forward/backward finite", passed=finite),
        SmokeCheckResult(
            name="one-round FedAvg matches weighted average fixture",
            passed=fedavg_matches,
        ),
        SmokeCheckResult(name="checkpoint restore reproduces predictions", passed=restore_matches),
        SmokeCheckResult(
            name="report-test loader cannot be requested by training",
            passed=report_test_rejected,
        ),
        SmokeCheckResult(
            name="post-reference minibatch with no supported rows keeps KL defined",
            passed=kl_zero,
        ),
        SmokeCheckResult(
            name="honest reproduction constructor has no source-artifact parameter",
            passed=constructor_has_no_source,
        ),
    )


def _extended_protocol_invariants() -> tuple[SmokeCheckResult, ...]:
    config = current_application_context().scientific_config
    fixture = load_test_fixture_config(TEST_FIXTURE_CONFIG_PATH)
    source_weight_zero = True
    try:
        validate_source_excluded_production_weight(SOURCE_DIRECT_PRODUCTION_WEIGHT)
        validate_source_excluded_production_weight(fixture.smoke_nonzero_production_weight)
        source_weight_zero = False
    except ValueError:
        source_weight_zero = True
    verification = config.protocol.verification
    abstain_panel = tuple(TernaryOutcome.ABSTAIN for _ in range(verification.panel_size))
    abstain_not_positive = not reproduction_row_is_certified(
        abstain_panel, verification.panel_size, verification.required_positive_reports
    )
    five_row_required = False
    try:
        select_krum_update((), config.protocol.synthesis.maximum_byzantine_reproduction_rows)
    except ValueError:
        five_row_required = True
    admission_requires_gate = False
    try:
        validate_admission_requires_final_gate(ClaimState.ADMITTED, False)
    except ValueError:
        admission_requires_gate = True
    eight_cases = resolve_all_eight_cases()
    eight_resolved = len(eight_cases) == 2**3
    disjoint_roles = (
        frozenset(SUPPORTED_ROLE_ORDER).isdisjoint(
            frozenset((Role.SOURCE_PROPOSAL, Role.REPRODUCTION))
        )
        and Role.SOURCE_PROPOSAL not in SUPPORTED_ROLE_ORDER
    )
    return (
        SmokeCheckResult(
            name="source direct production weight cannot become nonzero",
            passed=source_weight_zero,
        ),
        SmokeCheckResult(
            name="Abstain cannot be cast to boolean vote",
            passed=abstain_not_positive,
        ),
        SmokeCheckResult(
            name="fewer than five certified rows cannot call primary Krum synthesis",
            passed=five_row_required,
        ),
        SmokeCheckResult(
            name="final admission without final-gate artifact is impossible",
            passed=admission_requires_gate,
        ),
        SmokeCheckResult(
            name="all eight collapse combinations resolve",
            passed=eight_resolved,
        ),
        SmokeCheckResult(
            name="source/reproducer/verifier/final/report roles are disjoint",
            passed=disjoint_roles,
        ),
    )


def _extended_mathematical_invariants() -> tuple[SmokeCheckResult, ...]:
    config = current_application_context().scientific_config
    fixture = load_test_fixture_config(TEST_FIXTURE_CONFIG_PATH)
    diagnostic = config.protocol.diagnostic_random_verifier_profile
    pool = len(NBaiotDomain) - len((_DANMINI, _ENNIO))
    zero = diagnostic_at_least_two_byzantine_probability(pool, 0, diagnostic.panel_size)
    one = diagnostic_at_least_two_byzantine_probability(pool, 1, diagnostic.panel_size)
    tolerance = config.validation_tolerances.random_committee_probability_absolute
    delay = AdmissionDelayDecomposition(
        logical_information_arrival_cycles=1,
        assignment_seconds=fixture.smoke_delay_assignment_seconds,
        reproduce_seconds=fixture.smoke_delay_reproduce_seconds,
        verify_seconds=fixture.smoke_delay_verify_seconds,
        synthesize_seconds=fixture.smoke_delay_synthesize_seconds,
    )
    delay_matches = (
        abs(
            delay.post_evidence_wall_clock_seconds
            - (
                delay.assignment_seconds
                + delay.reproduce_seconds
                + delay.verify_seconds
                + delay.synthesize_seconds
            )
        )
        < config.validation_tolerances.delay_component_sum_seconds_absolute
    )
    quantiles = quantile_type7(fixture.smoke_quantile_values, fixture.smoke_quantile_probability)
    numpy_matches = quantiles == float(
        numpy.quantile(
            fixture.smoke_quantile_values, fixture.smoke_quantile_probability, method="linear"
        )
    )
    sample = numpy.array(fixture.smoke_sample_sd_values)
    sd_matches = float(sample.std(ddof=1)) == float(numpy.std(sample, ddof=1))
    confusion = compute_confusion_counts(
        fixture.smoke_confusion_true_labels,
        fixture.smoke_confusion_predicted_labels,
        fixture.smoke_confusion_class_token,
    )
    confusion_matches = (
        confusion.true_positive == fixture.smoke_confusion_true_positive
        and confusion.false_positive == fixture.smoke_confusion_false_positive
        and confusion.false_negative == fixture.smoke_confusion_false_negative
        and confusion.true_negative == fixture.smoke_confusion_true_negative
    )
    zero_den = accuracy(OrderedDict(), 0)
    zero_is_na = zero_den.value is None and zero_den.denominator == 0
    bootstrap_config = config.metrics_and_statistics.bootstrap
    analysis_seed = config.seeds_and_determinism.analysis_seed
    first_interval = bootstrap_percentile_confidence_interval(
        fixture.smoke_bootstrap_values, bootstrap_config, analysis_seed
    )
    second_interval = bootstrap_percentile_confidence_interval(
        fixture.smoke_bootstrap_values, bootstrap_config, analysis_seed
    )
    bootstrap_deterministic = first_interval == second_interval
    return (
        SmokeCheckResult(
            name="random-committee exact probability is 0 for compromised-verifier counts 0/1",
            passed=abs(zero) < tolerance and abs(one) < tolerance,
        ),
        SmokeCheckResult(
            name="post-evidence wall-clock components sum to T_post",
            passed=delay_matches,
        ),
        SmokeCheckResult(name="type-7 quantiles match NumPy linear fixtures", passed=numpy_matches),
        SmokeCheckResult(name="sample SD uses ddof=1", passed=sd_matches),
        SmokeCheckResult(
            name="confusion-derived metrics match hand calculations",
            passed=confusion_matches,
        ),
        SmokeCheckResult(name="zero denominators return NA plus reason", passed=zero_is_na),
        SmokeCheckResult(
            name="bootstrap draws are deterministic under the analysis seed",
            passed=bootstrap_deterministic,
        ),
    )


def _artifact_invariants() -> tuple[SmokeCheckResult, ...]:
    graph = ArtifactGraph()
    parent = ArtifactManifest(
        family=ArtifactFamily.SCALER,
        identity="a" * 64,
        checksum="b" * 64,
        lifecycle_state=ArtifactLifecycleState.COMPLETE,
        upstream_identities=(),
    )
    child = ArtifactManifest(
        family=ArtifactFamily.SCALER,
        identity="c" * 64,
        checksum="d" * 64,
        lifecycle_state=ArtifactLifecycleState.COMPLETE,
        upstream_identities=(parent.identity,),
    )
    graph.register(parent)
    graph.register(child)
    staled = graph.mark_stale_descendants(parent.identity)
    stale_ok = staled == (child.identity,) and not graph.is_active(child.identity)
    return (
        SmokeCheckResult(
            name="changing one parent identity marks transitive descendants stale",
            passed=stale_ok,
        ),
    )


def run_data_and_domain_evidence_validation(
    reproduction_target_count: PreparedReproductionTargetCount,
    reproduction_supported_count: PreparedSupportedReplayCount,
    final_gate_adequate_domain_count: AdequateFinalGateDomainCount,
) -> None:
    config = current_application_context().scientific_config
    failed = tuple(check.name for check in _data_invariants() if not check.passed)
    if failed:
        raise ValueError(f"data and domain evidence validation failed: {', '.join(failed)}")
    minima = config.capability_claim.evidence_minima
    if reproduction_target_count < minima.reproduction_target_examples:
        raise ValueError(
            "reproduction-target evidence is below the configured minimum "
            f"{minima.reproduction_target_examples}"
        )
    if reproduction_supported_count < minima.reproduction_supported_control_examples:
        raise ValueError(
            "reproduction supported-control evidence is below the configured minimum "
            f"{minima.reproduction_supported_control_examples}"
        )
    required_final_gate_domains = config.protocol.final_gate.minimum_adequate_non_source_domains
    if final_gate_adequate_domain_count < required_final_gate_domains:
        raise ValueError(
            "final-gate adequate non-source domain count is below the configured minimum "
            f"{required_final_gate_domains}"
        )


def run_protocol_invariant_validation() -> None:
    result = run_smoke_suite()
    if not result.passed:
        failed = tuple(check.name for check in result.checks if not check.passed)
        raise ValueError(f"protocol invariant validation failed: {', '.join(failed)}")


def run_smoke_suite(overwrite: OverwriteExisting = False) -> SmokeSuiteResult:
    checks = (
        *_data_invariants(),
        *_model_invariants(),
        *_protocol_invariants(),
        *_extended_protocol_invariants(),
        *_mathematical_invariants(),
        *_extended_mathematical_invariants(),
        *_artifact_invariants(),
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
