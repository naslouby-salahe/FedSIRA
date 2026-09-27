
## Fresh audit, 2026-09-25

- `graphify extract . --force --code-only` completed as fresh pass 1: 4,208 nodes, 15,065 edges, 167 communities. Snapshot stored at `docs/.audit/graphify-pass1/`.
- Started real CICIoT2023 production preprocessing (allowed pre-experiment workflow) using the repository CLI. PID and complete log are in `docs/.audit/preprocess-cic-20260925.pid` and `docs/.audit/preprocess-cic-20260925.log`. It processes actual `data/raw/CIC_IOT_Dataset2023/CSV/MERGED_CSV` shards. No scientific experiment has been launched.
- The first production attempt exited at 7,200 seconds with `OperationTimeoutError` inside `_ciciot_pseudo_domain`; it had not published prepared views. Its complete trace is in `preprocess-cic-20260925.log`.
- Replaced per-row Python UDF calls for stable-row IDs, pseudo-domain hashing, and sampling digests with native DuckDB SHA-256 over the identical framed bytes. Labels are now normalized once per distinct raw label per shard. Regression tests compare native SQL outputs with the prior Python definitions.
- Optimized production retry remains active (PID `1229427`; log and exit code files are `preprocess-cic-optimized-20260925.log` and `preprocess-cic-optimized-20260925.exit`). Latest checkpoint: 1h51m elapsed, CPU-active, with 1,247 output files visible. The log is still buffered after its start event; inspect publication manifests and final exit after completion.
- The optimized retry subsequently reached the configured 2-hour limit while ingesting a 265,519-row shard; DuckDB raised `RuntimeError: Query interrupted`. It hashed the actual file manifest and scanned 36,920,877 raw rows across the shard sequence, but published no prepared views. Root cause is the single-threaded per-row transformation path. CICIoT transforms and stable-keyed role ranking now use four DuckDB threads while CSV physical-row indexing remains single-threaded. Focused tests and static checks are running/passing before a fresh final-code retry; use `launch_ciciot.py` to start it and record its PID/log/exit.
- Final-code CICIoT2023 production retry (wrapper PID `1626697`, worker PID `1626703`; `preprocess-cic-final-20260925.log`, `.pid`, `.exit`) exited `1` at the configured 7,200-second bound while inserting into `retained` during `_ingest_shard`; no prepared views were published. DuckDB cumulative process writes exceeded 434 GB with a 12,250,001,408-byte staging database. The staging-table primary-key indexes have now been removed; rerun full checks before the next production attempt.
- An indexless staging regression test was added to check that the three temporary tables do not declare primary-key indexes. Ingestion now casts each predictor once and avoids writing a second wide identified table. The repository-pinned Ruff 0.7.4 passes lint and formatting checks over all `src`, `tests`, and `docs/.audit` files (237 formatted); tests and strict Pyright remain to be rerun in WSL.
- First final-code full suite (wrapper PID `1635920`) completed with 895 passed and 3 architecture failures: Ruff formatting/lint plus the repository's no-comments policy. Removed the production comments, formatted modified files, and moved the high-complexity temporary inventory program to an `.audit` extension; the six relevant architecture checks now pass and Ruff is clean.
- Final full-suite rerun completed successfully (wrapper PID `1647083`; exit `0`): `898 passed, 279 warnings in 195.82s`, with no skipped tests. It ran independently alongside CICIoT production preprocessing.
- First final full-suite pass (session `24707`) completed with 895 passed, 1 failure: the production-only-by-tests architecture rule flagged three obsolete Python CIC hash helpers after production hashing moved to DuckDB SQL. Removed those helpers and moved parity reference calculations into the tests.
- Corrected full suite in Codex terminal session `87793` passed: 892 tests, no skips; the final suite below supersedes it after subsequent artifact changes.
- Full-suite session `64147` after artifact schema/scoped-dependency and stale-execution changes completed with 892 passed, 279 warnings, and six failures (five architecture checks plus the ablation reference fixture). The scope boundary is now represented by typed configuration components; the corrected focused architecture/artifact/comparison suite passed 19 tests, and the affected artifact/CIC/execution suite passed 101 tests.
- Ruff and strict Pyright passed after the typed-scope fix. An incremental `graphify update .` completed successfully; final forced Graphify extraction remains pending.
- Final Graphify pass 2 completed after code remediation: 4,219 nodes, 15,212 edges, 181 communities. Snapshot is under `docs/.audit/graphify-pass2/`; analyzer output is in `callable-inventory.md`.
- Final forced Graphify extraction on the remediated tree completed at 2026-09-25 16:16 UTC: 4,245 nodes, 15,465 edges, 190 communities. Full snapshot is under `docs/.audit/graphify-final-snapshot/graphify-out/`; callable and all 19 prospective handler-path inventories were regenerated from it. No experiment was executed.

