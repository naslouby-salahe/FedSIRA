from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Annotated, Literal, Self, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

UINT32_MODULUS = 4_294_967_296

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
FeatureShiftSign: TypeAlias = Literal[-1, 1]

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
DatasetColumnName = TextValue
FeatureName = TextValue
RoleToken = TextValue
AlgorithmName = TextValue
ParameterName = TextValue
MessageEndpoint = TextValue
EnvironmentText = TextValue
FailureMessage = TextValue
FixtureCaseName = TextValue
ComparisonName = TextValue
ComparisonState = TextValue
CheckpointIdentity = TextValue
TrainingConditionId = TextValue
SeedDerivationLabel = TextValue
SampleId = TextValue
SampleIdPrefix = TextValue
RelativePathText = TextValue
PathToken = TextValue
ModuleName = TextValue
SchemaVersion = TextValue
ExecutionSchemaVersion = SchemaVersion
DependencyImportName = TextValue
FingerprintPayload = TextValue
AstDumpText = TextValue
ClaimId = TextValue
ClaimScopeText = TextValue
ClaimReason = TextValue
AttackFamilyDirectoryToken = TextValue
AttackFamilyName = TextValue
AttackBasename = TextValue
ReproductionRowId = TextValue
ScientificCellSemanticKey = TextValue
CellPhaseIdentity = TextValue
RuntimeComponentName = TextValue
ScientificConfigurationSubset = TextValue
EnvironmentRecord = TextValue
CreationContext = TextValue
TensorName = TextValue
FigureName = TextValue
TableName = TextValue
ReportVerificationFailure = TextValue
PreparedViewKey = TextValue
DoctorArtifactSummary = TextValue
DoctorExperimentSummary = TextValue
ProjectProgressDescription = TextValue
NextValidAction = TextValue

MasterSeed = Uint32Bound
NamespaceSeed = Uint32Bound
DerivedSeed = Uint32Bound
PartitionSalt = Uint32Bound
DatasetManifestDigest = ArtifactDigest
DatasetFileDigest = ArtifactDigest
FeatureSchemaDigest = ArtifactDigest
RoundIndex = Annotated[int, Field(ge=-1, strict=True)]
EpochIndex = NonNegativeInt
RetryCount = NonNegativeInt

