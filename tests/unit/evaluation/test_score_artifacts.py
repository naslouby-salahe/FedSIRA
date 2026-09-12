from pathlib import Path

import pytest

from fedsira.artifacts.paths import artifact_slot_directory
from fedsira.artifacts.store import ArtifactManifest, read_current_artifact
from fedsira.domain.enums import ArtifactDependencyKind, ArtifactFamily, DatasetId, Role
from fedsira.evaluation.scores import (
    DEFAULT_SCORING_TRANSFORM,
    DomainClassScore,
    ModelScorePayload,
    class_registry_digest,
    model_score_slot,
    model_score_view_digest,
    publish_model_score,
    sample_ids_digest,
)


@pytest.fixture
def isolated_repository(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr("fedsira.evaluation.scores.REPOSITORY_ROOT", tmp_path)
    return tmp_path


def _shards(predicted: tuple[int, ...]) -> tuple[DomainClassScore, ...]:
    return (
        DomainClassScore(
            domain="Danmini Doorbell",
            class_id="GAFGYT_COMBO",
            role=Role.CANDIDATE_SCREEN,
            sample_count=len(predicted),
            predicted_class_indices=",".join(str(index) for index in predicted),
            sample_ids_digest=sample_ids_digest(("a" * 64,)),
        ),
    )


def test_score_artifact_is_sharded_by_domain_class_and_role(isolated_repository: Path) -> None:
    manifest, reused = publish_model_score(
        DatasetId.N_BAIOT,
        "b" * 64,
        DEFAULT_SCORING_TRANSFORM,
        ("BENIGN", "GAFGYT_COMBO"),
        _shards((0, 1, 1)),
    )
    assert reused is False
    assert manifest.family is ArtifactFamily.MODEL_SCORE_ARTIFACT
    kinds = tuple(dependency.kind for dependency in manifest.dependencies)
    assert kinds == (
        ArtifactDependencyKind.CONTENT,
        ArtifactDependencyKind.CONTENT,
        ArtifactDependencyKind.CONTENT,
        ArtifactDependencyKind.CONTENT,
        ArtifactDependencyKind.CONTENT,
    )
    current = read_current_artifact(isolated_repository / artifact_slot_directory(manifest.slot))
    assert current is not None
    _stored, payload = current
    restored = ModelScorePayload.model_validate_json(payload)
    assert restored.model_identity == "b" * 64
    assert restored.shards == _shards((0, 1, 1))
    assert restored.class_tokens == ("BENIGN", "GAFGYT_COMBO")


def test_score_artifact_reuses_and_invalidates_on_model_or_view_identity(
    isolated_repository: Path,
) -> None:
    first, _reused = publish_model_score(
        DatasetId.N_BAIOT,
        "b" * 64,
        DEFAULT_SCORING_TRANSFORM,
        ("BENIGN", "GAFGYT_COMBO"),
        _shards((0, 1, 1)),
    )
    repeated, reused_again = publish_model_score(
        DatasetId.N_BAIOT,
        "b" * 64,
        DEFAULT_SCORING_TRANSFORM,
        ("BENIGN", "GAFGYT_COMBO"),
        _shards((0, 1, 1)),
    )
    assert reused_again is True
    assert repeated.identity == first.identity
    changed_transform, _reused_transform = publish_model_score(
        DatasetId.N_BAIOT,
        "b" * 64,
        "argmax-probabilities",
        ("BENIGN", "GAFGYT_COMBO"),
        _shards((0, 1, 1)),
    )
    assert changed_transform.identity != first.identity
    other_model, _reused_model = publish_model_score(
        DatasetId.N_BAIOT,
        "c" * 64,
        DEFAULT_SCORING_TRANSFORM,
        ("BENIGN", "GAFGYT_COMBO"),
        _shards((0, 1, 1)),
    )
    assert other_model.identity != first.identity


def test_view_digest_is_order_independent_and_content_sensitive() -> None:
    first = _shards((0, 1))
    second = DomainClassScore(
        domain="Danmini Doorbell",
        class_id="BENIGN",
        role=Role.ANCHOR_TRAIN,
        sample_count=1,
        predicted_class_indices="0",
        sample_ids_digest=sample_ids_digest(("c" * 64,)),
    )
    assert model_score_view_digest((*first, second)) == model_score_view_digest((second, *first))
    assert model_score_view_digest(first) != model_score_view_digest((second,))


def test_score_identity_tracks_the_numerical_runtime(
    isolated_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, _reused = publish_model_score(
        DatasetId.N_BAIOT,
        "b" * 64,
        DEFAULT_SCORING_TRANSFORM,
        ("BENIGN",),
        _shards((0,)),
    )
    monkeypatch.setattr("fedsira.evaluation.scores.numerical_runtime_identity", lambda: "0" * 64)
    changed_runtime, _reused_runtime = publish_model_score(
        DatasetId.N_BAIOT,
        "b" * 64,
        DEFAULT_SCORING_TRANSFORM,
        ("BENIGN",),
        _shards((0,)),
    )
    assert changed_runtime.identity != first.identity


def test_class_registry_digest_separates_output_registries() -> None:
    assert class_registry_digest(("BENIGN", "GAFGYT_COMBO")) != class_registry_digest(("BENIGN",))


def test_score_slot_separates_models_and_views() -> None:
    assert model_score_slot("b" * 64, "c" * 64) != model_score_slot("d" * 64, "c" * 64)
    assert model_score_slot("b" * 64, "c" * 64) != model_score_slot("b" * 64, "e" * 64)


def test_score_manifest_exposes_its_identity_type(isolated_repository: Path) -> None:
    manifest: ArtifactManifest = publish_model_score(
        DatasetId.N_BAIOT,
        "b" * 64,
        DEFAULT_SCORING_TRANSFORM,
        ("BENIGN",),
        _shards((0,)),
    )[0]
    assert manifest.slot.family is ArtifactFamily.MODEL_SCORE_ARTIFACT
    assert manifest.slot.experiment is None