## 2026-09-25 follow-up

- At 19:06 UTC, Windows reported Ubuntu as running, but `wsl.exe --distribution Ubuntu --exec /bin/echo alive` produced no output within 10 seconds and was cancelled. Existing Ubuntu/FedORBIT work remains active, so the distribution was not terminated or restarted.
- Windows-side in-memory `compile()` verified syntax for all 234 source/test Python modules and `verify_prepared_outputs.audit`. The latest pinned Ruff check is recorded above and passes.
- Full tests, strict Pyright, fresh Graphify, production CIC retry, prepared-artifact verification/idempotence, and fresh N-BaIoT production/reuse remain pending on Ubuntu execution. No experiment was run.

## WSL resumed, 2026-09-25

- Fresh forced Graphify extraction completed against the current tree. Snapshot copied to `docs/.audit/graphify-pass3/`; 4,245 nodes, 15,465 edges, 190 communities. Callable and 19-handler workflow inventories were regenerated from this extraction.
- Focused CIC preprocessing tests passed after replacing a private-helper test with an end-to-end materialization constraint check (22 passed); strict Pyright reports 0 errors/0 warnings. Ruff lint/format, Deptry, Import Linter, and Vulture pass.
- Current full suite ran in WSL session 10406 and passed: 898 passed, 279 warnings, 183.92s; no skipped count was reported.
- Real CICIoT2023 production preprocessing launched through `.venv/bin/fedsira preprocess CICIoT2023` at 19:58:18 UTC. Wrapper PID 58649, worker PID 58655; log `docs/.audit/preprocess-cic-indexless-20260925.log`, PID file `docs/.audit/preprocess-cic-indexless-20260925.pid`, completion code file `docs/.audit/preprocess-cic-indexless-20260925.exit`. The job is active; keep it running and inspect it at natural checkpoints.

- The indexless production retry exited with code 1 when the DuckDB WAL exhausted available filesystem space; its log is `preprocess-cic-indexless-20260925.log`. No prepared views were published. Its 3 GiB temporary staging database and WAL were removed after confirming no worker remained, restoring capacity.
- Bounded WAL growth by checkpointing the persistent DuckDB database every 16 completed shard ingests and after the final shard. The combined CIC preprocessing/schema, reporting, comparison-evidence, and execution tests passed: 99 passed, 14 third-party deprecation warnings, no skips.
- A fresh actual CICIoT2023 production CLI retry is running with the checkpoint change: PID 107933; log `preprocess-cic-checkpoint-20260925.log`; PID record `preprocess-cic-checkpoint-20260925.pid`; expected exit record `preprocess-cic-checkpoint-20260925.exit`. At the first checkpoint, it had written a 929 MiB staging database and an 820 KiB WAL, with shard processing still active.
- Reporting-lineage fixtures passed separately (2 selected tests), including metric/aggregate source references and paired-seed/source-cell comparison lineage. The full suite must be rerun after the remaining changes.

## 2026-09-26 continuation

