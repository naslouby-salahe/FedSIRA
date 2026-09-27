# Graph Report - FedSIRA  (2026-09-26)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 4086 nodes · 15884 edges · 186 communities (142 shown, 44 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 3047 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9449c601`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- common.py
- FedSIRAClassifier
- current_application_context
- DatasetAdapter
- service.py
- baselines/training.py
- ciciot2023/prepare.py
- ArtifactFamily
- export.py
- application.py
- figures.py
- handlers.py
- ExperimentLifecycleState
- DatasetId
- tables.py
- models.py
- defenses.py
- comparisons.py
- nbaiot/prepare.py
- NBaiotClass
- execution.py
- federated.py
- collapse.py
- store.py
- paths.py
- ExperimentName
- enums.py
- runtime.py
- config.py
- pathlib
- planning.py
- protocol/test_verification.py
- nbaiot_adapter
- framed_bytes
- ciciot2023/test_preprocessing.py
- metrics.py
- parse
- Roadmap.md
- FrozenDomainModel
- learning/training.py
- ArtifactSlot
- test_metrics.py
- Role
- rules.py
- protocol/test_reproduction.py
- test_common.py
- iter_python_files
- test_no_primitive_leaks.py
- model_validator
- 4. Audit requirements
- test_determinism.py
- test_theory.py
- CertifiedReproductionRow
- ReproducerCondition
- evaluation/test_aggregation.py
- 16.5 Baseline implementation completion rules
- exact_sign_flip_two_sided_p_value
- MetricResult
- ciciot2023/test_acquisition.py
- run_smoke_suite
- test_experiment_registry_contracts.py
- ast
- boundary_metric_set
- 35.2 Exact claim rules
- test_no_hardcoded_values.py
- AdmissionOpeningMode
- baselines/test_registry.py
- 5. Core Engineering Rules
- 30. Experiment registry
- 33.2 Result tables
- RuntimeComponentName
- load_scientific_config
- protocol_tables.py
- .run
- .values
- discover_primary_csv_files
- AblationVariant
- test_workflow_call_topology.py
- 15. Adversarial and diagnostic transformation registry
- screen_fold_index
- 17.2 Capability Contract metrics
- _diagnostic_marker_for_domain
- cli.py
- 18. Statistical analysis protocol
- fit_feature_moments
- test_no_any_dict_object.py
- apply_sampling_cap
- 17.1 Classification metrics
- 34. Required manuscript figures
- select_krum_update
- test_comparison_evidence.py
- FailureClass
- independent_local_reference_reviewer_is_positive
- load_published_manifests
- build_comparison_results_for_experiment
- CLI workflow traces
- evaluation/test_validation.py
- FedSIRAApplication
- 18.9 Exact comparison registry
- test_preprocess_plan_smoke.py
- test_commands.py
- Scientific and workflow test crosswalk
- 10. Exact data roles, sampling, and preprocessing
- 13. Role assignment, seeds, security profiles, and deterministic ties
- 16.2 Core and mechanism baselines
- 7. Exact FedSIRA procedure
- 8. Theory and proof obligations
- direct_krum_committee_rows
- test_enum_integrity.py
- Final audit evidence
- FedSIRA Pre-Experiment Audit Matrix
- prepared_validation.py
- test_no_comments_or_docstrings.py
- test_dataset_subsystem.py
- test_no_redirects_shims_reexports.py
- test_public_type_boundaries.py
- test_validation_run_path.py
- first_cycle_with_minimum_eligible_evidence_holders
- 24. Public CLI contract
- 9. Primary dataset and experimental domain construction
- pytest
- BaselineIdentity
- test_no_free_string_enum_bypass.py
- test_run_status_report.py
- test_enums.py
- 12. Model, anchor training, source training, and reproduction training
- 26. Scientific output contract
- 28. Validation and smoke-test contract
- ProtocolPhaseDurations
- test_config_as_parameter.py
- 17.4 Cross-domain distribution metrics
- 17. Metric registry and mathematical definitions
- 1. Scientific problem, contribution boundary, and claims
- minimum_honest_positive_count
- reproduction_stage_identity
- background-jobs.md
- 17.10 Additional specified metrics
- 17.3 Security and admission metrics
- 4. Threat model, trust assumptions, and explicit boundaries
- FedSIRA
- malicious_admission_rate
- StructuredJsonFormatter
- _ListConvertibleTensor
- baseline_calibration_rule
- .__init__
- AGENTS.md
- claim-evidence-map.md
- library-audit.md
- fedsira

## God Nodes (most connected - your core abstractions)
1. `current_application_context()` - 224 edges
2. `FrozenDomainModel` - 201 edges
3. `ExperimentName` - 188 edges
4. `AdmissionState` - 172 edges
5. `MetricResult` - 149 edges
6. `ScientificCell` - 142 edges
7. `DatasetId` - 126 edges
8. `ExperimentLifecycleState` - 118 edges
9. `ArtifactFamily` - 102 edges
10. `ProtocolCellDispatch` - 99 edges

## Surprising Connections (you probably didn't know these)
- ``preprocess [dataset] [--overwrite]`` --references--> `DatasetId`  [INFERRED]
  docs/.audit/cli-workflows.md → src/fedsira/domain/enums.py
- ``doctor`` --references--> `DoctorReport`  [INFERRED]
  docs/.audit/cli-workflows.md → src/fedsira/application.py
- `17.7 Efficiency and communication metrics` --references--> `dataset_manifest_hash()`  [INFERRED]
  docs/Roadmap.md → src/fedsira/datasets/common.py
- `Remaining test-coverage actions` --references--> `test_no_public_production_symbol_used_only_by_tests()`  [INFERRED]
  docs/.audit/test-audit.md → tests/architecture/test_no_test_only_production_code.py
- `13.2 Seed namespaces and canonical hash semantics` --references--> `local_training_seed()`  [INFERRED]
  docs/Roadmap.md → src/fedsira/runtime.py

## Import Cycles
- 3-file cycle: `src/fedsira/experiments/collapse.py -> src/fedsira/experiments/engine.py -> src/fedsira/experiments/execution.py -> src/fedsira/experiments/collapse.py`
- 3-file cycle: `src/fedsira/evaluation/comparison_evidence.py -> src/fedsira/experiments/engine.py -> src/fedsira/experiments/execution.py -> src/fedsira/evaluation/comparison_evidence.py`

## Communities (186 total, 44 thin omitted)

### Community 0 - "common.py"
Cohesion: 0.04
Nodes (109): AttackCount, enum, FeatureName, FeatureShiftSign, HeterogeneityMultiplier, OrderItem, PreparedEvidencePresent, specification() (+101 more)

### Community 1 - "FedSIRAClassifier"
Cohesion: 0.05
Nodes (94): DeltaScale, math, PostReferenceConfig, TrainingConfig, supported_replay_cap_for_target_role(), FedSIRAClassifier, flatten_trainable_parameters(), TrainableParameterCount (+86 more)

