# Fresh Graphify callable inventory — final pass

- Graphify nodes: 4131; edges: 15944; communities: 187.
- Production callables: 1107 (925 functions, 182 class methods by Graphify labels).
- Independent AST inventory: 925 functions, 182 direct class methods, 355 classes.
- Public CLI entry points: 7; 19 experiment registrations map to 17 distinct handlers.
- Dynamic-dispatch check: dispatcher reachable from `run`: True; registered handlers reachable after registry-edge injection: 17/17.
- Source-verified lexical and inherited-mixin method edges absent from Graphify: 63; ledger: `source-verified-method-call-edges.csv`.
- Pydantic validator callbacks dispatched during config loading but omitted by Graphify: 19.
- Typed method/property dispatch edges omitted by Graphify: 232; framework edge classes are in `source-verified-framework-dispatch-edges.csv`.
- Implicit constructor dispatch edges omitted by Graphify: 42; framework edge classes are in `source-verified-framework-dispatch-edges.csv`.
- Graphify omits Typer-to-`FedSIRAApplication` instance-method edges. The analyzer injects the verified CLI/application pairs and registry-resolved protocol handlers under `_execute_cell_protocol()`.
- Reachability follows Graphify `calls` and `indirect_call` edges. Unreachable callables require review; they are not presumed dead code.

## Per-command reachability

| CLI | Direct callees | Unique transitive callables | Shared | Terminal leaves | Maximum acyclic call depth |
|---|---:|---:|---:|---:|---:|
| `doctor` | 1 | 107 | 0 | 49 | 13 |
| `preprocess` | 1 | 171 | 42 | 72 | 10 |
| `plan` | 1 | 71 | 61 | 39 | 8 |
| `smoke` | 1 | 112 | 47 | 65 | 10 |
| `run_experiment` | 1 | 874 | 194 | 373 | 24 |
| `status` | 1 | 85 | 81 | 41 | 10 |
| `report` | 1 | 303 | 214 | 128 | 12 |

## Prospective experiment workflow counts

Each count retains the shared `run` planning/execution path and narrows dynamic handler dispatch to the registered handler. The handlers were analyzed prospectively; no experiment was executed.

| Experiment registration | Unique transitive callables | Terminal leaves | Maximum acyclic call depth |
|---|---:|---:|---:|
| `DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME` | 364 | 151 | 20 |
| `PROTOCOL_INVARIANT_VALIDATION_NAME` | 416 | 180 | 23 |
| `BASELINE_IMPLEMENTATION_VALIDATION_NAME` | 742 | 319 | 29 |
| `PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME` | 633 | 275 | 29 |
| `SINGLE_REPRODUCTION_NECESSITY_NAME` | 629 | 273 | 29 |
| `SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME` | 640 | 281 | 29 |
| `EXTERNAL_VERIFICATION_NECESSITY_NAME` | 628 | 272 | 29 |
| `PRIMARY_CONFIRMATORY_EVALUATION_NAME` | 743 | 319 | 30 |
| `MECHANISM_ABLATION_NAME` | 665 | 288 | 31 |
| `COMPROMISED_REPRODUCER_ROBUSTNESS_NAME` | 630 | 273 | 29 |
| `COMPROMISED_VERIFIER_ROBUSTNESS_NAME` | 631 | 273 | 29 |
| `BYZANTINE_BOUND_VIOLATION_NAME` | 634 | 274 | 30 |
| `EVIDENCE_SCARCITY_AND_DORMANCY_NAME` | 640 | 278 | 29 |
| `SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME` | 662 | 287 | 29 |
| `CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME` | 662 | 287 | 29 |
| `HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME` | 662 | 287 | 29 |
| `ADMISSION_DELAY_DECOMPOSITION_NAME` | 749 | 322 | 30 |
| `EFFICIENCY_MEASUREMENT_NAME` | 762 | 331 | 31 |
| `SECONDARY_DATASET_GENERALIZATION_NAME` | 628 | 272 | 29 |

## Union

- Reachable production callables across all CLI commands: 1084.
- Static graph callables outside the CLI union: 23.
- Outside-union functions: 9; methods: 14.
- Current `indirect_call` edges: 56.
- Additional callables reachable through verified framework/dynamic edges: 1077.
- Unique terminal leaves across the CLI union: 437.
- Prospective experiment paths analyzed: 19.
- Pairwise experiment-path overlaps: 171; complete counts and shared-prefix/tail splits are in `experiment-path-overlaps.csv`.
- Experiment-by-subsystem reachability: 19 registrations × 12 source subsystems; callable counts are in `experiment-subsystem-reachability.csv`.
- Scientific subsystem trace: 19 registrations × 15 reviewed source categories; counts are in `experiment-scientific-subsystems.csv`.
- Largest pairwise shared path: ADMISSION_DELAY_DECOMPOSITION_NAME × BASELINE_IMPLEMENTATION_VALIDATION_NAME (742 callables; 339 shared prefix).
- The unresolved set was checked against decorators, Pydantic model/enum declarations, public registry accessors, and framework dispatch before dead-code disposition.