- The actual CICIoT2023 retry using DuckDB staging on the H: Windows-mounted volume (worker PID 460388) terminated with exit code 1 in `_assign_secondary_roles`: DuckDB could not allocate memory while reading `/mnt/h/FedSIRA-audit-ciciot-preprocessing-20260925/ciciot2023_preparation.duckdb` (3.5 GiB). No prepared views were published. The shared raw tree at `/home/naslouby/Projects/datp-shared-data/raw` was not changed.
- The H: staging directory and its failed database are audit-created scratch. To isolate DuckDB I/O from the mounted-volume read failure, the next production retry will place the temporary database on the local Linux filesystem; no source data or existing prepared outputs are being relocated.
- Fresh forced Graphify after the cache-identity remediation: 5,597 nodes, 17,110 edges, 378 communities. AST and graph counts reconcile at 1,102 production callables (922 functions, 180 methods), 357 classes; 19 prospective handler paths refreshed. The 206 callables outside the injected CLI union are enumerated in `unreachable-callables.md` for explicit dynamic/framework review.
- Changed-input prepared-view cache regressions passed for both dataset writers; generic prepared-view sidecar consumer tests passed. Ruff passed; Pyright passed before the final common sidecar fields were added and will be rerun.
- A report-path review found that report loading and resolved-core materialization rebuilt comparisons instead of consuming the persisted statistical artifact. Split comparison construction from read-only evidence loading, require current comparison evidence for registered workflows, and attach the exact artifact identity to each comparison Parquet row. Updated comparison currency digests to include provenance and scoring-artifact IDs; bumped the comparison evidence and report-export schemas. The report topology guard rejects statistical-builder reachability. Focused workflow/comparison/report/execution suite passed (67); strict Pyright and Ruff/format passed.

- The H: staging attempt failed with DuckDB `Cannot allocate memory` while scanning the 3.5 GiB database. After the user's instruction to continue without regard to storage, a fresh production `fedsira preprocess CICIoT2023` retry was started with its temporary DuckDB on local ext4 and 8 GiB DuckDB memory cap. Worker PID 68647; wrapper PID 68646; log `preprocess-cic-local-staging-20260926.log`; PID file `preprocess-cic-local-staging-20260926.pid`; completion file `preprocess-cic-local-staging-20260926.exit`.
- At 2026-09-26 11:20 UTC the worker was active, CPU-bound, and had written a 1.7 GiB DuckDB database with a 748 KiB WAL. No prepared views were published yet. Shared raw files and existing published views remain in place.
- Cache remediation is verified by the focused N-BaIoT/CIC/prepared-sidecar suite: 55 passed. Ruff lint/format, strict Pyright (0 errors/warnings), Deptry, Import Linter (3 kept, 0 broken), and Vulture completed successfully. The full suite is still running; its final summary has not yet been recorded.
- The first post-remediation full suite exposed eight architecture-policy failures. Fixed Ruff coverage of generated audit helpers, removed a raw mapping and the unused checkpoint restore helper, replaced primitive boundary annotations with domain aliases, and used the claim-state enum. The corrected full suite passed: 909 passed, 279 third-party warnings, no skips in 796.73 seconds. Ruff lint/format, strict Pyright, Deptry, Import Linter (3 kept/0 broken), and Vulture also pass.
- Fresh `doctor` and `status` exited 0; `plan` reported 299 pre-core, 1,690 post-core, 1,989 total cells. Doctor saw 7 ready/12 blocked workflows and no resolved core. `report` exited 1 with explicit incomplete-evidence refusal; only diagnostic logs changed. The report still surfaced obsolete schema-2 historical manifests and the project-summary refusal, as expected.
- `smoke --overwrite` passed all 32 invariant checks and regenerated the smoke record; the ordinary rerun passed and reused the identical SHA-256 `28de70b45af0dca0cf2dcee5a13ef711f385f696bcacaba636751f375819bb27`. The pre-existing smoke record was preserved as `smoke-record-before-20260926.json`.
- The local-ext4 CIC retry resumed after the full suite. At 2026-09-26 12:00 UTC it remained active around 3.6 GiB staging; no newly written prepared CIC views were yet observed. Continue to inspect the live worker and verify the prepared outputs before closing PRE/EXEC rows.

