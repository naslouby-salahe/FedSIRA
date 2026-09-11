import hashlib
import json
from collections import defaultdict
from pathlib import Path

from fedsira.domain.enums import DatasetId
from fedsira.domain.types import (
    ArtifactDigest,
    DatasetClassToken,
    DomainId,
    FrozenDomainModel,
    PredictorCount,
    RepositoryPath,
    RoleToken,
    RowCount,
    TextValue,
)


class DatasetSpecification(FrozenDomainModel):
    dataset: DatasetId
    class_tokens: tuple[DatasetClassToken, ...]
    domain_ids: tuple[DomainId, ...]
    target_class: DatasetClassToken
    benign_class: DatasetClassToken
    supported_class_tokens: tuple[DatasetClassToken, ...]
    expected_predictor_count: PredictorCount | None
    domain_proxy_semantics: TextValue
    raw_data_relative: RepositoryPath


class PreparedDomainSummary(FrozenDomainModel):
    domain_id: DomainId
    counts: tuple[tuple[RoleToken, DatasetClassToken, RowCount], ...]

    def count(self, role: RoleToken, class_token: DatasetClassToken) -> RowCount:
        return next(
            (
                value
                for observed_role, observed_class, value in self.counts
                if observed_role == role and observed_class == class_token
            ),
            0,
        )

    def count_for_role(
        self, role: RoleToken, excluded_classes: frozenset[DatasetClassToken] = frozenset()
    ) -> RowCount:
        return sum(
            value
            for observed_role, observed_class, value in self.counts
            if observed_role == role and observed_class not in excluded_classes
        )


def dataset_specification(dataset: DatasetId) -> DatasetSpecification:
    if dataset is DatasetId.N_BAIOT:
        from fedsira.datasets.nbaiot.specification import specification

        return specification()
    if dataset is DatasetId.CICIOT2023:
        from fedsira.datasets.ciciot2023.specification import specification

        return specification()
    raise ValueError(f"no dataset specification for {dataset.value}")


def prepared_domain_summaries(
    dataset: DatasetId,
    prepared_root: Path,
) -> tuple[PreparedDomainSummary, ...]:
    specification = dataset_specification(dataset)
    counts: defaultdict[DomainId, defaultdict[tuple[str, DatasetClassToken], int]] = defaultdict(
        lambda: defaultdict(int)
    )
    for sidecar in sorted(prepared_root.glob("*.json")):
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        domain = payload.get("domain", payload.get("pseudo_domain"))
        class_token = payload.get("class_id", payload.get("normalized_label"))
        role = payload.get("role")
        row_count = payload.get("row_count")
        if domain is None or class_token is None or role is None or not isinstance(row_count, int):
            raise ValueError(f"invalid prepared-view sidecar: {sidecar}")
        domain_id = (
            f"PSEUDO_DOMAIN_{int(domain) + 1}" if dataset is DatasetId.CICIOT2023 else str(domain)
        )
        if domain_id not in specification.domain_ids:
            raise ValueError(f"unexpected {dataset.value} domain {domain_id!r} in {sidecar}")
        counts[domain_id][(str(role), str(class_token))] += row_count
    if not counts:
        raise ValueError(f"no prepared-view evidence exists for {dataset.value}")
    return tuple(
        PreparedDomainSummary(
            domain_id=domain_id,
            counts=tuple(
                (role, class_token, row_count)
                for (role, class_token), row_count in sorted(domain_counts.items())
            ),
        )
        for domain_id, domain_counts in sorted(counts.items())
    )


def prepared_view_digest(prepared_root: Path) -> ArtifactDigest:
    sidecars = tuple(sorted(prepared_root.glob("*.json")))
    if not sidecars:
        raise ValueError(f"no prepared-view evidence exists at {prepared_root}")
    digest = hashlib.sha256()
    for sidecar in sidecars:
        digest.update(sidecar.name.encode("utf-8"))
        digest.update(sidecar.read_bytes())
    return digest.hexdigest()