### Community 2 - "current_application_context"
Cohesion: 0.09
Nodes (43): CompromisedProductionAncestry, DiscardSourceWeights, Architecture responsibility review, Follow-up findings, Deliberate narrow workflows, Disposition, Experiment scientific-subsystem review, Per-experiment prospective CLI-to-leaf workflows (+35 more)

### Community 3 - "DatasetAdapter"
Cohesion: 0.05
Nodes (82): AttackCarrierRequired, ClassCount, collections, FeatureSchemaDigest, RoleHashToken, EvidenceMinimaConfig, DatasetAdapter, domain_is_reproduction_adequate() (+74 more)

### Community 4 - "service.py"
Cohesion: 0.06
Nodes (81): CommunicationMessageCount, DomainT, FinalGateArtifactValid, parametrize, PluralityActive, HeterogeneityScope, RealAnchor, RootCauseScope (+73 more)

### Community 5 - "baselines/training.py"
Cohesion: 0.07
Nodes (81): Production callables outside the prospective CLI union, DomainLocalEvaluation, SourceAvailable, flat_parameters_identity(), AlgorithmName, triggered_to_benign_rate(), LocalTrainingClient, ArtifactDigest (+73 more)

### Community 6 - "ciciot2023/prepare.py"
Cohesion: 0.07
Nodes (79): DatasetColumnCount, FeatureMoment, PartitionSalt, re, _assign_secondary_roles(), _cached_view_is_reusable(), _cap_case_sql(), CICIoTPreparedViewMetadata (+71 more)

### Community 7 - "ArtifactFamily"
Cohesion: 0.09
Nodes (73): Artifact dependency and invalidation matrix, ArtifactConfigurationComponent, ArtifactConfigurationScope, ArtifactDependency, ArtifactManifest, configuration_scope_dependency(), ArtifactDependencyKind, ArtifactDependencyLabel (+65 more)

### Community 8 - "export.py"
Cohesion: 0.07
Nodes (76): pandas, ReportRowIdentity, _collapse_experiment_completed(), _materialize_core_if_complete(), dataset_readiness(), collapse_evaluation_from_records(), materialize_resolved_core(), current_execution_records() (+68 more)

### Community 9 - "application.py"
Cohesion: 0.06
Nodes (70): DeterministicExecutionReady, CLI to application roots, DoctorArtifactSummary, DoctorExperimentSummary, NextValidAction, ProjectProgressDescription, RarArchivesPresent, RunRenderText (+62 more)

### Community 10 - "figures.py"
Cohesion: 0.08
Nodes (73): Axes, AxisDraw, BoundarySeries, FigureAnnotationText, FigureAxisLabel, FigureLegendText, matplotlib_axes, FigureAxisName (+65 more)

### Community 11 - "handlers.py"
Cohesion: 0.05
Nodes (67): AdmissionStateIsTerminal, dataclasses, NewlyAdequateEvidenceExists, ProductionWeight, ReproductionRowCertified, ReproductionRowId, SourceExcludedFromKrum, SourceIsProductionUpdate (+59 more)

### Community 12 - "ExperimentLifecycleState"
Cohesion: 0.10
Nodes (63): CellCompletionStatus, csv, matplotlib_figure, _export_completed_experiment(), CoreMethodIdentity, ExperimentLifecycleState, CellExecutionOutcome, experiment_execution_digest() (+55 more)

### Community 13 - "DatasetId"
Cohesion: 0.09
Nodes (62): DatasetManifestPayload, artifact_staging_root(), current_repository_root(), preprocessing_extraction_cache_root(), CICIoT2023DatasetManifestPayload, RawDatasetFileIdentity, RawDatasetIdentityPayload, ScalerMetadata (+54 more)

### Community 14 - "tables.py"
Cohesion: 0.13
Nodes (62): FormattedStatisticText, ResolvedCoreIdentity, ReportCellLiteral, ReportColumnName, TableName, ComparisonFamilyResult, ResolvedCore, render_mandatory_tables() (+54 more)

### Community 15 - "models.py"
Cohesion: 0.06
Nodes (50): ByteCount, EncodedBytes, inspect, json, LengthPrefixBytes, ModelTransmissionCount, ModelTransmissionPresent, communication_bytes() (+42 more)

### Community 16 - "defenses.py"
Cohesion: 0.06
Nodes (60): ClassIndex, GroupCount, GroupIndex, certified_ensemble_domain_groups(), _cluster_members(), cosine_distance(), cosine_distance_matrix(), density_cluster_labels() (+52 more)

### Community 17 - "comparisons.py"
Cohesion: 0.11
Nodes (61): ComparisonReferenceLabel, MaterialityDecision, MultiplicityConfig, ComparisonFamily, ComparisonMetric, _ablation_comparisons(), ablation_material_threshold(), _adjusted_p_value() (+53 more)

### Community 18 - "nbaiot/prepare.py"
Cohesion: 0.08
Nodes (58): AttackBasename, AttackFamilyName, PathToken, RetainMaterializedViews, compute_file_checksum(), _cached_view_is_reusable(), _cast_feature_select(), classes_structurally_unavailable() (+50 more)

### Community 19 - "NBaiotClass"
Cohesion: 0.08
Nodes (54): duckdb, RoleSamplingCap, assign_stream_roles_and_sample_ids(), ArtifactDigest, DomainId, RelativePathText, SamplingCap, RoleAssignment (+46 more)

### Community 20 - "execution.py"
Cohesion: 0.08
Nodes (52): CellHandlerName, Dynamic protocol dispatch, Production call-graph audit — current snapshot, Runtime boundaries, prepared_evidence_root(), configuration_digest(), configure_artifact_logging(), CodeRevision (+44 more)

### Community 21 - "federated.py"
Cohesion: 0.09
Nodes (53): EvaluationCadenceReached, PreparedReproductionTargetCount, PreparedSupportedReplayCount, SmokeRenderText, AnchorFedAvgConfig, OptimizerConfig, AdmissionDelayDecomposition, WallClockSeconds (+45 more)

### Community 22 - "collapse.py"
Cohesion: 0.08
Nodes (53): MinimumCompletePairCount, _best_passed_metric(), _collapse_comparator(), collapse_decision_from_comparison_families(), CollapseDecision, CollapseDecisionKind, CollapseEvaluationInput, _constraints_pass() (+45 more)

### Community 23 - "store.py"
Cohesion: 0.10
Nodes (51): ArtifactComplete, ArtifactPayloadBytes, ArtifactSerializedText, ArtifactCurrentPointer, ArtifactLogFields, compute_checksum(), _configuration_scope_digest(), current_pointer_path() (+43 more)

### Community 24 - "paths.py"
Cohesion: 0.11
Nodes (49): Repository path ownership review, Root owners, Static inventory, artifact_log_path(), artifact_publication_root(), execution_outputs_root(), execution_workspace_root(), experiment_execution_root() (+41 more)

### Community 25 - "ExperimentName"
Cohesion: 0.10
Nodes (37): ExperimentName, SourceExclusionMethod, ExecutionRecordStore, PersistedExecutionRecord, Path, ScientificCellSemanticKey, _cell(), _completed_outcome() (+29 more)

