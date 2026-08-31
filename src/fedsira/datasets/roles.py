from fedsira.config.models import RoleIntervals
from fedsira.datasets.common import SUPPORTED_ROLE_ORDER, TARGET_ROLE_ORDER, RoleWindow


def supported_role_windows(role_intervals: RoleIntervals) -> tuple[RoleWindow, ...]:
    return tuple(
        RoleWindow(
            role=role,
            lower_inclusive=role_intervals.supported.interval_for(role)[0],
            upper_exclusive=role_intervals.supported.interval_for(role)[1],
        )
        for role in SUPPORTED_ROLE_ORDER
    )


def target_role_windows(role_intervals: RoleIntervals) -> tuple[RoleWindow, ...]:
    return tuple(
        RoleWindow(
            role=role,
            lower_inclusive=role_intervals.target.interval_for(role)[0],
            upper_exclusive=role_intervals.target.interval_for(role)[1],
        )
        for role in TARGET_ROLE_ORDER
    )
