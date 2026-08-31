from __future__ import annotations

import csv
from io import StringIO

from fedsira.analysis.claims import CLAIM_DEFINITIONS, ClaimDefinition, ClaimStateResult
from fedsira.analysis.comparisons import (
    ComparisonDefinition,
    ComparisonFamilyResult,
    ComparisonMetric,
    ComparisonReferenceKind,
    ComparisonResult,
    ComparisonState,
    ComparisonTestKind,
    MaterialityDirection,
    build_comparison_registry,
)
from fedsira.baselines.registry import (
    BASELINE_VALIDATION_FIXTURE_MAP,
    BaselineIdentity,
    BaselineValidationFixture,
)
from fedsira.config.schema import PublicationRoundingConfig
from fedsira.datasets.ciciot2023.schema import (
    OFFICIAL_EXPECTED_PREDICTOR_COUNT,
    PSEUDO_DOMAIN_COUNT,
    TARGET_LABEL,
)
from fedsira.datasets.nbaiot.preprocessing import NBAIOT_PRIMARY_PREDICTOR_COUNT
from fedsira.datasets.nbaiot.schema import NBAIOT_CLASS_ORDER, NBAIOT_DOMAIN_ORDER
from fedsira.domain.records import (
    ExperimentName,
    FormattedStatisticText,
    FrozenDomainModel,
    MethodName,
    MetricValue,
    PValue,
    ScenarioName,
    TableCsvText,
    TableName,
    TextValue,
)
from fedsira.experiments.collapse import (
    CollapseDecision,
    CollapseDecisionKind,
    ProductionUpdateRule,
    ReproductionRowRequirement,
    ResolvedCore,
    RowVerificationMode,
)
from fedsira.experiments.planning import ExperimentPlan
from fedsira.experiments.registry import (
    ADMISSION_DELAY_DECOMPOSITION_NAME,
    BYZANTINE_BOUND_VIOLATION_NAME,
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
    MECHANISM_ABLATION_NAME,
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    SECONDARY_DATASET_GENERALIZATION_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    AblationVariant,
    ExperimentClass,
    PrimaryScenario,
)
from fedsira.runtime.state import current_application_context

MANUSCRIPT_TABLE_NAMES: tuple[TableName, ...] = (
    "Dataset and Domain Protocol",
    "Primary Domain Statistics",
    "Model and Training Protocol",
    "Security and Capability-Contract Protocol",
    "Baseline Protocol",
    "Experiment Plan",
    "Metric and Statistics Protocol",
    "Primary Results",
    "Source-Exclusion Results",
    "Collapse Decisions",
    "Ablation Results",
    "Byzantine Robustness",
    "Failure Boundaries",
    "Delay and Efficiency",
    "Generalization Results",
    "Statistical Summary",
    "Claim Support",
)


class RenderedTable(FrozenDomainModel):
    name: TableName
    csv_text: TableCsvText


def _csv_text(
    header: tuple[TextValue, ...],
    rows: tuple[tuple[TextValue, ...], ...],
) -> TextValue:
    buffer = StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue().rstrip("\n")


def _publication_rounding() -> PublicationRoundingConfig:
    statistics = current_application_context().scientific_config.metrics_and_statistics
    return statistics.publication_rounding


def format_metric_value(value: MetricValue | None) -> FormattedStatisticText:
    rounding = _publication_rounding()
    if value is None:
        return "NA"
    return f"{value:.{rounding.f1_accuracy_rates_decimals}f}"


def format_p_value(value: PValue | None) -> FormattedStatisticText:
    rounding = _publication_rounding()
    if value is None:
        return "NA"
    if value < rounding.p_value_display_floor:
        return f"<{rounding.p_value_display_floor:.4f}"
    return f"{value:.{rounding.p_value_significant_digits}g}"


def _experiment_class_label(experiment_class: ExperimentClass) -> TextValue:
    return experiment_class.value


def render_experiment_plan_table(plan: ExperimentPlan) -> RenderedTable:
    rows = tuple(
        (
            planned.definition.name,
            _experiment_class_label(planned.definition.experiment_class),
            str(len(planned.definition.methods)),
            str(len(planned.definition.conditions)),
            str(planned.definition.seed_count),
            str(len(planned.cells)),
            (
                planned.definition.claim_family.value
                if planned.definition.claim_family is not None
                else "NA"
            ),
        )
        for planned in plan.experiments
    )
    return RenderedTable(
        name="Experiment Plan",
        csv_text=_csv_text(
            (
                "experiment",
                "class",
                "methods",
                "conditions",
                "seeds",
                "nominal_run_count",
                "claim_family",
            ),
            rows,
        ),
    )


