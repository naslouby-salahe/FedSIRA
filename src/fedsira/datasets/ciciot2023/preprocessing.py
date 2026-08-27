from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from dataclasses import dataclass

from fedsira.config.schema import RoleIntervals, SamplingCapsPerDomain
from fedsira.datasets.ciciot2023.schema import (
    BENIGN_LABEL,
    TARGET_LABEL,
    CICIoT2023PseudoDomain,
    canonicalize_label,
    hash_to_pseudo_domain,
)
from fedsira.datasets.common import (
    ROLE_HASH_TOKEN,
    DatasetExclusionReason,
    Role,
    role_for_normalized_position,
)
from fedsira.datasets.roles import supported_role_windows, target_role_windows
from fedsira.datasets.sampling import PREPROCESSING_SAMPLE_ORDER_SEED
from fedsira.domain.records import ArtifactDigest, CanonicalToken, NonNegativeInt, PositiveInt
from fedsira.runtime.determinism import canonical_bytes

STABLE_ROW_ID_PREFIX = "CICIOT2023_SAMPLE_ID_V1"


@dataclass(frozen=True)
class SecondaryRawRow:
    original_row_index: NonNegativeInt
    values: tuple[str, ...]


@dataclass(frozen=True)
class SecondaryRetainedRow:
    stable_row_id: ArtifactDigest
    file_sha256: ArtifactDigest
    relative_path: CanonicalToken
    original_row_index: NonNegativeInt
    canonical_label: CanonicalToken
    pseudo_domain: CICIoT2023PseudoDomain
    features: tuple[float, ...]


@dataclass(frozen=True)
class SecondaryExcludedRow:
    stable_row_id: ArtifactDigest
    file_sha256: ArtifactDigest
    relative_path: CanonicalToken
    original_row_index: NonNegativeInt
    reason: DatasetExclusionReason


@dataclass(frozen=True)
class SecondaryRoleAssignment:
    stable_row_id: ArtifactDigest
    canonical_label: CanonicalToken
    pseudo_domain: CICIoT2023PseudoDomain
    role: Role


def compute_stable_row_id(
    normalized_relative_csv_path: CanonicalToken,
    file_sha256: ArtifactDigest,
    zero_based_original_row_index: NonNegativeInt,
) -> ArtifactDigest:
    return hashlib.sha256(
        canonical_bytes(
            STABLE_ROW_ID_PREFIX,
            normalized_relative_csv_path,
            file_sha256,
            zero_based_original_row_index,
        )
    ).hexdigest()


def resolve_predictor_columns(
    header: tuple[CanonicalToken, ...],
    label_column: CanonicalToken,
    row_identifier_columns: frozenset[CanonicalToken] = frozenset(),
) -> tuple[CanonicalToken, ...]:
    predictors = tuple(
        column
        for column in header
        if column != label_column and column not in row_identifier_columns
    )
    if not predictors:
        raise ValueError("CICIoT2023 resolved no predictor columns")
    if len(set(predictors)) != len(predictors):
        raise ValueError("CICIoT2023 predictor schema contains duplicate names")
    return predictors


