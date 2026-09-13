from pathlib import Path

import pytest

from fedsira.artifacts.paths import artifact_slot_directory
from fedsira.artifacts.store import ArtifactManifest, read_current_artifact
from fedsira.domain.enums import (
    ArtifactDependencyKind,
    ArtifactFamily,
    ArtifactInstanceLabel,
    ExperimentName,
    TableName,
)
from fedsira.reporting.publication import (
    TableFigureExportPayload,
    TableFigureSourceDataPayload,
    publish_table_figure_export,
    publish_table_figure_source_data,
    table_figure_export_slot,
    table_figure_source_data_slot,
)
from fedsira.reporting.tables import RenderedTable
from fedsira.reporting.verification import (
    artifact_manifest_dependency_failures,
    verify_report_export_currency,
)

EXPERIMENT = ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION


@pytest.fixture
def isolated_repository(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr("fedsira.reporting.publication.REPOSITORY_ROOT", tmp_path)
    return tmp_path


def _rendered_table(csv_text: str) -> RenderedTable:
    return RenderedTable(name=TableName.CELL_METRICS, csv_text=csv_text)


def _products(root: Path, csv_text: str) -> tuple[Path, Path]:
    tables_root = root / "tables" / "main"
    figures_root = root / "figures" / "main"
    tables_root.mkdir(parents=True, exist_ok=True)
    figures_root.mkdir(parents=True, exist_ok=True)
    table_path = tables_root / "Cell Metrics.csv"
    table_path.write_text(csv_text)
    figure_path = figures_root / "Primary Security-Utility Tradeoff.png"
    figure_path.write_bytes(b"png-bytes")
    return table_path, figure_path


def _publish_source_data(
    experiment_root: Path,
    csv_text: str,
) -> tuple[ArtifactManifest, Path]:
    table_path, figure_path = _products(experiment_root, csv_text)
    manifest, _reused = publish_table_figure_source_data(
        EXPERIMENT,
        "e" * 64,
        (_rendered_table(csv_text),),
        (str(figure_path),),
        (str(table_path),),
        (str(table_path),),
    )
    return manifest, table_path


def test_source_data_records_table_and_figure_content(isolated_repository: Path) -> None:
    csv_text = "experiment,method\nA,B\nA,C\n"
    manifest, table_path = _publish_source_data(isolated_repository, csv_text)
    assert manifest.family is ArtifactFamily.TABLE_FIGURE_SOURCE_DATA
    slot = table_figure_source_data_slot(EXPERIMENT)
    assert slot.instance == ArtifactInstanceLabel.SOURCE_DATA
    assert slot.experiment == EXPERIMENT
    current = read_current_artifact(isolated_repository / artifact_slot_directory(slot))
    assert current is not None
    _stored, payload = current
    restored = TableFigureSourceDataPayload.model_validate_json(payload)
    assert restored.execution_digest == "e" * 64
    assert restored.tables[0].row_count == 2
    assert restored.figures[0].content_bytes == len(b"png-bytes")
    assert restored.evidence[0].evidence_name == table_path.name
    assert manifest.dependencies[0].digest == "e" * 64


def test_source_data_identity_changes_when_rendered_content_changes(
    isolated_repository: Path,
) -> None:
    first, _reused = _publish_source_data(isolated_repository, "experiment,method\nA,B\n")
    second, _reused_again = _publish_source_data(
        isolated_repository, "experiment,method\nA,B\nA,C\n"
    )
    assert first.identity != second.identity


def test_export_records_products_relative_to_the_experiment_root(
    isolated_repository: Path,
) -> None:
    source_data, table_path = _publish_source_data(isolated_repository, "experiment,method\nA,B\n")
    manifest, _reused = publish_table_figure_export(
        EXPERIMENT,
        source_data.identity,
        isolated_repository,
        (str(table_path),),
    )
    assert manifest.family is ArtifactFamily.TABLE_FIGURE_REPORT_EXPORT
    assert manifest.slot.instance == ArtifactInstanceLabel.REPORT_EXPORT
    assert manifest.dependencies[0].kind is ArtifactDependencyKind.ARTIFACT
    assert manifest.dependencies[0].digest == source_data.identity
    current = read_current_artifact(
        isolated_repository / artifact_slot_directory(table_figure_export_slot(EXPERIMENT))
    )
    assert current is not None
    _stored, payload = current
    restored = TableFigureExportPayload.model_validate_json(payload)
    assert restored.exported_paths == ("tables/main/Cell Metrics.csv",)


def test_report_gate_requires_the_published_source_data_artifact(
    isolated_repository: Path,
) -> None:
    source_data, table_path = _publish_source_data(isolated_repository, "experiment,method\nA,B\n")
    export, _reused = publish_table_figure_export(
        EXPERIMENT,
        source_data.identity,
        isolated_repository,
        (str(table_path),),
    )
    assert artifact_manifest_dependency_failures((export,)) == (
        f"{export.slot.family.value}/{export.slot.instance}: source-data upstream "
        f"{source_data.identity} is not a published artifact",
    )
    assert artifact_manifest_dependency_failures((source_data, export)) == ()


def test_export_currency_flags_a_stale_source_data_identity(isolated_repository: Path) -> None:
    source_data, table_path = _publish_source_data(isolated_repository, "experiment,method\nA,B\n")
    publish_table_figure_export(
        EXPERIMENT,
        source_data.identity,
        isolated_repository,
        (str(table_path),),
    )
    relative = ("tables/main/Cell Metrics.csv",)
    assert (
        verify_report_export_currency(
            EXPERIMENT, source_data.identity, isolated_repository, relative
        )
        == ()
    )
    stale = verify_report_export_currency(
        EXPERIMENT,
        ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION * 64,
        isolated_repository,
        relative,
    )
    assert any("stale for its source data" in failure for failure in stale)
    missing = verify_report_export_currency(
        EXPERIMENT,
        source_data.identity,
        isolated_repository,
        ("tables/main/Absent.csv",),
    )
    assert any("does not name its own products" in failure for failure in missing)
