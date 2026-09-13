import torch

from fedsira.config import AnchorFedAvgConfig, OptimizerConfig, TrainingConfig
from fedsira.datasets.common import (
    DatasetAdapter,
    RealAnchor,
    Role,
)
from fedsira.domain.enums import LogEvent, SeedNamespace
from fedsira.domain.types import (
    AlgorithmName,
    ArtifactDigest,
    DerivedSeed,
    DomainId,
    EvaluationCadenceReached,
    ExampleCount,
    FeatureCount,
    FederatedRoundCount,
    FrozenDomainModel,
    LearningRate,
    LocalEpochCount,
    MasterSeed,
    ModelInputWidth,
    ModelOutputWidth,
    ModelParameterValue,
    RepositoryPath,
    RoundIndex,
    SampleId,
    SeedDerivationLabel,
    TensorDomainModel,
    TrainableParameterCount,
    WallClockSeconds,
)
from fedsira.experiments.definitions import ReproducerCondition
from fedsira.learning.model import (
    FedSIRAClassifier,
    flatten_trainable_parameters,
    trainable_parameter_count,
)
from fedsira.learning.training import (
    ModelState,
    WeightedModelState,
    build_loss_function,
    build_optimizer,
    federated_averaging,
    load_model_state,
    model_state_from_classifier,
    train_epochs_with_deterministic_batch_order,
)
from fedsira.runtime import (
    ElapsedTimer,
    current_application_context,
    derive_uint32,
    deterministic_order,
    get_structured_logger,
    local_training_seed,
    namespace_seed,
    seed_job_local_rng_streams,
)


class LocalTrainingClient(TensorDomainModel):
    features: torch.Tensor
    labels: torch.Tensor
    sample_ids: tuple[SampleId, ...]
    training_seed: DerivedSeed


def _validate_client_rows(client: LocalTrainingClient) -> ExampleCount:
    feature_rows = client.features.shape[0]
    if feature_rows <= 0:
        raise ValueError("local training requires at least one example")
    if client.labels.shape[0] != feature_rows or len(client.sample_ids) != feature_rows:
        raise ValueError("features, labels, and sample ids must have identical row counts")
    return feature_rows


def train_one_client_locally(
    global_state: ModelState,
    input_width: ModelInputWidth,
    output_width: ModelOutputWidth,
    learning_rate: LearningRate,
    optimizer_config: OptimizerConfig,
    training_config: TrainingConfig,
    local_epochs: LocalEpochCount,
    client: LocalTrainingClient,
) -> WeightedModelState:
    example_count = _validate_client_rows(client)
    model = FedSIRAClassifier(input_width, output_width)
    load_model_state(model, global_state)
    optimizer = build_optimizer(model, learning_rate, optimizer_config)
    loss_function = build_loss_function()
    train_epochs_with_deterministic_batch_order(
        model,
        optimizer,
        loss_function,
        training_config,
        client.features,
        client.labels,
        client.sample_ids,
        client.training_seed,
        local_epochs,
    )
    return WeightedModelState(
        state=model_state_from_classifier(model),
        example_count=example_count,
    )


def run_fedavg_round(
    global_state: ModelState,
    input_width: ModelInputWidth,
    output_width: ModelOutputWidth,
    learning_rate: LearningRate,
    optimizer_config: OptimizerConfig,
    training_config: TrainingConfig,
    local_epochs: LocalEpochCount,
    clients: tuple[LocalTrainingClient, ...],
) -> ModelState:
    if not clients:
        raise ValueError("FedAvg round requires at least one client")
    trained_clients = tuple(
        train_one_client_locally(
            global_state,
            input_width,
            output_width,
            learning_rate,
            optimizer_config,
            training_config,
            local_epochs,
            client,
        )
        for client in clients
    )
    return federated_averaging(trained_clients)


def _model_state_parameter_count(state: ModelState) -> TrainableParameterCount:
    parameter_count = sum(parameter.value.numel() for parameter in state.parameters)
    if parameter_count <= 0:
        raise ValueError("anchor model state must contain trainable parameters")
    return parameter_count