RowCount = NonNegativeInt
SourceRowIndex = NonNegativeInt
SamplingCap = NonNegativeInt
FeatureIndex = NonNegativeInt
ClassIndex = NonNegativeInt
ExampleCount = NonNegativeInt
MinimumExampleCount = PositiveInt
DomainCount = PositiveInt
ClassCount = PositiveInt
FeatureCount = PositiveInt
ScreenDomainCount = PositiveInt
VerifierCount = PositiveInt
CommitteeSize = PositiveInt
ReviewerCount = PositiveInt
ReproductionRowCount = NonNegativeInt
CompromisedReproducerCount = NonNegativeInt
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
GigabyteCount = PositiveInt
GpuCount = PositiveInt
AdmissionCount = NonNegativeInt
HashModulus = PositiveInt
UciDatasetId = PositiveInt
SeedCount = PositiveInt
PredictorCount = PositiveInt
TrimCount = NonNegativeInt
ClusterSize = PositiveInt
MinimumCompletePairCount = PositiveInt
ConfigFormatVersion = PositiveInt
CompleteSeedCount = NonNegativeInt
ByteCount = NonNegativeInt
ModelTransmissionCount = NonNegativeInt
AdequateFinalGateDomainCount = NonNegativeInt
PreparedScreenTargetCount = NonNegativeInt
PreparedReproductionTargetCount = NonNegativeInt
PreparedSupportedReplayCount = NonNegativeInt
RequiredReproductionRowCount = PositiveInt
MaximumByzantineReproductionRows = NonNegativeInt
KrumNeighborCount = PositiveInt
SignFlipSampleCount = NonNegativeInt
ObservedPositiveReportCount = NonNegativeInt
MaximumByzantineReportCount = NonNegativeInt
MinimumHonestPositiveReportCount = NonNegativeInt
EligibleEvidenceHolderCount = NonNegativeInt
MinimumEligibleEvidenceHolderCount = PositiveInt
EvidenceArrivalCycleIndex = NonNegativeInt
ClaimedCompletionCycleIndex = NonNegativeInt
EligiblePoolSize = PositiveInt
ByzantineDomainCount = NonNegativeInt

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
PValueDisplayFloor = PositiveFloat
DbscanEpsilon = PositiveFloat
ProductionWeight = NonNegativeFloat
KrumScore = NonNegativeFloat
FeatureShiftMagnitude = PositiveFloat
TriggerFeatureValue = FiniteFloat
MetricValue = FiniteFloat
MetricObservation: TypeAlias = tuple[MetricName, MetricValue | None]

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
AtLeastTwoByzantineProbability = Probability
Percentile = Percentage
QuantileProbability = Probability
RoleBoundary = Probability
RolePosition = Probability

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
ClaimGateDecision = BooleanValue
CapabilityContractSatisfied = BooleanValue
SourceExcludedFromKrum = BooleanValue
KrumCommitteeAdmissible = BooleanValue
BaselineFullParticipationAllowed = BooleanValue
FinalGateArtifactValid = BooleanValue
PluralityActive = BooleanValue
InvariantChecksPassed = BooleanValue
AttackCarrierRequired = BooleanValue
ScreenDomainDecision = BooleanValue
ResolvedCoreComplete = BooleanValue
CollapseDecisionPassed = BooleanValue
ResolvedCoreDependent = BooleanValue
ProvenancePayloadStale = BooleanValue
ScientificConfigurationChanged = BooleanValue
DatasetSplitUpstreamChanged = BooleanValue
ProducerCodeOrRuntimeChanged = BooleanValue
ArtifactInvalidated = BooleanValue
OverwriteExisting = BooleanValue
CellCompletionStatus = BooleanValue
ConfigurationLoadable = BooleanValue
DeterministicExecutionReady = BooleanValue
ArtifactReuseDecision = BooleanValue
RarArchivesPresent = BooleanValue
KeepGradients = BooleanValue
SourceAvailable = BooleanValue
TargetBearingMemberPresent = BooleanValue
NonAbstainingReproduction = BooleanValue
TriggeredSampleMask = BooleanValue
BinaryLabelMask = BooleanValue
PredicateSatisfied = BooleanValue
ScopedContractActive = BooleanValue
NewlyAdequateEvidenceExists = BooleanValue
UnderlyingVoteIsPositive = BooleanValue
AllowSourceAsVerifier = BooleanValue
AdmissionIndicator = BooleanValue
ModelInputWidth = PositiveInt
ModelOutputWidth = PositiveInt
TrainableParameterCount = PositiveInt
ParticipantCount = PositiveInt
ClaimDefinitionCount = NonNegativeInt
VerifierReportCount = NonNegativeInt
ReproductionOpportunityCount = NonNegativeInt
ReproductionAttemptCount = NonNegativeInt
FalseCertificationCount = NonNegativeInt
LengthPrefixBytes = PositiveInt
FileCount = PositiveInt
TensorAxisSize = PositiveInt
CalibrationErrorCount = PositiveInt
MinimumDefinedDomainCount = PositiveInt
MemberIndex = NonNegativeInt
AttackCount = NonNegativeInt
TensorPayloadCount = NonNegativeInt
DecileBinIndex = NonNegativeInt
ConfusionCount = NonNegativeInt
PeakMemoryBytes = ByteCount
VectorNorm = NonNegativeFloat
TrainingLoss = NonNegativeFloat
WallClockSeconds = NonNegativeFloat
FeatureMoment = FiniteFloat
FeatureAccumulator = FiniteFloat
SquaredFeatureAccumulator = NonNegativeFloat
PreparedEvidencePresent = BooleanValue
ArtifactComplete = BooleanValue
ArtifactActive = BooleanValue
ModelTransmissionPresent = BooleanValue
ReconstructionAccepted = BooleanValue
RecoveryRollbackTriggered = BooleanValue
ParameterSimilarityCertified = BooleanValue
DomainLocalEvaluation = BooleanValue
SourceIsProductionUpdate = BooleanValue
DiscardSourceWeights = BooleanValue
ReviewerPositiveDecision = BooleanValue
RoleWindowContainsSample = BooleanValue
CleanOracleDegradationMaterial = BooleanValue
FalseSameEquivalenceCheck = BooleanValue
VerificationPassed = BooleanValue
ClaimStateIsTerminal = BooleanValue
VerifierEligible = BooleanValue
TimestampValid = BooleanValue
OneVotePerDomain = BooleanValue
ReproductionRowCertified = BooleanValue
AutomaticRecoveryPermitted = BooleanValue
AutomaticallyRetriable = BooleanValue
FinalGateRequired = BooleanValue
PlanRenderText = TextValue
RunRenderText = TextValue
TableCsvText = TextValue
FormattedStatisticText = TextValue
LogRecordText = TextValue
ResolvedCoreIdentity = TextValue
ReconstructionError = NonNegativeFloat
ReconstructionThreshold = NonNegativeFloat
PairwiseDistance = NonNegativeFloat
ParameterSimilarity = FiniteFloat
MonotonicTimestamp = PositiveFloat
ReconstructionErrorSeries: TypeAlias = tuple[ReconstructionError, ...]
PairwiseDistanceMatrix: TypeAlias = tuple[tuple[PairwiseDistance, ...], ...]
EvidenceArrivalCycleSequence: TypeAlias = tuple[EvidenceArrivalCycleIndex, ...]
AdmissionIndicatorSeries: TypeAlias = Sequence[AdmissionIndicator]
TriggeredSampleMaskSeries: TypeAlias = Sequence[TriggeredSampleMask]
BinaryLabelMaskSeries: TypeAlias = Sequence[BinaryLabelMask]
NonAbstainingReproductionSeries: TypeAlias = Sequence[NonAbstainingReproduction]
ClassSupportCounts: TypeAlias = Mapping[DatasetClassToken, ExampleCount]
OptionalParameterSimilarity: TypeAlias = ParameterSimilarity | None
OptionalTriggeredSampleMaskSeries: TypeAlias = TriggeredSampleMaskSeries | None


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
