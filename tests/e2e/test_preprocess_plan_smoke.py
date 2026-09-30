import csv
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fedsira import application as doctor
from fedsira.artifacts.paths import current_repository_root, prepared_evidence_root
from fedsira.cli import app
from fedsira.datasets.common import FeatureMoments
from fedsira.datasets.nbaiot.prepare import DiscoveredCsvFile, PreparedView
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_PRIMARY_PREDICTOR_COUNT,
    NBAIOT_TRIGGER_FEATURES,
)
from fedsira.domain.enums import (
    DatasetId,
    ExperimentLifecycleState,
    ExperimentName,
    ProjectStage,
)
from fedsira.experiments.engine import ExecutionRecordStore
from fedsira.experiments.planning import ExperimentPlan, build_plan, plan_cell_count_contract
from fedsira.runtime import (
    ApplicationContext,
    EnvironmentMismatch,
    bound_application_context,
    current_application_context,
)

runner = CliRunner()


def _no_mismatches(_rar_archives_present: object) -> tuple[EnvironmentMismatch, ...]:
    return ()


def test_plan_command_prints_roadmap_cell_counts() -> None:
    result = runner.invoke(app, ["plan"])
    contract = plan_cell_count_contract()
    assert result.exit_code == 0
    assert f"total cells: {contract.complete_scientific_plan}" in result.stdout
    assert f"pre-core cells: {contract.pre_core_subtotal}" in result.stdout
    assert f"post-core cells: {contract.post_core_subtotal}" in result.stdout


def test_smoke_command_passes_protocol_invariants() -> None:
    result = runner.invoke(app, ["smoke"])
    assert result.exit_code == 0
    assert "result: PASSED" in result.stdout


def test_doctor_command_reports_configuration_and_next_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(doctor, "collect_environment_mismatches", _no_mismatches)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "configuration: valid" in result.stdout
    assert "next valid action:" in result.stdout
    assert "project stage:" in result.stdout


def test_preprocess_does_not_start_experiment_after_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, DatasetId | ExperimentName | None]] = []

    def preprocess(dataset: DatasetId | None, overwrite: bool) -> None:
        calls.append(("preprocess", dataset))

    def run(name: ExperimentName, overwrite: bool) -> None:
        calls.append(("run", name))

    monkeypatch.setattr(doctor, "execute_preprocess", preprocess)
    monkeypatch.setattr(doctor, "execute_run", run)

    assert doctor.FedSIRAApplication().preprocess(None, False) == 0
    assert calls == [("preprocess", None)]


def test_secondary_only_preprocess_only_materializes_dataset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs: list[ExperimentName] = []

    def preprocess(dataset: DatasetId | None, overwrite: bool) -> None:
        return None

    def run(name: ExperimentName, overwrite: bool) -> None:
        runs.append(name)

    monkeypatch.setattr(doctor, "execute_preprocess", preprocess)
    monkeypatch.setattr(doctor, "execute_run", run)

    assert doctor.FedSIRAApplication().preprocess(DatasetId.CICIOT2023, False) == 0
    assert runs == []


def test_doctor_keeps_pre_experiment_validation_before_baseline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plan = build_plan(resolved_core_complete=False)
    store = ExecutionRecordStore(tmp_path)

    def experiment_state(
        _plan: ExperimentPlan,
        _store: ExecutionRecordStore,
        _name: ExperimentName,
    ) -> ExperimentLifecycleState:
        return ExperimentLifecycleState.READY

    monkeypatch.setattr(doctor, "_smoke_complete", lambda: True)
    monkeypatch.setattr(doctor, "_experiment_state", experiment_state)

    stage = doctor.derive_project_stage((), ExperimentLifecycleState.COMPLETED, plan, store, False)

    assert stage is ProjectStage.PREPROCESSING_AND_DATA_VALIDATION


def test_prepared_datasets_name_the_validation_experiment_as_next_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(doctor, "collect_environment_mismatches", _no_mismatches)
    monkeypatch.setattr(doctor, "_repository_layout_mismatches", lambda: ())
    monkeypatch.setattr(doctor, "dataset_readiness", lambda: ExperimentLifecycleState.COMPLETED)

    def experiment_state(
        _plan: ExperimentPlan,
        _store: ExecutionRecordStore,
        _name: ExperimentName,
    ) -> ExperimentLifecycleState:
        return ExperimentLifecycleState.READY

    monkeypatch.setattr(doctor, "_experiment_state", experiment_state)
    report = doctor.diagnose()
    assert report.project_stage is ProjectStage.PREPROCESSING_AND_DATA_VALIDATION
    assert report.next_valid_action == ('run fedsira run "Data and Domain Evidence Validation"')


def test_missing_prepared_datasets_name_preprocess_as_next_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(doctor, "collect_environment_mismatches", _no_mismatches)
    monkeypatch.setattr(doctor, "_repository_layout_mismatches", lambda: ())
    monkeypatch.setattr(doctor, "dataset_readiness", lambda: ExperimentLifecycleState.READY)
    report = doctor.diagnose()
    assert report.project_stage is ProjectStage.PREPROCESSING_AND_DATA_VALIDATION
    assert report.next_valid_action == "run fedsira preprocess to prepare roadmap datasets"


