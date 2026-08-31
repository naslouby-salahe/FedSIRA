from collections import OrderedDict
from pathlib import Path

from fedsira.artifacts.records import ArtifactManifest
from fedsira.domain.enums import ArtifactLifecycleState
from fedsira.domain.records import ArtifactActive, ArtifactDigest

PUBLISHED_MANIFEST_SUFFIX = ".manifest.json"


class ArtifactGraph:
    def __init__(self) -> None:
        self._nodes: tuple[ArtifactManifest, ...] = ()

    @property
    def nodes(self) -> tuple[ArtifactManifest, ...]:
        return self._nodes

    def _find(self, identity: ArtifactDigest) -> ArtifactManifest | None:
        for node in self._nodes:
            if node.identity == identity:
                return node
        return None

    def register(self, manifest: ArtifactManifest) -> None:
        for upstream_identity in manifest.upstream_identities:
            if self._find(upstream_identity) is None:
                raise ValueError(f"unknown upstream artifact identity {upstream_identity}")
        retained = tuple(node for node in self._nodes if node.identity != manifest.identity)
        self._nodes = (*retained, manifest)

    def get(self, identity: ArtifactDigest) -> ArtifactManifest:
        node = self._find(identity)
        if node is None:
            raise KeyError(identity)
        return node

    def is_active(self, identity: ArtifactDigest) -> ArtifactActive:
        node = self._find(identity)
        return node is not None and node.lifecycle_state is ArtifactLifecycleState.COMPLETE

    def direct_descendants(self, identity: ArtifactDigest) -> tuple[ArtifactDigest, ...]:
        return tuple(node.identity for node in self._nodes if identity in node.upstream_identities)

    def mark_stale_descendants(
        self,
        changed_identity: ArtifactDigest,
    ) -> tuple[ArtifactDigest, ...]:
        staled: list[ArtifactDigest] = []
        frontier = list(self.direct_descendants(changed_identity))
        visited: set[ArtifactDigest] = set()
        while frontier:
            identity = frontier.pop()
            if identity in visited:
                continue
            visited.add(identity)
            node = self.get(identity)
            if node.lifecycle_state is ArtifactLifecycleState.COMPLETE:
                stale_node = ArtifactManifest(
                    family=node.family,
                    identity=node.identity,
                    checksum=node.checksum,
                    lifecycle_state=ArtifactLifecycleState.STALE,
                    upstream_identities=node.upstream_identities,
                )
                self.register(stale_node)
                staled.append(identity)
            frontier.extend(self.direct_descendants(identity))
        return tuple(staled)


def load_published_manifests(roots: tuple[Path, ...]) -> tuple[ArtifactManifest, ...]:
    manifests: list[ArtifactManifest] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob(f"*{PUBLISHED_MANIFEST_SUFFIX}")):
            manifests.append(ArtifactManifest.model_validate_json(path.read_text(encoding="utf-8")))
    return tuple(manifests)


def artifact_graph_from_manifests(
    manifests: tuple[ArtifactManifest, ...],
) -> tuple[ArtifactGraph, tuple[ArtifactDigest, ...]]:
    graph = ArtifactGraph()
    remaining: OrderedDict[ArtifactDigest, ArtifactManifest] = OrderedDict()
    for manifest in manifests:
        remaining[manifest.identity] = manifest
    registered: set[ArtifactDigest] = set()
    while remaining:
        ready = tuple(
            manifest
            for manifest in remaining.values()
            if all(upstream in registered for upstream in manifest.upstream_identities)
        )
        if not ready:
            break
        for manifest in ready:
            graph.register(manifest)
            registered.add(manifest.identity)
            del remaining[manifest.identity]
    return graph, tuple(remaining)


def load_published_artifact_graph(
    roots: tuple[Path, ...],
) -> tuple[ArtifactGraph, tuple[ArtifactDigest, ...]]:
    return artifact_graph_from_manifests(load_published_manifests(roots))


def stale_artifact_identities(graph: ArtifactGraph) -> tuple[ArtifactDigest, ...]:
    return tuple(
        node.identity
        for node in graph.nodes
        if node.lifecycle_state is ArtifactLifecycleState.STALE
    )
