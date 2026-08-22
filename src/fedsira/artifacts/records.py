from pydantic import BaseModel, ConfigDict

from fedsira.domain.enums import ArtifactFamily, ArtifactLifecycleState
from fedsira.domain.records import ArtifactDigest


class ArtifactManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    family: ArtifactFamily
    identity: ArtifactDigest
    checksum: ArtifactDigest
    lifecycle_state: ArtifactLifecycleState
    upstream_identities: tuple[ArtifactDigest, ...]
