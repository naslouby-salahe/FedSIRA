from pathlib import Path

import pytest
from pydantic import ValidationError

from fedsira.config.loading import (
    PRODUCTION_CONFIG_PATH,
    SMOKE_CONFIG_PATH,
    TEST_FIXTURE_CONFIG_PATH,
    load_scientific_config,
    load_smoke_config,
    load_test_fixture_config,
)


def test_production_config_loads_and_validates() -> None:
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    assert config.datasets.primary.name.value == "N-BaIoT"
    assert config.seeds_and_determinism.master_seeds[0] == 1103


def test_test_fixture_config_loads() -> None:
    config = load_test_fixture_config(TEST_FIXTURE_CONFIG_PATH)
    assert config.fixture_format_version == 1


def test_smoke_config_loads() -> None:
    config = load_smoke_config(SMOKE_CONFIG_PATH)
    assert config.smoke_format_version == 1


def test_missing_file_raises_value_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        load_scientific_config(tmp_path / "does-not-exist.yaml")


def test_non_mapping_yaml_raises_value_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("- 1\n- 2\n")
    with pytest.raises(ValueError):
        load_scientific_config(bad)


def test_extra_key_is_rejected(tmp_path: Path) -> None:
    source = PRODUCTION_CONFIG_PATH.read_text(encoding="utf-8")
    bad = tmp_path / "extra.yaml"
    bad.write_text(source + "unexpected_top_level_key: 1\n")
    with pytest.raises(ValueError):
        load_scientific_config(bad)


def test_config_is_immutable() -> None:
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    with pytest.raises(ValidationError):
        setattr(config.seeds_and_determinism, "analysis_seed", 1)
