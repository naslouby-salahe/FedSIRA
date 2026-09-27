# Graph Report - FedSIRA  (2026-09-26)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 4087 nodes · 15890 edges · 182 communities (138 shown, 44 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 3051 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9449c601`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- handlers.py
- common.py
- FedSIRAClassifier
- baselines/training.py
- application.py
- export.py
- AdmissionState
- figures.py
- execution.py
- comparisons.py
- ciciot2023/prepare.py
- ExperimentLifecycleState
- post_reference.py
- enums.py
- tables.py
- store.py
- FrozenDomainModel
- federated.py
- nbaiot/prepare.py
- ProtocolCellExecutor
- screen_evidence.py
- collapse.py
- paths.py
- nbaiot_adapter
- admission.py
- test_metrics.py
- reproduction_progression
- defenses.py
- MetricResult
- config.py
- runtime.py
- planning.py
- models.py
- statistics.py
- pathlib
- learning/training.py
- protocol/test_verification.py
- ExperimentName
- parse
- framed_bytes
- Roadmap.md
- NBaiotClass
- 17.1 Classification metrics
- ciciot2023/test_preprocessing.py
- materialize_nbaiot_prepared_views
- artifact_slot_directory
- EvidenceArrivalSchedule
- test_common.py
- test_theory.py
- test_no_primitive_leaks.py
- model_validator
- CertifiedReproductionRow
- iter_python_files
- ArtifactFamily
- 4. Audit requirements
- 18.9 Exact comparison registry
- Role
- comparison_evidence.py
- run_smoke_suite
- exact_sign_flip_two_sided_p_value
- ciciot2023/test_acquisition.py
- 16.2 Core and mechanism baselines
- RuntimeComponentName
- test_capability_contract.py
- 35.2 Exact claim rules
- test_no_hardcoded_values.py
- ciciot2023/schema.py
- AdmissionOpeningMode
- rules.py
- 5. Core Engineering Rules
- 30. Experiment registry
- 33.2 Result tables
- load_scientific_config
- discover_primary_csv_files
- protocol_tables.py
- test_experiment_registry_contracts.py
- baselines/test_registry.py
- .run
- test_workflow_call_topology.py
- 15. Adversarial and diagnostic transformation registry
- screen_fold_index
- ArtifactSlot
- TernaryOutcome
- 17.2 Capability Contract metrics
- .values
- ast
- cli.py
- artifact_identity
- fit_feature_moments
- test_no_any_dict_object.py
- apply_sampling_cap
- 34. Required manuscript figures
- select_krum_update
- ElapsedTimer
- FailureClass
- screen_domain_decision_is_positive
- load_published_manifests
- build_comparison_results_for_experiment
- CLI workflow traces
- evaluation/test_validation.py
- test_epistemic_failure.py
- FedSIRAApplication
- 16.5 Baseline implementation completion rules
- test_preprocess_plan_smoke.py
- test_commands.py
- 10. Exact data roles, sampling, and preprocessing
- 13. Role assignment, seeds, security profiles, and deterministic ties
- 7. Exact FedSIRA procedure
- 8. Theory and proof obligations
- direct_krum_committee_rows
- observations.py
- test_enum_integrity.py
- source_selection_order
- Final audit evidence
- FedSIRA Pre-Experiment Audit Matrix
- Scientific and workflow test crosswalk
- test_no_comments_or_docstrings.py
- independent_local_reference_reviewer_is_positive
- test_no_redirects_shims_reexports.py
- test_no_test_only_production_code.py
- test_public_type_boundaries.py
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
- test_generic_wrappers.py
- test_naming_policy.py
- 1. Scientific problem, contribution boundary, and claims
- minimum_honest_positive_count
- background-jobs.md
- 6. FedSIRA state machine and non-negotiable invariants
- FedSIRA
- StructuredJsonFormatter
- _ListConvertibleTensor
- PreparedEvidencePresent
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
6. `ScientificCell` - 143 edges
7. `DatasetId` - 126 edges
8. `ExperimentLifecycleState` - 119 edges
9. `ArtifactFamily` - 102 edges
10. `ProtocolCellDispatch` - 99 edges

## Surprising Connections (you probably didn't know these)
- ``preprocess [dataset] [--overwrite]`` --references--> `DatasetId`  [INFERRED]
  docs/.audit/cli-workflows.md → src/fedsira/domain/enums.py
- ``doctor`` --references--> `DoctorReport`  [INFERRED]
  docs/.audit/cli-workflows.md → src/fedsira/application.py
- `2026-09-26 continuation` --references--> `_assign_secondary_roles()`  [INFERRED]
  docs/.audit/background-jobs.md → src/fedsira/datasets/ciciot2023/prepare.py
- `Remaining test-coverage actions` --references--> `test_no_public_production_symbol_used_only_by_tests()`  [INFERRED]
  docs/.audit/test-audit.md → tests/architecture/test_no_test_only_production_code.py
- `13.2 Seed namespaces and canonical hash semantics` --references--> `local_training_seed()`  [INFERRED]
  docs/Roadmap.md → src/fedsira/runtime.py

## Import Cycles
- 3-file cycle: `src/fedsira/experiments/collapse.py -> src/fedsira/experiments/engine.py -> src/fedsira/experiments/execution.py -> src/fedsira/experiments/collapse.py`
- 3-file cycle: `src/fedsira/evaluation/comparison_evidence.py -> src/fedsira/experiments/engine.py -> src/fedsira/experiments/execution.py -> src/fedsira/evaluation/comparison_evidence.py`

## Communities (182 total, 44 thin omitted)

### Community 0 - "handlers.py"
Cohesion: 0.06
Nodes (89): ClassCount, collections, dataclasses, FeatureSchemaDigest, RoleHashToken, EvidenceMinimaConfig, DatasetAdapter, RealAnchor (+81 more)

### Community 1 - "common.py"
Cohesion: 0.05
Nodes (78): AttackCount, enum, FeatureName, specification(), apply_attacker_induced_common_context(), apply_epistemic_target_marker(), apply_heterogeneity_shift(), apply_quantity_skew_to_cap() (+70 more)

### Community 2 - "FedSIRAClassifier"
Cohesion: 0.05
Nodes (85): DeltaScale, KeepGradients, PostReferenceConfig, triggered_to_benign_rate(), FedSIRAClassifier, flatten_trainable_parameters(), load_flat_trainable_parameters(), logits_for_samples() (+77 more)

### Community 3 - "baselines/training.py"
Cohesion: 0.07
Nodes (80): Production callables outside the prospective CLI union, flat_parameters_identity(), AlgorithmName, model_state_from_classifier(), clip_source_update(), cosine_distance(), cosine_distance_matrix(), density_cluster_labels() (+72 more)

### Community 4 - "application.py"
Cohesion: 0.06
Nodes (74): DeterministicExecutionReady, CLI to application roots, Production call-graph audit — current snapshot, Runtime boundaries, DoctorArtifactSummary, DoctorExperimentSummary, NextValidAction, ProjectProgressDescription (+66 more)

