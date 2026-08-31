import pytest
from pydantic import ValidationError

from fedsira.domain.types import SeedBundle


def test_seed_bundle_confirmatory_seed_count_matches_master_seed_length() -> None:
    bundle = SeedBundle(master_seeds=(1, 2, 3), analysis_seed=100, smoke_seed=200)
    assert bundle.confirmatory_seed_count == 3


def test_seed_bundle_rejects_empty_master_seeds() -> None:
    with pytest.raises(ValidationError):
        SeedBundle(master_seeds=(), analysis_seed=1, smoke_seed=2)


def test_seed_bundle_rejects_duplicate_master_seeds() -> None:
    with pytest.raises(ValidationError):
        SeedBundle(master_seeds=(1, 1), analysis_seed=2, smoke_seed=3)


def test_seed_bundle_rejects_out_of_range_seed() -> None:
    with pytest.raises(ValidationError):
        SeedBundle(master_seeds=(1,), analysis_seed=2, smoke_seed=2**32)


def test_seed_bundle_is_frozen() -> None:
    bundle = SeedBundle(master_seeds=(1,), analysis_seed=2, smoke_seed=3)
    with pytest.raises(ValidationError):
        setattr(bundle, "analysis_seed", 5)
