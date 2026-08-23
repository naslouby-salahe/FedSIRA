import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from fedsira.domain.enums import SeedNamespace
from fedsira.domain.records import (
    CanonicalToken,
    DerivedSeed,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveInt,
)
from fedsira.evaluation.aggregation import match_nearest_within_decile
from fedsira.runtime.determinism import canonical_bytes

SCREEN_FOLD_SEPARATOR = SeedNamespace.SCREEN_FOLD.value


@dataclass(frozen=True)
class ScreenLossObservation:
    sample_id: CanonicalToken
    anchor_loss: NonNegativeFloat
    source_loss: NonNegativeFloat


def screen_fold_index(
    sample_id: CanonicalToken, screen_fold_seed: DerivedSeed, fold_count: PositiveInt
) -> NonNegativeInt:
    digest = hashlib.sha256(
        canonical_bytes(SCREEN_FOLD_SEPARATOR, screen_fold_seed, sample_id)
    ).digest()
    return int.from_bytes(digest[0:8], byteorder="big", signed=False) % fold_count


def match_held_out_fold(
    held_out_targets: Sequence[ScreenLossObservation],
    held_out_controls: Sequence[ScreenLossObservation],
    other_fold_controls: Sequence[ScreenLossObservation],
) -> tuple[tuple[ScreenLossObservation, ScreenLossObservation], ...] | None:
    targets_by_id = {observation.sample_id: observation for observation in held_out_targets}
    controls_by_id = {observation.sample_id: observation for observation in held_out_controls}
    matched_ids = match_nearest_within_decile(
        [(observation.sample_id, observation.anchor_loss) for observation in held_out_targets],
        [(observation.sample_id, observation.anchor_loss) for observation in held_out_controls],
        [observation.anchor_loss for observation in other_fold_controls],
    )
    if matched_ids is None:
        return None
    return tuple(
        (targets_by_id[target_id], controls_by_id[control_id])
        for target_id, control_id in matched_ids
    )


def proposal_screen_differential(
    matched_pairs: Sequence[tuple[ScreenLossObservation, ScreenLossObservation]],
) -> float | None:
    if len(matched_pairs) == 0:
        return None
    target_deltas = [target.anchor_loss - target.source_loss for target, _ in matched_pairs]
    control_deltas = [control.anchor_loss - control.source_loss for _, control in matched_pairs]
    differential_target = sum(target_deltas) / len(target_deltas)
    differential_control = sum(control_deltas) / len(control_deltas)
    return differential_target - differential_control


def run_proposal_screen_for_domain(
    fold_assignment_by_sample_id: Mapping[CanonicalToken, NonNegativeInt],
    target_observations: Sequence[ScreenLossObservation],
    control_observations: Sequence[ScreenLossObservation],
    fold_count: PositiveInt,
) -> float | None:
    all_matches: list[tuple[ScreenLossObservation, ScreenLossObservation]] = []
    for held_out_fold in range(fold_count):
        held_out_targets = [
            observation
            for observation in target_observations
            if fold_assignment_by_sample_id[observation.sample_id] == held_out_fold
        ]
        held_out_controls = [
            observation
            for observation in control_observations
            if fold_assignment_by_sample_id[observation.sample_id] == held_out_fold
        ]
        other_fold_controls = [
            observation
            for observation in control_observations
            if fold_assignment_by_sample_id[observation.sample_id] != held_out_fold
        ]
        fold_matches = match_held_out_fold(held_out_targets, held_out_controls, other_fold_controls)
        if fold_matches is None:
            return None
        all_matches.extend(fold_matches)
    return proposal_screen_differential(all_matches)
