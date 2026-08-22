import hashlib
from collections.abc import Sequence

from fedsira.domain.records import (
    UINT32_MODULUS,
    ArtifactDigest,
    CanonicalToken,
    DerivedSeed,
    NonNegativeInt,
)
from fedsira.runtime.determinism import canonical_bytes

PREPROCESSING_SAMPLE_ORDER_SEED: DerivedSeed = (
    int.from_bytes(
        hashlib.sha256(b"FedSIRA|preprocess_sample_order|1").digest()[0:8], byteorder="big"
    )
    % UINT32_MODULUS
)


def sampling_cap_selection_digest(
    dataset_file_sha256: ArtifactDigest,
    domain_hash_token: CanonicalToken,
    class_id: CanonicalToken,
    role_hash_token: CanonicalToken,
    original_row_index: NonNegativeInt,
) -> bytes:
    return hashlib.sha256(
        canonical_bytes(
            dataset_file_sha256,
            domain_hash_token,
            class_id,
            role_hash_token,
            original_row_index,
            PREPROCESSING_SAMPLE_ORDER_SEED,
        )
    ).digest()


def apply_sampling_cap(
    dataset_file_sha256: ArtifactDigest,
    domain_hash_token: CanonicalToken,
    class_id: CanonicalToken,
    role_hash_token: CanonicalToken,
    original_row_indices: Sequence[NonNegativeInt],
    cap: NonNegativeInt,
) -> tuple[NonNegativeInt, ...]:
    if len(original_row_indices) <= cap:
        return tuple(original_row_indices)

    def sort_key(original_row_index: NonNegativeInt) -> tuple[bytes, NonNegativeInt]:
        digest = sampling_cap_selection_digest(
            dataset_file_sha256, domain_hash_token, class_id, role_hash_token, original_row_index
        )
        return (digest, original_row_index)

    ordered = sorted(original_row_indices, key=sort_key)
    return tuple(ordered[:cap])
