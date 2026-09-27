from fedsira.domain.enums import DatasetId
from fedsira.experiments.checkpoints import checkpoint_stage_instance


def test_checkpoint_slot_instance_is_distinct_per_dataset() -> None:
    primary = checkpoint_stage_instance(DatasetId.N_BAIOT, 1103, "final")
    secondary = checkpoint_stage_instance(DatasetId.CICIOT2023, 1103, "final")

    assert primary != secondary
