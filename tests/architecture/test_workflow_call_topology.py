import ast
from pathlib import Path

from _repo import REPO_ROOT


def _called_names(path: Path) -> frozenset[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            names.add(node.func.id)
        if isinstance(node.func, ast.Attribute):
            names.add(node.func.attr)
    return frozenset(names)


def test_run_workflow_reaches_execution_evaluation_and_evidence_export() -> None:
    calls = _called_names(REPO_ROOT / "src" / "fedsira" / "application.py")
    expected: frozenset[str] = frozenset(
        (
            "ProtocolCellExecutor",
            "execute_experiment",
            "comparison_results_for_experiment",
            "export_experiment_report",
        )
    )
    assert expected <= calls, f"run workflow bypasses required execution path: {expected - calls}"


def test_report_workflow_reaches_persisted_evidence_and_publication_export() -> None:
    calls = _called_names(REPO_ROOT / "src" / "fedsira" / "reporting" / "export.py")
    expected: frozenset[str] = frozenset(
        (
            "ExecutionRecordStore",
            "export_experiment_report",
            "export_project_summary",
        )
    )
    assert (
        expected <= calls
    ), f"report workflow bypasses required publication path: {expected - calls}"


def test_status_workflow_reaches_persisted_evidence_without_execution() -> None:
    calls = _called_names(REPO_ROOT / "src" / "fedsira" / "experiments" / "execution.py")
    expected: frozenset[str] = frozenset(
        (
            "ExecutionRecordStore",
            "derive_experiment_lifecycle",
        )
    )
    assert expected <= calls, f"status workflow bypasses persisted evidence: {expected - calls}"
    assert "execute_status" in _called_names(REPO_ROOT / "src" / "fedsira" / "application.py")
    assert "execute_experiment" not in _called_names(REPO_ROOT / "src" / "fedsira" / "cli.py")


def test_cli_only_dispatches_to_application() -> None:
    calls = _called_names(REPO_ROOT / "src" / "fedsira" / "cli.py")
    expected = frozenset(("doctor", "preprocess", "plan", "smoke", "run", "status", "report"))
    assert expected <= calls
    assert "execute_experiment" not in calls
    assert "ProtocolCellExecutor" not in calls
    assert "export_experiment_report" not in calls


def test_preprocess_workflow_reaches_dataset_materialization() -> None:
    calls = _called_names(REPO_ROOT / "src" / "fedsira" / "datasets" / "preprocess.py")
    expected: frozenset[str] = frozenset(
        (
            "materialize_nbaiot_prepared_views",
            "materialize_ciciot2023_prepared_views",
            "publish_artifact",
        )
    )
    assert expected <= calls, f"preprocess bypasses dataset artifacts: {expected - calls}"


def test_plan_workflow_reaches_plan_construction() -> None:
    calls = _called_names(REPO_ROOT / "src" / "fedsira" / "experiments" / "planning.py")
    expected: frozenset[str] = frozenset(("build_plan", "validate_planned_cell_count_invariant"))
    assert expected <= calls, f"plan bypasses plan construction: {expected - calls}"


def test_application_wires_every_cli_command() -> None:
    calls = _called_names(REPO_ROOT / "src" / "fedsira" / "application.py")
    expected: frozenset[str] = frozenset(
        (
            "diagnose",
            "execute_preprocess",
            "execute_plan",
            "execute_smoke",
            "execute_run",
            "execute_status",
            "execute_report",
        )
    )
    assert expected <= calls, f"application missing CLI workflow: {expected - calls}"


def _method_node(path: Path, method_name: str) -> ast.FunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return node
    raise AssertionError(f"method {method_name} not found in {path.name}")


def test_opening_stage_observations_consume_the_callers_stage() -> None:
    handlers = REPO_ROOT / "src" / "fedsira" / "experiments" / "handlers.py"
    node = _method_node(handlers, "_opening_stage_observations")
    argument_names = tuple(argument.arg for argument in node.args.args)
    assert "stage" in argument_names, (
        "opening-stage observations must take the resolved stage explicitly rather than "
        "reading shared protocol state"
    )
    shared_state_reads = tuple(
        attribute.attr
        for attribute in ast.walk(node)
        if isinstance(attribute, ast.Attribute) and attribute.attr == "_last_opening_stage"
    )
    assert not shared_state_reads, (
        "opening-stage observations must not read _last_opening_stage, which the downstream "
        "protocol advance resets"
    )
    observation_calls = tuple(
        call
        for call in ast.walk(ast.parse(handlers.read_text(encoding="utf-8")))
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "_opening_stage_observations"
    )
    assert observation_calls, "the opening cell must emit its opening-stage observations"
    assert all(
        len(call.args) == 2 for call in observation_calls
    ), "every opening-stage observation call must pass the stage and the state"
