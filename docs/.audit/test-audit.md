# Scientific and workflow test crosswalk

This crosswalk links the current test fixtures to the test-coverage requirements
in `docs/Audit Matrix.md`. It names implementation-level test modules and the
distinct boundary checks they contain. The latest full suite passed 930 tests
in 184.62 seconds with no skipped tests. It emitted 279 upstream
deprecation/runtime warnings. This work includes removal of the
production-only-by-tests `CellPhaseState` enum and `SeedBundle` model, plus the
Pyright-clean topology mutation fixture.

After comparison-definition revalidation, the current protocol, analysis,
reporting, and evaluation unit subsets pass 337 tests with warnings promoted to
errors under the Windows Python 3.14 diagnostic environment. This current
targeted result does not replace the pinned Python 3.11.9 Linux full-suite run.

## TEST-001 — Scientific mathematics

| Contract | Fixture evidence |
|---|---|
| Screen folds, deciles, no-replacement matching, stable ties, and matched differential | `tests/unit/evaluation/test_aggregation.py` (`test_decile_boundaries_and_bin_are_consistent`, `test_match_nearest_within_decile_*`); `tests/unit/protocol/test_screen.py`; `tests/unit/protocol/test_opening.py` (predicate boundary fixtures). |
| Reproduction CE + stability KL + dimension-normalized delta penalty and anchor-relative initialization | `tests/unit/learning/test_post_reference.py` (`test_post_reference_training_step_matches_full_reproduction_objective`, empty-supported and anchor-relative fixtures); `tests/unit/protocol/test_reproduction.py`. |
| Three-valued verification, complete panels, eligibility, commitment ordering, and certification | `tests/unit/protocol/test_verification.py`; `tests/unit/protocol/test_reproduction.py` (`test_validate_commitment_exists_before_verifier_assignment`). |
| Krum admissibility, squared-distance score, neighbor count, direct row selection, deterministic tie break | `tests/unit/protocol/test_theory.py`; `tests/unit/protocol/test_synthesis.py`; `tests/scientific/test_source_artifact_exclusion.py`. |
| Exact diagnostic contamination probability | `tests/unit/protocol/test_theory.py` (`test_diagnostic_at_least_two_byzantine_probability_matches_exact_fraction`, zero-risk cases). |
| Logical expiry and post-evidence delay decomposition | `tests/unit/protocol/test_state_machine.py`; `tests/unit/evaluation/test_records.py`; `tests/unit/experiments/test_state_trajectory.py`. |
| Conjunctive final gate and each individual threshold/invariant failure | `tests/unit/protocol/test_admission.py` (`test_final_gate_predicates_pass_requires_all_four_thresholds_and_no_invariant_failure`, parameterized individual failures); `tests/unit/protocol/test_invariants.py`. |

## TEST-002 — Data invariants

| Contract | Fixture evidence |
|---|---|
| Deterministic role/sample regeneration, half-open intervals, and guard gaps | `tests/unit/datasets/test_common.py`, `tests/unit/datasets/test_roles.py`, `tests/unit/datasets/nbaiot/test_preprocessing.py`, `tests/unit/datasets/ciciot2023/test_preprocessing.py`. |
| Cross-role overlap and target exclusion from anchor roles | `tests/scientific/test_dataset_validation_gate.py`; `tests/unit/datasets/*/test_preprocessing.py`. |
| Scaler fit population, finite/clipped outputs, caps, stable IDs, schema and raw identity | `tests/unit/datasets/nbaiot/test_preprocessing.py::test_materialization_standardized_features_are_finite_and_clipped` asserts scaler training-row count equals the Anchor Train prepared population and that standardized Anchor Train feature means are zero; it also checks finite/clipped values. `tests/unit/datasets/ciciot2023/test_preprocessing.py::test_per_attack_shard_takes_its_class_from_the_directory_token` checks the secondary scaler count against non-target Anchor Train views. Raw identity and role manifests are covered by `tests/unit/datasets/test_preprocessing_artifacts.py`, `test_role_split_manifest.py`, and `test_common.py`. |
| Dataset target/class/domain vocabularies and acquisition identity | `tests/unit/datasets/nbaiot/test_schema.py`, `test_acquisition.py`, `test_validation.py`; `tests/unit/datasets/ciciot2023/test_schema.py`, `test_acquisition.py`, `test_validation.py`. |
| Independent production-output checks | `docs/.audit/verify_prepared_outputs.audit` and current output JSON evidence: all prepared checksums, row counts, schemas, IDs, roles, and retained/excluded disjointness. |

## TEST-003 — Protocol states and guards

| Contract | Fixture evidence |
|---|---|
| Terminal state set, resumable dormancy, configured expiry, and no terminal-state override | `tests/unit/protocol/test_state_machine.py`. |
| Opening transitions for both modes; threshold/insufficient-evidence branches | `tests/unit/protocol/test_opening.py`. |
| Domain consumption, self-exclusion, source-derived checkpoint rejection, commitment-before-verifier ordering | `tests/unit/protocol/test_reproduction.py`, `test_verification.py`, `test_invariants.py`. |
| One vote per domain, full verifier panel, quorum and abstention boundaries | `tests/unit/protocol/test_verification.py`. |
| Synthesis admitted/rejected/dormant branches; final gate prerequisite | `tests/unit/protocol/test_synthesis.py`, `test_admission.py`. |
| Capability contract immutability and production invariants | `tests/unit/protocol/test_invariants.py`, `test_capability_contract.py`. |
| Honest reproduction and source-excluded Krum are invariant to compatible source-artifact changes | `tests/unit/protocol/test_invariants.py::test_source_delta_does_not_change_honest_reproduction_or_source_excluded_krum` varies the source delta, verifies the source commitment changes while honest commitments/updates and selected Krum payload remain identical, calls `krum_input_excludes_source` for the honest committee, and requires synthesis-pending with five honest Krum rows (included in the 158 passed protocol/analysis tests under Windows Python 3.14 with temporary DuckDB/statsmodels and an in-memory `resource` shim; supported Linux rerun pending). |