### Community 5 - "export.py"
Cohesion: 0.07
Nodes (76): pandas, ReportRowIdentity, materialize_resolved_core(), _aggregate_rows(), AggregateMetricEvidenceRow, _comparison_rows(), _comparison_source_semantic_keys(), ComparisonEvidenceRow (+68 more)

### Community 6 - "AdmissionState"
Cohesion: 0.12
Nodes (31): CompromisedProductionAncestry, DiscardSourceWeights, Deliberate narrow workflows, Per-experiment prospective CLI-to-leaf workflows, Registered experiment workflow map, LegitimateAdmissionEligible, prepared_feature_names(), AdmissionState (+23 more)

### Community 7 - "figures.py"
Cohesion: 0.08
Nodes (74): Axes, AxisDraw, BoundarySeries, FigureAnnotationText, FigureAxisLabel, FigureLegendText, matplotlib_axes, FigureAxisName (+66 more)

### Community 8 - "execution.py"
Cohesion: 0.07
Nodes (62): CellHandlerName, Dynamic protocol dispatch, _collapse_experiment_completed(), _collapse_family_for_experiment(), _materialize_core_if_complete(), configuration_digest(), configure_artifact_logging(), CodeRevision (+54 more)

### Community 9 - "comparisons.py"
Cohesion: 0.10
Nodes (66): ComparisonReferenceLabel, MaterialityDecision, MultiplicityConfig, ComparisonFamily, ComparisonMetric, PrimaryScenario, _ablation_comparisons(), ablation_material_threshold() (+58 more)

### Community 10 - "ciciot2023/prepare.py"
Cohesion: 0.09
Nodes (65): DatasetColumnCount, FeatureMoment, PartitionSalt, _assign_secondary_roles(), _cached_view_is_reusable(), _cap_case_sql(), CICIoTPreparedViewMetadata, _comparison_token() (+57 more)

### Community 11 - "ExperimentLifecycleState"
Cohesion: 0.10
Nodes (60): CellCompletionStatus, csv, matplotlib_figure, _export_completed_experiment(), CoreMethodIdentity, ExperimentLifecycleState, CellExecutionOutcome, experiment_execution_digest() (+52 more)

### Community 12 - "post_reference.py"
Cohesion: 0.07
Nodes (64): OrderItem, balanced_capability_selection(), cap_replay_rows(), DatasetManifestDigest, supported_replay_cap_for_target_role(), SeedDerivationLabel, ArtifactDigest, DerivedSeed (+56 more)

### Community 13 - "enums.py"
Cohesion: 0.08
Nodes (59): ArtifactFileName, FeatureShiftMagnitude, FeatureShiftSign, HeterogeneityMultiplier, ScreenLoss, AblationScenario, ArtifactFileToken, BoundCondition (+51 more)

### Community 14 - "tables.py"
Cohesion: 0.14
Nodes (62): FormattedStatisticText, ReportCellLiteral, ReportColumnName, TableName, ComparisonFamilyResult, ComparisonResult, render_mandatory_tables(), render_baseline_protocol_table() (+54 more)

### Community 15 - "store.py"
Cohesion: 0.10
Nodes (55): ArtifactComplete, ArtifactPayloadBytes, ArtifactSerializedText, ArtifactCurrentPointer, ArtifactLogFields, ArtifactManifest, compute_checksum(), _configuration_scope_digest() (+47 more)

### Community 16 - "FrozenDomainModel"
Cohesion: 0.10
Nodes (57): DatasetManifestPayload, artifact_staging_root(), current_repository_root(), CICIoT2023DatasetManifestPayload, RawDatasetFileIdentity, RawDatasetIdentityPayload, ScalerMetadata, required_raw_dataset_root() (+49 more)

### Community 17 - "federated.py"
Cohesion: 0.09
Nodes (55): EvaluationCadenceReached, PreparedReproductionTargetCount, PreparedSupportedReplayCount, SmokeRenderText, AnchorFedAvgConfig, OptimizerConfig, TrainingConfig, AdmissionDelayDecomposition (+47 more)

### Community 18 - "nbaiot/prepare.py"
Cohesion: 0.07
Nodes (55): AttackBasename, AttackFamilyName, PathToken, _cached_view_is_reusable(), _cast_feature_select(), classes_structurally_unavailable(), _discover_attack_csv_files(), DiscoveredCsvFile (+47 more)

### Community 19 - "ProtocolCellExecutor"
Cohesion: 0.06
Nodes (36): Architecture responsibility review, Follow-up findings, Disposition, Experiment scientific-subsystem review, ReproducerCondition, VerifierCondition, compromised_reproducer_count(), compromised_verifier_count() (+28 more)

### Community 20 - "screen_evidence.py"
Cohesion: 0.11
Nodes (51): Artifact dependency and invalidation matrix, Percentile, ArtifactConfigurationComponent, ArtifactConfigurationScope, ArtifactDependency, configuration_scope_dependency(), ArtifactDependencyKind, ArtifactDependencyLabel (+43 more)

### Community 21 - "collapse.py"
Cohesion: 0.08
Nodes (53): MinimumCompletePairCount, ResolvedCoreIdentity, _best_passed_metric(), _collapse_comparator(), collapse_decision_from_comparison_families(), CollapseDecision, CollapseDecisionKind, CollapseEvaluationInput (+45 more)

### Community 22 - "paths.py"
Cohesion: 0.11
Nodes (51): Repository path ownership review, Root owners, Static inventory, artifact_log_path(), artifact_publication_root(), execution_outputs_root(), execution_workspace_root(), experiment_execution_root() (+43 more)

### Community 23 - "nbaiot_adapter"
Cohesion: 0.09
Nodes (31): SourceIsProductionUpdate, BackdoorScope, nbaiot_adapter(), Path, ReviewPanelProfile, MetricValue, Probability, train_source_candidate_delta() (+23 more)

### Community 24 - "admission.py"
Cohesion: 0.07
Nodes (50): CommunicationMessageCount, DomainT, FinalGateArtifactValid, parametrize, PluralityActive, HeterogeneityScope, CommunicationMessageType, compute_real_report_summary() (+42 more)

### Community 25 - "test_metrics.py"
Cohesion: 0.06
Nodes (50): AdmissionCount, BinaryLabelMaskSeries, CleanOracleDegradationMaterial, 30.16 `Capability Under-Specification Boundary`, `Capability-Granularity Boundary`, FalseCertificationCount, FalseSameEquivalenceCheck, PredicateSatisfied (+42 more)

### Community 26 - "reproduction_progression"
Cohesion: 0.06
Nodes (48): ExternalVerificationActive, AblationReproducerStrategy, ablation_reproducer_strategy(), ArtifactDigest, BooleanValue, DomainId, OrderedDict, RequiredReproductionRowCount (+40 more)

### Community 27 - "defenses.py"
Cohesion: 0.08
Nodes (47): ClassIndex, GroupCount, GroupIndex, dataset_manifest_hash(), certified_ensemble_domain_groups(), certified_ensemble_post_reference_rounds(), client_sampling_round_order(), client_sampling_round_seed() (+39 more)