def _comparison_reference_label(definition: ComparisonDefinition) -> TextValue:
    if definition.reference_kind is ComparisonReferenceKind.ZERO:
        return ComparisonReferenceKind.ZERO.value
    if (
        definition.reference_experiment == definition.experiment
        and definition.reference_scenario == definition.scientific_scenario
    ):
        return definition.reference_method
    if (
        definition.reference_experiment == definition.experiment
        and definition.reference_method == definition.method
    ):
        return definition.reference_scenario
    return (
        f"{definition.reference_experiment} / "
        f"{definition.reference_scenario} / {definition.reference_method}"
    )


def _statistical_summary_row(
    family: ComparisonFamilyResult,
    comparison: ComparisonResult,
) -> tuple[TextValue, ...]:
    definition = comparison.definition
    effect = (
        "NA"
        if comparison.paired_standardized_effect is None
        else f"{comparison.paired_standardized_effect:.3f}"
    )
    confidence_interval = (
        "NA"
        if comparison.confidence_interval is None
        else (
            f"[{comparison.confidence_interval[0]:.3f}," f"{comparison.confidence_interval[1]:.3f}]"
        )
    )
    margin = "NA" if definition.margin is None else f"{definition.margin:.3f}"
    materiality = (
        "NA" if definition.material_threshold is None else f"{definition.material_threshold:.3f}"
    )
    reference_label = _comparison_reference_label(definition)
    comparison_identity = (
        f"{definition.method} vs {reference_label} | "
        f"{definition.scientific_scenario} | {definition.metric.value}"
    )
    test_kind: ComparisonTestKind = definition.test_kind
    materiality_direction: MaterialityDirection = definition.materiality_direction
    return (
        family.family.value,
        comparison_identity,
        definition.metric.value,
        definition.orientation.value,
        test_kind.value,
        materiality_direction.value,
        margin,
        str(comparison.complete_seed_count),
        format_metric_value(comparison.mean_paired_difference),
        format_metric_value(comparison.median_paired_difference),
        effect,
        format_p_value(comparison.raw_p_value),
        format_p_value(comparison.adjusted_p_value),
        confidence_interval,
        materiality,
        "pass" if comparison.comparison_state is ComparisonState.PASSED else "fail",
        "pass" if comparison.materiality_passes is not False else "fail",
        comparison.comparison_state.value,
    )


def render_statistical_summary_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
) -> RenderedTable:
    rows = tuple(
        _statistical_summary_row(family, comparison)
        for family in comparison_results
        for comparison in family.comparisons
    )
    return RenderedTable(
        name="Statistical Summary",
        csv_text=_csv_text(
            (
                "claim",
                "comparison",
                "metric",
                "direction",
                "test_kind",
                "materiality_direction",
                "margin",
                "n_pairs",
                "mean_difference",
                "median_difference",
                "paired_dz",
                "raw_p",
                "holm_p",
                "confidence_interval_95",
                "materiality_threshold",
                "statistical_pass",
                "materiality_pass",
                "final_comparison_state",
            ),
            rows,
        ),
    )


def _claim_definition(claim_id: TextValue) -> ClaimDefinition | None:
    for definition in CLAIM_DEFINITIONS:
        if definition.claim_id == claim_id:
            return definition
    return None


def render_claim_support_table(
    claim_states: tuple[ClaimStateResult, ...],
) -> RenderedTable:
    rows_list: list[tuple[TextValue, ...]] = []
    for state in claim_states:
        definition = _claim_definition(state.claim_id)
        evidence = "|".join(definition.evidence_experiments) if definition is not None else "NA"
        metric = (
            definition.primary_metric
            if definition is not None and definition.primary_metric is not None
            else "NA"
        )
        required = (
            definition.required_family.value
            if definition is not None and definition.required_family is not None
            else "NA"
        )
        rows_list.append(
            (
                state.claim_id,
                state.scope,
                evidence,
                metric,
                required,
                state.state.value,
                "Claim Support",
                "FedSIRA Protocol Schematic",
                state.scope,
                state.reason,
            )
        )
    rows = tuple(rows_list)
    return RenderedTable(
        name="Claim Support",
        csv_text=_csv_text(
            (
                "claim",
                "exact_scoped_claim",
                "evidence_experiments",
                "primary_metric",
                "required_comparison",
                "claim_state",
                "supporting_table",
                "supporting_figure",
                "valid_scope",
                "forbidden_extrapolation",
            ),
            rows,
        ),
    )


