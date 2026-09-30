# Registered experiment workflow map

`build_plan` constructs exactly 19 registered experiment identities. Runtime
dispatch goes through `CELL_HANDLER_REGISTRATIONS` in
`src/fedsira/experiments/handlers.py`; `ProtocolCellExecutor` verifies identity
coverage and method existence before any cell executes.

| Experiment identity | Registered cell handler |
|---|---|
| Data and Domain Evidence Validation | `_execute_data_and_domain_validation_cell` |
| Protocol Invariant Validation | `_execute_protocol_invariant_validation_cell` |
| Baseline Implementation Validation | `_execute_baseline_cell` |
| Proposal-Assisted Opening Necessity | `_execute_opening_cell` |
| Single-Reproduction Necessity | `_execute_plurality_cell` |
| Source-Artifact Exclusion Necessity | `_execute_source_exclusion_cell` |
| External Verification Necessity | `_execute_external_verification_cell` |
| Primary Confirmatory Evaluation | `_execute_primary_cell` |
| Mechanism Ablation | `_execute_ablation_cell` |
| Compromised Reproducer Robustness | `_execute_reproducer_robustness_cell` |
| Compromised Verifier Robustness | `_execute_verifier_robustness_cell` |
| Byzantine Bound Violation | `_execute_byzantine_bound_cell` |
| Evidence Scarcity and Dormancy | `_execute_evidence_scarcity_cell` |
| Shared Epistemic Failure Boundary | `_execute_boundary_cell` |
| Capability Under-Specification Boundary | `_execute_boundary_cell` |
| Heterogeneous Reproduction Boundary | `_execute_boundary_cell` |
| Admission-Delay Decomposition | `_execute_admission_delay_cell` |
| Efficiency Measurement | `_execute_efficiency_cell` |
| Secondary-Dataset Generalization | `_execute_secondary_cell` |

The registry shares a single boundary handler for three boundary identities;
all other registered identities have their own named handlers. The primary
source-excluded protocol proceeds through `_advance_protocol`, reproduction
and certification, robust synthesis, and `_final_gate_outcome`; experiment
handlers then compute their declared metrics. The secondary generalization
handler uses the secondary dataset adapter and pseudo-domains.

The grid and execution plan were verified with `fedsira plan`: 299 pre-core
cells and 1,690 post-core cells, 1,989 total. All 19 workflow registrations
were inspected. No registered experiment was executed by this audit.
## Per-experiment prospective CLI-to-leaf workflows

Each path starts with the shared `run` prefix in `cli-workflows.md`, then uses
the registered handler and deepest reachable production leaf in the current
Graphify graph. Counts include unique handler descendants and terminal leaves;
dynamic dispatch is resolved through the validated registry. No experiment ran.

