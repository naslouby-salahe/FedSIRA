# CLI-to-artifact workflow overlay

This overlay joins the seven actual Typer commands and the 19 registered run
identities to artifact-family reads/writes. It supplements
[`artifact-dependency-matrix.md`](artifact-dependency-matrix.md), which records
identity/invalidation contracts, and the representative paths in
[`cli-workflows.md`](cli-workflows.md) and
[`experiment-workflows.md`](experiment-workflows.md). It is static source
review plus current safe-command evidence; no scientific experiment ran.

## Command roots

| CLI root / branch | Artifact-family writes | Artifact-family reads | Other stores / limitations |
|---|---|---|---|
| `doctor` | None | Dataset manifest, role/split/sample manifest, scaler, prepared role views, fixed protocol configuration, and all discovered complete artifact manifests through readiness checks | Reads experiment execution records and current pointers. Reports invalid current artifacts but does not repair them. |
| `preprocess <dataset>` / `preprocess` (all datasets) | Raw dataset identity, dataset/schema/exclusion manifest, role/split/sample manifest, scaler, prepared role view | Existing current manifests and view sidecars for exact identity/reuse; overwrite rebuilds the selected dataset products | The single-dataset branch is selected by the parsed dataset enum; omitted selection runs both dataset adapters in configured order. Production reruns and prepared-output verifiers cover both real branches. |
| `plan` | None | Fixed protocol configuration/resolved core when available; current execution state and dataset readiness | Reads execution records and dataset manifests through plan-state derivation. Prospective only. |
| `smoke` | None of the scientific `ArtifactFamily` members | None required | Writes/reads the dedicated smoke record and uses synthetic artifact-store fixtures. These smoke artifacts are intentionally not scientific family evidence. |
| `run <name>` (19 identities) | Shared execution records/telemetry are non-family stores. Depending on the registered handler: anchor/source/reproduction/baseline checkpoints; model scores; screen matching; calibration; verifier reports; certificates; Krum synthesis; final gate; comparisons; table/figure source-data and report-export products. Collapse completion may publish the resolved-core family. | Prepared role views, scaler and split manifests; compatible checkpoint/score/screen/calibration artifacts; protocol artifacts according to handler; resolved core for post-core identities; exact current comparison artifacts where collapse requires them | Runtime registration is `CELL_HANDLER_REGISTRATIONS`; dispatch is resolved in `ProtocolCellExecutor`. Per-family producer identities and dependency edges are in `artifact-dependency-matrix.md`. There is not yet a generated identity-by-family branch matrix, and per-experiment descriptive values are still rendered from outcomes before source-data publication. |
| `report <experiment>` | None | That experiment's table/figure source-data and report-export artifacts; validates their checksums, dependencies and published file digests | `_execute_bound(name)` calls `verify_persisted_experiment_report`; focused tests cover missing/stale source/export refusal. It does not render or call experiment execution. |
| `report` (project) | Manuscript tables/figures and reproducibility summary are ordinary result files; no typed project aggregate source-data artifact is published | Execution records, dataset/artifact manifests, current comparisons, collapse/core evidence, and claim summary inputs | Project path currently gathers aggregate outcomes and renders from them. It refuses before writing when evidence/claims are incomplete. A run-side project numeric-summary artifact and consumer-only project report path remain unresolved under WIRE-009, ART-011, FIG-003/004 and STAT-013. |
| `status` | None | Dataset/artifact readiness and current execution records | Operational state only; no scientific artifact family publication. |

## Producer and consumer anchors

| Artifact families | Producer source | Read/validation source | Command reachability |
|---|---|---|---|
| Raw dataset identity; dataset/schema/exclusion manifest; role/split/sample manifest; scaler; prepared role view | `datasets/preprocess.py`, `datasets/role_split.py`, `datasets/common.py` | Same modules' current-artifact and sidecar validators; `datasets/prepared_validation.py` | `preprocess` is the production writer; `doctor`, `plan`, and `run` readiness paths consume the results. |
| Anchor/source/reproduction/baseline checkpoints | `experiments/checkpoints.py` plus training call sites in `learning/*` and `experiments/handlers.py` | Checkpoint readers in `experiments/checkpoints.py` and protocol handlers | `run` registry handlers; compatible artifacts are reused only after slot/dependency validation. |
| Model score artifact; screen matching/differential; baseline calibration | `evaluation/scores.py`, `evaluation/screen_evidence.py`, `protocol/*`, baseline calibration producers | Corresponding `current_*` readers and score/screen validators | `run` handler descendants only; unit publication/reuse tests cover their artifact contracts. |
| Verifier assignment/report; reproduction certificate; Krum synthesized update/model; final-gate decision | `experiments/protocol_evidence.py` publication helpers called by `experiments/handlers.py`; protocol decisions are implemented in `protocol/verification.py`, `protocol/synthesis.py`, and `protocol/admission.py` | Matching protocol readers and admission validators | `run` protocol descendants only; dynamic protocol dispatch is validated by registry tests. |
| Fixed protocol configuration / resolved core | `experiments/collapse.py`; completion hook in `application.py` | `read_resolved_core()` in collapse/planning/application paths | Collapse `run` identities publish only after the four required collapse decisions; later `run` identities and `plan` consume it. |
| Domain/seed metric artifact | Current production family use is the ablation-reference artifact in `experiments/execution.py` | Exact expected-identity comparison before reuse | `run` ablation path. This family does **not** currently own the general Parquet metric evidence written by reporting. |
| Statistical comparison/gate artifact | `evaluation/comparison_evidence.py` | `current_comparison_evidence()` / `comparison_evidence_failures()` | `run` publishes; collapse materialization and `report` verification consume. Currency includes metric-evidence digest, statistical config, and analysis seed. |
| Table/figure source data; table/figure/report export | `reporting/publication.py`, called from `reporting/export.py` | `read_table_figure_source_data()`, `read_table_figure_export()`, and `reporting/verification.py` | Per-experiment products are created by the completed `run` path and verified by named `report`; source payload currently records rendered digests/evidence rather than canonical numeric row lineage. |

## Closure gaps

- The `run` row lists conditional producer families but does not yet give a
  generated per-identity/per-branch set of transitive family reads and writes.
- `report` project has no published typed numeric source artifact and still
  calculates project-wide descriptive summaries from execution outcomes.
- Parquet metric evidence is materialized during completed-experiment report
  export but is not yet owned by a current `DOMAIN_SEED_METRIC_ARTIFACT`
  publication with a typed lineage payload.
- Several real output directories contain historic schema-2 manifests. The
  current reader rejects them under schema 4 unless a newer current pointer
  supersedes them; this is a valid fail-closed state, not proof of a current
  run-side artifact consumer path.

Accordingly this overlay improves branch and ownership traceability but does
not close WIRE-011/012 or imply experiment readiness.
