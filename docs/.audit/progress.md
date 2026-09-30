# Pre-experiment audit progress

## Scope and guardrails

Fresh audit started 2026-09-15.  No `fedsira run` command or other
claim-bearing experiment was invoked, and no commit was created.

## Completed discovery

- Read the authoritative audit matrix and roadmap; refreshed Graphify before
  remediation (`graphify update . --force`).
- Confirmed actual CLI commands: `doctor`, `preprocess`, `plan`, `smoke`,
  `run`, `status`, and `report`.
- Ran the safe `doctor`, `plan`, `status`, and project `report` workflows.
- Corrected strict typing in the report-verification terminal-state boundary.
  Pyright, the targeted reporting tests, Ruff, import-linter, deptry, and
  Vulture now pass.
- Full test suite after remediation: 870 passed (warnings only).
- Refreshed Graphify after remediation: 4,378 nodes and 33,904 edges.  The
  increase from the initial graph includes the audit working material itself;
  it is not evidence of a production-code expansion.
- Production N-BaIoT preprocessing completed with manifest
  `3d43e867f1c28d4d31308e2f90cd871d419f5f36500d112109ea7b06277a8a8b`,
  534 prepared views and 320,000 scaler-training rows.  A second unchanged
  run returned the same identity with `dataset_manifest_reused=true`.
- `fedsira smoke` passed every defined invariant (32 checks).
- After the CIC staging-recovery and invariant-materialization remediation,
  the complete suite passed: 871 tests, 280 warnings, in 173.01 seconds.
- Refreshed Graphify after the latest source change: 4,514 nodes, 34,042
  edges, and 172 communities. The final closure analysis remains pending.
- CICIoT2023 preparation is still running in the background at the user's
  direction. It has exceeded the configured 7,200-second bound, revealing
  that the current threaded timeout helper waits during executor shutdown;
  this is logged as a separate remediation finding.
- Graphify's current production-node inventory has 1,066 `()`-labelled
  callables under `src/fedsira/` and the seven expected CLI roots. Full
  framework/dynamic reachability reconciliation is still pending.
- Repaired POSIX enforcement of configured operation timeouts: a main-thread
  operation is interrupted with `SIGALRM` rather than waiting for a timed-out
  executor worker. Runtime timing/recovery regression tests passed (9 tests)
  and the subsequent complete suite passed (872 tests, 280 warnings). Graphify
  was refreshed after the final source correction (4,518 nodes, 34,069 edges,
  172 communities).
- The read-only production plan confirms all 19 registered identities and the
  exact 1,989-cell decomposition (299 pre-core, 1,690 post-core), with the
  planned per-experiment counts recorded by `fedsira plan`. Baseline and
  experiment contract tests also passed (139 tests); per-workflow depth and
  artifact-edge evidence remain pending graph closure.
- Baseline and experiment contract test coverage passed (139 tests), including
  deterministic baseline registries, robust aggregation, source-authority
  comparator semantics, and validation/run-path guards. These are fixture and
  contract tests only; no registered scientific workflow was run.
- The pre-remediation CICIoT2023 process was stopped at the user's direction;
  it had no published prepared view. Fresh `doctor`/`status` confirms
  preprocessing remains incomplete, CICIoT2023 views are missing, and all
  post-core workloads are blocked. The associated monitor is paused.
- Continued matrix closure without restarting CICIoT2023: the exact model
  configuration-to-consumer trace is now recorded and its focused learning
  suite passed (35 tests). CLI-contract, test-duration, and no-roadmap-prose
  rows are also closed. No production source changed during this pass.
- Independently aggregated published N-BaIoT prepared-view sidecars. The real
  data supplies all nine device-proxy domains and target support in all nine;
  the target has 54 role views and 135,000 prepared rows. Anchor sidecars have
  zero target views/rows. Focused N-BaIoT schema/acquisition/validation (25)
  and preprocessing/role/common (40) tests passed. Matrix rows DATA-003,
  DATA-004, and PRE-002 are now closed; DATA-009 is accurately partial until
  CICIoT2023 preparation can publish its corresponding evidence.
- A read-only DuckDB scan of all published N-BaIoT parquet files confirms
  1,569,865 rows, 1,569,865 distinct stable IDs, and no cross-view reuse. The
  same artifact schema has 117 columns: 115 validated numerical predictors
  plus `sample_id` and `label`; it matches the classifier's 115-input layer.
  Focused preprocessing/model checks passed (35 tests). DATA-007, DATA-011,
  DATA-012, and DATA-013 are now closed.
- Report/replay population audit: every existing N-BaIoT Report Test class
  view has at least 500 examples (the configured minimum is 100); two devices
  have no Mirai raw stream, which remains absent rather than imputed and is
  represented by undefined metric semantics. Replay has 80 supported-only
  views and 949,399 rows with no target view. Focused evaluation/preprocessing
  suite passed (63 tests). DATA-014 and PRE-003 are now closed.
- Canonical-scaler audit: the current artifact-store scaler has 115 feature
  moments trained on all 320,000 supported Anchor Train rows, and the SQL
  explicitly excludes target/non-anchor rows. A stale noncanonical JSON scaler
  with a 40,000-row count was found under legacy output material, but no source
  references it; it is documented as contained rather than deleted. Targeted
  artifact/preprocessing/common suite passed (39 tests); PRE-010 is closed.
- Scaling numerics are now closed: source clamps standardization in SQL to
  [-10, 10] before any attack API receives a prepared feature tensor, and a
  read-only scan measured those exact global bounds in every published view.
  Zero-variance scaling is explicitly 1.0. Focused scaling/preprocessing/
  declared-attack tests passed (60).
- Completed source/screen/verification/final/report role-isolation traces.
  Static consumers match their authorized roles, the published stable-ID scan
  proves cross-role disjointness, and focused suites passed for source (46),
  screen (43), verification (49), final gate (26), and report isolation (58).
  PRE-004, PRE-005, PRE-007, PRE-008, and PRE-009 are now closed.
- Raw-schema and vocabulary review: N-BaIoT's real raw header and current
  prepared evidence validate the 115-column schema, while CIC production
  schema evidence remains blocked. Canonical vocabulary handling is complete
  for both implementations, including CIC normalization/collision rejection;
  focused schema/validation suite passed (21). DATA-006 is PARTIAL and
  DATA-008 is closed.
- Evidence-minima boundary audit is closed. Configuration contains the exact
  2,000/2,000, 1,000/1,000, and 500 thresholds; the guards use inclusive
  comparisons and map insufficiency to abstention/dormancy instead of zero
  metrics. Focused contract/state-machine/verification tests passed (33).
- Attack/boundary and statistics configuration are now closed. All condition
  grids are YAML-owned and consumed by definitions/handlers; inference uses
  unrounded alpha/bootstrap/margin/pair values while rounding remains in report
  formatting. Focused grid/boundary suite passed (32) and statistics/export
  suite passed (51).
- Configuration ownership/default audit is closed: production configuration is
  immutable, rejects extras, supplies all typed scientific fields without
  model defaults, and is loaded into the application context before workflow
  use. Config/architecture enforcement suite passed (22); CFG-001 and CFG-002
  are now closed.
- Secondary acquisition/partition review is complete as far as pre-experiment
  evidence permits. The declared `Per-attack shards` mode selects only
  label-less shards and derives the class from the shard path; pseudo-domain
  assignment is a framed hash of manifest, normalized label, stable row ID,
  and the configured `730201` salt. The focused CIC schema/acquisition/
  preparation/validation tests completed. Because the user stopped the
  resource-intensive real preparation and it published no views, DATA-015 is
  explicitly BLOCKED_BY_PRE_EXPERIMENT_STATE rather than silently downscoped
  to N-BaIoT or marked PASS.
- Dataset artifact isolation is closed. Prepared evidence, raw identities,
  role-split manifests, and scalers use distinct dataset roots or slots;
  experiment provenance also carries the prepared-manifest digest. Audit found
  one real checkpoint storage collision: a seed/stage slot did not include the
  dataset. Checkpoint slot identity now incorporates `DatasetId`, and the new
  cross-dataset regression fixture plus focused execution suite passed (22).
  Graphify was refreshed after the source change (4,520 nodes; 34,072 edges).
- Deterministic role generation is partially verified. Both dataset
  discoverers order their inputs; identities and manifests are order-stable;
  N-BaIoT production rerun reused manifest `3d43e867…277a8b`; and focused
  N-BaIoT/CIC fixtures cover deterministic materialization and role assignment.
  A second published CIC result cannot be compared because the user-directed
  stop emitted no prepared artifact, so PRE-015 remains PARTIAL rather than
  conflating fixture determinism with production evidence.
- Role-overlap review is likewise partial. The N-BaIoT published stable-ID
  scan covers 1,569,865 rows with no duplicate ID across views, and 43
  validation/common/preprocessing tests passed, including one-role-per-sample
  fixtures. A real CIC intersection matrix cannot be constructed until a
  bounded corrected preparation publishes its views.
- Stale-input handling is closed through synthetic mutation evidence: exact
  content-addressed slots replace wildcard/latest discovery; altered raw,
  role-split, model/view, configuration, or dataset identities do not reuse
  dependent artifacts, while unchanged publications do. The focused
  storage/role-split/preprocessing/score/execution suite passed (40, with one
  upstream Torch deprecation warning).
- The core authority-transition trace is closed. In the FedSIRA core,
  non-source domains reproduce from the anchor, certification precedes
  Krum/single-row synthesis, and a fresh final gate controls admission. The
  scientific and protocol suite passed (54); source-admission behavior exists
  only in explicitly named comparators/ablations, not the core path.
- Direct source-artifact non-interference is also closed. Core final-gate
  calls disable both source-delta insertion controls and build the committee
  from the non-source reproducer order. The sole source-insertion branches are
  explicit no-exclusion or Byzantine ablations, preserving their diagnostic
  purpose without contaminating source-excluded FedSIRA.
