from collections.abc import Hashable, Mapping, Sequence
from enum import StrEnum
from typing import Final, TypeVar

import torch

from fedsira.datasets.common import Role
from fedsira.domain.enums import AdmissionState, TernaryOutcome
from fedsira.domain.types import (
    BaselineFullParticipationAllowed,
    BaselineRetrainingCount,
    BooleanValue,
    DomainId,
    DomainLocalEvaluation,
    FederatedRoundCount,
    FrozenDomainModel,
    LocalEpochCount,
    ObservedPositiveReportCount,
    ReviewerCount,
    SourceAvailable,
    VerifierCount,
)
from fedsira.protocol.reproduction import next_reproducer_domain
from fedsira.runtime import current_application_context

Domain = TypeVar("Domain", bound=Hashable)


class BaselineIdentity(StrEnum):
    LOCAL_ONLY_REFERENCE = "Local-Only Reference"  # TODO: should be enum
    CENTRALIZED_REFERENCE = "Centralized Reference"  # TODO: should be enum
    FEDAVG_REFERENCE = "FedAvg Reference"  # TODO: should be enum
    CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION = "Client Review with Direct Source Admission"  # TODO: should be enum
    CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN = "Client Review then One Independent Retrain"  # TODO: should be enum
    ONE_INDEPENDENT_RETRAIN = "One Independent Retrain"  # TODO: should be enum
    CANDIDATE_FREE_FULL_PATH = "Candidate-Free Full Path"  # TODO: should be enum
    MULTIPLE_RETRAINS_WITH_DIRECT_KRUM = "Multiple Retrains with Direct Krum"  # TODO: should be enum
    THREE_ROW_COORDINATE_MEDIAN_ALTERNATIVE = "Three-Row Coordinate-Median Alternative"  # TODO: should be enum
    MULTIPLE_MODEL_CERTIFIED_ENSEMBLE = "Multiple-Model Certified Ensemble"  # TODO: should be enum
    INDEPENDENT_LOCAL_REFERENCE_WITH_SOURCE_ADMISSION = (
        "Independent Local Reference with Source Admission"
    )
    UPDATE_RECONSTRUCTION_FILTER = "Update Reconstruction Filter"  # TODO: should be enum
    DENSITY_CLUSTER_TRIMMED_MEAN = "Density-Cluster Trimmed Mean"  # TODO: should be enum
    SECURE_CONTINUAL_ASSESSMENT_REFERENCE = "Secure Continual Assessment Reference"  # TODO: should be enum
    RECOVERY_AFTER_SOURCE_ADMISSION = "Recovery after Source Admission"  # TODO: should be enum
    SOURCE_UPDATE_SANITIZATION_REFERENCE = "Source-Update Sanitization Reference"  # TODO: should be enum
    KRUM_ROBUST_AGGREGATION_REFERENCE = "Krum Robust Aggregation Reference"  # TODO: should be enum


class BaselineValidationFixture(StrEnum):
    LEGITIMATE_TARGET_CAPABILITY = "Legitimate Target Capability"  # TODO: should be enum
    USEFUL_BACKDOORED_SOURCE_5_PERCENT = "Useful Backdoored Source — 5%"  # TODO: should be enum
    MODEL_REPLACEMENT_BACKDOOR = "Model-Replacement Backdoor"  # TODO: should be enum


class BaselineMechanismFamily(StrEnum):
    LOCAL_REFERENCE = "local reference"  # TODO: should be enum
    CENTRALIZED_REFERENCE = "centralized reference"  # TODO: should be enum
    FEDERATED_AVERAGING = "federated averaging"  # TODO: should be enum
    SOURCE_REVIEW = "source review"  # TODO: should be enum
    SOURCE_REVIEW_THEN_RETRAIN = "source review then independent retrain"  # TODO: should be enum
    INDEPENDENT_RETRAIN = "independent retrain"  # TODO: should be enum
    CANDIDATE_FREE_FULL_PATH = "candidate-free full FedSIRA path"  # TODO: should be enum
    RETRAIN_WITH_DIRECT_KRUM = "multiple retrains with direct Krum"  # TODO: should be enum
    COORDINATE_MEDIAN = "coordinate-median synthesis"  # TODO: should be enum
    CERTIFIED_ENSEMBLE = "certified ensemble"  # TODO: should be enum
    INDEPENDENT_LOCAL_REFERENCE = "independent local reference"  # TODO: should be enum
    RECONSTRUCTION_FILTER = "update reconstruction filter"  # TODO: should be enum
    DENSITY_CLUSTER_TRIMMED_MEAN = "density-cluster trimmed mean"  # TODO: should be enum
    SECURE_CONTINUAL_ASSESSMENT = "secure continual assessment"  # TODO: should be enum
    RECOVERY_AFTER_SOURCE_ADMISSION = "recovery after source admission"  # TODO: should be enum
    SOURCE_UPDATE_SANITIZATION = "source-update sanitization"  # TODO: should be enum
    ROBUST_AGGREGATION = "robust round-level aggregation"  # TODO: should be enum


