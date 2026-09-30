from pathlib import Path

import pytest

from fedsira.artifacts.store import (
    ARTIFACT_SCHEMA_VERSION,
    ArtifactConfigurationComponent,
    ArtifactConfigurationScope,
    ArtifactDependency,
    ArtifactManifest,
    ArtifactSlot,
    artifact_identity,
    compute_checksum,
    configuration_scope_dependency,
    is_artifact_complete_and_valid,
    publish_artifact,
    publish_artifact_to_disk,
    read_current_artifact,
    read_published_manifest,
    read_validated_artifact_payload,
    stage_payload,
    verify_checksum,
)
from fedsira.domain.enums import (
    ArtifactDependencyKind,
    ArtifactDependencyLabel,
    ArtifactFamily,
    ArtifactLifecycleState,
    ArtifactProducer,
    ExperimentName,
)


def staged_manifest(identity: str, payload: bytes) -> ArtifactManifest:
    return ArtifactManifest(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        slot=ArtifactSlot(family=ArtifactFamily.SCALER, instance="test-scaler"),
        producer=ArtifactProducer.PREPROCESSING,
        identity=identity,
        checksum=compute_checksum(payload),
        payload_bytes=len(payload),
        lifecycle_state=ArtifactLifecycleState.STAGING,
        dependencies=(),
        procedure_identity="fedsira|test_scaler|1",
        configuration_digest="d" * 64,
        code_revision=None,
    )


def test_verify_checksum_accepts_matching_payload() -> None:
    payload = b"payload"
    verify_checksum(payload, staged_manifest("a" * 64, payload))


def test_verify_checksum_rejects_mismatched_payload() -> None:
    with pytest.raises(ValueError):
        verify_checksum(b"tampered", staged_manifest("a" * 64, b"payload"))


def test_artifact_identity_ignores_unrelated_global_configuration_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slot = ArtifactSlot(family=ArtifactFamily.SCALER, instance="test-scaler")
    monkeypatch.setattr("fedsira.artifacts.store.configuration_digest", lambda: "a" * 64)
    first = artifact_identity(slot, (), "fedsira|test_scaler|1")
    monkeypatch.setattr("fedsira.artifacts.store.configuration_digest", lambda: "b" * 64)
    changed = artifact_identity(slot, (), "fedsira|test_scaler|1")

    assert changed == first


def test_artifact_identity_changes_when_its_declared_configuration_scope_changes() -> None:
    slot = ArtifactSlot(family=ArtifactFamily.SCALER, instance="test-scaler")
    first = configuration_scope_dependency(
        ArtifactConfigurationScope(
            scope="preprocessing:N-BaIoT",
            components=(
                ArtifactConfigurationComponent(
                    name=ArtifactDependencyLabel.DATASET_PREPROCESSING,
                    configuration='{"clip_max":10}',
                ),
            ),
        )
    )
    changed = configuration_scope_dependency(
        ArtifactConfigurationScope(
            scope="preprocessing:N-BaIoT",
            components=(
                ArtifactConfigurationComponent(
                    name=ArtifactDependencyLabel.DATASET_PREPROCESSING,
                    configuration='{"clip_max":12}',
                ),
            ),
        )
    )

    first_identity = artifact_identity(slot, (first,), "fedsira|test_scaler|1")
    changed_identity = artifact_identity(slot, (changed,), "fedsira|test_scaler|1")

    assert changed_identity != first_identity


