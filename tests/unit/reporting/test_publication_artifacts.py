import hashlib
import json
from collections.abc import Iterator
from pathlib import Path

import pandas
import pytest

from fedsira.artifacts.paths import (
    artifact_slot_directory,
    artifact_staging_root,
    current_repository_root,
    experiment_metric_evidence_root,
    experiment_metric_evidence_slot,
)
from fedsira.artifacts.store import (
    ArtifactDependency,
    ArtifactManifest,
    ArtifactSlot,
    publish_artifact,
    read_current_artifact,
)
from fedsira.domain.enums import (
    ArtifactDependencyKind,
    ArtifactDependencyLabel,
    ArtifactFamily,
    ArtifactInstanceLabel,
    ArtifactProducer,
    ComparisonMetric,
    CoreMethodIdentity,
    DatasetId,
    ExperimentName,
    PrimaryScenario,
    ReportColumnName,
    TableName,
)
from fedsira.evaluation.claim_support import ClaimDerivationInputs
from fedsira.evaluation.comparison_evidence import (
    COMPARISON_EVIDENCE_PROCEDURE_IDENTITY,
    COMPARISON_EVIDENCE_SCHEMA_VERSION,
    PersistedComparisonEvidence,
    comparison_evidence_slot,
)
from fedsira.evaluation.comparisons import (
    ComparisonFamilyResult,
    ComparisonResult,
    ComparisonState,
    build_comparison_registry,
)
from fedsira.evaluation.summaries import claim_summary_from_inputs
from fedsira.experiments.definitions import (
    AGGREGATE_METRICS_PARQUET_NAME,
    SEED_METRICS_PARQUET_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    experiment_by_name,
)
from fedsira.reporting.publication import (
    CLAIM_DECISION_PROCEDURE_IDENTITY,
    PUBLICATION_SCHEMA_VERSION,
    ClaimStateArtifactPayload,
    MetricEvidencePayload,
    TableFigureExportPayload,
    TableFigureSourceDataPayload,
    claim_state_artifact_slot,
    publish_claim_state_artifact,
    publish_metric_evidence,
    publish_project_table_figure_source_data,
    publish_table_figure_export,
    publish_table_figure_source_data,
    read_claim_state_artifact,
    read_metric_evidence,
    read_table_figure_source_data,
    table_figure_export_slot,
    table_figure_source_data_slot,
)
from fedsira.reporting.tables import (
    AggregateDisplayStatistic,
    RenderedAggregateCellLineage,
    RenderedTable,
    render_source_exclusion_results_table,
    render_statistical_summary_table,
)
from fedsira.reporting.verification import (
    artifact_manifest_dependency_failures,
    verify_report_export_currency,
)
from fedsira.runtime import (
    ApplicationContext,
    bound_application_context,
    current_application_context,
)

EXPERIMENT = ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION


@pytest.fixture
def isolated_repository(tmp_path: Path) -> Iterator[Path]:
    context: ApplicationContext = current_application_context().model_copy(
        update={"repository_root": tmp_path}
    )
    with bound_application_context(context):
        yield tmp_path


def _rendered_table(csv_text: str) -> RenderedTable:
    return RenderedTable(name=TableName.CELL_METRICS, csv_text=csv_text)


def _publish_claim_upstream(
    family: ArtifactFamily,
    producer: ArtifactProducer,
    instance: str,
    payload: bytes = b"upstream-evidence",
) -> ArtifactManifest:
    slot = ArtifactSlot(family=family, instance=instance, experiment=EXPERIMENT)
    manifest, _reused = publish_artifact(
        slot=slot,
        producer=producer,
        payload=payload,
        dependencies=(
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=ArtifactDependencyLabel.EXECUTION_EVIDENCE,
                digest=hashlib.sha256(payload).hexdigest(),
            ),
        ),
        procedure_identity="fedsira|claim-upstream-fixture|1",
        slot_directory=current_repository_root() / artifact_slot_directory(slot),
        staging_root=current_repository_root() / artifact_staging_root(),
    )
    return manifest


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