def _decision_kind_label(kind: CollapseDecisionKind) -> TextValue:
    return kind.value


def render_collapse_decisions_table(
    decisions: tuple[CollapseDecision, ...],
    resolved_core: ResolvedCore,
) -> RenderedTable:
    decision_rows = tuple(
        (
            _decision_kind_label(decision.kind),
            decision.primary_material_effect or "NA",
            format_p_value(decision.adjusted_p_value),
            "pass" if decision.constraint_passes else "fail",
            "mechanical",
            "survives" if decision.survives else "removed",
            "survives" if decision.survives else "removed",
            "NA",
            "NA",
        )
        for decision in decisions
    )
    source_influence = (
        "source-excluded" if resolved_core.direct_source_exclusion_survives else "source-influenced"
    )
    production_update_rule: ProductionUpdateRule = resolved_core.production_update_rule
    row_verification_mode: RowVerificationMode = resolved_core.row_verification_mode
    reproduction_row_requirement: ReproductionRowRequirement = (
        resolved_core.reproduction_row_requirement
    )
    resolved_row = (
        "resolved core",
        resolved_core.decision_identity,
        "NA",
        source_influence,
        "mapping",
        "NA",
        production_update_rule.value,
        row_verification_mode.value,
        reproduction_row_requirement.value,
    )
    return RenderedTable(
        name="Collapse Decisions",
        csv_text=_csv_text(
            (
                "mechanism",
                "primary_material_effect",
                "adjusted_p",
                "liveness_safety_constraint",
                "survival_rule",
                "observed_outcome",
                "core_action",
                "row_verification_mode",
                "reproduction_row_requirement",
            ),
            (*decision_rows, resolved_row),
        ),
    )


def _comparison_value(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    experiment: ExperimentName,
    method: MethodName,
    scenario: ScenarioName,
    metric: ComparisonMetric,
) -> FormattedStatisticText:
    for family in comparison_results:
        for comparison in family.comparisons:
            definition = comparison.definition
            if (
                definition.experiment == experiment
                and definition.method == method
                and definition.scientific_scenario == scenario
                and definition.metric is metric
            ):
                return format_metric_value(comparison.mean_paired_difference)
    return "NA"


def render_dataset_and_domain_protocol_table() -> RenderedTable:
    config = current_application_context().scientific_config
    primary = config.datasets.primary
    secondary = config.datasets.secondary
    minima = config.capability_claim.evidence_minima
    rows = (
        (
            primary.name.value,
            f"UCI {primary.uci_dataset_id}; DOI {primary.doi}",
            "NA",
            "NA",
            str(NBAIOT_PRIMARY_PREDICTOR_COUNT),
            str(len(NBAIOT_CLASS_ORDER)),
            primary.target_class,
            str(len(NBAIOT_DOMAIN_ORDER)),
            "physical device proxy",
            str(primary.minimum_target_holding_domains),
            (
                f"reproduction>={minima.reproduction_target_examples};"
                f"final-gate>={config.protocol.final_gate.minimum_adequate_non_source_domains}"
            ),
            "role-interval split with guard gaps",
            "primary",
        ),
        (
            secondary.name.value,
            "CICIoT2023 CSV",
            "NA",
            "NA",
            str(OFFICIAL_EXPECTED_PREDICTOR_COUNT),
            "NA",
            secondary.target_class,
            str(PSEUDO_DOMAIN_COUNT),
            "synthetic hash partition",
            "NA",
            f"target={TARGET_LABEL}",
            "group-local role intervals",
            "secondary",
        ),
    )
    return RenderedTable(
        name="Dataset and Domain Protocol",
        csv_text=_csv_text(
            (
                "dataset",
                "source_identifier",
                "file_manifest_hash",
                "raw_rows",
                "retained_feature_count",
                "canonical_class_count",
                "target_class",
                "domain_proxy_count",
                "proxy_semantics",
                "target_holders",
                "evidence_minimum_rule",
                "split_replay_semantics",
                "primary_secondary_role",
            ),
            rows,
        ),
    )


