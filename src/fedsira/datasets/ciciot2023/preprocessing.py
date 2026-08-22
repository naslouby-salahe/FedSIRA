import hashlib

import pandas

from fedsira.config.schema import RoleIntervals
from fedsira.datasets.ciciot2023.schema import (
    ROW_IDENTIFIER_CANONICAL_TOKENS,
    TARGET_LABEL,
    canonicalize_token,
    hash_to_pseudo_domain,
    is_row_identifier_column,
)
from fedsira.datasets.common import Role, role_for_normalized_position
from fedsira.datasets.roles import supported_role_windows, target_role_windows
from fedsira.domain.records import ArtifactDigest, CanonicalToken, NonNegativeInt, PositiveInt
from fedsira.runtime.determinism import canonical_bytes

STABLE_ROW_ID_PREFIX = "CICIOT2023_SAMPLE_ID_V1"


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
    header: tuple[CanonicalToken, ...], label_column: CanonicalToken, sample: pandas.DataFrame
) -> tuple[CanonicalToken, ...]:
    predictors: list[CanonicalToken] = []
    for column in header:
        if column == label_column:
            continue
        canonical = canonicalize_token(column)
        if canonical in ROW_IDENTIFIER_CANONICAL_TOKENS:
            values = tuple(int(value) for value in sample[column])
            if is_row_identifier_column(canonical, values):
                continue
        predictors.append(column)
    return tuple(predictors)


def assign_pseudo_domains(
    dataset_manifest_hash: ArtifactDigest,
    canonical_label: CanonicalToken,
    stable_row_ids: tuple[ArtifactDigest, ...],
    pseudo_domain_partition_salt: PositiveInt,
) -> tuple[NonNegativeInt, ...]:
    return tuple(
        hash_to_pseudo_domain(
            dataset_manifest_hash, canonical_label, stable_row_id, pseudo_domain_partition_salt
        )
        for stable_row_id in stable_row_ids
    )


def order_group_by_stable_row_id(
    stable_row_ids: tuple[ArtifactDigest, ...],
) -> tuple[ArtifactDigest, ...]:
    return tuple(sorted(stable_row_ids))


def assign_group_local_roles(
    canonical_label: CanonicalToken,
    stable_row_ids_ascending: tuple[ArtifactDigest, ...],
    role_intervals: RoleIntervals,
) -> tuple[Role | None, ...]:
    is_target = canonical_label == TARGET_LABEL
    windows = (
        target_role_windows(role_intervals) if is_target else supported_role_windows(role_intervals)
    )
    group_size = len(stable_row_ids_ascending)
    return tuple(
        role_for_normalized_position(group_local_index / group_size, windows)
        for group_local_index in range(group_size)
    )