def _aggregate_metrics_file(root: Path) -> Path:
    path = root / AGGREGATE_METRICS_PARQUET_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    pandas.DataFrame(
        (
            (
                EXPERIMENT,
                CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
                PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY,
                "target-f1",
                1,
                1,
                0.9,
                0.0,
                0.9,
                0.9,
                0.9,
                0.9,
                0.9,
                ["a" * 64],
                ["semantic-cell-1"],
            ),
        ),
        columns=tuple(
            ReportColumnName(name)
            for name in (
                "experiment",
                "method",
                "condition",
                "metric",
                "observation_count",
                "seed_count",
                "mean_value",
                "sample_standard_deviation",
                "median_value",
                "first_quartile",
                "third_quartile",
                "confidence_interval_lower",
                "confidence_interval_upper",
                "source_observation_ids",
                "source_cell_semantic_keys",
            )
        ),
    ).to_parquet(path, index=False)
    return path


def _seed_metrics_file(root: Path) -> Path:
    path = root / SEED_METRICS_PARQUET_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    pandas.DataFrame(
        (
            (
                EXPERIMENT,
                DatasetId.N_BAIOT,
                CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
                PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY,
                1,
                "target-f1",
                0.9,
                "b" * 64,
                None,
                "c" * 64,
                ["d" * 64],
                ["a" * 64],
                ["semantic-cell-1"],
            ),
        ),
        columns=tuple(
            ReportColumnName(name)
            for name in (
                "experiment",
                "dataset",
                "method",
                "condition",
                "master_seed",
                "metric",
                "value",
                "configuration_digest",
                "code_revision",
                "dataset_manifest_hash",
                "scoring_artifact_ids",
                "source_observation_ids",
                "source_cell_semantic_keys",
            )
        ),
    ).to_parquet(path, index=False)
    return path


def test_metric_evidence_is_published_in_metric_family_with_content_lineage(
    isolated_repository: Path,
) -> None:
    evidence_path = isolated_repository / "cell-metrics.parquet"
    evidence_path.write_bytes(b"parquet-evidence")
    manifest, _reused = publish_metric_evidence(
        EXPERIMENT,
        "a" * 64,
        (str(evidence_path),),
    )

    assert manifest.family is ArtifactFamily.DOMAIN_SEED_METRIC_ARTIFACT
    slot = experiment_metric_evidence_slot(EXPERIMENT)
    assert slot.instance == ArtifactInstanceLabel.METRIC_EVIDENCE
    assert slot.experiment == EXPERIMENT
    current = read_current_artifact(isolated_repository / artifact_slot_directory(slot))
    assert current is not None
    _stored, payload = current
    restored = MetricEvidencePayload.model_validate_json(payload)
    assert restored.execution_digest == "a" * 64
    assert restored.evidence[0].evidence_name == evidence_path.name
    assert restored.evidence[0].content_bytes == len(b"parquet-evidence")
    assert manifest.dependencies[0].digest == "a" * 64
    assert manifest.dependencies[1].digest == restored.evidence[0].content_digest
    assert read_metric_evidence(EXPERIMENT) == (manifest, restored)


def test_metric_evidence_reader_rejects_older_producer_identity(
    isolated_repository: Path,
) -> None:
    evidence_path = isolated_repository / "cell-metrics.parquet"
    evidence_path.write_bytes(b"parquet-evidence")
    manifest, _reused = publish_metric_evidence(EXPERIMENT, "a" * 64, (str(evidence_path),))
    current = read_current_artifact(
        isolated_repository / artifact_slot_directory(experiment_metric_evidence_slot(EXPERIMENT))
    )
    assert current is not None
    _current_manifest, payload = current
    publish_artifact(
        slot=manifest.slot,
        producer=manifest.producer,
        payload=payload,
        dependencies=manifest.dependencies,
        procedure_identity="fedsira|metric_evidence|4",
        slot_directory=isolated_repository / artifact_slot_directory(manifest.slot),
        staging_root=isolated_repository / artifact_staging_root(),
    )

    assert read_metric_evidence(EXPERIMENT) is None