def render_primary_domain_statistics_table() -> RenderedTable:
    rows = tuple(
        (
            domain.value,
            domain.value,
            "NA",
            "NA",
            "NA",
            "NA",
            "NA",
            "NA",
            "NA",
        )
        for domain in NBAIOT_DOMAIN_ORDER
    )
    return RenderedTable(
        name="Primary Domain Statistics",
        csv_text=_csv_text(
            (
                "domain_id",
                "device_type",
                "target_availability",
                "role_target_counts",
                "supported_role_counts",
                "reproduction_eligibility",
                "verifier_eligibility",
                "final_gate_eligibility",
                "report_test_rows",
            ),
            rows,
        ),
    )


def render_model_and_training_protocol_table() -> RenderedTable:
    config = current_application_context().scientific_config
    model = config.model
    rows = (
        (
            "anchor",
            "MLP",
            "Xavier",
            "cross-entropy",
            "AdamW",
            str(model.optimizer.anchor_and_standard_fl_learning_rate),
            str(model.training.batch_size),
            str(model.anchor_fedavg.rounds),
            "none",
            "Anchor Train / Anchor Validation",
            str(model.anchor_fedavg.checkpoint_cadence_rounds),
            str(model.training.gradient_global_l2_clip),
        ),
        (
            "source candidate",
            "MLP",
            "Xavier from anchor",
            "CE+KL+delta-L2",
            "AdamW",
            str(model.optimizer.post_reference_learning_rate),
            str(model.training.batch_size),
            str(model.post_reference.local_epochs),
            (
                f"KL={model.post_reference.stability_weight};"
                f"L2={model.post_reference.delta_l2_weight}"
            ),
            "Source Proposal / Post-Reference Replay",
            "final local epoch",
            str(model.training.gradient_global_l2_clip),
        ),
        (
            "honest reproduction",
            "MLP",
            "Xavier from anchor",
            "CE+KL+delta-L2",
            "AdamW",
            str(model.optimizer.post_reference_learning_rate),
            str(model.training.batch_size),
            str(model.post_reference.local_epochs),
            (
                f"KL={model.post_reference.stability_weight};"
                f"L2={model.post_reference.delta_l2_weight}"
            ),
            "Reproduction / Post-Reference Replay",
            "final local epoch",
            str(model.training.gradient_global_l2_clip),
        ),
    )
    return RenderedTable(
        name="Model and Training Protocol",
        csv_text=_csv_text(
            (
                "stage",
                "architecture",
                "initialization",
                "loss",
                "optimizer",
                "learning_rate",
                "batch_size",
                "epochs_or_rounds",
                "regularizers",
                "data_roles",
                "checkpoint_rule",
                "gradient_clip",
            ),
            rows,
        ),
    )


