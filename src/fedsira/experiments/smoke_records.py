from fedsira.domain.enums import SmokeCheckName
from fedsira.domain.types import (
    ArtifactDigest,
    CodeRevision,
    FrozenDomainModel,
    InvariantChecksPassed,
    SchemaVersion,
    SmokeCheckDetail,
)


class SmokeCheckResult(FrozenDomainModel):
    name: SmokeCheckName
    passed: InvariantChecksPassed
    detail: SmokeCheckDetail | None = None


class SmokeSuiteResult(FrozenDomainModel):
    checks: tuple[SmokeCheckResult, ...]

    @property
    def passed(self) -> InvariantChecksPassed:
        return all(check.passed for check in self.checks)


class PersistedSmokeRecord(FrozenDomainModel):
    schema_version: SchemaVersion
    passed: InvariantChecksPassed
    checks: tuple[SmokeCheckResult, ...]
    configuration_digest: ArtifactDigest
    code_revision: CodeRevision | None