class BaselineExternalVerification(StrEnum):
    NONE = "none"  # TODO: should be enum
    THREE_REVIEWER_CAPABILITY_CONTRACT = "three-reviewer Capability Contract"  # TODO: should be enum
    THREE_REVIEWER_LOCAL_REFERENCE_NONINFERIORITY = (
        "three-reviewer Capability Contract with local-reference non-inferiority"
    )
    SINGLE_FRESH_VERIFIER = "single fresh verifier"  # TODO: should be enum
    FIVE_ROW_EXTERNAL_REPRODUCTION_CERTIFICATE = "five-row external reproduction certificate"  # TODO: should be enum
    THREE_MODEL_MAJORITY_VOTE = "three-model majority-vote certification"  # TODO: should be enum


class BaselineAggregationSynthesis(StrEnum):
    NONE = "none"  # TODO: should be enum
    FEDERATED_AVERAGING = "FedAvg"  # TODO: should be enum
    GROUP_FEDERATED_AVERAGING = "group FedAvg"  # TODO: should be enum
    KRUM = "Krum n=5,f=1"  # TODO: should be enum
    COORDINATE_MEDIAN = "coordinate-wise median"  # TODO: should be enum
    MAJORITY_VOTE_ENSEMBLE = "three-model majority vote"  # TODO: should be enum
    RECONSTRUCTION_ERROR_FILTER = "reconstruction-error filter then weighted FedAvg"  # TODO: should be enum
    DENSITY_CLUSTER_TRIMMED_MEAN = "DBSCAN cluster selection then coordinate-wise trimmed mean"  # TODO: should be enum
    COORDINATE_CLIPPING_THEN_APPLICATION = "coordinate-wise clipping then anchor application"  # TODO: should be enum


class BaselineTrainingBudget(StrEnum):
    CENTRALIZED_EPOCHS = "centralized epochs"  # TODO: should be enum
    DOMAIN_LOCAL_EPOCHS = "domain-local epochs"  # TODO: should be enum
    ANCHOR_FEDAVG_ROUNDS = "anchor FedAvg rounds"  # TODO: should be enum
    GROUP_FEDAVG_ROUNDS = "group FedAvg rounds"  # TODO: should be enum
    POST_REFERENCE_LOCAL_EPOCHS = "post-reference local epochs"  # TODO: should be enum
    POST_REFERENCE_FEDAVG_ROUNDS = "post-reference FedAvg rounds"  # TODO: should be enum
    ROUND_LEVEL_KRUM_ROUNDS = "round-level Krum rounds"  # TODO: should be enum


class BaselineProductionObject(StrEnum):
    LOCAL_CHECKPOINT = "local checkpoint"  # TODO: should be enum
    CENTRALIZED_MODEL = "centralized model"  # TODO: should be enum
    FEDERATED_GLOBAL_MODEL = "federated global model"  # TODO: should be enum
    SOURCE_CANDIDATE = "source candidate"  # TODO: should be enum
    SINGLE_REPRODUCTION = "single reproduction"  # TODO: should be enum
    KRUM_SYNTHESIZED_UPDATE = "Krum-synthesized update"  # TODO: should be enum
    COORDINATE_MEDIAN_UPDATE = "coordinate-median update"  # TODO: should be enum
    CERTIFIED_ENSEMBLE = "three-model certified ensemble"  # TODO: should be enum
    CLIPPED_SOURCE_UPDATE = "clipped source update applied to anchor"  # TODO: should be enum
    RECOVERED_FEDERATED_MODEL = "recovered federated model"  # TODO: should be enum
    FINAL_ROUND_CHECKPOINT = "final-round checkpoint"  # TODO: should be enum