def test_claim_state_artifact_records_current_statistical_and_gate_dependencies(
    isolated_repository: Path,
) -> None:
    statistical = _publish_claim_upstream(
        ArtifactFamily.STATISTICAL_COMPARISON_ARTIFACT,
        ArtifactProducer.EVALUATION_PRODUCER,
        "statistical-comparisons",
    )
    gate = _publish_claim_upstream(
        ArtifactFamily.FINAL_GATE_DECISION,
        ArtifactProducer.FINAL_GATE_EVALUATOR,
        "final-gate",
    )

    inputs = ClaimDerivationInputs(collapse_decisions=None, comparison_results=())
    manifest, _reused = publish_claim_state_artifact(inputs, (statistical, gate))

    assert manifest.family is ArtifactFamily.CLAIM_STATE_ARTIFACT
    assert manifest.producer is ArtifactProducer.CLAIM_DECISION
    assert manifest.slot == claim_state_artifact_slot()
    assert tuple(item.kind for item in manifest.dependencies) == (
        ArtifactDependencyKind.ARTIFACT,
        ArtifactDependencyKind.ARTIFACT,
        ArtifactDependencyKind.CONTENT,
    )
    assert {item.digest for item in manifest.dependencies[:2]} == {
        statistical.identity,
        gate.identity,
    }
    restored = read_claim_state_artifact((statistical, gate))
    assert restored is not None
    assert restored[0] == manifest
    assert isinstance(restored[1], ClaimStateArtifactPayload)
    assert restored[1].claim_inputs == inputs
    assert restored[1].claim_summary == claim_summary_from_inputs(inputs)
    assert artifact_manifest_dependency_failures((statistical, gate, manifest)) == ()
    changed_statistical = _publish_claim_upstream(
        ArtifactFamily.STATISTICAL_COMPARISON_ARTIFACT,
        ArtifactProducer.EVALUATION_PRODUCER,
        "statistical-comparisons",
        payload=b"changed-statistical-evidence",
    )
    assert read_claim_state_artifact((changed_statistical, gate)) is None


def test_claim_state_artifact_requires_statistical_and_final_gate_inputs(
    isolated_repository: Path,
) -> None:
    statistical = _publish_claim_upstream(
        ArtifactFamily.STATISTICAL_COMPARISON_ARTIFACT,
        ArtifactProducer.EVALUATION_PRODUCER,
        "statistical-comparisons",
    )

    with pytest.raises(ValueError, match="final-gate"):
        publish_claim_state_artifact(
            ClaimDerivationInputs(collapse_decisions=None, comparison_results=()),
            (statistical,),
        )


def test_claim_state_content_changes_change_artifact_identity(
    isolated_repository: Path,
) -> None:
    statistical = _publish_claim_upstream(
        ArtifactFamily.STATISTICAL_COMPARISON_ARTIFACT,
        ArtifactProducer.EVALUATION_PRODUCER,
        "statistical-comparisons",
    )
    gate = _publish_claim_upstream(
        ArtifactFamily.FINAL_GATE_DECISION,
        ArtifactProducer.FINAL_GATE_EVALUATOR,
        "final-gate",
    )
    original_inputs = ClaimDerivationInputs(collapse_decisions=None, comparison_results=())
    changed_inputs = original_inputs.model_copy(update={"safe_dormancy_verified": True})
    original_manifest, _reused = publish_claim_state_artifact(original_inputs, (statistical, gate))
    changed_manifest, _changed_reused = publish_claim_state_artifact(
        changed_inputs,
        (statistical, gate),
    )

    assert original_manifest.identity != changed_manifest.identity
    restored = read_claim_state_artifact((statistical, gate))
    assert restored is not None
    assert restored[1].claim_summary == claim_summary_from_inputs(changed_inputs)
    honest = claim_summary_from_inputs(changed_inputs)
    edited = honest.model_copy(
        update={
            "decisions": (
                honest.decisions[0].model_copy(update={"basis": "hand-edited basis"}),
                *honest.decisions[1:],
            )
        }
    )
    tampered = ClaimStateArtifactPayload(
        schema_version=PUBLICATION_SCHEMA_VERSION,
        claim_inputs=changed_inputs,
        claim_summary=edited,
    )
    slot = claim_state_artifact_slot()
    publish_artifact(
        slot=slot,
        producer=ArtifactProducer.CLAIM_DECISION,
        payload=tampered.model_dump_json().encode("utf-8"),
        dependencies=changed_manifest.dependencies,
        procedure_identity=CLAIM_DECISION_PROCEDURE_IDENTITY,
        slot_directory=isolated_repository / artifact_slot_directory(slot),
        staging_root=isolated_repository / artifact_staging_root(),
    )
    assert read_claim_state_artifact((statistical, gate)) is None


