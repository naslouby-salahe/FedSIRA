from __future__ import annotations

from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

UINT32_MODULUS = 4294967296

Probability = Annotated[float, Field(ge=0.0, le=1.0)]
Percentage = Annotated[float, Field(ge=0.0, le=100.0)]
NonNegativeInt = Annotated[int, Field(ge=0)]
PositiveInt = Annotated[int, Field(gt=0)]
NonNegativeFloat = Annotated[float, Field(ge=0.0)]
PositiveFloat = Annotated[float, Field(gt=0.0)]
FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]
BooleanFlag = Annotated[bool, Field()]
NonEmptyString = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
Uint32Bound = Annotated[int, Field(ge=0, lt=UINT32_MODULUS)]

ExperimentSlug = Annotated[str, StringConstraints(min_length=1, pattern=r"^[a-z][a-z0-9-]*$")]
ArtifactDigest = Annotated[
    str, StringConstraints(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
]
MasterSeed = Uint32Bound
NamespaceSeed = Uint32Bound
DerivedSeed = Uint32Bound
CanonicalToken = NonEmptyString
ExperimentName = CanonicalToken
DomainId = CanonicalToken
DatasetClassToken = CanonicalToken
RepositoryPath = NonEmptyString
Doi = NonEmptyString
RoundIndex = Annotated[int, Field(ge=-1)]
EpochIndex = NonNegativeInt
RetryCount = NonNegativeInt
FailureMessage = NonEmptyString

RowCount = NonNegativeInt
ExampleCount = NonNegativeInt
MinimumExampleCount = PositiveInt
DomainCount = PositiveInt
ClassCount = PositiveInt
FeatureCount = PositiveInt
ScreenDomainCount = PositiveInt
VerifierCount = PositiveInt
CommitteeSize = PositiveInt
ReproductionRowCount = NonNegativeInt
CompromisedReproducerCount = PositiveInt
ScientificCellCount = NonNegativeInt
LogicalEvidenceCycleCount = PositiveInt
EvidenceCycleIndex = NonNegativeInt
FoldCount = PositiveInt
MatchedControlCount = PositiveInt
LocalEpochCount = PositiveInt
FederatedRoundCount = PositiveInt
BatchSize = PositiveInt
CadenceRounds = PositiveInt
GroupCount = PositiveInt
BootstrapResampleCount = PositiveInt
DecimalPlaces = NonNegativeInt
SignificantDigits = PositiveInt
WorkerCount = NonNegativeInt
TimeoutSeconds = PositiveInt
WarmupPassCount = NonNegativeInt
AdmissionCount = NonNegativeInt
HashModulus = PositiveInt
UciDatasetId = PositiveInt
SeedCount = PositiveInt
PredictorCount = PositiveInt
PartitionSalt = Uint32Bound
TrimCount = NonNegativeInt
ClusterSize = PositiveInt
CommittedRowCount = PositiveInt
MinimumCompletePairCount = PositiveInt
ConfigFormatVersion = PositiveInt

StandardizedValue = FiniteFloat
MetricDifference = FiniteFloat
LearningRate = PositiveFloat
OptimizerEpsilon = PositiveFloat
NumericalEpsilon = PositiveFloat
WeightDecay = NonNegativeFloat
GradientL2Clip = PositiveFloat
Temperature = PositiveFloat
LossWeight = NonNegativeFloat
RegularizationWeight = NonNegativeFloat
DifferentialNatsPerExample = NonNegativeFloat
ScaleFactor = PositiveFloat
DeltaScale = PositiveFloat
MetricTolerance = PositiveFloat
PValueDisplayFloor = PositiveFloat
DbscanEpsilon = PositiveFloat
ProductionWeight = NonNegativeFloat
KrumScore = NonNegativeFloat

PoisonFraction = Probability
ClientDropout = Probability
TargetF1 = Probability
TargetF1Gain = Probability
SupportedMacroF1Drop = Probability
BenignFalseAlarmRateIncrease = Probability
ContaminationRisk = Probability
ConfidenceLevel = Probability
FamilyWiseAlpha = Probability
CosineSimilarity = Probability
HeterogeneityMultiplier = Probability

PinMemoryEnabled = BooleanFlag
PersistentWorkersEnabled = BooleanFlag
PredictorCountMatchesOfficial = BooleanFlag
SourceCommitted = BooleanFlag
EvidenceAdequate = BooleanFlag
OpeningPredicateSatisfied = BooleanFlag
FinalGatePredicatesPass = BooleanFlag
ReproductionWasTrained = BooleanFlag
ReproductionCertified = BooleanFlag
ExternalVerificationActive = BooleanFlag
ResolvedRowRequirementReached = BooleanFlag


class FrozenDomainModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", protected_namespaces=())


class TensorDomainModel(FrozenDomainModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        protected_namespaces=(),
        arbitrary_types_allowed=True,
    )


class SeedBundle(FrozenDomainModel):
    master_seeds: tuple[MasterSeed, ...]
    analysis_seed: MasterSeed
    smoke_seed: MasterSeed

    @model_validator(mode="after")
    def _validate_seed_authorities(self) -> Self:
        if not self.master_seeds:
            raise ValueError("master_seeds must not be empty")
        if len(set(self.master_seeds)) != len(self.master_seeds):
            raise ValueError("master_seeds must not contain duplicates")
        return self

    @property
    def confirmatory_seed_count(self) -> SeedCount:
        return len(self.master_seeds)
