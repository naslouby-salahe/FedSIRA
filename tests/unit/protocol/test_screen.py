from fedsira.protocol.proposal import (
    ScreenLossObservation,
    match_held_out_fold,
    proposal_screen_differential,
    run_proposal_screen_for_domain,
    screen_fold_index,
)


def test_screen_fold_index_is_deterministic_and_within_bounds() -> None:
    first = screen_fold_index("sample-1", 42, 5)
    second = screen_fold_index("sample-1", 42, 5)
    assert first == second
    assert 0 <= first < 5


def test_screen_fold_index_is_reproducible_across_calls_with_the_same_seed() -> None:
    a = screen_fold_index("sample-1", 7, 5)
    b = screen_fold_index("sample-1", 7, 5)
    assert a == b


def test_match_held_out_fold_matches_closest_anchor_loss_within_decile() -> None:
    targets = [ScreenLossObservation(sample_id="t1", anchor_loss=1.0, source_loss=0.5)]
    controls = [
        ScreenLossObservation(sample_id="c1", anchor_loss=0.9, source_loss=0.9),
        ScreenLossObservation(sample_id="c2", anchor_loss=1.1, source_loss=1.1),
    ]
    other_fold_controls = [
        ScreenLossObservation(sample_id=f"o{i}", anchor_loss=float(i), source_loss=float(i))
        for i in range(1, 10)
    ]
    matches = match_held_out_fold(targets, controls, other_fold_controls)
    assert matches is not None
    assert len(matches) == 1
    assert matches[0][1].sample_id == "c1"


def test_match_held_out_fold_returns_none_when_bin_has_no_candidate() -> None:
    targets = [ScreenLossObservation(sample_id="t1", anchor_loss=100.0, source_loss=50.0)]
    controls = [ScreenLossObservation(sample_id="c1", anchor_loss=0.1, source_loss=0.1)]
    other_fold_controls = [
        ScreenLossObservation(sample_id=f"o{i}", anchor_loss=float(i), source_loss=float(i))
        for i in range(1, 10)
    ]
    assert match_held_out_fold(targets, controls, other_fold_controls) is None


def test_proposal_screen_differential_empty_is_none() -> None:
    assert proposal_screen_differential(()) is None


def test_proposal_screen_differential_matches_hand_computation() -> None:
    target = ScreenLossObservation(sample_id="t1", anchor_loss=1.0, source_loss=0.4)
    control = ScreenLossObservation(sample_id="c1", anchor_loss=1.0, source_loss=0.9)
    differential = proposal_screen_differential([(target, control)])
    assert differential is not None
    assert abs(differential - 0.5) < 1e-9


def test_run_proposal_screen_for_domain_end_to_end() -> None:
    fold_count = 5
    targets = [
        ScreenLossObservation(sample_id=f"target-{i}", anchor_loss=float(i % 5), source_loss=0.1)
        for i in range(10)
    ]
    controls = [
        ScreenLossObservation(sample_id=f"control-{i}", anchor_loss=float(i % 5), source_loss=0.2)
        for i in range(50)
    ]
    fold_assignment = {
        observation.sample_id: index % fold_count
        for index, observation in enumerate(targets + controls)
    }
    result = run_proposal_screen_for_domain(fold_assignment, targets, controls, fold_count)
    assert result is not None
