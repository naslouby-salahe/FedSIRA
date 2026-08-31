from __future__ import annotations

from fedsira.domain.enums import ExperimentLifecycleState
from fedsira.domain.records import (
    CollapseDecisionPassed,
    ConditionName,
    ExperimentName,
    FrozenDomainModel,
    MasterSeed,
    MethodName,
    NonNegativeInt,
    ResolvedCoreComplete,
    ResolvedCoreDependent,
    ScientificCellCount,
    ScientificCellSemanticKey,
)
from fedsira.experiments.registry import (
    BASELINE_IMPLEMENTATION_VALIDATION_NAME,
    COLLAPSE_EXPERIMENT_NAMES,
    DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    EXPERIMENT_REGISTRY,
    MECHANISM_ABLATION_NAME,
    POST_CORE_EXPERIMENT_NAMES,
    PROTOCOL_INVARIANT_VALIDATION_NAME,
    AblationScenario,
    AblationVariant,
    ExperimentDefinition,
    ablation_scenario_for_variant,
    baseline_validation_fixture_for_method,
)


class ScientificCell(FrozenDomainModel):
    experiment: ExperimentName
    method: MethodName
    condition: ConditionName
    master_seed: MasterSeed

    @property
    def semantic_key(self) -> ScientificCellSemanticKey:
        return "|".join((self.experiment, self.method, self.condition, str(self.master_seed)))


class PlannedExperiment(FrozenDomainModel):
    definition: ExperimentDefinition
    cells: tuple[ScientificCell, ...]
    prerequisites: tuple[ExperimentName, ...]
    lifecycle_state: ExperimentLifecycleState
    resolved_core_dependent: ResolvedCoreDependent


class ExperimentPlan(FrozenDomainModel):
    experiments: tuple[PlannedExperiment, ...]

    def experiment(self, name: ExperimentName) -> PlannedExperiment:
        for planned in self.experiments:
            if planned.definition.name == name:
                return planned
        raise KeyError(f"unknown planned experiment {name!r}")

    @property
    def total_cell_count(self) -> ScientificCellCount:
        return sum(len(planned.cells) for planned in self.experiments)

    @property
    def pre_core_cell_count(self) -> ScientificCellCount:
        return sum(
            len(planned.cells)
            for planned in self.experiments
            if planned.definition.name in PRE_CORE_EXPERIMENT_NAMES
        )

    @property
    def post_core_cell_count(self) -> ScientificCellCount:
        return sum(
            len(planned.cells)
            for planned in self.experiments
            if planned.definition.name in POST_CORE_EXPERIMENT_NAMES
        )


class PlanCellCountContract(FrozenDomainModel):
    data_and_domain_evidence_validation: ScientificCellCount
    protocol_invariant_validation: ScientificCellCount
    baseline_implementation_validation: ScientificCellCount
    proposal_assisted_opening_necessity: ScientificCellCount
    single_reproduction_necessity: ScientificCellCount
    source_artifact_exclusion_necessity: ScientificCellCount
    external_verification_necessity: ScientificCellCount
    pre_core_subtotal: ScientificCellCount
    primary_confirmatory_evaluation: ScientificCellCount
    mechanism_ablation: ScientificCellCount
    compromised_reproducer_robustness: ScientificCellCount
    compromised_verifier_robustness: ScientificCellCount
    byzantine_bound_violation: ScientificCellCount
    evidence_scarcity_and_dormancy: ScientificCellCount
    shared_epistemic_failure_boundary: ScientificCellCount
    capability_under_specification_boundary: ScientificCellCount
    heterogeneous_reproduction_boundary: ScientificCellCount
    admission_delay_decomposition: ScientificCellCount
    efficiency_measurement: ScientificCellCount
    secondary_dataset_generalization: ScientificCellCount
    post_core_subtotal: ScientificCellCount
    complete_scientific_plan: ScientificCellCount


