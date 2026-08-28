from pathlib import Path

from _repo import SRC_ROOT

ROADMAP_MODULES = frozenset(
    {
        "__init__.py",
        "analysis/__init__.py",
        "analysis/claims.py",
        "analysis/comparisons.py",
        "analysis/statistics.py",
        "artifacts/__init__.py",
        "artifacts/fingerprints.py",
        "artifacts/graph.py",
        "artifacts/paths.py",
        "artifacts/provenance.py",
        "artifacts/records.py",
        "artifacts/storage.py",
        "artifacts/validation.py",
        "attacks/__init__.py",
        "attacks/reproduction.py",
        "attacks/source_backdoor.py",
        "attacks/verification.py",
        "baselines/__init__.py",
        "baselines/calibration.py",
        "baselines/certified_ensemble.py",
        "baselines/independent_retraining.py",
        "baselines/references.py",
        "baselines/registry.py",
        "baselines/robust_aggregation.py",
        "baselines/source_authority.py",
        "boundaries/__init__.py",
        "boundaries/capability_granularity.py",
        "boundaries/epistemic_failure.py",
        "boundaries/evidence_arrival.py",
        "boundaries/heterogeneity.py",
        "cli/__init__.py",
        "cli/commands/__init__.py",
        "cli/commands/doctor.py",
        "cli/commands/plan.py",
        "cli/commands/preprocess.py",
        "cli/commands/report.py",
        "cli/commands/run.py",
        "cli/commands/smoke.py",
        "cli/main.py",
        "config/__init__.py",
        "config/loading.py",
        "config/schema.py",
        "config/validation.py",
        "datasets/__init__.py",
        "datasets/ciciot2023/__init__.py",
        "datasets/ciciot2023/acquisition.py",
        "datasets/ciciot2023/preprocessing.py",
        "datasets/ciciot2023/schema.py",
        "datasets/ciciot2023/validation.py",
        "datasets/common.py",
        "datasets/nbaiot/__init__.py",
        "datasets/nbaiot/acquisition.py",
        "datasets/nbaiot/preprocessing.py",
        "datasets/nbaiot/schema.py",
        "datasets/nbaiot/validation.py",
        "datasets/roles.py",
        "datasets/sampling.py",
        "datasets/scaling.py",
        "domain/__init__.py",
        "domain/enums.py",
        "domain/records.py",
        "evaluation/__init__.py",
        "evaluation/aggregation.py",
        "evaluation/metrics.py",
        "evaluation/records.py",
        "evaluation/validation.py",
        "experiments/__init__.py",
        "experiments/collapse.py",
        "experiments/execution.py",
        "experiments/planning.py",
        "experiments/registry.py",
        "experiments/validation.py",
        "learning/__init__.py",
        "learning/aggregation.py",
        "learning/anchor.py",
        "learning/federated.py",
        "learning/post_reference.py",
        "learning/scoring.py",
        "learning/training.py",
        "models/__init__.py",
        "models/mlp.py",
        "protocol/__init__.py",
        "protocol/admission.py",
        "protocol/claim_contract.py",
        "protocol/opening.py",
        "protocol/reproduction.py",
        "protocol/state_machine.py",
        "protocol/synthesis.py",
        "protocol/theory.py",
        "protocol/verification.py",
        "reporting/__init__.py",
        "reporting/export.py",
        "reporting/figures.py",
        "reporting/tables.py",
        "reporting/verification.py",
        "runtime/__init__.py",
        "runtime/determinism.py",
        "runtime/environment.py",
        "runtime/logging.py",
        "runtime/recovery.py",
        "runtime/state.py",
        "runtime/timing.py",
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
