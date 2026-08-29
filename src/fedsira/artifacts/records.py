from typing import TypeAlias

from fedsira.domain.enums import ArtifactFamily, ArtifactLifecycleState
from fedsira.domain.records import (
    ArtifactDigest,
    DatasetClassToken,
    DatasetManifestDigest,
    FrozenDomainModel,
    NonNegativeInt,
    PositiveInt,
    PredictorCountMatchesOfficial,
)

ArtifactPayloadBytes: TypeAlias = bytes


class ArtifactManifest(FrozenDomainModel):
    family: ArtifactFamily
    identity: ArtifactDigest
    checksum: ArtifactDigest
    lifecycle_state: ArtifactLifecycleState
    upstream_identities: tuple[ArtifactDigest, ...]

    def with_lifecycle_state(
        self,
        lifecycle_state: ArtifactLifecycleState,
    ) -> "ArtifactManifest":
        return ArtifactManifest(
            family=self.family,
            identity=self.identity,
            checksum=self.checksum,
            lifecycle_state=lifecycle_state,
            upstream_identities=self.upstream_identities,
        )


class NBaiotDatasetManifestPayload(FrozenDomainModel):
    dataset_file_manifest_hash: DatasetManifestDigest
    structurally_unavailable_classes: tuple[DatasetClassToken, ...]


class CICIoT2023DatasetManifestPayload(FrozenDomainModel):
    dataset_file_manifest_hash: DatasetManifestDigest
    file_count: PositiveInt
    raw_row_count: NonNegativeInt
    retained_row_count: NonNegativeInt
    excluded_row_count: NonNegativeInt
    predictor_count: PositiveInt
    official_expected_predictor_count: PositiveInt
    predictor_count_matches_official: PredictorCountMatchesOfficial
    class_registry: tuple[DatasetClassToken, ...]
    pseudo_domain_count: PositiveInt


DatasetManifestPayload = NBaiotDatasetManifestPayload | CICIoT2023DatasetManifestPayload
