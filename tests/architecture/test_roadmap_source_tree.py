from pathlib import Path

from _repo import SRC_ROOT

ROADMAP_MODULES = frozenset(
    {
        "__init__.py",
        "application.py",
        "artifacts/__init__.py",
        "artifacts/paths.py",
        "artifacts/provenance.py",
        "artifacts/storage.py",
        "cli.py",
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
        "datasets/preprocess.py",
        "datasets/roles.py",
        "datasets/sampling.py",
        "datasets/scaling.py",
        "domain/__init__.py",
        "domain/enums.py",
        "domain/models.py",
        "domain/types.py",
        "evaluation/__init__.py",
        "evaluation/backdoor.py",
        "evaluation/capability_boundary.py",
        "evaluation/comparisons.py",
        "evaluation/domain.py",
        "evaluation/epistemic_boundary.py",
        "evaluation/indexing.py",
        "evaluation/metrics.py",
        "evaluation/report_summary.py",
        "evaluation/screening.py",
        "evaluation/service.py",
        "evaluation/statistics.py",
        "evaluation/summaries.py",
        "experiments/__init__.py",
        "experiments/cell_support.py",
        "experiments/cells.py",
        "experiments/collapse.py",
        "experiments/definitions.py",
        "experiments/execution.py",
        "experiments/executor.py",
        "experiments/planning.py",
        "experiments/prerequisites.py",
        "experiments/scenarios/__init__.py",
        "experiments/scenarios/capability_granularity.py",
        "experiments/scenarios/evidence_arrival.py",
        "experiments/scenarios/evidence_scarcity.py",
        "experiments/scenarios/heterogeneity.py",
        "experiments/validation.py",
        "experiments/workflow.py",
        "learning/__init__.py",
        "learning/aggregation.py",
        "learning/anchor.py",
        "learning/anchor_training.py",
        "learning/federated.py",
        "learning/model.py",
        "learning/post_reference.py",
        "learning/post_reference_training.py",
        "learning/reference.py",
        "learning/scoring.py",
        "learning/training.py",
        "protocol/__init__.py",
        "protocol/admission.py",
        "protocol/attacks/__init__.py",
        "protocol/attacks/byzantine.py",
        "protocol/attacks/source.py",
        "protocol/baselines/__init__.py",
        "protocol/baselines/calibration.py",
        "protocol/baselines/certified_ensemble.py",
        "protocol/baselines/fedavg_training.py",
        "protocol/baselines/independent_retraining.py",
        "protocol/baselines/outcomes.py",
        "protocol/baselines/reconstruction_training.py",
        "protocol/baselines/references.py",
        "protocol/baselines/registry.py",
        "protocol/baselines/robust_aggregation.py",
        "protocol/baselines/robust_training.py",
        "protocol/baselines/source_model.py",
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
        "reporting/materialization.py",
        "reporting/tables.py",
        "reporting/verification.py",
        "runtime.py",
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
