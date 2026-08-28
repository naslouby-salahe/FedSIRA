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
    FeatureCount,
    FeatureName,
    FeatureShiftSign,
    HeterogeneityMultiplier,
    NamespaceSeed,
    SamplingCap,
    SeedDerivationLabel,
)
from fedsira.runtime.determinism import deterministic_order, framed_bytes

QUANTITY_SKEW_SEPARATOR: SeedDerivationLabel = SeedNamespace.HETEROGENEITY.value
HETEROGENEITY_FEATURE_ORDER_SEPARATOR: SeedDerivationLabel = "HETEROGENEITY_FEATURE_ORDER"
HETEROGENEITY_FEATURE_SIGN_SEPARATOR: SeedDerivationLabel = "HETEROGENEITY_FEATURE_SIGN"


def quantity_skew_multiplier_by_domain(
    heterogeneity_namespace_seed: NamespaceSeed,
    multipliers: Sequence[HeterogeneityMultiplier],
) -> dict[NBaiotDomain, HeterogeneityMultiplier]:
    ordered = deterministic_domain_order(
        NBAIOT_DOMAIN_ORDER, QUANTITY_SKEW_SEPARATOR, heterogeneity_namespace_seed
    )
    return dict(zip(ordered, multipliers, strict=True))


def exclude_source_from_quantity_skew(
    multiplier_by_domain: Mapping[NBaiotDomain, HeterogeneityMultiplier],
    source_domain: NBaiotDomain,
) -> dict[NBaiotDomain, HeterogeneityMultiplier]:
    return {
        domain: multiplier
        for domain, multiplier in multiplier_by_domain.items()
        if domain != source_domain
    }


def apply_quantity_skew_to_cap(
    cap: SamplingCap, multiplier: HeterogeneityMultiplier
) -> SamplingCap:
    return math.floor(cap * multiplier)


def select_heterogeneity_shift_features(
    all_feature_names: Sequence[FeatureName],
    heterogeneity_namespace_seed: NamespaceSeed,
    selected_feature_count: FeatureCount,
) -> tuple[FeatureName, ...]:
    ordered = deterministic_order(
        all_feature_names,
        HETEROGENEITY_FEATURE_ORDER_SEPARATOR,
        heterogeneity_namespace_seed,
    )
    return ordered[:selected_feature_count]


def feature_shift_sign(
    domain: NBaiotDomain,
    feature_name: FeatureName,
    heterogeneity_namespace_seed: NamespaceSeed,
) -> FeatureShiftSign:
    digest = hashlib.sha256(
        framed_bytes(
            HETEROGENEITY_FEATURE_SIGN_SEPARATOR,
            heterogeneity_namespace_seed,
            NBAIOT_DOMAIN_HASH_TOKEN[domain],
            feature_name,
        )
    ).digest()
    return 1.0 if (digest[-1] & 1) == 1 else -1.0
