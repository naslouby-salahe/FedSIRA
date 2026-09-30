from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from typing import Protocol, TypeAlias, cast

import pandas

from fedsira.domain.enums import (
    DatasetId,
    ExperimentName,
    ReportColumnName,
)
from fedsira.domain.types import (
    ArtifactDigest,
    CodeRevision,
    FrozenDomainModel,
    MasterSeed,
    MethodName,
    MetricName,
    MetricValue,
    ScenarioName,
    ScientificCellCount,
    ScientificCellSemanticKeyTuple,
)


class ParquetStringArray(Protocol):
    def tolist(self) -> ScientificCellSemanticKeyTuple: ...


ParquetScalar: TypeAlias = str | int | float | None | list[str] | ParquetStringArray

AGGREGATE_METRIC_COLUMNS = (
    ReportColumnName.EXPERIMENT,
    ReportColumnName.METHOD,
    ReportColumnName.CONDITION,
    ReportColumnName.METRIC,
    ReportColumnName.OBSERVATION_COUNT,
    ReportColumnName.SEED_COUNT,
    ReportColumnName.MEAN_VALUE,
    ReportColumnName.SAMPLE_STANDARD_DEVIATION,
    ReportColumnName.MEDIAN_VALUE,
    ReportColumnName.FIRST_QUARTILE,
    ReportColumnName.THIRD_QUARTILE,
    ReportColumnName.CONFIDENCE_INTERVAL_LOWER,
    ReportColumnName.CONFIDENCE_INTERVAL_UPPER,
    ReportColumnName.SOURCE_OBSERVATION_IDS,
    ReportColumnName.SOURCE_CELL_SEMANTIC_KEYS,
)

SEED_METRIC_COLUMNS = (
    ReportColumnName.EXPERIMENT,
    ReportColumnName.DATASET,
    ReportColumnName.METHOD,
    ReportColumnName.CONDITION,
    ReportColumnName.MASTER_SEED,
    ReportColumnName.METRIC,
    ReportColumnName.VALUE,
    ReportColumnName.CONFIGURATION_DIGEST,
    ReportColumnName.CODE_REVISION,
    ReportColumnName.DATASET_MANIFEST_HASH,
    ReportColumnName.SCORING_ARTIFACT_IDS,
    ReportColumnName.SOURCE_OBSERVATION_IDS,
    ReportColumnName.SOURCE_CELL_SEMANTIC_KEYS,
)


class AggregateMetricEvidenceRow(FrozenDomainModel):
    experiment: ExperimentName
    method: MethodName
    condition: ScenarioName
    metric: MetricName
    observation_count: ScientificCellCount
    seed_count: ScientificCellCount
    mean_value: MetricValue
    sample_standard_deviation: MetricValue
    median_value: MetricValue
    first_quartile: MetricValue
    third_quartile: MetricValue
    confidence_interval_lower: MetricValue | None
    confidence_interval_upper: MetricValue | None
    source_observation_ids: tuple[ArtifactDigest, ...]
    source_cell_semantic_keys: ScientificCellSemanticKeyTuple

    def values(
        self,
    ) -> tuple[
        ExperimentName,
        MethodName,
        ScenarioName,
        MetricName,
        ScientificCellCount,
        ScientificCellCount,
        MetricValue,
        MetricValue,
        MetricValue,
        MetricValue,
        MetricValue,
        MetricValue | None,
        MetricValue | None,
        tuple[ArtifactDigest, ...],
        ScientificCellSemanticKeyTuple,
    ]:
        return (
            self.experiment,
            self.method,
            self.condition,
            self.metric,
            self.observation_count,
            self.seed_count,
            self.mean_value,
            self.sample_standard_deviation,
            self.median_value,
            self.first_quartile,
            self.third_quartile,
            self.confidence_interval_lower,
            self.confidence_interval_upper,
            self.source_observation_ids,
            self.source_cell_semantic_keys,
        )


class SeedMetricEvidenceRow(FrozenDomainModel):
    experiment: ExperimentName
    dataset: DatasetId
    method: MethodName
    condition: ScenarioName
    master_seed: MasterSeed
    metric: MetricName
    value: MetricValue
    configuration_digest: ArtifactDigest
    code_revision: CodeRevision | None
    dataset_manifest_hash: ArtifactDigest
    scoring_artifact_ids: tuple[ArtifactDigest, ...]
    source_observation_ids: tuple[ArtifactDigest, ...]
    source_cell_semantic_keys: ScientificCellSemanticKeyTuple

    def values(
        self,
    ) -> tuple[
        ExperimentName,
        DatasetId,
        MethodName,
        ScenarioName,
        MasterSeed,
        MetricName,
        MetricValue,
        ArtifactDigest,
        CodeRevision | None,
        ArtifactDigest,
        tuple[ArtifactDigest, ...],
        tuple[ArtifactDigest, ...],
        ScientificCellSemanticKeyTuple,
    ]:
        return (
            self.experiment,
            self.dataset,
            self.method,
            self.condition,
            self.master_seed,
            self.metric,
            self.value,
            self.configuration_digest,
            self.code_revision,
            self.dataset_manifest_hash,
            self.scoring_artifact_ids,
            self.source_observation_ids,
            self.source_cell_semantic_keys,
        )


