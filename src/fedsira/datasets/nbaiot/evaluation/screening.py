from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import torch

from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.evaluation.domain import evaluate_domain
from fedsira.datasets.nbaiot.schema import NBAIOT_CLASS_ORDER, NBaiotClass, NBaiotDomain
from fedsira.datasets.nbaiot.workflow import RealAnchor, load_prepared_rows, tensor_view
from fedsira.domain.enums import AdmissionOpeningMode
from fedsira.domain.models import MetricResult
from fedsira.domain.types import ArtifactDigest, FoldIndex, MasterSeed, MetricValue
from fedsira.evaluation.metrics import supported_macro_f1_harm, target_capability_gain
from fedsira.experiments.definitions import AblationVariant
from fedsira.learning.model import FedSIRAClassifier, load_flat_trainable_parameters
from fedsira.learning.scoring import per_sample_cross_entropy
from fedsira.protocol.capability_contract import screen_evidence_is_adequate
from fedsira.protocol.proposal import (
    ScreenDomainResult,
    ScreenLossObservation,
    candidate_free_screen_domain_predicate,
    raw_target_f1_screen_domain_decision_is_positive,
    run_proposal_screen_for_domain,
    screen_domain_decision_is_positive,
    screen_fold_index,
    unmatched_control_screen_domain_decision_is_positive,
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


def evaluate_screen_domain(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_delta: torch.Tensor | None,
    domain: NBaiotDomain,
    opening_mode: AdmissionOpeningMode,
    screen_predicate_variant: AblationVariant | None,
) -> ScreenDomainResult:
    config = current_application_context().scientific_config
    target_rows = load_prepared_rows(
        prepared_root, domain, NBaiotClass.GAFGYT_COMBO, Role.CANDIDATE_SCREEN
    )
    target_count = 0 if target_rows is None else target_rows.row_count
    if not screen_evidence_is_adequate(target_count, config.capability_contract.evidence_minima):
        return ScreenDomainResult(
            domain=domain, is_evidence_adequate=False, meets_opening_predicate=False
        )
    if opening_mode is AdmissionOpeningMode.CANDIDATE_FREE:
        anchor_screen = evaluate_domain(
            prepared_root,
            anchor,
            anchor.flat_parameters,
            domain,
            role=Role.POST_REFERENCE_REPLAY,
            target_role=Role.CANDIDATE_SCREEN,
        )
        predicate = candidate_free_screen_domain_predicate(
            anchor_screen.target_f1
            if anchor_screen is not None
            else MetricResult(value=None, denominator=0),
            config.capability_contract,
        )
        return ScreenDomainResult(
            domain=domain, is_evidence_adequate=True, meets_opening_predicate=predicate
        )
    if source_delta is None:
        return ScreenDomainResult(
            domain=domain, is_evidence_adequate=True, meets_opening_predicate=False
        )
    candidate_flat = anchor.flat_parameters + source_delta
    anchor_screen = evaluate_domain(
        prepared_root,
        anchor,
        anchor.flat_parameters,
        domain,
        role=Role.POST_REFERENCE_REPLAY,
        target_role=Role.CANDIDATE_SCREEN,
    )
    source_screen = evaluate_domain(
        prepared_root,
        anchor,
        candidate_flat,
        domain,
        role=Role.POST_REFERENCE_REPLAY,
        target_role=Role.CANDIDATE_SCREEN,
    )
    if anchor_screen is None or source_screen is None:
        return ScreenDomainResult(
            domain=domain, is_evidence_adequate=True, meets_opening_predicate=False
        )
    target_f1_gain = target_capability_gain(source_screen.target_f1, anchor_screen.target_f1)
    supported_macro_f1_drop = supported_macro_f1_harm(
        anchor_screen.supported_macro_f1, source_screen.supported_macro_f1
    )
    benign_far_increase = (
        MetricResult(
            value=source_screen.benign_far.value - anchor_screen.benign_far.value,
            denominator=1,
        )
        if source_screen.benign_far.value is not None and anchor_screen.benign_far.value is not None
        else MetricResult(value=None, denominator=0)
    )
    if screen_predicate_variant is AblationVariant.RAW_TARGET_F1_SCREEN_ONLY:
        predicate = raw_target_f1_screen_domain_decision_is_positive(
            target_f1_gain,
            supported_macro_f1_drop,
            benign_far_increase,
            config.capability_contract,
        )
    elif screen_predicate_variant is AblationVariant.NO_MATCHED_CONTROL:
        unmatched_differential = compute_unmatched_screen_differential(
            prepared_root, anchor, source_delta, domain
        )
        predicate = unmatched_control_screen_domain_decision_is_positive(
            unmatched_differential,
            target_f1_gain,
            supported_macro_f1_drop,
            benign_far_increase,
            config.protocol.proposal_screen,
            config.capability_contract,
        )
    else:
        differential_a = compute_screen_differential(
            prepared_root, master_seed, anchor, source_delta, domain
        )
        predicate = screen_domain_decision_is_positive(
            differential_a,
            target_f1_gain,
            supported_macro_f1_drop,
            benign_far_increase,
            config.protocol.proposal_screen,
            config.capability_contract,
        )
    return ScreenDomainResult(
        domain=domain, is_evidence_adequate=True, meets_opening_predicate=predicate
    )
