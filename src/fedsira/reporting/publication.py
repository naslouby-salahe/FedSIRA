import hashlib
from pathlib import Path

from fedsira.artifacts.paths import artifact_slot_directory, artifact_staging_root
from fedsira.artifacts.store import (
    ArtifactDependency,
    ArtifactManifest,
    ArtifactReuseDecision,
    ArtifactSlot,
    publish_artifact,
    read_current_artifact,
)
from fedsira.domain.enums import ArtifactDependencyKind, ArtifactFamily, ArtifactProducer
from fedsira.domain.types import (
    ArtifactDigest,
    ArtifactInstanceToken,
    ByteCount,
    ExperimentName,
    FigureName,
    FrozenDomainModel,
    ProcedureIdentity,
    RelativePathText,
    RepositoryPath,
    RowCount,
    SchemaVersion,
    TableName,
    TextValue,
)
from fedsira.reporting.tables import RenderedTable
from fedsira.runtime import REPOSITORY_ROOT

PUBLICATION_SCHEMA_VERSION: SchemaVersion = "fedsira|publication|1"
TABLE_FIGURE_SOURCE_DATA_PROCEDURE_IDENTITY: ProcedureIdentity = (
    "fedsira|table_figure_source_data|1"
)
TABLE_FIGURE_REPORT_EXPORT_PROCEDURE_IDENTITY: ProcedureIdentity = (
    "fedsira|table_figure_report_export|1"
)
SOURCE_DATA_INSTANCE: ArtifactInstanceToken = "source-data"
REPORT_EXPORT_INSTANCE: ArtifactInstanceToken = "report-export"


class RenderedTableIdentity(FrozenDomainModel):
    table: TableName
    row_count: RowCount
    content_digest: ArtifactDigest


class RenderedFigureIdentity(FrozenDomainModel):
    figure: FigureName
    content_bytes: ByteCount
    content_digest: ArtifactDigest


class ReportEvidenceIdentity(FrozenDomainModel):
    evidence_name: TextValue
    content_digest: ArtifactDigest


class TableFigureSourceDataPayload(FrozenDomainModel):
    schema_version: SchemaVersion
    experiment: ExperimentName
    execution_digest: ArtifactDigest
    tables: tuple[RenderedTableIdentity, ...]
    figures: tuple[RenderedFigureIdentity, ...]
    evidence: tuple[ReportEvidenceIdentity, ...]


class TableFigureExportPayload(FrozenDomainModel):
    schema_version: SchemaVersion
    experiment: ExperimentName
    source_data_identity: ArtifactDigest
    exported_paths: tuple[RelativePathText, ...]


def content_digest(path: RepositoryPath) -> ArtifactDigest:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def table_figure_source_data_slot(experiment: ExperimentName) -> ArtifactSlot:
    return ArtifactSlot(
        family=ArtifactFamily.TABLE_FIGURE_SOURCE_DATA,
        instance=SOURCE_DATA_INSTANCE,
        experiment=experiment,
    )


def table_figure_export_slot(experiment: ExperimentName) -> ArtifactSlot:
    return ArtifactSlot(
        family=ArtifactFamily.TABLE_FIGURE_REPORT_EXPORT,
        instance=REPORT_EXPORT_INSTANCE,
        experiment=experiment,
    )


def publish_table_figure_source_data(
    experiment: ExperimentName,
    execution_digest: ArtifactDigest,
    tables: tuple[RenderedTable, ...],
    figure_paths: tuple[RepositoryPath, ...],
    table_paths: tuple[RepositoryPath, ...],
    evidence_paths: tuple[RepositoryPath, ...],
) -> tuple[ArtifactManifest, ArtifactReuseDecision]:
    evidence = tuple(
        ReportEvidenceIdentity(
            evidence_name=Path(path).name,
            content_digest=content_digest(path),
        )
        for path in evidence_paths
    )
    payload = TableFigureSourceDataPayload(
        schema_version=PUBLICATION_SCHEMA_VERSION,
        experiment=experiment,
        execution_digest=execution_digest,
        tables=tuple(
            RenderedTableIdentity(
                table=table.name,
                row_count=_table_row_count(table),
                content_digest=content_digest(path),
            )
            for table, path in zip(tables, table_paths, strict=True)
        ),
        figures=tuple(
            RenderedFigureIdentity(
                figure=Path(path).stem,
                content_bytes=Path(path).stat().st_size,
                content_digest=content_digest(path),
            )
            for path in figure_paths
        ),
        evidence=evidence,
    )
    slot = table_figure_source_data_slot(experiment)
    return publish_artifact(
        slot=slot,
        producer=ArtifactProducer.REPORTING_SOURCE_DATA,
        payload=payload.model_dump_json().encode("utf-8"),
        dependencies=(
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency="execution-evidence",
                digest=execution_digest,
            ),
            *(
                ArtifactDependency(
                    kind=ArtifactDependencyKind.CONTENT,
                    dependency=item.evidence_name,
                    digest=item.content_digest,
                )
                for item in evidence
            ),
        ),
        procedure_identity=TABLE_FIGURE_SOURCE_DATA_PROCEDURE_IDENTITY,
        slot_directory=REPOSITORY_ROOT / artifact_slot_directory(slot),
        staging_root=REPOSITORY_ROOT / artifact_staging_root(),
    )


def publish_table_figure_export(
    experiment: ExperimentName,
    source_data_identity: ArtifactDigest,
    experiment_root: Path,
    exported_paths: tuple[RepositoryPath, ...],
) -> tuple[ArtifactManifest, ArtifactReuseDecision]:
    payload = TableFigureExportPayload(
        schema_version=PUBLICATION_SCHEMA_VERSION,
        experiment=experiment,
        source_data_identity=source_data_identity,
        exported_paths=tuple(
            str(Path(path).relative_to(experiment_root)) for path in exported_paths
        ),
    )
    slot = table_figure_export_slot(experiment)
    return publish_artifact(
        slot=slot,
        producer=ArtifactProducer.REPORT_EXPORT,
        payload=payload.model_dump_json().encode("utf-8"),
        dependencies=(
            ArtifactDependency(
                kind=ArtifactDependencyKind.ARTIFACT,
                dependency="source-data",
                digest=source_data_identity,
            ),
        ),
        procedure_identity=TABLE_FIGURE_REPORT_EXPORT_PROCEDURE_IDENTITY,
        slot_directory=REPOSITORY_ROOT / artifact_slot_directory(slot),
        staging_root=REPOSITORY_ROOT / artifact_staging_root(),
    )


def read_table_figure_export(experiment: ExperimentName) -> TableFigureExportPayload | None:
    slot = table_figure_export_slot(experiment)
    current = read_current_artifact(REPOSITORY_ROOT / artifact_slot_directory(slot))
    if current is None:
        return None
    _manifest, payload = current
    return TableFigureExportPayload.model_validate_json(payload)


def _table_row_count(table: RenderedTable) -> RowCount:
    rows = table.csv_text.strip().splitlines()
    return 0 if len(rows) <= 1 else len(rows) - 1