def _publish_source_data(
    experiment_root: Path,
    csv_text: str,
) -> tuple[ArtifactManifest, Path]:
    table_path, figure_path = _products(experiment_root, csv_text)
    evidence_root = experiment_metric_evidence_root(EXPERIMENT)
    aggregate_path = _aggregate_metrics_file(evidence_root)
    seed_path = _seed_metrics_file(evidence_root)
    metric_manifest, _metric_reused = publish_metric_evidence(
        EXPERIMENT,
        "e" * 64,
        (str(aggregate_path), str(seed_path), str(table_path)),
    )
    manifest, _reused = publish_table_figure_source_data(
        EXPERIMENT,
        "e" * 64,
        metric_manifest.identity,
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
    assert len(restored.verified_aggregate_metrics) == 1
    assert restored.verified_aggregate_metrics[0].source_observation_ids == ("a" * 64,)
    assert restored.verified_aggregate_metrics[0].source_cell_semantic_keys == ("semantic-cell-1",)
    assert len(restored.verified_seed_metrics) == 1
    seed = restored.verified_seed_metrics[0]
    assert seed.dataset is DatasetId.N_BAIOT
    assert seed.master_seed == 1
    assert seed.configuration_digest == "b" * 64
    assert seed.dataset_manifest_hash == "c" * 64
    assert seed.scoring_artifact_ids == ("d" * 64,)
    assert manifest.dependencies[0].digest == "e" * 64
    dependencies = {item.dependency: item.digest for item in manifest.dependencies}
    assert (
        dependencies[f"table-render:{TableName.CELL_METRICS}"] == restored.tables[0].content_digest
    )
    assert dependencies["figure-render:Primary Security-Utility Tradeoff"] == (
        restored.figures[0].content_digest
    )


def test_statistical_table_source_data_resolves_row_to_current_comparison_artifact(
    isolated_repository: Path,
) -> None:
    definition = next(
        item
        for item in build_comparison_registry()
        if item.experiment == EXPERIMENT and item.metric is ComparisonMetric.TARGET_F1
    )
    comparison = ComparisonResult(
        definition=definition,
        paired_differences=(0.1,),
        complete_seed_count=1,
        mean_paired_difference=0.1,
        median_paired_difference=0.1,
        paired_standardized_effect=None,
        raw_p_value=1.0,
        adjusted_p_value=1.0,
        confidence_interval=(-0.2, 0.3),
        materiality_passes=None,
        comparison_state=ComparisonState.INCONCLUSIVE_TECHNICAL,
        paired_master_seeds=(1103,),
    )
    family = ComparisonFamilyResult(family=definition.family, comparisons=(comparison,))
    table = render_statistical_summary_table((family,))
    comparison_slot = comparison_evidence_slot(EXPERIMENT)
    comparison_manifest, _reused = publish_artifact(
        slot=comparison_slot,
        producer=ArtifactProducer.EVALUATION_PRODUCER,
        payload=PersistedComparisonEvidence(
            schema_version=COMPARISON_EVIDENCE_SCHEMA_VERSION,
            experiment=EXPERIMENT,
            metric_evidence_digest="f" * 64,
            families=(family,),
        )
        .model_dump_json()
        .encode("utf-8"),
        dependencies=(),
        procedure_identity=COMPARISON_EVIDENCE_PROCEDURE_IDENTITY,
        slot_directory=isolated_repository / artifact_slot_directory(comparison_slot),
        staging_root=isolated_repository / artifact_staging_root(),
    )
    table_path, figure_path = _products(isolated_repository, table.csv_text)
    evidence_root = experiment_metric_evidence_root(EXPERIMENT)
    aggregate_path = _aggregate_metrics_file(evidence_root)
    seed_path = _seed_metrics_file(evidence_root)
    metric_manifest, _metric_reused = publish_metric_evidence(
        EXPERIMENT,
        "e" * 64,
        (str(aggregate_path), str(seed_path), str(table_path)),
    )

    manifest, _source_reused = publish_table_figure_source_data(
        EXPERIMENT,
        "e" * 64,
        metric_manifest.identity,
        (table,),
        (str(figure_path),),
        (str(table_path),),
        (str(table_path),),
        comparison_artifact_identity=comparison_manifest.identity,
    )

    current = read_current_artifact(
        isolated_repository / artifact_slot_directory(table_figure_source_data_slot(EXPERIMENT))
    )
    assert current is not None
    payload = TableFigureSourceDataPayload.model_validate_json(current[1])
    lineage = payload.tables[0].comparison_lineage[0]
    assert lineage.lineage.comparison_name == definition.comparison_name
    assert lineage.source_artifact.identity == comparison_manifest.identity
    assert lineage.lineage.source_cell_semantic_keys
    assert any(item.digest == comparison_manifest.identity for item in manifest.dependencies)
    restored = read_table_figure_source_data(EXPERIMENT)
    assert restored is not None
    assert restored[1].tables[0].comparison_lineage == payload.tables[0].comparison_lineage


def test_source_data_identity_changes_when_rendered_content_changes(
    isolated_repository: Path,
) -> None:
    first, _reused = _publish_source_data(isolated_repository, "experiment,method\nA,B\n")
    second, _reused_again = _publish_source_data(
        isolated_repository, "experiment,method\nA,B\nA,C\n"
    )
    assert first.identity != second.identity


def test_source_exclusion_aggregate_cells_resolve_without_a_displayed_scenario_column(
    isolated_repository: Path,
) -> None:
    definition = experiment_by_name(SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME)
    assert len(definition.conditions) == 1
    method = definition.methods[0]
    scenario = definition.conditions[0]
    observation_id = "a" * 64
    semantic_cell_key = "source-exclusion-cell"
    evidence_root = experiment_metric_evidence_root(SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME)
    aggregate_path = evidence_root / AGGREGATE_METRICS_PARQUET_NAME
    seed_path = evidence_root / SEED_METRICS_PARQUET_NAME
    aggregate_path.parent.mkdir(parents=True, exist_ok=True)
    metric = ComparisonMetric.ATTACK_SUCCESS_RATE
    pandas.DataFrame(
        (
            (
                SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
                method,
                scenario,
                metric,
                1,
                1,
                0.3,
                0.0,
                0.3,
                0.3,
                0.3,
                0.3,
                0.3,
                [observation_id],
                [semantic_cell_key],
            ),
        ),
        columns=tuple(
            ReportColumnName(name)
            for name in (
                "experiment",
                "method",
                "condition",
                "metric",
                "observation_count",
                "seed_count",
                "mean_value",
                "sample_standard_deviation",
                "median_value",
                "first_quartile",
                "third_quartile",
                "confidence_interval_lower",
                "confidence_interval_upper",
                "source_observation_ids",
                "source_cell_semantic_keys",
            )
        ),
    ).to_parquet(aggregate_path, index=False)
    pandas.DataFrame(
        (
            (
                SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
                DatasetId.N_BAIOT,
                method,
                scenario,
                1103,
                metric,
                0.3,
                "b" * 64,
                None,
                "c" * 64,
                ["d" * 64],
                [observation_id],
                [semantic_cell_key],
            ),
        ),
        columns=tuple(
            ReportColumnName(name)
            for name in (
                "experiment",
                "dataset",
                "method",
                "condition",
                "master_seed",
                "metric",
                "value",
                "configuration_digest",
                "code_revision",
                "dataset_manifest_hash",
                "scoring_artifact_ids",
                "source_observation_ids",
                "source_cell_semantic_keys",
            )
        ),
    ).to_parquet(seed_path, index=False)
    table = render_source_exclusion_results_table((), (), None)
    table_path, figure_path = _products(isolated_repository, table.csv_text)
    metric_manifest, _metric_reused = publish_metric_evidence(
        SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
        "e" * 64,
        (str(aggregate_path), str(seed_path), str(table_path)),
    )
    source_manifest, _source_reused = publish_table_figure_source_data(
        SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
        "e" * 64,
        metric_manifest.identity,
        (table,),
        (str(figure_path),),
        (str(table_path),),
        (str(table_path),),
    )
    restored = read_table_figure_source_data(SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME)

    assert restored is not None
    assert len(restored[1].tables[0].aggregate_lineage) == len(definition.methods) * 4
    assert (
        restored[1].tables[0].aggregate_lineage[0].source_artifact.identity
        == metric_manifest.identity
    )
    assert restored[1].tables[0].aggregate_lineage[0].configuration_digest == "b" * 64
    assert restored[1].tables[0].aggregate_lineage[0].dataset_manifest_hash == "c" * 64
    assert source_manifest.family is ArtifactFamily.TABLE_FIGURE_SOURCE_DATA
    assert table.csv_text.splitlines()[1].split(",")[1] == "0.300 ± 0.000"


def test_source_exclusion_comparison_cells_resolve_to_the_current_comparison_artifact(
    isolated_repository: Path,
) -> None:
    experiment = SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME
    method = experiment_by_name(experiment).methods[0]
    definition = next(
        item
        for item in build_comparison_registry()
        if item.experiment == experiment
        and item.method == method
        and item.scientific_scenario == PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT
        and item.metric is ComparisonMetric.ATTACK_SUCCESS_RATE
    )
    comparison = ComparisonResult(
        definition=definition,
        paired_differences=(0.1,),
        complete_seed_count=1,
        mean_paired_difference=0.1,
        median_paired_difference=0.1,
        paired_standardized_effect=None,
        raw_p_value=1.0,
        adjusted_p_value=1.0,
        confidence_interval=(-0.2, 0.3),
        materiality_passes=None,
        comparison_state=ComparisonState.INCONCLUSIVE_TECHNICAL,
        paired_master_seeds=(1103,),
    )
    family = ComparisonFamilyResult(family=definition.family, comparisons=(comparison,))
    evidence_root = experiment_metric_evidence_root(experiment)
    aggregate_path = evidence_root / AGGREGATE_METRICS_PARQUET_NAME
    seed_path = evidence_root / SEED_METRICS_PARQUET_NAME
    aggregate_path.parent.mkdir(parents=True, exist_ok=True)
    pandas.DataFrame(
        (
            (
                experiment,
                method,
                PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
                ComparisonMetric.ATTACK_SUCCESS_RATE,
                1,
                1,
                0.3,
                0.0,
                0.3,
                0.3,
                0.3,
                0.3,
                0.3,
                ["a" * 64],
                ["source-exclusion-cell"],
            ),
        ),
        columns=tuple(
            ReportColumnName(name)
            for name in (
                "experiment",
                "method",
                "condition",
                "metric",
                "observation_count",
                "seed_count",
                "mean_value",
                "sample_standard_deviation",
                "median_value",
                "first_quartile",
                "third_quartile",
                "confidence_interval_lower",
                "confidence_interval_upper",
                "source_observation_ids",
                "source_cell_semantic_keys",
            )
        ),
    ).to_parquet(aggregate_path, index=False)
    pandas.DataFrame(
        (
            (
                experiment,
                DatasetId.N_BAIOT,
                method,
                PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
                1103,
                ComparisonMetric.ATTACK_SUCCESS_RATE,
                0.3,
                "b" * 64,
                None,
                "c" * 64,
                ["d" * 64],
                ["a" * 64],
                ["source-exclusion-cell"],
            ),
        ),
        columns=tuple(
            ReportColumnName(name)
            for name in (
                "experiment",
                "dataset",
                "method",
                "condition",
                "master_seed",
                "metric",
                "value",
                "configuration_digest",
                "code_revision",
                "dataset_manifest_hash",
                "scoring_artifact_ids",
                "source_observation_ids",
                "source_cell_semantic_keys",
            )
        ),
    ).to_parquet(seed_path, index=False)
    table = render_source_exclusion_results_table((family,), (), None)
    assert table.comparison_cell_lineage
    comparison_slot = comparison_evidence_slot(experiment)
    comparison_manifest, _reused = publish_artifact(
        slot=comparison_slot,
        producer=ArtifactProducer.EVALUATION_PRODUCER,
        payload=PersistedComparisonEvidence(
            schema_version=COMPARISON_EVIDENCE_SCHEMA_VERSION,
            experiment=experiment,
            metric_evidence_digest="f" * 64,
            families=(family,),
        )
        .model_dump_json()
        .encode("utf-8"),
        dependencies=(),
        procedure_identity=COMPARISON_EVIDENCE_PROCEDURE_IDENTITY,
        slot_directory=isolated_repository / artifact_slot_directory(comparison_slot),
        staging_root=isolated_repository / artifact_staging_root(),
    )
    table_path, figure_path = _products(isolated_repository, table.csv_text)
    metric_manifest, _metric_reused = publish_metric_evidence(
        experiment,
        "e" * 64,
        (str(aggregate_path), str(seed_path), str(table_path)),
    )
    publish_table_figure_source_data(
        experiment,
        "e" * 64,
        metric_manifest.identity,
        (table,),
        (str(figure_path),),
        (str(table_path),),
        (str(table_path),),
        comparison_artifact_identity=comparison_manifest.identity,
    )
    restored = read_table_figure_source_data(experiment)

    assert restored is not None
    cells = restored[1].tables[0].comparison_cell_lineage
    assert cells
    assert all(cell.source_artifact.identity == comparison_manifest.identity for cell in cells)
    assert any(
        cell.lineage.metric is ComparisonMetric.ATTACK_SUCCESS_RATE
        and cell.lineage.method == method
        for cell in cells
    )


def test_source_data_refuses_aggregate_metrics_changed_after_publication(
    isolated_repository: Path,
) -> None:
    csv_text = "experiment,method\nA,B\n"
    table_path, figure_path = _products(isolated_repository, csv_text)
    evidence_root = experiment_metric_evidence_root(EXPERIMENT)
    aggregate_path = _aggregate_metrics_file(evidence_root)
    seed_path = _seed_metrics_file(evidence_root)
    metric_manifest, _metric_reused = publish_metric_evidence(
        EXPERIMENT,
        "e" * 64,
        (str(aggregate_path), str(seed_path), str(table_path)),
    )
    aggregate_path.write_bytes(b"changed after manifest publication")

    with pytest.raises(ValueError, match="aggregate-metrics.parquet is missing or stale"):
        publish_table_figure_source_data(
            EXPERIMENT,
            "e" * 64,
            metric_manifest.identity,
            (_rendered_table(csv_text),),
            (str(figure_path),),
            (str(table_path),),
            (str(table_path),),
        )


def test_source_data_refuses_unmatched_aggregate_to_seed_observation_lineage(
    isolated_repository: Path,
) -> None:
    csv_text = "experiment,method\nA,B\n"
    table_path, figure_path = _products(isolated_repository, csv_text)
    evidence_root = experiment_metric_evidence_root(EXPERIMENT)
    aggregate_path = _aggregate_metrics_file(evidence_root)
    seed_path = _seed_metrics_file(evidence_root)
    seed_frame = pandas.read_parquet(seed_path)
    seed_frame[ReportColumnName.SOURCE_OBSERVATION_IDS] = [["f" * 64]]
    seed_frame.to_parquet(seed_path, index=False)
    metric_manifest, _metric_reused = publish_metric_evidence(
        EXPERIMENT,
        "e" * 64,
        (str(aggregate_path), str(seed_path), str(table_path)),
    )

    with pytest.raises(ValueError, match="aggregate-to-seed source lineage does not match"):
        publish_table_figure_source_data(
            EXPERIMENT,
            "e" * 64,
            metric_manifest.identity,
            (_rendered_table(csv_text),),
            (str(figure_path),),
            (str(table_path),),
            (str(table_path),),
        )


def test_source_data_reader_rejects_prior_payload_schema(
    isolated_repository: Path,
) -> None:
    source_manifest, _table_path = _publish_source_data(
        isolated_repository,
        "experiment,method\nA,B\n",
    )
    current = read_current_artifact(
        isolated_repository / artifact_slot_directory(table_figure_source_data_slot(EXPERIMENT))
    )
    assert current is not None
    _manifest, payload_bytes = current
    old_payload = json.loads(payload_bytes)
    old_payload["schema_version"] = "fedsira|publication|3"
    slot = table_figure_source_data_slot(EXPERIMENT)
    publish_artifact(
        slot=slot,
        producer=ArtifactProducer.REPORTING_SOURCE_DATA,
        payload=json.dumps(old_payload).encode("utf-8"),
        dependencies=source_manifest.dependencies,
        procedure_identity="fedsira|table_figure_source_data|3",
        slot_directory=isolated_repository / artifact_slot_directory(slot),
        staging_root=isolated_repository / artifact_staging_root(),
    )

    assert read_table_figure_source_data(EXPERIMENT) is None


def test_source_data_reader_rejects_prior_procedure_identity(
    isolated_repository: Path,
) -> None:
    source_manifest, _table_path = _publish_source_data(
        isolated_repository,
        "experiment,method\nA,B\n",
    )
    current = read_current_artifact(
        isolated_repository / artifact_slot_directory(table_figure_source_data_slot(EXPERIMENT))
    )
    assert current is not None
    _manifest, payload = current
    publish_artifact(
        slot=table_figure_source_data_slot(EXPERIMENT),
        producer=ArtifactProducer.REPORTING_SOURCE_DATA,
        payload=payload,
        dependencies=source_manifest.dependencies,
        procedure_identity="fedsira|table_figure_source_data|5",
        slot_directory=isolated_repository
        / artifact_slot_directory(table_figure_source_data_slot(EXPERIMENT)),
        staging_root=isolated_repository / artifact_staging_root(),
    )

    assert read_table_figure_source_data(EXPERIMENT) is None


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
    metric_current = read_current_artifact(
        isolated_repository / artifact_slot_directory(experiment_metric_evidence_slot(EXPERIMENT))
    )
    assert metric_current is not None
    metric_manifest, _payload = metric_current
    assert artifact_manifest_dependency_failures((metric_manifest, source_data, export)) == ()


def _aggregate_lineage(experiment: ExperimentName) -> RenderedAggregateCellLineage:
    return RenderedAggregateCellLineage(
        row_index=0,
        source_column=ReportColumnName.METHOD,
        experiment=experiment,
        method=CoreMethodIdentity.RESOLVED_FEDSIRA_CORE,
        scenario="All Honest",
        metric=ComparisonMetric.ATTACK_SUCCESS_RATE,
        statistic=AggregateDisplayStatistic.MEAN_VALUE,
    )


def test_cross_experiment_aggregate_lineage_requires_an_experiment_column(
    isolated_repository: Path,
) -> None:
    csv_text = "method,value\n"
    table_path, figure_path = _products(isolated_repository, csv_text)
    evidence_root = experiment_metric_evidence_root(EXPERIMENT)
    aggregate_path = _aggregate_metrics_file(evidence_root)
    seed_path = _seed_metrics_file(evidence_root)
    metric_manifest, _metric_reused = publish_metric_evidence(
        EXPERIMENT,
        "e" * 64,
        (str(aggregate_path), str(seed_path), str(table_path)),
    )
    pooled = RenderedTable(
        name=TableName.PRIMARY_RESULTS,
        csv_text=csv_text,
        aggregate_lineage=(
            _aggregate_lineage(ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION),
            _aggregate_lineage(ExperimentName.SOURCE_ARTIFACT_EXCLUSION_NECESSITY),
        ),
    )
    with pytest.raises(ValueError, match="cross-experiment"):
        publish_table_figure_source_data(
            EXPERIMENT,
            "e" * 64,
            metric_manifest.identity,
            (pooled,),
            (str(figure_path),),
            (str(table_path),),
            (str(table_path),),
        )
    single = pooled.model_copy(
        update={
            "aggregate_lineage": (
                _aggregate_lineage(ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION),
            )
        }
    )
    with pytest.raises(ValueError, match="cell identity is invalid"):
        publish_table_figure_source_data(
            EXPERIMENT,
            "e" * 64,
            metric_manifest.identity,
            (single,),
            (str(figure_path),),
            (str(table_path),),
            (str(table_path),),
        )


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


def test_project_report_source_and_export_artifacts_are_ownerless_and_current(
    isolated_repository: Path,
) -> None:
    csv_text = "experiment,method\nA,B\n"
    table_path, figure_path = _products(isolated_repository / "project-summary", csv_text)
    evidence_root = experiment_metric_evidence_root(EXPERIMENT)
    aggregate_path = _aggregate_metrics_file(evidence_root)
    seed_path = _seed_metrics_file(evidence_root)
    upstream, _metric_reused = publish_metric_evidence(
        EXPERIMENT,
        "f" * 64,
        (str(aggregate_path), str(seed_path)),
    )
    dataset = _publish_claim_upstream(
        ArtifactFamily.DATASET_MANIFEST,
        ArtifactProducer.DATASET_PREPARATION,
        "project-dataset",
    )
    source, _source_reused = publish_project_table_figure_source_data(
        "d" * 64,
        (upstream, dataset),
        (_rendered_table(csv_text),),
        (str(figure_path),),
        (str(table_path),),
    )

    source_current = read_current_artifact(
        isolated_repository / artifact_slot_directory(table_figure_source_data_slot(None))
    )
    assert source_current is not None
    _source_manifest, source_payload_bytes = source_current
    source_payload = TableFigureSourceDataPayload.model_validate_json(source_payload_bytes)
    assert source_payload.experiment is None
    assert upstream.identity in {item.identity for item in source_payload.upstream_artifacts}
    assert len(source_payload.verified_aggregate_metrics) == 1
    assert len(source_payload.verified_seed_metrics) == 1
    assert (
        source_payload.tables[0].content_digest
        == hashlib.sha256(table_path.read_bytes()).hexdigest()
    )

    export, _export_reused = publish_table_figure_export(
        None,
        source.identity,
        isolated_repository / "project-summary",
        (str(table_path), str(figure_path)),
    )
    assert export.slot.experiment is None
    assert export.dependencies[0].digest == source.identity
    assert (
        verify_report_export_currency(
            None,
            source.identity,
            isolated_repository / "project-summary",
            ("tables/main/Cell Metrics.csv", "figures/main/Primary Security-Utility Tradeoff.png"),
        )
        == ()
    )
