from fedsira.artifacts.records import ArtifactManifest
from fedsira.domain.enums import ArtifactLifecycleState
from fedsira.domain.records import ArtifactDigest, BooleanValue


class ArtifactGraph:
    def __init__(self) -> None:
        self._nodes: tuple[ArtifactManifest, ...] = ()

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

    def is_active(self, identity: ArtifactDigest) -> BooleanValue:
        node = self._find(identity)
        return node is not None and node.lifecycle_state is ArtifactLifecycleState.COMPLETE

    def direct_descendants(self, identity: ArtifactDigest) -> tuple[ArtifactDigest, ...]:
        return tuple(
            node.identity for node in self._nodes if identity in node.upstream_identities
        )

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
