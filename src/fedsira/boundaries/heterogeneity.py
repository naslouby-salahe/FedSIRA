import hashlib
import math
from collections.abc import Mapping, Sequence

from fedsira.datasets.nbaiot.schema import (
    NBAIOT_DOMAIN_HASH_TOKEN,
    NBAIOT_DOMAIN_ORDER,
    NBaiotDomain,
    deterministic_domain_order,
)
from fedsira.domain.enums import SeedNamespace
from fedsira.domain.records import (
    CanonicalToken,
    NamespaceSeed,
    NonNegativeInt,
    PositiveInt,
    Probability,
)
from fedsira.runtime.determinism import canonical_bytes, deterministic_order

QUANTITY_SKEW_SEPARATOR = SeedNamespace.HETEROGENEITY.value
HETEROGENEITY_FEATURE_ORDER_SEPARATOR = "HETEROGENEITY_FEATURE_ORDER"
HETEROGENEITY_FEATURE_SIGN_SEPARATOR = "HETEROGENEITY_FEATURE_SIGN"


def quantity_skew_multiplier_by_domain(
    heterogeneity_namespace_seed: NamespaceSeed, multipliers: Sequence[Probability]
) -> dict[NBaiotDomain, Probability]:
    ordered = deterministic_domain_order(
        NBAIOT_DOMAIN_ORDER, QUANTITY_SKEW_SEPARATOR, heterogeneity_namespace_seed
    )
    return dict(zip(ordered, multipliers, strict=True))


def exclude_source_from_quantity_skew(
    multiplier_by_domain: Mapping[NBaiotDomain, Probability], source_domain: NBaiotDomain
) -> dict[NBaiotDomain, Probability]:
    return {
        domain: multiplier
        for domain, multiplier in multiplier_by_domain.items()
        if domain != source_domain
    }


def apply_quantity_skew_to_cap(cap: NonNegativeInt, multiplier: Probability) -> NonNegativeInt:
    return math.floor(cap * multiplier)


def select_heterogeneity_shift_features(
    all_feature_names: Sequence[CanonicalToken],
    heterogeneity_namespace_seed: NamespaceSeed,
    selected_feature_count: PositiveInt,
) -> tuple[CanonicalToken, ...]:
    ordered = deterministic_order(
        all_feature_names, HETEROGENEITY_FEATURE_ORDER_SEPARATOR, heterogeneity_namespace_seed
    )
    return ordered[:selected_feature_count]


def feature_shift_sign(
    domain: NBaiotDomain, feature_name: CanonicalToken, heterogeneity_namespace_seed: NamespaceSeed
) -> float:
    digest = hashlib.sha256(
        canonical_bytes(
            HETEROGENEITY_FEATURE_SIGN_SEPARATOR,
            heterogeneity_namespace_seed,
            NBAIOT_DOMAIN_HASH_TOKEN[domain],
            feature_name,
        )
    ).digest()
    return 1.0 if (digest[-1] & 1) == 1 else -1.0
