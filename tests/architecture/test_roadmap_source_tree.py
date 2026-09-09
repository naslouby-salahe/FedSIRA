from pathlib import Path

from _repo import SRC_ROOT

ROADMAP_MODULES = frozenset(
    {
        "__init__.py",
        "application.py",
        "artifacts.py",
        "attacks.py",
        "baselines/__init__.py",
        "baselines/calibration.py",
        "baselines/certified_ensemble.py",
        "baselines/independent_retraining.py",
        "baselines/references.py",
        "baselines/registry.py",
        "baselines/robust_aggregation.py",
        "baselines/source_model.py",
        "cli/__init__.py",
        "workflows/__init__.py",
        "workflows/doctor.py",
        "workflows/plan.py",
        "workflows/preprocess.py",
        "workflows/report.py",
        "workflows/run.py",
        "workflows/smoke.py",
        "cli/main.py",
        "config.py",
        "datasets/__init__.py",
        "datasets/ciciot2023/__init__.py",
        "datasets/ciciot2023/loading.py",
        "datasets/ciciot2023/preprocessing.py",
        "datasets/ciciot2023/schema.py",
        "datasets/ciciot2023/validation.py",
        "datasets/common.py",
        "datasets/nbaiot/__init__.py",
        "datasets/nbaiot/loading.py",
        "datasets/nbaiot/preprocessing.py",
        "datasets/nbaiot/schema.py",
        "datasets/nbaiot/validation.py",
        "datasets/roles.py",
        "datasets/sampling.py",
        "datasets/scaling.py",
        "domain/__init__.py",
        "domain/enums.py",
        "domain/models.py",
        "domain/types.py",
        "evaluation/__init__.py",
        "evaluation/comparisons.py",
        "evaluation/metrics.py",
        "evaluation/statistics.py",
        "evaluation/summaries.py",
        "experiments/__init__.py",
        "experiments/collapse.py",
        "experiments/definitions.py",
        "experiments/execution.py",
        "experiments/planning.py",
        "experiments/executor.py",
        "experiments/scenarios/__init__.py",
        "experiments/scenarios/capability_granularity.py",
        "experiments/scenarios/evidence_arrival.py",
        "experiments/scenarios/evidence_scarcity.py",
        "experiments/scenarios/heterogeneity.py",
        "experiments/validation.py",
        "io/__init__.py",
        "io/paths.py",
        "io/storage.py",
        "learning/__init__.py",
        "learning/aggregation.py",
        "learning/anchor.py",
        "learning/federated.py",
        "learning/model.py",
        "learning/post_reference.py",
        "learning/scoring.py",
        "learning/training.py",
        "protocol/__init__.py",
        "protocol/admission.py",
        "protocol/capability_contract.py",
        "protocol/proposal.py",
        "protocol/reproduction.py",
        "protocol/specification.py",
        "protocol/state_machine.py",
        "protocol/synthesis.py",
        "protocol/verification.py",
        "reporting/__init__.py",
        "reporting/export.py",
        "reporting/figures.py",
        "reporting/tables.py",
        "reporting/verification.py",
        "runtime.py",
        "runtime_execution.py",
    }
)


def _relative_python_modules() -> frozenset[str]:
    return frozenset(
        path.relative_to(SRC_ROOT).as_posix() for path in SRC_ROOT.rglob("*.py") if path.is_file()
    )


def test_source_tree_matches_authoritative_roadmap() -> None:
    observed = _relative_python_modules()
    missing = sorted(ROADMAP_MODULES - observed)
    unexpected = sorted(observed - ROADMAP_MODULES)
    assert (
        not missing and not unexpected
    ), f"Roadmap source tree drift; missing={missing}, unexpected={unexpected}"


def test_roadmap_module_paths_are_normalized() -> None:
    assert all(Path(path).as_posix() == path for path in ROADMAP_MODULES)