### Community 26 - "enums.py"
Cohesion: 0.11
Nodes (47): ArtifactFileName, FeatureShiftMagnitude, AblationScenario, ArtifactFileToken, BoundCondition, ByteUnit, CublasWorkspaceConfig, DelayPhaseMetric (+39 more)

### Community 27 - "runtime.py"
Cohesion: 0.06
Nodes (41): collections_abc, concurrent_futures, datetime, DecileBinIndex, itertools, numpy, PeakMemoryBytes, pydantic (+33 more)

### Community 28 - "config.py"
Cohesion: 0.08
Nodes (45): RoleBoundary, RoleInterval, AttackerInducedCommonContextConfig, AttacksAndBoundariesConfig, BaselinesConfig, BootstrapConfig, ByzantineOperatingRegionConfig, ByzantineReproductionConfig (+37 more)

### Community 29 - "pathlib"
Cohesion: 0.08
Nodes (29): main(), run_worker(), main(), run_worker(), os, pathlib, subprocess, sys (+21 more)

### Community 30 - "planning.py"
Cohesion: 0.10
Nodes (37): PlanRenderText, baseline_validation_fixture_for_method(), ExperimentDefinition, MethodName, _ablation_cells(), _ablation_condition(), _baseline_validation_cells(), build_plan() (+29 more)

### Community 31 - "protocol/test_verification.py"
Cohesion: 0.08
Nodes (40): AllowSourceAsVerifier, MonotonicTimestamp, OneVotePerDomain, byzantine_selection_order(), construct_above_bound_panel(), deterministic_verifier_panel(), diagnostic_committee_panel(), panel_votes_are_one_per_domain() (+32 more)

### Community 32 - "nbaiot_adapter"
Cohesion: 0.14
Nodes (22): nbaiot_adapter(), Path, ReviewPanelProfile, MetricValue, train_source_candidate_delta(), ReviewerCount, review_panel_requirements(), validate_client_review_reviewer_count() (+14 more)

### Community 33 - "framed_bytes"
Cohesion: 0.11
Nodes (37): contextlib, contextvars, FramedBytes, ScoringTransformName, artifact_instance_token(), ArtifactInstanceName, ArtifactInstanceToken, FramingField (+29 more)

### Community 34 - "ciciot2023/test_preprocessing.py"
Cohesion: 0.15
Nodes (36): IntEnum, assign_secondary_roles(), CICIoT2023PseudoDomain, DomainId, DatasetExclusionReason, StrEnum, _per_attack_csv_file(), Path (+28 more)

### Community 35 - "metrics.py"
Cohesion: 0.13
Nodes (37): OptionalTriggeredSampleMaskSeries, ReproductionOpportunityCount, sklearn_metrics, DomainTargetMetrics, ConfusionCounts, benign_false_alarm_rate(), compute_confusion_counts(), compute_confusion_counts_by_class() (+29 more)

### Community 36 - "parse"
Cohesion: 0.13
Nodes (36): _alias_bases(), _enum_class_names(), _enum_loop_variables(), _enum_member_unwrap(), enum_value_access_violations(), enum_value_in_comparison_violations(), forbidden_alias_symbol_violations(), expr (+28 more)

### Community 37 - "Roadmap.md"
Cohesion: 0.05
Nodes (36): 11.1 Secondary schema, labels, and raw-data adaptation, 11.2 Secondary domain proxies, 11.3 Secondary roles, 11. Secondary generalization dataset, 14. Final-gate and admission artifact semantics, 19.1 Scientific cell-phase boundaries, 19. Failure, null-result, and completion semantics, 20. Reference software and hardware environment (+28 more)

### Community 38 - "FrozenDomainModel"
Cohesion: 0.14
Nodes (34): RepositoryPath, artifact_family_directory_token(), artifact_slot_directory(), FrozenDomainModel, BaseModel, CapabilityScope, content_digest(), publish_table_figure_export() (+26 more)

### Community 39 - "learning/training.py"
Cohesion: 0.12
Nodes (31): BatchRowIndexSequence, BatchSize, DataLoader, build_epoch_batches(), DeclaredBatchDataset, ordered_batch_indices(), ordered_batch_row_indices(), ordered_minibatches() (+23 more)

### Community 40 - "ArtifactSlot"
Cohesion: 0.11
Nodes (28): artifact_identity(), ArtifactSlot, ProcedureIdentity, validate_artifact_lifecycle_readable(), ArtifactLifecycleState, ablation_reference_records(), artifact_invariants(), ablation_reference_slot() (+20 more)

### Community 41 - "test_metrics.py"
Cohesion: 0.08
Nodes (31): AdmissionCount, BinaryLabelMaskSeries, ReproductionAttemptCount, ProposalOracleLabel, accuracy(), attack_success_rate_within_domain(), auprc_one_vs_rest(), auroc_one_vs_rest() (+23 more)

### Community 42 - "Role"
Cohesion: 0.13
Nodes (29): Dataset adapter equivalence review, SamplingCapsPerDomain, PreparedViewSidecar, BooleanValue, SamplingCap, sampling_cap_for_role(), _supported_sampling_cap(), _target_sampling_cap() (+21 more)

### Community 43 - "rules.py"
Cohesion: 0.19
Nodes (29): EvidenceArrivalCycleSequence, EvidenceArrivalSchedule, compute_t_evidence(), cycle_when_requirement_met(), first_holder_cycle_for_domain(), holder_count_at_cycle(), _holder_counts_by_cycle(), holders_at_cycle() (+21 more)

### Community 44 - "protocol/test_reproduction.py"
Cohesion: 0.10
Nodes (28): ExternalVerificationActive, compute_reproduction_commitment_hash(), consumed_domains(), handle_adequate_domain_trained(), handle_no_adequate_unconsumed_domain(), next_reproducer_domain(), CompromisedReproducerCount, DerivedSeed (+20 more)

### Community 45 - "test_common.py"
Cohesion: 0.10
Nodes (23): RolePosition, RoleWindowContainsSample, SampleIdPrefix, compute_sample_id(), RelativePathText, role_for_normalized_position(), RoleWindow, supported_role_windows() (+15 more)

### Community 46 - "iter_python_files"
Cohesion: 0.13
Nodes (23): modulefinder, test_no_stale_project_or_algorithm_aliases(), test_violation_detected_for_milestone_or_issue_reference(), test_violation_detected_for_stale_alias(), vocabulary_violations(), occurrence_count(), public_top_level_symbols(), Module (+15 more)

### Community 47 - "test_no_primitive_leaks.py"
Cohesion: 0.15
Nodes (27): arg, AsyncFunctionDef, _all_violations(), config_scalar_foundation_violations(), domain_identifier_violations(), _function_arguments(), function_boundary_primitive_violations(), model_field_primitive_violations() (+19 more)

### Community 48 - "model_validator"
Cohesion: 0.11
Nodes (13): AdmissionOpeningConfig, DataLoaderConfig, DatasetsConfig, DiagnosticRandomVerifierProfileConfig, FinalGateConfig, HiddenSourceBackdoorConfig, model_validator, SeedCount (+5 more)

