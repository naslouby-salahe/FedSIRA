from collections.abc import Sequence

from fedsira.datasets.nbaiot.schema import (
    NBAIOT_DOMAIN_ORDER,
    NBaiotDomain,
    deterministic_domain_order,
)
from fedsira.domain.enums import SeedNamespace
from fedsira.domain.records import NamespaceSeed

SOURCE_SELECTION_SEPARATOR = SeedNamespace.SOURCE_SELECTION.value


def source_selection_order(
    source_selection_namespace_seed: NamespaceSeed,
) -> tuple[NBaiotDomain, ...]:
    return deterministic_domain_order(
        NBAIOT_DOMAIN_ORDER, SOURCE_SELECTION_SEPARATOR, source_selection_namespace_seed
    )


def select_source_domain(
    source_order: Sequence[NBaiotDomain],
    domains_with_target_stream: frozenset[NBaiotDomain],
    requires_gafgyt_udp_carrier: bool,
    domains_with_gafgyt_udp: frozenset[NBaiotDomain],
) -> NBaiotDomain | None:
    for domain in source_order:
        if domain not in domains_with_target_stream:
            continue
        if requires_gafgyt_udp_carrier and domain not in domains_with_gafgyt_udp:
            continue
        return domain
    return None
