from pathlib import Path

import pandas
import pytest
import torch

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.acquisition import DiscoveredCsvFile
from fedsira.datasets.nbaiot.materialization import materialize_nbaiot_prepared_views
from fedsira.datasets.nbaiot.preprocessing import NBAIOT_PRIMARY_PREDICTOR_COUNT
from fedsira.datasets.nbaiot.schema import NBaiotClass, NBaiotDomain
from fedsira.experiments.real_evidence import (
    RealAnchor,
    evaluate_domain,
    non_source_domains,
    real_evidence_available,
    train_anchor,
    train_domain_reproduction_delta,
)
from fedsira.models.mlp import FedSIRAClassifier, trainable_parameter_count

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
DOMAINS = (
    NBaiotDomain.DANMINI_DOORBELL,
    NBaiotDomain.ENNIO_DOORBELL,
    NBaiotDomain.ECOBEE_THERMOSTAT,
)
CLASSES = (NBaiotClass.BENIGN, NBaiotClass.GAFGYT_COMBO, NBaiotClass.GAFGYT_JUNK)


def _feature_names() -> list[str]:
    return [f"feature_{index:03d}" for index in range(NBAIOT_PRIMARY_PREDICTOR_COUNT)]


def _write_csv(path: Path, row_count: int, offset: float) -> None:
    frame = pandas.DataFrame(
        {name: [offset + index * 0.001 for index in range(row_count)] for name in _feature_names()}
    )
    frame.to_csv(path, index=False)


def _prepare_real_evidence(root: Path) -> Path:
    discovered: list[DiscoveredCsvFile] = []
    for domain_index, domain in enumerate(DOMAINS):
        for class_index, class_id in enumerate(CLASSES):
            relative_path = f"{class_id.value}.csv"
            absolute_path = root / "raw" / domain.value / relative_path
            absolute_path.parent.mkdir(parents=True, exist_ok=True)
            _write_csv(absolute_path, row_count=3000, offset=domain_index + class_index)
            discovered.append(
                DiscoveredCsvFile(
                    domain=domain,
                    class_id=class_id,
                    relative_path=relative_path,
                    file_sha256=f"{domain_index}{class_index}" * 32,
                    absolute_path=absolute_path,
                )
            )
    prepared_root = root / "prepared"
    scaler_root = root / "scaler"
    materialize_nbaiot_prepared_views(
        discovered, CONFIG, prepared_root, scaler_root, overwrite=True
    )
    return prepared_root


@pytest.fixture(scope="module")
def prepared_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _prepare_real_evidence(tmp_path_factory.mktemp("real-evidence"))


@pytest.fixture(scope="module")
def anchor(prepared_root: Path) -> RealAnchor:
    result = train_anchor(prepared_root, CONFIG, master_seed=1)
    assert result is not None
    return result


def test_real_evidence_available_reflects_parquet_presence(
    tmp_path: Path, prepared_root: Path
) -> None:
    assert not real_evidence_available(tmp_path)
    assert real_evidence_available(prepared_root)


def test_train_anchor_produces_a_flat_parameter_vector_of_the_expected_shape(
    anchor: RealAnchor,
) -> None:
    assert anchor.input_width == NBAIOT_PRIMARY_PREDICTOR_COUNT
    expected_parameter_count = trainable_parameter_count(
        FedSIRAClassifier(anchor.input_width, anchor.output_width)
    )
    assert anchor.flat_parameters.shape == (expected_parameter_count,)
    assert torch.isfinite(anchor.flat_parameters).all()


def test_train_anchor_returns_none_without_prepared_data(tmp_path: Path) -> None:
    assert train_anchor(tmp_path, CONFIG, master_seed=1) is None


def test_train_domain_reproduction_delta_is_nonzero_and_finite(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    delta = train_domain_reproduction_delta(
        prepared_root, CONFIG, master_seed=1, anchor=anchor, domain=DOMAINS[0]
    )
    assert delta is not None
    assert delta.shape == anchor.flat_parameters.shape
    assert torch.isfinite(delta).all()
    assert torch.any(delta != 0.0)


def test_train_domain_reproduction_delta_is_none_without_target_rows(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    delta = train_domain_reproduction_delta(
        prepared_root, CONFIG, master_seed=1, anchor=anchor, domain=NBaiotDomain.SAMSUNG_WEBCAM
    )
    assert delta is None


def test_evaluate_domain_reports_defined_target_metrics_on_report_test(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    metrics = evaluate_domain(
        prepared_root, anchor, anchor.flat_parameters, DOMAINS[0], Role.REPORT_TEST
    )
    assert metrics is not None
    assert metrics.target_f1.value is not None
    assert metrics.supported_macro_f1.value is not None
    assert metrics.benign_far.value is not None


def test_evaluate_domain_returns_none_without_report_test_rows(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    metrics = evaluate_domain(
        prepared_root,
        anchor,
        anchor.flat_parameters,
        NBaiotDomain.SAMSUNG_WEBCAM,
        Role.REPORT_TEST,
    )
    assert metrics is None


def test_non_source_domains_excludes_only_the_source() -> None:
    domains = non_source_domains(NBaiotDomain.DANMINI_DOORBELL)
    assert NBaiotDomain.DANMINI_DOORBELL not in domains
    assert len(domains) == 8
