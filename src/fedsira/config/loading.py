from pathlib import Path
from typing import cast

import yaml
from pydantic import ValidationError

from fedsira.config.schema import ScientificConfig, SmokeConfig, TestFixtureConfig
from fedsira.config.validation import validate_scientific_config

PRODUCTION_CONFIG_PATH = Path("configs/fedsira.yaml")
TEST_FIXTURE_CONFIG_PATH = Path("configs/tests.yml")
SMOKE_CONFIG_PATH = Path("configs/smoke.yml")


def _read_yaml_mapping(path: Path) -> dict[str, object]:
    try:
        with path.open(encoding="utf-8") as handle:
            parsed: object = yaml.safe_load(handle)
    except OSError as error:
        raise ValueError(f"cannot read configuration file {path}: {error}") from error
    if not isinstance(parsed, dict):
        raise ValueError(f"configuration file {path} must contain a YAML mapping at the top level")
    return cast("dict[str, object]", parsed)


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
