# Graph Report - FedSIRA  (2026-09-26)

## Corpus Check
- 290 files · ~334,298 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 32 file(s) not represented in the graph (top: .exit 10, .audit 8, .csv 8)

## Summary
- 4131 nodes · 15944 edges · 187 communities (143 shown, 44 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 3038 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9449c601`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- defenses.py
- protocol/test_verification.py
- test_training.py
- CertifiedReproductionRow
- preprocess.py
- framed_bytes
- AdmissionState
- figures.py
- FedSIRAClassifier
- comparisons.py
- ciciot2023/prepare.py
- CellExecutionOutcome
- metrics.py
- enums.py
- export.py
- store.py
- TernaryOutcome
- current_application_context
- checkpoints.py
- execution.py
- FrozenDomainModel
- collapse.py
- paths.py
- handlers.py
- reporting/verification.py
- test_enums.py
- test_capability_contract.py
- test_experiment_registry_contracts.py
- report_metric_set
- config.py
- _SteppableOptimizer
- DatasetId
- TimingWorkerResult
- MetricResult
- pathlib
- SamplingCapsPerDomain
- ExperimentName
- model_validator
- parse
- publish_prepared_role_view
- Roadmap.md
- test_metrics.py
- 17.1 Classification metrics
- materialize_ciciot2023_prepared_views
- CommunicationMessageMetadata
- current_repository_root
- .values
- test_common.py
- rules.py
- test_no_primitive_leaks.py
- ArtifactFamily
- BoundCondition
- iter_python_files
- ExperimentLifecycleState
- observations.py
- 18. Statistical analysis protocol
- ast
- nbaiot_adapter
- protocol/test_reproduction.py
- test_no_any_dict_object.py
- ciciot2023/test_acquisition.py
- 16.5 Baseline implementation completion rules
- FedSIRAApplication
- AdmissionOpeningMode
- 35.2 Exact claim rules
- test_no_hardcoded_values.py
- current_comparison_evidence
- fit_feature_moments
- artifact-workflow-io.md
- 5. Core Engineering Rules
- 30. Experiment registry
- 33.2 Result tables
- load_scientific_config
- discover_primary_csv_files
- Pre-experiment audit progress
- nbaiot/prepare.py
- planning.py
- test_determinism.py
- test_workflow_call_topology.py
- 15. Adversarial and diagnostic transformation registry
- load_published_manifests
- exact_sign_flip_two_sided_p_value
- 18.9 Exact comparison registry
- 17.2 Capability Contract metrics
- reproduction_progression
- test_no_comments_or_docstrings.py
- ciciot2023/schema.py
- application.py
- DormantOrigin
- _train_post_reference_delta
- boundary_metric_set
- 34. Required manuscript figures
- synthesis.py
- ProtocolCellExecutor
- models.py
- select_source_domain
- 4. Audit requirements
- test_no_free_string_enum_bypass.py
- .run
- commitment_digest
- CommunicationMessageType
- test_dataset_subsystem.py
- independent_local_reference_reviewer_is_positive
- NBaiotClass
- pytest
- 17. Metric registry and mathematical definitions
- cli.py
- 7. Exact FedSIRA procedure
- 8. Theory and proof obligations
- reproduction_progression.py
- runtime.py
- test_enum_integrity.py
- test_no_redirects_shims_reexports.py
- Final audit evidence
- Defaults and logging coverage audit
- FedSIRA Pre-Experiment Audit Matrix
- verify_report_export_currency
- test_config_as_parameter.py
- evaluation/test_validation.py
- 24. Public CLI contract
- test_public_type_boundaries.py
- test_certified_ensemble.py
- 9. Primary dataset and experimental domain construction
- test_run_status_report.py
- AblationScenario
- test_commands.py
- auprc_one_vs_rest
- test_invariants.py
- 12. Model, anchor training, source training, and reproduction training
- 26. Scientific output contract
- 28. Validation and smoke-test contract
- background-jobs.md
- 4. Threat model, trust assumptions, and explicit boundaries
- 1. Scientific problem, contribution boundary, and claims
- 13. Role assignment, seeds, security profiles, and deterministic ties
- 10. Exact data roles, sampling, and preprocessing
- 6. FedSIRA state machine and non-negotiable invariants
- FedSIRA
- fraction_to_attack_count
- malicious_admission_rate
- test_robust_aggregation.py
- AGENTS.md
- claim-evidence-map.md
- library-audit.md
- fedsira
- Formula duplication review
- .__init__
- test_model_replacement_requires_at_least_one_configured_carrier_row
- reproduction_attempt_count
- _ListConvertibleTensor

## God Nodes (most connected - your core abstractions)
1. `current_application_context()` - 225 edges
2. `FrozenDomainModel` - 201 edges
3. `ExperimentName` - 189 edges
4. `AdmissionState` - 172 edges
5. `ScientificCell` - 144 edges
6. `MetricResult` - 143 edges
7. `DatasetId` - 128 edges
8. `ExperimentLifecycleState` - 121 edges
9. `ArtifactFamily` - 103 edges
10. `ProtocolCellDispatch` - 99 edges

## Surprising Connections (you probably didn't know these)
- ``doctor`` --references--> `DoctorReport`  [INFERRED]
  docs/.audit/cli-workflows.md → src/fedsira/application.py
- `Per-command reachability` --references--> `run_experiment()`  [INFERRED]
  docs/.audit/callable-inventory.md → src/fedsira/cli.py
- `2026-09-26 continuation` --references--> `_assign_secondary_roles()`  [INFERRED]
  docs/.audit/background-jobs.md → src/fedsira/datasets/ciciot2023/prepare.py
- `17.7 Efficiency and communication metrics` --references--> `dataset_manifest_hash()`  [INFERRED]
  docs/Roadmap.md → src/fedsira/datasets/common.py
- ``preprocess [dataset] [--overwrite]`` --references--> `DatasetId`  [INFERRED]
  docs/.audit/cli-workflows.md → src/fedsira/domain/enums.py

## Import Cycles
- 3-file cycle: `src/fedsira/evaluation/comparison_evidence.py -> src/fedsira/experiments/engine.py -> src/fedsira/experiments/execution.py -> src/fedsira/evaluation/comparison_evidence.py`
- 3-file cycle: `src/fedsira/experiments/collapse.py -> src/fedsira/experiments/engine.py -> src/fedsira/experiments/execution.py -> src/fedsira/experiments/collapse.py`

## Communities (187 total, 44 thin omitted)

### Community 0 - "defenses.py"
Cohesion: 0.05
Nodes (81): GroupCount, GroupIndex, PairwiseDistanceMatrix, SourceIsProductionUpdate, dataset_manifest_hash(), DomainTargetMetrics, ReviewPanelProfile, certified_ensemble_domain_groups() (+73 more)

### Community 1 - "protocol/test_verification.py"
Cohesion: 0.09
Nodes (25): AllowSourceAsVerifier, MonotonicTimestamp, ByzantineDomainCount, ObservedPositiveReportCount, ResolvedRowRequirementReached, VerifierReportCount, select_compromised_verifiers(), verification_pending_transition() (+17 more)

### Community 2 - "test_training.py"
Cohesion: 0.13
Nodes (31): BatchRowIndexSequence, BatchSize, DataLoader, build_epoch_batches(), DeclaredBatchDataset, ordered_batch_indices(), ordered_batch_row_indices(), ordered_minibatches() (+23 more)

### Community 3 - "CertifiedReproductionRow"
Cohesion: 0.25
Nodes (28): CalibrationErrorCount, ClusterSize, DbscanEpsilon, MemberIndex, NumericalEpsilon, OptionalParameterSimilarity, PairwiseDistance, ParameterSimilarityCertified (+20 more)

### Community 4 - "preprocess.py"
Cohesion: 0.10
Nodes (40): Audit findings, FrameType, Logger, logging, LogRecord, OperationResult, RuntimeError, prepared_evidence_root() (+32 more)

### Community 5 - "framed_bytes"
Cohesion: 0.12
Nodes (34): contextlib, contextvars, FramedBytes, ScoringTransformName, artifact_instance_token(), ArtifactInstanceName, ArtifactInstanceToken, FramingField (+26 more)

### Community 6 - "AdmissionState"
Cohesion: 0.11
Nodes (31): CompromisedProductionAncestry, DiscardSourceWeights, Deliberate narrow workflows, Per-experiment prospective CLI-to-leaf workflows, Registered experiment workflow map, LegitimateAdmissionEligible, AdmissionState, PreparedEvidenceCounts (+23 more)

### Community 7 - "figures.py"
Cohesion: 0.09
Nodes (70): Axes, AxisDraw, BoundarySeries, FigureAnnotationText, FigureAxisLabel, FigureLegendText, matplotlib_axes, FigureAxisName (+62 more)

### Community 8 - "FedSIRAClassifier"
Cohesion: 0.04
Nodes (132): EvaluationCadenceReached, AnchorFedAvgConfig, OptimizerConfig, PostReferenceConfig, TrainingConfig, _model_invariants(), anchor_round_is_evaluated(), anchor_round_participants() (+124 more)

### Community 9 - "comparisons.py"
Cohesion: 0.10
Nodes (63): ComparisonReferenceLabel, MaterialityDecision, MultiplicityConfig, ComparisonMetric, PrimaryScenario, _ablation_comparisons(), ablation_material_threshold(), ablation_metric() (+55 more)

### Community 10 - "ciciot2023/prepare.py"
Cohesion: 0.10
Nodes (52): DatasetColumnCount, FeatureMoment, FeatureName, PartitionSalt, _assign_secondary_roles(), _cached_view_is_reusable(), _cap_case_sql(), CICIoTPreparedViewMetadata (+44 more)

### Community 11 - "CellExecutionOutcome"
Cohesion: 0.11
Nodes (55): CellCompletionStatus, matplotlib_figure, CoreMethodIdentity, CellExecutionOutcome, ExperimentExecutionResult, ExperimentReportSummary, export_experiment_report(), RelativePathText (+47 more)

### Community 12 - "metrics.py"
Cohesion: 0.07
Nodes (68): collections_abc, FeatureShiftSign, KeepGradients, PreparedEvidencePresent, ReproductionOpportunityCount, sklearn_metrics, apply_attacker_induced_common_context(), apply_root_cause_feature_shift() (+60 more)

### Community 13 - "enums.py"
Cohesion: 0.08
Nodes (62): ArtifactFileName, FeatureShiftMagnitude, AblationVariant, ArtifactFamilyDirectoryToken, ArtifactFileToken, BaselineIdentity, ByteUnit, CublasWorkspaceConfig (+54 more)

### Community 14 - "export.py"
Cohesion: 0.07
Nodes (103): FormattedStatisticText, specification(), dataset_specification(), DatasetSpecification, prepared_domain_summaries(), prepared_view_digest(), PreparedDomainSummary, ReportCellLiteral (+95 more)

### Community 15 - "store.py"
Cohesion: 0.09
Nodes (55): ArtifactComplete, ArtifactPayloadBytes, ArtifactSerializedText, PreparedReproductionTargetCount, PreparedSupportedReplayCount, SmokeRenderText, ArtifactCurrentPointer, ArtifactLogFields (+47 more)

### Community 16 - "TernaryOutcome"
Cohesion: 0.06
Nodes (41): AtLeastTwoByzantineProbability, CompletionCycleIndex, EligiblePoolSize, EvidenceArrivalCycleIndex, fractions, KrumCommitteeAdmissible, MaximumByzantineReportCount, MinimumHonestPositiveReportCount (+33 more)

### Community 17 - "current_application_context"
Cohesion: 0.08
Nodes (76): SourceAvailable, flat_parameters_identity(), RealAnchor, supported_replay_cap_for_target_role(), AlgorithmName, non_source_domains(), declared_contract_scopes(), ArtifactDigest (+68 more)

### Community 18 - "checkpoints.py"
Cohesion: 0.13
Nodes (25): CheckpointStageIdentity, checkpoint_procedure_identity(), checkpoint_producer(), checkpoint_slot(), checkpoint_stage_instance(), CheckpointPayload, publish_anchor_checkpoints(), publish_checkpoint() (+17 more)

### Community 19 - "execution.py"
Cohesion: 0.11
Nodes (40): Repository path ownership review, Root owners, Static inventory, json, configuration_digest(), CodeRevision, repository_revision(), SmokeCheckName (+32 more)

### Community 20 - "FrozenDomainModel"
Cohesion: 0.11
Nodes (61): Artifact dependency and invalidation matrix, Production callables outside the prospective CLI union, Percentile, artifact_staging_root(), ArtifactConfigurationComponent, ArtifactConfigurationScope, ArtifactDependency, configuration_scope_dependency() (+53 more)

### Community 21 - "collapse.py"
Cohesion: 0.08
Nodes (61): enum, MinimumCompletePairCount, ResolvedCoreIdentity, ComparisonFamily, ResolvedCoreDecisionToken, ComparisonState, _best_passed_metric(), _collapse_comparator() (+53 more)

### Community 22 - "paths.py"
Cohesion: 0.09
Nodes (58): artifact_log_path(), artifact_publication_root(), execution_outputs_root(), execution_workspace_root(), experiment_execution_root(), experiment_log_path(), experiment_metrics_root(), experiment_repetition_telemetry_root() (+50 more)

### Community 23 - "handlers.py"
Cohesion: 0.04
Nodes (106): ClassCount, collections, dataclasses, 10.5 Scaling, FeatureSchemaDigest, HeterogeneityMultiplier, OneVotePerDomain, OrderItem (+98 more)

### Community 24 - "reporting/verification.py"
Cohesion: 0.19
Nodes (23): _execute_bound(), OverwriteExisting, evidence_trajectory(), CompletenessVerificationResult, ExperimentLifecycleRecord, ExperimentTerminalCount, _lifecycle_state(), metric_artifact_is_semantically_complete() (+15 more)

### Community 25 - "test_enums.py"
Cohesion: 0.25
Nodes (7): test_artifact_lifecycle_state_members(), test_dataset_id_has_exactly_the_two_roadmap_datasets(), test_enum_members_are_not_equal_to_plain_strings_by_construction(), test_experiment_lifecycle_state_members(), test_failure_class_has_exactly_nine_classes(), test_scientific_cell_phase_has_exactly_six_phases(), test_seed_derivation_label_retains_the_fifteen_namespace_tokens()

### Community 26 - "test_capability_contract.py"
Cohesion: 0.15
Nodes (19): ProductionWeight, EvidenceMinimaConfig, EvidenceAdequate, ExampleCount, screen_evidence_is_adequate(), validate_source_excluded_production_weight(), verification_evidence_is_adequate(), _contract() (+11 more)

### Community 27 - "test_experiment_registry_contracts.py"
Cohesion: 0.11
Nodes (20): experiment_names(), experiment_registry(), efficiency_repetition_indices(), RepetitionIndex, _rendered_table_names(), test_efficiency_repetitions_follow_the_configured_count(), test_every_ablation_variant_is_dispatched_explicitly(), test_every_experiment_declares_a_known_dataset() (+12 more)

### Community 28 - "report_metric_set"
Cohesion: 0.19
Nodes (23): OptionalTriggeredSampleMaskSeries, ConfusionCounts, compute_confusion_counts(), compute_confusion_counts_by_class(), f1_for_class(), false_negative_rate_for_class(), false_positive_rate_for_class(), macro_auprc() (+15 more)

### Community 29 - "config.py"
Cohesion: 0.07
Nodes (53): RoleBoundary, RoleInterval, AdmissionOpeningConfig, AttackerInducedCommonContextConfig, AttacksAndBoundariesConfig, BaselinesConfig, BootstrapConfig, ByzantineOperatingRegionConfig (+45 more)

### Community 31 - "DatasetId"
Cohesion: 0.22
Nodes (22): dataset_preprocessing_configuration(), prepared_view_cache_identity(), publish_role_split_sample_manifest(), ArtifactDigest, ArtifactReuseDecision, DatasetManifestDigest, role_split_sample_manifest(), role_split_sample_manifest_slot() (+14 more)

### Community 32 - "TimingWorkerResult"
Cohesion: 0.12
Nodes (15): PeakMemoryBytes, TimingWorkerObservation, CudaIntervalTimer, ElapsedTimer, peak_gpu_memory_bytes(), peak_host_resident_set_bytes(), WallClockSeconds, reset_peak_gpu_memory_counter() (+7 more)

### Community 33 - "MetricResult"
Cohesion: 0.04
Nodes (116): ClassIndex, ConfidenceIntervalBound, DecileBinIndex, TEST-001 — Scientific mathematics, FinalGateArtifactValid, itertools, MatchedControlCount, math (+108 more)

### Community 34 - "pathlib"
Cohesion: 0.08
Nodes (29): main(), run_worker(), main(), run_worker(), os, pathlib, subprocess, sys (+21 more)

### Community 35 - "SamplingCapsPerDomain"
Cohesion: 0.15
Nodes (19): DatasetFileDigest, Dataset adapter equivalence review, SamplingSelectionDigest, SourceRowIndex, SamplingCapsPerDomain, apply_sampling_cap(), BooleanValue, ClassLabel (+11 more)

### Community 36 - "ExperimentName"
Cohesion: 0.10
Nodes (43): ExperimentName, experiment_by_name(), ExecutionProvenance, ExecutionRecordStore, PersistedExecutionRecord, prerequisite_states_from_store(), Path, ScientificCellSemanticKey (+35 more)

### Community 37 - "model_validator"
Cohesion: 0.17
Nodes (5): FinalGateConfig, model_validator, SeedCount, Self, SeedsAndDeterminismConfig

### Community 38 - "parse"
Cohesion: 0.13
Nodes (36): _alias_bases(), _enum_class_names(), _enum_loop_variables(), _enum_member_unwrap(), enum_value_access_violations(), enum_value_in_comparison_violations(), forbidden_alias_symbol_violations(), expr (+28 more)

### Community 39 - "publish_prepared_role_view"
Cohesion: 0.12
Nodes (31): hashlib, PreparedRoleViewManifest, PreparedViewSidecar, PreparedViewKey, view_parquet_path(), _parquet_checksum(), prepared_view_publication_failures(), ArtifactDigest (+23 more)

### Community 40 - "Roadmap.md"
Cohesion: 0.06
Nodes (31): 11.1 Secondary schema, labels, and raw-data adaptation, 11.2 Secondary domain proxies, 11.3 Secondary roles, 11. Secondary generalization dataset, 14. Final-gate and admission artifact semantics, 19.1 Scientific cell-phase boundaries, 19. Failure, null-result, and completion semantics, 20. Reference software and hardware environment (+23 more)

### Community 41 - "test_metrics.py"
Cohesion: 0.10
Nodes (26): AdmissionCount, CleanOracleDegradationMaterial, ProposalOracleLabel, accuracy(), attack_success_rate_within_domain(), benign_false_alarm_rate(), clean_oracle_degradation_is_material(), clean_proposal_oracle_label() (+18 more)

### Community 42 - "17.1 Classification metrics"
Cohesion: 0.14
Nodes (14): 17.1 Classification metrics, Accuracy, AUPRC, AUROC, Balanced Accuracy, F1 for class $c$, False-negative rate, False-positive rate (+6 more)

### Community 43 - "materialize_ciciot2023_prepared_views"
Cohesion: 0.19
Nodes (34): IntEnum, assign_secondary_roles(), compute_dataset_manifest_hash(), materialize_ciciot2023_prepared_views(), resolve_predictor_columns(), resolve_row_identifier_columns(), SecondaryCsvFile, CICIoT2023PseudoDomain (+26 more)

### Community 44 - "CommunicationMessageMetadata"
Cohesion: 0.19
Nodes (16): ByteCount, ModelTransmissionCount, ModelTransmissionPresent, communication_bytes(), CommunicationMessageMetadata, is_model_transmission(), model_transmission_count(), TensorPayloadMetadata (+8 more)

### Community 45 - "current_repository_root"
Cohesion: 0.14
Nodes (34): RepositoryPath, artifact_family_directory_token(), artifact_slot_directory(), current_repository_root(), ArtifactInstanceLabel, ablation_reference_records(), PersistedAblationReference, materialize_ablation_references() (+26 more)

### Community 46 - ".values"
Cohesion: 0.20
Nodes (13): ScientificCellSemanticKeyTuple, ArtifactDigest, CodeRevision, ComparisonName, EvidenceCycleIndex, MasterSeed, MethodName, MetricName (+5 more)

### Community 47 - "test_common.py"
Cohesion: 0.10
Nodes (23): RolePosition, RoleWindowContainsSample, SampleIdPrefix, compute_sample_id(), RelativePathText, role_for_normalized_position(), RoleWindow, supported_role_windows() (+15 more)

### Community 48 - "rules.py"
Cohesion: 0.16
Nodes (33): EvidenceArrivalCycleSequence, MinimumEligibleEvidenceHolderCount, EvidenceArrivalSchedule, compute_t_evidence(), cycle_when_requirement_met(), first_cycle_with_minimum_eligible_evidence_holders(), first_holder_cycle_for_domain(), holder_count_at_cycle() (+25 more)

### Community 49 - "test_no_primitive_leaks.py"
Cohesion: 0.15
Nodes (27): arg, AsyncFunctionDef, _all_violations(), config_scalar_foundation_violations(), domain_identifier_violations(), _function_arguments(), function_boundary_primitive_violations(), model_field_primitive_violations() (+19 more)

### Community 50 - "ArtifactFamily"
Cohesion: 0.08
Nodes (42): DatasetManifestPayload, artifact_identity(), ArtifactSlot, ProcedureIdentity, RawDatasetIdentityPayload, _publish_dataset_manifest(), publish_raw_dataset_identity(), ArtifactReuseDecision (+34 more)

### Community 51 - "BoundCondition"
Cohesion: 0.17
Nodes (9): BoundCondition, MonkeyPatch, test_byzantine_bound_preserves_resolved_core_cell_for_verifier_attack(), fake_load_counts(), test_byzantine_bound_routes_verifier_condition_through_direct_krum_reproducer(), test_model_replacement_condition_resolves_attack_scope(), fake_feature_names(), test_source_backdoor_scope_is_separate_from_reproducer_attack_scope() (+1 more)

### Community 52 - "iter_python_files"
Cohesion: 0.13
Nodes (23): modulefinder, test_no_stale_project_or_algorithm_aliases(), test_violation_detected_for_milestone_or_issue_reference(), test_violation_detected_for_stale_alias(), vocabulary_violations(), occurrence_count(), public_top_level_symbols(), Module (+15 more)

### Community 53 - "ExperimentLifecycleState"
Cohesion: 0.10
Nodes (39): AutomaticallyRetriable, AutomaticRecoveryPermitted, CellHandlerName, RetryCount, ExperimentLifecycleState, FailureClass, ScientificCellPhase, CellExecutor (+31 more)

### Community 54 - "observations.py"
Cohesion: 0.25
Nodes (15): Outcome summary means, Audit continuation, 2026-09-26, mean_of_defined_values(), observation_value(), observations_with_replacements(), outcome_metric_mean(), outcome_metric_values(), MethodName (+7 more)

### Community 55 - "18. Statistical analysis protocol"
Cohesion: 0.13
Nodes (15): 18.10 Rounding, 18.1 Experimental unit and pairing, 18.2 Primary hypothesis tests, 18.3 Alpha and multiplicity, 18.4 Effect sizes, 18.5 Confidence intervals, 18.6 Materiality criteria, 18.7 Collapse/survival rules (+7 more)

### Community 56 - "ast"
Cohesion: 0.14
Nodes (19): ast, naming_violations(), Module, test_no_banned_generic_artificial_or_forbidden_names(), test_violation_detected_for_forbidden_identifier(), test_violation_detected_for_generic_module_name(), test_violation_detected_for_versioned_symbol_name(), find_duplicate_constant_names() (+11 more)

### Community 57 - "nbaiot_adapter"
Cohesion: 0.08
Nodes (37): BaselineFullParticipationAllowed, DomainLocalEvaluation, nbaiot_adapter(), Path, supported_macro_f1_harm(), BooleanValue, Tensor, train_source_candidate_delta() (+29 more)

### Community 58 - "protocol/test_reproduction.py"
Cohesion: 0.13
Nodes (18): ExternalVerificationActive, handle_adequate_domain_trained(), handle_no_adequate_unconsumed_domain(), next_reproducer_domain(), CompromisedReproducerCount, ResolvedRowRequirementReached, select_compromised_reproducers(), test_handle_adequate_domain_trained_continues_scanning() (+10 more)

### Community 59 - "test_no_any_dict_object.py"
Cohesion: 0.24
Nodes (14): annotation_occurrences(), annotation_violations(), forbidden_symbol_violations(), expr, Module, raw_mapping_violations(), test_any_annotation_is_detected(), test_dictionary_construction_is_detected() (+6 more)

### Community 60 - "ciciot2023/test_acquisition.py"
Cohesion: 0.22
Nodes (22): discover_secondary_csv_files(), read_csv_header(), resolve_label_column(), validate_consistent_header(), CICIoT2023Acquisition, Path, skipif, test_compute_file_checksum_is_a_sha256_hex_digest() (+14 more)

### Community 61 - "16.5 Baseline implementation completion rules"
Cohesion: 0.06
Nodes (33): 16.1 Common budget rules, 16.2 Core and mechanism baselines, 16.3 Prior-art family representatives, 16.4 Baseline fairness, 16.5 Baseline implementation completion rules, 16. Baseline contracts, Baseline validation fixture map, `Candidate-Free Full Path` (+25 more)

### Community 62 - "FedSIRAApplication"
Cohesion: 0.33
Nodes (5): ApplicationExitCode, Console, FedSIRAApplication, OverwriteExisting, render()

### Community 63 - "AdmissionOpeningMode"
Cohesion: 0.22
Nodes (17): AdmissionOpeningMode, candidate_free_full_path_opening_mode(), AdmissionOpeningEntry, candidate_screen_transition(), ScreenDomainResult, start_admission(), test_candidate_free_full_path_uses_candidate_free_opening_mode(), test_one_independent_retrain_local_epochs_is_five() (+9 more)

### Community 64 - "35.2 Exact claim rules"
Cohesion: 0.09
Nodes (22): 35.1 State semantics, 35.2 Exact claim rules, 35. Claim-support decisions, `Authority Transition`, `Byzantine Operating Region`, `Capability-Granularity Boundary`, `Conditional Non-Interference`, `Direct Source Exclusion` (+14 more)

### Community 65 - "test_no_hardcoded_values.py"
Cohesion: 0.17
Nodes (19): Name, stmt, module_level_constant_values(), Module, test_no_module_level_constants_duplicate_governed_values(), test_violation_detected_for_duplicated_constant(), _uppercase_targets(), display_path() (+11 more)

### Community 66 - "current_comparison_evidence"
Cohesion: 0.24
Nodes (17): Producer and consumer anchors, comparison_evidence_failures(), current_comparison_evidence(), metric_evidence_digest(), ArtifactDigest, FailureMessage, Path, _record() (+9 more)

### Community 67 - "fit_feature_moments"
Cohesion: 0.22
Nodes (13): SecondaryMaterializationSummary, FeatureMoments, FeatureStatistic, fit_feature_moments(), model_validator, Self, _statistic(), test_feature_moments_reject_inconsistent_lengths() (+5 more)

### Community 68 - "artifact-workflow-io.md"
Cohesion: 0.21
Nodes (5): CLI-to-artifact workflow overlay, Closure gaps, Command roots, Production call-graph audit — current snapshot, Runtime boundaries

### Community 69 - "5. Core Engineering Rules"
Cohesion: 0.10
Nodes (18): 1. Think Before Coding, 2. Simplicity First, 3. Surgical Changes, 4. Goal-Driven Execution, 5. Core Engineering Rules, 6. Static Analysis and Automated Enforcement, 7. Testing Rules, 8. Definition of Done (+10 more)

### Community 70 - "30. Experiment registry"
Cohesion: 0.10
Nodes (21): 30.10 `Mechanism Ablation`, 30.11 `Compromised-Reproducer Robustness`, 30.12 `Compromised-Verifier Robustness`, 30.13 `Byzantine-Bound Violation`, 30.14 `Evidence Scarcity and Dormancy`, 30.15 `Shared Epistemic-Failure Boundary`, 30.16 `Capability Under-Specification Boundary`, 30.17 `Heterogeneous-Reproduction Boundary` (+13 more)

### Community 71 - "33.2 Result tables"
Cohesion: 0.10
Nodes (20): 33.1 Protocol tables, 33.2 Result tables, 33.3 Table rounding/significance display, 33. Required manuscript tables, `Ablation Results`, `Baseline Protocol`, `Byzantine Robustness`, `Collapse Decisions` (+12 more)

### Community 72 - "load_scientific_config"
Cohesion: 0.16
Nodes (18): pydantic, load_scientific_config(), Path, YamlValue, _read_yaml_mapping(), ScientificConfig, validate_scientific_config(), Path (+10 more)

### Community 73 - "discover_primary_csv_files"
Cohesion: 0.26
Nodes (18): compute_dataset_manifest_hash(), discover_primary_csv_files(), DatasetManifestDigest, Path, test_archive_and_already_extracted_layouts_yield_identical_dataset_manifest_hash(), Path, skipif, test_compute_dataset_manifest_hash_changes_when_a_file_changes() (+10 more)

### Community 74 - "Pre-experiment audit progress"
Cohesion: 0.12
Nodes (16): Canonical target-F1 and benign-FAR calculations, 2026-09-26, Constructor dispatch audit, 2026-09-26, Final data and safe-check continuation, 2026-09-26, Findings so far, Fresh audit restart, 2026-09-25, Fresh graph reconciliation after dynamic edge expansion, 2026-09-26, Inherited outcome dispatch correction, 2026-09-26, Pre-experiment audit progress (+8 more)

### Community 75 - "nbaiot/prepare.py"
Cohesion: 0.07
Nodes (64): AttackBasename, AttackFamilyName, PathToken, RetainMaterializedViews, compute_file_checksum(), OverwriteExisting, write_json_payload(), _cached_view_is_reusable() (+56 more)

### Community 76 - "planning.py"
Cohesion: 0.10
Nodes (38): PlanRenderText, ExperimentDefinition, derive_experiment_lifecycle(), planned_execution_records(), validate_no_duplicate_semantic_cells(), _ablation_cells(), _ablation_condition(), _baseline_validation_cells() (+30 more)

### Community 77 - "test_determinism.py"
Cohesion: 0.09
Nodes (26): numpy, sort_key(), local_training_seed(), minibatch_order(), sort_key(), namespace_seed(), CheckpointIdentity, DatasetManifestDigest (+18 more)

### Community 78 - "test_workflow_call_topology.py"
Cohesion: 0.10
Nodes (24): Remaining test-coverage actions, Scientific and workflow test crosswalk, TEST-002 — Data invariants, TEST-003 — Protocol states and guards, _called_names(), _called_names_for_node(), _method_node(), _missing_calls() (+16 more)

### Community 79 - "15. Adversarial and diagnostic transformation registry"
Cohesion: 0.11
Nodes (18): 15.10 Transformation cardinality, root-cause, and controlled-episode completion rules, 15.1 Useful + hidden-backdoor source, 15.2 Byzantine reproduction strategies, 15.3 Byzantine verifier behavior, 15.4 Shared label-error boundary, 15.5 Shared spurious-feature boundary, 15.6 Attacker-induced common-context boundary, 15.7 Capability under-specification fixture (+10 more)

### Community 80 - "load_published_manifests"
Cohesion: 0.53
Nodes (11): load_published_manifests(), _manifest_text(), _point_current_at(), Path, test_absent_root_yields_no_manifests(), test_current_publication_is_loaded(), test_obsolete_current_schema_is_rejected_as_invalid_evidence(), test_unreadable_current_publication_is_invalid_evidence() (+3 more)

### Community 81 - "exact_sign_flip_two_sided_p_value"
Cohesion: 0.13
Nodes (21): NamedPValue, SignFlipAssignment, SignFlipSampleCount, enumerate_sign_flip_assignments(), exact_sign_flip_non_inferiority_p_value(), exact_sign_flip_two_sided_p_value(), holm_adjusted_p_values(), ComparisonMargin (+13 more)

### Community 82 - "18.9 Exact comparison registry"
Cohesion: 0.18
Nodes (11): 18.9 Exact comparison registry, Family 10 — secondary generalization, Family 1 — proposal-screen necessity, Family 2 — plurality necessity, Family 3 — source-exclusion central claim, Family 4 — external reproduction verification necessity, Family 5 — primary baseline comparisons, Family 6 — compromised-reproducer robustness (+3 more)

### Community 83 - "17.2 Capability Contract metrics"
Cohesion: 0.12
Nodes (17): 17.2 Capability Contract metrics, Anchor training budgets and cadences, Benign false-alarm-rate increase, Checkpoint artifacts, Data loading, Metric adequacy minima, Persisted cell evidence and reuse, Persisted statistical comparison evidence (+9 more)

### Community 84 - "reproduction_progression"
Cohesion: 0.14
Nodes (16): DeltaScale, model_replacement_attack_feasible_domains(), ArtifactDigest, BooleanValue, DomainId, OrderedDict, RequiredReproductionRowCount, Tensor (+8 more)

### Community 85 - "test_no_comments_or_docstrings.py"
Cohesion: 0.33
Nodes (8): io, has_comment_token(), has_docstring(), Module, test_no_comments_or_docstrings_in_repository_python_source(), test_violation_detected_for_comment(), test_violation_detected_for_docstring(), tokenize

### Community 86 - "ciciot2023/schema.py"
Cohesion: 0.10
Nodes (28): csv, re, _comparison_token(), ClassLabel, validate_label_collisions(), validate_target_label_present(), build_class_registry(), CICIoT2023TargetFamilyMember (+20 more)

### Community 87 - "application.py"
Cohesion: 0.06
Nodes (75): DeterministicExecutionReady, CLI to application roots, Command branches, Coverage boundary, Readiness and lifecycle terminal branches, Workflow branch and terminal-path trace, DoctorArtifactSummary, DoctorExperimentSummary (+67 more)

### Community 88 - "DormantOrigin"
Cohesion: 0.16
Nodes (20): AdmissionStateIsTerminal, NewlyAdequateEvidenceExists, ResourceHorizonConfig, DormantOrigin, measurement_cycles(), EvidenceCycleIndex, apply_logical_cycle_expiry(), _dormant_resume_state() (+12 more)

### Community 89 - "_train_post_reference_delta"
Cohesion: 0.10
Nodes (40): CommunicationMessageCount, DomainT, apply_epistemic_target_marker(), apply_heterogeneity_shift(), BackdoorScope, HeterogeneityScope, poison_backdoor_rows(), ArtifactDigest (+32 more)

### Community 90 - "boundary_metric_set"
Cohesion: 0.21
Nodes (14): FalseCertificationCount, FalseSameEquivalenceCheck, PredicateSatisfied, ScopedContractActive, FalseSameCapabilityReason, boundary_metric_set(), BoundaryMetricSet, false_same_capability_certification_rate() (+6 more)

### Community 91 - "34. Required manuscript figures"
Cohesion: 0.14
Nodes (14): 34.10 `Heterogeneity Synthesis Boundary`, 34.11 `Admission-Delay Decomposition`, 34.12 `Efficiency Profile`, 34.13 `Secondary Generalization`, 34.1 `FedSIRA Protocol Schematic`, 34.2 `Primary Security–Utility Tradeoff`, 34.3 `Useful Backdoored Source`, 34.4 `Collapse Decision Effects` (+6 more)

### Community 92 - "synthesis.py"
Cohesion: 0.13
Nodes (22): KrumNeighborCount, KrumScore, ReproductionRowId, SourceExcludedFromKrum, krum_input_excludes_source(), krum_neighbor_count(), krum_score(), CommitteeSize (+14 more)

### Community 93 - "ProtocolCellExecutor"
Cohesion: 0.07
Nodes (26): Architecture responsibility review, Follow-up findings, Dynamic protocol dispatch, Disposition, Experiment scientific-subsystem review, Zero-category reconciliation, AdmissionStateObservation, load_prepared_evidence_counts() (+18 more)

### Community 94 - "models.py"
Cohesion: 0.32
Nodes (11): EncodedBytes, LengthPrefixBytes, _CommunicationMetadataWire, encode_message_envelope(), encode_message_metadata(), encode_tensor_metadata(), length_prefixed_bytes(), TensorEnvelopePayload (+3 more)

### Community 95 - "select_source_domain"
Cohesion: 0.32
Nodes (7): AttackCarrierRequired, select_source_domain(), test_select_source_domain_picks_first_with_target_stream(), test_select_source_domain_requires_gafgyt_udp_carrier_when_needed(), test_select_source_domain_returns_none_when_no_domain_qualifies(), test_source_selection_order_is_deterministic_and_a_permutation(), test_source_selection_order_is_reproducible_for_the_same_seed()

### Community 96 - "4. Audit requirements"
Cohesion: 0.07
Nodes (55): 4. Audit requirements, TEST-004 — Metrics and statistical rules, EffectSize, FoldCount, FoldIndex, ScreenDifferential, ClaimId, ClaimState (+47 more)

### Community 97 - "test_no_free_string_enum_bypass.py"
Cohesion: 0.50
Nodes (7): enum_member_values(), Module, Path, string_literals(), test_no_free_string_enum_value_bypass_across_modules(), test_owner_module_usage_not_flagged(), test_violation_detected_for_free_string_enum_value()

### Community 98 - ".run"
Cohesion: 0.12
Nodes (17): Fresh Graphify callable inventory — final pass, Per-command reachability, Prospective experiment workflow counts, Union, CLI workflow traces, `doctor`, `plan`, `preprocess [dataset] [--overwrite]` (+9 more)

### Community 99 - "commitment_digest"
Cohesion: 0.19
Nodes (13): commitment_digest(), compute_reproduction_commitment_hash(), ArtifactDigest, DerivedSeed, DomainId, MasterSeed, Tensor, validate_commitment_exists_before_verifier_assignment() (+5 more)

### Community 100 - "CommunicationMessageType"
Cohesion: 0.33
Nodes (7): CommunicationMessageType, parameter_tensor_name(), ParameterName, StrEnum, TensorParameterKind, TensorName, test_parameter_tensor_name_prefixes_kind()

### Community 101 - "test_dataset_subsystem.py"
Cohesion: 0.31
Nodes (6): _dataset_files(), Path, test_dataset_public_functions_avoid_primitive_annotations(), test_datasets_do_not_import_replaced_tabular_libraries(), test_datasets_do_not_keep_manual_arrow_sqlite_abstractions(), test_preprocess_workflow_calls_materialize_functions()

### Community 102 - "independent_local_reference_reviewer_is_positive"
Cohesion: 0.31
Nodes (8): ReviewerPositiveDecision, independent_local_reference_reviewer_is_positive(), CapabilityContractSatisfied, test_independent_local_reference_reviewer_negative_beyond_benign_far_margin(), test_independent_local_reference_reviewer_negative_beyond_supported_f1_margin(), test_independent_local_reference_reviewer_negative_when_capability_contract_fails(), test_independent_local_reference_reviewer_positive_within_noninferiority_margins(), test_secure_continual_assessment_post_reference_rounds_uses_governed_config()

### Community 103 - "NBaiotClass"
Cohesion: 0.08
Nodes (55): duckdb, pandas, RoleSamplingCap, assign_stream_roles_and_sample_ids(), ArtifactDigest, DomainId, RelativePathText, SamplingCap (+47 more)

### Community 104 - "pytest"
Cohesion: 0.18
Nodes (10): pytest, declared_source_backdoor_poison_fractions(), Probability, validate_declared_source_backdoor_poison_fraction(), _no_mismatches(), MonkeyPatch, test_doctor_command_reports_configuration_and_next_action(), test_an_undeclared_poison_fraction_is_rejected() (+2 more)

### Community 105 - "17. Metric registry and mathematical definitions"
Cohesion: 0.09
Nodes (22): 10th-percentile domain target F1, 17.10 Additional specified metrics, 17.3 Security and admission metrics, 17.4 Cross-domain distribution metrics, 17.5 Candidate-screen metrics, 17.6 Delay metrics, 17.7 Efficiency and communication metrics, 17.8 Aggregation and evaluation populations (+14 more)

### Community 106 - "cli.py"
Cohesion: 0.30
Nodes (11): command, rich_console, doctor(), plan(), preprocess(), OverwriteExisting, report(), run_experiment() (+3 more)

### Community 107 - "7. Exact FedSIRA procedure"
Cohesion: 0.20
Nodes (10): 7.1 Admission opening, 7.2 Proposal screen, 7.3 Source-independent reproduction, 7.4 External verification, 7.5 Reproducibility certificate, 7.6 Robust source-excluded synthesis: Krum, 7.7 Final fresh gate, 7. Exact FedSIRA procedure (+2 more)

### Community 108 - "8. Theory and proof obligations"
Cohesion: 0.20
Nodes (10): 8.1 Pre-independent-evidence indistinguishability, 8.2 Independent evidence proposition, 8.3 Claim-conditional direct source-artifact non-interference, 8.4 Honest-support counting, 8.5 Synthesizer-specific reproduction count, 8.6 Conditional safety/liveness, 8.7 Independent-evidence delay lower bound, 8.8 Random-committee contamination calculation (+2 more)

### Community 109 - "reproduction_progression.py"
Cohesion: 0.27
Nodes (10): consumed_domains(), handle_inadequate_domain(), CheckpointIdentity, ReproductionAttempt, validate_reproduction_start_checkpoint(), struct, test_consumed_domain_retained_even_if_certification_later_fails(), test_consumed_domains_only_counts_trained_attempts() (+2 more)

### Community 110 - "runtime.py"
Cohesion: 0.14
Nodes (25): concurrent_futures, datetime, random, RarArchivesPresent, resource, signal, _repository_layout_mismatches(), repository_root_expectation() (+17 more)

### Community 111 - "test_enum_integrity.py"
Cohesion: 0.40
Nodes (9): annotation_names(), enum_class_defs(), ClassDef, Module, Path, test_enum_used_only_as_its_own_annotation_is_still_flagged(), test_every_enum_is_referenced_outside_or_used_as_a_typed_field(), test_violation_detected_for_unused_enum() (+1 more)

### Community 112 - "test_no_redirects_shims_reexports.py"
Cohesion: 0.39
Nodes (8): is_pure_redirect(), package_reexports(), Module, test_compliant_module_with_definitions_passes(), test_no_non_init_module_is_a_pure_redirect(), test_package_initializers_do_not_publish_imported_compatibility_aliases(), test_violation_detected_for_package_reexport_facade(), test_violation_detected_for_redirect_module()

### Community 113 - "Final audit evidence"
Cohesion: 0.20
Nodes (8): Empirical and architecture deviation ledger, Current gate, Final audit evidence, Latest verification update, 2026-09-26, Prepared-output validation, Production rerun and cache identity, Real datasets and raw provenance, Safe checks already completed

### Community 114 - "Defaults and logging coverage audit"
Cohesion: 0.50
Nodes (3): ARCH-009: literal/default inventory scope, ARCH-010: event coverage gaps, Defaults and logging coverage audit

### Community 115 - "FedSIRA Pre-Experiment Audit Matrix"
Cohesion: 0.22
Nodes (8): 1. Purpose and scope, 2. Authority hierarchy, 3. Status and severity definitions, 5. Fresh Graphify / callable-count summary template, 6. Per-command / per-workflow callable-count template, 7. Required later audit execution order, 8. Final pre-experiment acceptance gate, FedSIRA Pre-Experiment Audit Matrix

### Community 116 - "verify_report_export_currency"
Cohesion: 0.31
Nodes (9): ReportRowIdentity, ArtifactDigest, Path, RelativePathText, ReportColumnText, ReportVerificationFailure, _table_header(), verify_rendered_table() (+1 more)

### Community 117 - "test_config_as_parameter.py"
Cohesion: 0.43
Nodes (6): _annotation_names(), config_parameter_violations(), expr, Module, test_production_functions_do_not_take_scientific_config(), test_violation_detected_for_public_config_parameter()

### Community 118 - "evaluation/test_validation.py"
Cohesion: 0.27
Nodes (10): EvaluationValidationError, FailureMessage, ValueError, validate_metric_class_membership(), test_metric_class_membership_accepts_valid_configuration(), test_metric_class_membership_rejects_benign_outside_vocabulary(), test_metric_class_membership_rejects_supported_outside_vocabulary(), test_metric_class_membership_rejects_target_outside_vocabulary() (+2 more)

### Community 119 - "24. Public CLI contract"
Cohesion: 0.25
Nodes (8): 24.1 `fedsira doctor`, 24.2 `fedsira preprocess ["N-BaIoT"|"CICIoT2023"]`, 24.3 `fedsira plan`, 24.4 `fedsira smoke`, 24.5 `fedsira status`, 24.6 `fedsira run <experiment name>`, 24.7 `fedsira report [<experiment name>]`, 24. Public CLI contract

### Community 120 - "test_public_type_boundaries.py"
Cohesion: 0.42
Nodes (8): is_fully_annotated(), public_top_level_functions(), FunctionDef, Module, test_compliant_function_passes(), test_public_boundary_functions_are_fully_annotated(), test_violation_detected_for_unannotated_public_function(), violations_in_tree()

### Community 121 - "test_certified_ensemble.py"
Cohesion: 0.32
Nodes (7): ensemble_predicted_label(), test_certified_ensemble_domain_groups_are_deterministic_disjoint_and_cover_all_domains(), test_certified_ensemble_post_reference_rounds_uses_governed_config(), test_ensemble_predicted_label_breaks_full_tie_by_mean_softmax_then_lowest_class(), test_ensemble_predicted_label_full_tie_with_equal_mean_uses_lowest_class_index(), test_ensemble_predicted_label_uses_majority_vote_when_unambiguous(), test_validate_group_without_target_member_rejects_synthesized_target_rows()

### Community 122 - "9. Primary dataset and experimental domain construction"
Cohesion: 0.25
Nodes (8): 9.1.1 Raw release discovery and canonical mapping, 9.1 Primary dataset, 9.2 Domain proxies, 9.3 Class vocabulary, 9.4 Post-reference capability, 9.5 Supported classes, 9.6 Controlled replay semantics, 9. Primary dataset and experimental domain construction

### Community 124 - "AblationScenario"
Cohesion: 0.13
Nodes (14): AblationReproducerStrategy, AblationScenario, ablation_reproducer_strategy(), ablation_scenario_for_condition(), ablation_reference_cell(), MasterSeed, ScenarioName, DomainId (+6 more)

### Community 125 - "test_commands.py"
Cohesion: 0.12
Nodes (5): MonkeyPatch, test_doctor_exits_zero_when_environment_and_config_are_valid(), test_no_command_exposes_a_seed_or_method_override_option(), test_preprocess_without_dataset_runs_all_roadmap_datasets(), test_status_renders_planned_experiment_lifecycle()

### Community 126 - "auprc_one_vs_rest"
Cohesion: 0.29
Nodes (7): BinaryLabelMaskSeries, auprc_one_vs_rest(), auroc_one_vs_rest(), test_auprc_one_vs_rest_na_without_positives(), test_auprc_one_vs_rest_perfect_separation_is_one(), test_auroc_one_vs_rest_na_without_both_classes(), test_auroc_one_vs_rest_perfect_separation()

### Community 127 - "test_invariants.py"
Cohesion: 0.33
Nodes (6): inspect, _metadata(), test_admission_delay_timer_fixture_satisfies_post_evidence_sum_within_tolerance(), test_capability_contract_contract_mutation_after_construction_is_rejected(), test_communication_serializer_is_independent_of_dict_construction_order(), test_honest_reproduction_constructor_has_no_source_artifact_parameter()

### Community 128 - "12. Model, anchor training, source training, and reproduction training"
Cohesion: 0.29
Nodes (7): 12.1 Base classifier, 12.2 Common optimizer and loss constants, 12.3 Anchor FedAvg, 12.4 Post-reference training contract, 12.5 Verifier-aware malicious training override, 12.6 No test-set tuning, 12. Model, anchor training, source training, and reproduction training

### Community 129 - "26. Scientific output contract"
Cohesion: 0.29
Nodes (7): 26.1 Scientific execution dependencies, 26.2 Artifact validity and lifecycle, 26.3 Reusable artifact families, 26.4 Selective invalidation boundaries, 26.5 Experiment dependency and reuse map, 26.6 Cross-experiment reuse rules, 26. Scientific output contract

### Community 130 - "28. Validation and smoke-test contract"
Cohesion: 0.29
Nodes (7): 28.1 Data tests, 28.2 Model/FL tests, 28.3 Protocol invariant tests, 28.4 Mathematical tests, 28.5 Metric/statistical tests, 28.6 Artifact reuse and recovery tests, 28. Validation and smoke-test contract

### Community 131 - "background-jobs.md"
Cohesion: 0.33
Nodes (5): 2026-09-25 follow-up, 2026-09-26 continuation, Fresh audit, 2026-09-25, Safe overwrite audit continuation, 2026-09-26, WSL resumed, 2026-09-25

### Community 132 - "4. Threat model, trust assumptions, and explicit boundaries"
Cohesion: 0.40
Nodes (5): 4.1 Primary security setting, 4.2 Attacker knowledge, 4.3 Honest-path assumptions, 4.4 Failure boundaries that must be tested, 4. Threat model, trust assumptions, and explicit boundaries

### Community 133 - "1. Scientific problem, contribution boundary, and claims"
Cohesion: 0.33
Nodes (6): 1.1 Research problem, 1.2 Core authority transition, 1.3 Required mechanism, 1.4 Safe manuscript claims, 1.5 Forbidden claims, 1. Scientific problem, contribution boundary, and claims

### Community 134 - "13. Role assignment, seeds, security profiles, and deterministic ties"
Cohesion: 0.20
Nodes (10): 13.1 Master seeds, 13.2 Seed namespaces and canonical hash semantics, 13.3 Deterministic ordering instead of hidden RNG defaults, 13.4 Source selection, 13.5 Proposal-screen fold and matching semantics, 13.6 Primary deterministic verifier profile, 13.7 Diagnostic random verifier profile, 13.8 Compromised reproducer selection (+2 more)

### Community 135 - "10. Exact data roles, sampling, and preprocessing"
Cohesion: 0.33
Nodes (6): 10.1 Supported-class role intervals, 10.2 Target-class role intervals, 10.3 Deterministic sampling caps, 10.4 Data validation, 10.6 Preprocessing semantic identity, 10. Exact data roles, sampling, and preprocessing

### Community 136 - "6. FedSIRA state machine and non-negotiable invariants"
Cohesion: 0.40
Nodes (5): 6.1 States, 6.2 Resource horizon, 6.3 Exact transition and scheduling table, 6.4 Invariants, 6. FedSIRA state machine and non-negotiable invariants

### Community 137 - "FedSIRA"
Cohesion: 0.40
Nodes (4): CLI usage, FedSIRA, Reproducibility, Setup

### Community 138 - "fraction_to_attack_count"
Cohesion: 0.40
Nodes (4): AttackCount, fraction_to_attack_count(), ExampleCount, test_fraction_to_attack_count_floors()

### Community 139 - "malicious_admission_rate"
Cohesion: 0.67
Nodes (4): AdmissionIndicatorSeries, legitimate_admission_rate(), malicious_admission_rate(), test_malicious_admission_rate_and_legitimate_admission_rate()

### Community 140 - "test_robust_aggregation.py"
Cohesion: 0.21
Nodes (10): NonAbstainingReproductionSeries, ParticipantCount, ThreeRowCoordinateMedianConfig, direct_krum_committee_rows(), CommitteeSize, validate_three_row_coordinate_median_committee_size(), test_coordinate_wise_median_synthesis_is_coordinatewise_median_of_three_rows(), test_direct_krum_committee_rows_filters_abstaining_and_requires_committee_size() (+2 more)

### Community 182 - "Formula duplication review"
Cohesion: 0.50
Nodes (3): Centralized target and benign-FAR metrics, Formula duplication review, Remaining scope

### Community 184 - "test_model_replacement_requires_at_least_one_configured_carrier_row"
Cohesion: 0.50
Nodes (3): MonkeyPatch, test_model_replacement_requires_at_least_one_configured_carrier_row(), fake_load_rows()

### Community 185 - "reproduction_attempt_count"
Cohesion: 0.67
Nodes (3): ReproductionAttemptCount, reproduction_attempt_count(), test_reproduction_attempt_count_excludes_evidence_inadequate_domains()

### Community 193 - "_ListConvertibleTensor"
Cohesion: 0.50
Nodes (3): ModelParameterValue, _ListConvertibleTensor, Protocol

## Knowledge Gaps
- **348 isolated node(s):** `fedsira`, `graphify`, `1. Think Before Coding`, `2. Simplicity First`, `3. Surgical Changes` (+343 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 874 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **44 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExperimentName` connect `ExperimentName` to `preprocess.py`, `AdmissionState`, `figures.py`, `comparisons.py`, `CellExecutionOutcome`, `metrics.py`, `enums.py`, `export.py`, `store.py`, `checkpoints.py`, `execution.py`, `FrozenDomainModel`, `collapse.py`, `paths.py`, `handlers.py`, `reporting/verification.py`, `test_experiment_registry_contracts.py`, `current_repository_root`, `.values`, `ArtifactFamily`, `ExperimentLifecycleState`, `observations.py`, `FedSIRAApplication`, `current_comparison_evidence`, `planning.py`, `application.py`, `models.py`, `4. Audit requirements`, `.run`, `cli.py`, `verify_report_export_currency`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `current_application_context()` connect `current_application_context` to `defenses.py`, `test_training.py`, `preprocess.py`, `framed_bytes`, `AdmissionState`, `figures.py`, `FedSIRAClassifier`, `comparisons.py`, `ciciot2023/prepare.py`, `CellExecutionOutcome`, `metrics.py`, `enums.py`, `export.py`, `store.py`, `TernaryOutcome`, `checkpoints.py`, `execution.py`, `FrozenDomainModel`, `collapse.py`, `paths.py`, `handlers.py`, `reporting/verification.py`, `test_experiment_registry_contracts.py`, `DatasetId`, `MetricResult`, `ExperimentName`, `publish_prepared_role_view`, `materialize_ciciot2023_prepared_views`, `current_repository_root`, `ArtifactFamily`, `ExperimentLifecycleState`, `observations.py`, `nbaiot_adapter`, `current_comparison_evidence`, `nbaiot/prepare.py`, `planning.py`, `reproduction_progression`, `application.py`, `_train_post_reference_delta`, `ProtocolCellExecutor`, `4. Audit requirements`, `NBaiotClass`, `pytest`, `reproduction_progression.py`, `runtime.py`, `AblationScenario`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `DatasetId` connect `DatasetId` to `preprocess.py`, `framed_bytes`, `ciciot2023/prepare.py`, `CellExecutionOutcome`, `metrics.py`, `enums.py`, `export.py`, `checkpoints.py`, `execution.py`, `FrozenDomainModel`, `paths.py`, `handlers.py`, `test_enums.py`, `test_capability_contract.py`, `test_experiment_registry_contracts.py`, `config.py`, `ExperimentName`, `publish_prepared_role_view`, `materialize_ciciot2023_prepared_views`, `current_repository_root`, `.values`, `ArtifactFamily`, `ExperimentLifecycleState`, `test_model_replacement_requires_at_least_one_configured_carrier_row`, `FedSIRAApplication`, `nbaiot/prepare.py`, `planning.py`, `ciciot2023/schema.py`, `application.py`, `ProtocolCellExecutor`, `4. Audit requirements`, `.run`, `cli.py`, `test_invariants.py`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `current_application_context()` (e.g. with `test_standard_fl_baseline_budget_reads_yaml()` and `test_declared_poison_sweep_comes_from_configuration()`) actually correct?**
  _`current_application_context()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 31 inferred relationships involving `FrozenDomainModel` (e.g. with `CalibrationErrorCount` and `CellHandlerName`) actually correct?**
  _`FrozenDomainModel` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 151 inferred relationships involving `ExperimentName` (e.g. with `_all_complete()` and `_collapse_experiment_completed()`) actually correct?**
  _`ExperimentName` has 151 INFERRED edges - model-reasoned connections that need verification._
- **Are the 97 inferred relationships involving `AdmissionState` (e.g. with `AdmissionStateIsTerminal` and `CellHandlerName`) actually correct?**
  _`AdmissionState` has 97 INFERRED edges - model-reasoned connections that need verification._