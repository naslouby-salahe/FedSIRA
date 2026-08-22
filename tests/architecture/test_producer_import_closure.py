import sys
import tempfile
from pathlib import Path
from typing import cast

import fedsira
from fedsira.artifacts.fingerprints import (
    PRODUCER_ENTRY_MODULES,
    compute_producer_component_fingerprint,
    raw_schema_exclusion_manifest_entry_modules,
    resolve_producer_import_closure,
)
from fedsira.domain.enums import DatasetId


def test_every_registered_producer_entry_module_resolves() -> None:
    for entry_modules in PRODUCER_ENTRY_MODULES.values():
        closure = resolve_producer_import_closure(entry_modules)
        for entry in entry_modules:
            assert entry in closure


def test_raw_schema_exclusion_manifest_entry_modules_resolve_for_each_dataset() -> None:
    for dataset in DatasetId:
        entry_modules = raw_schema_exclusion_manifest_entry_modules(dataset)
        closure = resolve_producer_import_closure(entry_modules)
        assert set(entry_modules) <= closure.keys()


def _install_fixture_package(root: Path) -> None:
    package = root / "fixture_producer"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "entry.py").write_text("from fedsira.fixture_producer import helper\n")
    (package / "helper.py").write_text("VALUE = 1\n")
    cast("list[str]", fedsira.__path__).append(str(root))


def _uninstall_fixture_package(root: Path) -> None:
    search_path = cast("list[str]", fedsira.__path__)
    if str(root) in search_path:
        search_path.remove(str(root))
    for name in list(sys.modules):
        if name == "fedsira.fixture_producer" or name.startswith("fedsira.fixture_producer."):
            del sys.modules[name]


def test_import_closure_is_reproducible() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _install_fixture_package(root)
        try:
            first = compute_producer_component_fingerprint(("fedsira.fixture_producer.entry",), "1")
            second = compute_producer_component_fingerprint(
                ("fedsira.fixture_producer.entry",), "1"
            )
            assert first == second
        finally:
            _uninstall_fixture_package(root)


def test_import_closure_reaches_transitive_helper() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _install_fixture_package(root)
        try:
            closure = resolve_producer_import_closure(("fedsira.fixture_producer.entry",))
            assert "fedsira.fixture_producer.helper" in closure
        finally:
            _uninstall_fixture_package(root)


def test_fingerprint_changes_when_a_new_dependency_is_imported() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _install_fixture_package(root)
        try:
            baseline = compute_producer_component_fingerprint(
                ("fedsira.fixture_producer.entry",), "1"
            )
            package = root / "fixture_producer"
            (package / "helper.py").write_text("VALUE = 2\n")
            changed = compute_producer_component_fingerprint(
                ("fedsira.fixture_producer.entry",), "1"
            )
            assert baseline != changed
        finally:
            _uninstall_fixture_package(root)


def test_type_checking_guarded_import_is_excluded_from_closure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _install_fixture_package(root)
        package = root / "fixture_producer"
        (package / "entry.py").write_text(
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    from fedsira.fixture_producer import helper\n"
        )
        try:
            closure = resolve_producer_import_closure(("fedsira.fixture_producer.entry",))
            assert "fedsira.fixture_producer.helper" not in closure
        finally:
            _uninstall_fixture_package(root)


def test_dynamic_import_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _install_fixture_package(root)
        package = root / "fixture_producer"
        (package / "entry.py").write_text("import importlib\nimportlib.import_module('os')\n")
        try:
            raised = False
            try:
                compute_producer_component_fingerprint(("fedsira.fixture_producer.entry",), "1")
            except ValueError:
                raised = True
            assert raised
        finally:
            _uninstall_fixture_package(root)