def run_anchor_fedavg_training(
    input_width: ModelInputWidth,
    output_width: ModelOutputWidth,
    initial_state: ModelState,
    learning_rate: LearningRate,
    optimizer_config: OptimizerConfig,
    training_config: TrainingConfig,
    anchor_config: AnchorFedAvgConfig,
    clients_per_round: tuple[tuple[LocalTrainingClient, ...], ...],
) -> tuple[ModelState, tuple[ModelState, ...]]:
    if len(clients_per_round) != anchor_config.rounds:
        raise ValueError(
            f"expected exactly {anchor_config.rounds} rounds of client data, "
            f"got {len(clients_per_round)}"
        )
    expected_parameter_count = trainable_parameter_count(
        FedSIRAClassifier(input_width, output_width)
    )
    observed_parameter_count = _model_state_parameter_count(initial_state)
    if observed_parameter_count != expected_parameter_count:
        raise ValueError(
            f"initial model state has {observed_parameter_count} parameters, expected "
            f"{expected_parameter_count} for input_width={input_width}, "
            f"output_width={output_width}"
        )
    validation_model = FedSIRAClassifier(input_width, output_width)
    load_model_state(validation_model, initial_state)
    state = initial_state
    round_checkpoints: list[ModelState] = []
    for round_index, round_clients in enumerate(clients_per_round):
        participating_clients = anchor_round_participants(round_clients, anchor_config, round_index)
        state = run_fedavg_round(
            state,
            input_width,
            output_width,
            learning_rate,
            optimizer_config,
            training_config,
            anchor_config.local_epochs_per_round,
            participating_clients,
        )
        round_checkpoints.append(state)
        if anchor_round_is_evaluated(anchor_config, round_index):
            validation_model = FedSIRAClassifier(input_width, output_width)
            load_model_state(validation_model, state)
            ANCHOR_LOGGER.info(
                LogEvent.ANCHOR_ROUND_EVALUATED,
                extra=AnchorRoundEvaluationLogFields(
                    round_index=round_index,
                    validation_parameters=float(
                        flatten_trainable_parameters(validation_model).sum()
                    ),
                ).model_dump(),
            )
    return round_checkpoints[-1], tuple(round_checkpoints)


def anchor_round_participants(
    round_clients: tuple[LocalTrainingClient, ...],
    anchor_config: AnchorFedAvgConfig,
    round_index: RoundIndex,
) -> tuple[LocalTrainingClient, ...]:
    if anchor_config.client_dropout == 0.0:
        return round_clients
    if not round_clients:
        raise ValueError("anchor round requires at least one client")
    universe = tuple(
        LocalTrainingClient(
            features=client.features,
            labels=client.labels,
            sample_ids=client.sample_ids,
            training_seed=client.training_seed,
        )
        for client in round_clients
    )
    drop_seed = derive_uint32(
        ANCHOR_CLIENT_DROPOUT_SEPARATOR,
        round_index,
        repr(anchor_config.client_dropout),
    )
    ordered = deterministic_order(
        tuple(client.training_seed for client in universe),
        ANCHOR_CLIENT_DROPOUT_SEPARATOR,
        drop_seed,
    )
    retained_count = max(1, int(round(len(universe) * (1.0 - anchor_config.client_dropout))))
    retained_seeds = frozenset(ordered[:retained_count])
    return tuple(client for client in universe if client.training_seed in retained_seeds)


def anchor_round_is_evaluated(
    anchor_config: AnchorFedAvgConfig, round_index: RoundIndex
) -> EvaluationCadenceReached:
    return (round_index + 1) % anchor_config.evaluation_cadence_rounds == 0


ANCHOR_TRAINING_ALGORITHM_TOKEN: AlgorithmName = "ANCHOR_FEDAVG"
ANCHOR_TRAINING_CONDITION_TOKEN = ReproducerCondition.CLEAN
ANCHOR_LOGGER = get_structured_logger("anchor_training")


ANCHOR_CLIENT_DROPOUT_SEPARATOR: SeedDerivationLabel = "ANCHOR_CLIENT_DROPOUT"


class AnchorRoundEvaluationLogFields(FrozenDomainModel):
    round_index: RoundIndex
    validation_parameters: ModelParameterValue


class AnchorTrainingLogFields(FrozenDomainModel):
    master_seed: MasterSeed
    prepared_root: RepositoryPath
    round_count: FederatedRoundCount | None = None
    elapsed_seconds: WallClockSeconds | None = None


