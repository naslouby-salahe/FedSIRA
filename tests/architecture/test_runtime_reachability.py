from modulefinder import ModuleFinder

from _repo import REPO_ROOT, SRC_ROOT, iter_python_files, module_name

APPLICATION_ENTRY_MODULES = (
    "fedsira.cli.main",
    "fedsira.workflows.doctor",
    "fedsira.workflows.preprocess",
    "fedsira.workflows.plan",
    "fedsira.workflows.smoke",
    "fedsira.workflows.run",
    "fedsira.workflows.report",
)


def _application_modules() -> frozenset[str]:
    finder = ModuleFinder(path=[str(SRC_ROOT.parent)])
    finder.run_script(str(SRC_ROOT / "cli" / "main.py"))
    return frozenset(
        (
            "fedsira.cli.main",
            *(name for name in finder.modules if name == "fedsira" or name.startswith("fedsira.")),
        )
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
