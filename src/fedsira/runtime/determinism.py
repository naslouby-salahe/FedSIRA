import hashlib
import random
from typing import Annotated, Protocol, TypeVar, cast

import numpy
import torch
from pydantic import Field

from fedsira.domain.enums import SeedNamespace
from fedsira.domain.records import (
    UINT32_MODULUS,
    AlgorithmName,
    CheckpointIdentity,
    DatasetManifestDigest,
    DerivedSeed,
    DeterministicInteger,
    DomainId,
    EpochIndex,
    FramingField,
    MasterSeed,
    NamespaceSeed,
    RoundIndex,
    SampleId,
    SeedDerivationLabel,
    TextValue,
    TrainingConditionId,
)

NAMESPACE_SEED_PREFIX = "FedSIRA|seed_namespace|"
LOCAL_TRAINING_JOB_SEPARATOR: SeedDerivationLabel = "LOCAL_TRAINING_JOB"
LOCAL_TRAINING_BATCH_ORDER_SEPARATOR: SeedDerivationLabel = "LOCAL_TRAINING_BATCH_ORDER"

FramedBytes = Annotated[bytes, Field()]
DigestBytes = Annotated[bytes, Field(min_length=32, max_length=32)]
OrderItem = TypeVar("OrderItem")


class _TorchSeedFunction(Protocol):
    def __call__(self, seed: DeterministicInteger) -> None: ...


_TORCH_MANUAL_SEED = cast(_TorchSeedFunction, torch.manual_seed)
_TORCH_CUDA_MANUAL_SEED_ALL = cast(_TorchSeedFunction, torch.cuda.manual_seed_all)


def framed_bytes(*fields: FramingField) -> FramedBytes:
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
    separator: SeedDerivationLabel,
    parent: DeterministicInteger,
    *values: FramingField,
) -> DerivedSeed:
    digest = hashlib.sha256(framed_bytes(separator, parent, *values)).digest()
    return int.from_bytes(digest[0:8], byteorder="big", signed=False) % UINT32_MODULUS


def local_training_seed(
    local_training_namespace_seed: NamespaceSeed,
    dataset_manifest_hash: DatasetManifestDigest,
    start_checkpoint_identity: CheckpointIdentity,
    training_algorithm_token: AlgorithmName,
    domain_hash_token: DomainId,
    scientific_training_condition_token: TrainingConditionId,
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
    items: tuple[OrderItem, ...],
    domain_separator: SeedDerivationLabel,
    order_namespace_seed: NamespaceSeed,
) -> tuple[OrderItem, ...]:
    def sort_key(item: OrderItem) -> tuple[DigestBytes, TextValue]:
        item_text: TextValue = str(item)
        digest: DigestBytes = hashlib.sha256(
            framed_bytes(domain_separator, order_namespace_seed, item_text)
        ).digest()
        return digest, item_text

    return tuple(sorted(items, key=sort_key))


def minibatch_order(
    training_seed: DerivedSeed,
    epoch: EpochIndex,
    sample_ids: tuple[SampleId, ...],
) -> tuple[SampleId, ...]:
    def sort_key(sample_id: SampleId) -> tuple[DigestBytes, SampleId]:
        digest: DigestBytes = hashlib.sha256(
            framed_bytes(LOCAL_TRAINING_BATCH_ORDER_SEPARATOR, training_seed, epoch, sample_id)
        ).digest()
        return digest, sample_id

    return tuple(sorted(sample_ids, key=sort_key))


def seed_job_local_rng_streams(seed: DerivedSeed) -> None:
    random.seed(int(seed))
    numpy.random.seed(int(seed))
    _TORCH_MANUAL_SEED(seed)
    _TORCH_CUDA_MANUAL_SEED_ALL(seed)