### Community 28 - "MetricResult"
Cohesion: 0.11
Nodes (48): AdmissionIndicatorSeries, OptionalTriggeredSampleMaskSeries, ReproductionOpportunityCount, sklearn_metrics, DomainTargetMetrics, ConfusionCounts, MetricResult, accuracy() (+40 more)

### Community 29 - "config.py"
Cohesion: 0.08
Nodes (45): RoleBoundary, RoleInterval, AttackerInducedCommonContextConfig, AttacksAndBoundariesConfig, BaselinesConfig, BootstrapConfig, ByzantineOperatingRegionConfig, ByzantineReproductionConfig (+37 more)

### Community 30 - "runtime.py"
Cohesion: 0.07
Nodes (39): collections_abc, concurrent_futures, datetime, DomainLocalEvaluation, PeakMemoryBytes, pydantic, random, resource (+31 more)

### Community 31 - "planning.py"
Cohesion: 0.09
Nodes (39): PlanRenderText, baseline_validation_fixture_for_method(), ExperimentDefinition, MethodName, _ablation_cells(), _ablation_condition(), _baseline_validation_cells(), build_plan() (+31 more)

### Community 32 - "models.py"
Cohesion: 0.09
Nodes (39): ByteCount, EncodedBytes, inspect, json, LengthPrefixBytes, ModelTransmissionCount, ModelTransmissionPresent, communication_bytes() (+31 more)

### Community 33 - "statistics.py"
Cohesion: 0.08
Nodes (43): ConfidenceIntervalBound, DecileBinIndex, itertools, MatchedControlCount, MinimumDefinedDomainCount, numpy, bootstrap_percentile_confidence_interval(), _candidate_pool() (+35 more)

### Community 34 - "pathlib"
Cohesion: 0.08
Nodes (29): main(), run_worker(), main(), run_worker(), os, pathlib, subprocess, sys (+21 more)

### Community 35 - "learning/training.py"
Cohesion: 0.10
Nodes (38): BatchRowIndexSequence, BatchSize, DataLoader, math, build_epoch_batches(), DeclaredBatchDataset, ordered_batch_indices(), ordered_batch_row_indices() (+30 more)

### Community 36 - "protocol/test_verification.py"
Cohesion: 0.08
Nodes (40): AllowSourceAsVerifier, MonotonicTimestamp, OneVotePerDomain, byzantine_selection_order(), construct_above_bound_panel(), deterministic_verifier_panel(), diagnostic_committee_panel(), panel_votes_are_one_per_domain() (+32 more)

### Community 37 - "ExperimentName"
Cohesion: 0.12
Nodes (34): ExperimentName, SourceExclusionMethod, collapse_evaluation_from_records(), _cell(), _completed_outcome(), _override_workspace_root(), _provenance(), ConditionName (+26 more)

### Community 38 - "parse"
Cohesion: 0.11
Nodes (36): _dataset_files(), Path, test_dataset_public_functions_avoid_primitive_annotations(), test_datasets_do_not_import_replaced_tabular_libraries(), test_datasets_do_not_keep_manual_arrow_sqlite_abstractions(), test_preprocess_workflow_calls_materialize_functions(), _alias_bases(), _enum_class_names() (+28 more)

### Community 39 - "framed_bytes"
Cohesion: 0.11
Nodes (37): contextlib, contextvars, FramedBytes, ScoringTransformName, artifact_instance_token(), ArtifactInstanceName, ArtifactInstanceToken, FramingField (+29 more)

### Community 40 - "Roadmap.md"
Cohesion: 0.05
Nodes (36): 11.1 Secondary schema, labels, and raw-data adaptation, 11.2 Secondary domain proxies, 11.3 Secondary roles, 11. Secondary generalization dataset, 14. Final-gate and admission artifact semantics, 19.1 Scientific cell-phase boundaries, 19. Failure, null-result, and completion semantics, 20. Reference software and hardware environment (+28 more)

### Community 41 - "NBaiotClass"
Cohesion: 0.12
Nodes (34): Dataset adapter equivalence review, SamplingCapsPerDomain, BooleanValue, SamplingCap, RoleSamplingCap, sampling_cap_for_role(), _supported_sampling_cap(), _target_sampling_cap() (+26 more)

### Community 42 - "17.1 Classification metrics"
Cohesion: 0.06
Nodes (36): 10th-percentile domain target F1, 17.10 Additional specified metrics, 17.1 Classification metrics, 17.3 Security and admission metrics, 17.4 Cross-domain distribution metrics, 17.5 Candidate-screen metrics, 17.6 Delay metrics, 17.7 Efficiency and communication metrics (+28 more)

### Community 43 - "ciciot2023/test_preprocessing.py"
Cohesion: 0.18
Nodes (32): IntEnum, assign_secondary_roles(), resolve_row_identifier_columns(), CICIoT2023PseudoDomain, DomainId, DatasetExclusionReason, StrEnum, _per_attack_csv_file() (+24 more)

### Community 44 - "materialize_nbaiot_prepared_views"
Cohesion: 0.15
Nodes (29): duckdb, RetainMaterializedViews, materialize_nbaiot_prepared_views(), PreparedViewMetadata, OverwriteExisting, validate_consistent_predictor_schema(), validate_predictor_schema(), _assert_numeric_file() (+21 more)

### Community 45 - "artifact_slot_directory"
Cohesion: 0.15
Nodes (31): RepositoryPath, artifact_family_directory_token(), artifact_slot_directory(), content_digest(), publish_table_figure_export(), publish_table_figure_source_data(), ArtifactDigest, ArtifactReuseDecision (+23 more)

### Community 46 - "EvidenceArrivalSchedule"
Cohesion: 0.17
Nodes (31): EvidenceArrivalCycleSequence, MinimumEligibleEvidenceHolderCount, EvidenceArrivalSchedule, compute_t_evidence(), cycle_when_requirement_met(), first_cycle_with_minimum_eligible_evidence_holders(), first_holder_cycle_for_domain(), holder_count_at_cycle() (+23 more)

### Community 47 - "test_common.py"
Cohesion: 0.10
Nodes (23): RolePosition, RoleWindowContainsSample, SampleIdPrefix, compute_sample_id(), RelativePathText, role_for_normalized_position(), RoleWindow, supported_role_windows() (+15 more)

### Community 48 - "test_theory.py"
Cohesion: 0.09
Nodes (22): AtLeastTwoByzantineProbability, EligiblePoolSize, fractions, KrumCommitteeAdmissible, diagnostic_at_least_two_byzantine_probability(), krum_committee_is_admissible(), krum_minimum_committee_size(), ByzantineDomainCount (+14 more)

### Community 49 - "test_no_primitive_leaks.py"
Cohesion: 0.15
Nodes (27): arg, AsyncFunctionDef, _all_violations(), config_scalar_foundation_violations(), domain_identifier_violations(), _function_arguments(), function_boundary_primitive_violations(), model_field_primitive_violations() (+19 more)