- The indexless production retry exited with code 1 when the DuckDB WAL exhausted available filesystem space; its log is `preprocess-cic-indexless-20260925.log`. No prepared views were published. Its 3 GiB temporary staging database and WAL were removed after confirming no worker remained, restoring capacity.
- Bounded WAL growth by checkpointing the persistent DuckDB database every 16 completed shard ingests and after the final shard. The combined CIC preprocessing/schema, reporting, comparison-evidence, and execution tests passed: 99 passed, 14 third-party deprecation warnings, no skips.
- A fresh actual CICIoT2023 production CLI retry is running with the checkpoint change: PID 107933; log `preprocess-cic-checkpoint-20260925.log`; PID record `preprocess-cic-checkpoint-20260925.pid`; expected exit record `preprocess-cic-checkpoint-20260925.exit`. At the first checkpoint, it had written a 929 MiB staging database and an 820 KiB WAL, with shard processing still active.
- Reporting-lineage fixtures passed separately (2 selected tests), including metric/aggregate source references and paired-seed/source-cell comparison lineage. The full suite must be rerun after remaining changes.

- Correction at 2026-09-26 12:23 UTC: the active local-ext4 CIC retry began publishing freshly regenerated prepared views after 12:00. Worker PID 68647 remains active; the DuckDB staging file is 3.86 GB, and the newest writes are SYN-flood pseudo-domain role views. The retry has not exited; prior readiness snapshots taken while it ran are not production verification.
- Named report remediation: `report <experiment>` now verifies persisted source/export artifact identities, execution digest, product presence, and table/figure/evidence hashes rather than invoking render/stat producers. Project-wide report still assembles aggregate tables and figures from outcomes; uncertainty/source-summary lineage for aggregate metric Parquet remains open. Focused architecture/publication/report tests passed (15), Pyright passed (0 errors/warnings), Ruff passed.
- After tightening required metric registration and planned/completed count checks, the focused architecture/docstring/publication/report set passed again: 18 passed, 14 third-party warnings; strict Pyright had 0 errors/warnings and Ruff passed. The refreshed Graphify inventory is unchanged at 5,609 nodes, 17,238 edges, 386 communities, and 1,108 production callables (928 functions, 180 methods).
- CIC status at 2026-09-26 12:31 UTC: worker PID 68647 remains active; 877 files are present under the regenerated CIC prepared-output tree, with recent writes through the SYN-flood and DNS-spoofing pseudo-domain role views. Staging DuckDB remains 3.86 GB. No completion code is present yet.
- The final full suite after the report-verification change passed: 910 passed, 279 third-party warnings, 272.81 seconds. CIC worker PID 68647 resumed automatically after pytest; latest writes are in MITM pseudo-domain views. Production cache verification and an unchanged CIC rerun remain pending.
- Final static checks after all source changes: Ruff lint and format passed; strict Pyright reported 0 errors/warnings; Deptry found no dependency issues (82 files scanned); Import Linter reported 3 kept/0 broken; Vulture at confidence 100 reported no findings.
- CIC continued through pseudo-domains 2–4 after pytest resumed it; at 2026-09-26 12:57 UTC, 1,131 prepared-tree files existed and the newest output was pseudo-domain 4 benign anchor validation. Worker PID 68647 remained active; no completion code was written.
- At 2026-09-26 13:01 UTC, worker 68647 exited 1 with `RuntimeError: Query interrupted` while writing pseudo-domain-4 `DDOS_PSHACK_FLOOD_FINAL_GATE`. The configured dataset preprocessing timeout was 7,200 seconds, matching its two-hour runtime. The partial output tree reached 1,217 files; its failure log and exit code were preserved as `preprocess-cic-timeout-20260926.log` and `.exit`.
- The preparer deletes its temporary DuckDB at each invocation, so no resumable staging checkpoint survives. Increased only the infrastructure timeout in `configs/fedsira.yaml` from 7,200 to 28,800 seconds; the prepared-view cache identity uses the dataset-specific configuration scope and is unaffected. Replacement production worker PID 234969 launched from raw inputs at 13:09 UTC with the standard CLI; log/PID/exit paths remain `preprocess-cic-local-staging-20260926.{log,pid,exit}`.
- At 2026-09-26 13:31 UTC, the replacement worker is active and has passed the pseudo-domain-4 view that timed out. It is now refreshing pseudo-domain-5 views; the prepared tree has 1,489 files. Complete output validation and an unchanged-input reuse run remain pending.
- CICIoT2023 production preprocessing completed at 2026-09-26 14:18 UTC with exit 0: 31 classes, 39 observed predictors (the roadmap explicitly records the 39-versus-46 release-statistics discrepancy), 46,776,700 raw rows, 46,775,660 retained rows, 1,040 excluded rows, 1,674 prepared views, and 780,150 anchor-training rows. Raw manifest hash: `1b03c0af0be9a5a8142205e8496c47ad18a08244b39f2645e3a86361114038a6`. Independent prepared-output verification passed for all 1,674 views: payload SHA-256 and row counts matched sidecars, common schema had 39 predictors, all 7,720,601 prepared sample IDs were unique/non-null and exactly matched the CIC role manifest, with no overlap with excluded rows. Full verification JSON: `prepared-output-ciciot2023-verification-20260926.json`.
- N-BaIoT production refresh completed at 2026-09-26 14:39 UTC with exit 0: 534 prepared views, 320,000 anchor-training rows, no structurally unavailable classes, raw manifest hash `3d43e867f1c28d4d31308e2f90cd871d419f5f36500d112109ea7b06277a8a8b`. The unchanged-input production reuse rerun began at 15:08 UTC; verify `dataset_manifest_reused=true` and sidecar payload hashes before closing preprocessing audit rows.
- N-BaIoT unchanged-input reuse verification completed at 2026-09-26 15:21 UTC with exit 0 and `dataset_manifest_reused=true`. Independent pre/post SHA-256 and nanosecond-mtime comparison found all 534 JSON/Parquet pairs byte-identical; `prepared-output-nbaiot-verification-20260926.json` independently validates all payload checksums, row counts, schema, and sample IDs. Comparison record: `nbaiot-preprocess-rerun-comparison-20260926.json`.
- CICIoT2023 unchanged-input reuse verification began at 2026-09-26 15:22 UTC after capturing SHA-256/mtime baselines for all 1,674 output pairs in `ciciot-preprocess-rerun-baseline-20260926.json`. Worker PID 387257; standard CLI process is rebuilding its staging database. Reuse comparison and combined independent output audit remain pending.
- CICIoT2023 unchanged-input production rerun completed at 15:34 UTC with exit 0 and `dataset_manifest_reused=true`; all 1,674 output pairs retained identical payload/sidecar hashes and modification times. The combined independent audit passed for both datasets: 534 + 1,674 views, 1,569,865 + 7,720,601 rows, 115 + 39 predictors, zero duplicate/null IDs; CIC role manifest IDs exactly match prepared IDs and retained IDs do not overlap 1,040 exclusions. See `ciciot-preprocess-rerun-comparison-20260926.json` and `prepared-output-verification-production-20260926.json`.
- Independent raw inventory verification checked every recorded raw SHA-256 and file size: 89 selected N-BaIoT files (8,140,823,834 bytes) and 309 selected CIC per-attack shards (8,943,771,319 bytes). One N-BaIoT demonstration CSV and 63 alternative labeled/merged CIC CSVs are recorded as unselected. All selected files exactly match their production raw-identity artifacts; details are in `raw-dataset-inventory-verification-20260926.json`.
- Fresh read-only CLI checks after both datasets completed: `doctor` reports valid configuration/environment, both datasets prepared, and zero completed/running experiments; `status` and `plan` show seven pre-core experiments Ready/Not Started and twelve post-core experiments Blocked. Logs: `cli-doctor-production-final.log`, `cli-status-production-final.log`, and `cli-plan-production-final.log`. No experiment was run. The successful CIC invocation leaves a 3.7 GB staging database (no WAL); the next materialization invocation removes it before starting, so it is not a resumable checkpoint.
- The first post-fixture full test suite in session `5051` completed with 915 passed and 6 failed. Failures exposed one repository-root-context regression (five artifact/reuse tests) and two test-only production helpers (one architecture check). The root resolver now follows the active `ApplicationContext.repository_root`; both obsolete helpers and their self-tests were removed. Focused verification passed (91 tests); the final full suite is rerunning in session `37415` (`cd /home/naslouby/Projects/FedSIRA && .venv/bin/pytest -q`). Its output is captured in the Codex terminal session. No scientific experiment was run.

