from pathlib import Path

import pytest

from fedsira.artifacts.graph import ArtifactGraph
from fedsira.artifacts.records import ArtifactManifest
from fedsira.domain.enums import ArtifactFamily, ArtifactLifecycleState


def complete_manifest(identity: str, upstream: tuple[str, ...] = ()) -> ArtifactManifest:
    return ArtifactManifest(
        family=ArtifactFamily.SCALER,
        identity=identity,
        checksum="b" * 64,
        lifecycle_state=ArtifactLifecycleState.COMPLETE,
        upstream_identities=upstream,
    )


def test_register_requires_known_upstream() -> None:
    graph = ArtifactGraph()
    with pytest.raises(ValueError):
        graph.register(complete_manifest("a" * 64, upstream=("z" * 64,)))


def test_is_active_true_for_complete_registered_artifact() -> None:
    graph = ArtifactGraph()
    graph.register(complete_manifest("a" * 64))
    assert graph.is_active("a" * 64)


def test_is_active_false_for_unknown_artifact() -> None:
    graph = ArtifactGraph()
    assert not graph.is_active("a" * 64)


def test_mark_stale_descendants_only_affects_downstream() -> None:
    graph = ArtifactGraph()
    graph.register(complete_manifest("a" * 64))
    graph.register(complete_manifest("b" * 64, upstream=("a" * 64,)))
    graph.register(complete_manifest("c" * 64, upstream=("b" * 64,)))
    graph.register(complete_manifest("d" * 64))

    staled = graph.mark_stale_descendants("a" * 64)

    assert set(staled) == {"b" * 64, "c" * 64}
    assert not graph.is_active("b" * 64)
    assert not graph.is_active("c" * 64)
    assert graph.is_active("d" * 64)
    assert graph.get("b" * 64).lifecycle_state is ArtifactLifecycleState.STALE
    assert graph.get("c" * 64).lifecycle_state is ArtifactLifecycleState.STALE


def test_load_published_artifact_graph_walks_manifests_and_reports_stale(
    tmp_path: Path,
) -> None:
    from fedsira.artifacts.graph import (
        load_published_artifact_graph,
        stale_artifact_identities,
    )
    from fedsira.io.storage import ARTIFACT_MANIFEST_SUFFIX

    parent = complete_manifest("a" * 64)
    child = complete_manifest("b" * 64, upstream=("a" * 64,))
    (tmp_path / f"{parent.identity}{ARTIFACT_MANIFEST_SUFFIX}").write_text(parent.model_dump_json())
    stale_child = ArtifactManifest(
        family=child.family,
        identity=child.identity,
        checksum=child.checksum,
        lifecycle_state=ArtifactLifecycleState.STALE,
        upstream_identities=child.upstream_identities,
    )
    (tmp_path / f"{stale_child.identity}{ARTIFACT_MANIFEST_SUFFIX}").write_text(
        stale_child.model_dump_json()
    )
    graph, unresolved = load_published_artifact_graph((tmp_path,))
    assert not unresolved
    assert stale_artifact_identities(graph) == (stale_child.identity,)


def test_mark_stale_descendants_is_transitive_only_downstream() -> None:
    graph = ArtifactGraph()
    graph.register(complete_manifest("a" * 64))
    graph.register(complete_manifest("b" * 64, upstream=("a" * 64,)))

    graph.mark_stale_descendants("b" * 64)

    assert graph.is_active("a" * 64)
