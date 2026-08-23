from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from fedsira.domain.enums import ExperimentLifecycleState
from fedsira.domain.records import CanonicalToken, MasterSeed, PositiveInt
from fedsira.experiments.collapse import CollapseDecisionKind
from fedsira.experiments.registry import (
    COLLAPSE_EXPERIMENT_NAMES,
    EXPERIMENT_REGISTRY,
    POST_CORE_EXPERIMENT_NAMES,
    ExperimentClass,
    ExperimentDefinition,
)


def collapse_decision_kind_for_experiment(
    experiment: CanonicalToken,
) -> CollapseDecisionKind | None:
    return {
        "Proposal-Assisted Opening Necessity": CollapseDecisionKind.PROPOSAL_ASSISTANCE,
        "Single-Reproduction Necessity": CollapseDecisionKind.PLURALITY,
        "Source-Artifact Exclusion Necessity": CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION,
        "External Verification Necessity": CollapseDecisionKind.EXTERNAL_VERIFICATION,
    }.get(experiment)


@dataclass(frozen=True)
class ScientificCell:
    experiment: CanonicalToken
    method: CanonicalToken
    condition: CanonicalToken
    master_seed: MasterSeed

    @property
    def semantic_key(self) -> CanonicalToken:
        return "|".join((self.experiment, self.method, self.condition, str(self.master_seed)))


PRE_CORE_EXPERIMENT_NAMES: frozenset[CanonicalToken] = frozenset(
    {
        "Data and Domain Evidence Validation",
        "Protocol Invariant Validation",
        "Baseline Implementation Validation",
        *COLLAPSE_EXPERIMENT_NAMES,
    }
)


@dataclass(frozen=True)
class PlannedExperiment:
    definition: ExperimentDefinition
    cells: tuple[ScientificCell, ...]
    prerequisites: tuple[CanonicalToken, ...]
    lifecycle_state: ExperimentLifecycleState
    resolved_core_dependent: bool


@dataclass(frozen=True)
class ExperimentPlan:
    experiments: tuple[PlannedExperiment, ...]

    def experiment(self, name: CanonicalToken) -> PlannedExperiment:
        for planned in self.experiments:
            if planned.definition.name == name:
                return planned
        raise KeyError(f"unknown planned experiment {name!r}")

    @property
    def total_cell_count(self) -> PositiveInt:
        return sum(len(planned.cells) for planned in self.experiments)

    @property
    def pre_core_cell_count(self) -> PositiveInt:
        return sum(
            len(planned.cells)
            for planned in self.experiments
            if planned.definition.name in PRE_CORE_EXPERIMENT_NAMES
        )

    @property
    def post_core_cell_count(self) -> PositiveInt:
        return sum(
            len(planned.cells)
            for planned in self.experiments
            if planned.definition.name in POST_CORE_EXPERIMENT_NAMES
        )


def _experiment_seeds(
    definition: ExperimentDefinition,
    master_seeds: tuple[MasterSeed, ...],
    smoke_seed: MasterSeed,
) -> tuple[MasterSeed, ...]:
    if definition.seed_count == 1:
        return (smoke_seed,)
    return master_seeds[: definition.seed_count]


def _planned_experiment(
    definition: ExperimentDefinition,
    master_seeds: tuple[MasterSeed, ...],
    smoke_seed: MasterSeed,
) -> PlannedExperiment:
    seeds = _experiment_seeds(definition, master_seeds, smoke_seed)
    if definition.name == "Baseline Implementation Validation":
        cells = tuple(
            ScientificCell(
                experiment=definition.name,
                method=method,
                condition="Baseline Validation",
                master_seed=smoke_seed,
            )
            for method in definition.methods
        )
    elif definition.name == "Efficiency Measurement":
        cells = tuple(
            ScientificCell(
                experiment=definition.name,
                method=method,
                condition=f"repetition-{repetition_index}",
                master_seed=master_seed,
            )
            for method in definition.methods
            for master_seed in seeds
            for repetition_index in range(1, 6)
        )
    else:
        cells = tuple(
            ScientificCell(
                experiment=definition.name,
                method=method,
                condition=condition,
                master_seed=master_seed,
            )
            for method in definition.methods
            for condition in definition.conditions
            for master_seed in seeds
        )
    resolved_core_dependent = definition.name in POST_CORE_EXPERIMENT_NAMES
    return PlannedExperiment(
        definition=definition,
        cells=cells,
        prerequisites=definition.prerequisites,
        lifecycle_state=ExperimentLifecycleState.NOT_STARTED,
        resolved_core_dependent=resolved_core_dependent,
    )