### Community 50 - "model_validator"
Cohesion: 0.11
Nodes (13): AdmissionOpeningConfig, DataLoaderConfig, DatasetsConfig, DiagnosticRandomVerifierProfileConfig, FinalGateConfig, HiddenSourceBackdoorConfig, model_validator, SeedCount (+5 more)

### Community 51 - "CertifiedReproductionRow"
Cohesion: 0.28
Nodes (27): CalibrationErrorCount, ClusterSize, DbscanEpsilon, MemberIndex, NumericalEpsilon, OptionalParameterSimilarity, PairwiseDistance, PairwiseDistanceMatrix (+19 more)

### Community 52 - "iter_python_files"
Cohesion: 0.13
Nodes (21): modulefinder, test_no_stale_project_or_algorithm_aliases(), test_violation_detected_for_milestone_or_issue_reference(), test_violation_detected_for_stale_alias(), vocabulary_violations(), _annotation_names(), config_parameter_violations(), expr (+13 more)

### Community 53 - "ArtifactFamily"
Cohesion: 0.16
Nodes (24): CheckpointStageIdentity, ArtifactFamily, checkpoint_procedure_identity(), checkpoint_producer(), checkpoint_slot(), checkpoint_stage_instance(), CheckpointPayload, publish_anchor_checkpoints() (+16 more)

### Community 54 - "4. Audit requirements"
Cohesion: 0.15
Nodes (24): 4. Audit requirements, EffectSize, AblationVariant, ScientificCellSemanticKey, ablation_metric(), paired_standardized_effect_size(), PairedDifference, ablation_scenario_for_variant() (+16 more)

### Community 55 - "18.9 Exact comparison registry"
Cohesion: 0.08
Nodes (26): 18.10 Rounding, 18.1 Experimental unit and pairing, 18.2 Primary hypothesis tests, 18.3 Alpha and multiplicity, 18.4 Effect sizes, 18.5 Confidence intervals, 18.6 Materiality criteria, 18.7 Collapse/survival rules (+18 more)

### Community 56 - "Role"
Cohesion: 0.17
Nodes (22): PreparedViewSidecar, view_parquet_path(), prepared_view_publication_failures(), FailureMessage, Role, load_prepared_evidence_counts(), PreparedEvidenceProvenanceError, DatasetClassToken (+14 more)

### Community 57 - "comparison_evidence.py"
Cohesion: 0.20
Nodes (22): ArtifactInstanceLabel, comparison_evidence_failures(), comparison_evidence_slot(), current_comparison_evidence(), metric_evidence_digest(), PersistedComparisonEvidence, publish_comparison_evidence(), ArtifactDigest (+14 more)

### Community 58 - "run_smoke_suite"
Cohesion: 0.21
Nodes (21): SmokeCheckName, _data_invariants(), _extended_mathematical_invariants(), _extended_protocol_invariants(), _load_persisted_smoke_record(), _mathematical_invariants(), _protocol_invariants(), run_smoke_suite() (+13 more)

### Community 59 - "exact_sign_flip_two_sided_p_value"
Cohesion: 0.13
Nodes (21): NamedPValue, SignFlipAssignment, SignFlipSampleCount, enumerate_sign_flip_assignments(), exact_sign_flip_non_inferiority_p_value(), exact_sign_flip_two_sided_p_value(), holm_adjusted_p_values(), ComparisonMargin (+13 more)

### Community 60 - "ciciot2023/test_acquisition.py"
Cohesion: 0.22
Nodes (22): discover_secondary_csv_files(), read_csv_header(), resolve_label_column(), validate_consistent_header(), CICIoT2023Acquisition, Path, skipif, test_compute_file_checksum_is_a_sha256_hex_digest() (+14 more)

### Community 61 - "16.2 Core and mechanism baselines"
Cohesion: 0.09
Nodes (22): 16.1 Common budget rules, 16.2 Core and mechanism baselines, 16.3 Prior-art family representatives, 16.4 Baseline fairness, 16. Baseline contracts, `Candidate-Free Full Path`, `Centralized Reference`, `Client Review then One Independent Retrain` (+14 more)

### Community 62 - "RuntimeComponentName"
Cohesion: 0.16
Nodes (20): FrameType, Logger, logging, OperationResult, RuntimeError, RuntimeComponentName, configure_structured_file_logging(), get_structured_logger() (+12 more)

### Community 63 - "test_capability_contract.py"
Cohesion: 0.12
Nodes (20): ProductionWeight, ReproductionRowId, SourceExcludedFromKrum, validate_source_excluded_production_weight(), krum_input_excludes_source(), test_krum_input_rejects_source_row_identity(), test_source_excluded_production_weight_is_zero(), _contract() (+12 more)

### Community 64 - "35.2 Exact claim rules"
Cohesion: 0.10
Nodes (21): 35.1 State semantics, 35.2 Exact claim rules, 35. Claim-support decisions, `Authority Transition`, `Byzantine Operating Region`, `Conditional Non-Interference`, `Direct Source Exclusion`, `External Verification Necessity` (+13 more)

### Community 65 - "test_no_hardcoded_values.py"
Cohesion: 0.17
Nodes (19): Name, stmt, module_level_constant_values(), Module, test_no_module_level_constants_duplicate_governed_values(), test_violation_detected_for_duplicated_constant(), _uppercase_targets(), display_path() (+11 more)

### Community 66 - "ciciot2023/schema.py"
Cohesion: 0.16
Nodes (18): re, build_class_registry(), CICIoT2023TargetFamilyMember, _CICIoTBenignAlias, CICIoTRowIdentifierToken, normalize_label(), normalize_label_token(), BooleanValue (+10 more)

### Community 67 - "AdmissionOpeningMode"
Cohesion: 0.20
Nodes (19): ScreenDomainCount, AdmissionOpeningMode, candidate_free_full_path_opening_mode(), AdmissionOpeningEntry, candidate_screen_transition(), NamespaceSeed, screen_domain_order(), ScreenDomainResult (+11 more)

### Community 68 - "rules.py"
Cohesion: 0.21
Nodes (18): AdmissionStateIsTerminal, NewlyAdequateEvidenceExists, ResourceHorizonConfig, DormantOrigin, apply_logical_cycle_expiry(), _dormant_resume_state(), is_terminal_state(), EvidenceAdequate (+10 more)

### Community 69 - "5. Core Engineering Rules"
Cohesion: 0.10
Nodes (18): 1. Think Before Coding, 2. Simplicity First, 3. Surgical Changes, 4. Goal-Driven Execution, 5. Core Engineering Rules, 6. Static Analysis and Automated Enforcement, 7. Testing Rules, 8. Definition of Done (+10 more)

### Community 70 - "30. Experiment registry"
Cohesion: 0.10
Nodes (20): 30.10 `Mechanism Ablation`, 30.11 `Compromised-Reproducer Robustness`, 30.12 `Compromised-Verifier Robustness`, 30.13 `Byzantine-Bound Violation`, 30.14 `Evidence Scarcity and Dormancy`, 30.15 `Shared Epistemic-Failure Boundary`, 30.17 `Heterogeneous-Reproduction Boundary`, 30.18 `Admission-Delay Decomposition` (+12 more)