### Community 49 - "4. Audit requirements"
Cohesion: 0.12
Nodes (23): ConfidenceIntervalBound, 4. Audit requirements, EffectSize, ClaimId, ClaimState, ScientificCellSemanticKey, ComparisonResult, evaluate_comparison() (+15 more)

### Community 50 - "test_determinism.py"
Cohesion: 0.10
Nodes (26): sort_key(), local_training_seed(), minibatch_order(), sort_key(), namespace_seed(), CheckpointIdentity, DatasetManifestDigest, DerivedSeed (+18 more)

### Community 51 - "test_theory.py"
Cohesion: 0.10
Nodes (19): AtLeastTwoByzantineProbability, EligiblePoolSize, fractions, KrumCommitteeAdmissible, diagnostic_at_least_two_byzantine_probability(), krum_committee_is_admissible(), krum_minimum_committee_size(), ByzantineDomainCount (+11 more)

### Community 52 - "CertifiedReproductionRow"
Cohesion: 0.29
Nodes (26): CalibrationErrorCount, ClusterSize, DbscanEpsilon, MemberIndex, NumericalEpsilon, OptionalParameterSimilarity, PairwiseDistance, PairwiseDistanceMatrix (+18 more)

### Community 53 - "ReproducerCondition"
Cohesion: 0.13
Nodes (16): ReproducerCondition, VerifierCondition, compromised_reproducer_count(), compromised_verifier_count(), ByzantineDomainCount, CompromisedReproducerCount, ConditionName, validate_byzantine_vocabulary() (+8 more)

### Community 54 - "evaluation/test_aggregation.py"
Cohesion: 0.11
Nodes (23): MatchedControlCount, MinimumDefinedDomainCount, coefficient_of_variation(), match_nearest_within_decile(), minimum_defined_domain_count(), DomainCount, Probability, SampleId (+15 more)

### Community 55 - "16.5 Baseline implementation completion rules"
Cohesion: 0.09
Nodes (23): 16.1 Common budget rules, 16.3 Prior-art family representatives, 16.4 Baseline fairness, 16.5 Baseline implementation completion rules, 16. Baseline contracts, Baseline validation fixture map, Density-cluster baseline, `Density-Cluster Trimmed Mean` (+15 more)

### Community 56 - "exact_sign_flip_two_sided_p_value"
Cohesion: 0.13
Nodes (21): NamedPValue, SignFlipAssignment, SignFlipSampleCount, enumerate_sign_flip_assignments(), exact_sign_flip_non_inferiority_p_value(), exact_sign_flip_two_sided_p_value(), holm_adjusted_p_values(), ComparisonMargin (+13 more)

### Community 57 - "MetricResult"
Cohesion: 0.15
Nodes (23): ScreenDomainDecision, MetricResult, benign_false_alarm_rate_increase(), undefined_metric(), domain_disparity(), interquartile_range(), percentile_10_domain_target_f1(), candidate_free_screen_domain_predicate() (+15 more)

### Community 58 - "ciciot2023/test_acquisition.py"
Cohesion: 0.22
Nodes (22): discover_secondary_csv_files(), read_csv_header(), resolve_label_column(), validate_consistent_header(), CICIoT2023Acquisition, Path, skipif, test_compute_file_checksum_is_a_sha256_hex_digest() (+14 more)

### Community 59 - "run_smoke_suite"
Cohesion: 0.22
Nodes (20): SmokeCheckName, _data_invariants(), _extended_mathematical_invariants(), _load_persisted_smoke_record(), _mathematical_invariants(), _protocol_invariants(), run_smoke_suite(), PersistedSmokeRecord (+12 more)

### Community 60 - "test_experiment_registry_contracts.py"
Cohesion: 0.11
Nodes (20): experiment_names(), experiment_registry(), efficiency_repetition_indices(), RepetitionIndex, _rendered_table_names(), test_efficiency_repetitions_follow_the_configured_count(), test_every_ablation_variant_is_dispatched_explicitly(), test_every_experiment_declares_a_known_dataset() (+12 more)

### Community 61 - "ast"
Cohesion: 0.14
Nodes (19): ast, naming_violations(), Module, test_no_banned_generic_artificial_or_forbidden_names(), test_violation_detected_for_forbidden_identifier(), test_violation_detected_for_generic_module_name(), test_violation_detected_for_versioned_symbol_name(), find_duplicate_constant_names() (+11 more)

### Community 62 - "boundary_metric_set"
Cohesion: 0.13
Nodes (21): CleanOracleDegradationMaterial, 30.16 `Capability Under-Specification Boundary`, `Capability-Granularity Boundary`, FalseCertificationCount, FalseSameEquivalenceCheck, PredicateSatisfied, ScopedContractActive, CleanOracleMaterialityConfig (+13 more)

### Community 63 - "35.2 Exact claim rules"
Cohesion: 0.10
Nodes (21): 35.1 State semantics, 35.2 Exact claim rules, 35. Claim-support decisions, `Authority Transition`, `Byzantine Operating Region`, `Conditional Non-Interference`, `Direct Source Exclusion`, `External Verification Necessity` (+13 more)

### Community 64 - "test_no_hardcoded_values.py"
Cohesion: 0.17
Nodes (19): Name, stmt, module_level_constant_values(), Module, test_no_module_level_constants_duplicate_governed_values(), test_violation_detected_for_duplicated_constant(), _uppercase_targets(), display_path() (+11 more)

### Community 65 - "AdmissionOpeningMode"
Cohesion: 0.20
Nodes (19): ScreenDomainCount, AdmissionOpeningMode, candidate_free_full_path_opening_mode(), AdmissionOpeningEntry, candidate_screen_transition(), NamespaceSeed, screen_domain_order(), ScreenDomainResult (+11 more)

### Community 66 - "baselines/test_registry.py"
Cohesion: 0.13
Nodes (19): BaselineFullParticipationAllowed, domain_target_view(), domain_without_target_view_may_participate(), first_eligible_non_source_reproducer(), PostReferenceDataAccess, DomainId, single_fresh_verifier_domain(), single_fresh_verifier_outcome() (+11 more)

### Community 67 - "5. Core Engineering Rules"
Cohesion: 0.10
Nodes (18): 1. Think Before Coding, 2. Simplicity First, 3. Surgical Changes, 4. Goal-Driven Execution, 5. Core Engineering Rules, 6. Static Analysis and Automated Enforcement, 7. Testing Rules, 8. Definition of Done (+10 more)

### Community 68 - "30. Experiment registry"
Cohesion: 0.10
Nodes (20): 30.10 `Mechanism Ablation`, 30.11 `Compromised-Reproducer Robustness`, 30.12 `Compromised-Verifier Robustness`, 30.13 `Byzantine-Bound Violation`, 30.14 `Evidence Scarcity and Dormancy`, 30.15 `Shared Epistemic-Failure Boundary`, 30.17 `Heterogeneous-Reproduction Boundary`, 30.18 `Admission-Delay Decomposition` (+12 more)

### Community 69 - "33.2 Result tables"
Cohesion: 0.10
Nodes (20): 33.1 Protocol tables, 33.2 Result tables, 33.3 Table rounding/significance display, 33. Required manuscript tables, `Ablation Results`, `Baseline Protocol`, `Byzantine Robustness`, `Collapse Decisions` (+12 more)

