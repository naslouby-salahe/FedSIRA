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
    BooleanValue,
    DependencyImportName,
    FingerprintPayload,
    FrozenDomainModel,
    ModuleName,
    SchemaVersion,
)
from fedsira.runtime.determinism import framed_bytes


class DependencyDistributionBinding(FrozenDomainModel):
    import_name: DependencyImportName
    distribution_name: DependencyImportName


class ProducerFingerprintSpecification(FrozenDomainModel):
    family: ProducerFingerprintFamily
    entry_modules: tuple[ModuleName, ...]
    relevant_external_import_names: tuple[DependencyImportName, ...]


class ProducerModuleSource(FrozenDomainModel):
    module: ModuleName
    path: Path


DEPENDENCY_DISTRIBUTION_BINDINGS: tuple[DependencyDistributionBinding, ...] = (
    DependencyDistributionBinding(import_name="sklearn", distribution_name="scikit-learn"),
    DependencyDistributionBinding(import_name="yaml", distribution_name="pyyaml"),
)

PRODUCER_FINGERPRINT_SPECIFICATIONS: tuple[ProducerFingerprintSpecification, ...] = (
    ProducerFingerprintSpecification(
        family=ProducerFingerprintFamily.RAW_SCHEMA_EXCLUSION_MANIFEST,
        entry_modules=(),
        relevant_external_import_names=("pandas", "numpy"),
    ),
    ProducerFingerprintSpecification(
        family=ProducerFingerprintFamily.ROLE_SPLIT_SAMPLE_PREPARED_SCALER,
        entry_modules=(
            "fedsira.datasets.roles",
            "fedsira.datasets.sampling",
            "fedsira.datasets.scaling",
        ),
        relevant_external_import_names=("pandas", "numpy", "pyarrow"),
    ),
    ProducerFingerprintSpecification(
        family=ProducerFingerprintFamily.ANCHOR_FEDAVG_CHECKPOINTS,
        entry_modules=(
            "fedsira.models.mlp",
            "fedsira.learning.training",
            "fedsira.learning.federated",
            "fedsira.learning.anchor",
            "fedsira.runtime.determinism",
        ),
        relevant_external_import_names=("torch", "numpy"),
    ),
    ProducerFingerprintSpecification(
        family=ProducerFingerprintFamily.SOURCE_REPRODUCTION_CHECKPOINTS,
        entry_modules=(
            "fedsira.models.mlp",
            "fedsira.learning.training",
            "fedsira.learning.post_reference",
            "fedsira.runtime.determinism",
        ),
        relevant_external_import_names=("torch", "numpy"),
    ),
    ProducerFingerprintSpecification(
        family=ProducerFingerprintFamily.BASELINE_CHECKPOINT_CALIBRATION,
        entry_modules=("fedsira.baselines.registry", "fedsira.runtime.determinism"),
        relevant_external_import_names=("torch", "numpy", "scipy", "sklearn"),
    ),
    ProducerFingerprintSpecification(
        family=ProducerFingerprintFamily.MODEL_SCORES,
        entry_modules=("fedsira.models.mlp", "fedsira.learning.scoring"),
        relevant_external_import_names=("torch", "numpy"),
    ),
    ProducerFingerprintSpecification(
        family=ProducerFingerprintFamily.OPENING_VERIFIER_CERTIFICATE_SYNTHESIS_FINAL_GATE,
        entry_modules=("fedsira.evaluation.metrics", "fedsira.learning.aggregation"),
        relevant_external_import_names=("numpy", "scipy", "sklearn"),
    ),
    ProducerFingerprintSpecification(
        family=ProducerFingerprintFamily.BOUNDARY_TRANSFORMATION,
        entry_modules=("fedsira.datasets.sampling",),
        relevant_external_import_names=("numpy", "pandas", "pyarrow"),
    ),
    ProducerFingerprintSpecification(
        family=ProducerFingerprintFamily.METRIC_ARTIFACT,
        entry_modules=(
            "fedsira.evaluation.metrics",
            "fedsira.evaluation.aggregation",
            "fedsira.evaluation.validation",
        ),
        relevant_external_import_names=("numpy", "sklearn"),
    ),
    ProducerFingerprintSpecification(
        family=ProducerFingerprintFamily.STATISTICAL_COMPARISON_ARTIFACT,
        entry_modules=("fedsira.analysis.statistics", "fedsira.analysis.comparisons"),
        relevant_external_import_names=("numpy", "scipy", "statsmodels"),
    ),
    ProducerFingerprintSpecification(
        family=ProducerFingerprintFamily.CLAIM_STATE_ARTIFACT,
        entry_modules=("fedsira.analysis.claims", "fedsira.analysis.comparisons"),
        relevant_external_import_names=("numpy",),
    ),
    ProducerFingerprintSpecification(
        family=ProducerFingerprintFamily.REPORT_SOURCE_EXPORT,
        entry_modules=("fedsira.reporting",),
        relevant_external_import_names=("pandas", "pyarrow", "matplotlib"),
    ),
)


