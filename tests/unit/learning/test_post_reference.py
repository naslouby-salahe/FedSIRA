import math
from typing import cast

import pytest
import torch

import fedsira.learning.post_reference as post_reference
from fedsira.config import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.common import DatasetAdapter, RealAnchor
from fedsira.domain.enums import Role
from fedsira.domain.types import DomainId
from fedsira.learning.model import FedSIRAClassifier, flatten_trainable_parameters
from fedsira.learning.post_reference import (
    compute_delta_l2,
    compute_stability_kl,
    post_reference_training_step,
    run_post_reference_training,
)
from fedsira.learning.training import build_loss_function, build_optimizer
from fedsira.runtime import seed_job_local_rng_streams

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
OPTIMIZER_CONFIG = CONFIG.model.optimizer
TRAINING_CONFIG = CONFIG.model.training
POST_REFERENCE_CONFIG = CONFIG.model.post_reference


def test_stability_kl_is_zero_when_distributions_match() -> None:
    logits = torch.randn(5, 3)
    kl = compute_stability_kl(logits, logits, temperature=1.0)
    assert abs(float(kl)) < 1e-5


def test_stability_kl_is_positive_when_distributions_differ() -> None:
    anchor_logits = torch.tensor([[10.0, 0.0, 0.0]])
    current_logits = torch.tensor([[0.0, 10.0, 0.0]])
    kl = compute_stability_kl(anchor_logits, current_logits, temperature=1.0)
    assert float(kl) > 1.0


def test_stability_kl_uses_anchor_to_reproduction_direction() -> None:
    anchor_logits = torch.tensor([[2.0, 0.0]])
    reproduction_logits = torch.tensor([[0.0, 1.0]])

    actual = compute_stability_kl(anchor_logits, reproduction_logits, temperature=1.0)
    anchor_probabilities = torch.softmax(anchor_logits, dim=-1)
    expected = (
        anchor_probabilities
        * (
            torch.log_softmax(anchor_logits, dim=-1)
            - torch.log_softmax(reproduction_logits, dim=-1)
        )
    ).sum()
    reverse = compute_stability_kl(reproduction_logits, anchor_logits, temperature=1.0)

    assert torch.allclose(actual, expected)
    assert not torch.allclose(actual, reverse)


def test_delta_l2_is_zero_when_current_equals_anchor() -> None:
    model = FedSIRAClassifier(input_width=4, output_width=2)
    anchor_flat = flatten_trainable_parameters(model).detach().clone()
    delta = compute_delta_l2(model, anchor_flat)
    assert abs(float(delta.detach())) < 1e-9


def test_delta_l2_grows_with_parameter_distance() -> None:
    model = FedSIRAClassifier(input_width=4, output_width=2)
    anchor_flat = flatten_trainable_parameters(model).detach().clone() + 1.0
    delta = compute_delta_l2(model, anchor_flat)
    assert float(delta.detach()) > 0.0


def test_post_reference_training_step_with_zero_supported_examples_uses_zero_stability() -> None:
    anchor_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model.load_state_dict(anchor_model.state_dict())
    optimizer = build_optimizer(
        current_model, OPTIMIZER_CONFIG.post_reference_learning_rate, OPTIMIZER_CONFIG
    )
    loss_function = build_loss_function()
    features = torch.randn(6, 4)
    labels = torch.randint(0, 2, (6,))
    is_supported = torch.zeros(6, dtype=torch.bool)
    anchor_flat = flatten_trainable_parameters(anchor_model).detach()

    loss = post_reference_training_step(
        anchor_model,
        current_model,
        optimizer,
        loss_function,
        TRAINING_CONFIG,
        POST_REFERENCE_CONFIG,
        features,
        labels,
        is_supported,
        anchor_flat,
        trainable_parameter_count=sum(p.numel() for p in current_model.parameters()),
    )
    assert not math.isnan(loss)


def test_post_reference_training_step_zero_supported_matches_ce_and_delta_l2_exactly() -> None:
    anchor_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model.load_state_dict(anchor_model.state_dict())
    optimizer = build_optimizer(
        current_model, OPTIMIZER_CONFIG.post_reference_learning_rate, OPTIMIZER_CONFIG
    )
    loss_function = build_loss_function()
    features = torch.randn(6, 4)
    labels = torch.randint(0, 2, (6,))
    is_supported = torch.zeros(6, dtype=torch.bool)
    anchor_flat = flatten_trainable_parameters(anchor_model).detach()
    parameter_count = sum(p.numel() for p in current_model.parameters())

    seed_job_local_rng_streams(0)
    with torch.no_grad():
        expected_ce_loss = float(loss_function(current_model(features), labels))
    expected_delta_l2 = float(
        compute_delta_l2(current_model, anchor_flat).detach() / parameter_count
    )

    seed_job_local_rng_streams(0)
    loss = post_reference_training_step(
        anchor_model,
        current_model,
        optimizer,
        loss_function,
        TRAINING_CONFIG,
        POST_REFERENCE_CONFIG,
        features,
        labels,
        is_supported,
        anchor_flat,
        trainable_parameter_count=parameter_count,
    )
    expected_total = expected_ce_loss + POST_REFERENCE_CONFIG.delta_l2_weight * expected_delta_l2
    assert abs(loss - expected_total) < 1e-6


