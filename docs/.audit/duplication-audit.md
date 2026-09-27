# Formula duplication review

Reviewed on 2026-09-26 against the current Graphify graph and source. This is a
scoped remediation record, not proof that every formula in the repository has
been compared.

## Outcome summary means

Before remediation, `reporting.tables` and `reporting.figures` separately
selected completed outcomes by experiment, method, scenario, and metric, then
calculated their arithmetic mean. The table implementation sorted by seed;
the figure implementation did not. `evaluation.metrics` also contained a
separate arithmetic mean over defined metric results.

`experiments.observations.outcome_metric_values` and
`outcome_metric_mean` now own completed-outcome selection, seed ordering, and
mean calculation for both renderers. `evaluation.statistics.mean_of_defined_values`
owns the defined-value mean used by outcome summaries and class/domain metric
aggregation. Reporting functions no longer contain a competing seed-mean
formula. Tests verify failed outcomes are omitted, seed order is stable,
missing values remain undefined, and renderer outputs remain valid. The focused
observation/metric/report suite passed 67 tests; Ruff and Pyright passed.

The efficiency figure also used NumPy median/linear-quantile calls directly,
while its companion table used `quantile_type7`. The figure now delegates to
the same type-7 implementation. A deterministic fixture verifies the two-stage
rule in Roadmap §30.19: median/IQR over five repetitions for each of three
seeds, followed by median/IQR over the three seed medians. The updated focused
suite passed 68 tests; Ruff and Pyright passed.

## Remaining scope

- Compare all protocol-state, baseline, attack, admission, class/domain,
  comparison, and statistical formulas against the roadmap, including failure
  and undefined-value behavior.
- Compare tests for independent expected-value fixtures rather than copied
  production logic.

ARCH-002 remains PARTIAL until those comparisons are complete. No scientific
formula, configuration, or roadmap threshold was changed in this scoped
remediation.


## Centralized target and benign-FAR metrics

The target-class F1 wrapper is now used in production report-metric construction instead of selecting the target entry separately. The benign false-alarm-rate increase helper now governs deltas across evaluation summaries, screen evidence, protocol admission, baseline outcomes, and experiment handlers. This removes repeated defined/undefined-value handling from those paths. The metric fixture covers positive and undefined inputs; focused metric/protocol suites pass. This is a completed slice, not an exhaustive equivalence audit of every scientific formula.