## Safe overwrite audit continuation, 2026-09-26

- After the earlier successful unchanged-input reuse and independent dataset audits above, started a fresh `fedsira preprocess --overwrite` to complete the pre-experiment rerun check. Unified terminal session: `42021`; WSL worker PID: `675555`.
- At the latest check the process remained CPU-active after about 105 minutes, writing CICIoT2023 pseudo-domain 9 temporary prepared views; the configured dataset-preprocessing timeout is 2 hours. This run has not yet returned, so no post-run integrity/reuse claim is made from it.
- The full suite rerun during this overwrite attempt passed 930 tests and failed only the repository-wide Ruff test because `analyze_experiment_paths.py` had unsorted standard-library imports. The import order is corrected and root Ruff/format checks pass. The post-fix full suite will be rerun after preprocessing stops changing prepared outputs.
- The latest matrix validation is 225 PASS / 25 PARTIAL. No experiment was run.

- The overwrite run completed successfully: CICIoT2023 reused its manifest, with 31 classes, 46,776,700 raw rows, 46,775,660 retained, 1,040 excluded, and 1,674 views. The independent verifier passed for both datasets: N-BaIoT 534 views / 1,569,865 rows / 115 predictors; CICIoT2023 1,674 views / 7,720,601 rows / 39 predictors; all sample IDs are unique and non-null, and CIC prepared IDs match the role manifest without overlap with exclusions. Report: `prepared-output-verification-overwrite-20260926.json`.
- Post-overwrite no-`--overwrite` production rerun is active in unified exec session `29720`, WSL worker PID `827543`, logging to `preprocess-overwrite-reuse-20260926.log`. At the latest live check it remained CPU-active; it had logged the N-BaIoT start but not yet its completion. A pre-run SHA-256/mtime baseline for all 534 + 1,674 view pairs is `prepared-output-reuse-baseline-overwrite-20260926.json`. No result is claimed from this pending invocation.
- Continuation update: worker `827543` is confirmed alive and CICIoT2023 is the active dataset. N-BaIoT completed with `dataset_manifest_reused=true` and 534 prepared views. The CIC preparer has opened `outputs/cache/preprocessing/ciciot2023_preparation.duckdb` (about 3.53 GB at the latest check); therefore the final no-overwrite invocation is still staging/validating and no CIC reuse result is claimed yet. Its post-run file-hash/mtime comparison is being deferred until both datasets finish to avoid rescanning prepared files during the CIC run. The home filesystem had about 122 GB free at that check.
- Completion update: session `29720` exited 0. Both N-BaIoT and CICIoT2023 reported `dataset_manifest_reused=true`. `compare_prepared_reuse.audit` streamed every payload and sidecar against the pre-run baseline; all 534 N-BaIoT and 1,674 CICIoT2023 pairs were byte-identical and had unchanged nanosecond mtimes. Report: `prepared-output-reuse-comparison-overwrite-20260926.json`.
- The post-fix full suite completed with 931 passed, 279 upstream warnings, and no skips (326.18 seconds). Doctor, plan, smoke, and status exited 0; smoke passed 32 checks. Project-wide report exited 1 as expected while required comparison evidence is missing, historic schema-2 manifests are obsolete, a prepared-role artifact references an unpublished parent, and persisted comparison evidence has stale statistical configuration. No `fedsira run` or scientific experiment was invoked.

