# Fresh Graphify callable inventory — final pass

- Graphify nodes: 4232; edges: 17782; communities: 29.
- Production callables: 1123 (940 functions, 183 class methods by Graphify labels).
- Independent AST inventory: 940 functions, 183 direct class methods, 359 classes.
- Public CLI entry points: 7; 19 experiment registrations map to 17 distinct handlers.
- Dynamic-dispatch check: dispatcher reachable from `run`: True; registered handlers reachable after registry-edge injection: 17/17.
- Source-verified lexical and inherited-mixin method edges absent from Graphify: 63; ledger: `source-verified-method-call-edges.csv`.
- Pydantic validator callbacks dispatched during config loading but omitted by Graphify: 19.
- Typed method/property dispatch edges omitted by Graphify: 235; framework edge classes are in `source-verified-framework-dispatch-edges.csv`.
- Implicit constructor dispatch edges omitted by Graphify: 42; framework edge classes are in `source-verified-framework-dispatch-edges.csv`.
- Graphify omits Typer-to-`FedSIRAApplication` instance-method edges. The analyzer injects the verified CLI/application pairs and registry-resolved protocol handlers under `_execute_cell_protocol()`.
- Reachability follows Graphify `calls` and `indirect_call` edges. Unreachable callables require review; they are not presumed dead code.

## Per-command reachability

| CLI | Direct callees | Unique transitive callables | Shared | Terminal leaves | Maximum acyclic call depth |
|---|---:|---:|---:|---:|---:|
| `doctor` | 1 | 107 | 0 | 49 | 13 |
| `preprocess` | 1 | 890 | 89 | 371 | 24 |
| `plan` | 1 | 71 | 61 | 39 | 8 |
| `smoke` | 1 | 112 | 108 | 65 | 10 |
| `run_experiment` | 1 | 805 | 803 | 344 | 24 |
| `status` | 1 | 85 | 81 | 41 | 10 |
| `report` | 1 | 341 | 167 | 140 | 13 |

## Prospective experiment workflow counts

Each count retains the shared `run` planning/execution path and narrows dynamic handler dispatch to the registered handler. The handlers were analyzed prospectively; no experiment was executed.

| Experiment registration | Unique transitive callables | Terminal leaves | Maximum acyclic call depth |
|---|---:|---:|---:|
| `DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME` | 291 | 121 | 20 |
| `PROTOCOL_INVARIANT_VALIDATION_NAME` | 343 | 150 | 23 |
| `BASELINE_IMPLEMENTATION_VALIDATION_NAME` | 673 | 290 | 29 |
| `PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME` | 564 | 246 | 29 |
| `SINGLE_REPRODUCTION_NECESSITY_NAME` | 560 | 244 | 29 |
| `SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME` | 571 | 252 | 29 |
| `EXTERNAL_VERIFICATION_NECESSITY_NAME` | 559 | 243 | 29 |
| `PRIMARY_CONFIRMATORY_EVALUATION_NAME` | 674 | 290 | 30 |
| `MECHANISM_ABLATION_NAME` | 596 | 259 | 31 |
| `COMPROMISED_REPRODUCER_ROBUSTNESS_NAME` | 561 | 244 | 29 |
| `COMPROMISED_VERIFIER_ROBUSTNESS_NAME` | 562 | 244 | 29 |
| `BYZANTINE_BOUND_VIOLATION_NAME` | 565 | 245 | 30 |
| `EVIDENCE_SCARCITY_AND_DORMANCY_NAME` | 571 | 249 | 29 |
| `SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME` | 593 | 258 | 29 |
| `CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME` | 593 | 258 | 29 |
| `HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME` | 593 | 258 | 29 |
| `ADMISSION_DELAY_DECOMPOSITION_NAME` | 680 | 293 | 30 |
| `EFFICIENCY_MEASUREMENT_NAME` | 693 | 302 | 31 |
| `SECONDARY_DATASET_GENERALIZATION_NAME` | 559 | 243 | 29 |

## Union

- Reachable production callables across all CLI commands: 1102.
- Static graph callables outside the CLI union: 21.
- Outside-union functions: 7; methods: 14.
- Current `indirect_call` edges: 64.
- Additional callables reachable through verified framework/dynamic edges: 1095.
- Unique terminal leaves across the CLI union: 441.
- Prospective experiment paths analyzed: 19.
- Pairwise experiment-path overlaps: 171; complete counts and shared-prefix/tail splits are in `experiment-path-overlaps.csv`.
- Experiment-by-subsystem reachability: 19 registrations × 12 source subsystems; callable counts are in `experiment-subsystem-reachability.csv`.
- Scientific subsystem trace: 19 registrations × 15 reviewed source categories; counts are in `experiment-scientific-subsystems.csv`.
- Largest pairwise shared path: ADMISSION_DELAY_DECOMPOSITION_NAME × BASELINE_IMPLEMENTATION_VALIDATION_NAME (673 callables; 266 shared prefix).
- The unresolved set was checked against decorators, Pydantic model/enum declarations, public registry accessors, and framework dispatch before dead-code disposition.
