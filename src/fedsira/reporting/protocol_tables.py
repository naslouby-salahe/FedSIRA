from __future__ import annotations

from fedsira.artifacts.paths import prepared_evidence_root
from fedsira.datasets.specification import (
    PreparedDomainSummary,
    dataset_specification,
    prepared_domain_summaries,
    prepared_view_digest,
)
from fedsira.domain.enums import DatasetId, Role
from fedsira.domain.types import (
    DatasetClassToken,
    DomainId,
    ExperimentName,
    RowCount,
    TextValue,
)
from fedsira.evaluation.comparisons import (
    ComparisonDefinition,
    build_comparison_registry,
)
from fedsira.experiments.definitions import (
    ExperimentClass,
    ExperimentDefinition,
    TrainingProtocolStage,
    experiment_by_name,
)
from fedsira.experiments.planning import ExperimentPlan
from fedsira.protocol.baselines.registry import BASELINE_CONTRACTS
from fedsira.reporting.rendering import RenderedTable
from fedsira.reporting.rendering import csv_text as _csv_text
from fedsira.runtime import REPOSITORY_ROOT, current_application_context


def _experiment_class_label(experiment_class: ExperimentClass) -> TextValue:
    return experiment_class.value


def _downstream_role(
    experiment: ExperimentName,
    definitions: tuple[ExperimentDefinition, ...],
) -> TextValue:
    dependents = tuple(
        definition.name for definition in definitions if experiment in definition.prerequisites
    )
    if not dependents:
        return "terminal evidence product"
    return ";".join(dependents)


def render_experiment_plan_table(plan: ExperimentPlan) -> RenderedTable:
    definitions = tuple(planned.definition for planned in plan.experiments)
    rows = tuple(
        (
            planned.definition.name,
            _experiment_class_label(planned.definition.experiment_class),
            ";".join(planned.definition.methods),
            ";".join(planned.definition.conditions),
            ";".join(
                str(seed) for seed in sorted(frozenset(cell.master_seed for cell in planned.cells))
            ),
            str(len(planned.cells)),
            ";".join(metric.value for metric in planned.definition.primary_metrics),
            (
                planned.definition.comparison_family.value
                if planned.definition.comparison_family is not None
                else "none (descriptive evidence)"
            ),
            ";".join(planned.definition.prerequisites) or "none",
            _downstream_role(planned.definition.name, definitions),
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
                "scenarios_or_variants",
                "seeds",
                "nominal_run_count",
                "primary_metrics",
                "claim_family",
                "prerequisite",
                "downstream_role",
            ),
            rows,
        ),
    )


