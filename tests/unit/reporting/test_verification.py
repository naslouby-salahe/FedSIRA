from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER
from fedsira.domain.enums import (
    AdmissionState,
    BoundCondition,
    ComparisonMetric,
    CoreMethodIdentity,
    DescriptiveScientificMetric,
    EvidenceArrivalSchedule,
    ExperimentLifecycleState,
    ExperimentName,
)
from fedsira.experiments.definitions import (
    BYZANTINE_BOUND_VIOLATION_NAME,
    EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
)
from fedsira.experiments.engine import (
    EXECUTION_RECORD_SCHEMA_VERSION,
    AdmissionStateObservation,
    PersistedExecutionRecord,
)
from fedsira.experiments.observations import measurement_cycles
from fedsira.experiments.planning import build_plan
from fedsira.protocol.rules import compute_t_evidence
from fedsira.reporting.verification import (
    CompletenessVerificationResult,
    ExperimentLifecycleRecord,
    ExperimentTerminalCount,
    verify_artifact_manifest_dependencies,
    verify_byzantine_operating_region,
    verify_experiments_completed,
    verify_experiments_reached_terminal_state,
    verify_planned_cell_count_satisfied,
    verify_safe_dormancy,
)
from fedsira.runtime import current_application_context


def test_execution_evidence_verification_requires_each_planned_cell() -> None:
    plan = build_plan()
    counts = tuple(
        ExperimentTerminalCount(experiment=item.definition.name, count=len(item.cells))
        for item in plan.experiments
    )
    assert verify_planned_cell_count_satisfied(plan, counts).passed
    assert not verify_planned_cell_count_satisfied(plan, ()).passed


def test_execution_evidence_verification_requires_complete_terminal_experiments() -> None:
    states = (
        ExperimentLifecycleRecord(
            experiment=ExperimentName.DATA_AND_DOMAIN_EVIDENCE_VALIDATION,
            state=ExperimentLifecycleState.COMPLETED,
        ),
        ExperimentLifecycleRecord(
            experiment=ExperimentName.PROTOCOL_INVARIANT_VALIDATION,
            state=ExperimentLifecycleState.RUNNING,
        ),
    )
    assert verify_experiments_completed(
        states, (ExperimentName.DATA_AND_DOMAIN_EVIDENCE_VALIDATION,)
    ).passed
    assert not verify_experiments_reached_terminal_state(
        states, (ExperimentName.PROTOCOL_INVARIANT_VALIDATION,)
    ).passed


def test_invalid_artifact_evidence_blocks_completion() -> None:
    assert verify_artifact_manifest_dependencies(()).passed
    assert not verify_artifact_manifest_dependencies(("a" * 64,)).passed
    assert CompletenessVerificationResult(passed=True, failures=()).passed


def test_safe_dormancy_blocks_when_any_registered_cell_evidence_is_missing() -> None:
    planned = build_plan().experiment(EVIDENCE_SCARCITY_AND_DORMANCY_NAME)

    result = verify_safe_dormancy(planned, ())

    assert not result.passed
    assert len(result.failures) == len(planned.cells)
    assert all("expected exactly one current" in failure for failure in result.failures)


