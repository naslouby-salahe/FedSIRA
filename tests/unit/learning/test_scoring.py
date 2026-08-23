import torch

from fedsira.learning.scoring import logits_for_samples, probabilities_for_samples
from fedsira.learning.training import build_loss_function
from fedsira.models.mlp import FedSIRAClassifier


def _model() -> FedSIRAClassifier:
    return FedSIRAClassifier(input_width=8, output_width=4)


def test_logits_for_samples_inference_matches_forward_shape() -> None:
    model = _model()
    features = torch.randn(5, 8)
    logits = logits_for_samples(model, features)
    assert logits.shape == (5, 4)
    assert model.training is False


def test_logits_for_samples_keep_gradients_tracks_grad() -> None:
    model = _model()
    features = torch.randn(3, 8)
    logits = logits_for_samples(model, features, keep_gradients=True)
    assert logits.requires_grad is True


def test_probabilities_for_samples_are_normalized() -> None:
    logits = torch.randn(6, 4)
    probabilities = probabilities_for_samples(logits)
    assert probabilities.shape == (6, 4)
    assert torch.allclose(probabilities.sum(dim=-1), torch.ones(6), atol=1e-6)


def test_logits_and_probabilities_agree_for_log_softmax() -> None:
    model = _model()
    features = torch.randn(2, 8)
    logits = logits_for_samples(model, features).detach()
    probabilities = probabilities_for_samples(logits)
    expected = torch.softmax(logits, dim=-1)
    assert torch.allclose(probabilities, expected, atol=1e-6)


def test_scoring_composes_with_loss_function() -> None:
    model = _model()
    loss_function = build_loss_function()
    features = torch.randn(4, 8)
    logits = logits_for_samples(model, features)
    loss = loss_function(logits, torch.zeros(4, dtype=torch.long))
    assert loss.dim() == 0
    assert float(loss) >= 0.0