- The read-only status route is closed: it builds the plan, reads resolved-core
  and execution-record state, derives lifecycle, and prints it without any
  publication/execution call. Its actual pre-experiment output and the
  CLI/execution suite (29 passed) agree; 14 third-party Matplotlib/PyParsing
  deprecation warnings were non-fatal.
- The report route is closed independently of historical-output disposition.
  It loads records and artifacts, verifies completeness, and renders only from
  that evidence; it has no execution-engine or protocol-handler edge. The
  actual incomplete-evidence refusal and focused reporting suite (37 passed)
  confirm this. Fourteen Matplotlib/PyParsing deprecation warnings were
  third-party and non-fatal.
- Semantic cell identity is closed. It has only the roadmap coordinates
  (experiment, method, condition, seed, optional repetition); configuration,
  code revision, and dataset manifest are reuse provenance rather than cell
  coordinates. The new separation fixture and execution suite passed (18),
  with Ruff clean. Graphify was refreshed after the test addition (4,521
  nodes; 34,075 edges).
- Artifact identity remediation: generic publication previously recorded the
  scientific configuration digest but did not include it in the reuse key.
  The key now frames that digest with slot, procedure, and labelled parent
  dependencies. The focused artifact/reuse suite passed (51, one upstream
  Torch deprecation warning); Graphify refreshed to 4,523 nodes and 34,084
  edges. ART-002/ART-005 remain partial until every family has a documented
  dependency matrix.
- Cross-experiment reuse has a verified shared-anchor design: checkpoint slots
  are dataset/seed/stage rather than experiment keyed, and executor-level
  anchors are cached by seed. It remains partial until a two-workflow
  publication fixture documents the complete reuse map.
- Overwrite semantics are partially verified in fixtures: command scope is
  explicit and the focused CLI/smoke/execution suite passed (39). A complete
  synthetic shared-anchor reuse-count test remains necessary before ART-009
  can be closed.
- Idempotent reuse and recovery are closed. Compatible records bypass the
  executor, N-BaIoT reused its unchanged production manifest, and the new
  mocked phase fixture proves exactly one infrastructure retry with an
  unchanged scientific cell. Focused reuse/recovery tests passed (31) and
  execution/recovery tests passed (23), with Ruff clean; Graphify refreshed
  to 4,524 nodes and 34,107 edges.
- Manuscript provenance is partially traced: execution records provide cell,
  configuration, code, and dataset-manifest provenance, while source-data and
  report artifacts retain execution/content digests and explicit dependency
  edges. The publication suite passed (37), but a uniform per-number
  split/domain/seed lineage is not persisted yet, so ART-011 remains partial.
- Path discovery is closed. The repository-wide inventory found no
  latest/timestamp selection; sorted enumeration is restricted to raw/prepared
  discovery or validation under explicit roots, while scientific artifacts use
  centralized slots/current pointers. The focused path/history/preprocessing/
  acquisition suite completed; timestamps only support validation memoization.
- Proposal-screen decile isolation is closed. Held-out targets/controls are
  match candidates only; boundaries receive anchor losses from other-fold
  controls only. Proposal/aggregation fixtures passed (35, one upstream Torch
  TF32 deprecation warning).
- Reproduction mathematics is closed for the objective, directed stability
  divergence, and anchor-relative update construction. Independent tensor and
  controlled-wrapper fixtures passed with the protocol/model invariants (27),
  and Ruff was clean. Graphify was refreshed to 4,527 nodes, 34,118 edges,
  and 179 communities.
- Certification and Krum mechanics are closed through MATH-014. The focused
  verification/theory/synthesis/scientific-contract suite passed (45), with
  exact honest-support and insertion-order-independent tie fixtures added;
  Ruff was clean.
- The exact diagnostic probability, typed timing decomposition, and conjunctive
  final gate are closed (MATH-015–017). The 64-test protocol suite passed with
  individual final-gate threshold-failure fixtures added; Ruff was clean and
  Graphify refreshed to 4,528 nodes, 34,120 edges, 182 communities.
- Resource-horizon wiring is closed. Evidence-scarcity trajectories now apply
  configured expiry at every logical cycle, and the primary selector fixture
  proves eight unique non-source reproduction opportunities. The focused
  49-test protocol/trajectory suite passed with Ruff clean; Graphify refreshed
  to 4,532 nodes, 34,127 edges, and 180 communities.
- Model contract audit closed MODEL-001–009. Added deterministic-initialization,
  hand-computed CE, locked-AdamW, and fixed batch-size fixtures; corrected a
  gradient-tracked anchor log conversion. The focused suite passed (36) with
  Ruff clean; remaining warnings are upstream PyTorch pin-memory deprecations.
  Graphify refreshed to 4,535 nodes, 34,135 edges, and 173 communities.

## Findings so far

- The configured external raw-data root contains the authoritative CICIoT2023
  CSV release. Its first production preparation attempt did not publish any
  partial view, but exceeded the configured two-hour preprocessing budget.
  The preparation path is now being audited and optimized before any retry.
- Existing `outputs/` contains obsolete manifest schemas and historical
  experiment-related artifacts.  The report verifier rejects their manifests;
  they must not be treated as current evidence.

## Fresh audit restart, 2026-09-25

- Re-read the complete 4,007-line authoritative roadmap and the current 250-row audit matrix before implementation decisions.
- Verified current worktree and uncommitted state; preserving prior user/worktree edits. Existing audit notes and graph outputs are historical only.
- Fresh `graphify extract . --force --code-only`: 4,208 nodes, 15,065 edges, 167 communities; snapshot under `docs/.audit/graphify-pass1/`.
- Re-ran `fedsira doctor`: configuration/environment valid; N-BaIoT prepared; CICIoT2023 views missing; resolved core absent. No experiments are complete; doctor shows the expected pre-experiment state.
- Confirmed the raw CICIoT2023 per-attack release currently exists at `data/raw/CIC_IOT_Dataset2023/CSV/MERGED_CSV` (374 CSVs, 17 GiB), so the prior `BLOCKED` status cannot be carried forward without fresh preprocessing verification.
- Launched the production CICIoT2023 preprocessing CLI in the background; see `background-jobs.md`. No scientific experiments have been run.

## Fresh audit continuation, 2026-09-25

- Corrected CICIoT2023 label normalization to Unicode NFC/alphanumeric rules and documented the observed `Benign_Final` alias; the configured target and pseudo-domain semantics remain unchanged.
- Corrected current lifecycle handling for the Data and Domain Evidence Validation record across doctor, status, and report. Historical completion is no longer shown as current when prepared data are missing; project reports suppress stale validation outcomes and counts.
- Added runtime validation that each of the 19 experiment registrations resolves to an existing protocol handler method. Removed unreferenced `pool_domain_rows`, `parquet_contains_rows`, `clear_prepared_rows_cache`, and the unused `SecondaryRoleAssignment` model after whole-tree reference checks.
- Fresh doctor, plan, status, and synthetic-only smoke checks succeeded. The plan remains 19 experiments / 1,989 cells (299 pre-core, 1,690 post-core); smoke passed 32 checks. The scientific `run` command has not been invoked.
- Full test suite passed: 892 tests, 279 upstream warnings. Ruff and strict Pyright passed; Deptry found no dependency issues; Import Linter kept all three contracts. Vulture findings were reviewed against declared model/enum fields and dynamic handler registrations.
- Report lifecycle regression checks passed. Project report execution and completed CICIoT2023 preprocessing/reuse verification await the active production preprocessing job.
- Separated reporting logs from preprocessing logs after finding both components targeted the same file. The new path assertion and report topology tests pass; the final whole-suite run will include this change.
- Tightened current Data and Domain Validation reuse: a persisted result is current only when its configuration digest, repository revision, and prepared dataset manifest all match. Prerequisite lifecycle checks and report terminal counts use the same filter. Focused execution/reporting tests passed (50); Ruff and strict Pyright pass. A final whole-suite run is underway.
- The first actual CICIoT2023 preprocessing attempt hit the configured 7,200-second limit inside per-row Python pseudo-domain hashing without publishing views. Replaced per-row Python hashing for stable IDs, pseudo-domains, and role sampling with native DuckDB SHA-256 expressions over the same framed inputs, and normalized distinct shard labels once. Unit parity tests passed; an optimized production retry is running, with about 2 GiB staged after six minutes.
- Full-suite audit found that the Python reference hashing helpers had become production symbols used only by tests after the DuckDB SQL optimization. Removed the obsolete production copies and retained independent parity calculations in tests. CIC-specific preprocessing/schema/architecture checks passed (31). The full suite then passed (892 tests, 279 third-party warnings) with no skips; the architecture suite also enforced Ruff formatting and strict Pyright across source and tests.
- Artifact invalidation remediation: artifact schema version advanced to 4; identity now includes dependency kind as well as label/digest and no longer hashes the entire YAML configuration globally. Dataset prep, training, screen, protocol, baseline calibration, ablation reference, and statistical artifact publishers declare scoped configuration digests. Rendered table/figure content is now a source-data dependency, and reads of ablation references verify the expected current identity. Older schema manifests are rejected as current evidence. Execution lifecycle/status now filters all experiment records by current configuration/code/dataset provenance. Targeted artifact/report/workflow checks passed (80 tests), Ruff and strict Pyright passed; the final full suite is running.

- Follow-up at 19:06 UTC: pinned Ruff remains clean, and Windows-side syntax compilation passed for 234 source/test modules plus the prepared-output audit helper. A bounded trivial WSL process still does not start although Ubuntu reports Running; no WSL restart was attempted because unrelated FedORBIT work remains active. The new indexless CIC pipeline is not runtime-tested, and production preprocessing, final Graphify, fresh N-BaIoT verification, and final matrix closure remain open.

- WSL resumed. Corrected the new staging regression test to use public materialization; focused CIC suite passed (22). Strict Pyright, Ruff, Deptry, Import Linter, and Vulture passed. Fresh Graphify pass 3: 4,245 nodes / 15,465 edges / 190 communities; inventory and 19 prospective handler paths regenerated.
- The current full suite passed: 898 passed, 279 warnings, 183.92s, no skipped count reported. Corrected indexless CIC production preprocessing is now active (worker PID 58655; see `background-jobs.md`).

