# Production call-graph audit — current snapshot

Source: the latest Graphify update (`4,126` nodes / `15,944` edges /
`182` communities; 1,107 production callables). Reachability counts are in
[`callable-inventory.md`](callable-inventory.md).

The reachability analyzer supplements Graphify with source-verified lexical self/cls
and inherited-mixin method-call edges absent from Graphify. The 37 additions are in
[source-verified-method-call-edges.csv](source-verified-method-call-edges.csv);
The same framework ledger contains 19 Pydantic callbacks, 230 typed method/property
edges, and 42 constructor dispatch edges.
all audit edges are injected only into traversal, not into Graphify's source graph.

## CLI to application roots

Typer dispatches each of the seven CLI functions to the same-named
`FedSIRAApplication` method. Graphify omits those instance-method edges, so the
inventory injects the verified pairs from `cli.py` and `application.py` before
traversal. Full command-by-command method traces are in
[`cli-workflows.md`](cli-workflows.md).

| CLI function | Application method | Deepest checked production path |
|---|---|---|
| `doctor` | `doctor` | `diagnose` → environment/config checks, dataset readiness, plan, persisted evidence summaries → render |
| `preprocess` | `preprocess` | `execute_preprocess` → bounded `_execute_bound` → dataset-specific discovery, schema/role preparation, scaler and artifact publication |
| `plan` | `plan` | `execute_plan` → resolved-core state → `build_plan` → condition and 1,989-cell invariant validation → render |
| `smoke` | `smoke` | `execute_smoke` → deterministic backend → 32-check synthetic smoke suite → isolated smoke record |
| `run_experiment` | `run` | `execute_run` → `_execute_bound` → `execute_experiment` → retry/timeout cell phase → `ProtocolCellExecutor.execute_cell` → registered experiment handler → metrics/comparison evidence → report export and optional core materialization |
| `status` | `status` | `execute_status` → persisted execution records → current lifecycle/readiness derivation → render |
| `report` | `report` | `execute_report` → `_execute_bound` → persisted outcomes and project verifiers → `export_project_summary` or `export_experiment_report` → artifact currency/completeness verification |

## Dynamic protocol dispatch

`execute_experiment()` receives `ProtocolCellExecutor` from `application._execute_bound()`
through its `CellExecutor` protocol. Its `execute_cell()` calls
`_execute_cell_protocol()`, which resolves the method name and calls it through
`getattr`, clearing active-cell state in `finally`. Graphify misses both the
protocol implementation edge and the registry-selected handler edges. The
inventory injects these source-verified dynamic edges and confirms all 17
distinct handlers are reachable from `run`.
`ProtocolCellExecutor.__init__` also validates the registry identities and
checks that every handler name resolves to a callable method. The complete
identity-to-handler mapping and one deepest path per registration are recorded
in [`experiment-workflows.md`](experiment-workflows.md).

## Runtime boundaries

- Prepared evidence loads and provenance checks precede the experiment
  handler; missing or invalid evidence returns typed terminal outcomes.
- Cell execution is bounded by the configured timeout and retries only
  permitted infrastructure failures.
- Each handler returns typed admission state and metric observations. The
  executor persists outcomes before evaluation/export consumes them.
- Current data readiness gates historical Data and Domain Evidence Validation
  records in doctor, status, and report workflows.
- This audit exercised doctor, preprocess, plan, smoke, status, and report. It
  did not invoke `fedsira run`.