### Community 71 - "33.2 Result tables"
Cohesion: 0.10
Nodes (20): 33.1 Protocol tables, 33.2 Result tables, 33.3 Table rounding/significance display, 33. Required manuscript tables, `Ablation Results`, `Baseline Protocol`, `Byzantine Robustness`, `Collapse Decisions` (+12 more)

### Community 72 - "load_scientific_config"
Cohesion: 0.17
Nodes (17): load_scientific_config(), Path, YamlValue, _read_yaml_mapping(), ScientificConfig, validate_scientific_config(), Path, test_config_is_immutable() (+9 more)

### Community 73 - "discover_primary_csv_files"
Cohesion: 0.25
Nodes (19): compute_file_checksum(), compute_dataset_manifest_hash(), discover_primary_csv_files(), DatasetManifestDigest, Path, test_archive_and_already_extracted_layouts_yield_identical_dataset_manifest_hash(), Path, skipif (+11 more)

### Community 74 - "protocol_tables.py"
Cohesion: 0.24
Nodes (19): dataset_specification(), prepared_domain_summaries(), prepared_view_digest(), PreparedDomainSummary, domain_target_count(), _downstream_role(), eligibility_text(), _experiment_class_label() (+11 more)

### Community 75 - "test_experiment_registry_contracts.py"
Cohesion: 0.14
Nodes (17): experiment_names(), experiment_registry(), _rendered_table_names(), test_every_ablation_variant_is_dispatched_explicitly(), test_every_experiment_declares_a_known_dataset(), test_every_experiment_declares_an_artifact_specification(), test_every_experiment_declares_its_scientific_matrix(), test_every_experiment_name_is_unique() (+9 more)

### Community 76 - "baselines/test_registry.py"
Cohesion: 0.13
Nodes (18): BaselineFullParticipationAllowed, domain_target_view(), domain_without_target_view_may_participate(), first_eligible_non_source_reproducer(), PostReferenceDataAccess, DomainId, single_fresh_verifier_domain(), single_fresh_verifier_outcome() (+10 more)

### Community 77 - ".run"
Cohesion: 0.12
Nodes (15): Fresh Graphify callable inventory — final pass, Prospective experiment workflow counts, Union, Short end-to-end test scope, Audit findings, Audit continuation, 2026-09-26, Completed discovery, Findings so far (+7 more)

### Community 78 - "test_workflow_call_topology.py"
Cohesion: 0.21
Nodes (18): _called_names(), _called_names_for_node(), _method_node(), _missing_calls(), AST, FunctionDef, Path, test_application_wires_every_cli_command() (+10 more)

### Community 79 - "15. Adversarial and diagnostic transformation registry"
Cohesion: 0.11
Nodes (18): 15.10 Transformation cardinality, root-cause, and controlled-episode completion rules, 15.1 Useful + hidden-backdoor source, 15.2 Byzantine reproduction strategies, 15.3 Byzantine verifier behavior, 15.4 Shared label-error boundary, 15.5 Shared spurious-feature boundary, 15.6 Attacker-induced common-context boundary, 15.7 Capability under-specification fixture (+10 more)

### Community 80 - "screen_fold_index"
Cohesion: 0.21
Nodes (17): FoldCount, FoldIndex, ScreenDifferential, match_held_out_fold(), proposal_screen_differential(), DerivedSeed, SampleId, run_proposal_screen_for_domain() (+9 more)

### Community 81 - "ArtifactSlot"
Cohesion: 0.18
Nodes (16): hashlib, ArtifactSlot, PreparedRoleViewManifest, _parquet_checksum(), ArtifactDigest, Path, PreparedViewKey, RowCount (+8 more)

### Community 82 - "TernaryOutcome"
Cohesion: 0.19
Nodes (15): CompletionCycleIndex, EvidenceArrivalCycleIndex, ReproductionRowCertified, ByzantineVerifierBehavior, TernaryOutcome, resolve_byzantine_verifier_vote(), validate_no_safety_completion_before_tau_k(), reproduction_row_is_certified() (+7 more)

### Community 83 - "17.2 Capability Contract metrics"
Cohesion: 0.12
Nodes (17): 17.2 Capability Contract metrics, Anchor training budgets and cadences, Benign false-alarm-rate increase, Checkpoint artifacts, Data loading, Metric adequacy minima, Persisted cell evidence and reuse, Persisted statistical comparison evidence (+9 more)

### Community 84 - ".values"
Cohesion: 0.22
Nodes (13): ScientificCellSemanticKeyTuple, ArtifactDigest, CodeRevision, ComparisonName, EvidenceCycleIndex, MasterSeed, MethodName, MetricName (+5 more)

### Community 85 - "ast"
Cohesion: 0.20
Nodes (13): ast, find_duplicate_constant_names(), module_constant_names(), Module, Path, test_no_constant_name_defined_in_more_than_one_module(), test_violation_detected_for_duplicate_constant_name(), temporary_marker_violations() (+5 more)

### Community 86 - "cli.py"
Cohesion: 0.21
Nodes (12): command, Per-command reachability, rich_console, plan(), preprocess(), OverwriteExisting, report(), run_experiment() (+4 more)

### Community 87 - "artifact_identity"
Cohesion: 0.22
Nodes (13): artifact_identity(), ProcedureIdentity, ablation_reference_records(), ablation_reference_slot(), PersistedAblationReference, MasterSeed, ScenarioName, materialize_ablation_references() (+5 more)

### Community 88 - "fit_feature_moments"
Cohesion: 0.24
Nodes (12): FeatureMoments, FeatureStatistic, fit_feature_moments(), model_validator, Self, _statistic(), test_feature_moments_reject_inconsistent_lengths(), test_feature_moments_reject_nonpositive_scale() (+4 more)

### Community 89 - "test_no_any_dict_object.py"
Cohesion: 0.24
Nodes (14): annotation_occurrences(), annotation_violations(), forbidden_symbol_violations(), expr, Module, raw_mapping_violations(), test_any_annotation_is_detected(), test_dictionary_construction_is_detected() (+6 more)

### Community 90 - "apply_sampling_cap"
Cohesion: 0.23
Nodes (12): DatasetFileDigest, SamplingSelectionDigest, SourceRowIndex, apply_sampling_cap(), ClassLabel, sampling_cap_selection_digest(), test_apply_sampling_cap_is_deterministic_across_runs(), test_apply_sampling_cap_returns_all_rows_when_under_the_cap() (+4 more)

### Community 91 - "34. Required manuscript figures"
Cohesion: 0.14
Nodes (14): 34.10 `Heterogeneity Synthesis Boundary`, 34.11 `Admission-Delay Decomposition`, 34.12 `Efficiency Profile`, 34.13 `Secondary Generalization`, 34.1 `FedSIRA Protocol Schematic`, 34.2 `Primary Security–Utility Tradeoff`, 34.3 `Useful Backdoored Source`, 34.4 `Collapse Decision Effects` (+6 more)