## WSL continuation, 2026-09-25

- The indexless CIC production retry stopped with DuckDB WAL exhaustion and published no prepared views. The staging database was deleted after confirming no process remained. CIC materialization now checkpoints its persistent DuckDB file every 16 completed shards plus the final shard, bounding accumulated WAL without changing row identity or scientific transforms.
- The combined CIC preprocessing/schema, reporting, comparison-evidence, and execution tests passed (99); the separate report-lineage selection passed (2). Metric evidence includes dataset, semantic cell, current configuration/revision/data-manifest provenance, and exact scoring artifact IDs; aggregates point to source observations/cells and comparison rows point to paired seeds and source cells.
- Relaunched real CICIoT2023 preprocessing with periodic checkpoints (PID 107933). Its first checkpoint showed a 929 MiB DuckDB database and an 820 KiB WAL; production result remains pending.
- The reporting topology audit found that report and resolved-core paths recomputed inferential comparisons from execution records. They now load only a current persisted comparison artifact; execution alone owns the comparison builder. Comparison rows carry the statistical artifact identity, and the comparison evidence digest includes provenance and scoring-artifact IDs. Schema/procedure versions were advanced. The focused workflow, comparison, report, and execution suite passes (67), with strict Pyright and Ruff/format clean. The report and per-number lineage findings are closed pending final whole-suite/Graphify revalidation.

## Audit continuation, 2026-09-26

- Re-read the attached audit directive and continued without invoking any experiment or creating a commit.
- Repaired §30.12 verifier robustness to consume a trained/committed model-replacement row, evaluate per-row verifier panels, record verification/certificate/production evidence, and use the ordinary synthesis/final-gate path. Byzantine-bound dispatch now preserves the planned experiment/method cell; Resolved Core uses exact deterministic verifier panels, while Direct Krum consumes the fixed model-replacement reproducer without a verifier. Added bound-route, scope, and attack-feasibility fixtures. Focused verifier/reproduction/architecture checks passed (37), followed by a 6-test dispatch/feasibility set; Ruff and Pyright passed.
- Fixed execution/report root inconsistency: relative execution workspace and manuscript-results paths now resolve against `REPOSITORY_ROOT`; run, status, report, comparison, doctor, preprocessing-cache, and core-materialization paths share `execution_workspace_root()`. A changed-CWD fixture and focused path/execution/report checks passed (92 total); Ruff and Pyright passed.
- Fixed a cross-experiment plot issue: the Primary Security–Utility Tradeoff filters to the registered primary confirmatory family and labels points by scenario/method/comparator. Two-scenario fixture passes; external experiment evidence is excluded.
- Fresh Graphify after the verifier changes reported 5,644 nodes, 17,331 edges, 383 communities; the refreshed callable inventory found 1,113 production callables. A subsequent path/plot edit means another final Graphify pass is required. The matrix still has 41 PARTIAL rows; reporting summary/claim derivation and exhaustive per-callable/branch evidence remain in progress.
- FIG-006 received an additional completeness pass: fixtures verify the required evidence-arrival plot retains an `Expired` trajectory and the raw cell-metric table preserves a failed terminal state plus undefined-metric `NA`. All 30 reporting export/figure tests passed; isolated Pyright and Ruff checks are clean. Broader renderer-by-renderer coverage remains open, so FIG-006 stays PARTIAL.
- Re-executed all actual safe short CLI commands after the path changes: `doctor`, `plan`, `smoke`, and `status` exited 0; smoke passed 32 invariants. Project `report` exited 1 without launching science, as required, because there are no completed scientific experiments or current statistical comparison artifacts; artifact validation also rejected historical schema-2 manifests after the deliberate schema-4 migration. The new status shows the expected 19-experiment plan (299 pre-core, 1,690 post-core, 1,989 total), one completed protocol-invariant prerequisite, and twelve post-core blocks. No `run` command was called.
- The first post-fixture full suite exposed six failures: five artifact-path/cache tests because path resolution ignored a bound temporary repository context, and one architecture test because two public helpers were used only by self-tests. Resolved paths against `ApplicationContext.repository_root`, updated isolated-repository fixtures, and removed the redundant model-replacement wrapper and silent duplicate-report deduplicator (production already rejects repeated panel domains). Added anchor-train-only scaler-population checks for both dataset adapters. The focused artifact, preprocessing, dataset, attack, protocol, and architecture suite passed (91); Ruff passed and Pyright reported 0 errors/warnings. A corrected full-suite rerun is active.
- The corrected full-suite run found a second class of root-isolation defect: comparison, model-score, and verifier-report publishers still used the module-global repository root, while tests monkeypatched that global and had accumulated project artifacts. Those publishers now resolve storage through the active application context, and their tests bind a fresh temporary repository context. All 21 focused publication tests pass. Ruff and strict Pyright are clean; Deptry and all three Import Linter contracts pass. Graphify refreshed to 5,660 nodes / 17,427 edges / 387 communities, and the regenerated callable inventory reports 1,110 production callables (926 functions, 184 methods), 903 in the CLI union, and 370 union leaves. The corrected full suite is running; its final outcome is pending.
- Corrected full-suite result: 919 passed in 200.19 seconds; no skipped tests were reported, with 279 upstream warnings. The complete math, data, protocol-state, and metric/statistic fixture crosswalk is now recorded, so TEST-001–004 moved from PARTIAL to PASS. The matrix validates at 213 PASS / 37 PARTIAL. Report-summary numeric lineage, evidence-driven claim derivation, broad path centralization, and the remaining Graphify/architecture audits remain active.
- Project reporting now rejects missing evidence-driven claim states before creating result tables or figures. A deterministic regression forces otherwise-complete inputs with unavailable claim decisions and verifies the renderer is not reached and the output directory remains empty. Reporting tests pass (31), Ruff and Pyright pass, and Graphify refresh completed at 5,662 nodes / 17,445 edges / 382 communities. This closes partial-output-on-failed-report behavior; the numeric summary artifact and claim-decision derivation remain open.
- Path ownership was extended beyond execution/manuscript roots: operational repository joins for dataset preparation/validation, score and screen evidence, checkpoints, execution, telemetry, planning, protocol tables, publication artifacts, application state, and report paths now resolve through `current_repository_root()` from the bound `ApplicationContext`. Temporary-root fixtures now bind context instead of patching process globals. The affected dataset/artifact/execution/report suite passed (244); doctor also succeeds against the real prepared data. Ruff and Pyright pass, and Graphify refreshed to 5,661 nodes / 17,499 edges / 380 communities. The separate raw-literal/duplicate-directory inventory remains open.
- After the path migration, safe short CLI checks were rerun: `doctor`, `plan`, `smoke`, and `status` exited 0; smoke passed 32 invariants and the plan remains 19 experiments / 1,989 cells (299 pre-core, 1,690 post-core). `report` exited 1 before rendering because current experiment/comparison evidence and evidence-driven claim decisions do not exist; it did not invoke experiment execution. A fresh production `fedsira preprocess` verification was launched at 18:00 UTC and remains active, currently rebuilding N-BaIoT; no experiment or commit was made.
- Current matrix validation confirms 250 unique requirement rows: 216 PASS and 34 PARTIAL. The remaining set includes evidence-lineage/claim derivation, exhaustive callable and artifact reachability, architecture inventories, renderer/test crosswalks, and final acceptance. The full test suite must be rerun after the latest architecture guard and package-facade removal; final forced Graphify extraction also remains pending.
- A fresh full suite initially passed 920 tests but exposed two architecture findings: `CellPhaseState` and `SeedBundle` were production declarations used only in their own tests. Graphify and source references confirmed no production consumer or roadmap role; both unused declarations and their test-only fixtures were removed. Focused architecture/domain verification passed 124 tests; Ruff, strict Pyright, Deptry, Import Linter, and Vulture (80% confidence) passed. The subsequent full suite passed 916 tests, 279 upstream warnings, no skips, in 164.47 seconds.
- Forced post-remediation Graphify extraction and cluster-only completed at 5,871 nodes, 17,714 edges, 377 communities, and 1,109 production callables (927 functions, 182 methods). The refreshed inventory finds 904 prospective CLI-union callables and 205 outside that union. All 19 registered workflow deepest handler paths were regenerated; WIRE-007 moved to PASS. `docs/.audit/graphify-final-acceptance/` contains the post-remediation graph, while earlier immutable snapshots were moved to an external C: archive with links preserving their repository paths after the Ubuntu filesystem filled.
- Completed the static root/path inventory in `path-ownership-review.md` and closed ARCH-004: all operational roots use the active application context and typed path owners; the five remaining literal joins are filenames beneath those owners. Extended the empirical-deviation ledger with the observed exclusion reasons and confirmed N-BaIoT dimensions; SCI-012 is now PASS. The adapter comparison in `dataset-adapter-equivalence.md` closed ARCH-003 by confirming shared role-window, cap, scaling, and feature-transform owners alongside contract-specific identities/labels. Current matrix validation is 220 PASS / 30 PARTIAL.
- A post-migration preprocess verification at 18:00 UTC reused N-BaIoT successfully, then exited with a CICIoT2023 shard-ingest error while the Ubuntu filesystem was completely full. The same full-disk condition caused a concurrent test attempt to fail with 21 fixture setup errors; those errors were environmental and cleared by preserving the Graphify snapshots on C:. Neither failure is treated as successful verification; the clean reruns after disk recovery are recorded separately below.
- After disk recovery, a clean full-suite rerun passed 916 tests, 279 upstream warnings, and no skips in 164.47 seconds. The final safe short-command check also completed: doctor and status exited 0, plan exited 0 with 1,989 cells, smoke exited 0 with all 32 invariants, and report exited 1 before rendering because historical schema-2 artifacts are invalid under schema 4 and current comparison/claim evidence is absent. The recorded next valid scientific workflow is Baseline Implementation Validation; it was not run. The post-path production preprocessing rerun is still active.
- The dedicated E2E scope run passed 8 tests in 8.10 seconds with no scientific run. `e2e-scope-review.md` records each case's timing and the missing integrated preprocessing/status/reuse path; TEST-010 remains partial. The artifact/read-only, topology-mutation, and type-rule residuals are crosswalked in `test-audit.md`.
- Post-migration production preprocessing completed successfully with both dataset manifests reused. Independent verification passed all 534 N-BaIoT and 1,674 CICIoT2023 prepared views: 1,569,865 and 7,720,601 rows respectively, zero duplicate/null sample IDs, CIC role/exclusion manifest checks passed. Full JSON: `prepared-output-verification-final-20260926.json`.
- The new synthetic AST unwiring mutation is now type-clean and its topology/static-typing tests pass (13); `TEST-006` is PASS. Latest forced Graphify after that test edit reports 4,072 nodes / 15,816 edges / 167 communities; the source/AST inventory reconciles at 1,109 production callables (927 functions, 182 methods; 355 classes), with 904 CLI-union callables and 205 outside the union. Snapshot refreshed in `graphify-final-acceptance/`.
- Matrix validator initially reported 221 PASS / 29 PARTIAL; after the artifact recovery/overwrite/read-only fixtures, it reports 222 PASS / 28 PARTIAL across 250 requirements. The latest full suite passed 919 tests, with 279 upstream warnings and no skips, in 170.34 seconds. Fresh Graphify after the final test edits reports 4,075 nodes / 15,837 edges / 183 communities and the unchanged 1,109 source production callables. Ruff, formatting, Pyright, Deptry, Import Linter, and Vulture confidence-80 checks pass. The matrix remains NOT READY because unresolved partials include report summary/claim lineage, exhaustive callable/artifact branch reachability, and architecture audit work. No experiment was run and no commit was created.
- Type-rule escape review then found quoted forward-reference and qualified-primitive annotation bypasses, plus enum `.value` access through module/base aliases. The architecture scanners now detect them; all 124 architecture tests pass with Ruff and strict Pyright clean. TEST-007 moved to PASS, yielding 223 PASS / 27 PARTIAL.
- The cross-file report mean review found independent completed-outcome filtering/mean calculations in tables and figures plus another defined-value mean in evaluation metrics. These now share `experiments.observations.outcome_metric_mean` and `evaluation.statistics.mean_of_defined_values`; focused observations/metric/report tests pass (67). ARCH-002 remains PARTIAL because the repository-wide formula equivalence review is incomplete. Fresh forced Graphify now reports 4,086 nodes / 15,884 edges / 186 communities; the final full suite is running after this production refactor.
- Follow-up consolidated the efficiency figure's direct NumPy median/linear-quantile calls with the table's canonical `quantile_type7` path. A fixture checks the Section 30.19 rule at both levels: five repetition values per seed, then median/IQR across three seed medians. The focused observations/metrics/report suite passes (68); Ruff and Pyright pass. Fresh forced Graphify after this final source/test edit reports 4,087 nodes / 15,890 edges / 182 communities and 1,108 source callables (926 functions, 182 methods), with 903 CLI-union callables and 369 terminal leaves. Matrix remains 223 PASS / 27 PARTIAL; the refreshed full suite is running.
- Corrected two remaining reporting/statistical identity defects: comparison artifact currency now includes the configured analysis seed used by bootstrap intervals (10 focused tests pass), and descriptive Primary Results cells no longer substitute paired inferential effects when their raw descriptive metric is undefined (33 reporting tests pass). Full static checks pass. Graphify inventory refreshed at 4,092 nodes / 15,916 edges / 188 communities; AST inventory is 1,107 callables (925 functions, 182 methods), 902 CLI-union callables, and 369 terminal leaves. A full-suite rerun and final audit evidence refresh are in progress; summary-artifact lineage and §35 claim-state derivation remain blockers.
- Full post-change verification passed: 930 tests, 279 upstream warnings, no skips, 184.62 seconds. Ruff check/format, Pyright, Deptry, Import Linter (3 kept), and Vulture confidence-80 pass. Safe doctor/plan/smoke/status all exited 0; smoke passed 32 invariants. Project report exited 1 before rendering because current comparisons are absent, schema-2 manifests are obsolete under schema 4, and evidence-driven claims remain unresolved. No `fedsira run` or scientific experiment was invoked.
- Read-only branch reviews clarified that GRAPH/WORKFLOW and artifact-family reachability gaps are branch-level, not missing all route evidence. Added `artifact-workflow-io.md` to map seven CLI roots, named/project report, conditional run families and producer/reader anchors; WIRE-011/012 stay partial for per-branch leaf and handler-family expansion plus project numeric summary production. Added `architecture-defaults-logging-audit.md` with concrete unclassified defaults and failure-event coverage gaps; ARCH-009/010 remain partial. A safe `preprocess --overwrite` manifest-refresh rerun is active; it completed N-BaIoT cache validation and has started CICIoT2023. The matrix still validates at 223 PASS / 27 PARTIAL.
- Added bounded failure class, phase, and message fields to experiment cell terminal logs and timeout events. Focused execution tests pass (22), as do Ruff and strict Pyright for the touched files. Refreshed Graphify and the full callable/handler inventory: 4,102 nodes, 15,953 edges, 179 communities; 1,107 production callables (925 functions, 182 methods), with 17/17 registered handlers accounted for after verified dynamic-edge injection. ARCH-010 remains partial pending full event-branch, preprocessing/report/doctor failure, and resource-phase coverage. CICIoT2023 overwrite preprocessing remains CPU-active; this source change has not yet been included in a full-suite run.
- Closed WIRE-011 after adding `workflow-terminal-branches.md` for command selection, dataset readiness, record reuse, lifecycle, report, and terminal branches, cross-linked to complete command and per-experiment deepest-path inventories. The finalizer validates 224 PASS / 26 PARTIAL across 250 rows. Full static checks pass, and the post-change full suite passed 931 tests with 279 upstream warnings and no skips (294.99 seconds). CICIoT2023 overwrite preprocessing is still active; independent verification remains pending.
- Extended the call-reachability audit with a source-verified AST ledger for lexical `self`/`cls` calls that Graphify missed. The traversal now reaches 908 of 1,107 production callables, with 199 remaining outside the CLI union (down from 205); 21 injected edges are listed in `source-verified-method-call-edges.csv`. Updated the inventory and GRAPH-003/007/009/012 counts; callable-by-callable outside-set classification remains open.
- Refreshed Graphify after the audit changes and regenerated inventories from the latest snapshot: 4,107 nodes / 15,977 edges / 188 communities, with 908 CLI-reachable and 199 outside-union callables. Full suite and all static checks remain green; matrix finalizer remains at 224 PASS / 26 PARTIAL. CICIoT2023 overwrite preprocessing is still active and remains independent of this documentation-side reachability work.
- Completed the oversized-module responsibility review with source ownership, explicit candidate seams, line counts, and current Graphify cross-module fan-in/out for the seven largest modules. ARCH-001 now passes without introducing a line-count-only split or a wrapper layer; the remaining current matrix result is 225 PASS / 25 PARTIAL.
- Experiment terminal and metric log field copies now preserve the applicable dataset identity as well as bounded failure details. Focused execution tests (22), Ruff, and strict Pyright pass; Graphify was refreshed to 4,107 nodes / 15,978 edges / 177 communities. A post-change full-suite run remains pending; the earlier 931-test run predates this small logging fix.
- A post-change full-suite rerun passed 930 tests but caught one repository Ruff failure in the new audit script's import order. Fixed the import order; repository-wide Ruff and source/test format checks now pass. Rerun the full suite after active preprocessing stops changing prepared outputs.