### Community 70 - "RuntimeComponentName"
Cohesion: 0.18
Nodes (18): FrameType, Logger, logging, OperationResult, RuntimeError, RuntimeComponentName, get_structured_logger(), OperationTimeoutError (+10 more)

### Community 71 - "load_scientific_config"
Cohesion: 0.17
Nodes (17): load_scientific_config(), Path, YamlValue, _read_yaml_mapping(), ScientificConfig, validate_scientific_config(), Path, test_config_is_immutable() (+9 more)

### Community 72 - "protocol_tables.py"
Cohesion: 0.24
Nodes (19): dataset_specification(), prepared_domain_summaries(), prepared_view_digest(), PreparedDomainSummary, domain_target_count(), _downstream_role(), eligibility_text(), _experiment_class_label() (+11 more)

### Community 73 - ".run"
Cohesion: 0.12
Nodes (15): Fresh Graphify callable inventory — final pass, Prospective experiment workflow counts, Union, Short end-to-end test scope, Audit findings, Audit continuation, 2026-09-26, Completed discovery, Findings so far (+7 more)

### Community 74 - ".values"
Cohesion: 0.19
Nodes (14): ScientificCellSemanticKeyTuple, MetricEvidenceRow, ArtifactDigest, CodeRevision, ComparisonName, EvidenceCycleIndex, MasterSeed, MethodName (+6 more)

### Community 75 - "discover_primary_csv_files"
Cohesion: 0.26
Nodes (18): compute_dataset_manifest_hash(), discover_primary_csv_files(), DatasetManifestDigest, Path, test_archive_and_already_extracted_layouts_yield_identical_dataset_manifest_hash(), Path, skipif, test_compute_dataset_manifest_hash_changes_when_a_file_changes() (+10 more)

### Community 76 - "AblationVariant"
Cohesion: 0.23
Nodes (18): AblationVariant, ablation_metric(), ablation_scenario_for_variant(), ablation_reference_cell(), MasterSeed, ScenarioName, isolated_repository(), _master_seed() (+10 more)

### Community 77 - "test_workflow_call_topology.py"
Cohesion: 0.21
Nodes (18): _called_names(), _called_names_for_node(), _method_node(), _missing_calls(), AST, FunctionDef, Path, test_application_wires_every_cli_command() (+10 more)

### Community 78 - "15. Adversarial and diagnostic transformation registry"
Cohesion: 0.11
Nodes (18): 15.10 Transformation cardinality, root-cause, and controlled-episode completion rules, 15.1 Useful + hidden-backdoor source, 15.2 Byzantine reproduction strategies, 15.3 Byzantine verifier behavior, 15.4 Shared label-error boundary, 15.5 Shared spurious-feature boundary, 15.6 Attacker-induced common-context boundary, 15.7 Capability under-specification fixture (+10 more)

### Community 79 - "screen_fold_index"
Cohesion: 0.21
Nodes (17): FoldCount, FoldIndex, ScreenDifferential, match_held_out_fold(), proposal_screen_differential(), DerivedSeed, SampleId, run_proposal_screen_for_domain() (+9 more)

### Community 80 - "17.2 Capability Contract metrics"
Cohesion: 0.12
Nodes (17): 17.2 Capability Contract metrics, Anchor training budgets and cadences, Benign false-alarm-rate increase, Checkpoint artifacts, Data loading, Metric adequacy minima, Persisted cell evidence and reuse, Persisted statistical comparison evidence (+9 more)

### Community 81 - "_diagnostic_marker_for_domain"
Cohesion: 0.22
Nodes (15): KeepGradients, _diagnostic_marker_for_domain(), Tensor, logits_for_samples(), per_sample_cross_entropy(), probabilities_for_samples(), Module, Tensor (+7 more)

### Community 82 - "cli.py"
Cohesion: 0.21
Nodes (12): command, Per-command reachability, rich_console, plan(), preprocess(), OverwriteExisting, report(), run_experiment() (+4 more)

### Community 83 - "18. Statistical analysis protocol"
Cohesion: 0.13
Nodes (15): 18.10 Rounding, 18.1 Experimental unit and pairing, 18.2 Primary hypothesis tests, 18.3 Alpha and multiplicity, 18.4 Effect sizes, 18.5 Confidence intervals, 18.6 Materiality criteria, 18.7 Collapse/survival rules (+7 more)

### Community 84 - "fit_feature_moments"
Cohesion: 0.24
Nodes (12): FeatureMoments, FeatureStatistic, fit_feature_moments(), model_validator, Self, _statistic(), test_feature_moments_reject_inconsistent_lengths(), test_feature_moments_reject_nonpositive_scale() (+4 more)

### Community 85 - "test_no_any_dict_object.py"
Cohesion: 0.24
Nodes (14): annotation_occurrences(), annotation_violations(), forbidden_symbol_violations(), expr, Module, raw_mapping_violations(), test_any_annotation_is_detected(), test_dictionary_construction_is_detected() (+6 more)

### Community 86 - "apply_sampling_cap"
Cohesion: 0.23
Nodes (12): DatasetFileDigest, SamplingSelectionDigest, SourceRowIndex, apply_sampling_cap(), ClassLabel, sampling_cap_selection_digest(), test_apply_sampling_cap_is_deterministic_across_runs(), test_apply_sampling_cap_returns_all_rows_when_under_the_cap() (+4 more)

### Community 87 - "17.1 Classification metrics"
Cohesion: 0.14
Nodes (14): 17.1 Classification metrics, Accuracy, AUPRC, AUROC, Balanced Accuracy, F1 for class $c$, False-negative rate, False-positive rate (+6 more)

### Community 88 - "34. Required manuscript figures"
Cohesion: 0.14
Nodes (14): 34.10 `Heterogeneity Synthesis Boundary`, 34.11 `Admission-Delay Decomposition`, 34.12 `Efficiency Profile`, 34.13 `Secondary Generalization`, 34.1 `FedSIRA Protocol Schematic`, 34.2 `Primary Security–Utility Tradeoff`, 34.3 `Useful Backdoored Source`, 34.4 `Collapse Decision Effects` (+6 more)

### Community 89 - "select_krum_update"
Cohesion: 0.25
Nodes (13): KrumNeighborCount, KrumScore, krum_neighbor_count(), krum_score(), CommitteeSize, MaximumByzantineReproductionRows, select_krum_update(), _row() (+5 more)

### Community 90 - "test_comparison_evidence.py"
Cohesion: 0.26
Nodes (13): metric_evidence_digest(), ArtifactDigest, Path, _record(), test_comparison_evidence_slot_is_per_experiment_and_uses_the_family(), test_currency_check_is_silent_when_no_evidence_was_published(), test_current_comparison_evidence_is_required_for_registered_comparisons(), test_metric_evidence_digest_distinguishes_undefined_from_zero() (+5 more)

### Community 91 - "FailureClass"
Cohesion: 0.27
Nodes (11): AutomaticallyRetriable, AutomaticRecoveryPermitted, RetryCount, FailureClass, automatic_recovery_permitted(), is_automatically_retriable(), test_data_invalid_is_never_automatically_retried(), test_infrastructure_interruption_is_not_permitted_after_limit_reached() (+3 more)