def test_post_reference_training_step_matches_full_reproduction_objective() -> None:
    anchor_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model.load_state_dict(anchor_model.state_dict())
    with torch.no_grad():
        next(current_model.parameters()).add_(0.1)
    optimizer = torch.optim.AdamW(current_model.parameters(), lr=0.0)
    features = torch.tensor([[0.1, 0.2, 0.3, 0.4], [0.4, 0.3, 0.2, 0.1], [0.2, 0.1, 0.4, 0.3]])
    labels = torch.tensor([0, 1, 0])
    is_supported = torch.tensor([True, False, True])
    anchor_flat = flatten_trainable_parameters(anchor_model).detach()
    parameter_count = sum(parameter.numel() for parameter in current_model.parameters())

    current_model.train()
    anchor_model.eval()
    seed_job_local_rng_streams(11)
    with torch.no_grad():
        current_logits = current_model(features)
        expected_ce = build_loss_function()(current_logits, labels)
        expected_stability = compute_stability_kl(
            anchor_model(features[is_supported]),
            current_logits[is_supported],
            temperature=POST_REFERENCE_CONFIG.stability_kl_temperature,
        )
        expected_delta = compute_delta_l2(current_model, anchor_flat) / parameter_count
        expected_total = (
            expected_ce
            + POST_REFERENCE_CONFIG.stability_weight * expected_stability
            + POST_REFERENCE_CONFIG.delta_l2_weight * expected_delta
        )

    seed_job_local_rng_streams(11)
    actual = post_reference_training_step(
        anchor_model,
        current_model,
        optimizer,
        build_loss_function(),
        TRAINING_CONFIG,
        POST_REFERENCE_CONFIG,
        features,
        labels,
        is_supported,
        anchor_flat,
        trainable_parameter_count=parameter_count,
    )

    assert POST_REFERENCE_CONFIG.stability_weight == 1.0
    assert POST_REFERENCE_CONFIG.delta_l2_weight == 1.0e-5
    assert abs(actual - float(expected_total)) < 1e-6


def test_run_post_reference_training_runs_the_configured_epoch_count() -> None:
    anchor_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model.load_state_dict(anchor_model.state_dict())
    optimizer = build_optimizer(
        current_model, OPTIMIZER_CONFIG.post_reference_learning_rate, OPTIMIZER_CONFIG
    )
    loss_function = build_loss_function()
    features = torch.randn(10, 4)
    labels = torch.randint(0, 2, (10,))
    is_supported = torch.tensor([True, False] * 5)
    sample_ids = tuple(f"sample-{i}" for i in range(10))

    epoch_losses = run_post_reference_training(
        anchor_model,
        current_model,
        optimizer,
        loss_function,
        TRAINING_CONFIG,
        POST_REFERENCE_CONFIG,
        features,
        labels,
        is_supported,
        sample_ids,
        training_seed=42,
        local_epochs=3,
    )
    assert len(epoch_losses) == 3


def test_run_post_reference_training_moves_parameters_away_from_the_anchor() -> None:
    anchor_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model.load_state_dict(anchor_model.state_dict())
    optimizer = build_optimizer(
        current_model, OPTIMIZER_CONFIG.post_reference_learning_rate, OPTIMIZER_CONFIG
    )
    loss_function = build_loss_function()
    features = torch.randn(10, 4)
    labels = torch.randint(0, 2, (10,))
    is_supported = torch.tensor([True, False] * 5)
    sample_ids = tuple(f"sample-{i}" for i in range(10))

    run_post_reference_training(
        anchor_model,
        current_model,
        optimizer,
        loss_function,
        TRAINING_CONFIG,
        POST_REFERENCE_CONFIG,
        features,
        labels,
        is_supported,
        sample_ids,
        training_seed=42,
        local_epochs=3,
    )
    anchor_flat = flatten_trainable_parameters(anchor_model)
    current_flat = flatten_trainable_parameters(current_model)
    assert not torch.allclose(anchor_flat, current_flat)


def test_domain_reproduction_initializes_from_anchor_and_returns_anchor_relative_delta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    anchor_model = FedSIRAClassifier(input_width=4, output_width=2)
    anchor = RealAnchor(
        input_width=4,
        output_width=2,
        flat_parameters=flatten_trainable_parameters(anchor_model).detach(),
        dataset_manifest_hash="a" * 64,
        round_start_flat_parameters=(),
    )
    features = torch.randn(3, 4)
    labels = torch.tensor([0, 1, 0])
    sample_ids = ("one", "two", "three")
    is_supported = torch.tensor([True, False, True])
    expected_delta = torch.zeros_like(anchor.flat_parameters)
    first_parameter_size = next(anchor_model.parameters()).numel()
    expected_delta[:first_parameter_size] = 0.2
    observed_initializations: list[torch.Tensor] = []

    class Adapter:
        def domain_token(self, domain: str) -> str:
            return domain

    def fake_training(
        anchor_model: FedSIRAClassifier,
        current_model: FedSIRAClassifier,
        *args: object,
        **kwargs: object,
    ) -> tuple[float, ...]:
        del args, kwargs
        observed_initializations.extend(
            (
                flatten_trainable_parameters(anchor_model),
                flatten_trainable_parameters(current_model),
            )
        )
        with torch.no_grad():
            next(current_model.parameters()).add_(0.2)
        return ()

    def fake_combined_rows(
        _adapter: DatasetAdapter,
        _domain: DomainId,
        _target_role: Role,
        *_args: object,
        **_kwargs: object,
    ) -> tuple[torch.Tensor, torch.Tensor, tuple[str, ...], torch.Tensor]:
        del _args, _kwargs
        return features, labels, sample_ids, is_supported

    monkeypatch.setattr(post_reference, "combined_post_reference_rows", fake_combined_rows)
    monkeypatch.setattr(post_reference, "run_post_reference_training", fake_training)

    actual = post_reference.train_domain_reproduction_delta(
        cast(DatasetAdapter, Adapter()), 7, anchor, "domain"
    )

    assert actual is not None
    assert len(observed_initializations) == 2
    assert all(
        torch.equal(initialization, anchor.flat_parameters)
        for initialization in observed_initializations
    )
    assert torch.allclose(actual, expected_delta)