## Final data and safe-check continuation, 2026-09-26

- CICIoT2023 overwrite preparation and independent verification completed successfully. A subsequent ordinary `fedsira preprocess` run also exited 0 and reported `dataset_manifest_reused=true` for both N-BaIoT and CICIoT2023.
- The post-overwrite byte/mtime comparator streamed every one of the 2,208 prepared JSON/Parquet pairs against the pre-run baseline. All 2,208 pairs were byte-identical and retained their original nanosecond mtimes; evidence: `prepared-output-reuse-comparison-overwrite-20260926.json`.
- The final full test suite passed 931 tests with 279 upstream warnings and no skips (326.18 seconds). Root Ruff and source/test formatting checks pass. Doctor, plan, smoke, and status pass; smoke reports 32 checks. Project-wide report remains fail-closed on missing comparison evidence, obsolete schema-2 manifests, an unpublished prepared-role parent, and stale statistical configuration. No `fedsira run` or scientific experiment was invoked.
- The matrix validator confirms 250 rows: 225 PASS / 25 PARTIAL. The remaining rows concern formula/default/logging review, summary and figure lineage, claim-state derivation, graph/callable classification, integrated E2E coverage, and final acceptance; the gate remains NOT READY.

## Scientific-subsystem reach correction, 2026-09-26

- Fixed a prospective path-analysis error: registered handler methods were being removed from a workflow whenever they appeared as direct shared-helper calls, rather than only at the dynamic dispatcher's fan-out. Regenerated the 19 × 15 scientific-subsystem matrix. Byzantine Bound Violation now reaches the expected attack, learning, metric, reproduction, synthesis, and verification categories.
- The remaining seven zero cells belong only to the deliberately narrow Data and Domain Evidence Validation and Protocol Invariant Validation workflows. Added `experiment-scientific-subsystem-zero-review.csv` and an executable verifier; it confirms all seven justifications match the generated table and checks required Byzantine-bound categories.
- GRAPH-006 is now PASS. The finalizer validates 226 PASS / 24 PARTIAL across 250 rows. The current Graphify snapshot has 4,110 nodes / 15,981 edges / 195 communities; 1,107 production callables remain inventoried, with 908 in the CLI union and 199 still requiring per-callable disposition. No experiment ran.
- Focused topology validation passed (11 tests), repository-wide Ruff passed, source/test formatting passed, and Pyright reported 0 errors/warnings. `verify_subsystem_zero_review.audit` independently confirmed 19 workflows × 15 subsystems, seven justified narrow-workflow zeros, and all required Byzantine-bound categories. Matrix finalizer remains 226 PASS / 24 PARTIAL.
- Added an executable producer/source checklist for all project tables, mandatory figures, and the experiment-owned cell-metrics table. It maps every product to a renderer, records current consumer inputs and required artifact families, and validates required metric/table/figure specs for all 19 experiment registrations. FIG-007 is now PASS. Current Graphify: 4,112 nodes / 15,983 edges / 186 communities. Matrix finalizer: 227 PASS / 23 PARTIAL.