### Community 92 - "independent_local_reference_reviewer_is_positive"
Cohesion: 0.19
Nodes (12): ReviewerPositiveDecision, independent_local_reference_reviewer_is_positive(), parameter_similarity_certifies(), CapabilityContractSatisfied, Probability, test_parameter_similarity_certifies_at_threshold(), test_parameter_similarity_na_on_zero_norm(), test_independent_local_reference_reviewer_negative_beyond_benign_far_margin() (+4 more)

### Community 93 - "load_published_manifests"
Cohesion: 0.46
Nodes (12): InvalidArtifactReport, load_published_manifests(), _manifest_text(), _point_current_at(), Path, test_absent_root_yields_no_manifests(), test_current_publication_is_loaded(), test_obsolete_current_schema_is_rejected_as_invalid_evidence() (+4 more)

### Community 94 - "build_comparison_results_for_experiment"
Cohesion: 0.31
Nodes (13): _benefit_difference(), build_comparison_results_for_experiment(), _comparison_pairs(), extend_index_from_records(), merge_metric_record(), merge_metric_records(), metric_index_from_outcomes(), metric_value() (+5 more)

### Community 95 - "CLI workflow traces"
Cohesion: 0.17
Nodes (8): CLI workflow traces, `doctor`, `plan`, `preprocess [dataset] [--overwrite]`, `report [ExperimentName] [--overwrite]`, `run <ExperimentName> [--overwrite]` (prospective only), `smoke [--overwrite]`, `status`

### Community 96 - "evaluation/test_validation.py"
Cohesion: 0.27
Nodes (10): EvaluationValidationError, FailureMessage, ValueError, validate_metric_class_membership(), test_metric_class_membership_accepts_valid_configuration(), test_metric_class_membership_rejects_benign_outside_vocabulary(), test_metric_class_membership_rejects_supported_outside_vocabulary(), test_metric_class_membership_rejects_target_outside_vocabulary() (+2 more)

### Community 97 - "FedSIRAApplication"
Cohesion: 0.33
Nodes (5): ApplicationExitCode, Console, FedSIRAApplication, OverwriteExisting, render()

### Community 98 - "18.9 Exact comparison registry"
Cohesion: 0.18
Nodes (11): 18.9 Exact comparison registry, Family 10 — secondary generalization, Family 1 — proposal-screen necessity, Family 2 — plurality necessity, Family 3 — source-exclusion central claim, Family 4 — external reproduction verification necessity, Family 5 — primary baseline comparisons, Family 6 — compromised-reproducer robustness (+3 more)

### Community 99 - "test_preprocess_plan_smoke.py"
Cohesion: 0.20
Nodes (6): doctor(), _no_mismatches(), MonkeyPatch, test_doctor_command_reports_configuration_and_next_action(), MonkeyPatch, test_status_renders_planned_experiment_lifecycle()

### Community 101 - "Scientific and workflow test crosswalk"
Cohesion: 0.20
Nodes (9): Remaining test-coverage actions, Scientific and workflow test crosswalk, TEST-001 — Scientific mathematics, TEST-002 — Data invariants, TEST-003 — Protocol states and guards, TEST-004 — Metrics and statistical rules, test_final_gate_predicates_pass_requires_all_four_thresholds_and_no_invariant_failure(), test_validate_commitment_exists_before_verifier_assignment() (+1 more)

### Community 102 - "10. Exact data roles, sampling, and preprocessing"
Cohesion: 0.20
Nodes (8): 10.1 Supported-class role intervals, 10.2 Target-class role intervals, 10.3 Deterministic sampling caps, 10.4 Data validation, 10.5 Scaling, 10.6 Preprocessing semantic identity, 10. Exact data roles, sampling, and preprocessing, RowCount

### Community 103 - "13. Role assignment, seeds, security profiles, and deterministic ties"
Cohesion: 0.20
Nodes (10): 13.1 Master seeds, 13.2 Seed namespaces and canonical hash semantics, 13.3 Deterministic ordering instead of hidden RNG defaults, 13.4 Source selection, 13.5 Proposal-screen fold and matching semantics, 13.6 Primary deterministic verifier profile, 13.7 Diagnostic random verifier profile, 13.8 Compromised reproducer selection (+2 more)

### Community 104 - "16.2 Core and mechanism baselines"
Cohesion: 0.20
Nodes (10): 16.2 Core and mechanism baselines, `Candidate-Free Full Path`, `Centralized Reference`, `Client Review then One Independent Retrain`, `Client Review with Direct Source Admission`, `FedAvg Reference`, `Local-Only Reference`, `Multiple Retrains with Direct Krum` (+2 more)

### Community 105 - "7. Exact FedSIRA procedure"
Cohesion: 0.20
Nodes (10): 7.1 Admission opening, 7.2 Proposal screen, 7.3 Source-independent reproduction, 7.4 External verification, 7.5 Reproducibility certificate, 7.6 Robust source-excluded synthesis: Krum, 7.7 Final fresh gate, 7. Exact FedSIRA procedure (+2 more)

### Community 106 - "8. Theory and proof obligations"
Cohesion: 0.20
Nodes (10): 8.1 Pre-independent-evidence indistinguishability, 8.2 Independent evidence proposition, 8.3 Claim-conditional direct source-artifact non-interference, 8.4 Honest-support counting, 8.5 Synthesizer-specific reproduction count, 8.6 Conditional safety/liveness, 8.7 Independent-evidence delay lower bound, 8.8 Random-committee contamination calculation (+2 more)

### Community 107 - "direct_krum_committee_rows"
Cohesion: 0.22
Nodes (9): NonAbstainingReproductionSeries, ParticipantCount, ThreeRowCoordinateMedianConfig, direct_krum_committee_rows(), CommitteeSize, validate_three_row_coordinate_median_committee_size(), test_direct_krum_committee_rows_filters_abstaining_and_requires_committee_size(), test_direct_krum_committee_rows_none_when_insufficient_non_abstaining_rows() (+1 more)

### Community 108 - "test_enum_integrity.py"
Cohesion: 0.40
Nodes (9): annotation_names(), enum_class_defs(), ClassDef, Module, Path, test_enum_used_only_as_its_own_annotation_is_still_flagged(), test_every_enum_is_referenced_outside_or_used_as_a_typed_field(), test_violation_detected_for_unused_enum() (+1 more)

### Community 109 - "Final audit evidence"
Cohesion: 0.22
Nodes (7): Empirical and architecture deviation ledger, Current gate, Final audit evidence, Prepared-output validation, Production rerun and cache identity, Real datasets and raw provenance, Safe checks already completed

### Community 110 - "FedSIRA Pre-Experiment Audit Matrix"
Cohesion: 0.22
Nodes (8): 1. Purpose and scope, 2. Authority hierarchy, 3. Status and severity definitions, 5. Fresh Graphify / callable-count summary template, 6. Per-command / per-workflow callable-count template, 7. Required later audit execution order, 8. Final pre-experiment acceptance gate, FedSIRA Pre-Experiment Audit Matrix

