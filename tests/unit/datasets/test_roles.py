from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.common import Role
from fedsira.datasets.roles import supported_role_windows, target_role_windows

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
ROLE_INTERVALS = CONFIG.datasets.primary.role_intervals


def test_supported_role_windows_cover_the_six_supported_roles_in_order() -> None:
    windows = supported_role_windows(ROLE_INTERVALS)
    assert [window.role for window in windows] == [
        Role.ANCHOR_TRAIN,
        Role.ANCHOR_VALIDATION,
        Role.POST_REFERENCE_REPLAY,
        Role.ROW_VERIFICATION,
        Role.FINAL_GATE,
        Role.REPORT_TEST,
    ]


def test_target_role_windows_cover_the_six_target_roles_in_order() -> None:
    windows = target_role_windows(ROLE_INTERVALS)
    assert [window.role for window in windows] == [
        Role.SOURCE_PROPOSAL,
        Role.CANDIDATE_SCREEN,
        Role.REPRODUCTION,
        Role.ROW_VERIFICATION,
        Role.FINAL_GATE,
        Role.REPORT_TEST,
    ]


def test_supported_role_windows_match_roadmap_anchor_train_boundary() -> None:
    windows = supported_role_windows(ROLE_INTERVALS)
    anchor_train = windows[0]
    assert anchor_train.contains(0.0)
    assert anchor_train.contains(0.394)
    assert not anchor_train.contains(0.395)


def test_target_role_windows_match_roadmap_source_proposal_boundary() -> None:
    windows = target_role_windows(ROLE_INTERVALS)
    source_proposal = windows[0]
    assert source_proposal.contains(0.0)
    assert source_proposal.contains(0.144)
    assert not source_proposal.contains(0.145)
