# Workflow branch and terminal-path trace

This supplements [`cli-workflows.md`](cli-workflows.md) with the branch
conditions that change a CLI path or terminal result. Paths refer to the
current production implementation. Experiment handler paths and their deepest
reachable leaves are enumerated separately in
[`experiment-workflows.md`](experiment-workflows.md) and
[`callable-inventory.md`](callable-inventory.md). No experiment was run.

## Command branches

| Root | Branch condition | Production route / terminal result |
|---|---|---|
| `doctor` | Invalid configuration | `diagnose()` returns a blocked report before dataset and artifact inspection; application renders it and exits 1. |
| `doctor` | Valid configuration | `_diagnose_bound()` checks layout, plan, prepared-data readiness, artifact summaries, experiment summaries, project stage, and next action; render; exit reflects deterministic execution readiness. |
| `preprocess` | Dataset supplied | `execute_preprocess()` passes the selected `DatasetId` into bounded dispatch; only that dataset preparer runs. |
| `preprocess` | Dataset omitted | Bounded dispatch iterates both configured `DatasetId` values, invoking N-BaIoT and CICIoT2023 preparation in registry order. |
| `preprocess` | Preparation succeeds / fails | Success publishes and validates prepared-view evidence; validation or preparation exceptions propagate from the bounded command and produce a nonzero CLI result. |
| `plan` | Resolved core absent / present | `execute_plan()` builds the corresponding prerequisite plan and renders all registered cells without dispatching a cell executor. |
| `smoke` | Synthetic invariant suite passes / fails | `execute_smoke()` publishes its separate smoke record and renders the result; CLI exits 0 for `passed`, otherwise nonzero. |
| `run` | Blocking environment mismatch | `execute_run()` raises `SystemExit` before backend configuration, plan execution, or cell dispatch. |
| `run` | Experiment plan is blocked | `execute_experiment()` returns `BLOCKED` without running cells; `execute_run()` renders the result and exits 1. |
| `run` | Current reusable cell record exists and overwrite is false | `execute_experiment()` emits reuse and includes the persisted outcome without invoking the handler for that cell. |
| `run` | No reusable record, or overwrite is true | Cell runs through retry and timeout handling, persists its terminal outcome and metrics, then contributes to current experiment lifecycle. |
| `run` | Completed lifecycle | `_export_completed_experiment()` publishes per-experiment tables, figures, evidence, and manifests; then core materialization is considered; successful no-overwrite execution also prints its digest. |
| `run` | Failed, invalid, or blocked lifecycle | Result is rendered, completed-only export/core work is skipped, and the command exits 1. |
| `status` | Any current readiness/lifecycle state | Read-only renderer distinguishes current outcomes using dataset readiness and execution provenance; no record is changed. |
| `report <name>` | Persisted products missing/stale/invalid | `verify_persisted_experiment_report()` returns typed failures; named report prints no regenerated science and exits 1. |
| `report <name>` | Persisted products current | Verifies identities, dependency/checksums, and required product paths; reports verified paths without invoking renderers. |
| `report` | Any project completeness/evidence/claim gate fails | Completeness checks, result evidence checks, or claim-state gate fail before project result materialization; command exits 1 and writes no result products. |
| `report` | All project gates pass | `export_project_summary()` materializes project tables/figures and current verification checks their products. This path still has the separately tracked numeric-summary artifact/source-lineage gap (`WIRE-009`, `ART-011`, `FIG-003/004`). |

## Readiness and lifecycle terminal branches

`dataset_readiness()` has four exhaustive outcomes: all prepared datasets
present gives `COMPLETED`; all raw datasets present gives `READY`; some raw
dataset present gives `RUNNING`; otherwise it gives `NOT_STARTED`. Current
execution records are filtered by schema/configuration/revision/data-manifest
provenance only when dataset readiness is `COMPLETED`. The current Data and
Domain Evidence Validation record is suppressed when readiness is incomplete.

`derive_experiment_lifecycle()` has five terminal paths: a plan prerequisite
block returns `BLOCKED`; no relevant current records returns `READY`; any
`INVALID` record returns `INVALID`; otherwise any `FAILED` record returns
`FAILED`; all planned cells completed returns `COMPLETED`; remaining partial
records return `RUNNING`. `derive_current_experiment_lifecycle()` first applies
the readiness override for Data and Domain Evidence Validation, then delegates
to the same provenance-filtered lifecycle derivation.

At cell scope, retry is limited to permitted infrastructure interruption;
timeout returns a typed failed outcome with the phase and timeout context.
Successful or exhausted attempts are persisted before terminal/progress logs.
Comparison construction is skipped when no builder is configured; otherwise
the comparison result is published only when the builder returns comparison
families. Per-experiment export is guarded by `COMPLETED` lifecycle.

## Coverage boundary

The table covers public-command selection, readiness/lifecycle outcomes,
record reuse versus execution, and report/run terminal handling. Handler
identity and all 19 experiment descendants are indexed by experiment in
`experiment-workflows.md`. Artifact-family producer/consumer completeness is
not implied by call reachability and remains separately audited under
`WIRE-012`.
