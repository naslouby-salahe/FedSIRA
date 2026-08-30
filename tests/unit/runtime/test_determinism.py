import hashlib

import numpy
import torch

from fedsira.domain.enums import SeedNamespace
from fedsira.runtime.determinism import (
    derive_uint32,
    deterministic_order,
    framed_bytes,
    local_training_seed,
    minibatch_order,
    namespace_seed,
    seed_job_local_rng_streams,
)


def test_namespace_seed_matches_manual_reference_computation() -> None:
    master_seed = 1103
    namespace = SeedNamespace.DATA_SPLIT
    message = f"FedSIRA|seed_namespace|{master_seed}|{namespace.value}"
    digest = hashlib.sha256(message.encode("utf-8")).digest()
    expected = int.from_bytes(digest[0:8], byteorder="big", signed=False) % 4294967296
    assert namespace_seed(master_seed, namespace) == expected


def test_namespace_seed_is_deterministic() -> None:
    first = namespace_seed(1217, SeedNamespace.MODEL_INITIALIZATION)
    second = namespace_seed(1217, SeedNamespace.MODEL_INITIALIZATION)
    assert first == second


def test_namespace_seed_differs_across_namespaces() -> None:
    first = namespace_seed(1103, SeedNamespace.DATA_SPLIT)
    second = namespace_seed(1103, SeedNamespace.DOMAIN_PARTITION)
    assert first != second


def test_namespace_seed_differs_across_master_seeds() -> None:
    first = namespace_seed(1103, SeedNamespace.DATA_SPLIT)
    second = namespace_seed(1217, SeedNamespace.DATA_SPLIT)
    assert first != second


def test_framed_bytes_is_length_prefixed_and_unambiguous() -> None:
    left = framed_bytes("ab", "c")
    right = framed_bytes("a", "bc")
    assert left != right


def test_derive_uint32_is_deterministic() -> None:
    first = derive_uint32("SEPARATOR", 1, "a", "b", 3)
    second = derive_uint32("SEPARATOR", 1, "a", "b", 3)
    assert first == second


def test_derive_uint32_changes_with_any_field() -> None:
    baseline = derive_uint32("SEPARATOR", 1, "a", "b", 3)
    assert derive_uint32("SEPARATOR", 2, "a", "b", 3) != baseline
    assert derive_uint32("SEPARATOR", 1, "a", "b", 4) != baseline
    assert derive_uint32("OTHER", 1, "a", "b", 3) != baseline


def test_local_training_seed_is_deterministic() -> None:
    first = local_training_seed(42, "a" * 64, "checkpoint-1", "fedavg", "domain-1", "clean", -1)
    second = local_training_seed(42, "a" * 64, "checkpoint-1", "fedavg", "domain-1", "clean", -1)
    assert first == second


def test_deterministic_order_is_a_stable_permutation() -> None:
    items = ("client-3", "client-1", "client-2")
    ordered_once = deterministic_order(items, "SOURCE_ORDER", 7)
    ordered_twice = deterministic_order(items, "SOURCE_ORDER", 7)
    assert ordered_once == ordered_twice
    assert set(ordered_once) == set(items)


def test_deterministic_order_changes_with_namespace_seed() -> None:
    items = tuple(f"item-{index}" for index in range(20))
    ordered_a = deterministic_order(items, "SOURCE_ORDER", 1)
    ordered_b = deterministic_order(items, "SOURCE_ORDER", 2)
    assert ordered_a != ordered_b


def test_minibatch_order_is_deterministic_per_epoch() -> None:
    sample_ids = tuple(f"sample-{index}" for index in range(10))
    first = minibatch_order(999, 0, sample_ids)
    second = minibatch_order(999, 0, sample_ids)
    assert first == second
    assert set(first) == set(sample_ids)


def test_minibatch_order_differs_across_epochs() -> None:
    sample_ids = tuple(f"sample-{index}" for index in range(10))
    epoch_zero = minibatch_order(999, 0, sample_ids)
    epoch_one = minibatch_order(999, 1, sample_ids)
    assert epoch_zero != epoch_one


def test_seed_job_local_rng_streams_makes_python_random_reproducible() -> None:
    import random

    seed_job_local_rng_streams(123)
    first = [random.random() for _ in range(5)]
    seed_job_local_rng_streams(123)
    second = [random.random() for _ in range(5)]
    assert first == second


def test_seed_job_local_rng_streams_makes_numpy_reproducible() -> None:
    seed_job_local_rng_streams(123)
    first = numpy.random.rand(5).tolist()
    seed_job_local_rng_streams(123)
    second = numpy.random.rand(5).tolist()
    assert first == second


def test_seed_job_local_rng_streams_makes_torch_reproducible() -> None:
    seed_job_local_rng_streams(123)
    first = torch.rand(5)
    seed_job_local_rng_streams(123)
    second = torch.rand(5)
    assert torch.equal(first, second)
