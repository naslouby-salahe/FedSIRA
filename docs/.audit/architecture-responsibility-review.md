# Architecture responsibility review

Reviewed from a forced code-only Graphify extraction and direct AST responsibility inventory on 2026-09-26. This records module boundaries and actionable findings; it does not treat file length alone as a defect.

| Module | Lines | Current responsibility | Boundary finding |
|---|---:|---|---|
| `experiments/handlers.py` | 3,087 | `ProtocolCellDispatch` contains 45 methods across 2,124 lines, including shared protocol progression, 17 registered cell handlers, baseline outcome adapters, scope resolution, and experiment-specific evidence collection. `ProtocolCellExecutor` contains 15 methods for handler registration, executor setup, and per-cell dispatch. | The public dispatch/registry path is coherent, but the large dispatch class combines shared protocol state transitions with experiment-specific observations and boundary calculations. Candidate split: keep shared progression and registry ownership together; move only cohesive experiment-specific handler groups if imports and dispatch identities remain direct and testable. No line-only split was made.
| `datasets/common.py` | 1,354 | Shared dataset schemas, role windows and sampling caps, row identifiers, DuckDB/Parquet helpers, prepared evidence summaries, dataset adapter, and attack/backdoor/label-error/spurious-feature/heterogeneity/epistemic row transforms. | This is the clearest responsibility mix: dataset preparation and adapter APIs share a module with experiment perturbation transformations. Any split must preserve sample-ID framing, role eligibility, target/source exclusions, and adapter typing; a move without a production-owned home would only create wrappers. Remains an actionable boundary review.
| `evaluation/metrics.py` | 1,187 | Classification metrics, admission/security outcomes, ROC/PR metrics, per-domain evaluation, report metric summaries, protocol-state metrics, screen differentials, and source-backdoor ASR. | Metric formulas have a recognizable owner, but the module combines score-derived metrics with report aggregation and screen-evidence summaries. Typed run-side summary lineage should be designed before separating those owners.
| `evaluation/comparisons.py` | 1,093 | Comparison states, paired test/effect evaluation, Holm correction, comparison definitions and the experiment comparison registry. | The large registry is grouped by experiment family and delegates inferential evaluation to shared functions; no competing production inferential implementation was identified in this scoped review.
| `reporting/tables.py` | 1,534 | Publication table formatting, paired comparison columns, collapse tables, experiment result tables, boundaries, delay/efficiency and generalization tables. | Some descriptive mean, timing and bootstrap interval transformations are computed from outcomes here. They should consume persisted typed summary evidence; splitting rendering before fixing source ownership risks duplicating the same calculation.
| `reporting/figures.py` | 1,571 | Publication figures, metric/effect panels, protocol state trajectories, robustness/boundary plots, efficiency and secondary generalization. | This module includes similar outcome mean/interval helpers and report-time data selection. It shares the typed-summary lineage issue with tables and is not a safe isolated line-count refactor.
| `reporting/export.py` | 1,567 | Named-report verification, project completeness and summary export, experiment report publication, persisted evidence materialization, and table rendering orchestration. | Responsibility is broad but follows the report lifecycle. The project-summary renderer still derives aggregate values at report time; artifact/source lineage must be addressed before moving the aggregate pipeline.

The following cross-module fan-in/out counts are direct `calls` and
`indirect_call` edges in the current Graphify source graph; dynamic registry,
CLI/application, and framework edges are reported separately by the callgraph
audit. Counts support the responsibility review and are not a complexity score.

| Module | Lines | Distinct caller modules | Distinct callee modules |
|---|---:|---:|---:|
| `experiments/handlers.py` | 3,087 | 1 | 34 |
| `datasets/common.py` | 1,354 | 22 | 3 |
| `evaluation/metrics.py` | 1,188 | 9 | 7 |
| `evaluation/comparisons.py` | 1,093 | 5 | 3 |
| `reporting/tables.py` | 1,488 | 2 | 5 |
| `reporting/figures.py` | 1,556 | 1 | 3 |
| `reporting/export.py` | 1,567 | 1 | 16 |

## Follow-up findings

- Do not split modules solely to reduce line counts. Preserve one production owner for each statistic, scientific transform, artifact producer, and dispatch registration.
- Highest-value boundary candidates are dataset preparation versus experiment row perturbations in `datasets/common.py`, and shared protocol progression versus per-experiment handlers in `experiments/handlers.py`.
- Table/figure aggregation currently overlaps; `FIG-003`, `FIG-004`, `ART-011`, and `WIRE-009` remain partial until typed numeric summaries have a run-side producer and report-side verify-only consumer.
- This review is scoped to the largest modules and module-level responsibilities. It does not complete the whole-tree formula-equivalence audit (`ARCH-002`), dataset-adapter equivalence audit (`ARCH-003`), raw-path/literal inventory (`ARCH-004`), or exhaustive logging/default inventories (`ARCH-009`/`ARCH-010`).
