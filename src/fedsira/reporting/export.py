from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from fedsira.analysis.claims import ClaimEvidence, ClaimStateResult, derive_claim_states
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import ExperimentLifecycleState
from fedsira.domain.records import CanonicalToken
from fedsira.experiments.execution import ExperimentExecutionResult
from fedsira.experiments.planning import ExperimentPlan
from fedsira.reporting import tables as table_renderers
from fedsira.reporting.figures import validate_mandatory_figures_covered
from fedsira.reporting.tables import MANUSCRIPT_TABLE_NAMES
from fedsira.reporting.verification import CompletenessVerificationResult

EXPORT_SCHEMA_VERSION = "fedsira|report_export|1"


@dataclass(frozen=True)
class ReportExportResult:
    experiment: CanonicalToken | None
    exported_paths: tuple[Path, ...]
    verification: CompletenessVerificationResult


def _results_root() -> Path:
    return Path("results")


def derive_claim_states_for_export(
    claim_evidence: Mapping[CanonicalToken, ClaimEvidence] | None = None,
    config_path: Path = PRODUCTION_CONFIG_PATH,
) -> tuple[ClaimStateResult, ...]:
    config = load_scientific_config(config_path)
    return derive_claim_states(
        claim_evidence or {},
        config.metrics_and_statistics.materiality,
        config.claim_support_thresholds,
        config.metrics_and_statistics.technical_completion.minimum_complete_pairs_for_claim_support,
    )


def export_experiment_report(
    result: ExperimentExecutionResult,
    config_path: Path,
    experiment_root: Path,
) -> ReportExportResult:
    config = load_scientific_config(config_path)
    rounding = config.metrics_and_statistics.publication_rounding
    tables_root = experiment_root / "tables" / "main"
    metrics_root = experiment_root / "metrics" / "primary"
    tables_root.mkdir(parents=True, exist_ok=True)
    metrics_root.mkdir(parents=True, exist_ok=True)

    exported: list[Path] = []
    statistical_table = table_renderers.render_statistical_summary_table(
        result.comparison_results, rounding
    )
    if result.comparison_results:
        statistical_path = tables_root / "Statistical Summary.md"
        statistical_path.write_text(statistical_table)
        exported.append(statistical_path)

    summary = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "experiment": result.experiment,
        "lifecycle_state": result.lifecycle_state.value,
        "cell_completion_count": result.cell_completion_count,
        "total_cells": len(result.outcomes),
    }
    summary_path = metrics_root / "summary.json"
    summary_path.write_text(json.dumps(summary, sort_keys=True, indent=2))
    exported.append(summary_path)
    return ReportExportResult(
        experiment=result.experiment,
        exported_paths=tuple(exported),
        verification=CompletenessVerificationResult(passed=True, failures=()),
    )


def export_project_summary(
    plan: ExperimentPlan,
    claim_states: Sequence[ClaimStateResult],
    lifecycle_states: Mapping[CanonicalToken, ExperimentLifecycleState],
    config_path: Path,
    verification: CompletenessVerificationResult,
) -> ReportExportResult:
    project_root = _results_root() / "project_summary"
    tables_root = project_root / "tables" / "main"
    claim_root = project_root / "claim_registry"
    reproducibility_root = project_root / "reproducibility" / "execution"
    tables_root.mkdir(parents=True, exist_ok=True)
    claim_root.mkdir(parents=True, exist_ok=True)
    reproducibility_root.mkdir(parents=True, exist_ok=True)

    exported: list[Path] = []

    materialized_tables: list[str] = []
    plan_table = table_renderers.render_experiment_plan_table(plan)
    plan_path = tables_root / "Experiment Plan.md"
    plan_path.write_text(plan_table)
    exported.append(plan_path)
    materialized_tables.append("Experiment Plan")

    claim_table = table_renderers.render_claim_support_table(claim_states)
    claim_path = claim_root / "Claim Support.md"
    claim_path.write_text(claim_table)
    exported.append(claim_path)
    materialized_tables.append("Claim Support")

    reproducibility_summary = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "experiment_states": {name: state.value for name, state in lifecycle_states.items()},
        "verification_passed": verification.passed,
        "verification_failures": list(verification.failures),
        "mandatory_tables": list(MANUSCRIPT_TABLE_NAMES),
        "materialized_tables": materialized_tables,
        "pending_mandatory_tables": [
            name for name in MANUSCRIPT_TABLE_NAMES if name not in materialized_tables
        ],
        "pending_mandatory_figures": [
            str(missing) for missing in validate_mandatory_figures_covered(tuple(exported))
        ],
    }
    reproducibility_path = reproducibility_root / "execution_summary.json"
    reproducibility_path.write_text(json.dumps(reproducibility_summary, sort_keys=True, indent=2))
    exported.append(reproducibility_path)

    return ReportExportResult(
        experiment=None,
        exported_paths=tuple(exported),
        verification=verification,
    )
