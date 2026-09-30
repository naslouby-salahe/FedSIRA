from __future__ import annotations

import hashlib
from pathlib import Path

from fedsira.artifacts.paths import experiment_execution_root
from fedsira.domain.enums import (
    AdmissionDecisionMethod,
    AdmissionState,
    ControlledAdmissionWorld,
    ExperimentName,
    MetricObservationKey,
    SeedDerivationLabel,
    WorkspaceDirectoryToken,
)
from fedsira.domain.models import ScientificCell
from fedsira.domain.types import (
    ArtifactFileName,
    BooleanValue,
    ConditionName,
    FrozenDomainModel,
    MasterSeed,
    MethodName,
    MetricObservation,
    MetricValue,
    ProductionWeight,
    StandardizedValue,
    SupportedMacroF1Drop,
    TargetF1,
    TextValue,
)
from fedsira.evaluation.metrics import metrics_from_state
from fedsira.protocol.admission_comparison import (
    AdmissionComparisonContext,
    AdmissionComparisonResult,
    admission_comparison_records,
)
from fedsira.protocol.leave_fault_certificate import LeaveFaultAdmissionInput
from fedsira.runtime import current_application_context, namespace_seed

_COMPARISON_TABLE_NAME: ArtifactFileName = "admission-comparison.csv"
_CERTIFICATE_BATCH_NAME: ArtifactFileName = "certificate-decisions.json"
_MATRIX_CACHE: list[tuple[TextValue, tuple[AdmissionComparisonResult, ...]]] = []


class LeaveFaultAdmissionArtifact(FrozenDomainModel):
    method: AdmissionDecisionMethod
    world: ControlledAdmissionWorld
    master_seed: MasterSeed
    useful_capability: BooleanValue
    admission_input: LeaveFaultAdmissionInput
    state: AdmissionState
    certificate_utility: TargetF1 | None
    certificate_harm: SupportedMacroF1Drop | None
    source_production_weight: ProductionWeight
    production_update: tuple[StandardizedValue, ...] | None
    production_equals_malicious: BooleanValue


def comparison_context_for_seed(master_seed: MasterSeed) -> AdmissionComparisonContext:
    loaded = current_application_context().scientific_config
    protocol = loaded.protocol
    return AdmissionComparisonContext(
        certificate_config=protocol.leave_fault_certificate,
        opening_config=protocol.admission_opening,
        contract_config=loaded.capability_contract,
        final_gate=protocol.final_gate,
        synthesis_fault_bound=protocol.synthesis.maximum_byzantine_reproduction_rows,
        screen_seed=namespace_seed(master_seed, SeedDerivationLabel.SCREEN_DOMAIN_ORDER),
    )


def certificate_validation_records(
    master_seed: MasterSeed,
) -> tuple[AdmissionComparisonResult, ...]:
    context = comparison_context_for_seed(master_seed)
    return _records_for(context, master_seed)


def execute_leave_fault_validation_cell(
    cell: ScientificCell,
) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
    records = certificate_validation_records(cell.master_seed)
    method = _decision_method(cell.method)
    world = _controlled_world(cell.condition)
    record = _matching_record(records, method, world)
    _write_cell_artifact(cell, record)
    _write_matrix_artifacts(cell.master_seed, records)
    return record.state, _metrics(record)


def _records_for(
    context: AdmissionComparisonContext,
    master_seed: MasterSeed,
) -> tuple[AdmissionComparisonResult, ...]:
    key = _cache_key(master_seed, context)
    for cached_key, cached_records in _MATRIX_CACHE:
        if cached_key == key:
            return cached_records
    records = admission_comparison_records(context, master_seed)
    _MATRIX_CACHE.append((key, records))
    return records


def _cache_key(master_seed: MasterSeed, context: AdmissionComparisonContext) -> TextValue:
    return f"{master_seed}|{context.model_dump_json()}"


def _decision_method(method: MethodName) -> AdmissionDecisionMethod:
    for candidate in AdmissionDecisionMethod:
        if candidate == method:
            return candidate
    raise ValueError(f"cell method {method} is not an admission decision")