PRE_CORE_EXPERIMENT_NAMES: frozenset[ExperimentName] = frozenset(
    {
        DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,
        PROTOCOL_INVARIANT_VALIDATION_NAME,
        BASELINE_IMPLEMENTATION_VALIDATION_NAME,
        *COLLAPSE_EXPERIMENT_NAMES,
    }
)
EFFICIENCY_REPETITION_INDICES: tuple[NonNegativeInt, ...] = (1, 2, 3, 4, 5)
PLAN_CELL_COUNT_CONTRACT = PlanCellCountContract(
    data_and_domain_evidence_validation=1,
    protocol_invariant_validation=1,
    baseline_implementation_validation=17,
    proposal_assisted_opening_necessity=80,
    single_reproduction_necessity=60,
    source_artifact_exclusion_necessity=60,
    external_verification_necessity=80,
    pre_core_subtotal=299,
    primary_confirmatory_evaluation=420,
    mechanism_ablation=180,
    compromised_reproducer_robustness=280,
    compromised_verifier_robustness=100,
    byzantine_bound_violation=80,
    evidence_scarcity_and_dormancy=40,
    shared_epistemic_failure_boundary=90,
    capability_under_specification_boundary=60,
    heterogeneous_reproduction_boundary=160,
    admission_delay_decomposition=120,
    efficiency_measurement=60,
    secondary_dataset_generalization=100,
    post_core_subtotal=1690,
    complete_scientific_plan=1989,
)


def _experiment_seeds(
    definition: ExperimentDefinition,
    master_seeds: tuple[MasterSeed, ...],
    smoke_seed: MasterSeed,
) -> tuple[MasterSeed, ...]:
    if definition.seed_count == 1:
        return (smoke_seed,)
    return master_seeds[: definition.seed_count]


def _baseline_validation_cells(
    definition: ExperimentDefinition,
    smoke_seed: MasterSeed,
) -> tuple[ScientificCell, ...]:
    return tuple(
        ScientificCell(
            experiment=definition.name,
            method=method,
            condition=baseline_validation_fixture_for_method(method),
            master_seed=smoke_seed,
        )
        for method in definition.methods
    )


def _ablation_condition(variant: AblationVariant) -> ConditionName:
    scenario: AblationScenario = ablation_scenario_for_variant(variant)
    return scenario.value


def _ablation_cells(
    definition: ExperimentDefinition,
    seeds: tuple[MasterSeed, ...],
) -> tuple[ScientificCell, ...]:
    return tuple(
        ScientificCell(
            experiment=definition.name,
            method=variant.value,
            condition=_ablation_condition(variant),
            master_seed=seed,
        )
        for variant in AblationVariant
        for seed in seeds
    )


def _efficiency_cells(
    definition: ExperimentDefinition,
    seeds: tuple[MasterSeed, ...],
) -> tuple[ScientificCell, ...]:
    return tuple(
        ScientificCell(
            experiment=definition.name,
            method=method,
            condition=f"repetition-{repetition_index}",
            master_seed=seed,
        )
        for method in definition.methods
        for seed in seeds
        for repetition_index in EFFICIENCY_REPETITION_INDICES
    )


def _cartesian_cells(
    definition: ExperimentDefinition,
    seeds: tuple[MasterSeed, ...],
) -> tuple[ScientificCell, ...]:
    return tuple(
        ScientificCell(
            experiment=definition.name,
            method=method,
            condition=condition,
            master_seed=seed,
        )
        for method in definition.methods
        for condition in definition.conditions
        for seed in seeds
    )