## Inherited outcome dispatch correction, 2026-09-26

- Graphify omitted concrete baseline outcome methods inherited by ProtocolCellExecutor because statically observed calls resolve to interface stubs. Added an audit-only source resolver that validates ProtocolBaselineOutcomes precedes ProtocolCellDispatch in the executor bases and maps concrete self-dispatch calls to their implemented methods.
- Added a topology regression that checks 13 representative runtime-resolved outcome methods actually come from fedsira.protocol.baselines.outcomes. The focused topology file passes (12 tests); Pyright passes with zero errors and warnings.
- The refreshed analyzer now validates 37 source-verified lexical/inherited-mixin edges and moves 80 callables into the prospective CLI union: 988/1,107 reachable, 119 outside. No callable was labelled dead.
- Fresh Graphify after the audit analyzer/test change reports 4,118 nodes, 15,932 edges, and 186 communities. The matrix remains 227 PASS / 23 PARTIAL pending reconciliation of the remaining callable dispositions and other substantive blockers.


## Pydantic validator dispatch audit, 2026-09-26

- The current Graphify query and direct source inspection showed that Pydantic model/field validator callbacks were absent from the CLI call union. The analyzer now resolves the 15 decorated validator methods through load_scientific_config and emits a separate framework-dispatch ledger. Experiment path regeneration consumes both audit ledgers.
- Added a topology regression that compares every Pydantic validator method in config.py against the generated dispatch ledger. The topology suite now passes 13 tests; strict Pyright, Ruff, and source/test formatting pass.
- Updated the current reachability partition to 1,003/1,107 CLI-union callables and 104 outside-union callables. This includes the earlier 16 additional inherited-mixin edges that recovered 80 baseline callables. All 104 remaining callables still require complete source disposition.
- The current finalizer remains 227 PASS / 23 PARTIAL. Fresh Graphify reports 4,120 nodes / 15,933 edges / 182 communities; no experiments or commits were made.


## Typed property dispatch audit, 2026-09-26

- Added source-verified property descriptor edges where the caller receiver type is established by an annotation, constructor assignment, or enclosing class. The framework ledger now contains 15 Pydantic validator callbacks and 20 typed property access edges.
- Updated experiment path traversal to consume these dispatch edges. The prospective CLI union is 1,008/1,107; 99 remain outside and require full disposition.
- Added a topology test checking each property edge resolves to an actual Python property descriptor. Ruff formatting and the focused topology suite pass (14 tests); the full matrix remains 227 PASS / 23 PARTIAL.


## Constructor dispatch audit, 2026-09-26

- Added source-verified edges for explicit class construction to each class explicit __init__ method. Graphify omits this Python dispatch; the current ledger contains 42 candidate edges, with callers and targets checked against AST source.
- The reachability analyzer now accounts for constructor dispatch in addition to mixin methods, Pydantic validators, and typed property descriptors. The CLI union rises to 1,018/1,107; 89 callable dispositions remain.
- Added regression coverage that validates each ledger constructor edge against an actual class constructor and call expression. Full static and focused checks plus a fresh Graphify rerun are next; no scientific experiment has run.


## Fresh graph reconciliation after dynamic edge expansion, 2026-09-26

- After adding constructor dispatch resolution and its regression test, refreshed Graphify: 4,120 nodes, 15,933 edges, 182 communities. The analyzer reconciles 1,107 production callables as 1,018 CLI-union reachable and 89 outside. Current missing Graphify edge ledgers contain 37 lexical/inherited-mixin method edges, 15 Pydantic callback edges, 20 typed property edges, and 42 implicit constructor edges.
- The focused topology suite passed 15 tests. Ruff, format, and strict Pyright pass; the full-suite rerun is pending. Matrix finalizer remains 227 PASS / 23 PARTIAL.


## Typed instance-method dispatch audit, 2026-09-26

- Extended the AST resolver to trace member calls when receiver types are established by method annotations, local constructors, instance attributes assigned in ProtocolCellExecutor, or its explicit ProtocolCellDispatch inheritance. The framework ledger now has 37 typed method/property entries, alongside 15 Pydantic and 42 implicit constructor entries.
- The graph traversal now reaches 1,024 of 1,107 production callables; 83 remain outside and still need full disposition. Added a regression checking each typed method edge against the callsite and method definition.
- This expansion is audit-only and does not alter experiment behavior. Matrix finalizer remains 227 PASS / 23 PARTIAL; full-suite run session 65398 began before the latest topology test and must be repeated after this batch.


## Top-level typed receiver dispatch and latest reachability, 2026-09-26

- Expanded method/property call resolution to top-level functions with explicit parameter/local types, including iterable element annotations. This makes typed uses of artifact stores, prepared dataset adapters, and outcome objects visible in the prospective CLI graph.
- Reachability is now 1,062/1,107 with 45 outside-union callables. The source dispatch ledgers show 15 Pydantic callbacks, 194 typed method/property edges, and 42 constructor edges. The 16-test topology suite, Ruff, format, and Pyright pass.
- Latest Graphify after the new regression test: 4,123 nodes / 15,932 edges / 199 communities. The earlier full-suite session passed 935 tests/279 warnings/no skips before the newest test was added; final full-suite rerun remains pending.


## Reachability disposition and final audit refresh, 2026-09-26

- Corrected the matrix reachability evidence after the source-verified resolver reached 1,079/1,107 production callables (28 outside the CLI union). The Pydantic topology assertion now verifies that all 15 config validators are present while allowing additional model-construction callbacks.
- Refreshed Graphify after the topology-test update: 4,124 nodes, 15,929 edges, 184 communities. The matrix finalizer still validates all 250 rows and reports 227 PASS / 23 PARTIAL.
- Focused topology suite passes (16 tests); Ruff and format checks pass for the edited test. Final full suite is running in session 98635. No experiment or commit was made.


## Canonical target-F1 and benign-FAR calculations, 2026-09-26

- Replaced duplicated benign-FAR delta arithmetic across evaluation, screen evidence, protocol admission, baseline outcomes, and experiment handlers with benign_false_alarm_rate_increase; production metric construction now uses target_f1 for target selection. This centralizes undefined-value semantics with the existing typed helpers.
- Added a regression for positive and undefined FAR deltas. The affected metric and protocol suites passed (71 tests), Ruff/format passed, and strict Pyright reports 0 errors/warnings.
- Fresh Graphify now reports 4,126 nodes / 15,944 edges / 182 communities. The source traversal reaches 1,081/1,107 callables, leaving 26 outside the CLI union. The final full suite after this production edit remains pending; matrix remains 227 PASS / 23 PARTIAL. No experiment or commit was made.


## Pre-experiment gate remediation and fresh audit, 2026-09-27

- Fixed the workflow-order gap: preprocessing of all datasets or N-BaIoT now runs the one-cell Data and Domain Evidence Validation workflow after successful preparation; CICIoT2023-only preprocessing does not invoke that primary-dataset gate. `doctor` now remains in preprocessing/data validation until the current validation record exists. Added E2E checks for sequencing, secondary-only behavior, and stage ordering.
- The updated E2E suite passes (11 tests). The fresh full suite passes (942 tests, 279 upstream warnings). Ruff, formatting, strict Pyright, Deptry, and all three Import Linter contracts pass. Vulture reports no candidates at confidence 80 or higher; its unfiltered 60% mode reports typed/Pydantic fields and framework hooks and is not treated as dead-code proof.
- Regenerated Graphify from the current source tree: 4,142 nodes and 17,401 edges. Independent AST count reconciles 1,107 production callables. Source-verified reachability is 1,087/1,107, with 20 outside-union callables still requiring per-callable disposition. Regenerated dispatch ledgers; three AST-ledger checks that previously failed on stale source locations now pass.
- Safe current CLI checks: doctor reports configuration/environment valid and correctly directs to preprocessing/data validation; status reports 0/19 complete; report exits nonzero before export on obsolete schema-2 artifacts, a missing prepared-role parent, and missing/stale comparisons. No `fedsira run` scientific experiment was invoked.
- A whole-project no-overwrite preprocess invocation started before the application wiring change. N-BaIoT completed with its dataset manifest reused and 534 views; CICIoT2023 is still being rescanned. That process cannot verify the newly wired data-validation callback. Prepared-view hashes/mtimes and the CIC no-overwrite result remain to be checked after it exits.
- The per-callable ledger now classifies all 20 outside-union entries as callbacks, registry-time helpers, value-object accessors, or intentional library-facing functions. The matrix closes GRAPH-003, GRAPH-007, GRAPH-008, GRAPH-009, and GRAPH-012 for the current graph; GRAPH-011 remains open until all other findings are remediated and the final fresh graph is generated. The validator now reports 232 PASS / 18 PARTIAL. Remaining PARTIAL rows include claim-state derivation, run-side descriptive summary lineage, project-report numeric consumers, event/default audits, and evidence-renderer checks. The pre-experiment readiness gate is **NOT READY**. No scientific experiment, commit, or result steering was performed.


## Reporting aggregation correction and completed preprocessing rerun, 2026-09-27