def _invalidation_fixture_identities(
    *,
    training_config: str = "training-v1",
    scoring_config: str = "scoring-v1",
    metric_config: str = "metric-v1",
    statistics_config: str = "statistics-v1",
    rendering_digest: str = "render-v1",
) -> tuple[str, ...]:
    def identity(
        family: ArtifactFamily,
        instance: str,
        procedure: str,
        scope: str,
        scope_value: str,
        parent: str | None,
    ) -> str:
        dependencies = (
            ()
            if parent is None
            else (
                ArtifactDependency(
                    kind=ArtifactDependencyKind.ARTIFACT,
                    dependency=ArtifactDependencyLabel.PARENT,
                    digest=parent,
                ),
            )
        )
        return artifact_identity(
            ArtifactSlot(family=family, instance=instance),
            (
                *dependencies,
                configuration_scope_dependency(
                    ArtifactConfigurationScope(
                        scope=scope,
                        components=(
                            ArtifactConfigurationComponent(
                                name=ArtifactDependencyLabel.PARENT,
                                configuration=scope_value,
                            ),
                        ),
                    )
                ),
            ),
            procedure,
        )

    prepared = identity(
        ArtifactFamily.PREPARED_ROLE_VIEW,
        "view",
        "fedsira|prepared_view|1",
        "preprocessing",
        "preprocessing-v1",
        None,
    )
    checkpoint = identity(
        ArtifactFamily.ANCHOR_CHECKPOINT,
        "anchor",
        "fedsira|anchor|1",
        "training",
        training_config,
        prepared,
    )
    score = identity(
        ArtifactFamily.MODEL_SCORE_ARTIFACT,
        "score",
        "fedsira|score|1",
        "scoring",
        scoring_config,
        checkpoint,
    )
    metric = identity(
        ArtifactFamily.DOMAIN_SEED_METRIC_ARTIFACT,
        "metric",
        "fedsira|metric|1",
        "metric",
        metric_config,
        score,
    )
    comparison = identity(
        ArtifactFamily.STATISTICAL_COMPARISON_ARTIFACT,
        "comparison",
        "fedsira|comparison|1",
        "statistics",
        statistics_config,
        metric,
    )
    source_data = identity(
        ArtifactFamily.TABLE_FIGURE_SOURCE_DATA,
        "source-data",
        "fedsira|source-data|1",
        "rendering",
        rendering_digest,
        comparison,
    )
    export = artifact_identity(
        ArtifactSlot(family=ArtifactFamily.TABLE_FIGURE_REPORT_EXPORT, instance="export"),
        (
            ArtifactDependency(
                kind=ArtifactDependencyKind.ARTIFACT,
                dependency=ArtifactDependencyLabel.SOURCE_DATA,
                digest=source_data,
            ),
        ),
        "fedsira|export|1",
    )
    return prepared, checkpoint, score, metric, comparison, source_data, export


def test_stage_scoped_changes_invalidate_only_their_descendants() -> None:
    baseline = _invalidation_fixture_identities()
    training_changed = _invalidation_fixture_identities(training_config="training-v2")
    scoring_changed = _invalidation_fixture_identities(scoring_config="scoring-v2")
    metric_changed = _invalidation_fixture_identities(metric_config="metric-v2")
    statistics_changed = _invalidation_fixture_identities(statistics_config="statistics-v2")
    rendering_changed = _invalidation_fixture_identities(rendering_digest="render-v2")

    assert training_changed[0] == baseline[0]
    assert training_changed[1] != baseline[1]
    assert all(training_changed[index] != baseline[index] for index in range(2, 7))
    assert scoring_changed[:2] == baseline[:2]
    assert all(scoring_changed[index] != baseline[index] for index in range(2, 7))
    assert metric_changed[:3] == baseline[:3]
    assert all(metric_changed[index] != baseline[index] for index in range(3, 7))
    assert statistics_changed[:4] == baseline[:4]
    assert all(statistics_changed[index] != baseline[index] for index in range(4, 7))
    assert rendering_changed[:5] == baseline[:5]
    assert rendering_changed[5] != baseline[5]
    assert rendering_changed[6] != baseline[6]


