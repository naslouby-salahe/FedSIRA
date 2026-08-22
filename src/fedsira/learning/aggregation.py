from collections.abc import Mapping, Sequence

import torch

from fedsira.domain.records import PositiveInt


def federated_averaging(
    client_state_dicts: Sequence[Mapping[str, torch.Tensor]],
    client_example_counts: Sequence[PositiveInt],
) -> dict[str, torch.Tensor]:
    if len(client_state_dicts) != len(client_example_counts):
        raise ValueError("client_state_dicts and client_example_counts must have equal length")
    if len(client_state_dicts) == 0:
        raise ValueError("federated averaging requires at least one client update")

    total_examples = sum(client_example_counts)
    averaged: dict[str, torch.Tensor] = {}
    for parameter_name in client_state_dicts[0]:
        weighted_sum = torch.zeros_like(client_state_dicts[0][parameter_name], dtype=torch.float32)
        for state_dict, example_count in zip(
            client_state_dicts, client_example_counts, strict=True
        ):
            weighted_sum += state_dict[parameter_name].to(torch.float32) * (
                example_count / total_examples
            )
        averaged[parameter_name] = weighted_sum
    return averaged
