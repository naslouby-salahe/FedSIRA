from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fedsira.config.loading import (
    PRODUCTION_CONFIG_PATH,
    TEST_FIXTURE_CONFIG_PATH,
    load_scientific_config,
    load_test_fixture_config,
)
from fedsira.config.schema import ScientificConfig, TestFixtureConfig
from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.preprocessing import assign_stream_roles_and_sample_ids
from fedsira.datasets.nbaiot.schema import NBaiotClass, NBaiotDomain
from fedsira.evaluation.statistics import exact_sign_flip_two_sided_p_value, holm_adjusted_p_values
from fedsira.protocol.reproduction import validate_commitment_exists_before_verifier_assignment
from fedsira.protocol.synthesis import krum_committee_is_admissible
from fedsira.protocol.theory import (
    diagnostic_at_least_two_byzantine_probability,
    minimum_honest_positive_count,
)
from fedsira.protocol.verification import verifier_is_eligible

SMOKE_RECORD_SCHEMA_VERSION = "fedsira|smoke_record|1"

_DANMINI = NBaiotDomain.DANMINI_DOORBELL
_ENNIO = NBaiotDomain.ENNIO_DOORBELL


@dataclass(frozen=True)
class SmokeCheckResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class SmokeSuiteResult:
    checks: tuple[SmokeCheckResult, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


def _data_invariants(config: ScientificConfig) -> tuple[SmokeCheckResult, ...]:
    role_intervals = config.datasets.primary.role_intervals
    sampling_caps = config.datasets.primary.sampling_caps_per_domain
    stream_row_count = sampling_caps.reproduction_target

    assignments = assign_stream_roles_and_sample_ids(
        dataset_file_sha256="a" * 64,
        domain_hash_token="DANMINI_DOORBELL",
        class_id=NBaiotClass.GAFGYT_COMBO,
        normalized_relative_csv_path="Danmini Doorbell/combo.csv",
        stream_row_count=stream_row_count,
        role_intervals=role_intervals,
        sampling_caps_per_domain=sampling_caps,
    )
    roles_seen = {assignment.role for assignment in assignments}
    no_target_in_anchor = (
        Role.ANCHOR_TRAIN not in roles_seen and Role.ANCHOR_VALIDATION not in roles_seen
    )

    supported_assignments = assign_stream_roles_and_sample_ids(
        dataset_file_sha256="a" * 64,
        domain_hash_token="DANMINI_DOORBELL",
        class_id=NBaiotClass.BENIGN,
        normalized_relative_csv_path="Danmini Doorbell/benign_traffic.csv",
        stream_row_count=stream_row_count,
        role_intervals=role_intervals,
        sampling_caps_per_domain=sampling_caps,
    )
    row_to_roles: dict[int, set[Role]] = {}
    for assignment in supported_assignments:
        row_to_roles.setdefault(assignment.original_row_index, set()).add(assignment.role)
    no_overlap = all(len(roles) == 1 for roles in row_to_roles.values())

    return (
        SmokeCheckResult(
            "no target sample in anchor roles",
            no_target_in_anchor,
        ),
        SmokeCheckResult(
            "no cross-role sample overlap",
            no_overlap,
        ),
    )


def _protocol_invariants(config: ScientificConfig) -> tuple[SmokeCheckResult, ...]:
    source_not_verifier = not verifier_is_eligible(_DANMINI, _DANMINI, _ENNIO)
    honest_positive = minimum_honest_positive_count(2, 1) == 1
    krum_admissible = krum_committee_is_admissible(5, 1)
    krum_three_rejected = not krum_committee_is_admissible(3, 1)

    commitment_rejected = False
    try:
        validate_commitment_exists_before_verifier_assignment(None)
    except ValueError:
        commitment_rejected = True

    eligible_pool_size = len(NBaiotDomain) - 2
    probability = diagnostic_at_least_two_byzantine_probability(eligible_pool_size, 2, 3)
    tolerance = config.validation_tolerances.random_committee_probability_absolute
    expected_probability = 1 / eligible_pool_size
    probability_matches = abs(probability - expected_probability) < tolerance

    return (
        SmokeCheckResult(
            "source cannot be verifier",
            source_not_verifier,
        ),
        SmokeCheckResult(
            "2 positives with f_V=1 implies at least one honest positive",
            honest_positive,
        ),
        SmokeCheckResult(
            "Krum n=5 f=1 admissible",
            krum_admissible,
        ),
        SmokeCheckResult(
            "Krum n=3 f=1 rejected",
            krum_three_rejected,
        ),
        SmokeCheckResult(
            "verifier assignment before commitment throws",
            commitment_rejected,
        ),
        SmokeCheckResult(
            "random committee contamination probability 1/7 for b=2",
            probability_matches,
            f"observed {probability:.12f}",
        ),
    )


def _mathematical_invariants(
    config: ScientificConfig, fixture_config: TestFixtureConfig
) -> tuple[SmokeCheckResult, ...]:
    sample_count = fixture_config.sign_flip_sample_count
    sign_flip = exact_sign_flip_two_sided_p_value([1.0] * sample_count)
    sign_flip_matches = sign_flip == fixture_config.sign_flip_expected_p_value
    holm = holm_adjusted_p_values(fixture_config.holm_fixture_raw_p_values)
    holm_matches = holm == fixture_config.holm_fixture_adjusted_p_values
    return (
        SmokeCheckResult(
            "exact sign-flip test enumerates all assignments",
            sign_flip_matches,
            f"p={sign_flip:.10f}",
        ),
        SmokeCheckResult(
            "Holm adjustment matches hand fixture",
            holm_matches,
        ),
    )


def run_smoke_suite(
    config_path: Path = PRODUCTION_CONFIG_PATH,
    overwrite: bool = False,
) -> SmokeSuiteResult:
    config = load_scientific_config(config_path)
    fixture_config = load_test_fixture_config(TEST_FIXTURE_CONFIG_PATH)
    checks = (
        *_data_invariants(config),
        *_protocol_invariants(config),
        *_mathematical_invariants(config, fixture_config),
    )
    return SmokeSuiteResult(checks=checks)


def render_smoke(result: SmokeSuiteResult) -> str:
    lines = ["FedSIRA smoke suite"]
    for check in result.checks:
        marker = "PASS" if check.passed else "FAIL"
        detail = f" ({check.detail})" if check.detail else ""
        lines.append(f"  [{marker}] {check.name}{detail}")
    lines.append(f"result: {'PASSED' if result.passed else 'FAILED'}")
    return "\n".join(lines)