### Community 92 - "select_krum_update"
Cohesion: 0.25
Nodes (13): KrumNeighborCount, KrumScore, krum_neighbor_count(), krum_score(), CommitteeSize, MaximumByzantineReproductionRows, select_krum_update(), _row() (+5 more)

### Community 93 - "ElapsedTimer"
Cohesion: 0.16
Nodes (9): TimingWorkerObservation, ElapsedTimer, WallClockSeconds, test_elapsed_timer_advances(), test_elapsed_timer_fresh_instance_restarts(), test_elapsed_timer_is_non_negative(), test_peak_host_resident_set_bytes_is_positive(), time (+1 more)

### Community 94 - "FailureClass"
Cohesion: 0.27
Nodes (11): AutomaticallyRetriable, AutomaticRecoveryPermitted, RetryCount, FailureClass, automatic_recovery_permitted(), is_automatically_retriable(), test_data_invalid_is_never_automatically_retried(), test_infrastructure_interruption_is_not_permitted_after_limit_reached() (+3 more)

### Community 95 - "screen_domain_decision_is_positive"
Cohesion: 0.15
Nodes (13): ScreenDomainDecision, candidate_free_screen_domain_predicate(), raw_target_f1_screen_domain_decision_is_positive(), screen_domain_decision_is_positive(), unmatched_control_screen_domain_decision_is_positive(), test_candidate_free_screen_domain_predicate_boundary(), test_raw_target_f1_screen_domain_decision_fails_when_target_gain_too_small(), test_raw_target_f1_screen_domain_decision_ignores_the_differential() (+5 more)

### Community 96 - "load_published_manifests"
Cohesion: 0.46
Nodes (12): InvalidArtifactReport, load_published_manifests(), _manifest_text(), _point_current_at(), Path, test_absent_root_yields_no_manifests(), test_current_publication_is_loaded(), test_obsolete_current_schema_is_rejected_as_invalid_evidence() (+4 more)

### Community 97 - "build_comparison_results_for_experiment"
Cohesion: 0.31
Nodes (13): _benefit_difference(), build_comparison_results_for_experiment(), _comparison_pairs(), extend_index_from_records(), merge_metric_record(), merge_metric_records(), metric_index_from_outcomes(), metric_value() (+5 more)

### Community 98 - "CLI workflow traces"
Cohesion: 0.17
Nodes (8): CLI workflow traces, `doctor`, `plan`, `preprocess [dataset] [--overwrite]`, `report [ExperimentName] [--overwrite]`, `run <ExperimentName> [--overwrite]` (prospective only), `smoke [--overwrite]`, `status`

### Community 99 - "evaluation/test_validation.py"
Cohesion: 0.27
Nodes (10): EvaluationValidationError, FailureMessage, ValueError, validate_metric_class_membership(), test_metric_class_membership_accepts_valid_configuration(), test_metric_class_membership_rejects_benign_outside_vocabulary(), test_metric_class_membership_rejects_supported_outside_vocabulary(), test_metric_class_membership_rejects_target_outside_vocabulary() (+2 more)

### Community 100 - "test_epistemic_failure.py"
Cohesion: 0.20
Nodes (11): diagnostic_marker_metric_or_insufficient(), match_diagnostic_benign_report_test_rows(), ArtifactDigest, test_apply_attacker_induced_common_context_sets_all_four_indices(), test_apply_shared_spurious_feature_sets_only_the_given_index(), test_diagnostic_marker_metric_is_insufficient_when_no_match(), test_diagnostic_marker_metric_returns_value_when_matched(), test_match_diagnostic_benign_report_test_rows_matches_by_nearest_loss() (+3 more)

### Community 101 - "FedSIRAApplication"
Cohesion: 0.33
Nodes (5): ApplicationExitCode, Console, FedSIRAApplication, OverwriteExisting, render()

### Community 102 - "16.5 Baseline implementation completion rules"
Cohesion: 0.18
Nodes (11): 16.5 Baseline implementation completion rules, Baseline validation fixture map, Density-cluster baseline, FLCert-style ensemble, Parameter-similarity ablation, Reconstruction-filter calibration, Recovery baseline, Review-style baselines (+3 more)

### Community 103 - "test_preprocess_plan_smoke.py"
Cohesion: 0.20
Nodes (6): doctor(), _no_mismatches(), MonkeyPatch, test_doctor_command_reports_configuration_and_next_action(), MonkeyPatch, test_status_renders_planned_experiment_lifecycle()

### Community 105 - "10. Exact data roles, sampling, and preprocessing"
Cohesion: 0.20
Nodes (8): 10.1 Supported-class role intervals, 10.2 Target-class role intervals, 10.3 Deterministic sampling caps, 10.4 Data validation, 10.5 Scaling, 10.6 Preprocessing semantic identity, 10. Exact data roles, sampling, and preprocessing, RowCount

### Community 106 - "13. Role assignment, seeds, security profiles, and deterministic ties"
Cohesion: 0.20
Nodes (10): 13.1 Master seeds, 13.2 Seed namespaces and canonical hash semantics, 13.3 Deterministic ordering instead of hidden RNG defaults, 13.4 Source selection, 13.5 Proposal-screen fold and matching semantics, 13.6 Primary deterministic verifier profile, 13.7 Diagnostic random verifier profile, 13.8 Compromised reproducer selection (+2 more)

### Community 107 - "7. Exact FedSIRA procedure"
Cohesion: 0.20
Nodes (10): 7.1 Admission opening, 7.2 Proposal screen, 7.3 Source-independent reproduction, 7.4 External verification, 7.5 Reproducibility certificate, 7.6 Robust source-excluded synthesis: Krum, 7.7 Final fresh gate, 7. Exact FedSIRA procedure (+2 more)

### Community 108 - "8. Theory and proof obligations"
Cohesion: 0.20
Nodes (10): 8.1 Pre-independent-evidence indistinguishability, 8.2 Independent evidence proposition, 8.3 Claim-conditional direct source-artifact non-interference, 8.4 Honest-support counting, 8.5 Synthesizer-specific reproduction count, 8.6 Conditional safety/liveness, 8.7 Independent-evidence delay lower bound, 8.8 Random-committee contamination calculation (+2 more)

### Community 109 - "direct_krum_committee_rows"
Cohesion: 0.22
Nodes (9): NonAbstainingReproductionSeries, ParticipantCount, ThreeRowCoordinateMedianConfig, direct_krum_committee_rows(), CommitteeSize, validate_three_row_coordinate_median_committee_size(), test_direct_krum_committee_rows_filters_abstaining_and_requires_committee_size(), test_direct_krum_committee_rows_none_when_insufficient_non_abstaining_rows() (+1 more)

### Community 110 - "observations.py"
Cohesion: 0.29
Nodes (9): DescriptiveScientificMetric, declared_contract_scopes(), measurement_cycles(), observation_value(), observations_with_replacements(), permanent_singleton_admission(), EligibleEvidenceHolderCount, EvidenceCycleIndex (+1 more)

