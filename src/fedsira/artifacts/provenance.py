import hashlib
import os
import platform
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path
from typing import TypeAlias

import torch

from fedsira.domain.enums import ArtifactFamily, ArtifactLifecycleState
from fedsira.domain.types import (
    ArtifactActive,
    ArtifactDigest,
    DatasetClassToken,
    DatasetManifestDigest,
    DomainCount,
    FileCount,
    FrozenDomainModel,
    GitCommit,
    PredictorCount,
    PredictorCountMatchesOfficial,
    RowCount,
)

ArtifactPayloadBytes: TypeAlias = bytes


class ArtifactManifest(FrozenDomainModel):
    family: ArtifactFamily
    identity: ArtifactDigest
    checksum: ArtifactDigest
    lifecycle_state: ArtifactLifecycleState
    upstream_identities: tuple[ArtifactDigest, ...]

    def with_lifecycle_state(
        self,
        lifecycle_state: ArtifactLifecycleState,
    ) -> "ArtifactManifest":
        return ArtifactManifest(
            family=self.family,
            identity=self.identity,
            checksum=self.checksum,
            lifecycle_state=lifecycle_state,
            upstream_identities=self.upstream_identities,
        )


class NBaiotDatasetManifestPayload(FrozenDomainModel):
    dataset_file_manifest_hash: DatasetManifestDigest
    structurally_unavailable_classes: tuple[DatasetClassToken, ...]


class CICIoT2023DatasetManifestPayload(FrozenDomainModel):
    dataset_file_manifest_hash: DatasetManifestDigest
    file_count: FileCount
    raw_row_count: RowCount
    retained_row_count: RowCount
    excluded_row_count: RowCount
    predictor_count: PredictorCount
    official_expected_predictor_count: PredictorCount
    predictor_count_matches_official: PredictorCountMatchesOfficial
    class_registry: tuple[DatasetClassToken, ...]
    pseudo_domain_count: DomainCount


DatasetManifestPayload = NBaiotDatasetManifestPayload | CICIoT2023DatasetManifestPayload


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


class ReconstructionProvenance(FrozenDomainModel):
    repository_commit: GitCommit
    dependency_lock_digest: ArtifactDigest
    environment_fingerprint: ArtifactDigest


def collect_reconstruction_provenance(repository_root: Path) -> ReconstructionProvenance:
    lock_path = repository_root / "uv.lock"
    if not lock_path.is_file():
        raise ValueError(f"required dependency lock is missing: {lock_path}")
    result = subprocess.run(
        ["git", "-C", str(repository_root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    commit = result.stdout.strip()
    git_commit_hex_length = 40
    if result.returncode != 0 or len(commit) != git_commit_hex_length:
        raise ValueError("unable to resolve the current repository commit for provenance")
    return ReconstructionProvenance(
        repository_commit=commit,
        dependency_lock_digest=hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        environment_fingerprint=_environment_fingerprint(),
    )


def _environment_fingerprint() -> ArtifactDigest:
    cuda_device = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "unavailable"
    payload = "\n".join(
        (
            os.name,
            platform.system(),
            platform.release(),
            platform.machine(),
            sys.version,
            torch.__version__,
            str(torch.version.cuda),
            str(torch.backends.cudnn.version()),
            cuda_device,
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_artifact_lifecycle_readable(manifest: ArtifactManifest) -> None:
    if manifest.lifecycle_state is not ArtifactLifecycleState.COMPLETE:
        raise ValueError(
            f"artifact {manifest.identity} is not Complete ({manifest.lifecycle_state.value}); "
            "it is never a valid input to downstream science"
        )
