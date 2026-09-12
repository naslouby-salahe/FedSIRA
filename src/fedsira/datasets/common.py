from __future__ import annotations

import hashlib
import json
import math
from collections import OrderedDict, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Self

import duckdb
import torch
from pydantic import model_validator

from fedsira.config import RoleIntervals, SamplingCapsPerDomain, ScalingConfig
from fedsira.domain.enums import (
    CapabilityContractScope,
    DatasetId,
    EpistemicFailureType,
    Role,
    RootCause,
    SeedNamespace,
)
from fedsira.domain.models import MetricResult
from fedsira.domain.types import (
    UINT32_MODULUS,
    ArtifactDigest,
    ArtifactReuseDecision,
    AttackCount,
    BooleanValue,
    ClassCount,
    ClassLabel,
    DatasetClassToken,
    DatasetColumnName,
    DatasetFileDigest,
    DatasetManifestDigest,
    DerivedSeed,
    DomainId,
    ExampleCount,
    FeatureAccumulator,
    FeatureCount,
    FeatureIndex,
    FeatureMoment,
    FeatureName,
    FeatureShiftSign,
    FeatureVector,
    FrozenDomainModel,
    HeterogeneityMultiplier,
    NamespaceSeed,
    OverwriteExisting,
    PredictorCount,
    PreparedEvidencePresent,
    PreparedViewKey,
    Probability,
    RelativePathText,
    RepositoryPath,
    RoleBoundary,
    RolePosition,
    RoleToken,
    RoleWindowContainsSample,
    RowCount,
    SampleId,
    SampleIdPrefix,
    SamplingCap,
    SamplingSelectionDigest,
    SchemaVersion,
    SeedDerivationLabel,
    SourceRowIndex,
    SquaredFeatureAccumulator,
    StandardizedValue,
    TextValue,
    TriggerFeatureValue,
)
from fedsira.runtime import deterministic_order, framed_bytes

SUPPORTED_ROLE_ORDER: tuple[Role, ...] = (
    Role.ANCHOR_TRAIN,
    Role.ANCHOR_VALIDATION,
    Role.POST_REFERENCE_REPLAY,
    Role.ROW_VERIFICATION,
    Role.FINAL_GATE,
    Role.REPORT_TEST,
)
TARGET_ROLE_ORDER: tuple[Role, ...] = (
    Role.SOURCE_PROPOSAL,
    Role.CANDIDATE_SCREEN,
    Role.REPRODUCTION,
    Role.ROW_VERIFICATION,
    Role.FINAL_GATE,
    Role.REPORT_TEST,
)
TRAINING_AND_SCREENING_ROLES: frozenset[Role] = frozenset(
    (
        Role.ANCHOR_TRAIN,
        Role.ANCHOR_VALIDATION,
        Role.POST_REFERENCE_REPLAY,
        Role.SOURCE_PROPOSAL,
        Role.CANDIDATE_SCREEN,
        Role.REPRODUCTION,
    )
)
EVIDENCE_ROLES: frozenset[Role] = frozenset(
    (Role.ROW_VERIFICATION, Role.FINAL_GATE, Role.REPORT_TEST)
)
PREPROCESSING_SAMPLE_ORDER_SEED: DerivedSeed = (
    int.from_bytes(
        hashlib.sha256(b"FedSIRA|preprocess_sample_order|1").digest()[0:8], byteorder="big"
    )
    % UINT32_MODULUS
)
FILE_DIGEST_CHUNK_BYTES = 1_048_576


class DatasetExclusionReason(StrEnum):
    NON_FINITE_PREDICTOR = "non_finite_predictor"
    UNPARSEABLE_PREDICTOR = "unparseable_predictor"
    ROW_WIDTH_MISMATCH = "row_width_mismatch"


class RoleWindow(FrozenDomainModel):
    role: Role
    lower_inclusive: RoleBoundary
    upper_exclusive: RoleBoundary

    @model_validator(mode="after")
    def _validate_bounds(self) -> Self:
        if self.lower_inclusive >= self.upper_exclusive:
            raise ValueError(
                f"role interval for {self.role.name} must satisfy lower < upper, "
                f"got [{self.lower_inclusive}, {self.upper_exclusive})"
            )
        return self

    def contains(self, normalized_position: RolePosition) -> RoleWindowContainsSample:
        return self.lower_inclusive <= normalized_position < self.upper_exclusive


class FeatureStatistic(FrozenDomainModel):
    count: RowCount
    total: FeatureAccumulator
    total_squared: SquaredFeatureAccumulator


class FeatureMoments(FrozenDomainModel):
    feature_names: tuple[FeatureName, ...]
    means: tuple[FeatureMoment, ...]
    standard_deviations: tuple[FeatureMoment, ...]
    training_row_count: RowCount

    @model_validator(mode="after")
    def _validate_consistency(self) -> Self:
        if not (len(self.feature_names) == len(self.means) == len(self.standard_deviations)):
            raise ValueError("feature moments must have matching lengths")
        if any(standard_deviation <= 0.0 for standard_deviation in self.standard_deviations):
            raise ValueError("feature standard deviations must be positive")
        return self


class ScalerMetadata(FrozenDomainModel):
    schema_version: SchemaVersion
    feature_names: tuple[DatasetColumnName, ...]
    means: tuple[FeatureMoment, ...]
    standard_deviations: tuple[FeatureMoment, ...]
    training_row_count: RowCount


class RoleSamplingCap(FrozenDomainModel):
    role: Role
    cap: SamplingCap | None


if not TRAINING_AND_SCREENING_ROLES.isdisjoint(EVIDENCE_ROLES):
    raise AssertionError("evidence roles must never also be eligible for training/screening")


