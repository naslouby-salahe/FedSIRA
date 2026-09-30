# Defaults and logging coverage audit

Current source review for ARCH-009 and ARCH-010. This document records
candidate gaps and does not promote operational defaults to scientific
configuration without evidence. One unintended one-cell data-validation run
occurred through the former preprocess side effect; it produced no model-
performance outcomes and is documented in `final-evidence.md`.

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
| `configs/fedsira.yaml:293` | `execution.data_loader.pin_memory=false` | Operational transfer option is disabled because the current model/training path stays on CPU. |

### Behavior-sensitive boolean defaults reviewed

The generated candidate inventory is at `docs/.audit/architecture-default-candidates.csv`.
Focused caller tracing classifies these behavior-sensitive defaults as explicit
mode selectors or fail-safe defaults, rather than hidden scientific parameters:

| Source location | Default | Classification and evidence |
|---|---|---|
| `experiments/reproduction_progression.py:182` | `include_source_as_first_reproducer=False` | Conservative default; the main handler passes the no-origin-exclusion condition explicitly, while the ablation path intentionally omits it. |
| `protocol/verification.py:54,160` | `allow_source_as_verifier=False` | Fail-safe source exclusion; the main handler opts in only when the no-origin-exclusion condition is active. |
| `experiments/handlers.py:1324` | `opening_resolved=False` | Internal state default; the resolved opening-stage path explicitly passes `True` after resolving its stage. |
| `learning/post_reference.py:490` | `verifier_aware=False` | Training-mode selector; only the verifier-aware reproduction wrapper passes `True`, selecting its configured override. |
| `protocol/baselines/training.py:112` | `exclude_source_from_participants=False` | Baseline API default; recovery-after-source-admission explicitly passes `True` to exclude that source. |
| Dataset materializers | `overwrite=False` | Operational preservation default; caller must opt in to replacing prepared outputs. |
| `datasets/nbaiot/prepare.py:613` | `retain_materialized_views=True` | Output-retention default required by downstream prepared-view consumers; remains explicit storage behavior. |
| `datasets/common.py:453` | `ignore_errors=False` | Integrity-preserving default; malformed CSV rows are not silently discarded. |

These traces close the high-risk boolean subset only. The repeated-string
classification and `Field`-constraint review below are additional completed
subsets. Typed defaults requiring call-site review, conditional fallbacks, and
numeric literals still require broader
semantic classification and any justified regression guards. ARCH-009 remains
PARTIAL.

### Typed model and field defaults

The inventory contains 72 typed model field defaults: 66 `None`, four `0.0`,
and two `True`. The `None` entries broadly represent optional scope, identity,
repetition, evidence, comparison, and diagnostic/log fields. `RootCauseScope`
also has `balanced_selection_seed=None`; its production callers are classified
below. The four zeroes initialize protocol
phase-duration accumulators, and the two `True` values
(`ResolvedCore.final_gate_required` and `.source_excluded`) encode resolved-core
invariants. The remaining typed defaults still need source-level review before
this inventory family can be closed. The 14 Pydantic `Field` constraints are
type/domain invariants: bounded probability and percentage ranges, nonnegative
or positive numeric types, fixed 32-byte digests, the uint32 seed range, and a
`-1` pre-round sentinel. These are validation contracts, not implicit
experiment settings.

### Callable signature defaults

The inventory contains 89 callable signature defaults: 69 `None`, 16 `False`,
one `True`, and three zeroes. The `None` values represent optional typed
context/evidence/scope/report fields; absence remains explicit and does not
select a numeric or method value. `RootCauseScope.balanced_selection_seed=None`
disables balanced row selection in general scope evaluation; the capability-
boundary handler derives and supplies a deterministic seed for the dedicated
balanced certification-rate calculation. The 16 false defaults are opt-in,
fail-closed, or mode-selection flags: the production capability-boundary
caller supplies the contract-scope value, the scoped predicate placeholders
remain false because the actual false-same rate is computed per candidate in
the dedicated handler, and training callers explicitly set
`keep_gradients=True` while inference uses the default. The `True` default
retains N-BaIoT materialized views for downstream readers. The three zeroes
initialize two optional false-certification tallies and the timing-worker
warmup count; the production timing handler supplies its count from
configuration. This classifies the signature-default value families, but the
69 `None` entries still need per-call confirmation; regression coverage and
semantic review of the remaining conditional branches are also needed.

