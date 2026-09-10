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
    assert "execute_experiment" not in calls
