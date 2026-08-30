import hashlib
import math

from fedsira.datasets.nbaiot.schema import (
    NBAIOT_DOMAIN_ORDER,
    NBaiotDomain,
    deterministic_domain_order,
    nbaiot_domain_hash_token,
)
from fedsira.domain.enums import SeedNamespace
from fedsira.domain.records import (
    FeatureCount,
    FeatureName,
    FeatureShiftSign,
    FrozenDomainModel,
    HeterogeneityMultiplier,
    NamespaceSeed,
    SamplingCap,
    SeedDerivationLabel,
)
from fedsira.runtime.determinism import deterministic_order, framed_bytes

QUANTITY_SKEW_SEPARATOR: SeedDerivationLabel = SeedNamespace.HETEROGENEITY.value
HETEROGENEITY_FEATURE_ORDER_SEPARATOR: SeedDerivationLabel = "HETEROGENEITY_FEATURE_ORDER"
HETEROGENEITY_FEATURE_SIGN_SEPARATOR: SeedDerivationLabel = "HETEROGENEITY_FEATURE_SIGN"


class DomainQuantitySkew(FrozenDomainModel):
    domain: NBaiotDomain
    multiplier: HeterogeneityMultiplier


def quantity_skew_multiplier_by_domain(
    heterogeneity_namespace_seed: NamespaceSeed,
    multipliers: tuple[HeterogeneityMultiplier, ...],
) -> tuple[DomainQuantitySkew, ...]:
    if len(multipliers) != len(NBAIOT_DOMAIN_ORDER):
        raise ValueError("quantity-skew multiplier count must match N-BaIoT domain count")
    ordered_domains = deterministic_domain_order(
        NBAIOT_DOMAIN_ORDER,
        QUANTITY_SKEW_SEPARATOR,
        heterogeneity_namespace_seed,
    )
    return tuple(
        DomainQuantitySkew(domain=domain, multiplier=multiplier)
        for domain, multiplier in zip(ordered_domains, multipliers, strict=True)
    )


def exclude_source_from_quantity_skew(
    assignments: tuple[DomainQuantitySkew, ...],
    source_domain: NBaiotDomain,
) -> tuple[DomainQuantitySkew, ...]:
    return tuple(assignment for assignment in assignments if assignment.domain is not source_domain)


def quantity_skew_multiplier_for_domain(
    assignments: tuple[DomainQuantitySkew, ...],
    domain: NBaiotDomain,
) -> HeterogeneityMultiplier:
    for assignment in assignments:
        if assignment.domain is domain:
            return assignment.multiplier
    raise ValueError(f"no quantity-skew multiplier assigned to {domain.value}")


def apply_quantity_skew_to_cap(
    cap: SamplingCap,
    multiplier: HeterogeneityMultiplier,
) -> SamplingCap:
    return math.floor(cap * multiplier)


def select_heterogeneity_shift_features(
    all_feature_names: tuple[FeatureName, ...],
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
            nbaiot_domain_hash_token(domain),
            feature_name,
        )
    ).digest()
    return 1 if digest[-1] & 1 else -1
