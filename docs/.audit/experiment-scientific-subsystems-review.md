# Experiment scientific-subsystem review

This review interprets `experiment-scientific-subsystems.csv` against the
registered handler map and Roadmap §§29–30. The CSV is a static reachability
union through the shared `ProtocolCellExecutor`; its counts do not prove that a
workflow consumes a subsystem's required evidence. The analyzer prunes
registered handlers only at the dynamic dispatcher's outgoing edges. It
previously pruned a registered method even when another workflow called it
directly as a shared helper, understating the Byzantine-bound path.

## Deliberate narrow workflows

| Workflow | Expected scope | Review |
|---|---|---|
| Data and Domain Evidence Validation | Prepared data/roles, evidence minima, data validation and reported validation metrics | `_execute_data_and_domain_validation_cell` calls `run_data_and_domain_evidence_validation`; training, proposal, reproduction, synthesis and inference are not part of this prerequisite. |
| Protocol Invariant Validation | Deterministic protocol/state/guard fixtures | `_execute_protocol_invariant_validation_cell` calls `run_protocol_invariant_validation`; it must remain an invariant check, not train models or produce claim statistics. |
| Compromised Verifier Robustness | Existing committed reproduction rows, manipulated verifier reports, certification/admission metrics; no retraining | `_execute_verifier_robustness_cell` now delegates to `_advance_protocol`, which trains and commits the required model-replacement row for false-positive conditions, evaluates assigned panels, records verifier/certificate evidence, and sends certified rows through synthesis and the final gate. Focused dispatch, reproduction, protocol, and architecture tests passed (37). |
| Byzantine Bound Violation | Both reproduced attack branches and verifier-bound branches, with bound-specific certification and admission evidence | `_execute_byzantine_bound_cell` preserves the declared `ScientificCell` and method. Resolved Core verifier conditions use the deterministic exact-count panel and real false-positive reproduction path; Direct Krum conditions use one model-replacement row and Krum without inventing a verifier. Focused regression tests cover both method routes. |

All other registered workflows have nonzero static reachability for the shared
training, protocol, metric, artifact, and report paths. That is only a path
check. It does not substitute for validation of their method/condition-specific
contracts, which remain covered by their own matrix rows and tests.

## Zero-category reconciliation

The regenerated 19 × 15 scientific-subsystem CSV now reaches attacks/baselines,
learning, metrics, reproduction, synthesis, and verification for Byzantine
Bound Violation. The previous zeros were a traversal bug: the reproducer and
verifier robustness methods are both registered experiment handlers and are
also called directly as shared helpers by the bound-violation handler. Those
direct calls must remain in the prospective per-workflow path.

Seven zero-category cells remain. They are the six absent subsystems for Data
and Domain Evidence Validation and the absent proposal/opening subsystem for
Protocol Invariant Validation. Each is individually recorded in
`experiment-scientific-subsystem-zero-review.csv`; each is expected for the
narrow prerequisite or invariant-only workflow. The separate subsystem and
artifact consumer reconciliation remains under WIRE-012/GRAPH-010. Focused
verifier-robustness and Byzantine-bound branch tests cover both attack and
verifier routes. No experiment was executed.

## Disposition

GRAPH-006 passes: all 19 workflows have current reachability rows, and every
zero-category cell has an explicit roadmap-scoped reason. This is a static
route review; it does not claim scientific outcomes were generated or that
artifact-family reconciliation is complete.