def role_hash_token(role: Role) -> RoleToken:
    return role.name


def role_from_hash_token(token: RoleToken) -> Role:
    try:
        return Role[token]
    except KeyError as error:
        raise ValueError(f"unsupported role token: {token}") from error


def role_for_normalized_position(
    normalized_position: RolePosition,
    windows: tuple[RoleWindow, ...],
) -> Role | None:
    for window in windows:
        if window.contains(normalized_position):
            return window.role
    return None


def supported_role_windows(role_intervals: RoleIntervals) -> tuple[RoleWindow, ...]:
    return tuple(
        RoleWindow(
            role=role,
            lower_inclusive=role_intervals.supported.interval_for(role)[0],
            upper_exclusive=role_intervals.supported.interval_for(role)[1],
        )
        for role in SUPPORTED_ROLE_ORDER
    )


def target_role_windows(role_intervals: RoleIntervals) -> tuple[RoleWindow, ...]:
    return tuple(
        RoleWindow(
            role=role,
            lower_inclusive=role_intervals.target.interval_for(role)[0],
            upper_exclusive=role_intervals.target.interval_for(role)[1],
        )
        for role in TARGET_ROLE_ORDER
    )


def compute_sample_id(
    sample_id_prefix: SampleIdPrefix,
    normalized_relative_csv_path: RelativePathText,
    file_sha256: ArtifactDigest,
    zero_based_original_row_index: SourceRowIndex,
) -> ArtifactDigest:
    return hashlib.sha256(
        framed_bytes(
            sample_id_prefix,
            normalized_relative_csv_path,
            file_sha256,
            zero_based_original_row_index,
        )
    ).hexdigest()


def compute_file_checksum(path: Path) -> DatasetFileDigest:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(FILE_DIGEST_CHUNK_BYTES), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def sampling_cap_selection_digest(
    dataset_file_sha256: DatasetFileDigest,
    domain_hash_token: DomainId,
    class_id: ClassLabel,
    role_hash_token_value: RoleToken,
    original_row_index: SourceRowIndex,
) -> SamplingSelectionDigest:
    return hashlib.sha256(
        framed_bytes(
            dataset_file_sha256,
            domain_hash_token,
            class_id,
            role_hash_token_value,
            original_row_index,
            PREPROCESSING_SAMPLE_ORDER_SEED,
        )
    ).digest()


def apply_sampling_cap(
    dataset_file_sha256: DatasetFileDigest,
    domain_hash_token: DomainId,
    class_id: ClassLabel,
    role_hash_token_value: RoleToken,
    original_row_indices: tuple[SourceRowIndex, ...],
    cap: SamplingCap,
) -> tuple[SourceRowIndex, ...]:
    if len(original_row_indices) <= cap:
        return original_row_indices
    ordered = sorted(
        original_row_indices,
        key=lambda original_row_index: (
            sampling_cap_selection_digest(
                dataset_file_sha256,
                domain_hash_token,
                class_id,
                role_hash_token_value,
                original_row_index,
            ),
            original_row_index,
        ),
    )
    return tuple(ordered[:cap])


def sampling_cap_for_role(
    caps: SamplingCapsPerDomain,
    role: Role,
    is_target: BooleanValue,
    is_benign: BooleanValue,
) -> SamplingCap | None:
    if is_target:
        return _target_sampling_cap(caps, role)
    return _supported_sampling_cap(caps, role, is_benign)


def _target_sampling_cap(caps: SamplingCapsPerDomain, role: Role) -> SamplingCap | None:
    if role is Role.SOURCE_PROPOSAL:
        return caps.source_proposal_target
    if role is Role.CANDIDATE_SCREEN:
        return caps.candidate_screen_target
    if role is Role.REPRODUCTION:
        return caps.reproduction_target
    if role is Role.ROW_VERIFICATION:
        return caps.row_verification_target
    if role is Role.FINAL_GATE:
        return caps.final_gate_target
    if role is Role.REPORT_TEST:
        return caps.report_test_target
    raise ValueError(f"unsupported target-data role: {role.name}")


def _supported_sampling_cap(
    caps: SamplingCapsPerDomain,
    role: Role,
    is_benign: BooleanValue,
) -> SamplingCap | None:
    if role is Role.ANCHOR_TRAIN:
        return caps.anchor_train_per_supported_class
    if role is Role.ANCHOR_VALIDATION:
        return caps.anchor_validation_per_supported_class
    if role is Role.POST_REFERENCE_REPLAY:
        return None
    if role is Role.ROW_VERIFICATION:
        return caps.row_verification_supported_per_supported_class
    if role is Role.FINAL_GATE:
        return caps.final_gate_supported_per_supported_class
    if role is Role.REPORT_TEST:
        return caps.report_test_benign if is_benign else caps.report_test_other_supported_per_class
    raise ValueError(f"unsupported supported-data role: {role.name}")


def fit_feature_moments(
    feature_names: tuple[FeatureName, ...],
    statistics: tuple[FeatureStatistic, ...],
    scaling_config: ScalingConfig,
) -> FeatureMoments:
    if len(feature_names) != len(statistics):
        raise ValueError("feature name count must match statistics count")
    means: list[FeatureMoment] = []
    standard_deviations: list[FeatureMoment] = []
    row_count: RowCount = 0
    for feature_index, feature_name in enumerate(feature_names):
        statistic = statistics[feature_index]
        if statistic.count <= 0:
            raise ValueError(f"feature {feature_name} has no supported anchor-train rows")
        row_count = statistic.count
        mean = statistic.total / statistic.count
        variance = max(statistic.total_squared / statistic.count - mean * mean, 0.0)
        standard_deviation = math.sqrt(variance)
        if standard_deviation == 0.0:
            standard_deviation = scaling_config.zero_standard_deviation_scale
        means.append(mean)
        standard_deviations.append(standard_deviation)
    return FeatureMoments(
        feature_names=feature_names,
        means=tuple(means),
        standard_deviations=tuple(standard_deviations),
        training_row_count=row_count,
    )


