import hashlib
import random
from collections.abc import Sequence

import numpy
import torch

from fedsira.domain.enums import SeedNamespace
from fedsira.domain.records import (
    UINT32_MODULUS,
    CanonicalToken,
    DerivedSeed,
    EpochIndex,
    MasterSeed,
    NamespaceSeed,
    RoundIndex,
)

NAMESPACE_SEED_PREFIX = "FedSIRA|seed_namespace|"
LOCAL_TRAINING_JOB_SEPARATOR = "LOCAL_TRAINING_JOB"
LOCAL_TRAINING_BATCH_ORDER_SEPARATOR = "LOCAL_TRAINING_BATCH_ORDER"


def canonical_bytes(*fields: CanonicalToken | int) -> bytes:
    encoded = bytearray()
    for field in fields:
        payload = str(field).encode("utf-8")
        encoded += len(payload).to_bytes(4, byteorder="big", signed=False)
        encoded += payload
    return bytes(encoded)


def namespace_seed(master_seed: MasterSeed, namespace: SeedNamespace) -> NamespaceSeed:
    message = f"{NAMESPACE_SEED_PREFIX}{master_seed}|{namespace.value}"
    digest = hashlib.sha256(message.encode("utf-8")).digest()
    return int.from_bytes(digest[0:8], byteorder="big", signed=False) % UINT32_MODULUS


def derive_uint32(
    separator: CanonicalToken, parent: int, *values: CanonicalToken | int
) -> DerivedSeed:
    digest = hashlib.sha256(canonical_bytes(separator, parent, *values)).digest()
    return int.from_bytes(digest[0:8], byteorder="big", signed=False) % UINT32_MODULUS


def local_training_seed(
    local_training_namespace_seed: NamespaceSeed,
    dataset_manifest_hash: CanonicalToken,
    start_checkpoint_identity: CanonicalToken,
    training_algorithm_token: CanonicalToken,
    domain_hash_token: CanonicalToken,
    scientific_training_condition_token: CanonicalToken,
    round_index_or_minus_one: RoundIndex,
) -> DerivedSeed:
    return derive_uint32(
        LOCAL_TRAINING_JOB_SEPARATOR,
        local_training_namespace_seed,
        dataset_manifest_hash,
        start_checkpoint_identity,
        training_algorithm_token,
        domain_hash_token,
        scientific_training_condition_token,
        round_index_or_minus_one,
    )


def deterministic_order(
    items: Sequence[CanonicalToken],
    domain_separator: CanonicalToken,
    order_namespace_seed: NamespaceSeed,
) -> tuple[CanonicalToken, ...]:
    def sort_key(item: CanonicalToken) -> tuple[bytes, CanonicalToken]:
        digest = hashlib.sha256(
            canonical_bytes(domain_separator, order_namespace_seed, item)
        ).digest()
        return (digest, item)

    return tuple(sorted(items, key=sort_key))


def minibatch_order(
    training_seed: DerivedSeed,
    epoch: EpochIndex,
    sample_ids: Sequence[CanonicalToken],
) -> tuple[CanonicalToken, ...]:
    def sort_key(sample_id: CanonicalToken) -> tuple[bytes, CanonicalToken]:
        digest = hashlib.sha256(
            canonical_bytes(LOCAL_TRAINING_BATCH_ORDER_SEPARATOR, training_seed, epoch, sample_id)
        ).digest()
        return (digest, sample_id)

    return tuple(sorted(sample_ids, key=sort_key))


def seed_job_local_rng_streams(seed: DerivedSeed) -> None:
    random.seed(seed)
    numpy.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
