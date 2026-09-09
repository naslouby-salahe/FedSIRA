import hashlib
import os
import platform
import subprocess
import sys
from pathlib import Path

import torch

from fedsira.domain.types import ArtifactDigest, FrozenDomainModel, GitCommit


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
    if result.returncode != 0 or len(commit) != 40:
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
