from fedsira.config.schema import RoleIntervals
from fedsira.datasets.common import SUPPORTED_ROLE_ORDER, TARGET_ROLE_ORDER, RoleWindow


def supported_role_windows(role_intervals: RoleIntervals) -> tuple[RoleWindow, ...]:
    return tuple(
        RoleWindow(
            role=role,
            lower_inclusive=role_intervals.supported[role.value][0],
            upper_exclusive=role_intervals.supported[role.value][1],
        )
        for role in SUPPORTED_ROLE_ORDER
    )


def target_role_windows(role_intervals: RoleIntervals) -> tuple[RoleWindow, ...]:
    return tuple(
        RoleWindow(
            role=role,
            lower_inclusive=role_intervals.target[role.value][0],
            upper_exclusive=role_intervals.target[role.value][1],
        )
        for role in TARGET_ROLE_ORDER
    )