class BaselineImplementationStatus(StrEnum):
    REGISTERED = "registered"  # TODO: should be enum
    INVALID = "invalid"  # TODO: should be enum


class BaselineContract(FrozenDomainModel):
    identity: BaselineIdentity
    mechanism_family: BaselineMechanismFamily
    source_artifact_deployed: BooleanValue
    independent_retraining_count: BaselineRetrainingCount
    external_verification: BaselineExternalVerification
    aggregation_synthesis: BaselineAggregationSynthesis
    training_budget: BaselineTrainingBudget
    production_object: BaselineProductionObject
    implementation_status: BaselineImplementationStatus


BASELINE_CONTRACTS: Final[tuple[BaselineContract, ...]] = (
    BaselineContract(
        identity=BaselineIdentity.LOCAL_ONLY_REFERENCE,
        mechanism_family=BaselineMechanismFamily.LOCAL_REFERENCE,
        source_artifact_deployed=False,
        independent_retraining_count=0,
        external_verification=BaselineExternalVerification.NONE,
        aggregation_synthesis=BaselineAggregationSynthesis.NONE,
        training_budget=BaselineTrainingBudget.DOMAIN_LOCAL_EPOCHS,
        production_object=BaselineProductionObject.LOCAL_CHECKPOINT,
        implementation_status=BaselineImplementationStatus.REGISTERED,
    ),
    BaselineContract(
        identity=BaselineIdentity.CENTRALIZED_REFERENCE,
        mechanism_family=BaselineMechanismFamily.CENTRALIZED_REFERENCE,
        source_artifact_deployed=False,
        independent_retraining_count=0,
        external_verification=BaselineExternalVerification.NONE,
        aggregation_synthesis=BaselineAggregationSynthesis.NONE,
        training_budget=BaselineTrainingBudget.CENTRALIZED_EPOCHS,
        production_object=BaselineProductionObject.CENTRALIZED_MODEL,
        implementation_status=BaselineImplementationStatus.REGISTERED,
    ),
    BaselineContract(
        identity=BaselineIdentity.FEDAVG_REFERENCE,
        mechanism_family=BaselineMechanismFamily.FEDERATED_AVERAGING,
        source_artifact_deployed=False,
        independent_retraining_count=0,
        external_verification=BaselineExternalVerification.NONE,
        aggregation_synthesis=BaselineAggregationSynthesis.FEDERATED_AVERAGING,
        training_budget=BaselineTrainingBudget.POST_REFERENCE_FEDAVG_ROUNDS,
        production_object=BaselineProductionObject.FEDERATED_GLOBAL_MODEL,
        implementation_status=BaselineImplementationStatus.REGISTERED,
    ),
    BaselineContract(
        identity=BaselineIdentity.CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION,
        mechanism_family=BaselineMechanismFamily.SOURCE_REVIEW,
        source_artifact_deployed=True,
        independent_retraining_count=0,
        external_verification=BaselineExternalVerification.THREE_REVIEWER_CAPABILITY_CONTRACT,
        aggregation_synthesis=BaselineAggregationSynthesis.NONE,
        training_budget=BaselineTrainingBudget.POST_REFERENCE_LOCAL_EPOCHS,
        production_object=BaselineProductionObject.SOURCE_CANDIDATE,
        implementation_status=BaselineImplementationStatus.REGISTERED,
    ),
    BaselineContract(
        identity=BaselineIdentity.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN,
        mechanism_family=BaselineMechanismFamily.SOURCE_REVIEW_THEN_RETRAIN,
        source_artifact_deployed=False,
        independent_retraining_count=1,
        external_verification=BaselineExternalVerification.SINGLE_FRESH_VERIFIER,
        aggregation_synthesis=BaselineAggregationSynthesis.NONE,
        training_budget=BaselineTrainingBudget.POST_REFERENCE_LOCAL_EPOCHS,
        production_object=BaselineProductionObject.SINGLE_REPRODUCTION,
        implementation_status=BaselineImplementationStatus.REGISTERED,
    ),
    BaselineContract(
        identity=BaselineIdentity.ONE_INDEPENDENT_RETRAIN,
        mechanism_family=BaselineMechanismFamily.INDEPENDENT_RETRAIN,
        source_artifact_deployed=False,
        independent_retraining_count=1,
        external_verification=BaselineExternalVerification.SINGLE_FRESH_VERIFIER,
        aggregation_synthesis=BaselineAggregationSynthesis.NONE,
        training_budget=BaselineTrainingBudget.POST_REFERENCE_LOCAL_EPOCHS,
        production_object=BaselineProductionObject.SINGLE_REPRODUCTION,
        implementation_status=BaselineImplementationStatus.REGISTERED,
    ),
    BaselineContract(
        identity=BaselineIdentity.CANDIDATE_FREE_FULL_PATH,
        mechanism_family=BaselineMechanismFamily.CANDIDATE_FREE_FULL_PATH,
        source_artifact_deployed=False,
        independent_retraining_count=5,
        external_verification=(
            BaselineExternalVerification.FIVE_ROW_EXTERNAL_REPRODUCTION_CERTIFICATE
        ),
        aggregation_synthesis=BaselineAggregationSynthesis.KRUM,
        training_budget=BaselineTrainingBudget.POST_REFERENCE_LOCAL_EPOCHS,
        production_object=BaselineProductionObject.KRUM_SYNTHESIZED_UPDATE,
        implementation_status=BaselineImplementationStatus.REGISTERED,
    ),
    BaselineContract(
        identity=BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM,
        mechanism_family=BaselineMechanismFamily.RETRAIN_WITH_DIRECT_KRUM,
        source_artifact_deployed=False,
        independent_retraining_count=5,
        external_verification=BaselineExternalVerification.NONE,
        aggregation_synthesis=BaselineAggregationSynthesis.KRUM,
        training_budget=BaselineTrainingBudget.POST_REFERENCE_LOCAL_EPOCHS,
        production_object=BaselineProductionObject.KRUM_SYNTHESIZED_UPDATE,
        implementation_status=BaselineImplementationStatus.REGISTERED,
    ),
    BaselineContract(
        identity=BaselineIdentity.THREE_ROW_COORDINATE_MEDIAN_ALTERNATIVE,
        mechanism_family=BaselineMechanismFamily.COORDINATE_MEDIAN,
        source_artifact_deployed=False,
        independent_retraining_count=3,
        external_verification=BaselineExternalVerification.NONE,
        aggregation_synthesis=BaselineAggregationSynthesis.COORDINATE_MEDIAN,
        training_budget=BaselineTrainingBudget.POST_REFERENCE_LOCAL_EPOCHS,
        production_object=BaselineProductionObject.COORDINATE_MEDIAN_UPDATE,
        implementation_status=BaselineImplementationStatus.REGISTERED,
    ),
    BaselineContract(
        identity=BaselineIdentity.MULTIPLE_MODEL_CERTIFIED_ENSEMBLE,
        mechanism_family=BaselineMechanismFamily.CERTIFIED_ENSEMBLE,
        source_artifact_deployed=False,
        independent_retraining_count=3,
        external_verification=BaselineExternalVerification.THREE_MODEL_MAJORITY_VOTE,
        aggregation_synthesis=BaselineAggregationSynthesis.MAJORITY_VOTE_ENSEMBLE,
        training_budget=BaselineTrainingBudget.GROUP_FEDAVG_ROUNDS,
        production_object=BaselineProductionObject.CERTIFIED_ENSEMBLE,
        implementation_status=BaselineImplementationStatus.REGISTERED,
    ),
    BaselineContract(
        identity=BaselineIdentity.INDEPENDENT_LOCAL_REFERENCE_WITH_SOURCE_ADMISSION,
        mechanism_family=BaselineMechanismFamily.INDEPENDENT_LOCAL_REFERENCE,
        source_artifact_deployed=True,
        independent_retraining_count=0,
        external_verification=(
            BaselineExternalVerification.THREE_REVIEWER_LOCAL_REFERENCE_NONINFERIORITY
        ),
        aggregation_synthesis=BaselineAggregationSynthesis.NONE,
        training_budget=BaselineTrainingBudget.DOMAIN_LOCAL_EPOCHS,
        production_object=BaselineProductionObject.SOURCE_CANDIDATE,
        implementation_status=BaselineImplementationStatus.REGISTERED,
    ),
    BaselineContract(
        identity=BaselineIdentity.UPDATE_RECONSTRUCTION_FILTER,
        mechanism_family=BaselineMechanismFamily.RECONSTRUCTION_FILTER,
        source_artifact_deployed=False,
        independent_retraining_count=0,
        external_verification=BaselineExternalVerification.NONE,
        aggregation_synthesis=BaselineAggregationSynthesis.RECONSTRUCTION_ERROR_FILTER,
        training_budget=BaselineTrainingBudget.ANCHOR_FEDAVG_ROUNDS,
        production_object=BaselineProductionObject.FEDERATED_GLOBAL_MODEL,
        implementation_status=BaselineImplementationStatus.REGISTERED,
    ),
    BaselineContract(
        identity=BaselineIdentity.DENSITY_CLUSTER_TRIMMED_MEAN,
        mechanism_family=BaselineMechanismFamily.DENSITY_CLUSTER_TRIMMED_MEAN,
        source_artifact_deployed=False,
        independent_retraining_count=0,
        external_verification=BaselineExternalVerification.NONE,
        aggregation_synthesis=BaselineAggregationSynthesis.DENSITY_CLUSTER_TRIMMED_MEAN,
        training_budget=BaselineTrainingBudget.ANCHOR_FEDAVG_ROUNDS,
        production_object=BaselineProductionObject.FEDERATED_GLOBAL_MODEL,
        implementation_status=BaselineImplementationStatus.REGISTERED,
    ),
    BaselineContract(
        identity=BaselineIdentity.SECURE_CONTINUAL_ASSESSMENT_REFERENCE,
        mechanism_family=BaselineMechanismFamily.SECURE_CONTINUAL_ASSESSMENT,
        source_artifact_deployed=False,
        independent_retraining_count=0,
        external_verification=BaselineExternalVerification.THREE_REVIEWER_CAPABILITY_CONTRACT,
        aggregation_synthesis=BaselineAggregationSynthesis.FEDERATED_AVERAGING,
        training_budget=BaselineTrainingBudget.POST_REFERENCE_FEDAVG_ROUNDS,
        production_object=BaselineProductionObject.FEDERATED_GLOBAL_MODEL,
        implementation_status=BaselineImplementationStatus.REGISTERED,
    ),
    BaselineContract(
        identity=BaselineIdentity.RECOVERY_AFTER_SOURCE_ADMISSION,
        mechanism_family=BaselineMechanismFamily.RECOVERY_AFTER_SOURCE_ADMISSION,
        source_artifact_deployed=True,
        independent_retraining_count=1,
        external_verification=BaselineExternalVerification.THREE_REVIEWER_CAPABILITY_CONTRACT,
        aggregation_synthesis=BaselineAggregationSynthesis.FEDERATED_AVERAGING,
        training_budget=BaselineTrainingBudget.POST_REFERENCE_FEDAVG_ROUNDS,
        production_object=BaselineProductionObject.RECOVERED_FEDERATED_MODEL,
        implementation_status=BaselineImplementationStatus.REGISTERED,
    ),
    BaselineContract(
        identity=BaselineIdentity.SOURCE_UPDATE_SANITIZATION_REFERENCE,
        mechanism_family=BaselineMechanismFamily.SOURCE_UPDATE_SANITIZATION,
        source_artifact_deployed=True,
        independent_retraining_count=0,
        external_verification=BaselineExternalVerification.THREE_REVIEWER_CAPABILITY_CONTRACT,
        aggregation_synthesis=(BaselineAggregationSynthesis.COORDINATE_CLIPPING_THEN_APPLICATION),
        training_budget=BaselineTrainingBudget.ANCHOR_FEDAVG_ROUNDS,
        production_object=BaselineProductionObject.CLIPPED_SOURCE_UPDATE,
        implementation_status=BaselineImplementationStatus.REGISTERED,
    ),
    BaselineContract(
        identity=BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE,
        mechanism_family=BaselineMechanismFamily.ROBUST_AGGREGATION,
        source_artifact_deployed=False,
        independent_retraining_count=0,
        external_verification=BaselineExternalVerification.NONE,
        aggregation_synthesis=BaselineAggregationSynthesis.KRUM,
        training_budget=BaselineTrainingBudget.ROUND_LEVEL_KRUM_ROUNDS,
        production_object=BaselineProductionObject.FINAL_ROUND_CHECKPOINT,
        implementation_status=BaselineImplementationStatus.REGISTERED,
    ),
)