The numeric-valued conditional branches in the inventory were reviewed as a
separate subset. Their `0`/`0.0`/`1`/`1.0` values encode counts, Boolean metric
indicators, empty-denominator display values, and a conservative `p=1` when a
comparison has no defined raw p-value; the `-1` value is the sign selected from
a deterministic digest bit. None is an unconfigured scientific threshold.
The `:memory:` DuckDB branch is used by scratch readers; the production
materializers explicitly supply their disk-backed database path. Repeated
conditional string branches are pass/fail, lifecycle, eligibility, comparison,
and report-state labels. The 77 conditional `None` branches still need
per-call semantic confirmation.

The conditional-`None` subset was then reviewed at the expression level. These
branches preserve absence of a metric, evidence row, selected object, prepared
feature set, report identity, or optional protocol result; none substitutes a
zero, success state, or synthetic value for the absent item. They cluster in
readiness/diagnostic reporting, raw-schema and row selection, metric
availability, optional protocol scope/results, reuse checks, and report
rendering. The rendering paths either preserve `NA`/missing points or have a
separate completeness check. This establishes the absence-preserving value
semantics, but not the complete call-site-to-gate trace required to close
ARCH-009.

### Truthy (`or`) fallbacks

All 11 `or` fallback sites were traced. They canonicalize optional identity
fields when framing hashes or deterministic sort keys, serialize the optional
source-archive digest as an empty component while retaining each raw file's own
digest, or render absent experiment scope as `project`/`project summary` in
artifact dependency labels and diagnostics. Typed experiment identities cannot
be empty strings, so the sort/hash normalization does not conflate a valid
experiment with the project scope. These fallbacks do not choose a scientific
setting, metric, or dataset rule. The `or`-fallback subset is reviewed; its
caller and identity invariants are documented above.

The seven keyword defaults consist of optional comparison selectors and
prerequisite-state mappings, the two fail-closed evidence-verification flags,
`overwrite=False`, and `resolved_core_complete=False`. The single mapping
fallback, `counts.get(label, 0)`, initializes an ensemble-vote tally. These are
classified as optional API scope, fail-closed readiness, preservation, or
derived accumulator behavior. The 77 conditional `None` branches still need
per-call semantic confirmation. The 448 repeated string
occurrences (34 distinct values) are classified below; regression guards remain
necessary if any repeated value is later promoted to a scientific setting or
domain identity.

### Repeated string literals

