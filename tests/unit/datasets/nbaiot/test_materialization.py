from pathlib import Path

import pandas

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.acquisition import DiscoveredCsvFile
from fedsira.datasets.nbaiot.materialization import (
    PreparedView,
    materialize_nbaiot_prepared_views,
)
from fedsira.datasets.nbaiot.preprocessing import NBAIOT_PRIMARY_PREDICTOR_COUNT
from fedsira.datasets.nbaiot.schema import NBaiotClass, NBaiotDomain

TRIGGER_FEATURES = ("MI_dir_L0.1_weight", "H_L0.1_weight", "HH_L0.1_magnitude", "HpHp_L0.1_mean")


def _feature_names() -> list[str]:
    names = [f"feature_{index:03d}" for index in range(NBAIOT_PRIMARY_PREDICTOR_COUNT)]
    for index, trigger in enumerate(TRIGGER_FEATURES):
        names[index] = trigger
    return names


def _write_benign_csv(path: Path, row_count: int) -> None:
    frame = pandas.DataFrame(
        {name: [index * 0.001 for index in range(row_count)] for name in _feature_names()}
    )
    frame.to_csv(path, index=False)


def _discovered_csv(path: Path) -> DiscoveredCsvFile:
    return DiscoveredCsvFile(
        domain=NBaiotDomain.DANMINI_DOORBELL,
        class_id=NBaiotClass.BENIGN,
        relative_path="benign_traffic.csv",
        file_sha256="a" * 64,
        absolute_path=path,
    )


def _storage(tmp_path: Path) -> tuple[Path, Path]:
    return (tmp_path / "prepared", tmp_path / "scaler")


def test_prepared_view_row_count() -> None:
    view = PreparedView(
        domain=NBaiotDomain.DANMINI_DOORBELL,
        class_id=NBaiotClass.BENIGN,
        role=Role.ANCHOR_TRAIN,
        sample_ids=("s1", "s2"),
        features=((0.0,), (1.0,)),
        labels=("BENIGN", "BENIGN"),
    )
    assert view.row_count == 2


def test_materialization_runs_and_writes_artifacts(tmp_path: Path) -> None:
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    csv_path = tmp_path / "benign.csv"
    _write_benign_csv(csv_path, 6000)
    prepared_root, scaler_root = _storage(tmp_path)
    views, moments = materialize_nbaiot_prepared_views(
        [_discovered_csv(csv_path)], config, prepared_root, scaler_root, overwrite=True
    )
    assert views
    assert len(moments.feature_names) == NBAIOT_PRIMARY_PREDICTOR_COUNT
    scaler_json = scaler_root / "nbaiot_scaler.json"
    assert scaler_json.exists()


def test_materialization_is_deterministic(tmp_path: Path) -> None:
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    csv_path = tmp_path / "benign.csv"
    _write_benign_csv(csv_path, 6000)
    prepared_root, scaler_root = _storage(tmp_path)
    views_one, moments_one = materialize_nbaiot_prepared_views(
        [_discovered_csv(csv_path)], config, prepared_root, scaler_root, overwrite=True
    )
    prepared_two = tmp_path / "prepared_two"
    views_two, moments_two = materialize_nbaiot_prepared_views(
        [_discovered_csv(csv_path)], config, prepared_two, scaler_root, overwrite=True
    )
    assert tuple((view.role, view.row_count) for view in views_one) == tuple(
        (view.role, view.row_count) for view in views_two
    )
    assert moments_one.means == moments_two.means
    assert moments_one.standard_deviations == moments_two.standard_deviations


def test_materialization_standardized_features_are_finite_and_clipped(tmp_path: Path) -> None:
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    csv_path = tmp_path / "benign.csv"
    _write_benign_csv(csv_path, 6000)
    prepared_root, scaler_root = _storage(tmp_path)
    views, _moments = materialize_nbaiot_prepared_views(
        [_discovered_csv(csv_path)], config, prepared_root, scaler_root, overwrite=True
    )
    assert views
    clip_max = config.datasets.primary.scaling.clip_max
    clip_min = config.datasets.primary.scaling.clip_min
    for view in views:
        for row in view.features:
            assert all(clip_min <= value <= clip_max for value in row)