def baseline_contract(identity: BaselineIdentity) -> BaselineContract:
    for contract in BASELINE_CONTRACTS:
        if contract.identity is identity:
            return contract
    raise KeyError(f"no baseline contract registered for {identity!r}")


if frozenset(contract.identity for contract in BASELINE_CONTRACTS) != frozenset(BaselineIdentity):
    raise AssertionError("every registered baseline must have exactly one contract")

BASELINE_VALIDATION_FIXTURE_MAP: Final[
    tuple[tuple[BaselineIdentity, BaselineValidationFixture], ...]
] = (
    (BaselineIdentity.LOCAL_ONLY_REFERENCE, BaselineValidationFixture.LEGITIMATE_TARGET_CAPABILITY),
    (
        BaselineIdentity.CENTRALIZED_REFERENCE,
        BaselineValidationFixture.LEGITIMATE_TARGET_CAPABILITY,
    ),
    (BaselineIdentity.FEDAVG_REFERENCE, BaselineValidationFixture.LEGITIMATE_TARGET_CAPABILITY),
    (
        BaselineIdentity.ONE_INDEPENDENT_RETRAIN,
        BaselineValidationFixture.LEGITIMATE_TARGET_CAPABILITY,
    ),
    (
        BaselineIdentity.CANDIDATE_FREE_FULL_PATH,
        BaselineValidationFixture.LEGITIMATE_TARGET_CAPABILITY,
    ),
    (
        BaselineIdentity.MULTIPLE_MODEL_CERTIFIED_ENSEMBLE,
        BaselineValidationFixture.LEGITIMATE_TARGET_CAPABILITY,
    ),
    (
        BaselineIdentity.CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION,
        BaselineValidationFixture.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
    ),
    (
        BaselineIdentity.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN,
        BaselineValidationFixture.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
    ),
    (
        BaselineIdentity.RECOVERY_AFTER_SOURCE_ADMISSION,
        BaselineValidationFixture.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
    ),
    (
        BaselineIdentity.SOURCE_UPDATE_SANITIZATION_REFERENCE,
        BaselineValidationFixture.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
    ),
    (
        BaselineIdentity.INDEPENDENT_LOCAL_REFERENCE_WITH_SOURCE_ADMISSION,
        BaselineValidationFixture.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
    ),
    (
        BaselineIdentity.SECURE_CONTINUAL_ASSESSMENT_REFERENCE,
        BaselineValidationFixture.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
    ),
    (
        BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM,
        BaselineValidationFixture.MODEL_REPLACEMENT_BACKDOOR,
    ),
    (
        BaselineIdentity.THREE_ROW_COORDINATE_MEDIAN_ALTERNATIVE,
        BaselineValidationFixture.MODEL_REPLACEMENT_BACKDOOR,
    ),
    (
        BaselineIdentity.UPDATE_RECONSTRUCTION_FILTER,
        BaselineValidationFixture.MODEL_REPLACEMENT_BACKDOOR,
    ),
    (
        BaselineIdentity.DENSITY_CLUSTER_TRIMMED_MEAN,
        BaselineValidationFixture.MODEL_REPLACEMENT_BACKDOOR,
    ),
    (
        BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE,
        BaselineValidationFixture.MODEL_REPLACEMENT_BACKDOOR,
    ),
)

