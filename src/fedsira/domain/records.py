from __future__ import annotations

from typing import Annotated, Self, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

UINT32_MODULUS = 4_294_967_296

# Constrained scalar foundations. Production models should expose the semantic aliases
# below rather than these storage-oriented foundations directly.
Probability = Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]
Percentage = Annotated[float, Field(ge=0.0, le=100.0, allow_inf_nan=False)]
NonNegativeInt = Annotated[int, Field(ge=0, strict=True)]
PositiveInt = Annotated[int, Field(gt=0, strict=True)]
NonNegativeFloat = Annotated[float, Field(ge=0.0, allow_inf_nan=False)]
PositiveFloat = Annotated[float, Field(gt=0.0, allow_inf_nan=False)]
FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]
BooleanValue = Annotated[bool, Field(strict=True)]
TextValue = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
Uint32Bound = Annotated[int, Field(ge=0, lt=UINT32_MODULUS, strict=True)]
DeterministicInteger = Annotated[int, Field(strict=True)]
FramingField: TypeAlias = TextValue | DeterministicInteger

# Identifiers and text domains.
Identifier = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=256,
        strip_whitespace=True,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._: /+@-]*$",
    ),
]
ExperimentSlug = Annotated[
    str,
    StringConstraints(min_length=1, max_length=128, pattern=r"^[a-z][a-z0-9-]*$"),
]
ArtifactDigest = Annotated[
    str,
    StringConstraints(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$"),
]
GitCommit = Annotated[
    str,
    StringConstraints(
        min_length=7,
        max_length=40,
        strip_whitespace=True,
        pattern=r"^[0-9a-f]{7,40}$",
    ),
]
Doi = Annotated[
    str,
    StringConstraints(
        min_length=6,
        max_length=256,
        strip_whitespace=True,
        pattern=r"^10\.[0-9]{4,9}/\S+$",
    ),
]
RepositoryPath = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
ExperimentName = TextValue
MethodName = TextValue
ConditionName = TextValue
ScenarioName = TextValue
MetricName = TextValue
DomainId = TextValue
ClassLabel = TextValue
DatasetClassToken = ClassLabel
FeatureName = TextValue
RoleName = TextValue
RoleToken = TextValue
AlgorithmName = TextValue
ArtifactName = TextValue
ParameterName = TextValue
MessageEndpoint = TextValue
EnvironmentText = TextValue
FailureMessage = TextValue
FixtureCaseName = TextValue
ComparisonFamilyName = TextValue
ComparisonName = TextValue
ComparisonState = TextValue
ReportColumnName = TextValue
CheckpointIdentity = TextValue
TrainingConditionId = TextValue
SeedDerivationLabel = TextValue
SampleId = TextValue
SampleIdPrefix = TextValue
RelativePathText = TextValue
ModuleName = TextValue
SchemaVersion = TextValue
DependencyImportName = TextValue
FingerprintPayload = TextValue
AstDumpText = TextValue

# Deterministic identities and seeds.
MasterSeed = Uint32Bound
NamespaceSeed = Uint32Bound
DerivedSeed = Uint32Bound
PartitionSalt = Uint32Bound
DatasetManifestDigest = ArtifactDigest
DatasetFileDigest = ArtifactDigest
RoundIndex = Annotated[int, Field(ge=-1, strict=True)]
EpochIndex = NonNegativeInt
RetryCount = NonNegativeInt

# Counts and discrete quantities.
RowCount = NonNegativeInt
SourceRowIndex = NonNegativeInt
SamplingCap = NonNegativeInt
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
FoldIndex = NonNegativeInt
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
TrimCount = NonNegativeInt
ClusterSize = PositiveInt
CommittedRowCount = PositiveInt
MinimumCompletePairCount = PositiveInt
ConfigFormatVersion = PositiveInt
CompleteSeedCount = NonNegativeInt
ByteCount = NonNegativeInt
MemoryBytes = NonNegativeInt
ModelTransmissionCount = NonNegativeInt

# Continuous scientific quantities.
StandardizedValue = FiniteFloat
MetricDifference = FiniteFloat
PairedDifference = FiniteFloat
ConfidenceIntervalBound = FiniteFloat
ComparisonMargin = NonNegativeFloat
MaterialThreshold = NonNegativeFloat
EffectSize = Annotated[float, Field(allow_inf_nan=True)]
LearningRate = PositiveFloat
OptimizerEpsilon = PositiveFloat
NumericalEpsilon = PositiveFloat
WeightDecay = NonNegativeFloat
GradientL2Clip = PositiveFloat
Temperature = PositiveFloat
LossWeight = NonNegativeFloat
RegularizationWeight = NonNegativeFloat
DifferentialNatsPerExample = NonNegativeFloat
ScreenDifferential = FiniteFloat
ScreenLoss = NonNegativeFloat
ScaleFactor = PositiveFloat
DeltaScale = PositiveFloat
MetricTolerance = PositiveFloat
ProbabilityTolerance = PositiveFloat
DurationToleranceSeconds = PositiveFloat
DurationSeconds = NonNegativeFloat
PValueDisplayFloor = PositiveFloat
DbscanEpsilon = PositiveFloat
ProductionWeight = NonNegativeFloat
KrumScore = NonNegativeFloat
FeatureShiftMagnitude = PositiveFloat

# Probability/rate semantics.
PoisonFraction = Probability
AttackStrength = Probability
ClientDropout = Probability
TargetF1 = Probability
TargetF1Gain = Probability
SupportedMacroF1Drop = Probability
BenignFalseAlarmRateIncrease = Probability
ContaminationRisk = Probability
ConfidenceLevel = Probability
FamilyWiseAlpha = Probability
PValue = Probability
CosineSimilarity = Probability
HeterogeneityMultiplier = Probability
OptimizerBeta = Probability
DefinedDomainFraction = Probability
RateReduction = Probability
RateMargin = Probability
RateWorsening = Probability
CapabilityCertificationRate = Probability
AdmissionRateChange = Probability
TargetF1Change = Probability
Percentile = Percentage
RoleBoundary = Probability
RolePosition = Probability

# Boolean semantics. Each public field uses a meaning-specific alias.
PinMemoryEnabled = BooleanValue
PersistentWorkersEnabled = BooleanValue
PredictorCountMatchesOfficial = BooleanValue
SourceCommitted = BooleanValue
EvidenceAdequate = BooleanValue
OpeningPredicateSatisfied = BooleanValue
FinalGatePredicatesPass = BooleanValue
ReproductionWasTrained = BooleanValue
ReproductionCertified = BooleanValue
ExternalVerificationActive = BooleanValue
ResolvedRowRequirementReached = BooleanValue
MaterialityDecision = BooleanValue


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
