from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from pydantic import Field, StringConstraints

UINT32_MODULUS = 4294967296

Probability = Annotated[float, Field(ge=0.0, le=1.0)]
Percentage = Annotated[float, Field(ge=0.0, le=100.0)]
NonNegativeInt = Annotated[int, Field(ge=0)]
PositiveInt = Annotated[int, Field(gt=0)]
NonNegativeFloat = Annotated[float, Field(ge=0.0)]
PositiveFloat = Annotated[float, Field(gt=0.0)]
NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
Uint32Bound = Annotated[int, Field(ge=0, lt=UINT32_MODULUS)]

ExperimentId = Annotated[str, StringConstraints(min_length=1, pattern=r"^[a-z][a-z0-9-]*$")]
ArtifactDigest = Annotated[
    str, StringConstraints(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
]
MasterSeed = Uint32Bound
NamespaceSeed = Uint32Bound
DerivedSeed = Uint32Bound
CanonicalToken = NonEmptyString
RoundIndex = Annotated[int, Field(ge=-1)]
EpochIndex = NonNegativeInt
RetryCount = NonNegativeInt
FailureMessage = NonEmptyString


@dataclass(frozen=True)
class SeedBundle:
    master_seeds: tuple[MasterSeed, ...]
    analysis_seed: MasterSeed
    smoke_seed: MasterSeed

    def __post_init__(self) -> None:
        if len(self.master_seeds) == 0:
            raise ValueError("master_seeds must not be empty")
        if len(set(self.master_seeds)) != len(self.master_seeds):
            raise ValueError("master_seeds must not contain duplicates")
        for seed in (*self.master_seeds, self.analysis_seed, self.smoke_seed):
            if not (0 <= seed < UINT32_MODULUS):
                raise ValueError(f"seed {seed} outside uint32 range")

    @property
    def confirmatory_seed_count(self) -> int:
        return len(self.master_seeds)
