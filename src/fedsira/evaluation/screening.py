from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import torch

from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.schema import NBAIOT_CLASS_ORDER, NBaiotClass, NBaiotDomain
from fedsira.domain.types import ArtifactDigest, FoldIndex, MasterSeed, MetricValue
from fedsira.experiments.workflow import RealAnchor, load_prepared_rows, tensor_view
from fedsira.learning.model import FedSIRAClassifier, load_flat_trainable_parameters
from fedsira.learning.scoring import per_sample_cross_entropy
from fedsira.protocol.proposal import (
    ScreenLossObservation,
    run_proposal_screen_for_domain,
    screen_fold_index,
)
from fedsira.runtime import current_application_context, derive_uint32


def _screen_models(
    anchor: RealAnchor, source_delta: torch.Tensor
) -> tuple[FedSIRAClassifier, FedSIRAClassifier]:
    anchor_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(anchor_model, anchor.flat_parameters)
    source_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(source_model, anchor.flat_parameters + source_delta)
    return anchor_model, source_model


def compute_unmatched_screen_differential(
    prepared_root: Path, anchor: RealAnchor, source_delta: torch.Tensor, domain: NBaiotDomain
) -> MetricValue | None:
    target_rows = tensor_view(
        load_prepared_rows(prepared_root, domain, NBaiotClass.GAFGYT_COMBO, Role.CANDIDATE_SCREEN)
    )
    if target_rows is None:
        return None
    target_features, target_labels, _target_sample_ids = target_rows
    anchor_model, source_model = _screen_models(anchor, source_delta)
    target_anchor_loss = per_sample_cross_entropy(anchor_model, target_features, target_labels)
    target_source_loss = per_sample_cross_entropy(source_model, target_features, target_labels)
    return float(torch.mean(target_anchor_loss - target_source_loss))


def compute_screen_differential(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_delta: torch.Tensor,
    domain: NBaiotDomain,
) -> MetricValue | None:
    target_rows = tensor_view(
        load_prepared_rows(prepared_root, domain, NBaiotClass.GAFGYT_COMBO, Role.CANDIDATE_SCREEN)
    )
    if target_rows is None:
        return None
    target_features, target_labels, target_sample_ids = target_rows
    control_features_parts: list[torch.Tensor] = []
    control_labels_parts: list[torch.Tensor] = []
    control_sample_ids: list[ArtifactDigest] = []
    for class_id in NBAIOT_CLASS_ORDER:
        if class_id is NBaiotClass.GAFGYT_COMBO:
            continue
        replay_rows = tensor_view(
            load_prepared_rows(prepared_root, domain, class_id, Role.POST_REFERENCE_REPLAY)
        )
        if replay_rows is None:
            continue
        features, labels, sample_ids = replay_rows
        control_features_parts.append(features)
        control_labels_parts.append(labels)
        control_sample_ids.extend(sample_ids)
    if not control_features_parts:
        return None
    anchor_model, source_model = _screen_models(anchor, source_delta)
    target_anchor_loss = per_sample_cross_entropy(anchor_model, target_features, target_labels)
    target_source_loss = per_sample_cross_entropy(source_model, target_features, target_labels)
    control_features = torch.cat(control_features_parts, dim=0)
    control_labels = torch.cat(control_labels_parts, dim=0)
    control_anchor_loss = per_sample_cross_entropy(anchor_model, control_features, control_labels)
    control_source_loss = per_sample_cross_entropy(source_model, control_features, control_labels)
    config = current_application_context().scientific_config
    screen_fold_seed = derive_uint32("SCREEN_FOLD_SEED", master_seed)
    fold_count = config.protocol.proposal_screen.fold_count
    fold_assignment: OrderedDict[ArtifactDigest, FoldIndex] = OrderedDict()
    target_observations: list[ScreenLossObservation] = []
    for index, sample_id in enumerate(target_sample_ids):
        fold_assignment[sample_id] = screen_fold_index(sample_id, screen_fold_seed, fold_count)
        target_observations.append(
            ScreenLossObservation(
                sample_id=sample_id,
                anchor_loss=float(target_anchor_loss[index]),
                source_loss=float(target_source_loss[index]),
            )
        )
    control_observations: list[ScreenLossObservation] = []
    for index, sample_id in enumerate(control_sample_ids):
        fold_assignment[sample_id] = screen_fold_index(sample_id, screen_fold_seed, fold_count)
        control_observations.append(
            ScreenLossObservation(
                sample_id=sample_id,
                anchor_loss=float(control_anchor_loss[index]),
                source_loss=float(control_source_loss[index]),
            )
        )
    return run_proposal_screen_for_domain(
        fold_assignment, target_observations, control_observations, fold_count
    )
