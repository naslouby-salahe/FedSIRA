# CLI workflow traces

The seven command roots below are the actual Typer commands registered in
`src/fedsira/cli.py`. Typer passes each command to the same-named
`FedSIRAApplication` method. Counts are in `callable-inventory.md`; Graphify
omits these instance edges and the dynamic protocol-handler edge, so the
inventory injects only the source-verified application and registry routes.
The selection, readiness, lifecycle, reuse, and terminal branches are itemized
in [`workflow-terminal-branches.md`](workflow-terminal-branches.md).

## `doctor`

```text
doctor()
  → FedSIRAApplication.doctor()
    → diagnose()
      → ApplicationContext.load()
      → collect_environment_mismatches()
      → _diagnose_bound()
        → _repository_layout_mismatches()
        → build_plan()
        → dataset_readiness()
        → _artifact_summary()
        → _experiment_summary()
        → _project_stage()
        → _progress_and_action()
    → render()
      → project/artifact/experiment summary renderers
```

Branch: invalid configuration returns a typed blocked `DoctorReport` before
dataset/artifact inspection. Otherwise the report aggregates environment,
dataset, core, and current execution readiness, then renders actionable state.

## `preprocess [dataset] [--overwrite]`

```text
preprocess()
  → FedSIRAApplication.preprocess()
    → execute_preprocess()
      → run_bounded()
        → _execute_bound()
          → for selected DatasetId:
            → _preprocess_nbaiot()
              → discover/validate raw capture files
              → materialize_nbaiot_prepared_views()
                → read/validate captures, assign roles, fit scaler moments,
                  publish scaler, role manifest, parquet views, and sidecars
            → _preprocess_ciciot2023()
              → discover_secondary_csv_files()
              → validate_consistent_header()/resolve_predictor_columns()
              → materialize_ciciot2023_prepared_views()
                → _create_preparation_tables()
                → _ingest_shard() per deterministic shard
                → assign_secondary_roles()
                → _write_secondary_views()
                  → fit_feature_moments()/publish scaler and role manifest
                  → copy_query_to_parquet()/publish view sidecars
              → prepared_view_publication_failures()
```

If no dataset is supplied, `_execute_bound()` iterates the two `DatasetId`
members. The secondary route derives pseudo-domains from the declared shard
semantics and salt, validates actual headers and labels, and publishes
prepared evidence only after view validation.

## `plan`

```text
plan()
  → FedSIRAApplication.plan()
    → execute_plan()
      → read_resolved_core()
      → current seed/config resolution
      → build_plan()
        → experiment definitions and prerequisite-state derivation
        → condition/seed grid construction
        → plan consistency validation
      → render_plan()
```

The plan is prospective; it enumerates registered experiment cells and does not
execute them.

## `smoke [--overwrite]`

```text
smoke()
  → FedSIRAApplication.smoke()
    → execute_smoke()
      → ApplicationContext.load()
      → bound_application_context()
      → configure_deterministic_backend()
      → run_smoke_suite()
        → synthetic protocol/model/artifact invariant fixtures
        → isolated smoke record publication
      → render_smoke()
      → exit nonzero only when SmokeSuiteResult.passed is false
```

Smoke uses its dedicated synthetic fixtures and isolated record; its outputs
are not claim-bearing experiment evidence.

## `run <ExperimentName> [--overwrite]` (prospective only)

```text
run_experiment()
  → FedSIRAApplication.run()
    → execute_run()
      → ApplicationContext.load()/bound_application_context()
      → _execute_bound()
        → build_plan()/select experiment and prerequisite states
        → execute_experiment()
          → validate prerequisites/current artifacts
          → execute_cell_with_retry()
            → ProtocolCellExecutor.execute_cell()
              → _execute_cell_protocol()
                → cell_handler_registration()
                → getattr(self, registered handler name)
                  → one of 17 distinct `_execute_*_cell()` handlers
                    → dataset/model/protocol methods for that experiment
                    → terminal metric methods
        → persist execution records/provenance
        → comparison_results_for_experiment()
        → publish/read comparison evidence
        → _export_completed_experiment() on Completed lifecycle
        → collapse/resolved-core branch when the plan prerequisites qualify
        → render_result()
```

`CELL_HANDLER_REGISTRATIONS` maps 19 experiment identities to the handler
methods listed in `experiment-workflows.md`. Runtime construction validates
identity coverage and handler existence. Per-identity prospective counts are
in `callable-inventory.md`; this audit did not invoke `run`.

Dispatch branches are separated by prerequisite plan state: the four
collapse-experiment handlers produce the decisions needed for core
materialization; only after that current core exists can post-core identities
execute. The common executor also branches on compatible execution-record
reuse versus cell execution/retry, registered handler identity, comparison
expectations, and Completed versus non-Completed export. Full per-identity
family reads/writes are cross-referenced in `artifact-workflow-io.md` and are
still incomplete at the handler-family edge level.

## `status`

```text
status()
  → FedSIRAApplication.status()
    → execute_status()
      → ApplicationContext.load()/bound_application_context()
      → render_status()
        → current_execution_records()
        → dataset_readiness()
        → derive_current_experiment_lifecycle()
        → derive_experiment_lifecycle()
        → status rendering
```

Only execution rows whose configuration, code revision, and prepared dataset
manifest match current provenance contribute to current lifecycle state.

## `report [ExperimentName] [--overwrite]`

```text
report()
  → FedSIRAApplication.report()
    → execute_report()
      → ApplicationContext.load()/bound_application_context()
      → _execute_bound()
        → execute_report(name, overwrite)
          → named branch: verify_persisted_experiment_report()
            → read current per-experiment source-data/export artifacts
            → verify identities, dependencies, checksums and required products
            → return without rendering
          → project branch: verify completeness/artifact/comparison/collapse inputs
            → export_project_summary() only when required claim/evidence gates pass
            → currently gathers project outcomes and computes table/figure summaries
            → verify materialized project products
```

The named branch is read/verify-only. The project branch remains a substantive
gap: there is no current typed project numeric-source artifact, and it still
derives descriptive values from execution outcomes. When the claim gate is
unresolved it refuses before rendering/writing. The completed experiment
renderer is reached from the `run` workflow's `_export_completed_experiment()`
hook, not from the named `report` branch.