def test_safe_dormancy_checks_trajectory_against_computed_evidence_arrival() -> None:
    planned = build_plan().experiment(EVIDENCE_SCARCITY_AND_DORMANCY_NAME)
    config = current_application_context().scientific_config
    cycles = measurement_cycles(config.protocol.resource_horizon)
    target_capable_order = tuple(NBAIOT_DOMAIN_ORDER[1:])
    records: list[PersistedExecutionRecord] = []
    for cell in planned.cells:
        schedule = EvidenceArrivalSchedule(cell.condition)
        t_evidence = compute_t_evidence(
            schedule,
            target_capable_order,
            cycles,
            config.protocol.synthesis.committee_size,
            config.protocol.final_gate.minimum_adequate_non_source_domains,
        )
        trajectory = (
            (AdmissionStateObservation(cycle=t_evidence, state=AdmissionState.ADMITTED),)
            if schedule
            in (
                EvidenceArrivalSchedule.GRADUAL_TO_QUORUM,
                EvidenceArrivalSchedule.IMMEDIATE_QUORUM,
            )
            and t_evidence is not None
            else (AdmissionStateObservation(cycle=0, state=AdmissionState.DORMANT),)
        )
        records.append(
            PersistedExecutionRecord(
                schema_version=EXECUTION_RECORD_SCHEMA_VERSION,
                semantic_key=cell.semantic_key,
                experiment=cell.experiment,
                method=cell.method,
                condition=cell.condition,
                master_seed=cell.master_seed,
                terminal_state=ExperimentLifecycleState.COMPLETED,
                metrics=((DescriptiveScientificMetric.PERMANENT_SINGLETON_ADMISSION, 0.0),),
                state_trajectory=trajectory,
                failure=None,
            )
        )

    result = verify_safe_dormancy(planned, tuple(records))

    assert result.passed
    duplicate_plan = planned.model_copy(update={"cells": (*planned.cells, planned.cells[0])})
    assert not verify_safe_dormancy(duplicate_plan, tuple(records)).passed
    gradual_cell = next(
        cell
        for cell in planned.cells
        if cell.condition == EvidenceArrivalSchedule.GRADUAL_TO_QUORUM
    )
    gradual_index = next(
        index
        for index, record in enumerate(records)
        if record.semantic_key == gradual_cell.semantic_key
    )
    assert records[gradual_index].state_trajectory[0].cycle > 0
    records[gradual_index] = records[gradual_index].model_copy(
        update={
            "state_trajectory": (AdmissionStateObservation(cycle=0, state=AdmissionState.ADMITTED),)
        }
    )
    early_admission = verify_safe_dormancy(planned, tuple(records))
    assert not early_admission.passed
    assert any("before T_evidence" in failure for failure in early_admission.failures)


def test_byzantine_region_requires_complete_within_bound_seed_evidence() -> None:
    planned = build_plan().experiment(BYZANTINE_BOUND_VIOLATION_NAME)
    within_bound_cells = tuple(
        cell
        for condition in (
            BoundCondition.ONE_BYZANTINE_REPRODUCER_WITHIN_BOUND,
            BoundCondition.ONE_BYZANTINE_VERIFIER_WITHIN_BOUND,
        )
        for cell in tuple(
            candidate
            for candidate in planned.cells
            if candidate.condition == condition
            and candidate.method == CoreMethodIdentity.RESOLVED_FEDSIRA_CORE
        )[:9]
    )
    records = tuple(
        PersistedExecutionRecord(
            schema_version=EXECUTION_RECORD_SCHEMA_VERSION,
            semantic_key=cell.semantic_key,
            experiment=cell.experiment,
            method=cell.method,
            condition=cell.condition,
            master_seed=cell.master_seed,
            terminal_state=ExperimentLifecycleState.COMPLETED,
            metrics=(
                (ComparisonMetric.MALICIOUS_ADMISSION, 0.0),
                (ComparisonMetric.LEGITIMATE_ADMISSION, 1.0),
                (ComparisonMetric.ATTACK_SUCCESS_RATE, 0.0),
                (ComparisonMetric.TARGET_F1, 0.9),
            ),
            failure=None,
        )
        for cell in within_bound_cells
    )

    assert not verify_byzantine_operating_region(planned, ()).passed
    assert verify_byzantine_operating_region(planned, records).passed
    assert not verify_byzantine_operating_region(planned, records[:-1]).passed
    duplicate_plan = planned.model_copy(update={"cells": (*planned.cells, planned.cells[0])})
    assert not verify_byzantine_operating_region(duplicate_plan, records).passed
    incomplete = records[0].model_copy(update={"metrics": records[0].metrics[:-1]})
    assert not verify_byzantine_operating_region(planned, (incomplete, *records[1:])).passed
    mismatched = records[0].model_copy(update={"condition": "unexpected-condition"})
    assert not verify_byzantine_operating_region(planned, (mismatched, *records[1:])).passed
    first = records[0]
    harmful = first.model_copy(
        update={
            "metrics": (
                (ComparisonMetric.MALICIOUS_ADMISSION, 1.0),
                (ComparisonMetric.LEGITIMATE_ADMISSION, 1.0),
                (ComparisonMetric.ATTACK_SUCCESS_RATE, 0.0),
                (ComparisonMetric.TARGET_F1, 0.9),
            )
        }
    )
    assert not verify_byzantine_operating_region(planned, (harmful, *records[1:])).passed
