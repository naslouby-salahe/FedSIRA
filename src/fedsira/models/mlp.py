import torch
from torch import nn

from fedsira.domain.records import ModelInputWidth, ModelOutputWidth, PositiveInt


class FedSIRAClassifier(nn.Module):
    def __init__(self, input_width: ModelInputWidth, output_width: ModelOutputWidth) -> None:
        super().__init__()
        self.input_width = input_width
        self.output_width = output_width

        self.hidden_1 = nn.Linear(input_width, 256)
        self.norm_1 = nn.LayerNorm(256, eps=1e-5, elementwise_affine=True, bias=True)
        self.activation_1 = nn.GELU(approximate="none")
        self.dropout_1 = nn.Dropout(p=0.10)

        self.hidden_2 = nn.Linear(256, 128)
        self.norm_2 = nn.LayerNorm(128, eps=1e-5, elementwise_affine=True, bias=True)
        self.activation_2 = nn.GELU(approximate="none")
        self.dropout_2 = nn.Dropout(p=0.10)

        self.hidden_3 = nn.Linear(128, 64)
        self.norm_3 = nn.LayerNorm(64, eps=1e-5, elementwise_affine=True, bias=True)
        self.activation_3 = nn.GELU(approximate="none")

        self.output = nn.Linear(64, output_width)

        self._initialize_parameters()

    def _initialize_parameters(self) -> None:
        for linear in (self.hidden_1, self.hidden_2, self.hidden_3, self.output):
            nn.init.xavier_uniform_(linear.weight, gain=1.0)
            nn.init.zeros_(linear.bias)
        for norm in (self.norm_1, self.norm_2, self.norm_3):
            nn.init.ones_(norm.weight)
            nn.init.zeros_(norm.bias)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        hidden = self.dropout_1(self.activation_1(self.norm_1(self.hidden_1(inputs))))
        hidden = self.dropout_2(self.activation_2(self.norm_2(self.hidden_2(hidden))))
        hidden = self.activation_3(self.norm_3(self.hidden_3(hidden)))
        return self.output(hidden)


def trainable_parameter_count(model: FedSIRAClassifier) -> PositiveInt:
    return sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)


def flatten_trainable_parameters(model: FedSIRAClassifier) -> torch.Tensor:
    return torch.cat(
        [
            parameter.reshape(-1)
            for _, parameter in model.named_parameters()
            if parameter.requires_grad
        ]
    )


def load_flat_trainable_parameters(model: FedSIRAClassifier, flat_parameters: torch.Tensor) -> None:
    offset = 0
    with torch.no_grad():
        for _, parameter in model.named_parameters():
            if not parameter.requires_grad:
                continue
            count = parameter.numel()
            parameter.copy_(flat_parameters[offset : offset + count].reshape(parameter.shape))
            offset += count