- Corrected the Delay and Efficiency table to share the figure's typed two-stage aggregation: repetition medians within each seed, then median/IQR across seed medians. The shared summary now covers all seven efficiency metrics. Added a 3-seed × 5-repetition regression fixture.
- Persisted aggregate metric rows now exclude failed/invalid terminal outcomes while retaining those rows in cell-level evidence with their terminal states. Added a mixed completed/failed regression fixture.
- Focused reporting suite passes 33 tests. Ruff, formatting, and targeted Pyright pass for the reporting changes.
- The current no-overwrite whole-project preprocessing run completed both datasets with manifest reuse. SHA-256 and nanosecond-mtime comparison passed for all 534 N-BaIoT and 1,674 CICIoT2023 prepared sidecar/Parquet pairs. The 39-predictor CIC schema versus the 46-predictor published reference is already recorded in the empirical deviation ledger and matches the raw-schema verifier.
- The Graphify executable is unavailable in this runtime. A fresh Graphify update is still required after this source refactor, and the full test suite remains pending. No scientific experiment or commit was made.


## Final telemetry and Graphify reconciliation, 2026-09-27

- Centralized two-stage repeated-measurement summaries in reporting/telemetry.py; figure, table, and aggregate evidence now share the same per-seed median and across-seed mean/median/type-7 quartile calculations.
- A fresh Graphify update and regenerated analyzer inventory now report 4,203 nodes / 17,573 edges / 29 communities and 1,109 production callables (927 functions, 182 methods).
- The earlier full-suite run was concurrent with graph refresh and reported three architecture ledger source-location failures. After the graph and ledger were regenerated from the current source, all 18 workflow topology tests passed. Reporting tests pass (33). Full-suite and final static checks remain pending.
- Corrected stale matrix references to Graphify availability and callable counts; the matrix validator reports 232 PASS / 18 PARTIAL. The final second Graphify comparison and experiment readiness gate remain open. No experiment or commit was made.


## Final full-suite and static verification, 2026-09-27

- The rerun after removing the repository-policy violation passed all 942 tests (279 upstream warnings; 921.58 seconds). No scientific experiment was run.
- The full static set is clean: Ruff, format check, strict Pyright (0 diagnostics), Deptry, and all 3 Import Linter contracts. The focused 54-test policy/topology/reporting set also passed.
- Final source Graphify reports 4,203 nodes / 17,573 edges / 29 communities; 1,109 production callables reconcile with the AST inventory (927 functions, 182 class methods).
- The no-overwrite preprocessing rerun and independent SHA-256/nanosecond-mtime comparison preserve all 2,208 prepared pairs. Remaining 18 PARTIAL requirements are recorded explicitly; experiment readiness remains NOT READY.

## Run/report destination correction, 2026-09-27

- Completed runs now materialize per-experiment metric and telemetry Parquet in the output artifact slot. Named reports require semantically valid run-side metric evidence and write per-experiment tables, figures, summaries, and export manifests under the results tree. This fixes the prior mismatch where run products went under outputs while named report verification looked under results.
- Reporting tests pass (33); strict Pyright reports zero diagnostics and touched-file Ruff passes. The full suite has not yet been rerun after this report-path correction.
- Fresh Graphify after named-report verification and topology updates reports 4,213 nodes / 17,636 edges / 29 communities. The analyzer inventory has 1,112 callables, 1,084 in the CLI union, and 28 outside with documented dispositions. Matrix validation remains 232 PASS / 18 PARTIAL; report aggregation/lineage and claim derivation remain open. The architecture suite passes 131 tests, reporting passes 33, and the corrected full suite passes 942 tests with 279 upstream warnings in 193.20 seconds. No experiment or commit was made.

## Reporting lineage remediation, 2026-09-27

- Corrected `seed-metrics.parquet` to contain one row per seed and metric, combining any within-seed repetitions before across-seed aggregation. Each seed row carries configuration, code, dataset-manifest, scoring-artifact, source-observation, and source-cell lineage. Aggregate rows now derive from those seed rows; efficiency retains its prespecified per-seed median semantics. Metric-evidence producer identity was bumped to version 2.
- Report loading now verifies metric-family publication identity, execution digest, file sizes/checksums, and semantic completeness, then loads cell values from Parquet. It clears in-memory values if the published evidence or provenance is missing or invalid. Project export checks required metric evidence for every completed experiment before rendering.
- Added regressions for within-seed aggregation and aggregate seed counts. The full suite passes 944 tests (279 upstream warnings); full Ruff, format, strict Pyright, Deptry, 3 Import Linter contracts, and Vulture at confidence 80 pass. No scientific experiment or commit was performed.
- Final forced Graphify currently reports 4,232 nodes, 17,782 edges, and 29 communities. The source-verified inventory reconciles 1,123 production callables (1,102 in the CLI union; 21 dispositioned outside it). A dated snapshot is retained at `docs/.audit/graphify-final-2026-09-27/`.
- The matrix validates all 250 rows at 232 PASS / 18 PARTIAL. It remains NOT READY because descriptive summaries and some intervals are still calculated during table/figure rendering, project renderers do not directly consume all aggregate/statistical/admission artifacts, and claim-specific state derivation is absent. Other open PARTIALs include defaults/events and final artifact-branch evidence.

## Section 35 claim derivation and final pre-experiment verification, 2026-09-27

- Added fail-closed Section 35 derivation for proposal assistance, plurality, external verification, and aggregate mechanism necessity from the persisted complete comparison families and collapse decisions. Derivation validates exact preregistered family membership and terminal states; incomplete or technically inconclusive evidence remains `Not Tested`. A partially supported mechanism can still be resolved where the known component states determine it despite one unresolved component. The other 15 claim rules remain open.
- Added fixtures for complete evidence, failed survival rules, technical inconclusiveness, partial-family incompleteness, and mechanically determined partial mechanism support. The focused reporting/evaluation suite passes 50 tests. Final full suite: 950 passed, 279 upstream warnings. Ruff/format, strict Pyright, Deptry, all three Import Linter contracts, and Vulture at confidence 80 pass.
- Fresh Graphify reports 4,259 nodes / 16,436 edges / 186 communities. Its inventory reconciles 1,130 production callables (946 functions, 184 direct class methods), 1,104 in the CLI union, and 26 outside with dispositions. Matrix validation remains 233 PASS / 17 PARTIAL.
- Safe `doctor`, `plan`, and `status` commands exit 0. Project `report` exits 1 before materializing outputs because current validation finds obsolete historical artifact manifests, an unpublished role-split dependency, and missing/stale comparison evidence. No scientific experiment or commit was made. The gate remains NOT READY.
- Added the Section 35 claim-state artifact to the production report path. It stores all 19 typed claim decisions, derives identity from the exact current statistical and final-gate manifests plus serialized claim content, verifies those dependencies on read, and is published before unresolved claim states block a complete report. Added round-trip, lineage-change, missing-gate, stale-input, visibility, and project-report blocking tests. Fresh Graphify now reports 4,271 nodes / 16,557 edges / 201 communities and reconciles 1,132 production callables (948 functions, 184 class methods; 1,109 in the CLI union and 23 individually dispositioned outside it). Refreshed the current outside-callable disposition ledger and matrix evidence.
- Current-tree validation passes 955 tests with 279 third-party warnings; Ruff, format, strict Pyright, Deptry, all three Import Linter contracts, and Vulture at confidence 80 pass. Matrix validation reports 233 PASS / 17 PARTIAL. Safe doctor, plan, and status exit 0; project report exits 1 because no experiment terminal records exist and persisted manifests/comparison evidence are obsolete, invalid, missing, or stale. No scientific experiment, `fedsira run`, or commit was performed. The pre-experiment gate remains NOT READY.
- The Evidence Arrival State Trajectory now materializes run-side schedule/cycle/state fractions with counts, denominators, and source-cell keys; named and project figures consume the checksum-bound Parquet. The first whole-suite run passed 951 tests and exposed four architecture-policy issues in touched source and the dispatch ledger. All four were corrected; 71 targeted architecture/reporting tests pass. The corrected full suite passes 955 tests with 279 warnings; Ruff, formatting, strict Pyright, Deptry, Import Linter, and Vulture pass. Fresh Graphify reports 4,290 nodes / 16,625 edges / 200 communities; callable inventory is 1,137 total, 1,113 in the CLI union, and 24 dispositioned outside it. Matrix remains 233 PASS / 17 PARTIAL. No scientific experiment, `fedsira run`, or commit was performed.
- FIG-006 review exposed an omitted valid state: `Rejected Admission` could not appear in the four-state trajectory fractions, breaking partition validation. Added a distinct fifth trajectory state, exact unsupported-state validation, a mixed admitted/rejected two-seed fixture, and bumped metric-evidence procedure identity to 5. Roadmap §34.7 and deviation ledger now document the correction; 44 reporting tests and touched-file Ruff/format/Pyright pass. The broader renderer-by-renderer audit and full-suite rerun remain pending. No scientific experiment or commit was performed.
- Continued the FIG-006 audit: admission-delay plots had coerced missing phase values to 0, and grouped figure helpers silently omitted unavailable rows/series. Delay stacks now annotate incomplete cells `NA`; grouped/series panels annotate missing points and retain all-NA series. Regression fixtures pass with the rejected-state trajectory cases (3 focused checks); touched-file Ruff and Pyright pass. Full renderer coverage and a full-suite rerun remain pending; no scientific experiment or commit was performed.
- Completed the current outcome-completeness renderer batch: comparison, collapse, source-exclusion, delay, and capability plots retain incomplete observations with visible `NA`; rejected admissions remain in the persisted fifth-state trajectory. Reporting tests pass (58), full static checks pass, and the full suite passes 960 tests with 279 upstream warnings. Matrix remains 233 PASS / 17 PARTIAL; no scientific experiment, `fedsira run`, or commit was performed.
- Project report publication is now wired end to end: ownerless source-data artifacts record sorted references to current dataset/split/configuration, metric, comparison, final-gate, and claim-state manifests; rendered table/figure digests are checked on readback; project export artifacts record relative paths and are verified against the source identity and product files. Project reproducibility JSON records the source-data identity. Rendering occurs in a temporary stage and incomplete mandatory material coverage returns no result products. Added ownerless source/export lineage coverage. The focused reporting suite passes (50); full suite passes 961 tests with 279 warnings. Full Ruff, format, strict Pyright, Deptry, three Import Linter contracts, and Vulture pass. Fresh Graphify: 4,316 nodes / 16,788 edges / 185 communities; inventory: 1,141 callables, 1,113 in CLI union, 28 outside with dispositions. Matrix remains 233 PASS / 17 PARTIAL. Safe doctor, plan, smoke, and status pass; report displays BLOCKED for obsolete schema-2 manifests, invalid prepared-role lineage, and absent/stale comparison evidence. No scientific experiment, `fedsira run`, or commit was performed.

