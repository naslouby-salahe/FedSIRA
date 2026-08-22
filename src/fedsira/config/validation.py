from fedsira.config.schema import ScientificConfig


def validate_scientific_config(config: ScientificConfig) -> None:
    seeds = config.seeds_and_determinism
    if seeds.smoke_seed in seeds.master_seeds or seeds.smoke_seed == seeds.analysis_seed:
        raise ValueError(
            "seeds_and_determinism.smoke_seed must not collide with another seed authority"
        )
    if seeds.analysis_seed in seeds.master_seeds:
        raise ValueError("seeds_and_determinism.analysis_seed must not collide with a master seed")
