import pytest
from pydantic import TypeAdapter, ValidationError

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.config.schema import RoleInterval, ScalingConfig
from fedsira.config.validation import validate_scientific_config


def test_production_config_passes_cross_field_validation() -> None:
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    validate_scientific_config(config)


def test_smoke_seed_colliding_with_master_seed_is_rejected() -> None:
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    colliding = config.model_copy(
        update={
            "seeds_and_determinism": config.seeds_and_determinism.model_copy(
                update={"smoke_seed": config.seeds_and_determinism.master_seeds[0]}
            )
        }
    )
    with pytest.raises(ValueError):
        validate_scientific_config(colliding)


def test_analysis_seed_colliding_with_master_seed_is_rejected() -> None:
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    colliding = config.model_copy(
        update={
            "seeds_and_determinism": config.seeds_and_determinism.model_copy(
                update={"analysis_seed": config.seeds_and_determinism.master_seeds[1]}
            )
        }
    )
    with pytest.raises(ValueError):
        validate_scientific_config(colliding)


def test_role_interval_end_before_start_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(RoleInterval).validate_python((0.5, 0.1))


def test_scaling_clip_bounds_reversed_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ScalingConfig(zero_standard_deviation_scale=1.0, clip_min=10.0, clip_max=-10.0)