def render_security_and_capability_contract_protocol_table() -> RenderedTable:
    config = current_application_context().scientific_config
    protocol = config.protocol
    claim = config.capability_claim
    diagnostic = protocol.diagnostic_random_verifier_profile
    rows = (
        (
            "deterministic verifier profile",
            str(protocol.synthesis.maximum_byzantine_reproduction_rows),
            str(protocol.verification.maximum_byzantine_verifiers_per_panel),
            str(protocol.verification.panel_size),
            str(protocol.verification.required_positive_reports),
            str(protocol.synthesis.committee_size),
            str(protocol.synthesis.committee_size),
            str(
                protocol.synthesis.committee_size
                - protocol.synthesis.maximum_byzantine_reproduction_rows
                - 2
            ),
            str(claim.target_f1_minimum),
            str(claim.supported_macro_f1_drop_maximum),
            str(claim.benign_false_alarm_rate_increase_maximum),
            str(claim.evidence_minima.verification_target_examples),
            "ordinary 2-of-3",
        ),
        (
            "random diagnostic verifier profile",
            str(protocol.synthesis.maximum_byzantine_reproduction_rows),
            str(diagnostic.byzantine_domain_count),
            str(diagnostic.panel_size),
            str(diagnostic.required_positive_reports),
            "NA",
            "NA",
            "NA",
            str(claim.target_f1_minimum),
            str(claim.supported_macro_f1_drop_maximum),
            str(claim.benign_false_alarm_rate_increase_maximum),
            str(claim.evidence_minima.verification_target_examples),
            f"contamination<{diagnostic.tolerated_contamination_risk}",
        ),
        (
            "Krum synthesis",
            str(protocol.synthesis.maximum_byzantine_reproduction_rows),
            "NA",
            str(protocol.synthesis.committee_size),
            "NA",
            str(protocol.synthesis.committee_size),
            str(protocol.synthesis.committee_size),
            str(
                protocol.synthesis.committee_size
                - protocol.synthesis.maximum_byzantine_reproduction_rows
                - 2
            ),
            "NA",
            "NA",
            "NA",
            "NA",
            "source-excluded",
        ),
        (
            "final gate",
            "NA",
            "NA",
            "NA",
            "NA",
            "NA",
            "NA",
            "NA",
            str(protocol.final_gate.median_target_f1_minimum),
            str(protocol.final_gate.supported_macro_f1_drop_maximum),
            str(protocol.final_gate.benign_false_alarm_rate_increase_maximum),
            str(protocol.final_gate.minimum_adequate_non_source_domains),
            "fresh domains",
        ),
    )
    return RenderedTable(
        name="Security and Capability-Contract Protocol",
        csv_text=_csv_text(
            (
                "profile",
                "f_R",
                "f_V",
                "panel_size",
                "positive_threshold",
                "certified_row_requirement",
                "krum_n",
                "krum_nearest_neighbor_count",
                "target_threshold",
                "supported_f1_margin",
                "benign_fpr_margin",
                "evidence_minimum",
                "scope",
            ),
            rows,
        ),
    )


def _baseline_validation_fixture(
    identity: BaselineIdentity,
) -> BaselineValidationFixture | None:
    for registered, fixture in BASELINE_VALIDATION_FIXTURE_MAP:
        if registered is identity:
            return fixture
    return None


def render_baseline_protocol_table() -> RenderedTable:
    config = current_application_context().scientific_config
    rows_list: list[tuple[TextValue, ...]] = []
    for identity in BaselineIdentity:
        fixture = _baseline_validation_fixture(identity)
        if fixture is None:
            continue
        independent_retrain = (
            "1"
            if "Retrain" in identity.value or identity is BaselineIdentity.ONE_INDEPENDENT_RETRAIN
            else "0"
        )
        rows_list.append(
            (
                identity.value,
                identity.value,
                "no"
                if fixture is BaselineValidationFixture.LEGITIMATE_TARGET_CAPABILITY
                else "yes",
                independent_retrain,
                "yes" if "Krum" in identity.value else "no",
                identity.value,
                str(config.model.post_reference.local_epochs),
                "never report-test or final-gate",
                "production checkpoint",
                "registered",
            )
        )
    rows = tuple(rows_list)
    return RenderedTable(
        name="Baseline Protocol",
        csv_text=_csv_text(
            (
                "method",
                "mechanism_family",
                "source_artifact_deployed",
                "independent_retraining_count",
                "external_verification",
                "aggregation_synthesis",
                "training_budget",
                "tuning_data",
                "production_object",
                "implementation_status",
            ),
            rows,
        ),
    )


def render_metric_and_statistics_protocol_table() -> RenderedTable:
    config = current_application_context().scientific_config
    multiplicity = config.metrics_and_statistics.multiplicity
    bootstrap = config.metrics_and_statistics.bootstrap
    rows = tuple(
        (
            definition.metric.value,
            definition.orientation.value,
            "seed after domain aggregation",
            "NA plus reason",
            definition.family.value,
            "NA" if definition.material_threshold is None else str(definition.material_threshold),
            definition.test_kind.value,
            definition.test_kind.value,
            str(multiplicity.family_wise_alpha),
            definition.family.value,
            f"percentile-{bootstrap.confidence_level}",
        )
        for definition in build_comparison_registry()
    )
    unique: list[tuple[TextValue, ...]] = []
    for row in rows:
        if row in unique:
            continue
        unique.append(row)
    return RenderedTable(
        name="Metric and Statistics Protocol",
        csv_text=_csv_text(
            (
                "metric",
                "mathematical_orientation",
                "aggregation_unit",
                "undefined_rule",
                "primary_secondary_role",
                "effect_threshold",
                "test",
                "sidedness",
                "alpha",
                "multiplicity_family",
                "ci_method",
            ),
            tuple(unique),
        ),
    )


