import hashlib
from typing import Annotated

from pydantic import Field

from fedsira.domain.types import (
    UINT32_MODULUS,
    ClassLabel,
    DatasetFileDigest,
    DerivedSeed,
    DomainId,
    RoleToken,
    SamplingCap,
    SourceRowIndex,
)
from fedsira.runtime.determinism import framed_bytes

SamplingSelectionDigest = Annotated[bytes, Field(min_length=32, max_length=32)]

PREPROCESSING_SAMPLE_ORDER_SEED: DerivedSeed = (
    int.from_bytes(
        hashlib.sha256(b"FedSIRA|preprocess_sample_order|1").digest()[0:8], byteorder="big"
    )
    % UINT32_MODULUS
)


def sampling_cap_selection_digest(
    dataset_file_sha256: DatasetFileDigest,
    domain_hash_token: DomainId,
    class_id: ClassLabel,
    role_hash_token: RoleToken,
    original_row_index: SourceRowIndex,
) -> SamplingSelectionDigest:
    return hashlib.sha256(
        framed_bytes(
            dataset_file_sha256,
            domain_hash_token,
            class_id,
            role_hash_token,
            original_row_index,
            PREPROCESSING_SAMPLE_ORDER_SEED,
        )
    ).digest()


def apply_sampling_cap(
    dataset_file_sha256: DatasetFileDigest,
    domain_hash_token: DomainId,
    class_id: ClassLabel,
    role_hash_token: RoleToken,
    original_row_indices: tuple[SourceRowIndex, ...],
    cap: SamplingCap,
) -> tuple[SourceRowIndex, ...]:
    if len(original_row_indices) <= cap:
        return original_row_indices

    def sort_key(
        original_row_index: SourceRowIndex,
    ) -> tuple[SamplingSelectionDigest, SourceRowIndex]:
        digest = sampling_cap_selection_digest(
            dataset_file_sha256,
            domain_hash_token,
            class_id,
            role_hash_token,
            original_row_index,
        )
        return digest, original_row_index

    ordered = sorted(original_row_indices, key=sort_key)
    return tuple(ordered[:cap])