if frozenset(identity for identity, _fixture in BASELINE_VALIDATION_FIXTURE_MAP) != frozenset(
    BaselineIdentity
):
    raise AssertionError("every registered baseline must have exactly one predeclared fixture")

TUNING_FORBIDDEN_ROLES: Final[frozenset[Role]] = frozenset(
    {Role.REPORT_TEST, Role.FINAL_GATE, Role.ROW_VERIFICATION}
)


class PostReferenceDataAccess(FrozenDomainModel):
    source_target_view: Role
    non_source_target_view: Role
    supported_replay_view: Role


ORDINARY_POST_REFERENCE_DATA_ACCESS: Final[PostReferenceDataAccess] = PostReferenceDataAccess(
    source_target_view=Role.SOURCE_PROPOSAL,
    non_source_target_view=Role.REPRODUCTION,
    supported_replay_view=Role.POST_REFERENCE_REPLAY,
)


def domain_target_view(
    domain: DomainId,
    source_domain: DomainId | None,
    data_access: PostReferenceDataAccess,
) -> Role:
    if domain == source_domain:
        return data_access.source_target_view
    return data_access.non_source_target_view


def validate_role_not_used_for_tuning(role: Role) -> None:
    if role in TUNING_FORBIDDEN_ROLES:
        raise ValueError(f"role {role.value} must never be used for baseline tuning")