def render_dataset_and_domain_protocol_table() -> RenderedTable:
    config = current_application_context().scientific_config
    primary = config.datasets.primary
    secondary = config.datasets.secondary
    primary_specification = dataset_specification(DatasetId.N_BAIOT)
    secondary_specification = dataset_specification(DatasetId.CICIOT2023)
    primary_root = REPOSITORY_ROOT / prepared_evidence_root(DatasetId.N_BAIOT)
    secondary_root = REPOSITORY_ROOT / prepared_evidence_root(DatasetId.CICIOT2023)
    primary_summaries = prepared_domain_summaries(DatasetId.N_BAIOT, primary_root)
    secondary_summaries = prepared_domain_summaries(DatasetId.CICIOT2023, secondary_root)
    primary_classes = frozenset(primary_specification.class_tokens) | frozenset(
        class_token
        for summary in primary_summaries
        for _role, class_token, _count in summary.counts
    )
    secondary_classes = frozenset(secondary_specification.class_tokens) | frozenset(
        class_token
        for summary in secondary_summaries
        for _role, class_token, _count in summary.counts
    )
    minima = config.capability_contract.evidence_minima
    evidence_minimum_rule = (
        f"reproduction>={minima.reproduction_target_examples};"
        f"verification>={minima.verification_target_examples};"
        f"final-gate>={config.protocol.final_gate.minimum_adequate_non_source_domains} domains"
    )
    rows = (
        (
            primary.name.value,
            f"UCI {primary.uci_dataset_id}; DOI {primary.doi}",
            prepared_view_digest(primary_root),
            str(
                sum(
                    count
                    for summary in primary_summaries
                    for _role, _class, count in summary.counts
                )
            ),
            str(primary_specification.expected_predictor_count),
            str(len(primary_classes)),
            primary.target_class,
            str(len(primary_specification.domain_ids)),
            primary_specification.domain_proxy_semantics,
            str(
                sum(
                    1
                    for summary in primary_summaries
                    if domain_target_count(summary, primary.target_class) > 0
                )
            ),
            evidence_minimum_rule,
            "role-interval split with guard gaps",
            "primary",
        ),
        (
            secondary.name.value,
            f"{secondary.name.value} ({secondary_specification.raw_data_relative})",
            prepared_view_digest(secondary_root),
            str(
                sum(
                    count
                    for summary in secondary_summaries
                    for _role, _class, count in summary.counts
                )
            ),
            str(secondary_specification.expected_predictor_count),
            str(len(secondary_classes)),
            secondary.target_class,
            str(len(secondary_specification.domain_ids)),
            secondary_specification.domain_proxy_semantics,
            str(
                sum(
                    1
                    for summary in secondary_summaries
                    if domain_target_count(summary, secondary.target_class) > 0
                )
            ),
            evidence_minimum_rule,
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
                "prepared_view_digest",
                "materialized_rows",
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
    config = current_application_context().scientific_config
    primary_specification = dataset_specification(DatasetId.N_BAIOT)
    summaries = prepared_domain_summaries(
        DatasetId.N_BAIOT,
        REPOSITORY_ROOT / prepared_evidence_root(DatasetId.N_BAIOT),
    )
    missing_domains = tuple(
        domain
        for domain in primary_specification.domain_ids
        if not any(summary.domain_id == domain for summary in summaries)
    )
    if missing_domains:
        raise ValueError(
            "prepared primary-domain evidence is incomplete: " + ", ".join(missing_domains)
        )
    target = config.datasets.primary.target_class
    supported_exclusions = frozenset((target, primary_specification.benign_class))
    rows = tuple(
        (
            domain,
            domain,
            "available"
            if domain_target_count(summary_for_domain(summaries, domain), target) > 0
            else "unavailable",
            role_counts(summary_for_domain(summaries, domain), target),
            supported_role_counts(summary_for_domain(summaries, domain), supported_exclusions),
            eligibility_text(
                summary_for_domain(summaries, domain).count(Role.REPRODUCTION.value, target),
                config.datasets.primary.sampling_caps_per_domain.reproduction_target,
            ),
            eligibility_text(
                summary_for_domain(summaries, domain).count(Role.ROW_VERIFICATION.value, target),
                config.datasets.primary.sampling_caps_per_domain.row_verification_target,
            ),
            eligibility_text(
                summary_for_domain(summaries, domain).count(Role.FINAL_GATE.value, target),
                config.datasets.primary.sampling_caps_per_domain.final_gate_target,
            ),
            str(summary_for_domain(summaries, domain).count_for_role(Role.REPORT_TEST.value)),
        )
        for domain in primary_specification.domain_ids
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
            TrainingProtocolStage.ANCHOR.value,
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
            TrainingProtocolStage.SOURCE_CANDIDATE.value,
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
            TrainingProtocolStage.HONEST_REPRODUCTION.value,
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
    contract = config.capability_contract
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
            str(contract.target_f1_minimum),
            str(contract.supported_macro_f1_drop_maximum),
            str(contract.benign_false_alarm_rate_increase_maximum),
            str(contract.evidence_minima.verification_target_examples),
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
            str(contract.target_f1_minimum),
            str(contract.supported_macro_f1_drop_maximum),
            str(contract.benign_false_alarm_rate_increase_maximum),
            str(contract.evidence_minima.verification_target_examples),
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


BASELINE_TUNING_DATA_RULE: TextValue = (
    "anchor-train/anchor-validation only; report-test, row-verification and "
    "final-gate rows are never used for tuning"
)


def render_baseline_protocol_table() -> RenderedTable:
    rows = tuple(
        (
            contract.identity.value,
            contract.mechanism_family.value,
            "yes" if contract.source_artifact_deployed else "no",
            str(contract.independent_retraining_count),
            contract.external_verification.value,
            contract.aggregation_synthesis.value,
            contract.training_budget.value,
            BASELINE_TUNING_DATA_RULE,
            contract.production_object.value,
            contract.implementation_status.value,
        )
        for contract in BASELINE_CONTRACTS
    )
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


def _metric_primary_role(definition: ComparisonDefinition) -> TextValue:
    experiment = experiment_by_name(definition.experiment)
    for metric in experiment.primary_metrics:
        if metric is definition.metric:
            return "primary"
    return "secondary"


def _metric_effect_threshold(definition: ComparisonDefinition) -> TextValue:
    thresholds: list[TextValue] = []
    if definition.material_threshold is not None:
        thresholds.append(f"material {definition.material_threshold:.3f}")
    if definition.margin is not None:
        thresholds.append(f"non-inferiority margin {definition.margin:.3f}")
    if not thresholds:
        return "none"
    return "; ".join(thresholds)


def render_metric_and_statistics_protocol_table() -> RenderedTable:
    config = current_application_context().scientific_config
    multiplicity = config.metrics_and_statistics.multiplicity
    bootstrap = config.metrics_and_statistics.bootstrap
    rows = tuple(
        (
            definition.metric.value,
            definition.orientation.value,
            "master-seed instance after equal-weight domain aggregation",
            "zero denominator or structurally inapplicable metric is NA with reason",
            _metric_primary_role(definition),
            _metric_effect_threshold(definition),
            definition.test_kind.value,
            definition.sidedness.value,
            f"{multiplicity.family_wise_alpha:.3f}",
            definition.family.value,
            (
                f"{bootstrap.confidence_level:.3f} percentile bootstrap, "
                f"{bootstrap.resamples} resamples, analysis seed "
                f"{config.seeds_and_determinism.analysis_seed}, type-7 endpoints"
            ),
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


def domain_target_count(summary: PreparedDomainSummary, target: DatasetClassToken) -> RowCount:
    return sum(
        summary.count(role.value, target)
        for role in (
            Role.SOURCE_PROPOSAL,
            Role.CANDIDATE_SCREEN,
            Role.REPRODUCTION,
            Role.ROW_VERIFICATION,
            Role.FINAL_GATE,
            Role.REPORT_TEST,
        )
    )


def summary_for_domain(
    summaries: tuple[PreparedDomainSummary, ...], domain: DomainId
) -> PreparedDomainSummary:
    for summary in summaries:
        if summary.domain_id == domain:
            return summary
    raise ValueError(f"no summary for {domain}")


def role_counts(summary: PreparedDomainSummary, target: DatasetClassToken) -> TextValue:
    return ";".join(
        f"{role.value}={summary.count(role.value, target)}"
        for role in (Role.REPRODUCTION, Role.ROW_VERIFICATION, Role.FINAL_GATE, Role.REPORT_TEST)
    )


def supported_role_counts(
    summary: PreparedDomainSummary, excluded_classes: frozenset[DatasetClassToken]
) -> TextValue:
    return ";".join(
        f"{role.value}={summary.count_for_role(role.value, excluded_classes)}"
        for role in (
            Role.POST_REFERENCE_REPLAY,
            Role.ROW_VERIFICATION,
            Role.FINAL_GATE,
            Role.REPORT_TEST,
        )
    )


def eligibility_text(observed: RowCount, required: RowCount) -> TextValue:
    return f"{'eligible' if observed >= required else 'insufficient'} ({observed}/{required})"
