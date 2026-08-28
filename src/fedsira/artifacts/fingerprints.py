import ast
import hashlib
import importlib.metadata
import importlib.util
from pathlib import Path

import torch

from fedsira.domain.enums import DatasetId, ProducerFingerprintFamily
from fedsira.domain.records import (
    ArtifactDigest,
    AstDumpText,
    DependencyImportName,
    FingerprintPayload,
    ModuleName,
    SchemaVersion,
)
from fedsira.runtime.determinism import framed_bytes

IMPORT_NAME_TO_DISTRIBUTION_NAME: dict[DependencyImportName, DependencyImportName] = {
    "sklearn": "scikit-learn",
    "yaml": "pyyaml",
}

DATASET_PACKAGE_NAME: dict[DatasetId, ModuleName] = {
    DatasetId.N_BAIOT: "nbaiot",
    DatasetId.CICIOT2023: "ciciot2023",
}

PRODUCER_ENTRY_MODULES: dict[ProducerFingerprintFamily, tuple[ModuleName, ...]] = {
    ProducerFingerprintFamily.ROLE_SPLIT_SAMPLE_PREPARED_SCALER: (
        "fedsira.datasets.roles",
        "fedsira.datasets.sampling",
        "fedsira.datasets.scaling",
    ),
    ProducerFingerprintFamily.ANCHOR_FEDAVG_CHECKPOINTS: (
        "fedsira.models.mlp",
        "fedsira.learning.training",
        "fedsira.learning.federated",
        "fedsira.learning.anchor",
        "fedsira.runtime.determinism",
    ),
    ProducerFingerprintFamily.SOURCE_REPRODUCTION_CHECKPOINTS: (
        "fedsira.models.mlp",
        "fedsira.learning.training",
        "fedsira.learning.post_reference",
        "fedsira.runtime.determinism",
    ),
    ProducerFingerprintFamily.BASELINE_CHECKPOINT_CALIBRATION: (
        "fedsira.baselines.registry",
        "fedsira.runtime.determinism",
    ),
    ProducerFingerprintFamily.MODEL_SCORES: (
        "fedsira.models.mlp",
        "fedsira.learning.scoring",
    ),
    ProducerFingerprintFamily.OPENING_VERIFIER_CERTIFICATE_SYNTHESIS_FINAL_GATE: (
        "fedsira.evaluation.metrics",
        "fedsira.learning.aggregation",
    ),
    ProducerFingerprintFamily.BOUNDARY_TRANSFORMATION: ("fedsira.datasets.sampling",),
    ProducerFingerprintFamily.METRIC_ARTIFACT: (
        "fedsira.evaluation.metrics",
        "fedsira.evaluation.aggregation",
        "fedsira.evaluation.validation",
    ),
    ProducerFingerprintFamily.STATISTICAL_COMPARISON_ARTIFACT: (
        "fedsira.analysis.statistics",
        "fedsira.analysis.comparisons",
    ),
    ProducerFingerprintFamily.CLAIM_STATE_ARTIFACT: (
        "fedsira.analysis.claims",
        "fedsira.analysis.comparisons",
    ),
    ProducerFingerprintFamily.REPORT_SOURCE_EXPORT: ("fedsira.reporting",),
}