def domain_without_target_view_may_participate(
    baseline_allows_full_participation: BaselineFullParticipationAllowed,
) -> BaselineFullParticipationAllowed:
    return baseline_allows_full_participation


def first_eligible_non_source_reproducer(
    reproducer_order: Sequence[DomainId], non_source_eligible_domains: frozenset[DomainId]
) -> DomainId | None:
    return next_reproducer_domain(reproducer_order, frozenset(), non_source_eligible_domains)


def single_fresh_verifier_domain(
    verifier_assignment_order: Sequence[DomainId],
    excluded_domains: frozenset[DomainId],
    adequate_eligible_domains: frozenset[DomainId],
) -> DomainId | None:
    return next_reproducer_domain(
        verifier_assignment_order, excluded_domains, adequate_eligible_domains
    )


def single_fresh_verifier_outcome(
    verifier_domain: DomainId | None, verifier_vote: TernaryOutcome | None
) -> AdmissionState:
    if verifier_domain is None:
        return AdmissionState.DORMANT
    if verifier_vote is TernaryOutcome.POSITIVE:
        return AdmissionState.ADMITTED
    return AdmissionState.REJECTED


def review_style_baseline_outcome(
    adequate_reviewer_count: ReviewerCount,
    positive_report_count: ObservedPositiveReportCount,
    panel_size: VerifierCount,
    required_positive_reports: VerifierCount,
) -> AdmissionState:
    if adequate_reviewer_count < panel_size:
        return AdmissionState.DORMANT
    if positive_report_count >= required_positive_reports:
        return AdmissionState.ADMITTED
    return AdmissionState.REJECTED


