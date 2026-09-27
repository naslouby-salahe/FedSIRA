# Short end-to-end test scope

Ran `.venv/bin/pytest -q tests/e2e --durations=0` on 2026-09-26: 8 passed, 14 upstream warnings, 8.10 seconds total. No scientific experiment ran.

| Test module | Covered path | Observed longest case |
|---|---|---:|
| `tests/e2e/test_preprocess_plan_smoke.py` | CLI doctor against available prepared data, roadmap plan counts, and the 32-invariant smoke suite. It does not invoke production preprocessing or an isolated fixture preprocessing CLI path. | Doctor: 1.98 s; smoke: 1.48 s; plan: 0.15 s. |
| `tests/e2e/test_run_status_report.py` | Missing/unknown/blocked `run` and incomplete `report` refusal. It does not exercise `status` in this module. | Blocked run: 1.85 s; refused report: 0.99 s. |
| `tests/e2e/test_reuse_recovery_overwrite.py` | CLI help exposes `--overwrite` without scientific design overrides. It does not perform artifact reuse, crash recovery, overwrite, or read-only report verification. | 0.02 s. |

Related unit suites exercise actual status rendering, fixture dataset preparation, artifact identity/reuse/corruption/recovery and report verification. They are separate test layers rather than one short workflow integration test. The missing fixture-preprocess-to-plan-to-smoke chain and end-to-end status/reuse/recovery path are why TEST-010 remains partial.
