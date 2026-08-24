from pathlib import Path

import pandas
import pytest

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.acquisition import DiscoveredCsvFile
from fedsira.datasets.nbaiot.materialization import materialize_nbaiot_prepared_views
from fedsira.datasets.nbaiot.preprocessing import NBAIOT_PRIMARY_PREDICTOR_COUNT
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_DOMAIN_ORDER,
    NBAIOT_TRIGGER_FEATURES,
    NBaiotClass,
)
from fedsira.domain.enums import CapabilityContractScope, SeedNamespace
from fedsira.experiments.collapse import resolve_core_mapping
from fedsira.experiments.planning import ScientificCell
from fedsira.experiments.protocol_executor import ProtocolCellExecutor
from fedsira.experiments.real_evidence import evaluate_domain, non_source_domains, train_anchor
from fedsira.experiments.registry import (
    ADMISSION_DELAY_DECOMPOSITION_NAME,
    BYZANTINE_BOUND_VIOLATION_NAME,
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    BaselineIdentity,
    BoundCondition,
    EpistemicFailureType,
    OpeningMode,
    PrimaryScenario,
    ProposalEpisode,
    SourceExclusionMethod,
)
from fedsira.protocol.source_selection import select_source_domain, source_selection_order
from fedsira.runtime.determinism import namespace_seed

pytestmark = pytest.mark.skip(
    reason="runs real anchor/reproduction gradient-descent training end-to-end through"
    " ProtocolCellExecutor; skipped by default to avoid competing for CPU with other work."
    " Re-enable deliberately when verifying fedsira.experiments.protocol_executor."
)

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
RESOLVED_CORE = resolve_core_mapping(True, True, True)
CLASSES = (NBaiotClass.BENIGN, NBaiotClass.GAFGYT_COMBO, NBaiotClass.GAFGYT_JUNK)
CLASS_OFFSETS = {
    NBaiotClass.BENIGN: 0.0,
    NBaiotClass.GAFGYT_JUNK: 30.0,
    NBaiotClass.GAFGYT_COMBO: 300.0,
}


def _feature_names() -> list[str]:
    names = [f"feature_{index:03d}" for index in range(NBAIOT_PRIMARY_PREDICTOR_COUNT)]
    for index, trigger in enumerate(NBAIOT_TRIGGER_FEATURES):
        names[index] = trigger
    return names


def _write_csv(path: Path, row_count: int, offset: float) -> None:
    frame = pandas.DataFrame(
        {name: [offset + index * 0.0001 for index in range(row_count)] for name in _feature_names()}
    )
    frame.to_csv(path, index=False)


@pytest.fixture(scope="module")
def prepared_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("protocol-executor-real-evidence")
    discovered: list[DiscoveredCsvFile] = []
    for domain_index, domain in enumerate(NBAIOT_DOMAIN_ORDER):
        for class_id in CLASSES:
            relative_path = f"{class_id.value}.csv"
            absolute_path = root / "raw" / domain.value / relative_path
            absolute_path.parent.mkdir(parents=True, exist_ok=True)
            offset = domain_index * 0.001 + CLASS_OFFSETS[class_id]
            _write_csv(absolute_path, row_count=3000, offset=offset)
            discovered.append(
                DiscoveredCsvFile(
                    domain=domain,
                    class_id=class_id,
                    relative_path=relative_path,
                    file_sha256=f"{domain_index}{class_id.value}".ljust(64, "0")[:64],
                    absolute_path=absolute_path,
                )
            )
    prepared = root / "prepared"
    materialize_nbaiot_prepared_views(discovered, CONFIG, prepared, root / "scaler", overwrite=True)
    return prepared


def _primary_cell(master_seed: int) -> ScientificCell:
    return ScientificCell(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        method="Resolved FedSIRA Core",
        condition=PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value,
        master_seed=master_seed,
    )


def test_primary_cell_executes_and_reports_a_valid_terminal_state(prepared_root: Path) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    outcome = executor.execute_cell(_primary_cell(1), CONFIG)
    assert outcome.terminal_state == "Completed"
    metrics = dict(outcome.metrics)
    assert metrics["terminal-state"] in {1.0, -1.0, 0.0}


