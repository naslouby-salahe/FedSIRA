from pathlib import Path

from pytest import MonkeyPatch

from fedsira.datasets.common import DatasetAdapter, PreparedRows, Role, dataset_specification
from fedsira.domain.enums import DatasetId
from fedsira.domain.types import DatasetClassToken, DomainId
from fedsira.experiments.reproduction_progression import model_replacement_attack_feasible_domains


def test_model_replacement_requires_at_least_one_configured_carrier_row(
    monkeypatch: MonkeyPatch,
) -> None:
    adapter = DatasetAdapter(
        specification=dataset_specification(DatasetId.N_BAIOT),
        prepared_root=Path("prepared-fixture"),
    )
    no_carrier_domains = frozenset(adapter.domain_ids[:2])

    def fake_load_rows(
        _adapter: DatasetAdapter,
        domain: DomainId,
        _class_token: DatasetClassToken,
        _role: Role,
    ) -> PreparedRows | None:
        if domain in no_carrier_domains:
            return None
        return PreparedRows(
            sample_ids=tuple(f"sample-{index}" for index in range(10)),
            features=(),
            labels=(),
        )

    monkeypatch.setattr(DatasetAdapter, "load_rows", fake_load_rows)

    feasible = model_replacement_attack_feasible_domains(adapter)

    assert feasible == frozenset(adapter.domain_ids[2:])