- Completion: session 65398 finished successfully with 935 passed, 279 warnings, no skips, in 325.62 seconds. It predates the typed instance-method regression; schedule the final full suite after current audit edits.


- Final full-suite rerun after the 16-test topology suite update: ........................................................................ [  7%]
........................................................................ [ 15%]
........................................................................ [ 23%]
........................................................................ [ 30%]
........................................................................ [ 38%]
........................................................................ [ 46%]
........................................................................ [ 53%]
........................................................................ [ 61%]
........................................................................ [ 69%]
........................................................................ [ 76%]
........................................................................ [ 84%]
........................................................................ [ 92%]
........................................................................ [100%]
=============================== warnings summary ===============================
.venv/lib/python3.11/site-packages/matplotlib/_fontconfig_pattern.py:64
  /home/naslouby/Projects/FedSIRA/.venv/lib/python3.11/site-packages/matplotlib/_fontconfig_pattern.py:64: PyparsingDeprecationWarning: 'oneOf' deprecated - use 'one_of'
    prop = Group((name + Suppress("=") + comma_separated(value)) | oneOf(_CONSTANTS))

.venv/lib/python3.11/site-packages/matplotlib/_fontconfig_pattern.py:85
.venv/lib/python3.11/site-packages/matplotlib/_fontconfig_pattern.py:85
.venv/lib/python3.11/site-packages/matplotlib/_fontconfig_pattern.py:85
.venv/lib/python3.11/site-packages/matplotlib/_fontconfig_pattern.py:85
.venv/lib/python3.11/site-packages/matplotlib/_fontconfig_pattern.py:85
.venv/lib/python3.11/site-packages/matplotlib/_fontconfig_pattern.py:85
  /home/naslouby/Projects/FedSIRA/.venv/lib/python3.11/site-packages/matplotlib/_fontconfig_pattern.py:85: PyparsingDeprecationWarning: 'parseString' deprecated - use 'parse_string'
    parse = parser.parseString(pattern)