def local_only_reference_local_epochs() -> LocalEpochCount:
    return current_application_context().scientific_config.baselines.local_only_reference_epochs


def local_only_reference_training_role() -> Role:
    return Role.ANCHOR_TRAIN


def local_only_reference_evaluation_is_domain_local(
    checkpoint_domain: DomainId, evaluation_domain: DomainId
) -> DomainLocalEvaluation:
    return checkpoint_domain == evaluation_domain


def centralized_reference_local_epochs() -> LocalEpochCount:
    return current_application_context().scientific_config.baselines.centralized_reference_epochs


def pool_domain_rows(
    ordered_domains: Sequence[DomainId], domain_rows: Mapping[DomainId, torch.Tensor]
) -> torch.Tensor:
    return torch.cat([domain_rows[domain] for domain in ordered_domains], dim=0)


def centralized_reference_pooled_rows(
    ordered_rows: Sequence[torch.Tensor],
) -> torch.Tensor:
    return torch.cat(tuple(ordered_rows), dim=0)


def fedavg_reference_post_reference_rounds() -> FederatedRoundCount:
    return current_application_context().scientific_config.baselines.fedavg_post_reference_rounds


def standard_fl_anchor_rounds() -> FederatedRoundCount:
    return current_application_context().scientific_config.model.anchor_fedavg.rounds


def fedavg_reference_post_reference_local_epochs() -> LocalEpochCount:
    return (
        current_application_context().scientific_config.model.anchor_fedavg.local_epochs_per_round
    )


def post_reference_retrain_maximum_local_epochs() -> LocalEpochCount:
    return current_application_context().scientific_config.model.post_reference.local_epochs


def update_reconstruction_local_epochs() -> LocalEpochCount:
    reconstruction_filter = (
        current_application_context().scientific_config.baselines.reconstruction_filter
    )
    return reconstruction_filter.reconstruction_local_epochs


def recovery_after_source_admission_rounds() -> FederatedRoundCount:
    recovery = (
        current_application_context().scientific_config.baselines.recovery_after_source_admission
    )
    return recovery.recovery_rounds


def fedavg_reference_post_reference_participants(
    domain_order: Sequence[Domain],
    post_reference_eligible_domains: Sequence[Domain],
    source_domain: Domain | None,
    source_is_available: SourceAvailable,
) -> tuple[Domain, ...]:
    participant_set = set(post_reference_eligible_domains)
    if source_is_available and source_domain is not None:
        participant_set.add(source_domain)
    return tuple(domain for domain in domain_order if domain in participant_set)
