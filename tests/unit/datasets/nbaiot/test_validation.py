from pathlib import Path

import pytest

from fedsira.datasets.nbaiot.acquisition import DiscoveredCsvFile
from fedsira.datasets.nbaiot.schema import NBAIOT_CLASS_ORDER, NBaiotClass, NBaiotDomain
from fedsira.datasets.nbaiot.validation import (
    classes_structurally_unavailable,
    domains_missing_target_stream,
    domains_with_target_stream,
    validate_target_holder_feasibility,
)


def _file(domain: NBaiotDomain, class_id: NBaiotClass) -> DiscoveredCsvFile:
    return DiscoveredCsvFile(
        domain=domain,
        class_id=class_id,
        relative_path="x.csv",
        file_sha256="a" * 64,
        absolute_path=Path("x.csv"),
    )


def test_domains_with_target_stream_counts_only_gafgyt_combo() -> None:
    discovered = (
        _file(NBaiotDomain.DANMINI_DOORBELL, NBaiotClass.GAFGYT_COMBO),
        _file(NBaiotDomain.DANMINI_DOORBELL, NBaiotClass.BENIGN),
        _file(NBaiotDomain.ENNIO_DOORBELL, NBaiotClass.GAFGYT_JUNK),
    )
    assert domains_with_target_stream(discovered) == {NBaiotDomain.DANMINI_DOORBELL}


def test_domains_missing_target_stream_is_ordered_and_excludes_holders() -> None:
    discovered = (_file(NBaiotDomain.DANMINI_DOORBELL, NBaiotClass.GAFGYT_COMBO),)
    missing = domains_missing_target_stream(discovered)
    assert NBaiotDomain.DANMINI_DOORBELL not in missing
    assert NBaiotDomain.ENNIO_DOORBELL in missing
    assert len(missing) == 8


def test_validate_target_holder_feasibility_accepts_sufficient_holders() -> None:
    discovered = tuple(_file(domain, NBaiotClass.GAFGYT_COMBO) for domain in list(NBaiotDomain)[:7])
    validate_target_holder_feasibility(discovered, minimum_target_holding_domains=7)


def test_validate_target_holder_feasibility_rejects_insufficient_holders() -> None:
    discovered = tuple(_file(domain, NBaiotClass.GAFGYT_COMBO) for domain in list(NBaiotDomain)[:6])
    with pytest.raises(ValueError, match="only 6"):
        validate_target_holder_feasibility(discovered, minimum_target_holding_domains=7)


def test_classes_structurally_unavailable_reports_absent_classes_in_order() -> None:
    discovered = (_file(NBaiotDomain.ENNIO_DOORBELL, NBaiotClass.BENIGN),)
    unavailable = classes_structurally_unavailable(discovered)
    assert unavailable[0] is NBaiotClass.GAFGYT_COMBO
    assert len(unavailable) == len(NBAIOT_CLASS_ORDER) - 1


def test_classes_structurally_unavailable_is_empty_when_every_class_is_observed() -> None:
    discovered = tuple(
        _file(NBaiotDomain.DANMINI_DOORBELL, class_id) for class_id in NBAIOT_CLASS_ORDER
    )
    assert classes_structurally_unavailable(discovered) == ()