def render_primary_results_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
) -> RenderedTable:
    methods_scenarios: list[tuple[MethodName, ScenarioName]] = []
    seen: set[tuple[MethodName, ScenarioName]] = set()
    for family in comparison_results:
        for comparison in family.comparisons:
            definition = comparison.definition
            if definition.experiment != PRIMARY_CONFIRMATORY_EVALUATION_NAME:
                continue
            key = (definition.method, definition.scientific_scenario)
            if key in seen:
                continue
            seen.add(key)
            methods_scenarios.append(key)
    rows = tuple(
        (
            method,
            scenario,
            _comparison_value(
                comparison_results,
                PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                method,
                scenario,
                ComparisonMetric.TARGET_F1,
            ),
            "NA",
            _comparison_value(
                comparison_results,
                PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                method,
                scenario,
                ComparisonMetric.SUPPORTED_MACRO_F1_HARM,
            ),
            _comparison_value(
                comparison_results,
                PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                method,
                scenario,
                ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE,
            ),
            _comparison_value(
                comparison_results,
                PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                method,
                scenario,
                ComparisonMetric.ATTACK_SUCCESS_RATE,
            ),
            _comparison_value(
                comparison_results,
                PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                method,
                scenario,
                ComparisonMetric.MALICIOUS_ADMISSION,
            ),
            _comparison_value(
                comparison_results,
                PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                method,
                scenario,
                ComparisonMetric.LEGITIMATE_ADMISSION,
            ),
            _comparison_value(
                comparison_results,
                PRIMARY_CONFIRMATORY_EVALUATION_NAME,
                method,
                scenario,
                ComparisonMetric.WORST_DOMAIN_TARGET_F1,
            ),
            "NA",
        )
        for method, scenario in methods_scenarios
    )
    return RenderedTable(
        name="Primary Results",
        csv_text=_csv_text(
            (
                "method",
                "scenario",
                "target_f1_mean",
                "target_f1_95_ci",
                "supported_macro_f1_harm",
                "benign_false_alarm_rate_increase",
                ComparisonMetric.ATTACK_SUCCESS_RATE.value,
                "malicious_admission",
                "legitimate_admission",
                "worst_domain_target_f1",
                "complete_seed_count",
            ),
            rows,
        ),
    )


def render_source_exclusion_results_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
) -> RenderedTable:
    methods: list[MethodName] = []
    seen: set[MethodName] = set()
    for family in comparison_results:
        for comparison in family.comparisons:
            definition = comparison.definition
            if definition.experiment != SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME:
                continue
            if definition.method in seen:
                continue
            seen.add(definition.method)
            methods.append(definition.method)
    rows = tuple(
        (
            method,
            _comparison_value(
                comparison_results,
                SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
                method,
                PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,
                ComparisonMetric.ATTACK_SUCCESS_RATE,
            ),
            "NA",
            "NA",
            "NA",
            _comparison_value(
                comparison_results,
                SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
                method,
                PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,
                ComparisonMetric.TARGET_F1,
            ),
            "NA",
            _comparison_value(
                comparison_results,
                SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
                method,
                PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,
                ComparisonMetric.SUPPORTED_MACRO_F1_HARM,
            ),
            _comparison_value(
                comparison_results,
                SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
                method,
                PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,
                ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE,
            ),
            "NA",
        )
        for method in methods
    )
    return RenderedTable(
        name="Source-Exclusion Results",
        csv_text=_csv_text(
            (
                "method",
                "post_production_asr",
                "asr_difference_vs_fedsira",
                "adjusted_p",
                "confidence_interval_95",
                "target_f1",
                "target_noninferiority_pass",
                "supported_f1_harm",
                "benign_fpr_increase",
                "source_exclusion_gate_outcome",
            ),
            rows,
        ),
    )