## TEST-004 — Metrics and statistical rules

| Contract | Fixture evidence |
|---|---|
| Classification/security metrics, direction, undefined denominators, AUROC/AUPRC, evidence minima | `tests/unit/evaluation/test_metrics.py`; domain pooling in `tests/unit/evaluation/test_aggregation.py`. |
| Paired unit/reference identity and minimum complete-pair rule | `tests/unit/evaluation/test_ablation_pairing.py` (`test_inference_requires_nine_of_ten_complete_seed_pairs`, persisted reference fixtures). |
| Exact sign-flip superiority/non-inferiority, Holm ordering/ties/cap | `tests/unit/analysis/test_statistics.py`; independent expected p-value in `tests/scientific/test_statistical_contracts.py`. |
| Required materiality threshold/margin on registered comparisons; copied or mismatched definitions, altered p-values, duplicate comparisons, stale non-inferiority margins, and sidedness mismatch fail closed during Holm adjustment | `tests/unit/analysis/test_comparisons.py` (18 tests pass in the Windows Python 3.14 diagnostic environment; the module is included in the 158 passed protocol/analysis tests; supported Linux rerun pending). |
| Paired standardized effect using sample SD and zero-variance boundaries | `tests/unit/evaluation/test_ablation_pairing.py` (`test_paired_effect_size_uses_sample_standard_deviation_and_handles_zero_variance`). |
| Bootstrap determinism/empty input, type-7 quantiles, domain resampling unit, undefined summaries | `tests/unit/evaluation/test_aggregation.py`. |
| Statistical evidence persistence, freshness, and undefined-versus-zero identity | `tests/unit/evaluation/test_comparison_evidence.py`. |

## Remaining test-coverage actions

TEST-001 through TEST-004 have complete mapped fixtures and pass in the full suite.

| Requirement | Covered today | Remaining gap |
|---|---|---|
| TEST-005 artifact tests | `tests/unit/artifacts/test_storage.py` covers checksum acceptance/rejection, scoped identity, parent/dependency identity, unique staging paths, complete publication, corruption, compatible cross-experiment reuse, and current pointers. Export artifacts store relative product identities as POSIX paths and verify exact published bytes; `test_export_records_products_relative_to_the_experiment_root`, `test_export_currency_flags_a_stale_source_data_identity`, and `test_project_report_source_and_export_artifacts_are_ownerless_and_current` cover this across host path and newline conventions. New fixtures simulate an interrupted manifest publication and changed-dependency pointer promotion while retaining the previous valid artifact. `test_manifest_history.py`, `test_validation.py`, execution retry/reuse tests, publication tests, and report topology checks cover malformed/stale/incomplete evidence and persisted product verification. `test_persisted_experiment_report_verifies_published_products_without_rebuilding` snapshots the full export tree before and after verification. Focused artifact/report verification passed (45); the complete reporting unit directory passed 80 diagnostic tests. Ruff and Pyright are clean. | Closed; see `TEST-005` in the matrix. |
| TEST-006 workflow topology | `tests/architecture/test_workflow_call_topology.py` asserts CLI/application roots, run execution/evaluation/export edges, named-report verification-only behavior, report freshness, all command registrations, and verifier-robustness protocol evidence. `test_workflow_topology_detects_a_removed_required_edge` removes a required call from a synthetic AST and verifies the checker reports the missing edge. The topology and static-typing modules passed 13 tests. | Closed; see `TEST-006` in the matrix. |
| TEST-007 type architecture | Architecture tests inspect enum values, aliases, primitives, generic/Any/dict/object usage, conversion casts, and representative forbidden alias/enum mutations. False-negative review found and fixed quoted forward-reference annotations, qualified built-in primitive types, aliased enum modules, and aliased `StrEnum` bases. Mutation fixtures cover the findings; all 124 architecture tests and strict Pyright pass. | Closed; see `TEST-007` in the matrix. |
| TEST-010 short E2E | `tests/e2e/test_preprocess_plan_smoke.py::test_fixture_preprocess_recovery_reuse_and_safe_cli_chain` executes real fixture preprocessing in a temporary repository, corrupts and repairs a prepared Parquet through the cache-miss fallback, proves a subsequent cache hit bypasses materialization, then runs plan/smoke/status and checks report refusal. `test_run_status_report.py` retains missing/unknown/post-core-blocked run coverage. The E2E suite passes 12 tests in 18.93 seconds without a scientific experiment. | Closed; see `TEST-010` in the matrix and `docs/.audit/e2e-scope-review.md`. |

TEST-005, TEST-006, TEST-007, and TEST-010 are closed by the fixtures above. The `test_no_public_production_symbol_used_only_by_tests` architecture guard passes after removing the unused production enum/model and their test-only fixtures. FIG-006 renderer-specific edge cases remain tracked separately.