| Experiment | Handler | Unique handler descendants | Terminal leaves | Deepest handler path |
|---|---|---:|---:|---|
| Data and Domain Evidence Validation | `_execute_data_and_domain_validation_cell` | 27 | 13 | `._execute_data_and_domain_validation_cell → run_data_and_domain_evidence_validation → _data_invariants → assign_stream_roles_and_sample_ids → supported_class_sampling_caps → sampling_cap_for_role → _supported_sampling_cap` |
| Protocol Invariant Validation | `_execute_protocol_invariant_validation_cell` | 93 | 49 | `._execute_protocol_invariant_validation_cell → run_protocol_invariant_validation → run_smoke_suite → _data_invariants → assign_stream_roles_and_sample_ids → supported_class_sampling_caps → sampling_cap_for_role → _supported_sampling_cap` |
| Baseline Implementation Validation | `_execute_baseline_cell` | 447 | 200 | `._execute_baseline_cell → ._centralized_reference_outcome → train_centralized_reference_checkpoint → train_one_client_locally → train_epochs_with_deterministic_batch_order → build_epoch_batches → .__init__` |
| Proposal-Assisted Opening Necessity | `_execute_opening_cell` | 338 | 156 | `._execute_opening_cell → ._advance_protocol → .real_anchor → train_anchor → run_anchor_fedavg_training → run_fedavg_round → train_one_client_locally → train_epochs_with_deterministic_batch_order → build_epoch_batches → .__init__` |
| Single-Reproduction Necessity | `_execute_plurality_cell` | 334 | 154 | `._execute_plurality_cell → ._advance_protocol → .real_anchor → train_anchor → run_anchor_fedavg_training → run_fedavg_round → train_one_client_locally → train_epochs_with_deterministic_batch_order → build_epoch_batches → .__init__` |
| Source-Artifact Exclusion Necessity | `_execute_source_exclusion_cell` | 345 | 162 | `._execute_source_exclusion_cell → .real_anchor → train_anchor → run_anchor_fedavg_training → run_fedavg_round → train_one_client_locally → train_epochs_with_deterministic_batch_order → build_epoch_batches → .__init__` |
| External Verification Necessity | `_execute_external_verification_cell` | 333 | 153 | `._execute_external_verification_cell → ._advance_protocol → .real_anchor → train_anchor → run_anchor_fedavg_training → run_fedavg_round → train_one_client_locally → train_epochs_with_deterministic_batch_order → build_epoch_batches → .__init__` |
| Primary Confirmatory Evaluation | `_execute_primary_cell` | 448 | 200 | `._execute_primary_cell → ._execute_baseline_cell → ._centralized_reference_outcome → train_centralized_reference_checkpoint → train_one_client_locally → train_epochs_with_deterministic_batch_order → build_epoch_batches → .__init__` |
| Mechanism Ablation | `_execute_ablation_cell` | 371 | 170 | `._execute_ablation_cell → .real_anchor → train_anchor → run_anchor_fedavg_training → run_fedavg_round → train_one_client_locally → train_epochs_with_deterministic_batch_order → build_epoch_batches → .__init__` |
| Compromised-Reproducer Robustness | `_execute_reproducer_robustness_cell` | 336 | 155 | `._execute_reproducer_robustness_cell → .real_anchor → train_anchor → run_anchor_fedavg_training → run_fedavg_round → train_one_client_locally → train_epochs_with_deterministic_batch_order → build_epoch_batches → .__init__` |
| Compromised-Verifier Robustness | `_execute_verifier_robustness_cell` | 336 | 154 | `._execute_verifier_robustness_cell → ._advance_protocol → .real_anchor → train_anchor → run_anchor_fedavg_training → run_fedavg_round → train_one_client_locally → train_epochs_with_deterministic_batch_order → build_epoch_batches → .__init__` |
| Byzantine-Bound Violation | `_execute_byzantine_bound_cell` | 340 | 156 | `._execute_byzantine_bound_cell → ._execute_reproducer_robustness_cell → .real_anchor → train_anchor → run_anchor_fedavg_training → run_fedavg_round → train_one_client_locally → train_epochs_with_deterministic_batch_order → build_epoch_batches → .__init__` |
| Evidence Scarcity and Dormancy | `_execute_evidence_scarcity_cell` | 345 | 159 | `._execute_evidence_scarcity_cell → ._advance_protocol → .real_anchor → train_anchor → run_anchor_fedavg_training → run_fedavg_round → train_one_client_locally → train_epochs_with_deterministic_batch_order → build_epoch_batches → .__init__` |
| Shared Epistemic-Failure Boundary | `_execute_boundary_cell` | 367 | 168 | `._execute_boundary_cell → compute_capability_under_specification_summary → train_domain_reproduction_delta → _train_post_reference_delta → run_post_reference_training → post_reference_training_step → compute_stability_kl → probabilities_for_samples` |
| Capability Under-Specification Boundary | `_execute_boundary_cell` | 367 | 168 | `._execute_boundary_cell → compute_capability_under_specification_summary → train_domain_reproduction_delta → _train_post_reference_delta → run_post_reference_training → post_reference_training_step → compute_stability_kl → probabilities_for_samples` |
| Heterogeneous-Reproduction Boundary | `_execute_boundary_cell` | 367 | 168 | `._execute_boundary_cell → compute_capability_under_specification_summary → train_domain_reproduction_delta → _train_post_reference_delta → run_post_reference_training → post_reference_training_step → compute_stability_kl → probabilities_for_samples` |
| Admission-Delay Decomposition | `_execute_admission_delay_cell` | 454 | 203 | `._execute_admission_delay_cell → ._execute_baseline_cell → ._centralized_reference_outcome → train_centralized_reference_checkpoint → train_one_client_locally → train_epochs_with_deterministic_batch_order → build_epoch_batches → .__init__` |
| Efficiency Measurement | `_execute_efficiency_cell` | 468 | 213 | `._execute_efficiency_cell → ._execute_baseline_cell → ._centralized_reference_outcome → train_centralized_reference_checkpoint → train_one_client_locally → train_epochs_with_deterministic_batch_order → build_epoch_batches → .__init__` |
| Secondary-Dataset Generalization | `_execute_secondary_cell` | 333 | 153 | `._execute_secondary_cell → ._advance_protocol → .real_anchor → train_anchor → run_anchor_fedavg_training → run_fedavg_round → train_one_client_locally → train_epochs_with_deterministic_batch_order → build_epoch_batches → .__init__` |