def test_artifact_identity_distinguishes_dependency_kind_and_is_order_independent() -> None:
    slot = ArtifactSlot(family=ArtifactFamily.SCALER, instance="test-scaler")
    content_parent = ArtifactDependency(
        kind=ArtifactDependencyKind.CONTENT,
        dependency=ArtifactDependencyLabel.PARENT,
        digest="a" * 64,
    )
    artifact_parent = content_parent.model_copy(update={"kind": ArtifactDependencyKind.ARTIFACT})
    raw_parent = ArtifactDependency(
        kind=ArtifactDependencyKind.CONTENT,
        dependency=ArtifactDependencyLabel.RAW_DATASET,
        digest="b" * 64,
    )
    procedure = "fedsira|test_scaler|1"

    content_identity = artifact_identity(slot, (content_parent,), procedure)
    artifact_identity_value = artifact_identity(slot, (artifact_parent,), procedure)
    forward = artifact_identity(slot, (content_parent, raw_parent), procedure)
    reverse = artifact_identity(slot, (raw_parent, content_parent), procedure)

    assert content_identity != artifact_identity_value
    assert forward == reverse


def test_stage_payload_gives_each_call_a_distinct_path(tmp_path: Path) -> None:
    first = stage_payload(tmp_path / "staging", b"payload")
    second = stage_payload(tmp_path / "staging", b"payload")
    assert first != second


def test_publish_artifact_to_disk_writes_complete_manifest(tmp_path: Path) -> None:
    payload = b"payload"
    manifest = staged_manifest("a" * 64, payload)
    staged_path = stage_payload(tmp_path / "staging", payload)
    published = publish_artifact_to_disk(staged_path, tmp_path / "canonical", manifest, payload)
    assert published.lifecycle_state is ArtifactLifecycleState.COMPLETE
    assert read_published_manifest(tmp_path / "canonical", "a" * 64) == published


def test_interrupted_manifest_write_never_makes_payload_readable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = b"payload"
    directory = tmp_path / "canonical"
    staged_path = stage_payload(tmp_path / "staging", payload)

    def fail_manifest_write(_path: Path, _text: str) -> None:
        raise OSError("simulated interruption")

    monkeypatch.setattr("fedsira.artifacts.store._write_text_atomically", fail_manifest_write)
    with pytest.raises(OSError, match="simulated interruption"):
        publish_artifact_to_disk(
            staged_path,
            directory,
            staged_manifest("a" * 64, payload),
            payload,
        )

    assert not (directory / f"{'a' * 64}.manifest.json").exists()
    assert not is_artifact_complete_and_valid(directory, "a" * 64)
    assert read_current_artifact(directory) is None


def test_changed_dependency_promotes_current_without_mutating_previous_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("fedsira.artifacts.store.configuration_digest", lambda: "d" * 64)
    slot = ArtifactSlot(family=ArtifactFamily.SCALER, instance="test-scaler")
    directory = tmp_path / "canonical"
    staging = tmp_path / "staging"
    procedure = "fedsira|test_scaler|1"
    first_dependency = ArtifactDependency(
        kind=ArtifactDependencyKind.CONTENT,
        dependency=ArtifactDependencyLabel.RAW_DATASET,
        digest="a" * 64,
    )
    second_dependency = first_dependency.model_copy(update={"digest": "b" * 64})

    first, first_reused = publish_artifact(
        slot=slot,
        producer=ArtifactProducer.PREPROCESSING,
        payload=b"first",
        dependencies=(first_dependency,),
        procedure_identity=procedure,
        slot_directory=directory,
        staging_root=staging,
    )
    second, second_reused = publish_artifact(
        slot=slot,
        producer=ArtifactProducer.PREPROCESSING,
        payload=b"second",
        dependencies=(second_dependency,),
        procedure_identity=procedure,
        slot_directory=directory,
        staging_root=staging,
    )

    assert not first_reused and not second_reused
    assert first.identity != second.identity
    assert is_artifact_complete_and_valid(directory, first.identity)
    current = read_current_artifact(directory)
    assert current is not None
    assert current[0].identity == second.identity
    assert current[1] == b"second"
    assert len(tuple(directory.glob("*.manifest.json"))) == 2