PRODUCER_RELEVANT_EXTERNAL_IMPORT_NAMES: dict[
    ProducerFingerprintFamily, tuple[DependencyImportName, ...]
] = {
    ProducerFingerprintFamily.RAW_SCHEMA_EXCLUSION_MANIFEST: ("pandas", "numpy"),
    ProducerFingerprintFamily.ROLE_SPLIT_SAMPLE_PREPARED_SCALER: (
        "pandas",
        "numpy",
        "pyarrow",
    ),
    ProducerFingerprintFamily.ANCHOR_FEDAVG_CHECKPOINTS: ("torch", "numpy"),
    ProducerFingerprintFamily.SOURCE_REPRODUCTION_CHECKPOINTS: ("torch", "numpy"),
    ProducerFingerprintFamily.BASELINE_CHECKPOINT_CALIBRATION: (
        "torch",
        "numpy",
        "scipy",
        "sklearn",
    ),
    ProducerFingerprintFamily.MODEL_SCORES: ("torch", "numpy"),
    ProducerFingerprintFamily.OPENING_VERIFIER_CERTIFICATE_SYNTHESIS_FINAL_GATE: (
        "numpy",
        "scipy",
        "sklearn",
    ),
    ProducerFingerprintFamily.BOUNDARY_TRANSFORMATION: ("numpy", "pandas", "pyarrow"),
    ProducerFingerprintFamily.METRIC_ARTIFACT: ("numpy", "sklearn"),
    ProducerFingerprintFamily.STATISTICAL_COMPARISON_ARTIFACT: (
        "numpy",
        "scipy",
        "statsmodels",
    ),
    ProducerFingerprintFamily.CLAIM_STATE_ARTIFACT: ("numpy",),
    ProducerFingerprintFamily.REPORT_SOURCE_EXPORT: ("pandas", "pyarrow", "matplotlib"),
}


def raw_schema_exclusion_manifest_entry_modules(dataset: DatasetId) -> tuple[ModuleName, ...]:
    package = DATASET_PACKAGE_NAME[dataset]
    return (
        f"fedsira.datasets.{package}.acquisition",
        f"fedsira.datasets.{package}.schema",
        f"fedsira.datasets.{package}.validation",
    )


def compute_artifact_dependency_fingerprint(
    schema_version: SchemaVersion,
    scientific_configuration_subset: FingerprintPayload,
    dataset_split_view_identities: FingerprintPayload,
    semantic_coordinates_and_seed_namespaces: FingerprintPayload,
    upstream_artifact_identities: tuple[ArtifactDigest, ...],
    producer_component_fingerprint: ArtifactDigest,
    external_dependency_fingerprint: ArtifactDigest,
) -> ArtifactDigest:
    return hashlib.sha256(
        framed_bytes(
            schema_version,
            scientific_configuration_subset,
            dataset_split_view_identities,
            semantic_coordinates_and_seed_namespaces,
            *upstream_artifact_identities,
            producer_component_fingerprint,
            external_dependency_fingerprint,
        )
    ).hexdigest()


def _module_file_path(dotted_name: ModuleName) -> Path:
    spec = importlib.util.find_spec(dotted_name)
    if spec is None or spec.origin is None:
        raise ValueError(f"cannot resolve producer module {dotted_name}")
    return Path(spec.origin)


def _try_module_file_path(dotted_name: ModuleName) -> Path | None:
    try:
        spec = importlib.util.find_spec(dotted_name)
    except (ImportError, ValueError):
        return None
    if spec is None or spec.origin is None:
        return None
    return Path(spec.origin)


def _is_type_checking_test(test: ast.expr) -> bool:
    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
        return True
    return isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"


def _type_checking_guarded_node_ids(tree: ast.Module) -> set[int]:
    guarded: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and _is_type_checking_test(node.test):
            for statement in node.body:
                for descendant in ast.walk(statement):
                    guarded.add(id(descendant))
    return guarded


def _imported_fedsira_modules(tree: ast.Module) -> tuple[set[ModuleName], set[ModuleName]]:
    guarded_ids = _type_checking_guarded_node_ids(tree)
    certain: set[ModuleName] = set()
    speculative: set[ModuleName] = set()
    for node in ast.walk(tree):
        if id(node) in guarded_ids:
            continue
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "fedsira" or alias.name.startswith("fedsira."):
                    certain.add(alias.name)
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and (node.module == "fedsira" or node.module.startswith("fedsira."))
        ):
            certain.add(node.module)
            for alias in node.names:
                speculative.add(f"{node.module}.{alias.name}")
    return certain, speculative


def _has_dynamic_import(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Name) and function.id == "__import__":
            return True
        if isinstance(function, ast.Attribute) and function.attr == "import_module":
            return True
    return False