def _planned_experiment(
    definition: ExperimentDefinition,
    master_seeds: tuple[MasterSeed, ...],
    smoke_seed: MasterSeed,
) -> PlannedExperiment:
    seeds = _experiment_seeds(definition, master_seeds, smoke_seed)
    if definition.name == BASELINE_IMPLEMENTATION_VALIDATION_NAME:
        cells = _baseline_validation_cells(definition, smoke_seed)
    elif definition.name == MECHANISM_ABLATION_NAME:
        cells = _ablation_cells(definition, seeds)
    elif definition.name == EFFICIENCY_MEASUREMENT_NAME:
        cells = _efficiency_cells(definition, seeds)
    else:
        cells = _cartesian_cells(definition, seeds)
    return PlannedExperiment(
        definition=definition,
        cells=cells,
        prerequisites=definition.prerequisites,
        lifecycle_state=ExperimentLifecycleState.NOT_STARTED,
        resolved_core_dependent=definition.name in POST_CORE_EXPERIMENT_NAMES,
    )


def _with_lifecycle_state(
    planned: PlannedExperiment,
    lifecycle_state: ExperimentLifecycleState,
) -> PlannedExperiment:
    return PlannedExperiment(
        definition=planned.definition,
        cells=planned.cells,
        prerequisites=planned.prerequisites,
        lifecycle_state=lifecycle_state,
        resolved_core_dependent=planned.resolved_core_dependent,
    )


def _collapse_decision_passed(
    experiment: ExperimentName,
    states: tuple[tuple[ExperimentName, CollapseDecisionPassed], ...],
) -> CollapseDecisionPassed | None:
    for recorded_experiment, passed in states:
        if recorded_experiment == experiment:
            return passed
    return None


def build_plan(
    resolved_core_complete: ResolvedCoreComplete = False,
    collapse_decision_states: tuple[tuple[ExperimentName, CollapseDecisionPassed], ...]
    | None = None,
    master_seeds: tuple[MasterSeed, ...] | None = None,
    smoke_seed: MasterSeed | None = None,
) -> ExperimentPlan:
    if master_seeds is None or smoke_seed is None:
        from fedsira.runtime.state import current_application_context

        seeds = current_application_context().scientific_config.seeds_and_determinism
        master_seeds = master_seeds or seeds.master_seeds
        smoke_seed = smoke_seed or seeds.smoke_seed
    decision_states = tuple(collapse_decision_states or ())
    planned: list[PlannedExperiment] = []
    for definition in EXPERIMENT_REGISTRY:
        item = _planned_experiment(definition, master_seeds, smoke_seed)
        if item.resolved_core_dependent and not resolved_core_complete:
            item = _with_lifecycle_state(item, ExperimentLifecycleState.BLOCKED)
        elif definition.name in COLLAPSE_EXPERIMENT_NAMES:
            passed = _collapse_decision_passed(definition.name, decision_states)
            if passed is False:
                item = _with_lifecycle_state(item, ExperimentLifecycleState.COMPLETED)
        planned.append(item)
    return ExperimentPlan(experiments=tuple(planned))


def plan_cell_count_contract() -> PlanCellCountContract:
    return PLAN_CELL_COUNT_CONTRACT


def validate_planned_cell_count_invariant(plan: ExperimentPlan) -> None:
    nominal = plan_cell_count_contract()
    for planned in plan.experiments:
        observed = len(planned.cells)
        expected = planned.definition.nominal_cell_count
        if observed != expected:
            raise ValueError(
                f"experiment {planned.definition.name} plans {observed} cells but "
                f"its nominal Section 31 count is {expected}"
            )
    if plan.pre_core_cell_count != nominal.pre_core_subtotal:
        raise ValueError(
            f"pre-core planned cell count {plan.pre_core_cell_count} does not match "
            f"the Section 31 contract {nominal.pre_core_subtotal}"
        )
    if plan.post_core_cell_count != nominal.post_core_subtotal:
        raise ValueError(
            f"post-core planned cell count {plan.post_core_cell_count} does not match "
            f"the Section 31 contract {nominal.post_core_subtotal}"
        )
    if plan.total_cell_count != nominal.complete_scientific_plan:
        raise ValueError(
            f"total planned cell count {plan.total_cell_count} does not match "
            f"the Section 31 contract {nominal.complete_scientific_plan}"
        )
