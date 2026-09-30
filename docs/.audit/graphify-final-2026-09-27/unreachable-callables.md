# Production callables outside the prospective CLI union

Count: 21 (7 functions, 14 class methods). Static absence is not proof of dead code.

| Source | Callable | Graphify id |
|---|---|---|
| `src/fedsira/artifacts/paths.py` | `experiment_telemetry_root()` | `src_fedsira_artifacts_paths_experiment_telemetry_root` |
| `src/fedsira/artifacts/store.py` | `.family()` | `src_fedsira_artifacts_store_artifactmanifest_family` |
| `src/fedsira/datasets/ciciot2023/schema.py` | `.raw_token()` | `src_fedsira_datasets_ciciot2023_schema_ciciot2023targetfamilymember_raw_token` |
| `src/fedsira/datasets/common.py` | `.row_count()` | `src_fedsira_datasets_common_preparedrows_row_count` |
| `src/fedsira/datasets/common.py` | `.supported_class_tokens()` | `src_fedsira_datasets_common_datasetadapter_supported_class_tokens` |
| `src/fedsira/datasets/nbaiot/prepare.py` | `.row_count()` | `src_fedsira_datasets_nbaiot_prepare_preparedview_row_count` |
| `src/fedsira/experiments/definitions.py` | `_unique()` | `src_fedsira_experiments_definitions_unique` |
| `src/fedsira/experiments/definitions.py` | `experiment_names()` | `src_fedsira_experiments_definitions_experiment_names` |
| `src/fedsira/experiments/engine.py` | `.__call__()` | `src_fedsira_experiments_engine_comparisonresultbuilder_call` |
| `src/fedsira/experiments/handlers.py` | `.__call__()` | `src_fedsira_experiments_handlers_cellhandler_call` |
| `src/fedsira/experiments/handlers.py` | `._configured_backdoor_scope()` | `src_fedsira_experiments_handlers_protocolcelldispatch_configured_backdoor_scope` |
| `src/fedsira/learning/model.py` | `.forward()` | `src_fedsira_learning_model_fedsiraclassifier_forward` |
| `src/fedsira/learning/training.py` | `.__iter__()` | `src_fedsira_learning_training_declaredbatchdataset_iter` |
| `src/fedsira/learning/training.py` | `.step()` | `src_fedsira_learning_training_steppableoptimizer_step` |
| `src/fedsira/protocol/reproduction.py` | `.tolist()` | `src_fedsira_protocol_reproduction_listconvertibletensor_tolist` |
| `src/fedsira/protocol/rules.py` | `reproducer_order()` | `src_fedsira_protocol_rules_reproducer_order` |
| `src/fedsira/reporting/figures.py` | `draw_admission()` | `src_fedsira_reporting_figures_render_heterogeneity_synthesis_boundary_draw_admission` |
| `src/fedsira/runtime.py` | `.__call__()` | `src_fedsira_runtime_torchseedfunction_call` |
| `src/fedsira/runtime.py` | `.format()` | `src_fedsira_runtime_structuredjsonformatter_format` |
| `src/fedsira/runtime.py` | `get_structured_logger()` | `src_fedsira_runtime_get_structured_logger` |
| `src/fedsira/runtime.py` | `sort_key()` | `src_fedsira_runtime_minibatch_order_sort_key` |
