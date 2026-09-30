from pathlib import Path

import torch
from pytest import MonkeyPatch

from fedsira.datasets.common import BackdoorScope, DomainTargetMetrics, RealAnchor
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER, NBAIOT_TRIGGER_FEATURES
from fedsira.domain.enums import (
    AdmissionState,
    BaselineIdentity,
    ComparisonMetric,
    PrimaryScenario,
)
from fedsira.domain.models import MetricResult, PreparedEvidenceCounts, ScientificCell
from fedsira.domain.types import DeltaScale, DomainId, MetricObservation
from fedsira.experiments.definitions import PRIMARY_CONFIRMATORY_EVALUATION_NAME
from fedsira.experiments.handlers import ProtocolCellExecutor
from fedsira.learning.model import FedSIRAClassifier
from fedsira.learning.training import load_model_state, model_state_from_classifier
from fedsira.protocol.attacks import model_replacement_client_state
from fedsira.protocol.baselines.defenses import clients_retained_by_trimmed_mean
from fedsira.protocol.baselines.registry import BaselineValidationFixture
from fedsira.runtime import current_application_context


def _filled_state(fill: float) -> FedSIRAClassifier:
    model = FedSIRAClassifier(4, 2)
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.fill_(fill)
    return model


def test_model_replacement_scales_the_round_delta_before_submission() -> None:
    current = model_state_from_classifier(_filled_state(0.0))
    trained = model_state_from_classifier(_filled_state(1.0))
    attacks = current_application_context().scientific_config.attacks_and_boundaries
    scale = attacks.byzantine_reproduction.model_replacement.delta_scale
    replaced = model_replacement_client_state(current, trained, 4, 2, scale)
    replaced_model = FedSIRAClassifier(4, 2)
    load_model_state(replaced_model, replaced)
    assert all(
        torch.allclose(parameter, torch.full_like(parameter, scale))
        for parameter in replaced_model.parameters()
    )


def test_trimmed_mean_drops_a_coordinate_outlier_from_ancestry() -> None:
    density = current_application_context().scientific_config.baselines.density_cluster_trimmed_mean
    width = density.minimum_cluster_size_for_trimming
    honest = torch.zeros(width)
    outlier = torch.full((width,), 10.0)
    updates = tuple(honest.clone() for _ in range(width - 1)) + (outlier,)
    domains = tuple(f"honest-{index}" for index in range(width - 1)) + ("outlier",)
    retained = clients_retained_by_trimmed_mean(
        domains,
        updates,
        density.minimum_cluster_size_for_trimming,
        density.trim_each_tail_count,
    )
    if density.trim_each_tail_count > 0 and width > density.trim_each_tail_count:
        assert "outlier" not in retained
    else:
        assert "outlier" in retained


def _primary_cell(method: BaselineIdentity, condition: PrimaryScenario) -> ScientificCell:
    return ScientificCell(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        method=method,
        condition=condition,
        master_seed=1103,
    )


