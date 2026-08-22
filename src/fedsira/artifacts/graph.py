from fedsira.artifacts.records import ArtifactManifest
from fedsira.domain.enums import ArtifactLifecycleState
from fedsira.domain.records import ArtifactDigest


class ArtifactGraph:
    def __init__(self) -> None:
        self._nodes: dict[ArtifactDigest, ArtifactManifest] = {}

    def register(self, manifest: ArtifactManifest) -> None:
        for upstream_identity in manifest.upstream_identities:
            if upstream_identity not in self._nodes:
                raise ValueError(f"unknown upstream artifact identity {upstream_identity}")
        self._nodes[manifest.identity] = manifest

    def get(self, identity: ArtifactDigest) -> ArtifactManifest:
        return self._nodes[identity]

    def is_active(self, identity: ArtifactDigest) -> bool:
        node = self._nodes.get(identity)
        return node is not None and node.lifecycle_state is ArtifactLifecycleState.COMPLETE

    def direct_descendants(self, identity: ArtifactDigest) -> tuple[ArtifactDigest, ...]:
        return tuple(
            node.identity for node in self._nodes.values() if identity in node.upstream_identities
        )

    def mark_stale_descendants(
        self, changed_identity: ArtifactDigest
    ) -> tuple[ArtifactDigest, ...]:
        staled: list[ArtifactDigest] = []
        frontier = list(self.direct_descendants(changed_identity))
        visited: set[ArtifactDigest] = set()
        while frontier:
            identity = frontier.pop()
            if identity in visited:
                continue
            visited.add(identity)
            node = self._nodes[identity]
            if node.lifecycle_state is ArtifactLifecycleState.COMPLETE:
                self._nodes[identity] = node.model_copy(
                    update={"lifecycle_state": ArtifactLifecycleState.STALE}
                )
                staled.append(identity)
            frontier.extend(self.direct_descendants(identity))
        return tuple(staled)
