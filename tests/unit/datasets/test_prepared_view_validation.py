from collections.abc import Iterator
from pathlib import Path

import pytest

from fedsira.datasets.common import view_parquet_path
from fedsira.datasets.prepared_validation import prepared_view_publication_failures
from fedsira.datasets.preprocess import publish_prepared_role_view
from fedsira.domain.enums import DatasetId, Role
from fedsira.runtime import (
    ApplicationContext,
    bound_application_context,
    current_application_context,
)

VIEW_KEY = "DANMINI_DOORBELL_GAFGYT_COMBO_ROW_VERIFICATION"


@pytest.fixture
def prepared_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    monkeypatch.setattr("fedsira.datasets.prepared_validation.REPOSITORY_ROOT", tmp_path)
    monkeypatch.setattr("fedsira.datasets.preprocess.REPOSITORY_ROOT", tmp_path)
    root = tmp_path / "prepared"
    root.mkdir()
    context = current_application_context().model_copy(update={"repository_root": tmp_path})
    with bound_application_context(context):
        yield root


def _materialize_view(root: Path, payload: bytes, row_count: int) -> Path:
    parquet_path = view_parquet_path(root, VIEW_KEY)
    parquet_path.write_bytes(payload)
    (root / f"{VIEW_KEY}.json").write_text(
        '{"class_id": "GAFGYT_COMBO", "domain": "Danmini Doorbell", '
        f'"role": "{Role.ROW_VERIFICATION.value}", "row_count": {row_count}, '
        '"schema_version": "fedsira|prepared_view_metadata|1"}'
    )
    return parquet_path


def test_unpublished_prepared_view_is_rejected(prepared_root: Path) -> None:
    _materialize_view(prepared_root, b"parquet-payload", 3)
    failures = prepared_view_publication_failures(prepared_root)
    assert len(failures) == 1
    assert "has no published Complete artifact" in failures[0]
    assert VIEW_KEY in failures[0]


def test_published_prepared_view_validates_against_its_payload(prepared_root: Path) -> None:
    parquet_path = _materialize_view(prepared_root, b"parquet-payload", 3)
    publish_prepared_role_view(
        DatasetId.N_BAIOT,
        "a" * 64,
        VIEW_KEY,
        Role.ROW_VERIFICATION,
        "GAFGYT_COMBO",
        "Danmini Doorbell",
        3,
        parquet_path,
    )
    assert prepared_view_publication_failures(prepared_root) == ()
    assert prepared_view_publication_failures(prepared_root) == ()


def test_tampered_prepared_view_payload_is_rejected(prepared_root: Path) -> None:
    parquet_path = _materialize_view(prepared_root, b"parquet-payload", 3)
    publish_prepared_role_view(
        DatasetId.N_BAIOT,
        "a" * 64,
        VIEW_KEY,
        Role.ROW_VERIFICATION,
        "GAFGYT_COMBO",
        "Danmini Doorbell",
        3,
        parquet_path,
    )
    assert prepared_view_publication_failures(prepared_root) == ()
    parquet_path.write_bytes(b"parquet-PAYLOAD")
    failures = prepared_view_publication_failures(prepared_root)
    assert any("payload digest" in failure for failure in failures)


def test_resized_prepared_view_payload_is_rejected(prepared_root: Path) -> None:
    parquet_path = _materialize_view(prepared_root, b"parquet-payload", 3)
    publish_prepared_role_view(
        DatasetId.N_BAIOT,
        "a" * 64,
        VIEW_KEY,
        Role.ROW_VERIFICATION,
        "GAFGYT_COMBO",
        "Danmini Doorbell",
        3,
        parquet_path,
    )
    parquet_path.write_bytes(b"parquet-payload-extended")
    failures = prepared_view_publication_failures(prepared_root)
    assert any("bytes but its published artifact declares" in failure for failure in failures)


def test_row_count_disagreeing_with_the_sidecar_is_rejected(prepared_root: Path) -> None:
    parquet_path = _materialize_view(prepared_root, b"parquet-payload", 7)
    publish_prepared_role_view(
        DatasetId.N_BAIOT,
        "a" * 64,
        VIEW_KEY,
        Role.ROW_VERIFICATION,
        "GAFGYT_COMBO",
        "Danmini Doorbell",
        3,
        parquet_path,
    )
    failures = prepared_view_publication_failures(prepared_root)
    assert any("publishes 3 rows but its sidecar declares 7" in failure for failure in failures)


def test_absent_prepared_root_has_no_failures(prepared_root: Path) -> None:
    assert prepared_view_publication_failures(prepared_root / "absent") == ()


def test_repository_root_of_the_bound_context_governs_publication_lookup(
    prepared_root: Path,
) -> None:
    assert current_application_context().repository_root == prepared_root.parent
    assert isinstance(current_application_context(), ApplicationContext)