### Community 111 - "prepared_validation.py"
Cohesion: 0.31
Nodes (8): hashlib, PreparedRoleViewManifest, _parquet_checksum(), ArtifactDigest, Path, PreparedViewKey, RowCount, _view_failures()

### Community 112 - "test_no_comments_or_docstrings.py"
Cohesion: 0.33
Nodes (8): io, has_comment_token(), has_docstring(), Module, test_no_comments_or_docstrings_in_repository_python_source(), test_violation_detected_for_comment(), test_violation_detected_for_docstring(), tokenize

### Community 113 - "test_dataset_subsystem.py"
Cohesion: 0.31
Nodes (6): _dataset_files(), Path, test_dataset_public_functions_avoid_primitive_annotations(), test_datasets_do_not_import_replaced_tabular_libraries(), test_datasets_do_not_keep_manual_arrow_sqlite_abstractions(), test_preprocess_workflow_calls_materialize_functions()

### Community 114 - "test_no_redirects_shims_reexports.py"
Cohesion: 0.39
Nodes (8): is_pure_redirect(), package_reexports(), Module, test_compliant_module_with_definitions_passes(), test_no_non_init_module_is_a_pure_redirect(), test_package_initializers_do_not_publish_imported_compatibility_aliases(), test_violation_detected_for_package_reexport_facade(), test_violation_detected_for_redirect_module()

### Community 115 - "test_public_type_boundaries.py"
Cohesion: 0.42
Nodes (8): is_fully_annotated(), public_top_level_functions(), FunctionDef, Module, test_compliant_function_passes(), test_public_boundary_functions_are_fully_annotated(), test_violation_detected_for_unannotated_public_function(), violations_in_tree()

### Community 116 - "test_validation_run_path.py"
Cohesion: 0.28
Nodes (6): MonkeyPatch, Path, test_baseline_implementation_validation_dispatches_to_baseline_cell(), test_data_and_domain_evidence_validation_cell_is_invalid_without_prepared_evidence(), test_data_and_domain_evidence_validation_rejects_insufficient_counts(), test_protocol_invariant_validation_cell_executes_smoke_invariants()

### Community 117 - "first_cycle_with_minimum_eligible_evidence_holders"
Cohesion: 0.25
Nodes (8): CompletionCycleIndex, EvidenceArrivalCycleIndex, MinimumEligibleEvidenceHolderCount, first_cycle_with_minimum_eligible_evidence_holders(), EligibleEvidenceHolderCount, validate_no_safety_completion_before_tau_k(), test_first_cycle_with_minimum_eligible_evidence_holders(), test_validate_no_safety_completion_before_tau_k_rejects_early_completion()

### Community 118 - "24. Public CLI contract"
Cohesion: 0.25
Nodes (8): 24.1 `fedsira doctor`, 24.2 `fedsira preprocess ["N-BaIoT"|"CICIoT2023"]`, 24.3 `fedsira plan`, 24.4 `fedsira smoke`, 24.5 `fedsira status`, 24.6 `fedsira run <experiment name>`, 24.7 `fedsira report [<experiment name>]`, 24. Public CLI contract

### Community 119 - "9. Primary dataset and experimental domain construction"
Cohesion: 0.25
Nodes (8): 9.1.1 Raw release discovery and canonical mapping, 9.1 Primary dataset, 9.2 Domain proxies, 9.3 Class vocabulary, 9.4 Post-reference capability, 9.5 Supported classes, 9.6 Controlled replay semantics, 9. Primary dataset and experimental domain construction

### Community 120 - "pytest"
Cohesion: 0.39
Nodes (7): pytest, declared_source_backdoor_poison_fractions(), Probability, validate_declared_source_backdoor_poison_fraction(), test_an_undeclared_poison_fraction_is_rejected(), test_declared_poison_sweep_comes_from_configuration(), test_every_declared_poison_fraction_is_admissible()

### Community 121 - "BaselineIdentity"
Cohesion: 0.50
Nodes (7): BaselineIdentity, BaselineContract, BaselineValidationFixture, _fixture_for(), test_fixture_map_covers_every_registered_baseline_exactly_once(), test_ordinary_utility_references_use_legitimate_target_capability(), test_robust_update_filtering_references_use_model_replacement_backdoor()

### Community 122 - "test_no_free_string_enum_bypass.py"
Cohesion: 0.50
Nodes (7): enum_member_values(), Module, Path, string_literals(), test_no_free_string_enum_value_bypass_across_modules(), test_owner_module_usage_not_flagged(), test_violation_detected_for_free_string_enum_value()

### Community 124 - "test_enums.py"
Cohesion: 0.25
Nodes (7): test_artifact_lifecycle_state_members(), test_dataset_id_has_exactly_the_two_roadmap_datasets(), test_enum_members_are_not_equal_to_plain_strings_by_construction(), test_experiment_lifecycle_state_members(), test_failure_class_has_exactly_nine_classes(), test_scientific_cell_phase_has_exactly_six_phases(), test_seed_derivation_label_retains_the_fifteen_namespace_tokens()

### Community 125 - "12. Model, anchor training, source training, and reproduction training"
Cohesion: 0.29
Nodes (7): 12.1 Base classifier, 12.2 Common optimizer and loss constants, 12.3 Anchor FedAvg, 12.4 Post-reference training contract, 12.5 Verifier-aware malicious training override, 12.6 No test-set tuning, 12. Model, anchor training, source training, and reproduction training

### Community 126 - "26. Scientific output contract"
Cohesion: 0.29
Nodes (7): 26.1 Scientific execution dependencies, 26.2 Artifact validity and lifecycle, 26.3 Reusable artifact families, 26.4 Selective invalidation boundaries, 26.5 Experiment dependency and reuse map, 26.6 Cross-experiment reuse rules, 26. Scientific output contract

### Community 127 - "28. Validation and smoke-test contract"
Cohesion: 0.29
Nodes (7): 28.1 Data tests, 28.2 Model/FL tests, 28.3 Protocol invariant tests, 28.4 Mathematical tests, 28.5 Metric/statistical tests, 28.6 Artifact reuse and recovery tests, 28. Validation and smoke-test contract

### Community 128 - "ProtocolPhaseDurations"
Cohesion: 0.33
Nodes (4): ProtocolPhaseDurations, MetricValue, Path, validate_cell_handler_registration()

### Community 129 - "test_config_as_parameter.py"
Cohesion: 0.43
Nodes (6): _annotation_names(), config_parameter_violations(), expr, Module, test_production_functions_do_not_take_scientific_config(), test_violation_detected_for_public_config_parameter()

### Community 130 - "17.4 Cross-domain distribution metrics"
Cohesion: 0.33
Nodes (6): 10th-percentile domain target F1, 17.4 Cross-domain distribution metrics, Coefficient of variation, Domain disparity, IQR, Worst-domain target F1

### Community 131 - "17. Metric registry and mathematical definitions"
Cohesion: 0.33
Nodes (6): 17.5 Candidate-screen metrics, 17.6 Delay metrics, 17.7 Efficiency and communication metrics, 17.8 Aggregation and evaluation populations, 17.9 Missing and undefined metric policy, 17. Metric registry and mathematical definitions

