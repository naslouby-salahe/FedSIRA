import torch

from fedsira.baselines.references import (
    centralized_reference_local_epochs,
    centralized_reference_pooled_rows,
    fedavg_reference_post_reference_local_epochs,
    fedavg_reference_post_reference_participants,
    fedavg_reference_post_reference_rounds,
    local_only_reference_evaluation_is_domain_local,
    local_only_reference_local_epochs,
    local_only_reference_training_role,
)
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
BASELINES_CONFIG = CONFIG.baselines

SOURCE = NBAIOT_DOMAIN_ORDER[0]


def test_local_only_reference_uses_governed_epoch_count_and_anchor_train_role() -> None:
    assert (
        local_only_reference_local_epochs(BASELINES_CONFIG)
        == BASELINES_CONFIG.local_only_reference_epochs
    )
    assert local_only_reference_training_role() is Role.ANCHOR_TRAIN


def test_local_only_reference_evaluation_is_domain_local() -> None:
    assert local_only_reference_evaluation_is_domain_local(SOURCE, SOURCE) is True
    assert local_only_reference_evaluation_is_domain_local(SOURCE, NBAIOT_DOMAIN_ORDER[1]) is False


def test_centralized_reference_uses_governed_epoch_count() -> None:
    assert (
        centralized_reference_local_epochs(BASELINES_CONFIG)
        == BASELINES_CONFIG.centralized_reference_epochs
    )


def test_centralized_reference_pooled_rows_concatenates_in_canonical_domain_order() -> None:
    domain_rows = {
        NBAIOT_DOMAIN_ORDER[1]: torch.full((2, 3), 1.0),
        NBAIOT_DOMAIN_ORDER[0]: torch.full((3, 3), 0.0),
    }
    pooled = centralized_reference_pooled_rows(domain_rows)
    assert pooled.shape == (5, 3)
    assert torch.equal(pooled[:3], torch.zeros(3, 3))
    assert torch.equal(pooled[3:], torch.ones(2, 3))


def test_fedavg_reference_post_reference_budget() -> None:
    assert (
        fedavg_reference_post_reference_rounds(BASELINES_CONFIG)
        == BASELINES_CONFIG.fedavg_post_reference_rounds
    )
    assert fedavg_reference_post_reference_local_epochs() == 1


def test_fedavg_reference_post_reference_participants_includes_source_when_available() -> None:
    eligible = NBAIOT_DOMAIN_ORDER[1:4]
    with_source = fedavg_reference_post_reference_participants(eligible, SOURCE, True)
    assert SOURCE in with_source
    assert set(with_source) == set(eligible) | {SOURCE}
    assert list(with_source) == [d for d in NBAIOT_DOMAIN_ORDER if d in with_source]


def test_fedavg_reference_post_reference_participants_excludes_source_when_unavailable() -> None:
    eligible = NBAIOT_DOMAIN_ORDER[1:4]
    without_source = fedavg_reference_post_reference_participants(eligible, SOURCE, False)
    assert SOURCE not in without_source
    assert set(without_source) == set(eligible)
