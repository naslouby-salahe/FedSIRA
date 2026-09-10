from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as torch_functional

from fedsira.domain.types import KeepGradients


def logits_for_samples(
    model: nn.Module, features: torch.Tensor, keep_gradients: KeepGradients = False
) -> torch.Tensor:
    if keep_gradients:
        model.train()
        return model(features)
    model.eval()
    with torch.no_grad():
        return model(features)


def probabilities_for_samples(logits: torch.Tensor) -> torch.Tensor:
    return torch_functional.softmax(logits, dim=-1)


def per_sample_cross_entropy(
    model: nn.Module,
    features: torch.Tensor,
    labels: torch.Tensor,
) -> torch.Tensor:
    logits = logits_for_samples(model, features)
    return torch_functional.cross_entropy(logits, labels, reduction="none")
