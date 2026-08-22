import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from fedsira.domain.records import CanonicalToken, DerivedSeed, NonNegativeInt, PositiveInt
from fedsira.evaluation.aggregation import quantile_type7
from fedsira.runtime.determinism import canonical_bytes

SCREEN_FOLD_SEPARATOR = "SCREEN_FOLD"


@dataclass(frozen=True)
class ScreenLossObservation:
    sample_id: CanonicalToken
    anchor_loss: float
    source_loss: float


def screen_fold_index(
    sample_id: CanonicalToken, screen_fold_seed: DerivedSeed, fold_count: PositiveInt
) -> NonNegativeInt:
    digest = hashlib.sha256(
        canonical_bytes(SCREEN_FOLD_SEPARATOR, screen_fold_seed, sample_id)
    ).digest()
    return int.from_bytes(digest[0:8], byteorder="big", signed=False) % fold_count


def _decile_boundaries(control_losses: Sequence[float]) -> tuple[float, ...]:
    sorted_losses = sorted(control_losses)
    return tuple(quantile_type7(sorted_losses, decile / 10.0) for decile in range(1, 10))


def _decile_bin(loss: float, boundaries: tuple[float, ...]) -> int:
    bin_index = 0
    for boundary in boundaries:
        if loss <= boundary:
            break
        bin_index += 1
    return bin_index


def match_held_out_fold(
    held_out_targets: Sequence[ScreenLossObservation],
    held_out_controls: Sequence[ScreenLossObservation],
    other_fold_controls: Sequence[ScreenLossObservation],
) -> tuple[tuple[ScreenLossObservation, ScreenLossObservation], ...] | None:
    boundaries = _decile_boundaries(
        [observation.anchor_loss for observation in other_fold_controls]
    )
    controls_by_bin: dict[int, list[ScreenLossObservation]] = {}
    for control in held_out_controls:
        controls_by_bin.setdefault(_decile_bin(control.anchor_loss, boundaries), []).append(control)
    for bin_controls in controls_by_bin.values():
        bin_controls.sort(key=lambda observation: observation.sample_id)

    matches: list[tuple[ScreenLossObservation, ScreenLossObservation]] = []
    for target in sorted(held_out_targets, key=lambda observation: observation.sample_id):
        candidates = controls_by_bin.get(_decile_bin(target.anchor_loss, boundaries), [])
        if not candidates:
            return None
        best_control = min(
            candidates,
            key=lambda control: (abs(control.anchor_loss - target.anchor_loss), control.sample_id),
        )
        candidates.remove(best_control)
        matches.append((target, best_control))
    return tuple(matches)


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