### Community 132 - "1. Scientific problem, contribution boundary, and claims"
Cohesion: 0.33
Nodes (6): 1.1 Research problem, 1.2 Core authority transition, 1.3 Required mechanism, 1.4 Safe manuscript claims, 1.5 Forbidden claims, 1. Scientific problem, contribution boundary, and claims

### Community 133 - "minimum_honest_positive_count"
Cohesion: 0.33
Nodes (6): MaximumByzantineReportCount, MinimumHonestPositiveReportCount, minimum_honest_positive_count(), ObservedPositiveReportCount, test_minimum_honest_positive_count_bound(), test_primary_verifier_profile_guarantees_at_least_one_honest_positive()

### Community 134 - "reproduction_stage_identity"
Cohesion: 0.50
Nodes (5): CheckpointStageIdentity, ConditionName, DomainId, reproduction_stage_identity(), source_candidate_stage_identity()

### Community 135 - "background-jobs.md"
Cohesion: 0.40
Nodes (4): 2026-09-25 follow-up, 2026-09-26 continuation, Fresh audit, 2026-09-25, WSL resumed, 2026-09-25

### Community 136 - "17.10 Additional specified metrics"
Cohesion: 0.40
Nodes (5): 17.10 Additional specified metrics, Clean-oracle degradation, Descriptive confidence intervals for method summaries, False same-capability certification rate, Protocol-specific aggregation sufficiency

### Community 137 - "17.3 Security and admission metrics"
Cohesion: 0.40
Nodes (5): 17.3 Security and admission metrics, Abstention/dormancy rate, Attack Success Rate, Legitimate admission rate, Malicious admission rate

### Community 138 - "4. Threat model, trust assumptions, and explicit boundaries"
Cohesion: 0.40
Nodes (5): 4.1 Primary security setting, 4.2 Attacker knowledge, 4.3 Honest-path assumptions, 4.4 Failure boundaries that must be tested, 4. Threat model, trust assumptions, and explicit boundaries

### Community 139 - "FedSIRA"
Cohesion: 0.40
Nodes (4): CLI usage, FedSIRA, Reproducibility, Setup

### Community 140 - "malicious_admission_rate"
Cohesion: 0.67
Nodes (4): AdmissionIndicatorSeries, legitimate_admission_rate(), malicious_admission_rate(), test_malicious_admission_rate_and_legitimate_admission_rate()

### Community 141 - "StructuredJsonFormatter"
Cohesion: 0.50
Nodes (3): LogRecord, LogRecordText, StructuredJsonFormatter

### Community 142 - "_ListConvertibleTensor"
Cohesion: 0.50
Nodes (3): ModelParameterValue, _ListConvertibleTensor, Protocol

### Community 143 - "baseline_calibration_rule"
Cohesion: 0.50
Nodes (4): Percentile, baseline_calibration_rule(), MethodName, ProtocolRuleText

## Knowledge Gaps
- **330 isolated node(s):** `TEST-003 — Protocol states and guards`, `10.1 Supported-class role intervals`, `10.2 Target-class role intervals`, `10.3 Deterministic sampling caps`, `10.4 Data validation` (+325 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 849 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **44 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `current_application_context()` connect `current_application_context` to `common.py`, `FedSIRAClassifier`, `DatasetAdapter`, `service.py`, `baselines/training.py`, `ciciot2023/prepare.py`, `ArtifactFamily`, `export.py`, `application.py`, `figures.py`, `handlers.py`, `ExperimentLifecycleState`, `DatasetId`, `tables.py`, `baseline_calibration_rule`, `defenses.py`, `comparisons.py`, `nbaiot/prepare.py`, `NBaiotClass`, `execution.py`, `federated.py`, `collapse.py`, `store.py`, `paths.py`, `enums.py`, `runtime.py`, `planning.py`, `nbaiot_adapter`, `framed_bytes`, `ciciot2023/test_preprocessing.py`, `metrics.py`, `FrozenDomainModel`, `learning/training.py`, `Role`, `test_theory.py`, `ReproducerCondition`, `run_smoke_suite`, `test_experiment_registry_contracts.py`, `AdmissionOpeningMode`, `protocol_tables.py`, `AblationVariant`, `screen_fold_index`, `build_comparison_results_for_experiment`, `pytest`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `ExperimentName` connect `ExperimentName` to `current_application_context`, `service.py`, `ArtifactFamily`, `export.py`, `application.py`, `figures.py`, `handlers.py`, `ExperimentLifecycleState`, `tables.py`, `models.py`, `comparisons.py`, `execution.py`, `collapse.py`, `store.py`, `paths.py`, `enums.py`, `runtime.py`, `planning.py`, `FrozenDomainModel`, `ArtifactSlot`, `test_experiment_registry_contracts.py`, `protocol_tables.py`, `.run`, `.values`, `cli.py`, `test_comparison_evidence.py`, `build_comparison_results_for_experiment`, `FedSIRAApplication`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Why does `FrozenDomainModel` connect `FrozenDomainModel` to `common.py`, `ProtocolPhaseDurations`, `current_application_context`, `DatasetAdapter`, `service.py`, `baselines/training.py`, `ciciot2023/prepare.py`, `ArtifactFamily`, `export.py`, `application.py`, `figures.py`, `handlers.py`, `ExperimentLifecycleState`, `DatasetId`, `tables.py`, `models.py`, `defenses.py`, `comparisons.py`, `nbaiot/prepare.py`, `NBaiotClass`, `execution.py`, `federated.py`, `collapse.py`, `store.py`, `ExperimentName`, `enums.py`, `runtime.py`, `planning.py`, `framed_bytes`, `metrics.py`, `ArtifactSlot`, `Role`, `rules.py`, `protocol/test_reproduction.py`, `test_common.py`, `4. Audit requirements`, `CertifiedReproductionRow`, `MetricResult`, `run_smoke_suite`, `AdmissionOpeningMode`, `baselines/test_registry.py`, `protocol_tables.py`, `.values`, `screen_fold_index`, `fit_feature_moments`, `load_published_manifests`, `build_comparison_results_for_experiment`, `prepared_validation.py`, `BaselineIdentity`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `current_application_context()` (e.g. with `test_standard_fl_baseline_budget_reads_yaml()` and `test_declared_poison_sweep_comes_from_configuration()`) actually correct?**
  _`current_application_context()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 31 inferred relationships involving `FrozenDomainModel` (e.g. with `CalibrationErrorCount` and `CellHandlerName`) actually correct?**
  _`FrozenDomainModel` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 150 inferred relationships involving `ExperimentName` (e.g. with `_all_complete()` and `_collapse_experiment_completed()`) actually correct?**
  _`ExperimentName` has 150 INFERRED edges - model-reasoned connections that need verification._
- **Are the 97 inferred relationships involving `AdmissionState` (e.g. with `AdmissionStateIsTerminal` and `CellHandlerName`) actually correct?**
  _`AdmissionState` has 97 INFERRED edges - model-reasoned connections that need verification._