def render_ablation_results_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
) -> RenderedTable:
    rows = tuple(
        (
            variant.value,
            variant.value,
            "NA",
            ComparisonMetric.LEGITIMATE_ADMISSION.value,
            _comparison_value(
                comparison_results,
                MECHANISM_ABLATION_NAME,
                variant.value,
                "NA",
                ComparisonMetric.LEGITIMATE_ADMISSION,
            ),
            "NA",
            "NA",
            "NA",
            "NA",
            "NA",
            "mechanical",
        )
        for variant in AblationVariant
    )
    return RenderedTable(
        name="Ablation Results",
        csv_text=_csv_text(
            (
                "variant",
                "targeted_mechanism",
                "scenario",
                "primary_metric",
                "difference_from_full_reference",
                "adjusted_p",
                "materiality_pass",
                "target_f1",
                "supported_harm",
                "asr_or_malicious_admission",
                "interpretation",
            ),
            rows,
        ),
    )


def render_byzantine_robustness_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
) -> RenderedTable:
    rows = tuple(
        (
            family.family.value,
            comparison.definition.method,
            comparison.definition.scientific_scenario,
            "Within Bound",
            "NA",
            comparison.definition.method,
            format_metric_value(comparison.mean_paired_difference)
            if comparison.definition.metric is ComparisonMetric.MALICIOUS_ADMISSION
            else "NA",
            format_metric_value(comparison.mean_paired_difference)
            if comparison.definition.metric is ComparisonMetric.LEGITIMATE_ADMISSION
            else "NA",
            format_metric_value(comparison.mean_paired_difference)
            if comparison.definition.metric is ComparisonMetric.ATTACK_SUCCESS_RATE
            else "NA",
            format_metric_value(comparison.mean_paired_difference)
            if comparison.definition.metric is ComparisonMetric.TARGET_F1
            else "NA",
            "NA",
            "NA",
            str(comparison.complete_seed_count),
        )
        for family in comparison_results
        for comparison in family.comparisons
        if comparison.definition.experiment
        in (
            COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
            COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
            BYZANTINE_BOUND_VIOLATION_NAME,
        )
    )
    return RenderedTable(
        name="Byzantine Robustness",
        csv_text=_csv_text(
            (
                "bound_family",
                "method",
                "condition",
                "bound_status",
                "compromised_count",
                "strategy",
                "malicious_admission",
                "legitimate_admission",
                ComparisonMetric.ATTACK_SUCCESS_RATE.value,
                "target_f1",
                "certified_yield",
                "dormant_rate",
                "complete_seeds",
            ),
            rows,
        ),
    )


def render_failure_boundaries_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
) -> RenderedTable:
    rows = tuple(
        (
            comparison.definition.experiment,
            comparison.definition.scientific_scenario,
            "NA",
            format_metric_value(comparison.mean_paired_difference)
            if comparison.definition.metric is ComparisonMetric.LEGITIMATE_ADMISSION
            else "NA",
            format_metric_value(comparison.mean_paired_difference)
            if comparison.definition.metric is ComparisonMetric.TARGET_F1
            else "NA",
            format_metric_value(comparison.mean_paired_difference)
            if comparison.definition.metric is ComparisonMetric.WORST_DOMAIN_TARGET_F1
            else "NA",
            (
                "NA"
                if comparison.definition.experiment != SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME
                else format_metric_value(comparison.mean_paired_difference)
            ),
            (
                "Not an Epistemic-Oracle Experiment"
                if comparison.definition.experiment != SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME
                else "epistemic oracle"
            ),
        )
        for family in comparison_results
        for comparison in family.comparisons
        if comparison.definition.experiment
        in (
            EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
            SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
            CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
            HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
        )
    )
    return RenderedTable(
        name="Failure Boundaries",
        csv_text=_csv_text(
            (
                "boundary_family",
                "condition",
                "strength",
                "admission_dormancy",
                "target_f1",
                "worst_domain_f1",
                "clean_oracle_error",
                "claim_implication",
            ),
            rows,
        ),
    )


