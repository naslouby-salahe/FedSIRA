from __future__ import annotations

import csv
import json
import re
from collections import defaultdict, deque
from pathlib import Path

from fedsira.experiments import definitions

ROOT = Path(__file__).resolve().parents[2]
GRAPH = json.loads((ROOT / "graphify-out" / "graph.json").read_text(encoding="utf-8"))
HANDLERS = (ROOT / "src" / "fedsira" / "experiments" / "handlers.py").read_text(encoding="utf-8")
DOC = ROOT / "docs" / ".audit" / "experiment-workflows.md"
nodes = {
    node["id"]: node
    for node in GRAPH["nodes"]
    if str(node.get("source_file", "")).startswith("src/fedsira/")
    and node.get("_callable")
    and str(node.get("label", "")).endswith("()")
}
by_source_label = {
    (str(node.get("source_file")), str(node.get("label"))): node_id
    for node_id, node in nodes.items()
}
adjacency: dict[str, set[str]] = defaultdict(set)
for link in GRAPH["links"]:
    if (
        link.get("relation") in ("calls", "indirect_call")
        and link.get("source") in nodes
        and link.get("target") in nodes
    ):
        adjacency[link["source"]].add(link["target"])
edge_ledgers = (
    ROOT / "docs" / ".audit" / "source-verified-method-call-edges.csv",
    ROOT / "docs" / ".audit" / "source-verified-framework-dispatch-edges.csv",
)
for edge_ledger in edge_ledgers:
    if not edge_ledger.exists():
        continue
    with edge_ledger.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            adjacency[row["caller_graph_id"]].add(row["callee_graph_id"])
registrations = re.findall(
    r"CellHandlerRegistration\(\s*experiment=(\w+),.*?handler=\"(_execute_[A-Za-z0-9_]+)\"\s*,?\s*\)",
    HANDLERS,
    re.DOTALL,
)
lines = [
    "",
    "## Per-experiment prospective CLI-to-leaf workflows",
    "",
    "Each path starts with the shared `run` prefix in `cli-workflows.md`, then uses",
    "the registered handler and deepest reachable production leaf in the current",
    "Graphify graph. Counts include unique handler descendants and terminal leaves;",
    "dynamic dispatch is resolved through the validated registry. No experiment ran.",
    "",
    "| Experiment | Handler | Unique handler descendants | Terminal leaves | "
    "Deepest handler path |",
    "|---|---|---:|---:|---|",
]
for experiment_token, handler in registrations:
    handler_id = by_source_label.get(("src/fedsira/experiments/handlers.py", f".{handler}()"))
    if handler_id is None:
        raise RuntimeError(f"Graphify did not resolve registered handler {handler}")
    distances = {handler_id: 0}
    parents: dict[str, str] = {}
    pending = deque((handler_id,))
    while pending:
        current = pending.popleft()
        for target in sorted(adjacency.get(current, ())):
            if target not in distances:
                distances[target] = distances[current] + 1
                parents[target] = current
                pending.append(target)
    reached = set(distances)
    leaves = tuple(item for item in reached if not adjacency.get(item, set()).intersection(reached))
    max_depth = max(distances[item] for item in leaves)
    deepest = min(
        (item for item in leaves if distances[item] == max_depth),
        key=lambda item: str(nodes[item].get("label")),
    )
    path = [deepest]
    while path[-1] != handler_id:
        path.append(parents[path[-1]])
    path.reverse()
    path_text = " → ".join(str(nodes[item].get("label", "")).removesuffix("()") for item in path)
    lines.append(
        f"| {getattr(definitions, experiment_token)} | `{handler}` | {len(reached)} | "
        f"{len(leaves)} | `{path_text}` |"
    )

existing = DOC.read_text(encoding="utf-8")
marker = "\n## Per-experiment prospective CLI-to-leaf workflows"
if marker in existing:
    existing = existing.split(marker, maxsplit=1)[0].rstrip()
DOC.write_text(existing + "\n" + "\n".join(lines).strip() + "\n", encoding="utf-8")
