from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TypeAlias

import yaml
from pydantic import ValidationError

from fedsira.config.models import ScientificConfig, SmokeConfig, TestFixtureConfig
from fedsira.domain.types import TextValue

PRODUCTION_CONFIG_PATH = Path("configs/fedsira.yaml")
TEST_FIXTURE_CONFIG_PATH = Path("configs/tests.yml")
SMOKE_CONFIG_PATH = Path("configs/smoke.yaml")


def validate_scientific_config(config: ScientificConfig) -> None:
    seeds = config.seeds_and_determinism
    if seeds.smoke_seed in seeds.master_seeds or seeds.smoke_seed == seeds.analysis_seed:
        raise ValueError(
            "seeds_and_determinism.smoke_seed must not collide with another seed authority"
        )
    if seeds.analysis_seed in seeds.master_seeds:
        raise ValueError("seeds_and_determinism.analysis_seed must not collide with a master seed")

YamlValue: TypeAlias = (
    "None | bool | int | float | TextValue | Sequence[YamlValue] | Mapping[TextValue, YamlValue]"
)


def _read_yaml_mapping(path: Path) -> Mapping[TextValue, YamlValue]:
    try:
        with path.open(encoding="utf-8") as handle:
            parsed: YamlValue = yaml.safe_load(handle)
    except OSError as error:
        raise ValueError(f"cannot read configuration file {path}: {error}") from error
    if not isinstance(parsed, Mapping):
        raise ValueError(f"configuration file {path} must contain a YAML mapping at the top level")
    return parsed


def load_scientific_config(path: Path = PRODUCTION_CONFIG_PATH) -> ScientificConfig:
    payload = _read_yaml_mapping(path)
    try:
        config = ScientificConfig.model_validate(payload)
    except ValidationError as error:
        raise ValueError(f"invalid scientific configuration in {path}: {error}") from error
    validate_scientific_config(config)
    return config


def load_test_fixture_config(path: Path = TEST_FIXTURE_CONFIG_PATH) -> TestFixtureConfig:
    payload = _read_yaml_mapping(path)
    try:
        return TestFixtureConfig.model_validate(payload)
    except ValidationError as error:
        raise ValueError(f"invalid test fixture configuration in {path}: {error}") from error


def load_smoke_config(path: Path = SMOKE_CONFIG_PATH) -> SmokeConfig:
    payload = _read_yaml_mapping(path)
    try:
        return SmokeConfig.model_validate(payload)
    except ValidationError as error:
        raise ValueError(f"invalid smoke configuration in {path}: {error}") from error