def training_seed(
    master_seed: MasterSeed,
    manifest_hash: ArtifactDigest,
    start_checkpoint_identity: ArtifactDigest,
    algorithm_token: AlgorithmName,
    domain_token: DomainId,
    round_index: RoundIndex,
) -> DerivedSeed:
    return local_training_seed(
        namespace_seed(master_seed, SeedNamespace.LOCAL_TRAINING),
        manifest_hash,
        start_checkpoint_identity,
        algorithm_token,
        domain_token,
        ANCHOR_TRAINING_CONDITION_TOKEN,
        round_index,
    )


def _flatten_model_state(
    state: ModelState, input_width: FeatureCount, output_width: FeatureCount
) -> torch.Tensor:
    model = FedSIRAClassifier(input_width, output_width)
    load_model_state(model, state)
    return flatten_trainable_parameters(model)


def train_anchor(adapter: DatasetAdapter, master_seed: MasterSeed) -> RealAnchor | None:
    timer = ElapsedTimer()
    ANCHOR_LOGGER.info(
        LogEvent.ANCHOR_TRAINING_STARTED,
        extra=AnchorTrainingLogFields(
            master_seed=master_seed, prepared_root=adapter.prepared_root.as_posix()
        ).model_dump(),
    )
    config = current_application_context().scientific_config
    first_rows = adapter.load_rows(
        adapter.domain_ids[0], adapter.benign_class_token, Role.ANCHOR_TRAIN
    )
    if first_rows is None:
        return None
    input_width = len(first_rows.features[0])
    output_width = len(adapter.class_tokens)
    manifest_hash = adapter.manifest_hash()
    seed_job_local_rng_streams(namespace_seed(master_seed, SeedNamespace.MODEL_INITIALIZATION))
    initial_state = model_state_from_classifier(FedSIRAClassifier(input_width, output_width))
    clients_per_round: list[tuple[LocalTrainingClient, ...]] = []
    for round_index in range(config.model.anchor_fedavg.rounds):
        round_clients: list[LocalTrainingClient] = []
        for domain_id in adapter.domain_ids:
            rows = adapter.supported_rows_for_role(domain_id, Role.ANCHOR_TRAIN)
            tensors = adapter.tensor_view(rows)
            if tensors is None:
                continue
            features, labels, sample_ids = tensors
            round_clients.append(
                LocalTrainingClient(
                    features=features,
                    labels=labels,
                    sample_ids=sample_ids,
                    training_seed=training_seed(
                        master_seed,
                        manifest_hash,
                        "anchor-start",
                        ANCHOR_TRAINING_ALGORITHM_TOKEN,
                        adapter.domain_token(domain_id),
                        round_index,
                    ),
                )
            )
        if not round_clients:
            return None
        clients_per_round.append(tuple(round_clients))
    final_state, round_checkpoints = run_anchor_fedavg_training(
        input_width,
        output_width,
        initial_state,
        config.model.optimizer.anchor_and_standard_fl_learning_rate,
        config.model.optimizer,
        config.model.training,
        config.model.anchor_fedavg,
        tuple(clients_per_round),
    )
    model = FedSIRAClassifier(input_width, output_width)
    load_model_state(model, final_state)
    checkpoint_cadence = config.model.anchor_fedavg.checkpoint_cadence_rounds
    round_start_states = tuple(
        state
        for round_index, state in enumerate((initial_state, *round_checkpoints[:-1]))
        if round_index % checkpoint_cadence == 0
    )
    ANCHOR_LOGGER.info(
        LogEvent.ANCHOR_TRAINING_COMPLETED,
        extra=AnchorTrainingLogFields(
            master_seed=master_seed,
            prepared_root=adapter.prepared_root.as_posix(),
            round_count=config.model.anchor_fedavg.rounds,
            elapsed_seconds=timer.elapsed_seconds(),
        ).model_dump(),
    )
    return RealAnchor(
        input_width=input_width,
        output_width=output_width,
        flat_parameters=flatten_trainable_parameters(model),
        dataset_manifest_hash=manifest_hash,
        round_start_flat_parameters=tuple(
            _flatten_model_state(state, input_width, output_width) for state in round_start_states
        ),
    )
