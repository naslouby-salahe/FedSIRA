from collections import OrderedDict
from collections.abc import Iterable, Iterator, Mapping
from typing import Protocol, cast

import torch
from torch import nn, optim
from torch.utils.data import DataLoader, Dataset, Sampler

from fedsira.config import OptimizerConfig, TrainingConfig
from fedsira.domain.types import (
    BatchRowIndexSequence,
    BatchRowIndices,
    BatchSize,
    DerivedSeed,
    EpochIndex,
    ExampleCount,
    LearningRate,
    LocalEpochCount,
    ParameterName,
    RowCount,
    SampleId,
    SampleRowIndex,
    TensorDomainModel,
    TrainingLoss,
)
from fedsira.learning.model import FedSIRAClassifier
from fedsira.runtime import current_application_context, minibatch_order


class _SteppableOptimizer(Protocol):
    def step(self) -> None: ...


def step_optimizer(optimizer: optim.AdamW) -> None:
    cast(_SteppableOptimizer, optimizer).step()


def build_loss_function() -> nn.CrossEntropyLoss:
    return nn.CrossEntropyLoss(weight=None, reduction="mean", label_smoothing=0.0)


def build_optimizer(
    model: FedSIRAClassifier,
    learning_rate: LearningRate,
    optimizer_config: OptimizerConfig,
) -> optim.AdamW:
    return optim.AdamW(
        model.parameters(),
        lr=learning_rate,
        betas=optimizer_config.betas,
        eps=optimizer_config.epsilon,
        weight_decay=optimizer_config.weight_decay,
        amsgrad=False,
        maximize=False,
        capturable=False,
        differentiable=False,
        foreach=False,
        fused=False,
    )


def clip_gradients(model: FedSIRAClassifier, training_config: TrainingConfig) -> None:
    nn.utils.clip_grad_norm_(
        model.parameters(),
        max_norm=training_config.gradient_global_l2_clip,
    )


def ordered_minibatches(
    training_seed: DerivedSeed,
    epoch: EpochIndex,
    sample_ids: tuple[SampleId, ...],
    batch_size: BatchSize,
) -> tuple[tuple[SampleId, ...], ...]:
    ordered = minibatch_order(training_seed, epoch, sample_ids)
    return tuple(
        ordered[start : start + batch_size] for start in range(0, len(ordered), batch_size)
    )


def ordered_batch_row_indices(
    sample_ids: tuple[SampleId, ...],
    training_seed: DerivedSeed,
    epoch: EpochIndex,
    batch_size: BatchSize,
) -> BatchRowIndexSequence:
    positions = sample_positions(sample_ids)
    return tuple(
        tuple(_sample_index(positions, sample_id) for sample_id in batch)
        for batch in ordered_minibatches(training_seed, epoch, sample_ids, batch_size)
    )


class OrderedIndexDataset(Dataset[tuple[torch.Tensor, torch.Tensor]]):
    def __init__(self, features: torch.Tensor, labels: torch.Tensor) -> None:
        self._features = features
        self._labels = labels

    def __len__(self) -> RowCount:
        return int(self._features.shape[0])

    def __getitem__(self, index: SampleRowIndex) -> tuple[torch.Tensor, torch.Tensor]:
        return (self._features[index], self._labels[index])


class DeclaredBatchSampler(Sampler[BatchRowIndices]):
    def __init__(self, batches: BatchRowIndexSequence) -> None:
        self._batches = batches

    def __iter__(self) -> Iterator[BatchRowIndices]:
        return iter([list(batch) for batch in self._batches])

    def __len__(self) -> RowCount:
        return len(self._batches)


def train_one_epoch(
    model: FedSIRAClassifier,
    optimizer: optim.AdamW,
    loss_function: nn.CrossEntropyLoss,
    training_config: TrainingConfig,
    batches: Iterable[tuple[torch.Tensor, torch.Tensor]],
) -> TrainingLoss:
    model.train()
    total_loss: TrainingLoss = 0.0
    batch_count = 0
    for features, labels in batches:
        batch_count += 1
        optimizer.zero_grad(set_to_none=True)
        logits = model(features)
        loss = loss_function(logits, labels)
        loss.backward()
        clip_gradients(model, training_config)
        step_optimizer(optimizer)
        total_loss += float(loss.detach())
    if batch_count == 0:
        raise ValueError("local training requires at least one minibatch")
    return total_loss / batch_count


def sample_positions(sample_ids: tuple[SampleId, ...]) -> Mapping[SampleId, EpochIndex]:
    positions: OrderedDict[SampleId, EpochIndex] = OrderedDict()
    for index, sample_id in enumerate(sample_ids):
        if sample_id in positions:
            raise ValueError("training population contains duplicate sample ids")
        positions[sample_id] = index
    return positions


def _sample_index(positions: Mapping[SampleId, EpochIndex], selected: SampleId) -> EpochIndex:
    try:
        return positions[selected]
    except KeyError as error:
        raise ValueError(
            f"ordered sample {selected} is absent from the training population"
        ) from error