def render_delay_and_efficiency_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
) -> RenderedTable:
    rows = tuple(
        (
            comparison.definition.method,
            comparison.definition.scientific_scenario,
            "NA",
            "NA",
            "NA",
            "NA",
            "NA",
            format_metric_value(comparison.mean_paired_difference)
            if comparison.definition.metric is ComparisonMetric.POST_EVIDENCE_OVERHEAD
            else "NA",
            "NA",
            "NA",
            "NA",
            "NA",
            "NA",
            "NA",
            "NA",
        )
        for family in comparison_results
        for comparison in family.comparisons
        if comparison.definition.experiment
        in (ADMISSION_DELAY_DECOMPOSITION_NAME, EFFICIENCY_MEASUREMENT_NAME)
    )
    return RenderedTable(
        name="Delay and Efficiency",
        csv_text=_csv_text(
            (
                "method",
                "schedule",
                "t_evidence",
                "assignment_seconds",
                "reproduction_seconds",
                "verification_seconds",
                "synthesis_seconds",
                "post_evidence_overhead",
                "wall_clock_runtime",
                "gpu_time",
                "peak_gpu_memory",
                "host_rss",
                "communication_bytes",
                "transmissions",
                "storage",
            ),
            rows,
        ),
    )


def render_generalization_results_table(
    comparison_results: tuple[ComparisonFamilyResult, ...],
) -> RenderedTable:
    rows = tuple(
        (
            comparison.definition.method,
            comparison.definition.scientific_scenario,
            format_metric_value(comparison.mean_paired_difference)
            if comparison.definition.metric is ComparisonMetric.TARGET_F1
            else "NA",
            format_metric_value(comparison.mean_paired_difference)
            if comparison.definition.metric is ComparisonMetric.SUPPORTED_MACRO_F1_HARM
            else "NA",
            format_metric_value(comparison.mean_paired_difference)
            if comparison.definition.metric is ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE
            else "NA",
            format_metric_value(comparison.mean_paired_difference)
            if comparison.definition.metric is ComparisonMetric.MALICIOUS_ADMISSION
            else "NA",
            format_metric_value(comparison.mean_paired_difference)
            if comparison.definition.metric is ComparisonMetric.LEGITIMATE_ADMISSION
            else "NA",
            format_metric_value(comparison.mean_paired_difference),
            format_p_value(comparison.adjusted_p_value),
            "pass" if comparison.materiality_passes is not False else "fail",
            "Data/Attack Generalization Only",
        )
        for family in comparison_results
        for comparison in family.comparisons
        if comparison.definition.experiment == SECONDARY_DATASET_GENERALIZATION_NAME
    )
    return RenderedTable(
        name="Generalization Results",
        csv_text=_csv_text(
            (
                "method",
                "scenario",
                "target_f1_or_gain",
                "supported_harm",
                "benign_false_alarm_rate_increase",
                "malicious_admission",
                "legitimate_admission",
                "paired_effect_vs_fedsira",
                "adjusted_p",
                "materiality_pass",
                "claim_label",
            ),
            rows,
        ),
    )


def render_mandatory_tables(
    plan: ExperimentPlan,
    claim_states: tuple[ClaimStateResult, ...],
    collapse_decisions: tuple[CollapseDecision, ...] | None = None,
    resolved_core: ResolvedCore | None = None,
    comparison_results: tuple[ComparisonFamilyResult, ...] = (),
) -> tuple[RenderedTable, ...]:
    tables = [
        render_dataset_and_domain_protocol_table(),
        render_primary_domain_statistics_table(),
        render_model_and_training_protocol_table(),
        render_security_and_capability_contract_protocol_table(),
        render_baseline_protocol_table(),
        render_experiment_plan_table(plan),
        render_metric_and_statistics_protocol_table(),
        render_primary_results_table(comparison_results),
        render_source_exclusion_results_table(comparison_results),
    ]
    if collapse_decisions is not None and resolved_core is not None:
        tables.append(render_collapse_decisions_table(collapse_decisions, resolved_core))
    else:
        tables.append(
            RenderedTable(
                name="Collapse Decisions",
                csv_text=_csv_text(
                    (
                        "mechanism",
                        "primary_material_effect",
                        "adjusted_p",
                        "liveness_safety_constraint",
                        "survival_rule",
                        "observed_outcome",
                        "core_action",
                        "row_verification_mode",
                        "reproduction_row_requirement",
                    ),
                    (),
                ),
            )
        )
    tables.extend(
        (
            render_ablation_results_table(comparison_results),
            render_byzantine_robustness_table(comparison_results),
            render_failure_boundaries_table(comparison_results),
            render_delay_and_efficiency_table(comparison_results),
            render_generalization_results_table(comparison_results),
            render_statistical_summary_table(comparison_results),
            render_claim_support_table(claim_states),
        )
    )
    return tuple(tables)
