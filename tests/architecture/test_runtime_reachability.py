from _repo import REPO_ROOT, SRC_ROOT, iter_python_files, module_name

from fedsira.artifacts.fingerprints import resolve_producer_import_closure

APPLICATION_ENTRY_MODULES = (
    "fedsira.cli.main",
    "fedsira.cli.commands.doctor",
    "fedsira.cli.commands.preprocess",
    "fedsira.cli.commands.plan",
    "fedsira.cli.commands.smoke",
    "fedsira.cli.commands.run",
    "fedsira.cli.commands.report",
)


def _application_modules() -> frozenset[str]:
    return frozenset(
        source.module for source in resolve_producer_import_closure(APPLICATION_ENTRY_MODULES)
    )


def test_every_production_module_is_on_the_cli_application_graph() -> None:
    reachable = _application_modules()
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        if path.name == "__init__.py":
            continue
        name = module_name(path)
        if name not in reachable:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert (
        not offenders
    ), f"Production modules not imported from CLI/application runtime graph: {offenders}"


def test_cli_entry_modules_are_present_in_the_runtime_graph() -> None:
    reachable = _application_modules()
    missing = [name for name in APPLICATION_ENTRY_MODULES if name not in reachable]
    assert not missing, f"CLI entry modules missing from import closure: {missing}"