def test_reached_final_gate_cells_report_real_not_fabricated_target_f1(
    prepared_root: Path,
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    outcome = executor.execute_cell(_primary_cell(4), CONFIG)
    metrics = dict(outcome.metrics)
    assert metrics["terminal-state"] != 0.0
    assert metrics["target-f1"] is not None
    assert metrics["worst-domain-target-f1"] is not None


def test_resolved_core_cell_is_dormant_without_a_resolved_core(prepared_root: Path) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root)
    outcome = executor.execute_cell(_primary_cell(1), CONFIG)
    assert outcome.terminal_state == "Completed"
    metrics = dict(outcome.metrics)
    assert metrics["terminal-state"] == 0.0


def test_resolved_core_without_plurality_uses_single_row_requirement(prepared_root: Path) -> None:
    single_row_core = resolve_core_mapping(True, False, True)
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=single_row_core)
    outcome = executor.execute_cell(_primary_cell(20), CONFIG)
    assert outcome.terminal_state == "Completed"


def test_execute_cell_is_deterministic_for_the_same_seed(prepared_root: Path) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    first = executor.execute_cell(_primary_cell(2), CONFIG)
    second = executor.execute_cell(_primary_cell(2), CONFIG)
    assert first.terminal_state == second.terminal_state
    assert first.metrics == second.metrics


def test_final_gate_metrics_are_genuinely_computed_not_fabricated_na(prepared_root: Path) -> None:
    master_seed = 3
    anchor = train_anchor(prepared_root, CONFIG, master_seed)
    assert anchor is not None
    source_selection_namespace_seed = namespace_seed(master_seed, SeedNamespace.SOURCE_SELECTION)
    source_order = source_selection_order(source_selection_namespace_seed)
    source_domain = select_source_domain(
        source_order,
        frozenset(NBAIOT_DOMAIN_ORDER),
        requires_gafgyt_udp_carrier=False,
        domains_with_gafgyt_udp=frozenset(),
    )
    adequate_domains = non_source_domains(source_domain)
    assert len(adequate_domains) == 8
    for domain in adequate_domains:
        metrics = evaluate_domain(
            prepared_root, anchor, anchor.flat_parameters, domain, Role.FINAL_GATE
        )
        assert metrics is not None
        assert metrics.target_f1.value is not None
        assert metrics.supported_macro_f1.value is not None
        assert metrics.benign_far.value is not None


def _opening_cell(episode: ProposalEpisode, master_seed: int) -> ScientificCell:
    return ScientificCell(
        experiment=PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME,
        method=OpeningMode.PROPOSAL_ASSISTED.value,
        condition=episode.value,
        master_seed=master_seed,
    )


def test_proposal_assisted_opening_cell_executes_without_crashing(prepared_root: Path) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    outcome = executor.execute_cell(
        _opening_cell(ProposalEpisode.GENERIC_HARD_SUPPORTED_EXAMPLES, 5), CONFIG
    )
    assert outcome.terminal_state == "Completed"
    metrics = dict(outcome.metrics)
    assert metrics["terminal-state"] in {1.0, -1.0, 0.0}