def parse_complete_case_rows(
    raw_rows: Sequence[SecondaryRawRow],
    *,
    header: tuple[CanonicalToken, ...],
    relative_path: CanonicalToken,
    file_sha256: ArtifactDigest,
    label_column: CanonicalToken,
    predictor_columns: tuple[CanonicalToken, ...],
    dataset_manifest_hash: ArtifactDigest,
    pseudo_domain_partition_salt: PositiveInt,
) -> tuple[tuple[SecondaryRetainedRow, ...], tuple[SecondaryExcludedRow, ...]]:
    column_index = {column: index for index, column in enumerate(header)}
    if len(column_index) != len(header):
        raise ValueError("CICIoT2023 header contains duplicate column names")
    try:
        label_index = column_index[label_column]
        predictor_indices = tuple(column_index[column] for column in predictor_columns)
    except KeyError as error:
        raise ValueError(f"CICIoT2023 column missing from validated header: {error.args[0]}") from error

    retained: list[SecondaryRetainedRow] = []
    excluded: list[SecondaryExcludedRow] = []
    for raw_row in raw_rows:
        if len(raw_row.values) != len(header):
            raise ValueError(
                "CICIoT2023 row width does not match the validated header: "
                f"row={raw_row.original_row_index}, expected={len(header)}, "
                f"observed={len(raw_row.values)}"
            )
        stable_row_id = compute_stable_row_id(
            relative_path,
            file_sha256,
            raw_row.original_row_index,
        )
        try:
            features = tuple(float(raw_row.values[index]) for index in predictor_indices)
        except ValueError:
            excluded.append(
                SecondaryExcludedRow(
                    stable_row_id=stable_row_id,
                    file_sha256=file_sha256,
                    relative_path=relative_path,
                    original_row_index=raw_row.original_row_index,
                    reason=DatasetExclusionReason.UNPARSEABLE_PREDICTOR,
                )
            )
            continue
        if any(not math.isfinite(value) for value in features):
            excluded.append(
                SecondaryExcludedRow(
                    stable_row_id=stable_row_id,
                    file_sha256=file_sha256,
                    relative_path=relative_path,
                    original_row_index=raw_row.original_row_index,
                    reason=DatasetExclusionReason.NON_FINITE_PREDICTOR,
                )
            )
            continue
        canonical_label = canonicalize_label(raw_row.values[label_index])
        pseudo_domain = hash_to_pseudo_domain(
            dataset_manifest_hash,
            canonical_label,
            stable_row_id,
            pseudo_domain_partition_salt,
        )
        retained.append(
            SecondaryRetainedRow(
                stable_row_id=stable_row_id,
                file_sha256=file_sha256,
                relative_path=relative_path,
                original_row_index=raw_row.original_row_index,
                canonical_label=canonical_label,
                pseudo_domain=pseudo_domain,
                features=features,
            )
        )
    return tuple(retained), tuple(excluded)


def assign_pseudo_domains(
    dataset_manifest_hash: ArtifactDigest,
    canonical_label: CanonicalToken,
    stable_row_ids: tuple[ArtifactDigest, ...],
    pseudo_domain_partition_salt: PositiveInt,
) -> tuple[CICIoT2023PseudoDomain, ...]:
    return tuple(
        hash_to_pseudo_domain(
            dataset_manifest_hash,
            canonical_label,
            stable_row_id,
            pseudo_domain_partition_salt,
        )
        for stable_row_id in stable_row_ids
    )


def order_group_by_stable_row_id(
    stable_row_ids: tuple[ArtifactDigest, ...],
) -> tuple[ArtifactDigest, ...]:
    return tuple(sorted(stable_row_ids, key=bytes.fromhex))


def assign_group_local_roles(
    canonical_label: CanonicalToken,
    stable_row_ids_ascending: tuple[ArtifactDigest, ...],
    role_intervals: RoleIntervals,
) -> tuple[Role | None, ...]:
    if tuple(stable_row_ids_ascending) != order_group_by_stable_row_id(stable_row_ids_ascending):
        raise ValueError(
            "CICIoT2023 group rows must be ordered by stable_row_id before role assignment"
        )
    windows = (
        target_role_windows(role_intervals)
        if canonical_label == TARGET_LABEL
        else supported_role_windows(role_intervals)
    )
    group_size = len(stable_row_ids_ascending)
    if group_size == 0:
        return ()
    return tuple(
        role_for_normalized_position(group_local_index / group_size, windows)
        for group_local_index in range(group_size)
    )