def build_plan(
    resolved_core_complete: bool = False,
    collapse_decision_states: Sequence[tuple[CanonicalToken, bool]] | None = None,
    master_seeds: tuple[MasterSeed, ...] | None = None,
    smoke_seed: MasterSeed | None = None,
) -> ExperimentPlan:
    decisions = dict(collapse_decision_states or ())
    if master_seeds is None or smoke_seed is None:
        from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config

        config = load_scientific_config(PRODUCTION_CONFIG_PATH)
        master_seeds = master_seeds or config.seeds_and_determinism.master_seeds
        smoke_seed = smoke_seed or config.seeds_and_determinism.smoke_seed
    planned: list[PlannedExperiment] = []
    for definition in EXPERIMENT_REGISTRY:
        if definition.experiment_class not in (
            ExperimentClass.VALIDATION,
            ExperimentClass.EXPLORATORY,
            ExperimentClass.CONFIRMATORY,
            ExperimentClass.ABLATION,
            ExperimentClass.ROBUSTNESS,
            ExperimentClass.FAILURE_BOUNDARY,
            ExperimentClass.DIAGNOSTIC,
            ExperimentClass.GENERALIZATION,
        ):
            raise ValueError(
                f"unknown experiment class {definition.experiment_class} for {definition.name}"
            )
        planned_experiment = _planned_experiment(definition, master_seeds, smoke_seed)
        if planned_experiment.resolved_core_dependent and not resolved_core_complete:
            planned_experiment = PlannedExperiment(
                definition=definition,
                cells=planned_experiment.cells,
                prerequisites=planned_experiment.prerequisites,
                lifecycle_state=ExperimentLifecycleState.BLOCKED,
                resolved_core_dependent=True,
            )
        elif (
            definition.name in COLLAPSE_EXPERIMENT_NAMES
            and collapse_decision_kind_for_experiment(definition.name) is not None
            and definition.name in decisions
            and not decisions[definition.name]
        ):
            planned_experiment = PlannedExperiment(
                definition=definition,
                cells=planned_experiment.cells,
                prerequisites=planned_experiment.prerequisites,
                lifecycle_state=ExperimentLifecycleState.COMPLETED,
                resolved_core_dependent=False,
            )
        planned.append(planned_experiment)
    return ExperimentPlan(experiments=tuple(planned))


def plan_cell_count_by_program_block() -> dict[CanonicalToken, PositiveInt]:
    return {
        "data_and_domain_evidence_validation": 1,
        "protocol_invariant_validation": 1,
        "baseline_implementation_validation": 17,
        "proposal_assisted_opening_necessity": 80,
        "single_reproduction_necessity": 60,
        "source_artifact_exclusion_necessity": 60,
        "external_verification_necessity": 80,
        "pre_core_subtotal": 299,
        "primary_confirmatory_evaluation": 420,
        "mechanism_ablation": 180,
        "compromised_reproducer_robustness": 280,
        "compromised_verifier_robustness": 100,
        "byzantine_bound_violation": 80,
        "evidence_scarcity_and_dormancy": 40,
        "shared_epistemic_failure_boundary": 90,
        "capability_under_specification_boundary": 60,
        "heterogeneous_reproduction_boundary": 160,
        "admission_delay_decomposition": 120,
        "efficiency_measurement": 60,
        "secondary_dataset_generalization": 100,
        "post_core_subtotal": 1690,
        "complete_scientific_plan": 1989,
    }


def validate_planned_cell_count_invariant(plan: ExperimentPlan) -> None:
    nominal_blocks = plan_cell_count_by_program_block()
    observed_pre_core = plan.pre_core_cell_count
    observed_post_core = plan.post_core_cell_count
    for planned in plan.experiments:
        expected_nominal = planned.definition.nominal_cell_count
        observed = len(planned.cells)
        if observed != expected_nominal:
            raise ValueError(
                f"experiment {planned.definition.name} plans {observed} cells but "
                f"its nominal Section 31 count is {expected_nominal}"
            )
    if observed_pre_core != nominal_blocks["pre_core_subtotal"]:
        raise ValueError(
            f"pre-core planned cell count {observed_pre_core} does not match "
            f"the Section 31 contract {nominal_blocks['pre_core_subtotal']}"
        )
    if observed_post_core != nominal_blocks["post_core_subtotal"]:
        raise ValueError(
            f"post-core planned cell count {observed_post_core} does not match "
            f"the Section 31 contract {nominal_blocks['post_core_subtotal']}"
        )
    if plan.total_cell_count != nominal_blocks["complete_scientific_plan"]:
        raise ValueError(
            f"total planned cell count {plan.total_cell_count} does not match "
            f"the Section 31 contract {nominal_blocks['complete_scientific_plan']}"
        )