### Community 111 - "test_enum_integrity.py"
Cohesion: 0.40
Nodes (9): annotation_names(), enum_class_defs(), ClassDef, Module, Path, test_enum_used_only_as_its_own_annotation_is_still_flagged(), test_every_enum_is_referenced_outside_or_used_as_a_typed_field(), test_violation_detected_for_unused_enum() (+1 more)

### Community 112 - "source_selection_order"
Cohesion: 0.31
Nodes (8): AttackCarrierRequired, select_source_domain(), source_selection_order(), test_select_source_domain_picks_first_with_target_stream(), test_select_source_domain_requires_gafgyt_udp_carrier_when_needed(), test_select_source_domain_returns_none_when_no_domain_qualifies(), test_source_selection_order_is_deterministic_and_a_permutation(), test_source_selection_order_is_reproducible_for_the_same_seed()

### Community 113 - "Final audit evidence"
Cohesion: 0.22
Nodes (7): Empirical and architecture deviation ledger, Current gate, Final audit evidence, Prepared-output validation, Production rerun and cache identity, Real datasets and raw provenance, Safe checks already completed

### Community 114 - "FedSIRA Pre-Experiment Audit Matrix"
Cohesion: 0.22
Nodes (8): 1. Purpose and scope, 2. Authority hierarchy, 3. Status and severity definitions, 5. Fresh Graphify / callable-count summary template, 6. Per-command / per-workflow callable-count template, 7. Required later audit execution order, 8. Final pre-experiment acceptance gate, FedSIRA Pre-Experiment Audit Matrix

### Community 115 - "Scientific and workflow test crosswalk"
Cohesion: 0.22
Nodes (8): Remaining test-coverage actions, Scientific and workflow test crosswalk, TEST-001 — Scientific mathematics, TEST-002 — Data invariants, TEST-003 — Protocol states and guards, TEST-004 — Metrics and statistical rules, test_final_gate_predicates_pass_requires_all_four_thresholds_and_no_invariant_failure(), test_validate_commitment_exists_before_verifier_assignment()

### Community 116 - "test_no_comments_or_docstrings.py"
Cohesion: 0.33
Nodes (8): io, has_comment_token(), has_docstring(), Module, test_no_comments_or_docstrings_in_repository_python_source(), test_violation_detected_for_comment(), test_violation_detected_for_docstring(), tokenize

### Community 117 - "independent_local_reference_reviewer_is_positive"
Cohesion: 0.31
Nodes (8): ReviewerPositiveDecision, independent_local_reference_reviewer_is_positive(), CapabilityContractSatisfied, test_independent_local_reference_reviewer_negative_beyond_benign_far_margin(), test_independent_local_reference_reviewer_negative_beyond_supported_f1_margin(), test_independent_local_reference_reviewer_negative_when_capability_contract_fails(), test_independent_local_reference_reviewer_positive_within_noninferiority_margins(), test_secure_continual_assessment_post_reference_rounds_uses_governed_config()

### Community 118 - "test_no_redirects_shims_reexports.py"
Cohesion: 0.39
Nodes (8): is_pure_redirect(), package_reexports(), Module, test_compliant_module_with_definitions_passes(), test_no_non_init_module_is_a_pure_redirect(), test_package_initializers_do_not_publish_imported_compatibility_aliases(), test_violation_detected_for_package_reexport_facade(), test_violation_detected_for_redirect_module()

### Community 119 - "test_no_test_only_production_code.py"
Cohesion: 0.42
Nodes (8): occurrence_count(), public_top_level_symbols(), Module, Path, referenced_in(), test_no_public_production_symbol_used_only_by_tests(), test_symbol_used_elsewhere_in_its_own_file_counts_as_used(), test_violation_detected_for_test_only_symbol()

### Community 120 - "test_public_type_boundaries.py"
Cohesion: 0.42
Nodes (8): is_fully_annotated(), public_top_level_functions(), FunctionDef, Module, test_compliant_function_passes(), test_public_boundary_functions_are_fully_annotated(), test_violation_detected_for_unannotated_public_function(), violations_in_tree()

### Community 121 - "24. Public CLI contract"
Cohesion: 0.25
Nodes (8): 24.1 `fedsira doctor`, 24.2 `fedsira preprocess ["N-BaIoT"|"CICIoT2023"]`, 24.3 `fedsira plan`, 24.4 `fedsira smoke`, 24.5 `fedsira status`, 24.6 `fedsira run <experiment name>`, 24.7 `fedsira report [<experiment name>]`, 24. Public CLI contract

### Community 122 - "9. Primary dataset and experimental domain construction"
Cohesion: 0.25
Nodes (8): 9.1.1 Raw release discovery and canonical mapping, 9.1 Primary dataset, 9.2 Domain proxies, 9.3 Class vocabulary, 9.4 Post-reference capability, 9.5 Supported classes, 9.6 Controlled replay semantics, 9. Primary dataset and experimental domain construction

### Community 123 - "pytest"
Cohesion: 0.39
Nodes (7): pytest, declared_source_backdoor_poison_fractions(), Probability, validate_declared_source_backdoor_poison_fraction(), test_an_undeclared_poison_fraction_is_rejected(), test_declared_poison_sweep_comes_from_configuration(), test_every_declared_poison_fraction_is_admissible()

### Community 124 - "BaselineIdentity"
Cohesion: 0.50
Nodes (7): BaselineIdentity, BaselineContract, BaselineValidationFixture, _fixture_for(), test_fixture_map_covers_every_registered_baseline_exactly_once(), test_ordinary_utility_references_use_legitimate_target_capability(), test_robust_update_filtering_references_use_model_replacement_backdoor()

### Community 125 - "test_no_free_string_enum_bypass.py"
Cohesion: 0.50
Nodes (7): enum_member_values(), Module, Path, string_literals(), test_no_free_string_enum_value_bypass_across_modules(), test_owner_module_usage_not_flagged(), test_violation_detected_for_free_string_enum_value()

### Community 127 - "test_enums.py"
Cohesion: 0.25
Nodes (7): test_artifact_lifecycle_state_members(), test_dataset_id_has_exactly_the_two_roadmap_datasets(), test_enum_members_are_not_equal_to_plain_strings_by_construction(), test_experiment_lifecycle_state_members(), test_failure_class_has_exactly_nine_classes(), test_scientific_cell_phase_has_exactly_six_phases(), test_seed_derivation_label_retains_the_fifteen_namespace_tokens()

### Community 128 - "12. Model, anchor training, source training, and reproduction training"
Cohesion: 0.29
Nodes (7): 12.1 Base classifier, 12.2 Common optimizer and loss constants, 12.3 Anchor FedAvg, 12.4 Post-reference training contract, 12.5 Verifier-aware malicious training override, 12.6 No test-set tuning, 12. Model, anchor training, source training, and reproduction training

### Community 129 - "26. Scientific output contract"
Cohesion: 0.29
Nodes (7): 26.1 Scientific execution dependencies, 26.2 Artifact validity and lifecycle, 26.3 Reusable artifact families, 26.4 Selective invalidation boundaries, 26.5 Experiment dependency and reuse map, 26.6 Cross-experiment reuse rules, 26. Scientific output contract