## Preprocessing side-effect correction, 2026-09-27

- A production N-BaIoT preprocessing invocation unexpectedly started the registered `Data and Domain Evidence Validation` run through `FedSIRAApplication.preprocess`. This was an unintended application-layer side effect. One validation cell completed and its execution record is preserved at `outputs/experiments/Data and Domain Evidence Validation/records/6daba1aaa3a53c1c8dac9d2ed0d706ffbfe866f72f7868f4c0fa8b539bc53c07.json`; it published metric-evidence files containing no model-performance outcomes (those metrics are `NA`) and no scoring artifacts. It is not treated as a scientific result. No other experiment was started.
- Removed automatic experiment execution from preprocessing; the data-validation workflow remains an explicit registered run. Bumped role/split manifest procedure identity to version 2 because the prior identity reused a valid but empty manifest after the preprocessing payload-generation logic changed. A targeted regression verifies preprocessing only materializes data. At this point in the audit the corrected manifest had not yet been regenerated; completion is recorded below. No experiment or commit was made after this correction.

## N-BaIoT lineage repair completed, 2026-09-27

- Updated preprocessing no longer starts an experiment. The full N-BaIoT materialization completed in 82m 46s using a temporary disk-backed DuckDB database with a 2 GB buffer-manager limit; it prepared 534 views and reported 320,000 anchor-train rows. The regenerated version-2 role/split manifest contains 534 non-empty counts across 11 classes and 9 domains, totaling 1,569,865 rows. All 534 current prepared-role artifacts reference the regenerated manifest identity `c21a5ebda4919b2e99fe140111200b575900bd5835126f33073f510da7dbd749`.
- The first in-memory materialization attempt was intentionally interrupted after about 11m when RSS reached 4.4 GB; its workflow terminal event is preserved as a failed preprocessing attempt. The disk-backed rerun completed with process RSS approximately 2.0–2.7 GB. Focused preprocessing/CLI tests pass (33), Ruff and strict Pyright pass for touched source and tests, and Graphify was refreshed. The only experiment record remains the unintended one-cell data-validation execution described above; no additional experiment or commit was made.
- Safe `doctor` and `status` both exit 0 after the lineage repair. Doctor reports dataset readiness Completed, one completed validation workflow, and 12 blocked downstream experiments; the next project action is the explicit Baseline Implementation Validation run. No such experiment was started. Matrix validation remains 250 rows: 233 PASS / 17 PARTIAL. The full suite and project report were not rerun after this change, so implementation/scientific closure remains incomplete.

## N-BaIoT verified cache reuse, 2026-09-27

- Added a fail-closed no-overwrite fast path requiring the current raw manifest and preprocessing configuration, version-2 role/split manifest, current scaler artifact, all view sidecars, and every prepared Parquet checksum to match. Cache misses fall back to the full disk-backed materializer. The scaler's feature schema is read only after each sidecar/checksum validates; malformed Parquet therefore becomes a cache miss.
- Added cache-path regression coverage for exact row-count/moment reuse and tampered-Parquet rejection. The focused N-BaIoT, role-manifest, and preprocessing-artifact suites pass: 37 tests. Ruff and strict Pyright pass for all touched source and test files.
- Independently checked the live production cache against all 89 discovered N-BaIoT CSVs: 534 views and 1,569,865 rows validated. A full `fedsira preprocess N-BaIoT` then completed in about 10 seconds, reused manifest `3d43e867…277a8b`, and reported 534 views / 320,000 anchor-train rows. This command did not run an experiment.
- Graphify refreshed to 4,335 nodes / 16,941 edges / 197 communities after the feature-schema reader was updated to close its DuckDB connection on both success and failure. The regenerated callable inventory reconciles 1,146 production callables (960 functions, 186 methods), with 24 outside the CLI union. Ruff/Pyright pass and the cache corruption regression passes again. The full suite and project report remain unrerun; the matrix remains 233 PASS / 17 PARTIAL and the pre-experiment gate remains NOT READY. No scientific experiment or commit was made.

## Short E2E workflow closure, 2026-09-27

- Added an isolated temporary-repository E2E workflow using actual N-BaIoT fixture preprocessing, checksum-corruption recovery, verified cache reuse, plan, smoke, status, and fail-closed report behavior. The test uses no scientific run path. Existing tests continue covering post-core `run` refusal.
- The full E2E suite passes 12 tests in 18.93 seconds (14 dependency deprecation warnings). Ruff and strict Pyright pass for the new E2E module. TEST-010 is now PASS; the matrix validates at 234 PASS / 16 PARTIAL. Fresh Graphify reports 4,339 nodes / 16,965 edges / 178 communities, and the analyzer inventory reconciles 1,146 production callables. No new experiment or commit was made.
- The project report-lineage review confirmed current exports bind upstream artifact sets and rendered table/figure bytes, while numeric outputs still lack exact per-number source-cell/config/statistical references. A global artifact list would not satisfy ART-011; row/figure lineage must be carried from each producer's actual numeric inputs. This requirement remains open for a producer-side implementation.

## Statistical-summary lineage remediation, 2026-09-27

- Added typed Statistical Summary row/column lineage from each output row to its comparison identity, paired seeds, and main/reference semantic cell keys.
- Named and project source-data publication now resolves those rows to current statistical-comparison manifests and checks every displayed field by rerendering from the persisted comparison result. Source-data payload schema/procedure is version 5; old versions fail readback.
- Added renderer lineage and artifact publication regressions. Focused renderer test passes (1); publication artifact tests pass (15); Ruff and strict Pyright pass on changed production code.
- This closes only the paired-comparison table crosswalk. Aggregate-backed result table values, all figure points, split/configuration-subset refs, and claim-state source lineage remain open; ART-011 and dependent matrix rows remain PARTIAL. The full reporting suite passes 65 tests (14 third-party warnings). Forced Graphify plus `analyze_graph.audit` report 4,367 nodes, 17,198 edges, 188 communities, 1,157 callables, 1,133 CLI-union callables, 24 dispositioned outside, 444 terminal leaves, and maximum CLI depth 24. No scientific experiment or commit.

### Primary Results aggregate cells

- Added source keys for all eight aggregate-backed Primary Results value cells per method/scenario row (mean/SD, CI, supported harm, FAR increase, ASR, admissions, and worst-domain F1). Publication checks keyed aggregate uniqueness, method/scenario identity, the precise rendered statistic, explicit `NA` for absent evidence, and a current metric-artifact reference; readback checks the source artifact is part of the payload upstream set.
- Reused the same formatter in rendering and publication verification to prevent formula/display drift. Source-data schema/procedure advanced to version 6 after the payload changed.
- The complete reporting suite passes 65 tests. Changed production modules pass Ruff and strict Pyright. This closes only Primary Results aggregate cells; other tables and figures still need the same treatment. No scientific experiment or commit.
- Forced Graphify and the source-verified inventory were refreshed after this production change: 4,377 nodes, 17,238 edges, 199 communities; 1,160 callables (974 functions, 186 methods), 1,136 CLI-union callables, 24 dispositioned outside, 444 terminal leaves, and maximum CLI depth 24. The report lineage additions are reachable from the production report path. The final audit acceptance pass remains open with 16 PARTIAL matrix rows.
- A fresh incremental Graphify pass after payload version 7 and typed-boundary fixes reports 4,384 nodes / 17,255 edges / 189 communities; the independent AST inventory remains at 1,160 callables. The first full repository run exposed five architecture failures and nine reporting test failures: formatting, a newly disallowed identifier/comment, stale metric payload field references, direct runtime evaluation of pandas generic aliases in `cast`, and resulting Pyright errors. Those causes were fixed; 59 focused reporting/architecture typing tests pass, and Ruff, formatting, Pyright, Deptry, Import Linter, and Vulture all pass repo-wide. The clean full-suite rerun under PID 753908 passed 973 tests with 279 upstream warnings and no failures in 403.39 seconds. No experiment or commit was made.

### Repository-wide static verification

- Repository-wide Pyright surfaced pandas stub ambiguity in aggregate CI validation and one trajectory grouping test. Replaced the production `isin` call with explicit typed comparisons, cast parquet series at the boundary, and iterated the fixed schedule × cycle grid in the test instead of relying on an untyped groupby key.
- Ruff, format check, strict Pyright, Deptry, all three Import Linter contracts, and Vulture at confidence 80 passed repository-wide after the typing cleanup. The full repository test suite passed separately with 973 passed and no failures. A later outcome-completeness renderer change is under focused and repository-wide revalidation.
- A renderer-level outcome-completeness hole was closed for evidence-arrival trajectories: rendering now requires all four schedules, all states at every configured logical cycle, unique keys, and state fractions that partition every seed. Full-grid and missing-grid fixtures pass; the reporting module passes 42 tests, and touched-file Ruff/Pyright pass. Repository-wide verification remains to be rerun after this production change. FIG-006 remains PARTIAL for other renderers. No experiment or commit was made.
- `graphify update .` and the independent analyzer ran after the trajectory renderer change: 4,385 nodes / 17,266 edges / 179 communities; 1,160 production callables still reconcile. Repository-wide Ruff, formatting, Pyright, Deptry, Import Linter, and Vulture pass. The updated full suite is running in terminal session 96056.
- The architecture suite rejected a literal floating-point partition tolerance. Replaced it with exact persisted instance counts/totals on each `EvidenceStateFraction`; the renderer now checks each fraction against its count and requires integer counts to sum to the shared denominator. Touched-file checks and 42 reporting tests pass. The final Graphify update reports 4,386 nodes / 17,268 edges / 183 communities; repository-wide static checks pass, and the full suite passes 974 tests with 279 upstream warnings and no failures in 256.64 seconds.
- The Secondary Generalization figure now enumerates target-F1 rows from the registered comparison design rather than whichever results happen to exist. It preserves scenario and comparator identity and displays `NA` for missing/inconclusive entries; a regression checks the complete preregistered row set. Focused report tests and touched-file Ruff/Pyright pass. Repository-wide checks need another run after this renderer change; no experiment or commit was made.
- After replacing forbidden raw dictionaries with typed tuple searches, the architecture/report-focused checks pass 50 tests. Forced Graphify update plus independent analyzer report 4,386 nodes / 17,273 edges / 183 communities and 1,160 production callables. Repository-wide Ruff, formatting, Pyright, Deptry, Import Linter, and Vulture pass; full suite passes 974 tests with 279 warnings and no failures in 303.42 seconds. No experiment or commit was made.