.venv/lib/python3.11/site-packages/matplotlib/_fontconfig_pattern.py:89
.venv/lib/python3.11/site-packages/matplotlib/_fontconfig_pattern.py:89
.venv/lib/python3.11/site-packages/matplotlib/_fontconfig_pattern.py:89
.venv/lib/python3.11/site-packages/matplotlib/_fontconfig_pattern.py:89
.venv/lib/python3.11/site-packages/matplotlib/_fontconfig_pattern.py:89
.venv/lib/python3.11/site-packages/matplotlib/_fontconfig_pattern.py:89
  /home/naslouby/Projects/FedSIRA/.venv/lib/python3.11/site-packages/matplotlib/_fontconfig_pattern.py:89: PyparsingDeprecationWarning: 'resetCache' deprecated - use 'reset_cache'
    parser.resetCache()

.venv/lib/python3.11/site-packages/matplotlib/_mathtext.py:45
  /home/naslouby/Projects/FedSIRA/.venv/lib/python3.11/site-packages/matplotlib/_mathtext.py:45: PyparsingDeprecationWarning: 'enablePackrat' deprecated - use 'enable_packrat'
    ParserElement.enablePackrat()

tests/unit/evaluation/test_score_artifacts.py::test_score_artifact_is_sharded_by_domain_class_and_role
  /home/naslouby/Projects/FedSIRA/.venv/lib/python3.11/site-packages/torch/__init__.py:1551: UserWarning: Please use the new API settings to control TF32 behavior, such as torch.backends.cudnn.conv.fp32_precision = 'tf32' or torch.backends.cuda.matmul.fp32_precision = 'ieee'. Old settings, e.g, torch.backends.cuda.matmul.allow_tf32 = True, torch.backends.cudnn.allow_tf32 = True, allowTF32CuDNN() and allowTF32CuBLAS() will be deprecated after Pytorch 2.9. Please see https://pytorch.org/docs/main/notes/cuda.html#tensorfloat-32-tf32-on-ampere-and-later-devices (Triggered internally at /pytorch/aten/src/ATen/Context.cpp:80.)
    return _C._get_float32_matmul_precision()

tests/unit/learning/test_anchor.py: 80 warnings
tests/unit/learning/test_federated.py: 12 warnings
tests/unit/learning/test_training.py: 40 warnings
  /home/naslouby/Projects/FedSIRA/.venv/lib/python3.11/site-packages/torch/utils/data/_utils/pin_memory.py:57: DeprecationWarning: The argument 'device' of Tensor.pin_memory() is deprecated. Please do not pass this argument. (Triggered internally at /pytorch/aten/src/ATen/native/Memory.cpp:46.)
    return data.pin_memory(device)

tests/unit/learning/test_anchor.py: 80 warnings
tests/unit/learning/test_federated.py: 12 warnings
tests/unit/learning/test_training.py: 40 warnings
  /home/naslouby/Projects/FedSIRA/.venv/lib/python3.11/site-packages/torch/utils/data/_utils/pin_memory.py:57: DeprecationWarning: The argument 'device' of Tensor.is_pinned() is deprecated. Please do not pass this argument. (Triggered internally at /pytorch/aten/src/ATen/native/Memory.cpp:31.)
    return data.pin_memory(device)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
936 passed, 279 warnings in 453.39s (0:07:33), session 98635. Started 2026-09-26; result pending.
