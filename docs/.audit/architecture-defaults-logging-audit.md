# Defaults and logging coverage audit

Current source review for ARCH-009 and ARCH-010. This document records
candidate gaps and does not promote operational defaults to scientific
configuration without evidence. No scientific experiment ran.

## ARCH-009: literal/default inventory scope

`tests/architecture/test_no_hardcoded_values.py` compares numeric source
literals with numeric values loaded from YAML. It does not classify repeated
strings, signature defaults, Pydantic model defaults, `Field` defaults,
mapping fallbacks, or `or`/ternary fallback values. The broader classification
remains incomplete.

Examples found for classification (not automatically defects):

| Source location | Default | Initial interpretation to verify |
|---|---|---|
| `datasets/ciciot2023/prepare.py:742` | `overwrite=False` | Operational API default. |
| `datasets/nbaiot/prepare.py:509-510` | `overwrite=False`, `retain_materialized_views=True` | Operational/storage lifecycle defaults. |
| `datasets/common.py:453` | DuckDB `ignore_errors=False` | Data-integrity default; fail closed. |
| `experiments/planning.py:283` | `resolved_core_complete=False` | Planning prerequisite default. |
| `protocol/baselines/defenses.py` | `counts.get(label, 0)` | Derived tally initialization, not a YAML authority. |

The remaining audit should emit an AST candidate inventory for numeric and
string literals, duplicate literals, function/constructor and Pydantic
defaults, and fallback expressions. Classify candidates as governed config,
roadmap-fixed rule, derived value, domain enum, implementation detail, or
unjustified scientific fallback. Add regression guards only for values that
must not drift or be duplicated.

## ARCH-010: event coverage gaps

Structured logging is present in `runtime.py`, `experiments/execution.py`,
`experiments/engine.py`, `datasets/preprocess.py`, `artifacts/store.py`,
`reporting/export.py`, and anchor-training paths. Current events cover major
start, progress, reuse, phase, completion, and product-generation events.

Coverage is not yet sufficient to close the requirement:

- Cell terminal events now include `FailureDetail.failure_class`, phase, and a
  message bounded to 256 characters. Metric events preserve those fields.
- Timeout events now include the timeout, `Timeout` failure class, protocol
  evaluation phase, and a bounded diagnostic message.
- Some preprocessing, report, and doctor exception/failure branches have no
  consistent structured terminal event.
- Resource logging is not mapped against costly workflow phases.
- The event inventory has not yet been traced through every success, reuse,
  blocked, invalid, and exception branch, and emitted-field tests cover only a
  subset of those branches.

Safe completion work is to build a command/phase/event/field matrix, add
bounded structured terminal events at the remaining failure boundaries, and
test emitted fields for every meaningful terminal path. Logs must remain
operational diagnostics and must not enter scientific artifact identity.
Avoid per-row/sample logging.

Neither row requires a scientific run, but neither is fully audited or
verified yet.
