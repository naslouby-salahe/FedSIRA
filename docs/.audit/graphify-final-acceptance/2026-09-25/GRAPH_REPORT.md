# Graph Report - FedSIRA  (2026-09-25)

## Corpus Check
- 261 files · ~2,434,120 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: (none) 4, .audit 2, .exit 2)

## Summary
- 4251 nodes · 15479 edges · 179 communities (138 shown, 41 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 2796 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9449c601`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Communities (193 total, 3 thin omitted)
- nbaiot/prepare.py
- Communities (169 total, 4 thin omitted)
- ciciot2023/test_preprocessing.py
- rules.py
- reproduction_progression.py
- common.py
- FailureClass
- figures.py
- service.py
- AdmissionState
- FedSIRAClassifier
- ExperimentName
- application.py
- DatasetId
- Role
- models.py
- handlers.py
- config.py
- FrozenDomainModel
- current_application_context
- comparisons.py
- defenses.py
- paths.py
- test_experiment_registry_contracts.py
- load_published_manifests
- exact_sign_flip_two_sided_p_value
- statistics.py
- CellExecutionOutcome
- build_epoch_batches
- enums.py
- run_smoke_suite
- ablation_reference_records
- model.py
- MetricResult
- post_reference.py
- planning.py
- store.py
- pathlib
- collapse.py
- CapabilityContractScope
- federated.py
- framed_bytes
- definitions.py
- NBaiotClass
- build_comparison_registry
- publication.py
- baselines/test_registry.py
- test_common.py
- publish_prepared_role_view
- nbaiot_adapter
- ProtocolCellExecutor
- fit_feature_moments
- parse
- Roadmap.md
- CertifiedReproductionRow
- SeedDerivationLabel
- test_domain_typing_hygiene.py
- test_no_primitive_leaks.py
- FedSIRAApplication
- ArtifactFamily
- tables.py
- boundary_metric_set
- ciciot2023/test_acquisition.py
- ciciot2023/prepare.py
- select_krum_update
- RuntimeComponentName
- protocol_evidence.py
- runtime.py
- ciciot2023/schema.py
- 16.2 Core and mechanism baselines
- cli.py
- 16.5 Baseline implementation completion rules
- 35.2 Exact claim rules
- _repo.py
- load_scientific_config
- 5. Core Engineering Rules
- 30. Experiment registry
- 33.2 Result tables
- iter_python_files
- learning/training.py
- artifact_slot_directory
- 15. Adversarial and diagnostic transformation registry
- ElapsedTimer
- DescriptiveScientificMetric
- types.py
- independent_local_reference_reviewer_is_positive
- test_commands.py
- 24. Public CLI contract
- 17.2 Capability Contract metrics
- model_validator
- test_run_status_report.py
- 18. Statistical analysis protocol
- FedSIRA Pre-Experiment Audit Matrix
- test_no_duplicate_constants.py
- apply_sampling_cap
- 17.1 Classification metrics
- 34. Required manuscript figures
- test_no_any_dict_object.py
- test_workflow_call_topology.py
- 10. Exact data roles, sampling, and preprocessing
- admission.py
- apply_holm_adjustment
- .values
- evaluation/test_validation.py
- AblationVariant
- BaselineIdentity
- collections
- 18.9 Exact comparison registry
- test_preprocess_plan_smoke.py
- 13. Role assignment, seeds, security profiles, and deterministic ties
- 7. Exact FedSIRA procedure
- 8. Theory and proof obligations
- test_robust_aggregation.py
- test_enum_integrity.py
- .__init__
- .run
- test_no_comments_or_docstrings.py
- test_no_test_only_production_code.py
- test_public_type_boundaries.py
- test_enums.py
- Graph Report - FedSIRA  (2026-09-15)
- Graph Report - FedSIRA  (2026-09-15)
- 9. Primary dataset and experimental domain construction
- test_no_free_string_enum_bypass.py
- CLI workflow traces
- 12. Model, anchor training, source training, and reproduction training
- 26. Scientific output contract
- 28. Validation and smoke-test contract
- test_config_as_parameter.py
- 17.4 Cross-domain distribution metrics
- 17. Metric registry and mathematical definitions
- 1. Scientific problem, contribution boundary, and claims
- 17.10 Additional specified metrics
- 17.3 Security and admission metrics
- 4. Threat model, trust assumptions, and explicit boundaries
- 6. FedSIRA state machine and non-negotiable invariants
- FedSIRA
- _ListConvertibleTensor
- AGENTS.md
- claim-evidence-map.md
- fedsira
- recovery_backdoor_alarm_threshold

## God Nodes (most connected - your core abstractions)
1. `current_application_context()` - 208 edges
2. `FrozenDomainModel` - 203 edges
3. `ExperimentName` - 182 edges
4. `AdmissionState` - 171 edges
5. `MetricResult` - 153 edges
6. `Communities (193 total, 3 thin omitted)` - 147 edges
7. `ScientificCell` - 128 edges
8. `DatasetId` - 122 edges
9. `Communities (169 total, 4 thin omitted)` - 122 edges
10. `ExperimentLifecycleState` - 109 edges

## Surprising Connections (you probably didn't know these)
- ``doctor`` --references--> `DoctorReport`  [INFERRED]
  docs/.audit/cli-workflows.md → src/fedsira/application.py
- `17.7 Efficiency and communication metrics` --references--> `dataset_manifest_hash()`  [INFERRED]
  docs/Roadmap.md → src/fedsira/datasets/common.py
- ``preprocess [dataset] [--overwrite]`` --references--> `DatasetId`  [INFERRED]
  docs/.audit/cli-workflows.md → src/fedsira/domain/enums.py
- `15.10 Transformation cardinality, root-cause, and controlled-episode completion rules` --references--> `false_same_capability_certification_rate()`  [INFERRED]
  docs/Roadmap.md → src/fedsira/evaluation/metrics.py
- `13.2 Seed namespaces and canonical hash semantics` --references--> `local_training_seed()`  [INFERRED]
  docs/Roadmap.md → src/fedsira/runtime.py

## Import Cycles
- 3-file cycle: `src/fedsira/experiments/collapse.py -> src/fedsira/experiments/engine.py -> src/fedsira/experiments/execution.py -> src/fedsira/experiments/collapse.py`
- 3-file cycle: `src/fedsira/evaluation/comparison_evidence.py -> src/fedsira/experiments/engine.py -> src/fedsira/experiments/execution.py -> src/fedsira/evaluation/comparison_evidence.py`

## Communities (179 total, 41 thin omitted)

### Community 0 - "Communities (193 total, 3 thin omitted)"
Cohesion: 0.01
Nodes (147): Communities (193 total, 3 thin omitted), Community 0 - "Community 0", Community 100 - "Community 100", Community 101 - "Community 101", Community 102 - "Community 102", Community 103 - "Community 103", Community 104 - "Community 104", Community 105 - "Community 105" (+139 more)

### Community 1 - "nbaiot/prepare.py"
Cohesion: 0.07
Nodes (72): AttackBasename, AttackFamilyName, csv, duckdb, PathToken, specification(), DatasetSpecification, sql_ident() (+64 more)

### Community 2 - "Communities (169 total, 4 thin omitted)"
Cohesion: 0.02
Nodes (122): Communities (169 total, 4 thin omitted), Community 0 - "Community 0", Community 100 - "Community 100", Community 101 - "Community 101", Community 102 - "Community 102", Community 103 - "Community 103", Community 104 - "Community 104", Community 105 - "Community 105" (+114 more)

### Community 3 - "ciciot2023/test_preprocessing.py"
Cohesion: 0.23
Nodes (27): IntEnum, assign_secondary_roles(), resolve_row_identifier_columns(), CICIoT2023PseudoDomain, DomainId, _per_attack_csv_file(), Path, _roles_by_stable_row_id() (+19 more)

### Community 4 - "rules.py"
Cohesion: 0.04
Nodes (91): AdmissionStateIsTerminal, AtLeastTwoByzantineProbability, CompletionCycleIndex, EligiblePoolSize, EvidenceArrivalCycleIndex, EvidenceArrivalCycleSequence, fractions, KrumCommitteeAdmissible (+83 more)

### Community 5 - "reproduction_progression.py"
Cohesion: 0.07
Nodes (55): ExternalVerificationActive, BackdoorScope, AblationReproducerStrategy, ArtifactDigest, BooleanValue, DomainId, OrderedDict, RequiredReproductionRowCount (+47 more)

### Community 6 - "common.py"
Cohesion: 0.05
Nodes (61): AttackCount, FeatureName, ScalingConfig, apply_attacker_induced_common_context(), apply_heterogeneity_shift(), apply_quantity_skew_to_cap(), apply_shared_spurious_feature(), apply_trigger_transform() (+53 more)

### Community 7 - "FailureClass"
Cohesion: 0.27
Nodes (11): AutomaticallyRetriable, AutomaticRecoveryPermitted, RetryCount, FailureClass, automatic_recovery_permitted(), is_automatically_retriable(), test_data_invalid_is_never_automatically_retried(), test_infrastructure_interruption_is_not_permitted_after_limit_reached() (+3 more)

### Community 8 - "figures.py"
Cohesion: 0.09
Nodes (70): Axes, AxisDraw, BoundarySeries, FigureAnnotationText, FigureAxisLabel, FigureLegendText, matplotlib_axes, matplotlib_figure (+62 more)

### Community 9 - "service.py"
Cohesion: 0.13
Nodes (34): RealAnchor, RootCauseScope, scope_and_shift_rows(), compute_real_report_summary(), compute_source_backdoor_asr(), compute_unmatched_screen_differential(), evaluate_domain(), non_source_domains() (+26 more)

### Community 10 - "AdmissionState"
Cohesion: 0.12
Nodes (26): CompromisedProductionAncestry, DiscardSourceWeights, Per-experiment prospective CLI-to-leaf workflows, Registered experiment workflow map, LegitimateAdmissionEligible, AdmissionState, PreparedEvidenceCounts, ScientificCellSemanticKey (+18 more)

### Community 11 - "FedSIRAClassifier"
Cohesion: 0.05
Nodes (91): DeltaScale, 4. Audit requirements, PostReferenceConfig, FedSIRAClassifier, flatten_trainable_parameters(), ModelInputWidth, ModelOutputWidth, TrainableParameterCount (+83 more)

### Community 12 - "ExperimentName"
Cohesion: 0.07
Nodes (77): configure_artifact_logging(), dataset_readiness(), ExperimentLifecycleState, ExperimentName, LogEvent, SourceExclusionMethod, CellExecutor, CellPhaseLogFields (+69 more)

### Community 13 - "application.py"
Cohesion: 0.06
Nodes (66): DeterministicExecutionReady, CLI to application roots, DoctorArtifactSummary, DoctorExperimentSummary, NextValidAction, ProjectProgressDescription, RunRenderText, _all_complete() (+58 more)

### Community 14 - "DatasetId"
Cohesion: 0.11
Nodes (50): DatasetManifestPayload, artifact_staging_root(), preprocessing_extraction_cache_root(), CICIoT2023DatasetManifestPayload, RawDatasetFileIdentity, RawDatasetIdentityPayload, prepared_dataset_present(), BooleanValue (+42 more)

### Community 15 - "Role"
Cohesion: 0.13
Nodes (33): SamplingCapsPerDomain, dataset_specification(), prepared_domain_summaries(), prepared_view_digest(), PreparedDomainSummary, BooleanValue, RowCount, SamplingCap (+25 more)

### Community 16 - "models.py"
Cohesion: 0.10
Nodes (39): ByteCount, EncodedBytes, inspect, LengthPrefixBytes, ModelTransmissionCount, ModelTransmissionPresent, communication_bytes(), CommunicationMessageMetadata (+31 more)

### Community 17 - "handlers.py"
Cohesion: 0.04
Nodes (110): ClassCount, collections_abc, CommunicationMessageCount, FeatureSchemaDigest, hashlib, MonotonicTimestamp, OneVotePerDomain, ProductionWeight (+102 more)

### Community 18 - "config.py"
Cohesion: 0.07
Nodes (51): RoleBoundary, RoleInterval, AdmissionOpeningConfig, AttackerInducedCommonContextConfig, AttacksAndBoundariesConfig, BaselinesConfig, BootstrapConfig, ByzantineOperatingRegionConfig (+43 more)

### Community 19 - "FrozenDomainModel"
Cohesion: 0.06
Nodes (81): pandas, ReportRowIdentity, ResolvedCoreIdentity, InvalidArtifactReport, PreparedViewSidecar, FrozenDomainModel, BaseModel, ResolvedCore (+73 more)

### Community 20 - "current_application_context"
Cohesion: 0.08
Nodes (71): DomainLocalEvaluation, SourceAvailable, flat_parameters_identity(), AlgorithmName, load_flat_trainable_parameters(), model_state_from_classifier(), clip_source_update(), krum_reference_post_reference_rounds() (+63 more)

### Community 21 - "comparisons.py"
Cohesion: 0.18
Nodes (40): ComparisonReferenceLabel, ComparisonMetric, CoreMethodIdentity, PrimaryScenario, _ablation_comparisons(), ablation_material_threshold(), build_comparison_name(), _capability_boundary_comparisons() (+32 more)

### Community 22 - "defenses.py"
Cohesion: 0.05
Nodes (76): ClassIndex, GroupCount, GroupIndex, dataset_manifest_hash(), deterministic_domain_order(), NamespaceSeed, certified_ensemble_domain_groups(), certified_ensemble_post_reference_rounds() (+68 more)

### Community 23 - "paths.py"
Cohesion: 0.14
Nodes (43): artifact_log_path(), artifact_publication_root(), execution_outputs_root(), execution_workspace_root(), experiment_execution_root(), experiment_log_path(), experiment_metrics_root(), experiment_repetition_telemetry_root() (+35 more)

### Community 24 - "test_experiment_registry_contracts.py"
Cohesion: 0.10
Nodes (30): experiment_names(), experiment_registry(), ExperimentDefinition, _ablation_cells(), _ablation_condition(), _baseline_validation_cells(), _cartesian_cells(), _efficiency_cells() (+22 more)

### Community 25 - "load_published_manifests"
Cohesion: 0.53
Nodes (11): load_published_manifests(), _manifest_text(), _point_current_at(), Path, test_absent_root_yields_no_manifests(), test_current_publication_is_loaded(), test_obsolete_current_schema_is_rejected_as_invalid_evidence(), test_unreadable_current_publication_is_invalid_evidence() (+3 more)

### Community 26 - "exact_sign_flip_two_sided_p_value"
Cohesion: 0.13
Nodes (21): NamedPValue, SignFlipAssignment, SignFlipSampleCount, enumerate_sign_flip_assignments(), exact_sign_flip_non_inferiority_p_value(), exact_sign_flip_two_sided_p_value(), holm_adjusted_p_values(), ComparisonMargin (+13 more)

### Community 27 - "statistics.py"
Cohesion: 0.08
Nodes (44): ConfidenceIntervalBound, DecileBinIndex, itertools, MatchedControlCount, MinimumDefinedDomainCount, numpy, bootstrap_percentile_confidence_interval(), _candidate_pool() (+36 more)

### Community 28 - "CellExecutionOutcome"
Cohesion: 0.12
Nodes (39): CellCompletionStatus, CellExecutionOutcome, experiment_execution_digest(), ExperimentExecutionResult, ArtifactDigest, ScientificCellCount, ExperimentReportSummary, export_experiment_report() (+31 more)

### Community 29 - "build_epoch_batches"
Cohesion: 0.16
Nodes (23): BatchRowIndexSequence, BatchSize, DataLoader, build_epoch_batches(), DeclaredBatchDataset, ordered_batch_indices(), ordered_batch_row_indices(), ordered_minibatches() (+15 more)

### Community 30 - "enums.py"
Cohesion: 0.12
Nodes (30): ArtifactFamilyDirectoryToken, ArtifactFileToken, ByteUnit, ByzantineVerifierBehavior, CellPhaseState, CublasWorkspaceConfig, DelayPhaseMetric, EnvironmentVariableName (+22 more)

### Community 31 - "run_smoke_suite"
Cohesion: 0.15
Nodes (28): CodeRevision, configuration_digest(), repository_revision(), SmokeCheckName, _extended_protocol_invariants(), _load_persisted_smoke_record(), _mathematical_invariants(), _persist_smoke_record() (+20 more)

### Community 32 - "ablation_reference_records"
Cohesion: 0.29
Nodes (13): ablation_reference_records(), _benefit_difference(), _comparison_pairs(), extend_index_from_records(), merge_metric_record(), merge_metric_records(), metric_index_from_outcomes(), metric_value() (+5 more)

### Community 33 - "model.py"
Cohesion: 0.24
Nodes (14): KeepGradients, logits_for_samples(), per_sample_cross_entropy(), probabilities_for_samples(), Module, Tensor, _model(), test_logits_and_probabilities_agree_for_log_softmax() (+6 more)

### Community 34 - "MetricResult"
Cohesion: 0.06
Nodes (85): AdmissionCount, AdmissionIndicatorSeries, BinaryLabelMaskSeries, CleanOracleDegradationMaterial, dataclasses, God Nodes (most connected - your core abstractions), God Nodes (most connected - your core abstractions), OptionalTriggeredSampleMaskSeries (+77 more)

### Community 35 - "post_reference.py"
Cohesion: 0.07
Nodes (58): DomainT, apply_epistemic_target_marker(), EpistemicFailureScope, relabel_shared_label_error_rows_for_scope(), ArtifactDigest, DerivedSeed, DomainId, MasterSeed (+50 more)

### Community 36 - "planning.py"
Cohesion: 0.13
Nodes (23): PlanRenderText, build_plan(), _collapse_decision_passed(), ExperimentPlan, plan_cell_count_contract(), PlanCellCountContract, CollapseDecisionPassed, ResolvedCoreComplete (+15 more)

### Community 37 - "store.py"
Cohesion: 0.10
Nodes (53): ArtifactComplete, ArtifactPayloadBytes, ArtifactSerializedText, pytest, ArtifactCurrentPointer, ArtifactLogFields, ArtifactManifest, compute_checksum() (+45 more)

### Community 38 - "pathlib"
Cohesion: 0.09
Nodes (24): pathlib, subprocess, sys, tempfile, CompletedProcess, Path, run_vulture(), test_no_dead_code_in_src() (+16 more)

### Community 39 - "collapse.py"
Cohesion: 0.11
Nodes (43): enum, MinimumCompletePairCount, ComparisonFamily, ComparisonResult, ComparisonState, _best_passed_metric(), _collapse_comparator(), collapse_decision_from_comparison_families() (+35 more)

### Community 40 - "CapabilityContractScope"
Cohesion: 0.19
Nodes (20): FeatureShiftSign, HeterogeneityMultiplier, PreparedEvidencePresent, ScreenLoss, apply_root_cause_feature_shift(), SampleId, real_evidence_available(), root_cause_for_sample() (+12 more)

### Community 41 - "federated.py"
Cohesion: 0.13
Nodes (34): EvaluationCadenceReached, AnchorFedAvgConfig, OptimizerConfig, TrainingConfig, anchor_round_is_evaluated(), anchor_round_participants(), AnchorRoundEvaluationLogFields, AnchorTrainingLogFields (+26 more)

### Community 42 - "framed_bytes"
Cohesion: 0.15
Nodes (29): FramedBytes, ScoringTransformName, class_registry_digest(), DomainClassScore, model_score_slot(), model_score_view_digest(), ModelScorePayload, publish_model_score() (+21 more)

### Community 43 - "definitions.py"
Cohesion: 0.13
Nodes (30): ArtifactFileName, FeatureShiftMagnitude, BoundCondition, EfficiencyCondition, EpistemicFailureType, ExperimentClass, ExternalVerificationCondition, HeterogeneityRegime (+22 more)

### Community 44 - "NBaiotClass"
Cohesion: 0.08
Nodes (58): Surprising Connections (you probably didn't know these), Surprising Connections (you probably didn't know these), RetainMaterializedViews, assign_stream_roles_and_sample_ids(), materialize_nbaiot_prepared_views(), PreparedView, PreparedViewMetadata, ArtifactDigest (+50 more)

### Community 45 - "build_comparison_registry"
Cohesion: 0.21
Nodes (16): EffectSize, build_comparison_registry(), _effect_size(), evaluate_comparison(), MasterSeed, PairedDifference, test_capability_granularity_ablation_treats_false_certification_as_harm(), test_evaluate_comparison_strong_consistent_effect() (+8 more)

### Community 46 - "publication.py"
Cohesion: 0.15
Nodes (29): RepositoryPath, content_digest(), publish_table_figure_export(), publish_table_figure_source_data(), ArtifactDigest, ArtifactReuseDecision, Path, RowCount (+21 more)

### Community 47 - "baselines/test_registry.py"
Cohesion: 0.12
Nodes (20): BaselineFullParticipationAllowed, domain_target_view(), domain_without_target_view_may_participate(), first_eligible_non_source_reproducer(), PostReferenceDataAccess, DomainId, single_fresh_verifier_domain(), single_fresh_verifier_outcome() (+12 more)

### Community 48 - "test_common.py"
Cohesion: 0.09
Nodes (25): RolePosition, RoleWindowContainsSample, SampleIdPrefix, SourceRowIndex, RoleIntervals, compute_sample_id(), RelativePathText, role_for_normalized_position() (+17 more)

### Community 49 - "publish_prepared_role_view"
Cohesion: 0.13
Nodes (28): PreparedRoleViewManifest, _parquet_checksum(), prepared_view_publication_failures(), ArtifactDigest, FailureMessage, Path, PreparedViewKey, RowCount (+20 more)

### Community 50 - "nbaiot_adapter"
Cohesion: 0.11
Nodes (28): SourceIsProductionUpdate, nbaiot_adapter(), Path, ReviewPanelProfile, MetricValue, train_source_candidate_delta(), client_review_direct_admission_production_is_source(), client_review_then_retrain_local_epochs() (+20 more)

### Community 51 - "ProtocolCellExecutor"
Cohesion: 0.07
Nodes (28): AllowSourceAsVerifier, CellHandlerName, Suggested Questions, Suggested Questions, MetricObservationKey, AdmissionStateObservation, load_prepared_evidence_counts(), PreparedEvidenceProvenanceError (+20 more)

### Community 52 - "fit_feature_moments"
Cohesion: 0.22
Nodes (13): math, FeatureMoments, FeatureStatistic, fit_feature_moments(), model_validator, Self, _statistic(), test_feature_moments_reject_inconsistent_lengths() (+5 more)

### Community 53 - "parse"
Cohesion: 0.13
Nodes (24): _dataset_files(), Path, test_dataset_public_functions_avoid_primitive_annotations(), test_datasets_do_not_import_replaced_tabular_libraries(), test_datasets_do_not_keep_manual_arrow_sqlite_abstractions(), test_preprocess_workflow_calls_materialize_functions(), generic_wrapper_violations(), Module (+16 more)

### Community 54 - "Roadmap.md"
Cohesion: 0.06
Nodes (33): 11.1 Secondary schema, labels, and raw-data adaptation, 11.2 Secondary domain proxies, 11.3 Secondary roles, 11. Secondary generalization dataset, 14. Final-gate and admission artifact semantics, 19.1 Scientific cell-phase boundaries, 19. Failure, null-result, and completion semantics, 20. Reference software and hardware environment (+25 more)

### Community 55 - "CertifiedReproductionRow"
Cohesion: 0.29
Nodes (26): CalibrationErrorCount, ClusterSize, DbscanEpsilon, MemberIndex, NumericalEpsilon, OptionalParameterSimilarity, PairwiseDistance, PairwiseDistanceMatrix (+18 more)

### Community 56 - "SeedDerivationLabel"
Cohesion: 0.05
Nodes (79): AttackCarrierRequired, FoldCount, FoldIndex, OrderItem, ScreenDifferential, ScreenDomainCount, ScreenDomainDecision, ProposalScreenConfig (+71 more)

### Community 57 - "test_domain_typing_hygiene.py"
Cohesion: 0.14
Nodes (26): _alias_bases(), _enum_class_names(), _enum_loop_variables(), _enum_member_unwrap(), enum_value_access_violations(), enum_value_in_comparison_violations(), forbidden_alias_symbol_violations(), expr (+18 more)

### Community 58 - "test_no_primitive_leaks.py"
Cohesion: 0.16
Nodes (25): arg, AsyncFunctionDef, _all_violations(), config_scalar_foundation_violations(), domain_identifier_violations(), _function_arguments(), function_boundary_primitive_violations(), model_field_primitive_violations() (+17 more)

### Community 59 - "FedSIRAApplication"
Cohesion: 0.33
Nodes (5): ApplicationExitCode, Console, FedSIRAApplication, OverwriteExisting, render()

### Community 60 - "ArtifactFamily"
Cohesion: 0.10
Nodes (44): CheckpointStageIdentity, Artifact dependency and invalidation matrix, artifact_identity(), ArtifactDependency, ArtifactSlot, ProcedureIdentity, ArtifactDependencyKind, ArtifactFamily (+36 more)

### Community 61 - "tables.py"
Cohesion: 0.13
Nodes (65): FormattedStatisticText, ReportCellLiteral, ReportColumnName, TableName, ComparisonFamilyResult, CollapseDecision, CollapseDecisionKind, _decision_for_kind() (+57 more)

### Community 62 - "boundary_metric_set"
Cohesion: 0.17
Nodes (16): 30.16 `Capability Under-Specification Boundary`, `Capability-Granularity Boundary`, FalseCertificationCount, FalseSameEquivalenceCheck, PredicateSatisfied, ScopedContractActive, FalseSameCapabilityReason, boundary_metric_set() (+8 more)

### Community 63 - "ciciot2023/test_acquisition.py"
Cohesion: 0.21
Nodes (23): discover_secondary_csv_files(), read_csv_header(), resolve_label_column(), validate_consistent_header(), compute_file_checksum(), CICIoT2023Acquisition, Path, skipif (+15 more)

### Community 64 - "ciciot2023/prepare.py"
Cohesion: 0.10
Nodes (57): DatasetColumnCount, FeatureMoment, PartitionSalt, _assign_secondary_roles(), _cap_case_sql(), compute_dataset_manifest_hash(), _create_preparation_tables(), _exclusion_reason_sql() (+49 more)

### Community 65 - "select_krum_update"
Cohesion: 0.16
Nodes (19): KrumNeighborCount, KrumScore, krum_neighbor_count(), krum_score(), AdequateFinalGateDomainCount, CommitteeSize, FinalGatePredicatesPass, MaximumByzantineReproductionRows (+11 more)

### Community 66 - "RuntimeComponentName"
Cohesion: 0.11
Nodes (25): Fresh audit, 2026-09-25, Audit findings, FrameType, Logger, logging, LogRecord, OperationResult, RuntimeError (+17 more)

### Community 67 - "protocol_evidence.py"
Cohesion: 0.09
Nodes (56): Percentile, artifact_instance_token(), ArtifactInstanceName, ArtifactInstanceToken, FramingField, ArtifactConfigurationComponent, ArtifactConfigurationScope, configuration_scope_dependency() (+48 more)

### Community 68 - "runtime.py"
Cohesion: 0.13
Nodes (28): concurrent_futures, contextlib, contextvars, datetime, os, random, RarArchivesPresent, resource (+20 more)

### Community 69 - "ciciot2023/schema.py"
Cohesion: 0.12
Nodes (25): _comparison_token(), ClassLabel, validate_label_collisions(), validate_target_label_present(), build_class_registry(), CICIoT2023TargetFamilyMember, _CICIoTBenignAlias, CICIoTRowIdentifierToken (+17 more)

### Community 70 - "16.2 Core and mechanism baselines"
Cohesion: 0.09
Nodes (22): 16.1 Common budget rules, 16.2 Core and mechanism baselines, 16.3 Prior-art family representatives, 16.4 Baseline fairness, 16. Baseline contracts, `Candidate-Free Full Path`, `Centralized Reference`, `Client Review then One Independent Retrain` (+14 more)

### Community 71 - "cli.py"
Cohesion: 0.21
Nodes (12): command, Per-command reachability, rich_console, plan(), preprocess(), OverwriteExisting, report(), run_experiment() (+4 more)

### Community 72 - "16.5 Baseline implementation completion rules"
Cohesion: 0.18
Nodes (11): 16.5 Baseline implementation completion rules, Baseline validation fixture map, Density-cluster baseline, FLCert-style ensemble, Parameter-similarity ablation, Reconstruction-filter calibration, Recovery baseline, Review-style baselines (+3 more)

### Community 73 - "35.2 Exact claim rules"
Cohesion: 0.10
Nodes (21): 35.1 State semantics, 35.2 Exact claim rules, 35. Claim-support decisions, `Authority Transition`, `Byzantine Operating Region`, `Conditional Non-Interference`, `Direct Source Exclusion`, `External Verification Necessity` (+13 more)

### Community 74 - "_repo.py"
Cohesion: 0.14
Nodes (21): AST, Name, stmt, module_level_constant_values(), Module, test_no_module_level_constants_duplicate_governed_values(), test_violation_detected_for_duplicated_constant(), _uppercase_targets() (+13 more)

### Community 75 - "load_scientific_config"
Cohesion: 0.17
Nodes (17): load_scientific_config(), Path, YamlValue, _read_yaml_mapping(), ScientificConfig, validate_scientific_config(), Path, test_config_is_immutable() (+9 more)

### Community 76 - "5. Core Engineering Rules"
Cohesion: 0.10
Nodes (18): 1. Think Before Coding, 2. Simplicity First, 3. Surgical Changes, 4. Goal-Driven Execution, 5. Core Engineering Rules, 6. Static Analysis and Automated Enforcement, 7. Testing Rules, 8. Definition of Done (+10 more)

### Community 77 - "30. Experiment registry"
Cohesion: 0.10
Nodes (20): 30.10 `Mechanism Ablation`, 30.11 `Compromised-Reproducer Robustness`, 30.12 `Compromised-Verifier Robustness`, 30.13 `Byzantine-Bound Violation`, 30.14 `Evidence Scarcity and Dormancy`, 30.15 `Shared Epistemic-Failure Boundary`, 30.17 `Heterogeneous-Reproduction Boundary`, 30.18 `Admission-Delay Decomposition` (+12 more)

### Community 78 - "33.2 Result tables"
Cohesion: 0.10
Nodes (20): 33.1 Protocol tables, 33.2 Result tables, 33.3 Table rounding/significance display, 33. Required manuscript tables, `Ablation Results`, `Baseline Protocol`, `Byzantine Robustness`, `Collapse Decisions` (+12 more)

### Community 79 - "iter_python_files"
Cohesion: 0.20
Nodes (15): modulefinder, test_production_has_no_repository_state_or_source_fingerprint_machinery(), temporary_marker_violations(), test_no_temporary_markers_in_repository_python_source(), test_no_unfinished_statements_in_production_source(), test_violation_detected_for_todo_marker(), test_violation_detected_for_unfinished_statements(), unfinished_statement_violations() (+7 more)

### Community 80 - "learning/training.py"
Cohesion: 0.15
Nodes (27): PreparedReproductionTargetCount, PreparedSupportedReplayCount, SmokeRenderText, AdmissionDelayDecomposition, WallClockSeconds, _model_invariants(), AdequateFinalGateDomainCount, run_data_and_domain_evidence_validation() (+19 more)

### Community 81 - "artifact_slot_directory"
Cohesion: 0.21
Nodes (20): artifact_family_directory_token(), artifact_slot_directory(), ArtifactInstanceLabel, comparison_evidence_failures(), comparison_evidence_slot(), metric_evidence_digest(), PersistedComparisonEvidence, publish_comparison_evidence() (+12 more)

### Community 82 - "15. Adversarial and diagnostic transformation registry"
Cohesion: 0.11
Nodes (18): 15.10 Transformation cardinality, root-cause, and controlled-episode completion rules, 15.1 Useful + hidden-backdoor source, 15.2 Byzantine reproduction strategies, 15.3 Byzantine verifier behavior, 15.4 Shared label-error boundary, 15.5 Shared spurious-feature boundary, 15.6 Attacker-induced common-context boundary, 15.7 Capability under-specification fixture (+10 more)

### Community 83 - "ElapsedTimer"
Cohesion: 0.12
Nodes (15): PeakMemoryBytes, SingleProcessTimingWorker, TimingWorkerObservation, CudaIntervalTimer, ElapsedTimer, peak_gpu_memory_bytes(), peak_host_resident_set_bytes(), WallClockSeconds (+7 more)

### Community 84 - "DescriptiveScientificMetric"
Cohesion: 0.27
Nodes (10): DescriptiveScientificMetric, declared_contract_scopes(), mean_of_defined(), observation_value(), observations_with_replacements(), permanent_singleton_admission(), EligibleEvidenceHolderCount, MetricName (+2 more)

### Community 85 - "types.py"
Cohesion: 0.17
Nodes (13): pydantic, RepositoryLayoutFailure, validate_repository_layout(), RepositoryRootName, model_validator, SeedCount, Self, SeedBundle (+5 more)

### Community 86 - "independent_local_reference_reviewer_is_positive"
Cohesion: 0.31
Nodes (8): ReviewerPositiveDecision, independent_local_reference_reviewer_is_positive(), CapabilityContractSatisfied, test_independent_local_reference_reviewer_negative_beyond_benign_far_margin(), test_independent_local_reference_reviewer_negative_beyond_supported_f1_margin(), test_independent_local_reference_reviewer_negative_when_capability_contract_fails(), test_independent_local_reference_reviewer_positive_within_noninferiority_margins(), test_secure_continual_assessment_post_reference_rounds_uses_governed_config()

### Community 87 - "test_commands.py"
Cohesion: 0.14
Nodes (4): doctor(), MonkeyPatch, test_doctor_exits_zero_when_environment_and_config_are_valid(), test_status_renders_planned_experiment_lifecycle()

### Community 88 - "24. Public CLI contract"
Cohesion: 0.25
Nodes (8): 24.1 `fedsira doctor`, 24.2 `fedsira preprocess ["N-BaIoT"|"CICIoT2023"]`, 24.3 `fedsira plan`, 24.4 `fedsira smoke`, 24.5 `fedsira status`, 24.6 `fedsira run <experiment name>`, 24.7 `fedsira report [<experiment name>]`, 24. Public CLI contract

### Community 89 - "17.2 Capability Contract metrics"
Cohesion: 0.12
Nodes (17): 17.2 Capability Contract metrics, Anchor training budgets and cadences, Benign false-alarm-rate increase, Checkpoint artifacts, Data loading, Metric adequacy minima, Persisted cell evidence and reuse, Persisted statistical comparison evidence (+9 more)

### Community 90 - "model_validator"
Cohesion: 0.17
Nodes (4): model_validator, SeedCount, Self, SeedsAndDeterminismConfig

### Community 92 - "18. Statistical analysis protocol"
Cohesion: 0.13
Nodes (15): 18.10 Rounding, 18.1 Experimental unit and pairing, 18.2 Primary hypothesis tests, 18.3 Alpha and multiplicity, 18.4 Effect sizes, 18.5 Confidence intervals, 18.6 Materiality criteria, 18.7 Collapse/survival rules (+7 more)

### Community 93 - "FedSIRA Pre-Experiment Audit Matrix"
Cohesion: 0.22
Nodes (8): 1. Purpose and scope, 2. Authority hierarchy, 3. Status and severity definitions, 5. Fresh Graphify / callable-count summary template, 6. Per-command / per-workflow callable-count template, 7. Required later audit execution order, 8. Final pre-experiment acceptance gate, FedSIRA Pre-Experiment Audit Matrix

### Community 94 - "test_no_duplicate_constants.py"
Cohesion: 0.43
Nodes (6): find_duplicate_constant_names(), module_constant_names(), Module, Path, test_no_constant_name_defined_in_more_than_one_module(), test_violation_detected_for_duplicate_constant_name()

### Community 95 - "apply_sampling_cap"
Cohesion: 0.24
Nodes (11): DatasetFileDigest, SamplingSelectionDigest, apply_sampling_cap(), ClassLabel, sampling_cap_selection_digest(), test_apply_sampling_cap_is_deterministic_across_runs(), test_apply_sampling_cap_returns_all_rows_when_under_the_cap(), test_apply_sampling_cap_selection_differs_by_role_and_class() (+3 more)

### Community 96 - "17.1 Classification metrics"
Cohesion: 0.14
Nodes (14): 17.1 Classification metrics, Accuracy, AUPRC, AUROC, Balanced Accuracy, F1 for class $c$, False-negative rate, False-positive rate (+6 more)

### Community 97 - "34. Required manuscript figures"
Cohesion: 0.14
Nodes (14): 34.10 `Heterogeneity Synthesis Boundary`, 34.11 `Admission-Delay Decomposition`, 34.12 `Efficiency Profile`, 34.13 `Secondary Generalization`, 34.1 `FedSIRA Protocol Schematic`, 34.2 `Primary Security–Utility Tradeoff`, 34.3 `Useful Backdoored Source`, 34.4 `Collapse Decision Effects` (+6 more)

### Community 98 - "test_no_any_dict_object.py"
Cohesion: 0.25
Nodes (13): annotation_occurrences(), annotation_violations(), forbidden_symbol_violations(), expr, Module, raw_mapping_violations(), test_any_annotation_is_detected(), test_dictionary_construction_is_detected() (+5 more)

### Community 99 - "test_workflow_call_topology.py"
Cohesion: 0.25
Nodes (13): _called_names(), _method_node(), FunctionDef, Path, test_application_wires_every_cli_command(), test_cli_only_dispatches_to_application(), test_opening_stage_observations_consume_the_callers_stage(), test_plan_workflow_reaches_plan_construction() (+5 more)

### Community 100 - "10. Exact data roles, sampling, and preprocessing"
Cohesion: 0.29
Nodes (7): 10.1 Supported-class role intervals, 10.2 Target-class role intervals, 10.3 Deterministic sampling caps, 10.4 Data validation, 10.5 Scaling, 10.6 Preprocessing semantic identity, 10. Exact data roles, sampling, and preprocessing

### Community 101 - "admission.py"
Cohesion: 0.11
Nodes (32): FinalGateArtifactValid, parametrize, PluralityActive, RealReportSummary, apply_production_update(), final_gate_decision(), final_gate_decision_from_production_checkpoint(), final_gate_predicates_pass() (+24 more)

### Community 102 - "apply_holm_adjustment"
Cohesion: 0.28
Nodes (9): MaterialityDecision, MultiplicityConfig, _adjusted_p_value(), _adjusted_result(), apply_holm_adjustment(), _materiality_passes(), ComparisonName, MetricDifference (+1 more)

### Community 103 - ".values"
Cohesion: 0.28
Nodes (9): ComparisonName, EvidenceCycleIndex, MasterSeed, MethodName, MetricName, MetricValue, RepetitionIndex, ScenarioName (+1 more)

### Community 104 - "evaluation/test_validation.py"
Cohesion: 0.27
Nodes (10): EvaluationValidationError, FailureMessage, ValueError, validate_metric_class_membership(), test_metric_class_membership_accepts_valid_configuration(), test_metric_class_membership_rejects_benign_outside_vocabulary(), test_metric_class_membership_rejects_supported_outside_vocabulary(), test_metric_class_membership_rejects_target_outside_vocabulary() (+2 more)

### Community 105 - "AblationVariant"
Cohesion: 0.15
Nodes (24): AblationScenario, AblationVariant, ablation_metric(), ablation_reproducer_strategy(), ablation_scenario_for_variant(), ablation_reference_cell(), MasterSeed, ScenarioName (+16 more)

### Community 106 - "BaselineIdentity"
Cohesion: 0.62
Nodes (6): BaselineIdentity, BaselineValidationFixture, _fixture_for(), test_fixture_map_covers_every_registered_baseline_exactly_once(), test_ordinary_utility_references_use_legitimate_target_capability(), test_robust_update_filtering_references_use_model_replacement_backdoor()

### Community 107 - "collections"
Cohesion: 0.19
Nodes (12): collections, acyclic_call_depth(), depth(), ast_inventory(), main(), production_callables(), json, re (+4 more)

### Community 108 - "18.9 Exact comparison registry"
Cohesion: 0.18
Nodes (11): 18.9 Exact comparison registry, Family 10 — secondary generalization, Family 1 — proposal-screen necessity, Family 2 — plurality necessity, Family 3 — source-exclusion central claim, Family 4 — external reproduction verification necessity, Family 5 — primary baseline comparisons, Family 6 — compromised-reproducer robustness (+3 more)

### Community 109 - "test_preprocess_plan_smoke.py"
Cohesion: 0.33
Nodes (3): _no_mismatches(), MonkeyPatch, test_doctor_command_reports_configuration_and_next_action()

### Community 110 - "13. Role assignment, seeds, security profiles, and deterministic ties"
Cohesion: 0.20
Nodes (10): 13.1 Master seeds, 13.2 Seed namespaces and canonical hash semantics, 13.3 Deterministic ordering instead of hidden RNG defaults, 13.4 Source selection, 13.5 Proposal-screen fold and matching semantics, 13.6 Primary deterministic verifier profile, 13.7 Diagnostic random verifier profile, 13.8 Compromised reproducer selection (+2 more)

### Community 111 - "7. Exact FedSIRA procedure"
Cohesion: 0.20
Nodes (10): 7.1 Admission opening, 7.2 Proposal screen, 7.3 Source-independent reproduction, 7.4 External verification, 7.5 Reproducibility certificate, 7.6 Robust source-excluded synthesis: Krum, 7.7 Final fresh gate, 7. Exact FedSIRA procedure (+2 more)

### Community 112 - "8. Theory and proof obligations"
Cohesion: 0.20
Nodes (10): 8.1 Pre-independent-evidence indistinguishability, 8.2 Independent evidence proposition, 8.3 Claim-conditional direct source-artifact non-interference, 8.4 Honest-support counting, 8.5 Synthesizer-specific reproduction count, 8.6 Conditional safety/liveness, 8.7 Independent-evidence delay lower bound, 8.8 Random-committee contamination calculation (+2 more)

### Community 113 - "test_robust_aggregation.py"
Cohesion: 0.27
Nodes (9): NonAbstainingReproductionSeries, ParticipantCount, ThreeRowCoordinateMedianConfig, direct_krum_committee_rows(), CommitteeSize, validate_three_row_coordinate_median_committee_size(), test_direct_krum_committee_rows_filters_abstaining_and_requires_committee_size(), test_direct_krum_committee_rows_none_when_insufficient_non_abstaining_rows() (+1 more)

### Community 114 - "test_enum_integrity.py"
Cohesion: 0.40
Nodes (9): annotation_names(), enum_class_defs(), ClassDef, Module, Path, test_enum_used_only_as_its_own_annotation_is_still_flagged(), test_every_enum_is_referenced_outside_or_used_as_a_typed_field(), test_violation_detected_for_unused_enum() (+1 more)

### Community 116 - ".run"
Cohesion: 0.14
Nodes (12): Fresh Graphify callable inventory — final pass, Prospective experiment workflow counts, Union, Dynamic protocol dispatch, Production call-graph audit — final snapshot, Runtime boundaries, Completed discovery, Findings so far (+4 more)

### Community 118 - "test_no_comments_or_docstrings.py"
Cohesion: 0.33
Nodes (8): io, has_comment_token(), has_docstring(), Module, test_no_comments_or_docstrings_in_repository_python_source(), test_violation_detected_for_comment(), test_violation_detected_for_docstring(), tokenize

### Community 119 - "test_no_test_only_production_code.py"
Cohesion: 0.42
Nodes (8): occurrence_count(), public_top_level_symbols(), Module, Path, referenced_in(), test_no_public_production_symbol_used_only_by_tests(), test_symbol_used_elsewhere_in_its_own_file_counts_as_used(), test_violation_detected_for_test_only_symbol()

### Community 120 - "test_public_type_boundaries.py"
Cohesion: 0.42
Nodes (8): is_fully_annotated(), public_top_level_functions(), FunctionDef, Module, test_compliant_function_passes(), test_public_boundary_functions_are_fully_annotated(), test_violation_detected_for_unannotated_public_function(), violations_in_tree()

### Community 121 - "test_enums.py"
Cohesion: 0.22
Nodes (8): test_artifact_lifecycle_state_members(), test_cell_phase_state_members(), test_dataset_id_has_exactly_the_two_roadmap_datasets(), test_enum_members_are_not_equal_to_plain_strings_by_construction(), test_experiment_lifecycle_state_members(), test_failure_class_has_exactly_nine_classes(), test_scientific_cell_phase_has_exactly_six_phases(), test_seed_derivation_label_retains_the_fifteen_namespace_tokens()

### Community 122 - "Graph Report - FedSIRA  (2026-09-15)"
Cohesion: 0.25
Nodes (7): Community Hubs (Navigation), Corpus Check, Graph Freshness, Graph Report - FedSIRA  (2026-09-15), Import Cycles, Knowledge Gaps, Summary

### Community 123 - "Graph Report - FedSIRA  (2026-09-15)"
Cohesion: 0.25
Nodes (7): Community Hubs (Navigation), Corpus Check, Graph Freshness, Graph Report - FedSIRA  (2026-09-15), Import Cycles, Knowledge Gaps, Summary

### Community 124 - "9. Primary dataset and experimental domain construction"
Cohesion: 0.25
Nodes (8): 9.1.1 Raw release discovery and canonical mapping, 9.1 Primary dataset, 9.2 Domain proxies, 9.3 Class vocabulary, 9.4 Post-reference capability, 9.5 Supported classes, 9.6 Controlled replay semantics, 9. Primary dataset and experimental domain construction

### Community 125 - "test_no_free_string_enum_bypass.py"
Cohesion: 0.50
Nodes (7): enum_member_values(), Module, Path, string_literals(), test_no_free_string_enum_value_bypass_across_modules(), test_owner_module_usage_not_flagged(), test_violation_detected_for_free_string_enum_value()

### Community 126 - "CLI workflow traces"
Cohesion: 0.22
Nodes (8): CLI workflow traces, `doctor`, `plan`, `preprocess [dataset] [--overwrite]`, `report [ExperimentName] [--overwrite]`, `run <ExperimentName> [--overwrite]` (prospective only), `smoke [--overwrite]`, `status`

### Community 127 - "12. Model, anchor training, source training, and reproduction training"
Cohesion: 0.29
Nodes (7): 12.1 Base classifier, 12.2 Common optimizer and loss constants, 12.3 Anchor FedAvg, 12.4 Post-reference training contract, 12.5 Verifier-aware malicious training override, 12.6 No test-set tuning, 12. Model, anchor training, source training, and reproduction training

### Community 128 - "26. Scientific output contract"
Cohesion: 0.29
Nodes (7): 26.1 Scientific execution dependencies, 26.2 Artifact validity and lifecycle, 26.3 Reusable artifact families, 26.4 Selective invalidation boundaries, 26.5 Experiment dependency and reuse map, 26.6 Cross-experiment reuse rules, 26. Scientific output contract

### Community 129 - "28. Validation and smoke-test contract"
Cohesion: 0.29
Nodes (7): 28.1 Data tests, 28.2 Model/FL tests, 28.3 Protocol invariant tests, 28.4 Mathematical tests, 28.5 Metric/statistical tests, 28.6 Artifact reuse and recovery tests, 28. Validation and smoke-test contract

### Community 131 - "test_config_as_parameter.py"
Cohesion: 0.43
Nodes (6): _annotation_names(), config_parameter_violations(), expr, Module, test_production_functions_do_not_take_scientific_config(), test_violation_detected_for_public_config_parameter()

### Community 133 - "17.4 Cross-domain distribution metrics"
Cohesion: 0.33
Nodes (6): 10th-percentile domain target F1, 17.4 Cross-domain distribution metrics, Coefficient of variation, Domain disparity, IQR, Worst-domain target F1

### Community 134 - "17. Metric registry and mathematical definitions"
Cohesion: 0.33
Nodes (6): 17.5 Candidate-screen metrics, 17.6 Delay metrics, 17.7 Efficiency and communication metrics, 17.8 Aggregation and evaluation populations, 17.9 Missing and undefined metric policy, 17. Metric registry and mathematical definitions

### Community 135 - "1. Scientific problem, contribution boundary, and claims"
Cohesion: 0.33
Nodes (6): 1.1 Research problem, 1.2 Core authority transition, 1.3 Required mechanism, 1.4 Safe manuscript claims, 1.5 Forbidden claims, 1. Scientific problem, contribution boundary, and claims

### Community 136 - "17.10 Additional specified metrics"
Cohesion: 0.40
Nodes (5): 17.10 Additional specified metrics, Clean-oracle degradation, Descriptive confidence intervals for method summaries, False same-capability certification rate, Protocol-specific aggregation sufficiency

### Community 137 - "17.3 Security and admission metrics"
Cohesion: 0.40
Nodes (5): 17.3 Security and admission metrics, Abstention/dormancy rate, Attack Success Rate, Legitimate admission rate, Malicious admission rate

### Community 138 - "4. Threat model, trust assumptions, and explicit boundaries"
Cohesion: 0.40
Nodes (5): 4.1 Primary security setting, 4.2 Attacker knowledge, 4.3 Honest-path assumptions, 4.4 Failure boundaries that must be tested, 4. Threat model, trust assumptions, and explicit boundaries

### Community 139 - "6. FedSIRA state machine and non-negotiable invariants"
Cohesion: 0.40
Nodes (5): 6.1 States, 6.2 Resource horizon, 6.3 Exact transition and scheduling table, 6.4 Invariants, 6. FedSIRA state machine and non-negotiable invariants

### Community 140 - "FedSIRA"
Cohesion: 0.40
Nodes (4): CLI usage, FedSIRA, Reproducibility, Setup

### Community 142 - "_ListConvertibleTensor"
Cohesion: 0.50
Nodes (3): ModelParameterValue, _ListConvertibleTensor, Protocol

### Community 185 - "recovery_backdoor_alarm_threshold"
Cohesion: 0.60
Nodes (5): MetricValue, recovery_alarm_threshold(), recovery_backdoor_alarm_threshold(), recovery_rollback_is_triggered(), test_recovery_alarm_threshold_and_rollback_trigger_paths()

## Knowledge Gaps
- **596 isolated node(s):** `fedsira`, `graphify`, `1. Think Before Coding`, `2. Simplicity First`, `3. Surgical Changes` (+591 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1105 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **41 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExperimentName` connect `ExperimentName` to `figures.py`, `service.py`, `AdmissionState`, `application.py`, `Role`, `models.py`, `handlers.py`, `FrozenDomainModel`, `comparisons.py`, `paths.py`, `test_experiment_registry_contracts.py`, `CellExecutionOutcome`, `enums.py`, `ablation_reference_records`, `MetricResult`, `planning.py`, `store.py`, `collapse.py`, `definitions.py`, `publication.py`, `ProtocolCellExecutor`, `FedSIRAApplication`, `ArtifactFamily`, `tables.py`, `protocol_evidence.py`, `cli.py`, `artifact_slot_directory`, `types.py`, `.values`, `.run`?**
  _High betweenness centrality (0.103) - this node is a cross-community bridge._
- **Why does `Graph Report - FedSIRA  (2026-09-15)` connect `Graph Report - FedSIRA  (2026-09-15)` to `Communities (193 total, 3 thin omitted)`, `MetricResult`, `ProtocolCellExecutor`, `NBaiotClass`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Why does `Communities (193 total, 3 thin omitted)` connect `Communities (193 total, 3 thin omitted)` to `Graph Report - FedSIRA  (2026-09-15)`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `current_application_context()` (e.g. with `test_standard_fl_baseline_budget_reads_yaml()` and `test_declared_poison_sweep_comes_from_configuration()`) actually correct?**
  _`current_application_context()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 35 inferred relationships involving `FrozenDomainModel` (e.g. with `CalibrationErrorCount` and `CellHandlerName`) actually correct?**
  _`FrozenDomainModel` has 35 INFERRED edges - model-reasoned connections that need verification._
- **Are the 144 inferred relationships involving `ExperimentName` (e.g. with `God Nodes (most connected - your core abstractions)` and `Suggested Questions`) actually correct?**
  _`ExperimentName` has 144 INFERRED edges - model-reasoned connections that need verification._
- **Are the 96 inferred relationships involving `AdmissionState` (e.g. with `AdmissionStateIsTerminal` and `CellHandlerName`) actually correct?**
  _`AdmissionState` has 96 INFERRED edges - model-reasoned connections that need verification._