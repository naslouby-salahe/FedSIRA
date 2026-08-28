import hashlib
from enum import StrEnum
from typing import Self

from pydantic import model_validator

from fedsira.domain.records import (
    ArtifactDigest,
    FrozenDomainModel,
    NonEmptyString,
    NonNegativeInt,
    Probability,
)
from fedsira.runtime.determinism import canonical_bytes


class Role(StrEnum):
    ANCHOR_TRAIN = "Anchor Train"
    ANCHOR_VALIDATION = "Anchor Validation"
    POST_REFERENCE_REPLAY = "Post-Reference Replay"
    ROW_VERIFICATION = "Row Verification"
    FINAL_GATE = "Final Gate"
    REPORT_TEST = "Report Test"
    SOURCE_PROPOSAL = "Source Proposal"
    CANDIDATE_SCREEN = "Candidate Screen"
    REPRODUCTION = "Reproduction"


ROLE_HASH_TOKEN: dict[Role, NonEmptyString] = {
    Role.ANCHOR_TRAIN: "ANCHOR_TRAIN",
    Role.ANCHOR_VALIDATION: "ANCHOR_VALIDATION",
    Role.POST_REFERENCE_REPLAY: "POST_REFERENCE_REPLAY",
    Role.ROW_VERIFICATION: "ROW_VERIFICATION",
    Role.FINAL_GATE: "FINAL_GATE",
    Role.REPORT_TEST: "REPORT_TEST",
    Role.SOURCE_PROPOSAL: "SOURCE_PROPOSAL",
    Role.CANDIDATE_SCREEN: "CANDIDATE_SCREEN",
    Role.REPRODUCTION: "REPRODUCTION",
}

SUPPORTED_ROLE_ORDER: tuple[Role, ...] = (
    Role.ANCHOR_TRAIN,
    Role.ANCHOR_VALIDATION,
    Role.POST_REFERENCE_REPLAY,
    Role.ROW_VERIFICATION,
    Role.FINAL_GATE,
    Role.REPORT_TEST,
)

TARGET_ROLE_ORDER: tuple[Role, ...] = (
    Role.SOURCE_PROPOSAL,
    Role.CANDIDATE_SCREEN,
    Role.REPRODUCTION,
    Role.ROW_VERIFICATION,
    Role.FINAL_GATE,
    Role.REPORT_TEST,
)

TRAINING_AND_SCREENING_ROLES: frozenset[Role] = frozenset(
    {
        Role.ANCHOR_TRAIN,
        Role.ANCHOR_VALIDATION,
        Role.POST_REFERENCE_REPLAY,
        Role.SOURCE_PROPOSAL,
        Role.CANDIDATE_SCREEN,
        Role.REPRODUCTION,
    }
)

EVIDENCE_ROLES: frozenset[Role] = frozenset(
    {Role.ROW_VERIFICATION, Role.FINAL_GATE, Role.REPORT_TEST}
)


class DatasetExclusionReason(StrEnum):
    NON_FINITE_PREDICTOR = "non_finite_predictor"
    UNPARSEABLE_PREDICTOR = "unparseable_predictor"


class RoleWindow(FrozenDomainModel):
    role: Role
    lower_inclusive: Probability
    upper_exclusive: Probability

    @model_validator(mode="after")
    def _validate_bounds(self) -> Self:
        if self.lower_inclusive >= self.upper_exclusive:
            raise ValueError(
                f"role interval for {self.role.value} must satisfy lower < upper, "
                f"got [{self.lower_inclusive}, {self.upper_exclusive})"
            )
        return self

    def contains(self, normalized_position: Probability) -> bool:
        return self.lower_inclusive <= normalized_position < self.upper_exclusive


def role_for_normalized_position(
    normalized_position: Probability, windows: tuple[RoleWindow, ...]
) -> Role | None:
    for window in windows:
        if window.contains(normalized_position):
            return window.role
    return None


if not TRAINING_AND_SCREENING_ROLES.isdisjoint(EVIDENCE_ROLES):
    raise AssertionError("evidence roles must never also be eligible for training/screening")


def compute_sample_id(
    sample_id_prefix: NonEmptyString,
    normalized_relative_csv_path: NonEmptyString,
    file_sha256: ArtifactDigest,
    zero_based_original_row_index: NonNegativeInt,
) -> ArtifactDigest:
    return hashlib.sha256(
        canonical_bytes(
            sample_id_prefix,
            normalized_relative_csv_path,
            file_sha256,
            zero_based_original_row_index,
        )
    ).hexdigest()
