from fedsira.datasets.nbaiot.acquisition import DiscoveredCsvFile
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_CLASS_ORDER,
    NBAIOT_DOMAIN_ORDER,
    NBAIOT_TARGET_CLASS,
    NBaiotClass,
    NBaiotDomain,
)
from fedsira.domain.records import DomainCount


def domains_with_target_stream(
    discovered: tuple[DiscoveredCsvFile, ...],
) -> frozenset[NBaiotDomain]:
    return frozenset(item.domain for item in discovered if item.class_id is NBAIOT_TARGET_CLASS)


def domains_missing_target_stream(
    discovered: tuple[DiscoveredCsvFile, ...],
) -> tuple[NBaiotDomain, ...]:
    holders = domains_with_target_stream(discovered)
    return tuple(domain for domain in NBAIOT_DOMAIN_ORDER if domain not in holders)


def classes_structurally_unavailable(
    discovered: tuple[DiscoveredCsvFile, ...],
) -> tuple[NBaiotClass, ...]:
    observed = frozenset(item.class_id for item in discovered)
    return tuple(class_id for class_id in NBAIOT_CLASS_ORDER if class_id not in observed)


def validate_target_holder_feasibility(
    discovered: tuple[DiscoveredCsvFile, ...],
    minimum_target_holding_domains: DomainCount,
) -> None:
    holder_count = len(domains_with_target_stream(discovered))
    if holder_count < minimum_target_holding_domains:
        missing = ", ".join(domain.value for domain in domains_missing_target_stream(discovered))
        raise ValueError(
            f"only {holder_count} of {len(NBAIOT_DOMAIN_ORDER)} device proxies hold the "
            f"{NBAIOT_TARGET_CLASS.value} target stream; at least "
            f"{minimum_target_holding_domains} are required (missing: {missing})"
        )