### Registered figure-grid completeness, 2026-09-28

- Updated boundary renderers to draw methods and conditions from registered experiment definitions rather than completed outcomes; shared-epistemic strengths now follow the configured registered strength tokens. Admission-delay rendering enumerates the full registered method × condition grid, retaining absent metric evidence as `NA`. Its regression asserts that every preregistered x-axis cell remains visible.
- Focused reporting figure tests pass: 42 passed, 14 third-party warnings. Changed files pass Ruff, formatting, and Pyright. `graphify update .` rebuilt 4,386 nodes / 17,276 edges / 182 communities. This closes part of FIG-006; other renderers still need outcome-completeness review. No scientific experiment or commit was made.
- Security–Utility Tradeoff now enumerates the full registered primary comparison design and displays absent/inconclusive effects as `NA`; it rejects duplicate or identity-mismatched observed evidence and still fails when no primary comparison evidence exists. Efficiency Profile now retains all experiment-registered methods for each plotted metric and marks method/metric gaps `NA`; duplicate telemetry fails closed. Focused regressions pass for delay, security-utility, and efficiency figures (4 selected tests), with Ruff and Pyright passing. The full reporting figure module and a post-change Graphify refresh are pending.
- Useful Backdoored Source now plots all registered source-exclusion methods once at least one valid outcome exists, leaving absent aggregate estimates visible as `NA`. Roadmap review found the reproducer boundary must distinguish attack strategy as well as method; it now builds one clean/one/two-count series for each registered attack strategy × method and fails if the explicit strategy mapping no longer covers the experiment condition design. Compromised-verifier conditions also validate against the registered condition grid, and condition counts now use typed explicit mappings instead of string prefixes. The focused changed-figure checks pass (7 tests); full module tests and Graphify refresh remain pending.
- Compromised-Verifier Boundary now produces separate false-positive and false-negative figure artifacts as required by Roadmap §34.6. The experiment artifact registry and mandatory-report figure inventory require both outputs. Both figures show the configured random-profile exact hypergeometric contamination risk; its eligible-pool domain derivation is shared with the preflight checks. Ruff and Pyright pass for all changed Python files; the reporting figure module passes 45 tests. Repository-wide test and static verification need rerunning after this last output-path change; Graphify refresh is pending.
- Completed the matching registered-grid audit for report tables: Primary Results, Source Exclusion, Failure Boundaries, Delay/Efficiency, and Byzantine Robustness now retain every registered identity when evidence is absent and render unavailable measurements as `NA`. Failure Boundary rows include method identity; Byzantine rows distinguish experiment/method/condition. Added full-grid regression coverage and updated the pre-existing Primary Results lineage assertion to cover all 42 rows. The reporting module passes 50 tests; changed reporting modules pass Ruff, format, and strict Pyright. Graphify refreshed to 4,408 nodes / 17,384 edges / 199 communities. Full repository verification and remaining renderer/provenance/claim audits are still open. No scientific experiment or commit was made.
- Repository-wide verification initially found a stale architecture test expecting 13 mandatory figures after the verifier boundary was correctly split into two artifacts. Updated the test to require both named verifier figures and a 14-artifact inventory. Focused architecture checks pass (13); repo-wide Ruff, format, strict Pyright, Deptry, Import Linter (3 contracts), and Vulture pass. The clean complete test rerun passes 982 tests with 279 upstream warnings in 563.61 seconds. Graphify reports 4,408 nodes / 17,385 edges / 195 communities. Audit matrix evidence was updated; the substantive PARTIAL requirements and acceptance gate remain open. No scientific experiment or commit was made.
- Expanded per-cell canonical aggregate lineage from Primary Results to Source Exclusion, Ablation, Byzantine Robustness, Failure Boundaries, Delay, and Generalization tables. Publication checks now bind those cells to registered row identities, current metric artifacts, and exact canonical display formatting; fixed single-scenario tables are validated against their registered design. Added full registered-cell lineage assertions and an end-to-end Source-Exclusion publication fixture with matching aggregate/seed evidence. All 77 reporting tests pass; repo-wide Ruff, format, strict Pyright, Deptry, all three Import Linter contracts, and Vulture pass. Graphify refreshed to 4,411 nodes / 17,417 edges / 190 communities. FIG-003, WIRE-009, ART-011, GRAPH-010 and final audit remain partial for comparison cells, figure points, telemetry, split/configuration lineage, claim derivation, and complete workflow artifact closure. No scientific experiment or commit was made.


## Safe-dormancy fail-closed claim wiring, 2026-09-28

- Rechecked live process state: no scientific experiment command, experiment Python process, or pytest process was active. No experiment was started during this remediation.
- `verify_safe_dormancy` previously returned success for an empty evidence tuple because it only counted observed permanent-singleton admissions. It now requires exactly one completed current record for every registered plan cell, one valid singleton outcome per cell, and a non-empty admission-state trajectory. It computes `T_evidence` using the same schedule, target-capable domain order, measurement horizon, committee size, and final-gate threshold as the experiment handler. It rejects any admission before that cycle, any admission for a schedule with no sufficient evidence, any permanent-singleton admission, and lack of post-evidence progression under gradual/immediate schedules.
- Project-report claim derivation now marks `Safe Dormancy` Supported only when that verifier passes; a missing verifier result leaves it Not Tested. Thirteen of the 19 claim rules remain unimplemented, and the project report remains blocked by unresolved claims.
- Focused Safe Dormancy verification: 5 tests pass, including missing planned-cell evidence and computed pre-evidence admission. After extending the claim-verification pass to Byzantine Operating Region, the combined reporting/evaluation subset passed 86 tests with 14 third-party warnings. This is not the full repository suite. No full suite has run after the preceding aggregate-cell lineage changes.
- Graph-guided inspection found the same empty-record false pass in Byzantine Operating Region. Its verifier now matches registered within-bound resolved-core cells, requires at least the configured nine complete seed records in each of the two conditions, requires exactly one finite [0,1] value for malicious admission, legitimate admission, attack success rate, and target F1, and requires zero malicious admissions. The configured maximum is required to be zero. Claim summarization derives Conditional only from this pass. Synthetic tests check empty evidence, nine-seed threshold, the eight-seed failure boundary, incomplete metric rejection, admission rejection, claim-state wiring, and Safe Dormancy. Full repository tests and a confirmed post-change Graphify snapshot remain pending. No scientific experiment or commit was made.
- Continued source review found that verifier joins should validate the persisted identity fields and should not count duplicated planned cells as distinct seeds. Safe Dormancy and Byzantine Operating Region now compare semantic key, experiment, method, condition, seed, and repetition against the planned cell; the Byzantine verifier deduplicates planned identities and rejects duplicate plan entries. Added regression assertions for duplicate plans and mismatched record identity. These newest assertions have not run because Ubuntu no longer responds to trivial `wsl.exe -d Ubuntu --exec /bin/echo` invocations; earlier live command handles were polled and then interrupted without affecting the WSL distro. Windows process inspection shows idle command wrappers for another project's campaign script, so I left that external workload untouched. The file checks show the changed Python targets are Ruff-clean under the host Ruff 0.14.14; the repository pins Ruff 0.7.4, so this is not a substitute for the pinned checks. Matrix revalidation confirms 250 rows: 234 PASS and 16 PARTIAL. No experiment or commit was made.
- Re-read Section 35.2's Mechanism Necessity rule and found a state-combination bug: one or two supported components with the remaining component evidence unresolved were incorrectly mapped to Not Tested when supported plus unresolved equaled all three components. Derivation now follows the explicit rule: all three supported → Supported; one or two supported → Partially Supported; zero supported with complete valid evidence → Null Result; otherwise Not Tested. Added fixtures for one and two supported components with unresolved remainder. Host Ruff 0.14.14 check/format pass for the edited module and tests. Unit execution and pinned Ruff remain pending because WSL is still unresponsive. No experiment or commit was made.
- Revalidated after that edit using the repository-pinned Ruff 0.7.4 via the existing `uvx` launcher on Windows: full-repository Ruff lint and format checks pass (250 files). Windows Python 3.11 also parsed all 241 production and test Python files successfully. This provides syntax/static evidence only; it does not replace Pyright, import-linter, Vulture, or pytest. Unit tests for the newest identity checks and Mechanism Necessity state combinations remain unrun; the 86-test reporting/claim result predates these edits. Ubuntu still hangs on `wsl.exe -l -v`; the affected command was polled and then cancelled without terminating the distro or unrelated project sessions. No experiment or commit was made.
- Follow-up claim review tightened Section 18 summary derivation: necessity claims now require exactly one collapse decision and family, consistent survival/effect/adjusted-p-value evidence, and a family comparison that matches the decision metric and passes. Mechanism Necessity also now maps one or two supported components with unresolved remainder to Partially Supported. Added regressions for mismatched collapse metrics, duplicate decisions, and supported-plus-unresolved component combinations. These newest tests remain unexecuted: Ubuntu/WSL stalls, and the Windows Python fallback fails at collection because the production runtime imports the Linux-only `resource` module. Exact pinned Ruff 0.7.4 lint/format and Python AST parsing passed on the changed files before this status check. No full scientific experiment or commit was made by this audit pass. Historical audit evidence still includes the earlier one-cell validation incident, so the zero-experiment acceptance predicate remains unmet.