def sql_string(value: TextValue) -> TextValue:
    return "'" + value.replace("'", "''") + "'"


def sql_ident(name: DatasetColumnName) -> TextValue:
    return '"' + name.replace('"', '""') + '"'


def varchar_column_map(names: tuple[DatasetColumnName, ...]) -> TextValue:
    return "{" + ", ".join(f"{sql_string(name)}: 'VARCHAR'" for name in names) + "}"


def read_csv_relation(
    path: Path,
    header: tuple[DatasetColumnName, ...],
    ignore_errors: BooleanValue = False,
) -> TextValue:
    return (
        "read_csv("
        f"{sql_string(path.as_posix())}, header=true, delim=',', quote='\"', escape='\"', "
        f"auto_detect=false, ignore_errors={'true' if ignore_errors else 'false'}, "
        f"columns={varchar_column_map(header)})"
    )


def role_case_sql(position_sql: TextValue, windows: tuple[RoleWindow, ...]) -> TextValue:
    clauses = tuple(
        "WHEN "
        f"{position_sql} >= {window.lower_inclusive} AND {position_sql} < {window.upper_exclusive} "
        f"THEN {sql_string(role_hash_token(window.role))}"
        for window in windows
    )
    return "CASE " + " ".join(clauses) + " END"


def standardized_feature_sql(
    column: DatasetColumnName,
    mean: FeatureMoment,
    standard_deviation: FeatureMoment,
    scaling_config: ScalingConfig,
) -> TextValue:
    expression = f"(({sql_ident(column)} - ({mean})) / ({standard_deviation}))"
    return (
        f"LEAST(GREATEST({expression}, {scaling_config.clip_min}), {scaling_config.clip_max}) "
        f"AS {sql_ident(column)}"
    )