### Community 130 - "28. Validation and smoke-test contract"
Cohesion: 0.29
Nodes (7): 28.1 Data tests, 28.2 Model/FL tests, 28.3 Protocol invariant tests, 28.4 Mathematical tests, 28.5 Metric/statistical tests, 28.6 Artifact reuse and recovery tests, 28. Validation and smoke-test contract

### Community 131 - "test_generic_wrappers.py"
Cohesion: 0.48
Nodes (6): generic_wrapper_violations(), Module, test_production_code_uses_no_generic_numeric_wrappers(), test_qualified_forbidden_alias_is_detected(), test_stringified_forbidden_alias_annotation_is_detected(), test_violation_detected_in_private_nested_generic_and_alias()

### Community 132 - "test_naming_policy.py"
Cohesion: 0.48
Nodes (6): naming_violations(), Module, test_no_banned_generic_artificial_or_forbidden_names(), test_violation_detected_for_forbidden_identifier(), test_violation_detected_for_generic_module_name(), test_violation_detected_for_versioned_symbol_name()

### Community 133 - "1. Scientific problem, contribution boundary, and claims"
Cohesion: 0.33
Nodes (6): 1.1 Research problem, 1.2 Core authority transition, 1.3 Required mechanism, 1.4 Safe manuscript claims, 1.5 Forbidden claims, 1. Scientific problem, contribution boundary, and claims

### Community 134 - "minimum_honest_positive_count"
Cohesion: 0.33
Nodes (6): MaximumByzantineReportCount, MinimumHonestPositiveReportCount, minimum_honest_positive_count(), ObservedPositiveReportCount, test_minimum_honest_positive_count_bound(), test_primary_verifier_profile_guarantees_at_least_one_honest_positive()

### Community 135 - "background-jobs.md"
Cohesion: 0.40
Nodes (4): 2026-09-25 follow-up, 2026-09-26 continuation, Fresh audit, 2026-09-25, WSL resumed, 2026-09-25

### Community 136 - "6. FedSIRA state machine and non-negotiable invariants"
Cohesion: 0.40
Nodes (5): 6.1 States, 6.2 Resource horizon, 6.3 Exact transition and scheduling table, 6.4 Invariants, 6. FedSIRA state machine and non-negotiable invariants

### Community 137 - "FedSIRA"
Cohesion: 0.40
Nodes (4): CLI usage, FedSIRA, Reproducibility, Setup

### Community 138 - "StructuredJsonFormatter"
Cohesion: 0.50
Nodes (3): LogRecord, LogRecordText, StructuredJsonFormatter

### Community 139 - "_ListConvertibleTensor"
Cohesion: 0.50
Nodes (3): ModelParameterValue, _ListConvertibleTensor, Protocol

## Knowledge Gaps
- **330 isolated node(s):** `Baseline validation fixture map`, `Density-cluster baseline`, `FLCert-style ensemble`, `Parameter-similarity ablation`, `Reconstruction-filter calibration` (+325 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 849 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **44 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExperimentName` connect `ExperimentName` to `handlers.py`, `application.py`, `export.py`, `AdmissionState`, `figures.py`, `execution.py`, `comparisons.py`, `ExperimentLifecycleState`, `enums.py`, `tables.py`, `store.py`, `screen_evidence.py`, `collapse.py`, `paths.py`, `runtime.py`, `planning.py`, `models.py`, `artifact_slot_directory`, `ArtifactFamily`, `comparison_evidence.py`, `protocol_tables.py`, `test_experiment_registry_contracts.py`, `.run`, `ArtifactSlot`, `.values`, `cli.py`, `build_comparison_results_for_experiment`, `FedSIRAApplication`, `observations.py`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Why does `current_application_context()` connect `handlers.py` to `common.py`, `FedSIRAClassifier`, `baselines/training.py`, `application.py`, `export.py`, `AdmissionState`, `figures.py`, `execution.py`, `comparisons.py`, `ciciot2023/prepare.py`, `ExperimentLifecycleState`, `post_reference.py`, `enums.py`, `tables.py`, `store.py`, `FrozenDomainModel`, `federated.py`, `nbaiot/prepare.py`, `ProtocolCellExecutor`, `screen_evidence.py`, `collapse.py`, `paths.py`, `nbaiot_adapter`, `admission.py`, `reproduction_progression`, `defenses.py`, `MetricResult`, `runtime.py`, `planning.py`, `statistics.py`, `learning/training.py`, `ExperimentName`, `framed_bytes`, `ciciot2023/test_preprocessing.py`, `materialize_nbaiot_prepared_views`, `artifact_slot_directory`, `test_theory.py`, `ArtifactFamily`, `4. Audit requirements`, `Role`, `comparison_evidence.py`, `run_smoke_suite`, `AdmissionOpeningMode`, `protocol_tables.py`, `screen_fold_index`, `TernaryOutcome`, `build_comparison_results_for_experiment`, `test_epistemic_failure.py`, `observations.py`, `pytest`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Why does `FrozenDomainModel` connect `FrozenDomainModel` to `handlers.py`, `common.py`, `application.py`, `export.py`, `AdmissionState`, `figures.py`, `execution.py`, `comparisons.py`, `ciciot2023/prepare.py`, `ExperimentLifecycleState`, `enums.py`, `tables.py`, `store.py`, `federated.py`, `nbaiot/prepare.py`, `ProtocolCellExecutor`, `screen_evidence.py`, `collapse.py`, `admission.py`, `reproduction_progression`, `defenses.py`, `MetricResult`, `runtime.py`, `planning.py`, `models.py`, `framed_bytes`, `NBaiotClass`, `materialize_nbaiot_prepared_views`, `artifact_slot_directory`, `EvidenceArrivalSchedule`, `test_common.py`, `CertifiedReproductionRow`, `ArtifactFamily`, `Role`, `comparison_evidence.py`, `run_smoke_suite`, `ciciot2023/schema.py`, `AdmissionOpeningMode`, `protocol_tables.py`, `baselines/test_registry.py`, `screen_fold_index`, `ArtifactSlot`, `artifact_identity`, `fit_feature_moments`, `load_published_manifests`, `build_comparison_results_for_experiment`, `BaselineIdentity`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `current_application_context()` (e.g. with `test_standard_fl_baseline_budget_reads_yaml()` and `test_declared_poison_sweep_comes_from_configuration()`) actually correct?**
  _`current_application_context()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 31 inferred relationships involving `FrozenDomainModel` (e.g. with `CalibrationErrorCount` and `CellHandlerName`) actually correct?**
  _`FrozenDomainModel` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 150 inferred relationships involving `ExperimentName` (e.g. with `_all_complete()` and `_collapse_experiment_completed()`) actually correct?**
  _`ExperimentName` has 150 INFERRED edges - model-reasoned connections that need verification._
- **Are the 97 inferred relationships involving `AdmissionState` (e.g. with `AdmissionStateIsTerminal` and `CellHandlerName`) actually correct?**
  _`AdmissionState` has 97 INFERRED edges - model-reasoned connections that need verification._