def resolve_producer_import_closure(
    entry_modules: tuple[ModuleName, ...],
) -> dict[ModuleName, Path]:
    resolved: dict[ModuleName, Path] = {}
    frontier = list(entry_modules)
    while frontier:
        dotted = frontier.pop()
        if dotted in resolved:
            continue
        path = _module_file_path(dotted)
        resolved[dotted] = path
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        certain, speculative = _imported_fedsira_modules(tree)
        frontier.extend(certain - resolved.keys())
        for candidate in speculative - resolved.keys():
            candidate_path = _try_module_file_path(candidate)
            if candidate_path is not None:
                frontier.append(candidate)
    return resolved


def _is_dunder_assignment(node: ast.stmt) -> bool:
    if not isinstance(node, ast.Assign):
        return False
    return all(
        isinstance(target, ast.Name) and target.id.startswith("__") for target in node.targets
    )


def _is_module_docstring_expression(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _is_trivial_init_module(tree: ast.Module) -> bool:
    for node in tree.body:
        if isinstance(node, ast.Import | ast.ImportFrom):
            continue
        if _is_dunder_assignment(node) or _is_module_docstring_expression(node):
            continue
        return False
    return True


def _strip_docstrings(tree: ast.Module) -> None:
    docstring_owners: list[ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef] = [
        tree
    ]
    docstring_owners.extend(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
    )
    for owner in docstring_owners:
        if owner.body and _is_module_docstring_expression(owner.body[0]):
            owner.body.pop(0)


def compute_producer_component_fingerprint(
    entry_modules: tuple[ModuleName, ...], schema_version: SchemaVersion
) -> ArtifactDigest:
    closure = resolve_producer_import_closure(entry_modules)
    normalized_pairs: list[tuple[ModuleName, AstDumpText]] = []
    for dotted, path in sorted(closure.items()):
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as error:
            raise ValueError(f"producer source {dotted} is syntactically invalid") from error
        if _has_dynamic_import(tree):
            raise ValueError(f"producer source {dotted} uses forbidden dynamic imports")
        if path.name == "__init__.py" and _is_trivial_init_module(tree):
            continue
        _strip_docstrings(tree)
        normalized_pairs.append(
            (dotted, ast.dump(tree, annotate_fields=True, include_attributes=False))
        )
    hasher = hashlib.sha256()
    for dotted, normalized_dump in normalized_pairs:
        hasher.update(framed_bytes(dotted, normalized_dump))
    hasher.update(framed_bytes(schema_version))
    return hasher.hexdigest()


def _imported_top_level_packages(tree: ast.Module) -> set[DependencyImportName]:
    packages: set[DependencyImportName] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                packages.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            packages.add(node.module.split(".")[0])
    return packages


def compute_cuda_environment_fingerprint() -> ArtifactDigest:
    if not torch.cuda.is_available():
        return hashlib.sha256(framed_bytes("cuda_unavailable")).hexdigest()
    major, minor = torch.cuda.get_device_capability(0)
    cudnn_version = torch.backends.cudnn.version()
    return hashlib.sha256(
        framed_bytes(
            torch.version.cuda or "cuda_version_unavailable",
            cudnn_version if cudnn_version is not None else 0,
            f"{major}.{minor}",
            torch.backends.cudnn.deterministic,
            torch.backends.cudnn.benchmark,
        )
    ).hexdigest()


def compute_external_dependency_fingerprint(
    entry_modules: tuple[ModuleName, ...],
    relevant_import_names: tuple[DependencyImportName, ...],
) -> ArtifactDigest:
    closure = resolve_producer_import_closure(entry_modules)
    imported_packages: set[DependencyImportName] = set()
    for path in closure.values():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported_packages |= _imported_top_level_packages(tree)
    actually_relevant = sorted(set(relevant_import_names) & imported_packages)
    hasher = hashlib.sha256()
    for import_name in actually_relevant:
        distribution_name = IMPORT_NAME_TO_DISTRIBUTION_NAME.get(import_name, import_name)
        version = importlib.metadata.version(distribution_name)
        hasher.update(framed_bytes(import_name, version))
    if "torch" in actually_relevant:
        hasher.update(framed_bytes(compute_cuda_environment_fingerprint()))
    return hasher.hexdigest()
