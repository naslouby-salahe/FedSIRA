from fedsira.domain.types import (
    ArtifactDigest,
    FrozenDomainModel,
    InvariantChecksPassed,
    SchemaVersion,
    TextValue,
)

SmokeCheckName = TextValue
SmokeCheckDetail = TextValue


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
    code_revision: TextValue | None