def read_aggregate_metric_evidence(
    path: Path,
    experiment: ExperimentName,
) -> tuple[AggregateMetricEvidenceRow, ...]:
    if not path.is_file():
        return ()
    return _read_aggregate_metric_evidence_cached(
        path,
        experiment,
        hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def read_seed_metric_evidence(
    path: Path,
    experiment: ExperimentName,
) -> tuple[SeedMetricEvidenceRow, ...]:
    if not path.is_file():
        return ()
    return _read_seed_metric_evidence_cached(
        path,
        experiment,
        hashlib.sha256(path.read_bytes()).hexdigest(),
    )


@lru_cache(maxsize=64)
def _read_seed_metric_evidence_cached(
    path: Path,
    experiment: ExperimentName,
    content_identity: ArtifactDigest,
) -> tuple[SeedMetricEvidenceRow, ...]:
    del content_identity
    frame = pandas.read_parquet(path)
    if not set(SEED_METRIC_COLUMNS).issubset(frame.columns):
        return ()
    raw_rows = cast(
        Iterable[tuple[ParquetScalar, ...]],
        frame.loc[:, list(SEED_METRIC_COLUMNS)].itertuples(index=False, name=None),
    )
    result: list[SeedMetricEvidenceRow] = []
    for raw in raw_rows:
        (
            raw_experiment,
            raw_dataset,
            raw_method,
            raw_condition,
            raw_master_seed,
            raw_metric,
            raw_value,
            raw_configuration_digest,
            raw_code_revision,
            raw_dataset_manifest_hash,
            raw_scoring_artifact_ids,
            raw_observation_ids,
            raw_cell_keys,
        ) = raw
        if raw_experiment != experiment:
            continue
        if not all(
            isinstance(value, str)
            for value in (
                raw_dataset,
                raw_method,
                raw_condition,
                raw_metric,
                raw_configuration_digest,
                raw_dataset_manifest_hash,
            )
        ):
            raise ValueError(f"{experiment}: seed metric identity is malformed")
        if raw_code_revision is not None and not isinstance(raw_code_revision, str):
            raise ValueError(f"{experiment}: seed metric code revision is malformed")
        if not isinstance(raw_value, int | float) or not math.isfinite(float(raw_value)):
            raise ValueError(f"{experiment}: seed metric value is malformed")
        result.append(
            SeedMetricEvidenceRow(
                experiment=experiment,
                dataset=DatasetId(raw_dataset),
                method=cast(MethodName, raw_method),
                condition=cast(ScenarioName, raw_condition),
                master_seed=int(cast(int, raw_master_seed)),
                metric=cast(MetricName, raw_metric),
                value=float(raw_value),
                configuration_digest=cast(ArtifactDigest, raw_configuration_digest),
                code_revision=raw_code_revision,
                dataset_manifest_hash=cast(ArtifactDigest, raw_dataset_manifest_hash),
                scoring_artifact_ids=tuple(_lineage_values(raw_scoring_artifact_ids, experiment)),
                source_observation_ids=tuple(_lineage_values(raw_observation_ids, experiment)),
                source_cell_semantic_keys=_lineage_values(raw_cell_keys, experiment),
            )
        )
    return tuple(result)


@lru_cache(maxsize=64)
def _read_aggregate_metric_evidence_cached(
    path: Path,
    experiment: ExperimentName,
    content_identity: ArtifactDigest,
) -> tuple[AggregateMetricEvidenceRow, ...]:
    del content_identity
    frame = pandas.read_parquet(path)
    if not set(AGGREGATE_METRIC_COLUMNS).issubset(frame.columns):
        return ()
    raw_rows = cast(
        Iterable[tuple[ParquetScalar, ...]],
        frame.loc[:, list(AGGREGATE_METRIC_COLUMNS)].itertuples(index=False, name=None),
    )
    result: list[AggregateMetricEvidenceRow] = []
    for raw in raw_rows:
        (
            raw_experiment,
            raw_method,
            raw_condition,
            raw_metric,
            raw_observation_count,
            raw_seed_count,
            raw_mean,
            raw_standard_deviation,
            raw_median,
            raw_first_quartile,
            raw_third_quartile,
            raw_ci_lower,
            raw_ci_upper,
            raw_observation_ids,
            raw_cell_keys,
        ) = raw
        if raw_experiment != experiment:
            continue
        if not all(isinstance(value, str) for value in (raw_method, raw_condition, raw_metric)):
            raise ValueError(f"{experiment}: aggregate metric identity is malformed")
        observation_ids = _lineage_values(raw_observation_ids, experiment)
        cell_keys = _lineage_values(raw_cell_keys, experiment)
        result.append(
            AggregateMetricEvidenceRow(
                experiment=experiment,
                method=cast(MethodName, raw_method),
                condition=cast(ScenarioName, raw_condition),
                metric=cast(MetricName, raw_metric),
                observation_count=int(cast(int, raw_observation_count)),
                seed_count=int(cast(int, raw_seed_count)),
                mean_value=float(cast(float, raw_mean)),
                sample_standard_deviation=float(cast(float, raw_standard_deviation)),
                median_value=float(cast(float, raw_median)),
                first_quartile=float(cast(float, raw_first_quartile)),
                third_quartile=float(cast(float, raw_third_quartile)),
                confidence_interval_lower=_optional_float(raw_ci_lower),
                confidence_interval_upper=_optional_float(raw_ci_upper),
                source_observation_ids=tuple(observation_ids),
                source_cell_semantic_keys=tuple(cell_keys),
            )
        )
    return tuple(result)


def _lineage_values(
    value: ParquetScalar,
    experiment: ExperimentName,
) -> ScientificCellSemanticKeyTuple:
    if isinstance(value, list) and all(type(item) is str for item in value):
        return tuple(value)
    if value is not None and not isinstance(value, str | int | float):
        values = tuple(cast(ParquetStringArray, value).tolist())
        if all(type(item) is str for item in values):
            return values
    raise ValueError(f"{experiment}: aggregate metric lineage is malformed")


def _optional_float(value: ParquetScalar) -> MetricValue | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        numeric = float(value)
        return None if math.isnan(numeric) else numeric
    raise ValueError("aggregate confidence interval bound is malformed")