class _OrdinaryAttackProbe(ProtocolCellExecutor):
    def training_args(
        self, cell: ScientificCell
    ) -> tuple[DomainId | None, BackdoorScope | None, DeltaScale | None]:
        return self._model_replacement_training_args(cell)

    def baseline(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        return self._execute_baseline_cell(cell, evidence)

    def contributors(self) -> tuple[DomainId, ...]:
        return self._last_production_contributor_ids


def _named_source(_adapter: object, _cell: object) -> str:
    return "source-device"


def _trigger_names(_root: object) -> tuple[str, ...]:
    return tuple(str(feature) for feature in NBAIOT_TRIGGER_FEATURES)


def _evidence() -> PreparedEvidenceCounts:
    return PreparedEvidenceCounts(
        screen_target_count=0,
        reproduction_target_count=2000,
        reproduction_supported_count=2000,
        final_gate_adequate_domain_count=6,
    )


def test_fedavg_byzantine_admission_scores_the_accepted_client_not_the_source(
    monkeypatch: MonkeyPatch,
) -> None:
    scope = BackdoorScope(
        attack_generation_seed=7,
        poison_fraction=0.1,
        trigger_feature_indices=(0,),
        trigger_value=6.0,
    )

    def accept_client(
        _prepared_root: object,
        _master_seed: int,
        _anchor: object,
        _source_domain: object,
        compromised_client: object = None,
        backdoor_scope: object = None,
        replacement_delta_scale: object = None,
        accepted_compromised: list[object] | None = None,
    ) -> torch.Tensor:
        del replacement_delta_scale
        if (
            accepted_compromised is not None
            and compromised_client is not None
            and backdoor_scope is not None
        ):
            accepted_compromised.append(compromised_client)
        return torch.zeros(1)

    def reject_client(
        _prepared_root: object,
        _master_seed: int,
        _anchor: object,
        _source_domain: object,
        compromised_client: object = None,
        backdoor_scope: object = None,
        replacement_delta_scale: object = None,
        accepted_compromised: list[object] | None = None,
    ) -> torch.Tensor:
        del compromised_client, backdoor_scope, replacement_delta_scale, accepted_compromised
        return torch.zeros(1)

    attacks = current_application_context().scientific_config.attacks_and_boundaries
    scale = attacks.byzantine_reproduction.model_replacement.delta_scale

    class _Anchor:
        flat_parameters = torch.zeros(1)

    def admitted_gate(
        _self: object,
        _evidence: object,
        _source: object,
        _anchor: object,
        _checkpoint: object,
    ) -> AdmissionState:
        return AdmissionState.ADMITTED

    def replacement_args(_self: object, _cell: object) -> tuple[str, BackdoorScope, DeltaScale]:
        return ("client-device", scope, scale)

    def anchor(_self: object, _seed: object) -> _Anchor:
        return _Anchor()

    monkeypatch.setattr(
        "fedsira.experiments.handlers.source_domain_for_cell",
        _named_source,
    )
    monkeypatch.setattr(
        "fedsira.protocol.baselines.outcomes.source_domain_for_cell",
        _named_source,
    )
    monkeypatch.setattr(ProtocolCellExecutor, "real_anchor", anchor)
    monkeypatch.setattr(ProtocolCellExecutor, "_final_gate_outcome", admitted_gate)
    monkeypatch.setattr(ProtocolCellExecutor, "_model_replacement_training_args", replacement_args)
    executor = _OrdinaryAttackProbe(primary_prepared_root=Path("prepared-fixture"))
    evidence = _evidence()
    cell = _primary_cell(
        BaselineIdentity.FEDAVG_REFERENCE,
        PrimaryScenario.ONE_BYZANTINE_POST_REFERENCE_PARTICIPANT,
    )
    monkeypatch.setattr(
        "fedsira.protocol.baselines.outcomes.train_fedavg_reference_delta",
        accept_client,
    )
    _accepted_state, accepted_metrics = executor.baseline(cell, evidence)
    monkeypatch.setattr(
        "fedsira.protocol.baselines.outcomes.train_fedavg_reference_delta",
        reject_client,
    )
    _rejected_state, rejected_metrics = executor.baseline(cell, evidence)
    assert dict(accepted_metrics)[ComparisonMetric.MALICIOUS_ADMISSION] == 1.0
    assert dict(rejected_metrics)[ComparisonMetric.MALICIOUS_ADMISSION] == 0.0


def test_byzantine_selector_names_one_non_source_client_at_the_configured_scale(
    monkeypatch: MonkeyPatch,
) -> None:
    source = NBAIOT_DOMAIN_ORDER[0]
    feasible = frozenset(domain for domain in NBAIOT_DOMAIN_ORDER if domain != source)

    def source_for_cell(_adapter: object, _cell: object) -> str:
        return source

    def feasible_domains(_adapter: object) -> frozenset[str]:
        return feasible

    def eligible_domains(_adapter: object, selected_source: object) -> tuple[str, ...]:
        return tuple(domain for domain in NBAIOT_DOMAIN_ORDER if domain != selected_source)

    monkeypatch.setattr(
        "fedsira.experiments.handlers.prepared_feature_names",
        _trigger_names,
    )
    monkeypatch.setattr(
        "fedsira.experiments.handlers.source_domain_for_cell",
        source_for_cell,
    )
    monkeypatch.setattr(
        "fedsira.experiments.handlers.model_replacement_attack_feasible_domains",
        feasible_domains,
    )
    monkeypatch.setattr(
        "fedsira.experiments.handlers.non_source_domains",
        eligible_domains,
    )
    executor = _OrdinaryAttackProbe(primary_prepared_root=Path("prepared-fixture"))
    attacks = current_application_context().scientific_config.attacks_and_boundaries
    replacement = attacks.byzantine_reproduction.model_replacement
    cell = _primary_cell(
        BaselineIdentity.MULTIPLE_MODEL_CERTIFIED_ENSEMBLE,
        PrimaryScenario.ONE_BYZANTINE_POST_REFERENCE_PARTICIPANT,
    )
    selected, scope, scale = executor.training_args(cell)
    repeated, _repeated_scope, _repeated_scale = executor.training_args(cell)
    honest = _primary_cell(
        BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE,
        PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY,
    )
    assert selected in feasible
    assert selected != source
    assert selected == repeated
    assert scale == replacement.delta_scale
    assert scope is not None
    assert scope.poison_fraction == replacement.poison_fraction
    assert executor.training_args(honest) == (None, None, None)
    krum_attack = ScientificCell(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        method=BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE,
        condition=BaselineValidationFixture.MODEL_REPLACEMENT_BACKDOOR,
        master_seed=1103,
    )
    krum_selected, krum_scope, krum_scale = executor.training_args(krum_attack)
    assert krum_selected in feasible
    assert krum_selected != source
    assert krum_scope is not None
    assert krum_scale == replacement.delta_scale


def test_source_backdoor_selector_poisons_averaging_clients_and_leaves_krum_unpoisoned(
    monkeypatch: MonkeyPatch,
) -> None:
    source = NBAIOT_DOMAIN_ORDER[0]

    def source_for_cell(_adapter: object, _cell: object) -> str:
        return source

    monkeypatch.setattr(
        "fedsira.experiments.handlers.prepared_feature_names",
        _trigger_names,
    )
    monkeypatch.setattr(
        "fedsira.experiments.handlers.source_domain_for_cell",
        source_for_cell,
    )
    executor = _OrdinaryAttackProbe(primary_prepared_root=Path("prepared-fixture"))
    attacks = current_application_context().scientific_config.attacks_and_boundaries
    hidden = attacks.hidden_source_backdoor
    fedavg = _primary_cell(
        BaselineIdentity.FEDAVG_REFERENCE,
        PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
    )
    ensemble = _primary_cell(
        BaselineIdentity.MULTIPLE_MODEL_CERTIFIED_ENSEMBLE,
        PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
    )
    krum = _primary_cell(
        BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE,
        PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
    )
    fedavg_client, fedavg_scope, fedavg_scale = executor.training_args(fedavg)
    ensemble_client, ensemble_scope, ensemble_scale = executor.training_args(ensemble)
    assert fedavg_client == source
    assert ensemble_client == source
    assert fedavg_scale is None
    assert ensemble_scale is None
    assert fedavg_scope is not None
    assert ensemble_scope is not None
    assert fedavg_scope.poison_fraction == hidden.confirmatory_poison_fraction
    assert ensemble_scope.poison_fraction == hidden.confirmatory_poison_fraction
    assert executor.training_args(krum) == (None, None, None)


def test_ensemble_byzantine_admission_scores_the_accepted_client_not_the_source(
    monkeypatch: MonkeyPatch,
) -> None:
    scope = BackdoorScope(
        attack_generation_seed=7,
        poison_fraction=0.1,
        trigger_feature_indices=(0,),
        trigger_value=6.0,
    )
    attacks = current_application_context().scientific_config.attacks_and_boundaries
    scale = attacks.byzantine_reproduction.model_replacement.delta_scale

    def accept_client(
        _prepared_root: object,
        _master_seed: int,
        compromised_client: object = None,
        backdoor_scope: object = None,
        replacement_delta_scale: object = None,
        accepted_compromised: list[object] | None = None,
    ) -> tuple[object, ...]:
        del replacement_delta_scale
        if (
            accepted_compromised is not None
            and compromised_client is not None
            and backdoor_scope is not None
        ):
            accepted_compromised.append(compromised_client)
        return (object(),)

    def reject_client(
        _prepared_root: object,
        _master_seed: int,
        compromised_client: object = None,
        backdoor_scope: object = None,
        replacement_delta_scale: object = None,
        accepted_compromised: list[object] | None = None,
    ) -> tuple[object, ...]:
        del compromised_client, backdoor_scope, replacement_delta_scale, accepted_compromised
        return (object(),)

    def empty_domains(_adapter: object, _source: object) -> tuple[str, ...]:
        return ()

    def admit(*_args: object, **_kwargs: object) -> AdmissionState:
        return AdmissionState.ADMITTED

    def anchor(_self: object, _seed: object) -> object:
        return object()

    def replacement_args(_self: object, _cell: object) -> tuple[str, BackdoorScope, DeltaScale]:
        return ("client-device", scope, scale)

    monkeypatch.setattr(
        "fedsira.experiments.handlers.source_domain_for_cell",
        _named_source,
    )
    monkeypatch.setattr(
        "fedsira.protocol.baselines.outcomes.source_domain_for_cell",
        _named_source,
    )
    monkeypatch.setattr(
        "fedsira.protocol.baselines.outcomes.non_source_domains",
        empty_domains,
    )
    monkeypatch.setattr(
        "fedsira.protocol.baselines.outcomes.synthesis_pending_transition",
        admit,
    )
    monkeypatch.setattr(ProtocolCellExecutor, "real_anchor", anchor)
    monkeypatch.setattr(
        ProtocolCellExecutor,
        "_model_replacement_training_args",
        replacement_args,
    )
    executor = _OrdinaryAttackProbe(primary_prepared_root=Path("prepared-fixture"))
    evidence = _evidence()
    cell = _primary_cell(
        BaselineIdentity.MULTIPLE_MODEL_CERTIFIED_ENSEMBLE,
        PrimaryScenario.ONE_BYZANTINE_POST_REFERENCE_PARTICIPANT,
    )
    monkeypatch.setattr(
        "fedsira.protocol.baselines.outcomes.train_certified_ensemble_group_checkpoints",
        accept_client,
    )
    _accepted_state, accepted_metrics = executor.baseline(cell, evidence)
    monkeypatch.setattr(
        "fedsira.protocol.baselines.outcomes.train_certified_ensemble_group_checkpoints",
        reject_client,
    )
    _rejected_state, rejected_metrics = executor.baseline(cell, evidence)
    assert dict(accepted_metrics)[ComparisonMetric.MALICIOUS_ADMISSION] == 1.0
    assert dict(rejected_metrics)[ComparisonMetric.MALICIOUS_ADMISSION] == 0.0


def test_one_byzantine_clean_source_baselines_are_not_malicious_admissions(
    monkeypatch: MonkeyPatch,
) -> None:
    source = NBAIOT_DOMAIN_ORDER[0]
    observed_scopes: list[object] = []
    screen = DomainTargetMetrics(
        target_f1=MetricResult(value=1.0, denominator=1),
        supported_macro_f1=MetricResult(value=1.0, denominator=1),
        benign_far=MetricResult(value=0.0, denominator=1),
    )

    def source_for_cell(_adapter: object, _cell: object) -> str:
        return source

    def anchor(_self: object, _seed: object) -> RealAnchor:
        return RealAnchor(
            input_width=4,
            output_width=2,
            flat_parameters=torch.zeros(4),
            dataset_manifest_hash="a" * 64,
            round_start_flat_parameters=(),
        )

    def clean_delta(
        _adapter: object,
        _seed: object,
        _anchor: object,
        _source: object,
        backdoor_scope: object = None,
    ) -> torch.Tensor:
        observed_scopes.append(backdoor_scope)
        return torch.zeros(4)

    def clean_update(
        _root: object, _seed: object, _anchor: object, _source: object
    ) -> torch.Tensor:
        return torch.zeros(4)

    def clean_checkpoint(*_args: object, **_kwargs: object) -> torch.Tensor:
        return torch.zeros(4)

    def contract_passes(
        _self: object, _anchor: object, _source: object, _checkpoint: object
    ) -> bool:
        return True

    def contract_function(*_args: object, **_kwargs: object) -> bool:
        return True

    def clean_screen(*_args: object, **_kwargs: object) -> DomainTargetMetrics:
        return screen

    def zero_trigger(*_args: object, **_kwargs: object) -> MetricResult:
        return MetricResult(value=0.0, denominator=1)

    def alarm(*_args: object, **_kwargs: object) -> float:
        return 1.0

    def admitted_gate(
        _self: object,
        _evidence: object,
        _source: object,
        _anchor: object,
        _checkpoint: object,
    ) -> AdmissionState:
        return AdmissionState.ADMITTED

    def skip_calibration(_cell: object, _anchor: object) -> None:
        return None

    monkeypatch.setattr("fedsira.experiments.handlers.source_domain_for_cell", source_for_cell)
    monkeypatch.setattr(
        "fedsira.protocol.baselines.outcomes.source_domain_for_cell",
        source_for_cell,
    )
    monkeypatch.setattr("fedsira.experiments.handlers.train_source_candidate_delta", clean_delta)
    monkeypatch.setattr(
        "fedsira.protocol.baselines.outcomes.train_source_candidate_delta",
        clean_delta,
    )
    monkeypatch.setattr(
        "fedsira.protocol.baselines.outcomes.train_source_update_sanitization_delta",
        clean_update,
    )
    monkeypatch.setattr(
        "fedsira.protocol.baselines.outcomes.train_local_only_reference_checkpoint",
        clean_checkpoint,
    )
    monkeypatch.setattr("fedsira.protocol.baselines.outcomes.evaluate_domain", clean_screen)
    monkeypatch.setattr(
        "fedsira.protocol.baselines.outcomes.capability_contract_passes",
        contract_function,
    )
    monkeypatch.setattr(
        "fedsira.protocol.baselines.outcomes.triggered_to_benign_rate",
        zero_trigger,
    )
    monkeypatch.setattr(
        "fedsira.protocol.baselines.outcomes.recovery_backdoor_alarm_threshold",
        alarm,
    )
    monkeypatch.setattr(ProtocolCellExecutor, "_final_gate_outcome", admitted_gate)
    monkeypatch.setattr(
        "fedsira.experiments.handlers.record_baseline_calibration",
        skip_calibration,
    )
    monkeypatch.setattr(
        ProtocolCellExecutor,
        "candidate_capability_contract_passes",
        contract_passes,
    )
    monkeypatch.setattr(ProtocolCellExecutor, "real_anchor", anchor)
    executor = _OrdinaryAttackProbe(primary_prepared_root=Path("prepared-fixture"))
    evidence = _evidence()
    methods = (
        BaselineIdentity.CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION,
        BaselineIdentity.SOURCE_UPDATE_SANITIZATION_REFERENCE,
        BaselineIdentity.RECOVERY_AFTER_SOURCE_ADMISSION,
        BaselineIdentity.INDEPENDENT_LOCAL_REFERENCE_WITH_SOURCE_ADMISSION,
    )
    for method in methods:
        observed_scopes.clear()
        state, metrics = executor.baseline(
            _primary_cell(method, PrimaryScenario.ONE_BYZANTINE_POST_REFERENCE_PARTICIPANT),
            evidence,
        )
        assert state is AdmissionState.ADMITTED
        assert executor.contributors() == (source,)
        assert dict(metrics)[ComparisonMetric.MALICIOUS_ADMISSION] == 0.0
        assert all(scope is None for scope in observed_scopes)
    backdoored_state, backdoored_metrics = executor.baseline(
        _primary_cell(
            BaselineIdentity.CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION,
            PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
        ),
        evidence,
    )
    assert backdoored_state is AdmissionState.ADMITTED
    assert executor.contributors() == (source,)
    assert dict(backdoored_metrics)[ComparisonMetric.MALICIOUS_ADMISSION] == 1.0