def producer_fingerprint_specification(
    family: ProducerFingerprintFamily,
) -> ProducerFingerprintSpecification:
    for specification in PRODUCER_FINGERPRINT_SPECIFICATIONS:
        if specification.family is family:
            return specification
    raise ValueError(f"unsupported producer fingerprint family: {family}")


def raw_schema_exclusion_manifest_entry_modules(
    dataset: DatasetId,
) -> tuple[ModuleName, ...]:
    if dataset is DatasetId.N_BAIOT:
        package: ModuleName = "nbaiot"
    elif dataset is DatasetId.CICIOT2023:
        package = "ciciot2023"
    else:
        raise ValueError(f"unsupported dataset identity: {dataset}")
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


def _is_type_checking_test(test: ast.expr) -> BooleanValue:
    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
        return True
    return isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"


def _type_checking_guarded_nodes(tree: ast.Module) -> set[ast.AST]:
    guarded: set[ast.AST] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and _is_type_checking_test(node.test):
            for statement in node.body:
                guarded.update(ast.walk(statement))
    return guarded


def _imported_fedsira_modules(tree: ast.Module) -> tuple[set[ModuleName], set[ModuleName]]:
    guarded_nodes = _type_checking_guarded_nodes(tree)
    certain: set[ModuleName] = set()
    speculative: set[ModuleName] = set()
    for node in ast.walk(tree):
        if node in guarded_nodes:
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


def _has_dynamic_import(tree: ast.Module) -> BooleanValue:
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
) -> tuple[ProducerModuleSource, ...]:
    resolved_names: set[ModuleName] = set()
    resolved_sources: list[ProducerModuleSource] = []
    frontier = list(entry_modules)
    while frontier:
        dotted = frontier.pop()
        if dotted in resolved_names:
            continue
        path = _module_file_path(dotted)
        resolved_names.add(dotted)
        resolved_sources.append(ProducerModuleSource(module=dotted, path=path))
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        certain, speculative = _imported_fedsira_modules(tree)
        frontier.extend(certain - resolved_names)
        for candidate in speculative - resolved_names:
            candidate_path = _try_module_file_path(candidate)
            if candidate_path is not None:
                frontier.append(candidate)
    return tuple(sorted(resolved_sources, key=lambda source: source.module))


def _is_dunder_assignment(node: ast.stmt) -> BooleanValue:
    if not isinstance(node, ast.Assign):
        return False
    return all(
        isinstance(target, ast.Name) and target.id.startswith("__") for target in node.targets
    )


def _is_module_docstring_expression(node: ast.stmt) -> BooleanValue:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _is_trivial_init_module(tree: ast.Module) -> BooleanValue:
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
    entry_modules: tuple[ModuleName, ...],
    schema_version: SchemaVersion,
) -> ArtifactDigest:
    closure = resolve_producer_import_closure(entry_modules)
    normalized_pairs: list[tuple[ModuleName, AstDumpText]] = []
    for source in closure:
        source_text = source.path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source_text, filename=str(source.path))
        except SyntaxError as error:
            raise ValueError(
                f"producer source {source.module} is syntactically invalid"
            ) from error
        if _has_dynamic_import(tree):
            raise ValueError(f"producer source {source.module} uses forbidden dynamic imports")
        if source.path.name == "__init__.py" and _is_trivial_init_module(tree):
            continue
        _strip_docstrings(tree)
        normalized_pairs.append(
            (
                source.module,
                ast.dump(tree, annotate_fields=True, include_attributes=False),
            )
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


def _distribution_name(import_name: DependencyImportName) -> DependencyImportName:
    for binding in DEPENDENCY_DISTRIBUTION_BINDINGS:
        if binding.import_name == import_name:
            return binding.distribution_name
    return import_name


def compute_external_dependency_fingerprint(
    entry_modules: tuple[ModuleName, ...],
    relevant_import_names: tuple[DependencyImportName, ...],
) -> ArtifactDigest:
    closure = resolve_producer_import_closure(entry_modules)
    imported_packages: set[DependencyImportName] = set()
    for source in closure:
        tree = ast.parse(
            source.path.read_text(encoding="utf-8"),
            filename=str(source.path),
        )
        imported_packages |= _imported_top_level_packages(tree)
    actually_relevant = sorted(set(relevant_import_names) & imported_packages)
    hasher = hashlib.sha256()
    for import_name in actually_relevant:
        version = importlib.metadata.version(_distribution_name(import_name))
        hasher.update(framed_bytes(import_name, version))
    if "torch" in actually_relevant:
        hasher.update(framed_bytes(compute_cuda_environment_fingerprint()))
    return hasher.hexdigest()
