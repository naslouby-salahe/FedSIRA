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
| `run <name>` (19 identities) | Shared execution records/telemetry are non-family stores. Depending on the registered handler: anchor/source/reproduction/baseline checkpoints; model scores; screen matching; calibration; verifier reports; certificates; Krum synthesis; final gate; comparisons; cell-, seed-, aggregate-, state-, trajectory-fraction-, and comparison-evidence Parquet. Collapse completion may publish the resolved-core family. | Prepared role views, scaler and split manifests; compatible checkpoint/score/screen/calibration artifacts; protocol artifacts according to handler; resolved core for post-core identities; exact current comparison artifacts where collapse requires them | Runtime registration is `CELL_HANDLER_REGISTRATIONS`; dispatch is resolved in `ProtocolCellExecutor`. Per-family producer identities and dependency edges are in `artifact-dependency-matrix.md`. The seed Parquet is one row per seed and metric; aggregate rows derive from seed rows. Evidence scarcity now writes raw per-cell state trajectories and source-keyed state fractions before publishing the metric-evidence manifest. An identity-by-family branch matrix and direct project-summary aggregate consumers remain open. |
| `report <experiment>` | Table/figure source-data and report-export artifacts; manuscript tables/figures/summary files under `results/experiments/<name>` | Checksum-verified cell, seed, aggregate, and state-trajectory fraction Parquet; execution identity for terminal/provenance joins; current comparison evidence; validates source/export identities, checksums, required outputs, and product digests | `_execute_bound(name)` exports the named report then independently calls `verify_persisted_experiment_report`; it does not call experiment execution. The Evidence-Arrival State Trajectory reads run-side state fractions with per-cell lineage. Some other descriptive summaries and intervals are still computed during table/figure rendering. |
| `report` (project) | Project table/figure source-data artifact under `outputs/artifacts/table-figure-source-data/source-data`; report-export artifact under `results/project_summary/table-figure-report-export/report-export`; rendered tables, figures, and reproducibility summary under project results | Execution records, current dataset/split/configuration, metric, comparison, final-gate, and claim-state manifest identities; rendered table/figure content digests; export lists all materialized project products | After required evidence and material coverage pass, `export_project_summary` publishes ownerless source data with sorted typed parent references, adds its identity to the reproducibility summary, publishes a relative-path export payload, and verifies the current export and product paths. The source payload currently binds project-rendered content to the full selected manifest set; it does not assign a minimal per-table/per-figure scientific parent set, and report-time descriptive calculations/claim rules remain open under WIRE-009, ART-011, FIG-003/004 and STAT-013. |
| `status` | None | Dataset/artifact readiness and current execution records | Operational state only; no scientific artifact family publication. |

## Producer and consumer anchors

| Artifact families | Producer source | Read/validation source | Command reachability |
|---|---|---|---|
| Raw dataset identity; dataset/schema/exclusion manifest; role/split/sample manifest; scaler; prepared role view | `datasets/preprocess.py`, `datasets/role_split.py`, `datasets/common.py` | Same modules' current-artifact and sidecar validators; `datasets/prepared_validation.py` | `preprocess` is the production writer; `doctor`, `plan`, and `run` readiness paths consume the results. |
| Anchor/source/reproduction/baseline checkpoints | `experiments/checkpoints.py` plus training call sites in `learning/*` and `experiments/handlers.py` | Checkpoint readers in `experiments/checkpoints.py` and protocol handlers | `run` registry handlers; compatible artifacts are reused only after slot/dependency validation. |
| Model score artifact; screen matching/differential; baseline calibration | `evaluation/scores.py`, `evaluation/screen_evidence.py`, `protocol/*`, baseline calibration producers | Corresponding `current_*` readers and score/screen validators | `run` handler descendants only; unit publication/reuse tests cover their artifact contracts. |
| Verifier assignment/report; reproduction certificate; Krum synthesized update/model; final-gate decision | `experiments/protocol_evidence.py` publication helpers called by `experiments/handlers.py`; protocol decisions are implemented in `protocol/verification.py`, `protocol/synthesis.py`, and `protocol/admission.py` | Matching protocol readers and admission validators | `run` protocol descendants only; dynamic protocol dispatch is validated by registry tests. |
| Fixed protocol configuration / resolved core | `experiments/collapse.py`; completion hook in `application.py` | `read_resolved_core()` in collapse/planning/application paths | Collapse `run` identities publish only after the four required collapse decisions; later `run` identities and `plan` consume it. |
| Domain/seed metric artifact | `reporting/publication.py::publish_metric_evidence`, called from completed-run handling in `application.py`; separate ablation-reference producer remains in `experiments/execution.py` | `read_metric_evidence()` and report validation check experiment/execution identity, required filenames, byte counts, and content digests; semantic validation checks cell, seed, aggregate, and state-trajectory schemas | `run` publishes the metric-family artifact after writing Parquet; named and project reports require it and source metric and evidence-trajectory values from it. The direct project aggregate consumer and complete no-recalculation renderer path remain open. |
| Statistical comparison/gate artifact | `evaluation/comparison_evidence.py` | `current_comparison_evidence()` / `comparison_evidence_failures()` | `run` publishes; collapse materialization and `report` verification consume. Currency includes metric-evidence digest, statistical config, and analysis seed. |
| Claim-state artifact | `reporting/publication.py::publish_claim_state_artifact`, called by verified project `report` | `read_claim_state_artifact()` verifies the complete payload and checksum; artifact manifest depends on current statistical and final-gate artifacts plus the exact claim-summary content digest | Project `report` publishes the mechanically derived 19-claim state snapshot before refusing unresolved states; resolved reports record the artifact identity in their reproducibility summary. |
| Table/figure source data; table/figure/report export | `reporting/publication.py`, called from completed-run named reporting and `export_project_summary` | `read_table_figure_source_data()`, `read_table_figure_export()`, `reporting/verification.py`, and report source-content checks | Named products are experiment-owned; project products use ownerless slots. Both paths bind rendered content and export paths to source-data identity, while the project payload records its selected upstream artifact references. Direct numeric row lineage for every project product remains open. |

## Closure gaps

- The `run` row lists conditional producer families but does not yet give a
  generated per-identity/per-branch set of transitive family reads and writes.
- Project-wide reporting still has no published typed numeric source artifact
  and derives descriptive summaries from execution outcomes. Per-identity and
  per-branch family reachability is not yet generated for every run workflow.
- Several real output directories contain historic schema-2 manifests. The
  current reader rejects active/current ones under schema 4; superseded
  historic manifests are excluded from evidence and logged at informational
  severity. This is a valid fail-closed state, not proof of a current run-side
  artifact consumer path.

Accordingly this overlay improves branch and ownership traceability but does
not close WIRE-011/012 or imply experiment readiness.