def open_tabular_engine(database_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect(":memory:" if database_path is None else str(database_path))
    connection.execute("SET threads TO 1")
    return connection


def copy_query_to_parquet(
    connection: duckdb.DuckDBPyConnection,
    query: TextValue,
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection.execute(f"COPY ({query}) TO {sql_string(path.as_posix())} (FORMAT PARQUET)")


def write_json_payload(
    path: Path,
    payload: FrozenDomainModel,
    overwrite: OverwriteExisting,
) -> None:
    if path.exists() and not overwrite:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.model_dump_json(indent=2), encoding="utf-8")


def view_parquet_path(prepared_root: Path, view_key: PreparedViewKey) -> Path:
    return prepared_root / f"{view_key}.parquet"


def fetch_feature_statistics(
    connection: duckdb.DuckDBPyConnection,
    source_sql: TextValue,
    feature_names: tuple[DatasetColumnName, ...],
) -> tuple[FeatureStatistic, ...]:
    aggregations = ", ".join(
        f"count(*), sum({sql_ident(name)}), sum({sql_ident(name)} * {sql_ident(name)})"
        for name in feature_names
    )
    row = connection.execute(f"SELECT {aggregations} FROM ({source_sql})").fetchone()
    if row is None:
        raise ValueError("feature statistic query returned no row")
    statistics: list[FeatureStatistic] = []
    for feature_index in range(len(feature_names)):
        offset = feature_index * 3
        count = row[offset]
        total = row[offset + 1]
        total_squared = row[offset + 2]
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise TypeError("feature count must be a non-negative integer")
        if total is None or total_squared is None:
            raise ValueError("feature aggregates must be present")
        statistics.append(
            FeatureStatistic(
                count=count,
                total=float(total),
                total_squared=float(total_squared),
            )
        )
    return tuple(statistics)


class DatasetPreparationLogFields(FrozenDomainModel):
    dataset: DatasetId | None = None
    domain: DomainId | None = None
    class_id: DatasetClassToken | None = None
    file: RelativePathText | None = None
    rows: RowCount | None = None
    selected: RowCount | None = None
    training_rows: RowCount | None = None
    view: PreparedViewKey | None = None
    path: RelativePathText | None = None
    raw_rows: RowCount | None = None
    retained_rows: RowCount | None = None
    excluded_rows: RowCount | None = None
    class_count: ClassCount | None = None
    predictor_count: PredictorCount | None = None
    predictor_count_matches_official: BooleanValue | None = None
    prepared_views: RowCount | None = None
    exclusion_rate: Probability | None = None
    dataset_file_manifest_hash: DatasetManifestDigest | None = None
    structurally_unavailable_classes: tuple[DatasetClassToken, ...] | None = None
    dataset_manifest_reused: ArtifactReuseDecision | None = None


class DatasetSpecification(FrozenDomainModel):
    dataset: DatasetId
    class_tokens: tuple[DatasetClassToken, ...]
    domain_ids: tuple[DomainId, ...]
    domain_hash_tokens: tuple[DomainId, ...]
    target_class: DatasetClassToken
    benign_class: DatasetClassToken
    supported_class_tokens: tuple[DatasetClassToken, ...]
    attack_carrier_class: DatasetClassToken | None
    trigger_feature_names: tuple[FeatureName, ...]
    expected_predictor_count: PredictorCount | None
    domain_proxy_semantics: TextValue
    raw_data_relative: RepositoryPath


class PreparedDomainSummary(FrozenDomainModel):
    domain_id: DomainId
    counts: tuple[tuple[RoleToken, DatasetClassToken, RowCount], ...]

    def count(self, role: RoleToken, class_token: DatasetClassToken) -> RowCount:
        return next(
            (
                value
                for observed_role, observed_class, value in self.counts
                if observed_role == role and observed_class == class_token
            ),
            0,
        )

    def count_for_role(
        self, role: RoleToken, excluded_classes: frozenset[DatasetClassToken] = frozenset()
    ) -> RowCount:
        return sum(
            value
            for observed_role, observed_class, value in self.counts
            if observed_role == role and observed_class not in excluded_classes
        )


def dataset_specification(dataset: DatasetId) -> DatasetSpecification:
    if dataset is DatasetId.N_BAIOT:
        from fedsira.datasets.nbaiot.schema import specification

        return specification()
    if dataset is DatasetId.CICIOT2023:
        from fedsira.datasets.ciciot2023.schema import specification

        return specification()
    raise ValueError(f"no dataset specification for {dataset.value}")


def prepared_domain_summaries(
    dataset: DatasetId,
    prepared_root: Path,
) -> tuple[PreparedDomainSummary, ...]:
    specification = dataset_specification(dataset)
    counts: defaultdict[DomainId, defaultdict[tuple[str, DatasetClassToken], int]] = defaultdict(
        lambda: defaultdict(int)
    )
    for sidecar in sorted(prepared_root.glob("*.json")):
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        domain = payload.get("domain", payload.get("pseudo_domain"))
        class_token = payload.get("class_id", payload.get("normalized_label"))
        role = payload.get("role")
        row_count = payload.get("row_count")
        if domain is None or class_token is None or role is None or not isinstance(row_count, int):
            raise ValueError(f"invalid prepared-view sidecar: {sidecar}")
        domain_id = (
            f"PSEUDO_DOMAIN_{int(domain) + 1}" if dataset is DatasetId.CICIOT2023 else str(domain)
        )
        if domain_id not in specification.domain_ids:
            raise ValueError(f"unexpected {dataset.value} domain {domain_id!r} in {sidecar}")
        counts[domain_id][(str(role), str(class_token))] += row_count
    if not counts:
        raise ValueError(f"no prepared-view evidence exists for {dataset.value}")
    return tuple(
        PreparedDomainSummary(
            domain_id=domain_id,
            counts=tuple(
                (role, class_token, row_count)
                for (role, class_token), row_count in sorted(domain_counts.items())
            ),
        )
        for domain_id, domain_counts in sorted(counts.items())
    )


def prepared_view_digest(prepared_root: Path) -> ArtifactDigest:
    sidecars = tuple(sorted(prepared_root.glob("*.json")))
    if not sidecars:
        raise ValueError(f"no prepared-view evidence exists at {prepared_root}")
    digest = hashlib.sha256()
    for sidecar in sidecars:
        digest.update(sidecar.name.encode("utf-8"))
        digest.update(sidecar.read_bytes())
    return digest.hexdigest()


def deterministic_domain_order(
    adapter: DatasetAdapter,
    domains: tuple[DomainId, ...],
    domain_separator: SeedDerivationLabel,
    order_namespace_seed: NamespaceSeed,
) -> tuple[DomainId, ...]:
    tokens = tuple(adapter.domain_token(domain) for domain in domains)
    ordered_tokens = deterministic_order(tokens, domain_separator, order_namespace_seed)
    return tuple(domains[tokens.index(token)] for token in ordered_tokens)


@dataclass(frozen=True)
class PreparedRows:
    sample_ids: tuple[ArtifactDigest, ...]
    features: tuple[FeatureVector, ...]
    labels: tuple[ClassLabel, ...]

    @property
    def row_count(self) -> ExampleCount:
        return len(self.sample_ids)


@dataclass(frozen=True)
class RealAnchor:
    input_width: FeatureCount
    output_width: FeatureCount
    flat_parameters: torch.Tensor
    dataset_manifest_hash: ArtifactDigest
    round_start_flat_parameters: tuple[torch.Tensor, ...]


@dataclass(frozen=True)
class DomainTargetMetrics:
    target_f1: MetricResult
    supported_macro_f1: MetricResult
    benign_far: MetricResult


def real_evidence_available(prepared_root: Path) -> PreparedEvidencePresent:
    return prepared_root.exists() and any(prepared_root.glob("*.parquet"))


def prepared_feature_names(prepared_root: Path) -> tuple[FeatureName, ...] | None:
    parquet_files = tuple(sorted(prepared_root.glob("*.parquet")))
    if not parquet_files:
        return None
    connection = open_tabular_engine()
    cursor = connection.execute(
        f"DESCRIBE SELECT * FROM read_parquet({sql_string(parquet_files[0].as_posix())})"
    )
    columns = tuple(str(row[0]) for row in cursor.fetchall())
    return tuple(column for column in columns if column not in ("sample_id", "label"))


def dataset_manifest_hash(prepared_root: Path) -> ArtifactDigest:
    parquet_files = tuple(sorted(prepared_root.glob("*.parquet")))
    if not parquet_files:
        return "0" * 64
    hasher = hashlib.sha256()
    for path in parquet_files:
        hasher.update(framed_bytes(path.name, path.stat().st_size))
    return hasher.hexdigest()


def flat_parameters_identity(flat_parameters: torch.Tensor) -> ArtifactDigest:
    values = flat_parameters.detach().cpu()
    joined = "|".join(repr(values[index].item()) for index in range(values.numel()))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DatasetAdapter:
    specification: DatasetSpecification
    prepared_root: Path

    @property
    def dataset(self) -> DatasetId:
        return self.specification.dataset

    @property
    def domain_ids(self) -> tuple[DomainId, ...]:
        return self.specification.domain_ids

    @property
    def class_tokens(self) -> tuple[DatasetClassToken, ...]:
        return self.specification.class_tokens

    @property
    def supported_class_tokens(self) -> tuple[DatasetClassToken, ...]:
        return self.specification.supported_class_tokens

    @property
    def target_class_token(self) -> DatasetClassToken:
        return self.specification.target_class

    @property
    def benign_class_token(self) -> DatasetClassToken:
        return self.specification.benign_class

    @property
    def trigger_feature_names(self) -> tuple[FeatureName, ...]:
        return self.specification.trigger_feature_names

    def domain_token(self, domain_id: DomainId) -> DomainId:
        try:
            index = self.specification.domain_ids.index(domain_id)
        except ValueError as error:
            raise ValueError(
                f"unknown domain identity for {self.dataset.value}: {domain_id}"
            ) from error
        return self.specification.domain_hash_tokens[index]

    def attack_carrier_class_token(self) -> DatasetClassToken:
        carrier = self.specification.attack_carrier_class
        if carrier is None:
            raise ValueError(f"{self.dataset.value} declares no attack carrier class")
        return carrier

    def view_key(
        self, domain_id: DomainId, class_token: DatasetClassToken, role: Role
    ) -> PreparedViewKey:
        return f"{self.domain_token(domain_id)}_{class_token}_{role_hash_token(role)}"

    def load_rows(
        self, domain_id: DomainId, class_token: DatasetClassToken, role: Role
    ) -> PreparedRows | None:
        path = view_parquet_path(self.prepared_root, self.view_key(domain_id, class_token, role))
        if not path.exists():
            return None
        connection = open_tabular_engine()
        cursor = connection.execute(f"SELECT * FROM read_parquet({sql_string(path.as_posix())})")
        columns = tuple(item[0] for item in cursor.description)
        rows = cursor.fetchall()
        if not rows:
            return None
        feature_indices = tuple(
            index for index, column in enumerate(columns) if column not in ("sample_id", "label")
        )
        sample_id_index = columns.index("sample_id")
        label_index = columns.index("label")
        return PreparedRows(
            sample_ids=tuple(str(row[sample_id_index]) for row in rows),
            features=tuple(tuple(float(row[index]) for index in feature_indices) for row in rows),
            labels=tuple(str(row[label_index]) for row in rows),
        )

    def tensor_view(
        self, rows: PreparedRows | None
    ) -> tuple[torch.Tensor, torch.Tensor, tuple[ArtifactDigest, ...]] | None:
        if rows is None:
            return None
        features = torch.tensor(rows.features, dtype=torch.float32)
        label_to_index = OrderedDict(
            (class_token, index) for index, class_token in enumerate(self.class_tokens)
        )
        labels = torch.tensor([label_to_index[label] for label in rows.labels], dtype=torch.long)
        return (features, labels, rows.sample_ids)

    def manifest_hash(self) -> ArtifactDigest:
        return dataset_manifest_hash(self.prepared_root)

    def evidence_available(self) -> PreparedEvidencePresent:
        return real_evidence_available(self.prepared_root)

    def feature_names(self) -> tuple[FeatureName, ...] | None:
        return prepared_feature_names(self.prepared_root)

    def supported_rows_for_role(self, domain_id: DomainId, role: Role) -> PreparedRows | None:
        combined_features: list[tuple[float, ...]] = []
        combined_labels: list[ClassLabel] = []
        combined_sample_ids: list[ArtifactDigest] = []
        for class_token in self.class_tokens:
            if class_token == self.target_class_token:
                continue
            rows = self.load_rows(domain_id, class_token, role)
            if rows is None:
                continue
            combined_features.extend(rows.features)
            combined_labels.extend(rows.labels)
            combined_sample_ids.extend(rows.sample_ids)
        if not combined_sample_ids:
            return None
        return PreparedRows(
            sample_ids=tuple(combined_sample_ids),
            features=tuple(combined_features),
            labels=tuple(combined_labels),
        )

    def anchor_train_feature_mean(self, domain_id: DomainId) -> torch.Tensor | None:
        combined_features: list[torch.Tensor] = []
        for class_token in self.class_tokens:
            if class_token == self.target_class_token:
                continue
            rows = self.tensor_view(self.load_rows(domain_id, class_token, Role.ANCHOR_TRAIN))
            if rows is not None:
                features, _labels, _sample_ids = rows
                combined_features.append(features)
        return None if not combined_features else torch.cat(combined_features, dim=0).mean(dim=0)


ATTACK_GENERATION_SEPARATOR = SeedNamespace.ATTACK_GENERATION.value


def fraction_to_attack_count(
    fraction: Probability, eligible_population_size: ExampleCount
) -> AttackCount:
    return math.floor(fraction * eligible_population_size)


def attack_row_order(
    eligible_row_ids: Sequence[ArtifactDigest], attack_generation_namespace_seed: NamespaceSeed
) -> tuple[ArtifactDigest, ...]:
    return deterministic_order(
        tuple(eligible_row_ids), ATTACK_GENERATION_SEPARATOR, attack_generation_namespace_seed
    )


def select_fractional_attack_rows(
    eligible_row_ids: Sequence[ArtifactDigest],
    fraction: Probability,
    attack_generation_namespace_seed: NamespaceSeed,
) -> tuple[ArtifactDigest, ...] | None:
    count = fraction_to_attack_count(fraction, len(eligible_row_ids))
    if fraction > 0.0 and count == 0:
        return None
    return attack_row_order(eligible_row_ids, attack_generation_namespace_seed)[:count]


def apply_trigger_transform(
    standardized_features: torch.Tensor,
    trigger_feature_indices: Sequence[FeatureIndex],
    trigger_value: TriggerFeatureValue,
) -> torch.Tensor:
    triggered = standardized_features.clone()
    for feature_index in trigger_feature_indices:
        triggered[..., feature_index] = trigger_value
    return triggered


def select_source_backdoor_poison_rows(
    eligible_gafgyt_udp_row_ids: Sequence[ArtifactDigest],
    poison_fraction: Probability,
    attack_generation_namespace_seed: NamespaceSeed,
) -> tuple[ArtifactDigest, ...] | None:
    return select_fractional_attack_rows(
        eligible_gafgyt_udp_row_ids, poison_fraction, attack_generation_namespace_seed
    )


def relabel_triggered_rows_as_benign(
    labels_by_row_id: Mapping[ArtifactDigest, DatasetClassToken],
    poisoned_row_ids: Sequence[ArtifactDigest],
    benign_class: DatasetClassToken,
) -> Mapping[ArtifactDigest, DatasetClassToken]:
    relabeled: OrderedDict[ArtifactDigest, DatasetClassToken] = OrderedDict(labels_by_row_id)
    for row_id in poisoned_row_ids:
        relabeled[row_id] = benign_class
    return relabeled


ROOT_CAUSE_SEPARATOR: SeedDerivationLabel = "CAPABILITY_ROOT_CAUSE"


def root_cause_for_sample(sample_id: SampleId) -> RootCause:
    digest = hashlib.sha256(framed_bytes(ROOT_CAUSE_SEPARATOR, sample_id)).digest()
    parity = int.from_bytes(digest[0:8], byteorder="big", signed=False) % 2
    return RootCause.A if parity == 0 else RootCause.B


def apply_root_cause_feature_shift(
    standardized_features: torch.Tensor,
    root_cause: RootCause,
    root_cause_a_feature_index: FeatureIndex,
    root_cause_b_feature_index: FeatureIndex,
    shift_value: StandardizedValue,
) -> torch.Tensor:
    shifted = standardized_features.clone()
    feature_index = (
        root_cause_a_feature_index if root_cause is RootCause.A else root_cause_b_feature_index
    )
    shifted[..., feature_index] = shifted[..., feature_index] + shift_value
    return shifted


def target_row_ids_for_contract(
    scope: CapabilityContractScope,
    root_cause_a_row_ids: frozenset[SampleId],
    root_cause_b_row_ids: frozenset[SampleId],
) -> frozenset[SampleId]:
    if scope is CapabilityContractScope.BROAD_TARGET_ONLY:
        return root_cause_a_row_ids | root_cause_b_row_ids
    if scope is CapabilityContractScope.ROOT_CAUSE_A_SCOPED:
        return root_cause_a_row_ids
    return root_cause_b_row_ids


def validate_excluded_root_cause_not_supported(
    scope: CapabilityContractScope,
    supported_row_ids: frozenset[SampleId],
    root_cause_a_row_ids: frozenset[SampleId],
    root_cause_b_row_ids: frozenset[SampleId],
) -> None:
    if scope is CapabilityContractScope.ROOT_CAUSE_A_SCOPED and not supported_row_ids.isdisjoint(
        root_cause_b_row_ids
    ):
        raise ValueError("the excluded root cause must never become a supported-control class")
    if scope is CapabilityContractScope.ROOT_CAUSE_B_SCOPED and not supported_row_ids.isdisjoint(
        root_cause_a_row_ids
    ):
        raise ValueError("the excluded root cause must never become a supported-control class")


def balanced_capability_selection(
    root_cause_a_row_ids: Sequence[SampleId],
    root_cause_b_row_ids: Sequence[SampleId],
    attack_generation_namespace_seed: NamespaceSeed,
) -> tuple[tuple[SampleId, ...], tuple[SampleId, ...]]:
    selected_count = min(len(root_cause_a_row_ids), len(root_cause_b_row_ids))
    separator = SeedNamespace.ATTACK_GENERATION.value
    ordered_a = deterministic_order(
        tuple(root_cause_a_row_ids), separator, attack_generation_namespace_seed
    )
    ordered_b = deterministic_order(
        tuple(root_cause_b_row_ids), separator, attack_generation_namespace_seed
    )
    return ordered_a[:selected_count], ordered_b[:selected_count]


def select_shared_label_error_rows(
    eligible_benign_row_ids: Sequence[ArtifactDigest],
    strength: Probability,
    attack_generation_namespace_seed: NamespaceSeed,
) -> tuple[ArtifactDigest, ...] | None:
    return select_fractional_attack_rows(
        eligible_benign_row_ids, strength, attack_generation_namespace_seed
    )


def relabel_shared_label_error_rows(
    labels_by_row_id: Mapping[ArtifactDigest, DatasetClassToken],
    selected_row_ids: Sequence[ArtifactDigest],
    target_class_token: DatasetClassToken,
) -> Mapping[ArtifactDigest, DatasetClassToken]:
    relabeled: OrderedDict[ArtifactDigest, DatasetClassToken] = OrderedDict(labels_by_row_id)
    for row_id in selected_row_ids:
        relabeled[row_id] = target_class_token
    return relabeled


def select_spurious_feature_rows(
    eligible_target_row_ids: Sequence[ArtifactDigest],
    strength: Probability,
    attack_generation_namespace_seed: NamespaceSeed,
) -> tuple[ArtifactDigest, ...] | None:
    return select_fractional_attack_rows(
        eligible_target_row_ids, strength, attack_generation_namespace_seed
    )


def apply_shared_spurious_feature(
    standardized_features: torch.Tensor,
    spurious_feature_index: FeatureIndex,
    trigger_value: TriggerFeatureValue,
) -> torch.Tensor:
    return apply_trigger_transform(standardized_features, [spurious_feature_index], trigger_value)


def apply_attacker_induced_common_context(
    standardized_features: torch.Tensor,
    trigger_feature_indices: Sequence[FeatureIndex],
    trigger_value: TriggerFeatureValue,
) -> torch.Tensor:
    return apply_trigger_transform(standardized_features, trigger_feature_indices, trigger_value)


QUANTITY_SKEW_SEPARATOR: SeedDerivationLabel = SeedNamespace.HETEROGENEITY.value


HETEROGENEITY_FEATURE_ORDER_SEPARATOR: SeedDerivationLabel = "HETEROGENEITY_FEATURE_ORDER"


HETEROGENEITY_FEATURE_SIGN_SEPARATOR: SeedDerivationLabel = "HETEROGENEITY_FEATURE_SIGN"


class DomainQuantitySkew(FrozenDomainModel):
    domain: DomainId
    multiplier: HeterogeneityMultiplier


def quantity_skew_multiplier_by_domain(
    adapter: DatasetAdapter,
    heterogeneity_namespace_seed: NamespaceSeed,
    multipliers: tuple[HeterogeneityMultiplier, ...],
) -> tuple[DomainQuantitySkew, ...]:
    domain_ids = adapter.domain_ids
    if len(multipliers) != len(domain_ids):
        raise ValueError("quantity-skew multiplier count must match the dataset domain count")
    ordered_domains = deterministic_domain_order(
        adapter,
        domain_ids,
        QUANTITY_SKEW_SEPARATOR,
        heterogeneity_namespace_seed,
    )
    return tuple(
        DomainQuantitySkew(domain=domain, multiplier=multiplier)
        for domain, multiplier in zip(ordered_domains, multipliers, strict=True)
    )


def exclude_source_from_quantity_skew(
    assignments: tuple[DomainQuantitySkew, ...],
    source_domain: DomainId,
) -> tuple[DomainQuantitySkew, ...]:
    return tuple(assignment for assignment in assignments if assignment.domain is not source_domain)


def quantity_skew_multiplier_for_domain(
    assignments: tuple[DomainQuantitySkew, ...],
    domain: DomainId,
) -> HeterogeneityMultiplier:
    for assignment in assignments:
        if assignment.domain == domain:
            return assignment.multiplier
    raise ValueError(f"no quantity-skew multiplier assigned to {domain}")


def apply_quantity_skew_to_cap(
    cap: SamplingCap,
    multiplier: HeterogeneityMultiplier,
) -> SamplingCap:
    return math.floor(cap * multiplier)


def select_heterogeneity_shift_features(
    all_feature_names: tuple[FeatureName, ...],
    heterogeneity_namespace_seed: NamespaceSeed,
    selected_feature_count: FeatureCount,
) -> tuple[FeatureName, ...]:
    ordered = deterministic_order(
        all_feature_names,
        HETEROGENEITY_FEATURE_ORDER_SEPARATOR,
        heterogeneity_namespace_seed,
    )
    return ordered[:selected_feature_count]


def feature_shift_sign(
    domain_token: DomainId,
    feature_name: FeatureName,
    heterogeneity_namespace_seed: NamespaceSeed,
) -> FeatureShiftSign:
    digest = hashlib.sha256(
        framed_bytes(
            HETEROGENEITY_FEATURE_SIGN_SEPARATOR,
            heterogeneity_namespace_seed,
            domain_token,
            feature_name,
        )
    ).digest()
    return 1 if digest[-1] & 1 else -1


@dataclass(frozen=True)
class RootCauseScope:
    contract_scope: CapabilityContractScope
    feature_names: tuple[FeatureName, ...]
    root_cause_a_feature_name: FeatureName
    root_cause_b_feature_name: FeatureName
    shift_value: TriggerFeatureValue
    balanced_selection_seed: DerivedSeed | None = None


@dataclass(frozen=True)
class BackdoorScope:
    attack_generation_seed: DerivedSeed
    poison_fraction: Probability
    trigger_feature_indices: tuple[FeatureIndex, ...]
    trigger_value: TriggerFeatureValue


@dataclass(frozen=True)
class HeterogeneityScope:
    heterogeneity_namespace_seed: DerivedSeed
    selected_feature_names: tuple[FeatureName, ...]
    feature_names: tuple[FeatureName, ...]
    shift_magnitude: TriggerFeatureValue


@dataclass(frozen=True)
class EpistemicFailureScope:
    failure_type: EpistemicFailureType
    strength: TriggerFeatureValue
    attack_generation_seed: DerivedSeed
    feature_names: tuple[FeatureName, ...]
    spurious_feature_name: FeatureName
    spurious_feature_value: TriggerFeatureValue
    common_context_feature_names: tuple[FeatureName, ...]
    common_context_trigger_value: TriggerFeatureValue


def poison_backdoor_rows(
    rows: PreparedRows, scope: BackdoorScope, benign_class_token: DatasetClassToken
) -> PreparedRows:
    poisoned_ids = select_source_backdoor_poison_rows(
        rows.sample_ids, scope.poison_fraction, scope.attack_generation_seed
    )
    if not poisoned_ids:
        return rows
    poisoned_id_set = frozenset(poisoned_ids)
    labels_by_row_id = OrderedDict(zip(rows.sample_ids, rows.labels, strict=True))
    relabeled = relabel_triggered_rows_as_benign(
        labels_by_row_id,
        poisoned_ids,
        benign_class_token,
    )
    kept_features: list[tuple[float, ...]] = []
    kept_labels: list[ClassLabel] = []
    for sample_id, features in zip(rows.sample_ids, rows.features, strict=True):
        if sample_id not in poisoned_id_set:
            kept_features.append(features)
            kept_labels.append(relabeled[sample_id])
            continue
        triggered = apply_trigger_transform(
            torch.tensor(features, dtype=torch.float32),
            scope.trigger_feature_indices,
            scope.trigger_value,
        )
        kept_features.append(tuple(float(value) for value in triggered))
        kept_labels.append(relabeled[sample_id])
    return PreparedRows(
        sample_ids=rows.sample_ids, features=tuple(kept_features), labels=tuple(kept_labels)
    )


def apply_heterogeneity_shift(
    rows: PreparedRows, domain_token: DomainId, scope: HeterogeneityScope
) -> PreparedRows:
    feature_indices_and_signs = tuple(
        (
            scope.feature_names.index(feature_name),
            feature_shift_sign(domain_token, feature_name, scope.heterogeneity_namespace_seed),
        )
        for feature_name in scope.selected_feature_names
    )
    shifted_features: list[tuple[float, ...]] = []
    for features in rows.features:
        tensor = torch.tensor(features, dtype=torch.float32)
        for feature_index, sign in feature_indices_and_signs:
            tensor[feature_index] = tensor[feature_index] + sign * scope.shift_magnitude
        shifted_features.append(tuple(float(value) for value in tensor))
    return PreparedRows(
        sample_ids=rows.sample_ids, features=tuple(shifted_features), labels=rows.labels
    )


def scope_and_shift_rows(
    rows: PreparedRows, root_cause_scope: RootCauseScope
) -> PreparedRows | None:
    root_cause_a_ids = frozenset(
        sample_id
        for sample_id in rows.sample_ids
        if root_cause_for_sample(sample_id) is RootCause.A
    )
    root_cause_b_ids = frozenset(rows.sample_ids) - root_cause_a_ids
    if root_cause_scope.balanced_selection_seed is not None:
        selected_a_ids, selected_b_ids = balanced_capability_selection(
            sorted(root_cause_a_ids),
            sorted(root_cause_b_ids),
            root_cause_scope.balanced_selection_seed,
        )
        root_cause_a_ids = frozenset(selected_a_ids)
        root_cause_b_ids = frozenset(selected_b_ids)
    allowed_ids = target_row_ids_for_contract(
        root_cause_scope.contract_scope, root_cause_a_ids, root_cause_b_ids
    )
    a_index = root_cause_scope.feature_names.index(root_cause_scope.root_cause_a_feature_name)
    b_index = root_cause_scope.feature_names.index(root_cause_scope.root_cause_b_feature_name)
    kept_sample_ids: list[ArtifactDigest] = []
    kept_features: list[tuple[float, ...]] = []
    kept_labels: list[ClassLabel] = []
    for sample_id, features, label in zip(rows.sample_ids, rows.features, rows.labels, strict=True):
        if sample_id not in allowed_ids:
            continue
        shifted = apply_root_cause_feature_shift(
            torch.tensor(features, dtype=torch.float32),
            root_cause_for_sample(sample_id),
            a_index,
            b_index,
            root_cause_scope.shift_value,
        )
        kept_sample_ids.append(sample_id)
        kept_features.append(tuple(float(value) for value in shifted))
        kept_labels.append(label)
    if not kept_sample_ids:
        return None
    return PreparedRows(
        sample_ids=tuple(kept_sample_ids), features=tuple(kept_features), labels=tuple(kept_labels)
    )


def relabel_shared_label_error_rows_for_scope(
    rows: PreparedRows, scope: EpistemicFailureScope, target_class_token: DatasetClassToken
) -> tuple[PreparedRows, tuple[BooleanValue, ...]]:
    selected = (
        select_shared_label_error_rows(
            rows.sample_ids, scope.strength, scope.attack_generation_seed
        )
        or ()
    )
    selected_ids = frozenset(selected)
    labels_by_row_id = OrderedDict(
        (sample_id, label) for sample_id, label in zip(rows.sample_ids, rows.labels, strict=True)
    )
    relabeled = relabel_shared_label_error_rows(labels_by_row_id, selected, target_class_token)
    return (
        PreparedRows(
            sample_ids=rows.sample_ids,
            features=rows.features,
            labels=tuple(relabeled[sample_id] for sample_id in rows.sample_ids),
        ),
        tuple(sample_id not in selected_ids for sample_id in rows.sample_ids),
    )


def mark_epistemic_rows(
    rows: PreparedRows,
    scope: EpistemicFailureScope,
    selected_ids: frozenset[ArtifactDigest],
) -> PreparedRows:
    if not selected_ids:
        return rows
    is_common_context = scope.failure_type is EpistemicFailureType.ATTACKER_INDUCED_COMMON_CONTEXT
    if is_common_context:
        feature_indices = tuple(
            scope.feature_names.index(name) for name in scope.common_context_feature_names
        )
        trigger_value = scope.common_context_trigger_value
    else:
        feature_indices = (scope.feature_names.index(scope.spurious_feature_name),)
        trigger_value = scope.spurious_feature_value
    marked_features: list[tuple[float, ...]] = []
    for sample_id, features in zip(rows.sample_ids, rows.features, strict=True):
        if sample_id not in selected_ids:
            marked_features.append(features)
            continue
        tensor = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
        shifted = (
            apply_attacker_induced_common_context(tensor, feature_indices, trigger_value)
            if is_common_context
            else apply_shared_spurious_feature(tensor, feature_indices[0], trigger_value)
        )
        marked_features.append(tuple(float(value) for value in shifted.squeeze(0)))
    return PreparedRows(
        sample_ids=rows.sample_ids, features=tuple(marked_features), labels=rows.labels
    )


def apply_epistemic_target_marker(rows: PreparedRows, scope: EpistemicFailureScope) -> PreparedRows:
    selected = (
        select_spurious_feature_rows(rows.sample_ids, scope.strength, scope.attack_generation_seed)
        or ()
    )
    return mark_epistemic_rows(rows, scope, frozenset(selected))