def _write_preprocessing_fixture(repository_root: Path) -> None:
    base_feature_count = NBAIOT_PRIMARY_PREDICTOR_COUNT - len(NBAIOT_TRIGGER_FEATURES)
    header = (
        *(f"fixture_feature_{index}" for index in range(base_feature_count)),
        *(feature.value for feature in NBAIOT_TRIGGER_FEATURES),
    )
    raw_directories = (
        "Danmini_Doorbell",
        "Ennio_Doorbell",
        "Ecobee_Thermostat",
        "Philips_B120N10_Baby_Monitor",
        "Provision_PT_737E_Security_Camera",
        "Provision_PT_838_Security_Camera",
        "SimpleHome_XCS7_1002_WHT_Security_Camera",
        "SimpleHome_XCS7_1003_WHT_Security_Camera",
        "Samsung_SNH_1011_N_Webcam",
    )
    raw_root = repository_root / "data" / "raw" / "N-BaIoT"
    for domain_index, directory in enumerate(raw_directories):
        domain_root = raw_root / directory
        domain_root.mkdir(parents=True, exist_ok=True)
        streams = [(domain_root / "benign_traffic.csv", 0)]
        if domain_index < 7:
            target_root = domain_root / "gafgyt_attacks"
            target_root.mkdir(parents=True, exist_ok=True)
            streams.append((target_root / "combo.csv", 1))
        for path, class_offset in streams:
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(header)
                for row_index in range(40):
                    writer.writerow(
                        [
                            float(row_index + feature_index + domain_index + class_offset)
                            for feature_index in range(NBAIOT_PRIMARY_PREDICTOR_COUNT)
                        ]
                    )


def test_fixture_preprocess_recovery_reuse_and_safe_cli_chain(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository_root = tmp_path / "repository"
    (repository_root / "configs").mkdir(parents=True)
    source_config = current_application_context().repository_root / "configs" / "fedsira.yaml"
    shutil.copyfile(source_config, repository_root / "configs" / "fedsira.yaml")
    _write_preprocessing_fixture(repository_root)

    import fedsira.application as application_module
    import fedsira.datasets.preprocess as preprocessing_module
    import fedsira.reporting.export as reporting_module

    monkeypatch.setattr(application_module, "REPOSITORY_ROOT", repository_root)
    monkeypatch.setattr(preprocessing_module, "REPOSITORY_ROOT", repository_root)
    monkeypatch.setattr(reporting_module, "REPOSITORY_ROOT", repository_root)
    context = ApplicationContext.load(repository_root)

    with bound_application_context(context):
        prepared_root = current_repository_root() / prepared_evidence_root(DatasetId.N_BAIOT)

        first_preprocess = runner.invoke(app, ["preprocess", "N-BaIoT"])
        assert first_preprocess.exit_code == 0, first_preprocess.stdout
        parquet_paths = tuple(sorted(prepared_root.glob("*.parquet")))
        assert parquet_paths

        parquet_paths[0].write_bytes(parquet_paths[0].read_bytes() + b"invalid-tail")
        actual_materializer = preprocessing_module.materialize_nbaiot_prepared_views
        materialization_calls = 0

        def count_materialization(
            discovered: tuple[DiscoveredCsvFile, ...],
            prepared_root: Path,
            scaler_root: Path,
            overwrite: bool = False,
            retain_materialized_views: bool = True,
        ) -> tuple[tuple[PreparedView, ...], FeatureMoments]:
            nonlocal materialization_calls
            materialization_calls += 1
            return actual_materializer(
                discovered,
                prepared_root,
                scaler_root,
                overwrite,
                retain_materialized_views,
            )

        monkeypatch.setattr(
            preprocessing_module,
            "materialize_nbaiot_prepared_views",
            count_materialization,
        )
        recovered_preprocess = runner.invoke(app, ["preprocess", "N-BaIoT"])
        assert recovered_preprocess.exit_code == 0, recovered_preprocess.stdout
        assert materialization_calls == 1

        def unexpected_materialization(
            discovered: tuple[DiscoveredCsvFile, ...],
            prepared_root: Path,
            scaler_root: Path,
            overwrite: bool = False,
            retain_materialized_views: bool = True,
        ) -> tuple[tuple[PreparedView, ...], FeatureMoments]:
            del discovered, prepared_root, scaler_root, overwrite, retain_materialized_views
            raise AssertionError("verified preprocessing cache should bypass materialization")

        monkeypatch.setattr(
            preprocessing_module,
            "materialize_nbaiot_prepared_views",
            unexpected_materialization,
        )
        reused_preprocess = runner.invoke(app, ["preprocess", "N-BaIoT"])
        assert reused_preprocess.exit_code == 0, reused_preprocess.stdout

        plan_result = runner.invoke(app, ["plan"])
        assert plan_result.exit_code == 0
        contract = plan_cell_count_contract()
        assert f"total cells: {contract.complete_scientific_plan}" in plan_result.stdout

        smoke_result = runner.invoke(app, ["smoke"])
        assert smoke_result.exit_code == 0
        assert "result: PASSED" in smoke_result.stdout

        status_result = runner.invoke(app, ["status"])
        assert status_result.exit_code == 0
        assert "Baseline Implementation Validation" in status_result.stdout

        report_result = runner.invoke(app, ["report"])
        assert report_result.exit_code == 1
        assert "BLOCKED" in report_result.stdout