def test_complete_artifact_is_reusable_only_when_payload_matches(tmp_path: Path) -> None:
    payload = b"payload"
    directory = tmp_path / "canonical"
    publish_artifact_to_disk(
        stage_payload(tmp_path / "staging", payload),
        directory,
        staged_manifest("a" * 64, payload),
        payload,
    )
    assert is_artifact_complete_and_valid(directory, "a" * 64)
    (directory / f"{'a' * 64}.artifact.bin").write_bytes(b"corrupted")
    assert not is_artifact_complete_and_valid(directory, "a" * 64)


def test_conflicting_payload_retires_the_current_pointer_without_replacing_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("fedsira.artifacts.store.configuration_digest", lambda: "d" * 64)
    slot = ArtifactSlot(family=ArtifactFamily.SCALER, instance="test-scaler")
    directory = tmp_path / "canonical"
    staging = tmp_path / "staging"
    dependency = ArtifactDependency(
        kind=ArtifactDependencyKind.CONTENT,
        dependency=ArtifactDependencyLabel.RAW_DATASET,
        digest="a" * 64,
    )
    first, first_reused = publish_artifact(
        slot=slot,
        producer=ArtifactProducer.PREPROCESSING,
        payload=b"honest",
        dependencies=(dependency,),
        procedure_identity="fedsira|test_scaler|1",
        slot_directory=directory,
        staging_root=staging,
    )
    conflicting, conflicting_reused = publish_artifact(
        slot=slot,
        producer=ArtifactProducer.PREPROCESSING,
        payload=b"tampered",
        dependencies=(dependency,),
        procedure_identity="fedsira|test_scaler|1",
        slot_directory=directory,
        staging_root=staging,
    )

    assert not first_reused
    assert not conflicting_reused
    assert conflicting.identity == first.identity
    assert conflicting.checksum == compute_checksum(b"honest")
    assert is_artifact_complete_and_valid(directory, first.identity)
    assert read_validated_artifact_payload(directory, first.identity) == b"honest"
    assert read_current_artifact(directory) is None
    assert len(tuple(directory.glob("*.manifest.json"))) == 1


def test_two_experiment_consumers_reuse_one_compatible_shared_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("fedsira.artifacts.store.configuration_digest", lambda: "d" * 64)
    slot = ArtifactSlot(
        family=ArtifactFamily.ANCHOR_CHECKPOINT,
        instance="N_BAIOT-seed-1-final",
    )
    dependencies = (
        ArtifactDependency(
            kind=ArtifactDependencyKind.CONTENT,
            dependency=ArtifactDependencyLabel.PREPARED_EVIDENCE,
            digest="e" * 64,
        ),
    )
    slot_directory = tmp_path / "anchor"
    staging_root = tmp_path / "staging"

    consumers = (
        ExperimentName.PROPOSAL_ASSISTED_OPENING_NECESSITY,
        ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION,
    )
    publications = tuple(
        publish_artifact(
            slot=slot,
            producer=ArtifactProducer.ANCHOR_TRAINING,
            payload=b"same compatible anchor",
            dependencies=dependencies,
            procedure_identity="fedsira|anchor_checkpoint|1",
            slot_directory=slot_directory,
            staging_root=staging_root,
        )
        for _consumer in consumers
    )
    (first, first_reused), (second, second_reused) = publications

    assert slot.experiment is None
    assert not first_reused
    assert second_reused
    assert second.identity == first.identity
    assert len(tuple(slot_directory.glob("*.manifest.json"))) == 1


def test_publishing_moves_the_current_pointer_to_the_published_identity(tmp_path: Path) -> None:
    payload = b"payload"
    directory = tmp_path / "canonical"
    published = publish_artifact_to_disk(
        stage_payload(tmp_path / "staging", payload),
        directory,
        staged_manifest("a" * 64, payload),
        payload,
    )
    current = read_current_artifact(directory)
    assert current is not None
    manifest, current_payload = current
    assert manifest == published
    assert current_payload == payload


def test_current_artifact_reports_nothing_before_any_publish(tmp_path: Path) -> None:
    assert read_current_artifact(tmp_path / "canonical") is None