def sampling_cap_for_secondary_role(
    caps: SamplingCapsPerDomain,
    canonical_label: CanonicalToken,
    role: Role,
) -> NonNegativeInt | None:
    if canonical_label == TARGET_LABEL:
        target_caps: dict[Role, NonNegativeInt | None] = {
            Role.SOURCE_PROPOSAL: caps.source_proposal_target,
            Role.CANDIDATE_SCREEN: caps.candidate_screen_target,
            Role.REPRODUCTION: caps.reproduction_target,
            Role.ROW_VERIFICATION: caps.row_verification_target,
            Role.FINAL_GATE: caps.final_gate_target,
            Role.REPORT_TEST: caps.report_test_target,
        }
        return target_caps.get(role)
    report_cap = (
        caps.report_test_benign
        if canonical_label == BENIGN_LABEL
        else caps.report_test_other_supported_per_class
    )
    supported_caps: dict[Role, NonNegativeInt | None] = {
        Role.ANCHOR_TRAIN: caps.anchor_train_per_supported_class,
        Role.ANCHOR_VALIDATION: caps.anchor_validation_per_supported_class,
        Role.POST_REFERENCE_REPLAY: None,
        Role.ROW_VERIFICATION: caps.row_verification_supported_per_supported_class,
        Role.FINAL_GATE: caps.final_gate_supported_per_supported_class,
        Role.REPORT_TEST: report_cap,
    }
    return supported_caps.get(role)


def secondary_sampling_selection_key(
    dataset_manifest_hash: ArtifactDigest,
    canonical_label: CanonicalToken,
    pseudo_domain: CICIoT2023PseudoDomain,
    role: Role,
    stable_row_id: ArtifactDigest,
) -> tuple[bytes, ArtifactDigest]:
    digest = hashlib.sha256(
        canonical_bytes(
            dataset_manifest_hash,
            pseudo_domain.display_token,
            canonical_label,
            ROLE_HASH_TOKEN[role],
            stable_row_id,
            PREPROCESSING_SAMPLE_ORDER_SEED,
        )
    ).digest()
    return digest, stable_row_id


def apply_secondary_sampling_cap(
    dataset_manifest_hash: ArtifactDigest,
    canonical_label: CanonicalToken,
    pseudo_domain: CICIoT2023PseudoDomain,
    role: Role,
    stable_row_ids: tuple[ArtifactDigest, ...],
    cap: NonNegativeInt | None,
) -> tuple[ArtifactDigest, ...]:
    if cap is None or len(stable_row_ids) <= cap:
        return stable_row_ids
    return tuple(
        sorted(
            stable_row_ids,
            key=lambda stable_row_id: secondary_sampling_selection_key(
                dataset_manifest_hash,
                canonical_label,
                pseudo_domain,
                role,
                stable_row_id,
            ),
        )[:cap]
    )


def assign_secondary_roles(
    rows: Sequence[SecondaryRetainedRow],
    role_intervals: RoleIntervals,
    sampling_caps: SamplingCapsPerDomain,
    dataset_manifest_hash: ArtifactDigest,
) -> tuple[SecondaryRoleAssignment, ...]:
    rows_by_group: dict[
        tuple[CanonicalToken, CICIoT2023PseudoDomain], list[SecondaryRetainedRow]
    ] = {}
    for row in rows:
        rows_by_group.setdefault((row.canonical_label, row.pseudo_domain), []).append(row)

    assignments: list[SecondaryRoleAssignment] = []
    for (canonical_label, pseudo_domain), group_rows in sorted(
        rows_by_group.items(),
        key=lambda item: (item[0][0], int(item[0][1])),
    ):
        ordered_rows = sorted(group_rows, key=lambda row: bytes.fromhex(row.stable_row_id))
        stable_row_ids = tuple(row.stable_row_id for row in ordered_rows)
        roles = assign_group_local_roles(canonical_label, stable_row_ids, role_intervals)
        ids_by_role: dict[Role, list[ArtifactDigest]] = {}
        for stable_row_id, role in zip(stable_row_ids, roles, strict=True):
            if role is not None:
                ids_by_role.setdefault(role, []).append(stable_row_id)
        for role, role_ids in ids_by_role.items():
            selected_ids = apply_secondary_sampling_cap(
                dataset_manifest_hash,
                canonical_label,
                pseudo_domain,
                role,
                tuple(role_ids),
                sampling_cap_for_secondary_role(sampling_caps, canonical_label, role),
            )
            assignments.extend(
                SecondaryRoleAssignment(
                    stable_row_id=stable_row_id,
                    canonical_label=canonical_label,
                    pseudo_domain=pseudo_domain,
                    role=role,
                )
                for stable_row_id in selected_ids
            )
    return tuple(assignments)