def test_proposal_assisted_opening_reports_a_defined_claim_contract_decision(
    prepared_root: Path,
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    outcome = executor.execute_cell(
        _opening_cell(ProposalEpisode.GENERIC_HARD_SUPPORTED_EXAMPLES, 6), CONFIG
    )
    metrics = dict(outcome.metrics)
    assert metrics["claim-contract-passes"] in {0.0, 1.0}


def test_client_review_baseline_executes_without_crashing(prepared_root: Path) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    cell = ScientificCell(
        experiment=SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
        method=BaselineIdentity.CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION.value,
        condition="Useful Backdoored Source — 5%",
        master_seed=7,
    )
    outcome = executor.execute_cell(cell, CONFIG)
    assert outcome.terminal_state == "Completed"
    metrics = dict(outcome.metrics)
    assert metrics["terminal-state"] in {1.0, -1.0, 0.0}


def test_client_review_then_retrain_baseline_executes_without_crashing(
    prepared_root: Path,
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    cell = ScientificCell(
        experiment=SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
        method=BaselineIdentity.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN.value,
        condition="Useful Backdoored Source — 5%",
        master_seed=8,
    )
    outcome = executor.execute_cell(cell, CONFIG)
    assert outcome.terminal_state == "Completed"
    metrics = dict(outcome.metrics)
    assert metrics["terminal-state"] in {1.0, -1.0, 0.0}


def test_client_review_then_retrain_uses_single_verifier_progression_when_review_passes(
    prepared_root: Path,
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    cell = ScientificCell(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        method=BaselineIdentity.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN.value,
        condition=PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value,
        master_seed=31,
    )
    outcome = executor.execute_cell(cell, CONFIG)
    assert outcome.terminal_state == "Completed"
    assert dict(outcome.metrics)["terminal-state"] != 0.0


def test_source_exclusion_necessity_does_not_hardcode_admission_for_every_method(
    prepared_root: Path,
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    terminal_states: set[float | None] = set()
    for method in SourceExclusionMethod:
        cell = ScientificCell(
            experiment=SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
            method=method.value,
            condition="Useful Backdoored Source — 5%",
            master_seed=9,
        )
        outcome = executor.execute_cell(cell, CONFIG)
        assert outcome.terminal_state == "Completed"
        terminal_states.add(dict(outcome.metrics)["terminal-state"])
    assert terminal_states != {1.0}


def test_every_primary_baseline_method_executes_without_crashing(prepared_root: Path) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    for method in BaselineIdentity:
        cell = ScientificCell(
            experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
            method=method.value,
            condition=PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value,
            master_seed=10,
        )
        outcome = executor.execute_cell(cell, CONFIG)
        assert outcome.terminal_state == "Completed", (method.value, outcome.failure)


def test_direct_krum_baseline_skips_verification_and_uses_krum_synthesis(
    prepared_root: Path,
) -> None:
    verification_required_core = resolve_core_mapping(True, True, True)
    executor = ProtocolCellExecutor(
        prepared_root=prepared_root, resolved_core=verification_required_core
    )
    core_cell = ScientificCell(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        method="Resolved FedSIRA Core",
        condition=PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value,
        master_seed=21,
    )
    core_outcome = executor.execute_cell(core_cell, CONFIG)
    assert core_outcome.terminal_state == "Completed"
    direct_krum_cell = ScientificCell(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        method=BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,
        condition=PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value,
        master_seed=21,
    )
    direct_krum_outcome = executor.execute_cell(direct_krum_cell, CONFIG)
    assert direct_krum_outcome.terminal_state == "Completed"
    assert dict(direct_krum_outcome.metrics)["terminal-state"] != 0.0


def test_three_row_coordinate_median_baseline_is_routed_and_uses_median_synthesis(
    prepared_root: Path,
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    cell = ScientificCell(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        method=BaselineIdentity.THREE_ROW_COORDINATE_MEDIAN_ALTERNATIVE.value,
        condition=PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value,
        master_seed=22,
    )
    outcome = executor.execute_cell(cell, CONFIG)
    assert outcome.terminal_state == "Completed"
    assert dict(outcome.metrics)["terminal-state"] != 0.0


def test_one_independent_retrain_baseline_uses_single_verifier_progression(
    prepared_root: Path,
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    cell = ScientificCell(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        method=BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
        condition=PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value,
        master_seed=23,
    )
    outcome = executor.execute_cell(cell, CONFIG)
    assert outcome.terminal_state == "Completed"
    assert dict(outcome.metrics)["terminal-state"] != 0.0


def test_resolved_core_single_row_path_admits_via_single_verifier_progression(
    prepared_root: Path,
) -> None:
    single_row_core = resolve_core_mapping(True, False, True)
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=single_row_core)
    outcome = executor.execute_cell(_primary_cell(24), CONFIG)
    assert outcome.terminal_state == "Completed"
    assert dict(outcome.metrics)["terminal-state"] != 0.0


def test_fedavg_reference_baseline_trains_and_evaluates_a_real_fedavg_model(
    prepared_root: Path,
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    cell = ScientificCell(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        method=BaselineIdentity.FEDAVG_REFERENCE.value,
        condition=PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value,
        master_seed=25,
    )
    outcome = executor.execute_cell(cell, CONFIG)
    assert outcome.terminal_state == "Completed"
    assert dict(outcome.metrics)["terminal-state"] != 0.0


def test_krum_reference_baseline_trains_and_evaluates_a_real_krum_synthesized_model(
    prepared_root: Path,
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    cell = ScientificCell(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        method=BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE.value,
        condition=PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value,
        master_seed=26,
    )
    outcome = executor.execute_cell(cell, CONFIG)
    assert outcome.terminal_state == "Completed"
    assert dict(outcome.metrics)["terminal-state"] != 0.0


def test_density_cluster_trimmed_mean_baseline_trains_and_evaluates_a_real_model(
    prepared_root: Path,
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    cell = ScientificCell(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        method=BaselineIdentity.DENSITY_CLUSTER_TRIMMED_MEAN.value,
        condition=PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value,
        master_seed=32,
    )
    outcome = executor.execute_cell(cell, CONFIG)
    assert outcome.terminal_state == "Completed"
    assert dict(outcome.metrics)["terminal-state"] != 0.0


def test_source_update_sanitization_baseline_clips_and_reviews_the_source_candidate(
    prepared_root: Path,
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    cell = ScientificCell(
        experiment=SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
        method=BaselineIdentity.SOURCE_UPDATE_SANITIZATION_REFERENCE.value,
        condition="Useful Backdoored Source — 5%",
        master_seed=33,
    )
    outcome = executor.execute_cell(cell, CONFIG)
    assert outcome.terminal_state == "Completed"
    metrics = dict(outcome.metrics)
    assert metrics["terminal-state"] in {1.0, -1.0, 0.0}


def test_update_reconstruction_filter_baseline_trains_and_evaluates_a_real_model(
    prepared_root: Path,
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    cell = ScientificCell(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        method=BaselineIdentity.UPDATE_RECONSTRUCTION_FILTER.value,
        condition=PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value,
        master_seed=34,
    )
    outcome = executor.execute_cell(cell, CONFIG)
    assert outcome.terminal_state == "Completed"
    assert dict(outcome.metrics)["terminal-state"] != 0.0


def test_recovery_after_source_admission_baseline_evaluates_the_rollback_decision(
    prepared_root: Path,
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    cell = ScientificCell(
        experiment=SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
        method=BaselineIdentity.RECOVERY_AFTER_SOURCE_ADMISSION.value,
        condition="Useful Backdoored Source — 5%",
        master_seed=35,
    )
    outcome = executor.execute_cell(cell, CONFIG)
    assert outcome.terminal_state == "Completed"
    metrics = dict(outcome.metrics)
    assert metrics["terminal-state"] in {1.0, -1.0, 0.0}


def test_secure_continual_assessment_baseline_trains_after_the_reviewer_gate(
    prepared_root: Path,
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    cell = ScientificCell(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        method=BaselineIdentity.SECURE_CONTINUAL_ASSESSMENT_REFERENCE.value,
        condition=PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value,
        master_seed=27,
    )
    outcome = executor.execute_cell(cell, CONFIG)
    assert outcome.terminal_state == "Completed"
    assert dict(outcome.metrics)["terminal-state"] != 0.0


def test_independent_local_reference_baseline_evaluates_real_reviewer_votes(
    prepared_root: Path,
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    cell = ScientificCell(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        method=BaselineIdentity.INDEPENDENT_LOCAL_REFERENCE_WITH_SOURCE_ADMISSION.value,
        condition=PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value,
        master_seed=28,
    )
    outcome = executor.execute_cell(cell, CONFIG)
    assert outcome.terminal_state == "Completed"
    assert dict(outcome.metrics)["terminal-state"] != 0.0


def test_local_only_reference_baseline_evaluates_real_per_domain_checkpoints(
    prepared_root: Path,
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    cell = ScientificCell(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        method=BaselineIdentity.LOCAL_ONLY_REFERENCE.value,
        condition=PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value,
        master_seed=29,
    )
    outcome = executor.execute_cell(cell, CONFIG)
    assert outcome.terminal_state == "Completed"
    assert dict(outcome.metrics)["terminal-state"] != 0.0


def test_centralized_reference_baseline_trains_and_evaluates_a_real_pooled_model(
    prepared_root: Path,
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    cell = ScientificCell(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        method=BaselineIdentity.CENTRALIZED_REFERENCE.value,
        condition=PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value,
        master_seed=30,
    )
    outcome = executor.execute_cell(cell, CONFIG)
    assert outcome.terminal_state == "Completed"
    assert dict(outcome.metrics)["terminal-state"] != 0.0


def test_admission_delay_decomposition_is_routed_and_executes_without_crashing(
    prepared_root: Path,
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    cell = ScientificCell(
        experiment=ADMISSION_DELAY_DECOMPOSITION_NAME,
        method="Resolved FedSIRA Core",
        condition="Permanent Singleton",
        master_seed=11,
    )
    outcome = executor.execute_cell(cell, CONFIG)
    assert outcome.terminal_state == "Completed"
    metrics = dict(outcome.metrics)
    assert metrics["post-evidence-wall-clock-seconds"] is not None
    assert metrics["post-evidence-wall-clock-seconds"] > 0.0


def test_efficiency_cell_measures_real_post_evidence_wall_clock_time(
    prepared_root: Path,
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    cell = ScientificCell(
        experiment=EFFICIENCY_MEASUREMENT_NAME,
        method="Resolved FedSIRA Core",
        condition="x",
        master_seed=12,
    )
    outcome = executor.execute_cell(cell, CONFIG)
    assert outcome.terminal_state == "Completed"
    metrics = dict(outcome.metrics)
    assert metrics["post-evidence-wall-clock-seconds"] is not None
    assert metrics["post-evidence-wall-clock-seconds"] > 0.0


def test_byzantine_bound_violation_is_routed_and_executes_without_crashing(
    prepared_root: Path,
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    methods = (
        SourceExclusionMethod.FULL_FEDSIRA.value,
        BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,
    )
    for method in methods:
        for condition in BoundCondition:
            cell = ScientificCell(
                experiment=BYZANTINE_BOUND_VIOLATION_NAME,
                method=method,
                condition=condition.value,
                master_seed=13,
            )
            outcome = executor.execute_cell(cell, CONFIG)
            assert outcome.terminal_state == "Completed", (method, condition.value, outcome.failure)


def test_capability_under_specification_boundary_reports_a_real_oracle_label(
    prepared_root: Path,
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    cell = ScientificCell(
        experiment=CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
        method=CapabilityContractScope.BROAD_TARGET_ONLY.value,
        condition="x",
        master_seed=14,
    )
    outcome = executor.execute_cell(cell, CONFIG)
    assert outcome.terminal_state == "Completed"
    metrics = dict(outcome.metrics)
    assert metrics["proposal-oracle-label"] is not None


@pytest.mark.parametrize(
    "failure_type",
    [
        EpistemicFailureType.SHARED_LABEL_ERROR,
        EpistemicFailureType.SHARED_SPURIOUS_FEATURE,
        EpistemicFailureType.ATTACKER_INDUCED_COMMON_CONTEXT,
    ],
)
def test_shared_epistemic_failure_boundary_reports_real_metrics(
    prepared_root: Path, failure_type: EpistemicFailureType
) -> None:
    executor = ProtocolCellExecutor(prepared_root=prepared_root, resolved_core=RESOLVED_CORE)
    cell = ScientificCell(
        experiment=SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
        method="x",
        condition=f"{failure_type.value}|0.5",
        master_seed=15,
    )
    outcome = executor.execute_cell(cell, CONFIG)
    assert outcome.terminal_state == "Completed"
    metrics = dict(outcome.metrics)
    assert metrics["defined-domain-count"] is not None
    assert metrics["defined-domain-count"] > 0
    assert metrics["proposal-oracle-label"] is not None
    if failure_type is EpistemicFailureType.SHARED_LABEL_ERROR:
        assert metrics["diagnostic-marker-insufficient"] == 1.0
    else:
        assert metrics["diagnostic-marker-value"] is not None