The 34 distinct repeated strings were reviewed at their source sites. They
classify as encoding/file suffixes (`utf-8`, `.png`, `.json`, `*.json`), SQL and
validator syntax (`SELECT`, `THEN`, Pydantic's `after` mode), separators and
formatting tokens (including `.3f`), Matplotlib style/missing-value markers
(`center`, `offset points`, `o`, `nan`), enum or report labels (`none`, `Within
Bound`), diagnostic prose, and synthetic fixture labels/hash characters (`a`,
`b`). No repeated string was found to carry a hidden scientific threshold,
treatment choice, or dataset rule. The `nan` plot values deliberately preserve
missing registered observations instead of dropping them. This closes the
semantic review of this repeated-string set; preventing accidental future
duplication still needs a targeted guard if a repeated value later becomes a
configuration or domain-identity token.

Current warning cleanup decision: FedSIRA keeps model parameters and batch
tensors on CPU; it does not perform a pinned-host-to-accelerator transfer.
Therefore `execution.data_loader.pin_memory` is now false, avoiding a
deprecated PyTorch internal call with no transfer benefit. The numerical
runtime digest reads the configured modern CUDA/cuDNN `fp32_precision`
properties instead of `torch.get_float32_matmul_precision()`, whose legacy
getter emits a PyTorch deprecation warning. Matplotlib is pinned to 3.10.8 to
avoid the Pyparsing deprecations triggered by the previous 3.9.2 release.
Focused learning, runtime, and figure tests pass with warnings treated as
errors; the complete suite also passes with warnings promoted to errors.
Pyright was advanced to 1.1.414, and its newly surfaced `@contextmanager`
return annotation deprecation was corrected from `Iterator` to `Generator`.

The remaining ARCH-009 obligation is to emit an AST candidate inventory for
numeric and string literals, duplicate literals, function/constructor and
Pydantic defaults, and fallback expressions. Classify candidates as governed
config, roadmap-fixed rule, derived value, domain enum, implementation detail,
or unjustified scientific fallback. Add regression guards only for values
that must not drift or be duplicated.

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
- A typed `workflow.terminal` event now records completed, blocked, and failed
  status, optional failure class, and a 256-character-bounded message for
  doctor readiness, preprocessing completion/failure/timeout, and report
  completion/verification blocking/failure/timeout. The terminal fields remain
  operational and do not enter artifact identity.
- Lower-level preprocessing and report exception branches, process interruption,
  and some doctor failures still need exhaustive boundary tests; unexpected
  exceptions outside the wrapped command paths can still lack a terminal event.
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

## N-BaIoT materialization resource bound

`materialize_nbaiot_prepared_views` accumulates the selected identity and
feature rows in one DuckDB database while processing all discovered CSVs. An
in-memory database grew to 4.4 GB RSS during production materialization, so
the first repair attempt was interrupted before writing prepared views. The
materializer now uses a temporary disk-backed database, directs spill files to
its temporary workspace, and sets DuckDB's buffer-manager limit to 2 GB. A
focused test checks the database path and both settings. Full-data
materialization completed in 82m 46s with 534 views; observed process RSS was
approximately 2.0–2.7 GB. This is an operational resource bound and does not
change the scientific preprocessing contract.

For no-overwrite runs, preprocessing now checks the current raw/configuration
identity, populated role/split manifest, scaler artifact, every view sidecar,
and every Parquet checksum before reuse. A failed check falls back to full
materialization. The production cache check validated all 534 views and
1,569,865 rows; the complete N-BaIoT preprocessing command then completed in
about 10 seconds. This avoids rescanning and recasting the full raw table when
all outputs are already current.

The production preprocessing interruption emitted a terminal failure event
classified as `Implementation Error` with message `Query interrupted`; this
was a deliberate resource-safety interruption during code repair, not a data
validation outcome.

## Comparison threshold fail-closed guard

The candidate review found that `ComparisonTemplate` and
`ComparisonDefinition` allowed a superiority threshold to default to `None`.
`_materiality_passes` then returned `None`, while Holm resolution treated any
value other than `False` as acceptable. This allowed an omitted threshold to
turn a declared superiority comparison into a p-value-only decision.

Superiority templates and definitions now reject missing materiality
thresholds, non-inferiority definitions reject missing margins, and the
superiority result gate requires materiality to be explicitly `True` even if a
model is created through an update path that bypasses validation. The
non-inferiority result path continues to use its declared margin as the
materiality/evidence boundary. `_superiority` also requires the threshold
argument instead of supplying a `None` default. Regression coverage checks
registry completeness, invalid template/definition construction, fail-closed
handling of copied invalid superiority and non-inferiority definitions, and
the non-inferiority path. Holm adjustment revalidates the serialized definition
because Pydantic `model_copy(update=...)` does not rerun validators. It also
checks that sidedness matches the test kind and recomputes the raw p-value from
the current paired differences and margin, rejecting a stale result after a
valid-looking margin change. The family adjustment also checks that each
definition exactly matches the current registered definition, belongs to the
requested family, and appears only once.

Repository-wide Ruff and format checks pass after these changes. The 17
comparison tests and all 337 protocol, analysis, reporting, and evaluation
tests pass with warnings treated as errors in the Windows Python 3.14
diagnostic environment; the supported Python 3.11.9 Linux run is still
pending. ARCH-009 remains open for the unreviewed default families and
complete call-site-to-gate crosswalk.
