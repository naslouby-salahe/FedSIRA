import ast
import csv
import json
from pathlib import Path

from _repo import REPO_ROOT
from fedsira.experiments.handlers import ProtocolCellExecutor


def _called_names_for_node(node: ast.AST) -> frozenset[str]:
    names: set[str] = set()
    for call in (child for child in ast.walk(node) if isinstance(child, ast.Call)):
        if isinstance(call.func, ast.Name):
            names.add(call.func.id)
        elif isinstance(call.func, ast.Attribute):
            names.add(call.func.attr)
    return frozenset(names)


def _missing_calls(node: ast.AST, expected: frozenset[str]) -> frozenset[str]:
    return expected - _called_names_for_node(node)


def _called_names(path: Path) -> frozenset[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return _called_names_for_node(tree)


def test_run_workflow_reaches_execution_evaluation_and_metric_materialization() -> None:
    calls = _called_names(REPO_ROOT / "src" / "fedsira" / "application.py")
    expected: frozenset[str] = frozenset(
        (
            "ProtocolCellExecutor",
            "execute_experiment",
            "build_comparison_results_for_experiment",
            "materialize_experiment_evidence",
            "publish_metric_evidence",
        )
    )
    expected_calls = expected - {"build_comparison_results_for_experiment"}
    assert not (
        expected_calls - calls
    ), f"run workflow bypasses required execution path: {expected_calls - calls}"
    tree = ast.parse((REPO_ROOT / "src" / "fedsira" / "application.py").read_text())
    names = frozenset(node.id for node in ast.walk(tree) if isinstance(node, ast.Name))
    assert "build_comparison_results_for_experiment" in names


def test_report_workflow_exports_and_verifies_persisted_products() -> None:
    calls = _called_names(REPO_ROOT / "src" / "fedsira" / "reporting" / "export.py")
    expected: frozenset[str] = frozenset(
        (
            "ExecutionRecordStore",
            "verify_persisted_experiment_report",
            "export_experiment_report",
            "export_project_summary",
        )
    )
    assert (
        expected <= calls
    ), f"report workflow bypasses required publication path: {expected - calls}"
    assert "current_comparison_evidence" in calls
    assert "build_comparison_results_for_experiment" not in calls
    assert "export_experiment_report" in calls
    bound = _method_node(
        REPO_ROOT / "src" / "fedsira" / "reporting" / "export.py", "_execute_bound"
    )
    named_report = next(
        node
        for node in ast.walk(bound)
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "name"
    )
    named_calls = frozenset(
        node.func.id
        for node in ast.walk(named_report)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    )
    assert "export_experiment_report" in named_calls


def test_report_workflow_does_not_accept_stale_data_validation_records() -> None:
    calls = _called_names(REPO_ROOT / "src" / "fedsira" / "reporting" / "export.py")
    expected: frozenset[str] = frozenset(
        (
            "derive_current_experiment_lifecycle",
            "dataset_readiness",
        )
    )
    assert expected <= calls, (
        "project and experiment reports must reflect current prepared-data readiness "
        f"rather than stale validation records: {expected - calls}"
    )
    tree = ast.parse(
        (REPO_ROOT / "src" / "fedsira" / "reporting" / "export.py").read_text(encoding="utf-8")
    )
    names = frozenset(node.id for node in ast.walk(tree) if isinstance(node, ast.Name))
    assert "DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME" in names


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


def test_executor_mro_dispatches_outcome_methods_to_the_concrete_mixin() -> None:
    outcome_methods = (
        "client_review_outcome",
        "_centralized_reference_outcome",
        "_local_only_reference_outcome",
        "_fedavg_reference_outcome",
        "_krum_reference_outcome",
        "_density_cluster_trimmed_mean_outcome",
        "_update_reconstruction_filter_outcome",
        "_source_update_sanitization_outcome",
        "_recovery_after_source_admission_outcome",
        "_secure_continual_assessment_outcome",
        "_independent_local_reference_outcome",
        "_multiple_model_certified_ensemble_outcome",
        "_source_release_after_full_external_check_outcome",
    )
    for method_name in outcome_methods:
        method = getattr(ProtocolCellExecutor, method_name)
        assert method.__module__ == "fedsira.protocol.baselines.outcomes"


def test_executor_mro_dispatch_edges_target_concrete_overrides() -> None:
    graph = json.loads((REPO_ROOT / "graphify-out" / "graph.json").read_text(encoding="utf-8"))
    nodes = {node["id"]: node for node in graph["nodes"]}
    with (REPO_ROOT / "docs" / ".audit" / "source-verified-method-call-edges.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        edges = {(row["caller_graph_id"], row["callee_graph_id"]) for row in csv.DictReader(stream)}

    def resolve(source_file: str, label: str) -> str:
        matches = tuple(
            node_id
            for node_id, node in nodes.items()
            if node.get("source_file") == source_file and node.get("label") == label
        )
        assert len(matches) == 1
        return matches[0]

    assert (
        resolve("src/fedsira/protocol/baselines/outcomes.py", "._centralized_reference_outcome()"),
        resolve("src/fedsira/experiments/handlers.py", "._final_gate_outcome()"),
    ) in edges
    assert (
        resolve("src/fedsira/protocol/baselines/outcomes.py", ".client_review_outcome()"),
        resolve("src/fedsira/experiments/handlers.py", ".candidate_capability_contract_passes()"),
    ) in edges


def test_typed_loop_dispatch_uses_iterable_element_type() -> None:
    graph = json.loads((REPO_ROOT / "graphify-out" / "graph.json").read_text(encoding="utf-8"))
    nodes = {node["id"]: node for node in graph["nodes"]}
    with (REPO_ROOT / "docs" / ".audit" / "source-verified-framework-dispatch-edges.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        edges = tuple(csv.DictReader(stream))
    caller_id = next(
        node_id
        for node_id, node in nodes.items()
        if node.get("source_file") == "src/fedsira/datasets/common.py"
        and node.get("label") == "role_for_normalized_position()"
    )
    callee_id = next(
        node_id
        for node_id, node in nodes.items()
        if node.get("source_file") == "src/fedsira/datasets/common.py"
        and node.get("label") == ".contains()"
    )
    assert any(
        row["caller_graph_id"] == caller_id
        and row["callee_graph_id"] == callee_id
        and row["dispatch_basis"] == "typed Python instance method dispatch"
        for row in edges
    )


def test_config_loader_dispatches_every_pydantic_validator() -> None:
    config_path = REPO_ROOT / "src" / "fedsira" / "config.py"
    config_tree = ast.parse(config_path.read_text(encoding="utf-8"))
    validator_lines = {
        method.lineno
        for class_node in config_tree.body
        if isinstance(class_node, ast.ClassDef)
        for method in class_node.body
        if isinstance(method, ast.FunctionDef | ast.AsyncFunctionDef)
        and any(
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Name)
            and decorator.func.id in {"model_validator", "field_validator"}
            for decorator in method.decorator_list
        )
    }
    graph = json.loads((REPO_ROOT / "graphify-out" / "graph.json").read_text(encoding="utf-8"))
    config_validator_ids = {
        node["id"]
        for node in graph["nodes"]
        if node.get("source_file") == "src/fedsira/config.py"
        and node.get("source_location") in {f"L{line}" for line in validator_lines}
    }
    with (REPO_ROOT / "docs" / ".audit" / "source-verified-framework-dispatch-edges.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        dispatched_ids = {
            row["callee_graph_id"]
            for row in csv.DictReader(stream)
            if row["dispatch_basis"] == "Pydantic model/field validator metadata"
        }
    assert len(validator_lines) == 16
    assert config_validator_ids <= dispatched_ids
    assert len(dispatched_ids) >= len(config_validator_ids)


def test_framework_dispatch_ledger_targets_real_property_descriptors() -> None:
    graph = json.loads((REPO_ROOT / "graphify-out" / "graph.json").read_text(encoding="utf-8"))
    nodes = {node["id"]: node for node in graph["nodes"]}
    with (REPO_ROOT / "docs" / ".audit" / "source-verified-framework-dispatch-edges.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        property_edges = tuple(
            row
            for row in csv.DictReader(stream)
            if row["dispatch_basis"] == "typed Python property descriptor access"
        )
    assert property_edges
    for edge in property_edges:
        caller = nodes[edge["caller_graph_id"]]
        callee = nodes[edge["callee_graph_id"]]
        assert caller["_callable"]
        assert callee["_callable"]
        source_path = REPO_ROOT / callee["source_file"]
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        method_name = callee["label"].removeprefix(".").removesuffix("()")
        method_line = int(callee["source_location"].removeprefix("L"))
        property_method = next(
            method
            for class_node in ast.walk(tree)
            if isinstance(class_node, ast.ClassDef)
            for method in class_node.body
            if isinstance(method, ast.FunctionDef)
            and method.name == method_name
            and method.lineno == method_line
        )
        assert any(
            isinstance(decorator, ast.Name) and decorator.id == "property"
            for decorator in property_method.decorator_list
        )


def test_framework_dispatch_ledger_tracks_typed_instance_method_calls() -> None:
    graph = json.loads((REPO_ROOT / "graphify-out" / "graph.json").read_text(encoding="utf-8"))
    nodes = {node["id"]: node for node in graph["nodes"]}
    with (REPO_ROOT / "docs" / ".audit" / "source-verified-framework-dispatch-edges.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        method_edges = tuple(
            row
            for row in csv.DictReader(stream)
            if row["dispatch_basis"] == "typed Python instance method dispatch"
        )
    assert method_edges
    for edge in method_edges:
        caller = nodes[edge["caller_graph_id"]]
        callee = nodes[edge["callee_graph_id"]]
        caller_tree = ast.parse((REPO_ROOT / caller["source_file"]).read_text(encoding="utf-8"))
        callee_tree = ast.parse((REPO_ROOT / callee["source_file"]).read_text(encoding="utf-8"))
        caller_line = int(caller["source_location"].removeprefix("L"))
        callee_line = int(callee["source_location"].removeprefix("L"))
        method_name = callee["label"].removeprefix(".").removesuffix("()")
        caller_method = next(
            method
            for method in ast.walk(caller_tree)
            if isinstance(method, ast.FunctionDef | ast.AsyncFunctionDef)
            and method.lineno == caller_line
        )
        target_method = next(
            method
            for class_node in ast.walk(callee_tree)
            if isinstance(class_node, ast.ClassDef)
            for method in class_node.body
            if isinstance(method, ast.FunctionDef | ast.AsyncFunctionDef)
            and method.name == method_name
            and method.lineno == callee_line
        )
        assert caller_method is not target_method
        assert any(
            isinstance(call.func, ast.Attribute) and call.func.attr == method_name
            for call in ast.walk(caller_method)
            if isinstance(call, ast.Call)
        )


def test_framework_dispatch_ledger_tracks_explicit_constructor_calls() -> None:
    graph = json.loads((REPO_ROOT / "graphify-out" / "graph.json").read_text(encoding="utf-8"))
    nodes = {node["id"]: node for node in graph["nodes"]}
    with (REPO_ROOT / "docs" / ".audit" / "source-verified-framework-dispatch-edges.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        constructor_edges = tuple(
            row
            for row in csv.DictReader(stream)
            if row["dispatch_basis"] == "implicit Python constructor dispatch"
        )
    assert constructor_edges
    for edge in constructor_edges:
        caller = nodes[edge["caller_graph_id"]]
        callee = nodes[edge["callee_graph_id"]]
        assert callee["label"].endswith(".__init__()")
        caller_tree = ast.parse((REPO_ROOT / caller["source_file"]).read_text(encoding="utf-8"))
        callee_tree = ast.parse((REPO_ROOT / callee["source_file"]).read_text(encoding="utf-8"))
        caller_line = int(caller["source_location"].removeprefix("L"))
        callee_line = int(callee["source_location"].removeprefix("L"))
        caller_method = next(
            method
            for method in ast.walk(caller_tree)
            if isinstance(method, ast.FunctionDef | ast.AsyncFunctionDef)
            and method.lineno == caller_line
        )
        owner = next(
            class_node
            for class_node in ast.walk(callee_tree)
            if isinstance(class_node, ast.ClassDef)
            and any(
                isinstance(method, ast.FunctionDef | ast.AsyncFunctionDef)
                and method.name == "__init__"
                and method.lineno == callee_line
                for method in class_node.body
            )
        )
        assert any(
            isinstance(call.func, ast.Name) and call.func.id == owner.name
            for call in ast.walk(caller_method)
            if isinstance(call, ast.Call)
        )


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
    expected: frozenset[str] = frozenset(("build_plan", "validate_planned_cell_count_invariant"))
    tree = ast.parse((REPO_ROOT / "src" / "fedsira" / "experiments" / "planning.py").read_text())
    assert not _missing_calls(
        tree, expected
    ), f"plan bypasses plan construction: {_missing_calls(tree, expected)}"


def test_workflow_topology_detects_a_removed_required_edge() -> None:
    tree = ast.parse("def execute():\n    execute_experiment()\n    export_experiment_report()\n")
    workflow = tree.body[0]
    assert isinstance(workflow, ast.FunctionDef)
    expected: frozenset[str] = frozenset(("execute_experiment", "export_experiment_report"))
    assert not _missing_calls(workflow, expected)
    workflow.body.pop()
    assert _missing_calls(workflow, expected) == frozenset(("export_experiment_report",))


def test_verifier_robustness_uses_committed_rows_and_full_protocol_evidence() -> None:
    handlers = REPO_ROOT / "src" / "fedsira" / "experiments" / "handlers.py"
    robust_handler = _method_node(handlers, "_execute_verifier_robustness_cell")
    assert "_advance_protocol" in _called_names_for_node(robust_handler)

    protocol = _method_node(handlers, "_advance_protocol")
    protocol_calls = _called_names_for_node(protocol)
    required_calls: frozenset[str] = frozenset(
        (
            "reproduction_progression",
            "record_verification_evidence",
            "record_production_evidence",
            "final_gate_decision",
        )
    )
    assert required_calls <= protocol_calls, (
        "verifier robustness must consume committed reproduction rows, publish verifier and "
        "certificate evidence, and use synthesis/final-gate wiring: "
        f"{required_calls - protocol_calls}"
    )


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
    assert "state" in argument_names
    expected_positional = len(argument_names) - 1
    assert all(
        len(call.args) == expected_positional for call in observation_calls
    ), "every opening-stage observation call must pass each explicit argument"
