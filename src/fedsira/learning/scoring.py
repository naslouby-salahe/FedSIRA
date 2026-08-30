from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as torch_functional

from fedsira.domain.records import BooleanValue


def logits_for_samples(
    model: nn.Module, features: torch.Tensor, keep_gradients: BooleanValue = False
) -> torch.Tensor:
    if keep_gradients:
        model.train()
        return model(features)
    model.eval()
    with torch.no_grad():
        return model(features)


def probabilities_for_samples(logits: torch.Tensor) -> torch.Tensor:
    return torch_functional.softmax(logits, dim=-1)