def ordered_batch_indices(
    sample_ids: tuple[SampleId, ...],
    training_seed: DerivedSeed,
    epoch: EpochIndex,
    batch_size: BatchSize,
) -> tuple[torch.Tensor, ...]:
    ordered_batches = ordered_minibatches(training_seed, epoch, sample_ids, batch_size)
    positions = sample_positions(sample_ids)
    return tuple(
        torch.tensor(
            tuple(_sample_index(positions, sample_id) for sample_id in batch_sample_ids),
            dtype=torch.long,
        )
        for batch_sample_ids in ordered_batches
    )


def build_epoch_batches(
    features: torch.Tensor,
    labels: torch.Tensor,
    sample_ids: tuple[SampleId, ...],
    training_seed: DerivedSeed,
    epoch: EpochIndex,
    batch_size: BatchSize,
) -> DataLoader[tuple[torch.Tensor, torch.Tensor]]:
    if features.shape[0] != labels.shape[0] or features.shape[0] != len(sample_ids):
        raise ValueError("features, labels, and sample ids must have identical row counts")
    row_indices = ordered_batch_row_indices(sample_ids, training_seed, epoch, batch_size)
    loader = current_application_context().scientific_config.execution.data_loader
    return DataLoader(
        OrderedIndexDataset(features, labels),
        batch_sampler=DeclaredBatchSampler(row_indices),
        num_workers=loader.workers,
        pin_memory=loader.pin_memory,
        persistent_workers=loader.persistent_workers,
    )


def train_epochs_with_deterministic_batch_order(
    model: FedSIRAClassifier,
    optimizer: optim.AdamW,
    loss_function: nn.CrossEntropyLoss,
    training_config: TrainingConfig,
    features: torch.Tensor,
    labels: torch.Tensor,
    sample_ids: tuple[SampleId, ...],
    training_seed: DerivedSeed,
    local_epochs: LocalEpochCount,
) -> tuple[TrainingLoss, ...]:
    epoch_losses: list[TrainingLoss] = []
    for epoch in range(local_epochs):
        batches = build_epoch_batches(
            features,
            labels,
            sample_ids,
            training_seed,
            epoch,
            training_config.batch_size,
        )
        epoch_losses.append(
            train_one_epoch(model, optimizer, loss_function, training_config, batches)
        )
    return tuple(epoch_losses)


class ModelParameter(TensorDomainModel):
    name: ParameterName
    value: torch.Tensor


class ModelState(TensorDomainModel):
    parameters: tuple[ModelParameter, ...]


class WeightedModelState(TensorDomainModel):
    state: ModelState
    example_count: ExampleCount


def model_state_from_classifier(model: FedSIRAClassifier) -> ModelState:
    return ModelState(
        parameters=tuple(
            ModelParameter(name=name, value=parameter.detach().clone())
            for name, parameter in model.named_parameters()
        )
    )


def load_model_state(model: FedSIRAClassifier, state: ModelState) -> None:
    expected_names = tuple(name for name, _parameter in model.named_parameters())
    observed_names = tuple(parameter.name for parameter in state.parameters)
    if observed_names != expected_names:
        raise ValueError("model parameter schema does not match classifier architecture")
    with torch.no_grad():
        for name, parameter in model.named_parameters():
            source = model_parameter(state, name)
            if source.value.shape != parameter.shape:
                raise ValueError(f"shape mismatch for model parameter {name}")
            parameter.copy_(source.value)


def model_parameter(
    state: ModelState,
    parameter_name: ParameterName,
) -> ModelParameter:
    for parameter in state.parameters:
        if parameter.name == parameter_name:
            return parameter
    raise ValueError(f"model state does not contain parameter {parameter_name}")


def _validate_parameter_schema(client_states: tuple[WeightedModelState, ...]) -> None:
    expected_names = tuple(parameter.name for parameter in client_states[0].state.parameters)
    if not expected_names:
        raise ValueError("federated averaging requires model parameters")
    if len(set(expected_names)) != len(expected_names):
        raise ValueError("model parameter names must be unique")
    for client_state in client_states[1:]:
        observed_names = tuple(parameter.name for parameter in client_state.state.parameters)
        if observed_names != expected_names:
            raise ValueError("client model parameter schemas must match exactly")


def federated_averaging(
    client_states: tuple[WeightedModelState, ...],
) -> ModelState:
    if not client_states:
        raise ValueError("federated averaging requires at least one client update")
    _validate_parameter_schema(client_states)
    total_examples = sum(client_state.example_count for client_state in client_states)
    averaged: list[ModelParameter] = []
    for reference_parameter in client_states[0].state.parameters:
        weighted_sum = torch.zeros_like(reference_parameter.value, dtype=torch.float32)
        for client_state in client_states:
            parameter = model_parameter(client_state.state, reference_parameter.name)
            weighted_sum += parameter.value.to(torch.float32) * (
                client_state.example_count / total_examples
            )
        averaged.append(ModelParameter(name=reference_parameter.name, value=weighted_sum))
    return ModelState(parameters=tuple(averaged))
