import torch

from fedsira.learning.model import (
    FedSIRAClassifier,
    flatten_trainable_parameters,
    load_flat_trainable_parameters,
    trainable_parameter_count,
)


def test_forward_produces_the_dataset_derived_output_width() -> None:
    model = FedSIRAClassifier(input_width=115, output_width=11)
    logits = model(torch.zeros(4, 115))
    assert logits.shape == (4, 11)


def test_layer_widths_match_the_exact_roadmap_architecture() -> None:
    model = FedSIRAClassifier(input_width=115, output_width=11)
    assert model.hidden_1.in_features == 115
    assert model.hidden_1.out_features == 256
    assert model.hidden_2.in_features == 256
    assert model.hidden_2.out_features == 128
    assert model.hidden_3.in_features == 128
    assert model.hidden_3.out_features == 64
    assert model.output.in_features == 64
    assert model.output.out_features == 11


def test_layer_norms_use_the_exact_epsilon() -> None:
    model = FedSIRAClassifier(input_width=115, output_width=11)
    assert model.norm_1.eps == 1e-5
    assert model.norm_2.eps == 1e-5
    assert model.norm_3.eps == 1e-5


def test_dropout_rate_is_exactly_point_one() -> None:
    model = FedSIRAClassifier(input_width=115, output_width=11)
    assert model.dropout_1.p == 0.10
    assert model.dropout_2.p == 0.10


def test_no_dropout_after_the_third_hidden_layer() -> None:
    model = FedSIRAClassifier(input_width=115, output_width=11)
    assert not hasattr(model, "dropout_3")


def test_linear_biases_initialize_to_zero() -> None:
    model = FedSIRAClassifier(input_width=115, output_width=11)
    for linear in (model.hidden_1, model.hidden_2, model.hidden_3, model.output):
        assert torch.all(linear.bias == 0.0)


def test_layer_norm_weight_and_bias_initialize_to_one_and_zero() -> None:
    model = FedSIRAClassifier(input_width=115, output_width=11)
    for norm in (model.norm_1, model.norm_2, model.norm_3):
        assert torch.all(norm.weight == 1.0)
        assert torch.all(norm.bias == 0.0)


def test_xavier_uniform_weights_are_bounded_by_the_xavier_limit() -> None:
    model = FedSIRAClassifier(input_width=115, output_width=11)
    fan_in, fan_out = model.hidden_1.in_features, model.hidden_1.out_features
    limit = (6 / (fan_in + fan_out)) ** 0.5
    assert torch.all(model.hidden_1.weight.abs() <= limit + 1e-6)


def test_trainable_parameter_count_matches_manual_sum() -> None:
    model = FedSIRAClassifier(input_width=115, output_width=11)
    manual = sum(p.numel() for p in model.parameters() if p.requires_grad)
    assert trainable_parameter_count(model) == manual


def test_load_flat_trainable_parameters_round_trips_through_flatten() -> None:
    source_model = FedSIRAClassifier(input_width=115, output_width=11)
    flat = flatten_trainable_parameters(source_model)
    target_model = FedSIRAClassifier(input_width=115, output_width=11)
    load_flat_trainable_parameters(target_model, flat)
    assert torch.equal(flatten_trainable_parameters(target_model), flat)


def test_load_flat_trainable_parameters_changes_forward_output() -> None:
    model = FedSIRAClassifier(input_width=115, output_width=11)
    inputs = torch.zeros(2, 115)
    model.eval()
    with torch.no_grad():
        before = model(inputs).clone()
        load_flat_trainable_parameters(model, torch.ones_like(flatten_trainable_parameters(model)))
        after = model(inputs)
    assert not torch.allclose(before, after)