def _controlled_world(condition: ConditionName) -> ControlledAdmissionWorld:
    for world in ControlledAdmissionWorld:
        if world == condition:
            return world
    raise ValueError(f"cell condition {condition} is not a controlled admission world")


def _matching_record(
    records: tuple[AdmissionComparisonResult, ...],
    method: AdmissionDecisionMethod,
    world: ControlledAdmissionWorld,
) -> AdmissionComparisonResult:
    for record in records:
        if record.method is method and record.world is world:
            return record
    raise ValueError(f"no admission comparison for {method} on {world}")


def _metrics(record: AdmissionComparisonResult) -> tuple[MetricObservation, ...]:
    base = metrics_from_state(
        record.state,
        legitimate_admission_eligible=record.useful_capability,
    )
    utility = _optional_metric(record.certificate_utility)
    return (
        *base,
        (MetricObservationKey.SOURCE_PRODUCTION_WEIGHT, float(record.source_production_weight)),
        (
            MetricObservationKey.PRODUCTION_EQUALS_MALICIOUS,
            _indicator(record.production_equals_malicious),
        ),
        (MetricObservationKey.LEAVE_FAULT_CERTIFICATE_UTILITY, utility),
    )


def _optional_metric(value: TargetF1 | None) -> MetricValue | None:
    if value is None:
        return None
    return float(value)


def _indicator(flag: BooleanValue) -> MetricValue:
    if flag:
        return 1.0
    return 0.0


def _write_cell_artifact(cell: ScientificCell, record: AdmissionComparisonResult) -> None:
    artifact = _artifact(cell.master_seed, record)
    directory = _artifact_directory()
    directory.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(cell.semantic_key.encode("utf-8")).hexdigest()
    (directory / f"{digest}.json").write_text(artifact.model_dump_json(), encoding="utf-8")


def _write_matrix_artifacts(
    master_seed: MasterSeed,
    records: tuple[AdmissionComparisonResult, ...],
) -> None:
    directory = _artifact_directory()
    directory.mkdir(parents=True, exist_ok=True)
    certificate_rows = tuple(
        _artifact(master_seed, record)
        for record in records
        if record.method is AdmissionDecisionMethod.LEAVE_FAULT_CERTIFICATE
    )
    body = ",".join(row.model_dump_json() for row in certificate_rows)
    (directory / _CERTIFICATE_BATCH_NAME).write_text(f"[{body}]", encoding="utf-8")
    table_directory = _table_directory()
    table_directory.mkdir(parents=True, exist_ok=True)
    (table_directory / _COMPARISON_TABLE_NAME).write_text(
        _comparison_csv(records), encoding="utf-8"
    )


def _artifact(
    master_seed: MasterSeed, record: AdmissionComparisonResult
) -> LeaveFaultAdmissionArtifact:
    return LeaveFaultAdmissionArtifact(
        method=record.method,
        world=record.world,
        master_seed=master_seed,
        useful_capability=record.useful_capability,
        admission_input=record.admission_input,
        state=record.state,
        certificate_utility=record.certificate_utility,
        certificate_harm=record.certificate_harm,
        source_production_weight=record.source_production_weight,
        production_update=record.production_update,
        production_equals_malicious=record.production_equals_malicious,
    )


def _comparison_csv(records: tuple[AdmissionComparisonResult, ...]) -> TextValue:
    lines = [
        "method,world,state,certificate_utility,source_production_weight,"
        "production_equals_malicious,useful_capability"
    ]
    for record in records:
        utility = "" if record.certificate_utility is None else str(record.certificate_utility)
        lines.append(
            f"{record.method},{record.world},{record.state},{utility},"
            f"{record.source_production_weight},{record.production_equals_malicious},"
            f"{record.useful_capability}"
        )
    return "\n".join(lines) + "\n"


def _artifact_directory() -> Path:
    return (
        experiment_execution_root(ExperimentName.LEAVE_FAULT_CERTIFICATE_VALIDATION)
        / WorkspaceDirectoryToken.ARTIFACTS
    )


def _table_directory() -> Path:
    return (
        experiment_execution_root(ExperimentName.LEAVE_FAULT_CERTIFICATE_VALIDATION)
        / WorkspaceDirectoryToken.TABLES
    )
