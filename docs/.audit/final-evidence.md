# Final audit evidence

Last refreshed: 2026-09-26. No scientific experiment or `fedsira run` was invoked.

## Real datasets and raw provenance

The configured primary release is N-BaIoT from the [UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/442/detection+of+iot+botnet+attacks+n+baiot). The configured secondary release is CICIoT2023 from the [Canadian Institute for Cybersecurity](https://www.unb.ca/cic/datasets/iotdataset-2023.html). CIC pseudo-domains are deterministic synthetic partitions and are not described as independent administrative domains.

| Dataset | Raw acquisition selected | Raw bytes selected | Raw manifest hash | Prepared views | Prepared rows | Predictors | Domains | Classes |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| N-BaIoT | 89 CSV files | 8,140,823,834 | `3d43e867f1c28d4d31308e2f90cd871d419f5f36500d112109ea7b06277a8a8b` | 534 | 1,569,865 | 115 | 9 physical-device proxies | 11 |
| CICIoT2023 | 309 per-attack CSV shards | 8,943,771,319 | `1b03c0af0be9a5a8142205e8496c47ad18a08244b39f2645e3a86361114038a6` | 1,674 | 7,720,601 | 39 | 9 synthetic pseudo-domains | 31 |

The independent [raw inventory verification](raw-dataset-inventory-verification-20260926.json) hashes every acquired source file and records its full path and byte size. Its hashes exactly match each production raw-identity artifact. It also records one N-BaIoT demonstration CSV and 63 alternative labeled/merged CIC CSVs as ancillary inputs excluded by the declared acquisition rule. No raw input was changed.

The independent [CIC raw-schema verification](ciciot-raw-schema-verification-20260926.json) checked all 309 selected shards: every ordered header is identical and contains 39 predictor columns. CIC documents a 46-predictor statistics schema; the roadmap explicitly says to record this as a release documentation discrepancy, retain observed numeric columns, and never fabricate absent fields. The selected per-attack release has 46,776,700 raw rows; 46,775,660 were retained and 1,040 structurally excluded. This is the fuller release representation specified by the roadmap.

## Prepared-output validation

The independent [final two-dataset verifier output](prepared-output-verification-final-20260926.json) checks each sidecar and payload: one cache identity per dataset, exact Parquet SHA-256, exact row count, common schema, unique/non-null sample IDs, and per-role/domain/class totals. It also joins all CIC prepared IDs against the stable role manifest and checks retained/excluded disjointness.

| Dataset | Views | Prepared rows | Unique IDs | Duplicate IDs | Null IDs | Role manifest rows | Exclusions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| N-BaIoT | 534 | 1,569,865 | 1,569,865 | 0 | 0 | n/a | n/a |
| CICIoT2023 | 1,674 | 7,720,601 | 7,720,601 | 0 | 0 | 7,720,601 | 1,040 |

The prepared role counts are in the verifier JSON. N-BaIoT counts are: Anchor Train 320,000; Anchor Validation 80,000; Candidate Screen 9,000; Final Gate 34,000; Post-Reference Replay 949,399; Report Test 71,466; Reproduction 36,000; Row Verification 34,000; Source Proposal 36,000. CIC counts are: Anchor Train 780,150; Anchor Validation 194,126; Candidate Screen 9,000; Final Gate 62,915; Post-Reference Replay 6,400,168; Report Test 139,334; Reproduction 36,000; Row Verification 62,908; Source Proposal 36,000.

## Production rerun and cache identity

Both datasets completed an unchanged-input production rerun with `dataset_manifest_reused=true` and exit code 0. Before each rerun, a baseline recorded the SHA-256 and nanosecond modification time of every prepared JSON/Parquet pair. The post-run comparisons found all pairs unchanged:

- N-BaIoT: 534 unchanged pairs; [comparison](nbaiot-preprocess-rerun-comparison-20260926.json); [first production-run verification](prepared-output-nbaiot-verification-20260926.json).
- CICIoT2023: 1,674 unchanged pairs; [comparison](ciciot-preprocess-rerun-comparison-20260926.json); [first production-run verification](prepared-output-ciciot2023-verification-20260926.json).

Each writer checks source/config cache identity, row count, and the sidecar's payload checksum before reuse. Focused stale-input and sidecar regressions passed. Production CLI events and timings are retained in `outputs/preprocessing/logs/preprocessing.log`; artifact publication/reuse events are in `outputs/artifacts/logs/artifacts.log`.

## Safe checks already completed

The earlier full-suite and preprocessing notes in this section are superseded by [the latest verification update](#latest-verification-update-2026-09-26) below. The historical Graphify snapshot remains the current call-inventory source until the final second-pass Graphify regeneration.

## Current gate

Production preprocessing, raw provenance, schema, role/sample identity, no-overlap, output integrity, and the post-overwrite unchanged-input reuse check are verified. Both datasets reported manifest reuse; all 2,208 prepared JSON/Parquet pairs matched the pre-run SHA-256 and modification-time baselines. The latest completed matrix validation reports 227 PASS and 23 PARTIAL requirements. The pre-experiment gate remains **NOT READY** while substantive reporting-lineage, exhaustive workflow/graph classification, and claim-state requirements listed as PARTIAL in `../Audit Matrix.md` remain open. This dataset evidence does not close those findings or authorize scientific execution.

## Latest verification update, 2026-09-26

The last full suite before the latest audit-only topology regressions passed 935 tests with 279 upstream warnings and no skips; the latest topology suite passes 16 tests. The prior full suite passed 936 tests with 279 upstream warnings and no skips. After the latest scientific-helper consolidation, 71 focused evaluation/protocol tests and strict Pyright pass; a new full-suite rerun is pending. Repository-wide Ruff lint and source/test formatting checks passed after correcting the audit-script import order; focused execution tests passed (22), touched-file Ruff/strict Pyright passed, and prior full Pyright, Deptry, Import Linter, and Vulture checks passed. Latest Graphify has 4,126 nodes, 15,944 edges, and 182 communities; its independent source inventory has 1,107 production callables, 1,081 in the CLI union, and 26 outside that union for review. The updated analyzer preserves direct calls to registered handler methods used as shared helpers; the 19 × 15 subsystem matrix was regenerated and its seven zero cells verified against explicit reasons. A producer/source checklist now covers all 16 project tables, 13 mandatory figures, the experiment-owned Cell Metrics table, and the per-experiment artifact specs for all 19 registrations. Current safe CLI checks: doctor, plan, smoke, and status exited 0; smoke passed all 32 invariants. `report` exited 1 because current comparison evidence is missing, historic manifests are obsolete under schema 4, a prepared-role artifact references an unpublished upstream identity, and persisted comparison evidence has stale statistical configuration. No `fedsira run` or scientific experiment was invoked during these checks. The post-overwrite no-overwrite reuse invocation exited 0 with `dataset_manifest_reused=true` for both datasets; all 2,208 prepared view pairs matched pre-run SHA-256 and nanosecond-mtime baselines (`prepared-output-reuse-comparison-overwrite-20260926.json`). The current matrix is 227 PASS / 23 PARTIAL.
