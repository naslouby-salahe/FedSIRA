from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas
import torch

from fedsira.config.schema import ScientificConfig
from fedsira.datasets.common import ROLE_HASH_TOKEN, Role
from fedsira.datasets.nbaiot.materialization import view_parquet_path
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_CLASS_ORDER,
    NBAIOT_DOMAIN_HASH_TOKEN,
    NBAIOT_DOMAIN_ORDER,
    NBaiotClass,
    NBaiotDomain,
)
from fedsira.domain.enums import SeedNamespace
from fedsira.domain.records import ArtifactDigest, CanonicalToken, DerivedSeed, MasterSeed
from fedsira.evaluation.metrics import (
    benign_false_alarm_rate,
    compute_confusion_counts_by_class,
    f1_for_class,
    macro_f1,
)
from fedsira.evaluation.records import MetricResult
from fedsira.experiments.registry import ReproducerCondition
from fedsira.learning.anchor import run_anchor_fedavg_training
from fedsira.learning.post_reference import run_post_reference_training
from fedsira.learning.scoring import logits_for_samples
from fedsira.models.mlp import (
    FedSIRAClassifier,
    flatten_trainable_parameters,
    load_flat_trainable_parameters,
)
from fedsira.runtime.determinism import (
    canonical_bytes,
    local_training_seed,
    namespace_seed,
    seed_job_local_rng_streams,
)

ANCHOR_TRAINING_ALGORITHM_TOKEN = "ANCHOR_FEDAVG"
REPRODUCTION_TRAINING_ALGORITHM_TOKEN = "REPRODUCTION"
CLEAN_TRAINING_CONDITION_TOKEN = ReproducerCondition.CLEAN.value


@dataclass(frozen=True)
class PreparedRows:
    sample_ids: tuple[ArtifactDigest, ...]
    features: tuple[tuple[float, ...], ...]
    labels: tuple[CanonicalToken, ...]

    @property
    def row_count(self) -> int:
        return len(self.sample_ids)


@dataclass(frozen=True)
class RealAnchor:
    input_width: int
    output_width: int
    flat_parameters: torch.Tensor
    dataset_manifest_hash: ArtifactDigest


@dataclass(frozen=True)
class DomainTargetMetrics:
    target_f1: MetricResult
    supported_macro_f1: MetricResult
    benign_far: MetricResult


def _view_key(domain: NBaiotDomain, class_id: NBaiotClass, role: Role) -> CanonicalToken:
    return f"{NBAIOT_DOMAIN_HASH_TOKEN[domain]}_{class_id.value}_{ROLE_HASH_TOKEN[role]}"


def real_evidence_available(prepared_root: Path) -> bool:
    return prepared_root.exists() and any(prepared_root.glob("*.parquet"))


def load_prepared_rows(
    prepared_root: Path, domain: NBaiotDomain, class_id: NBaiotClass, role: Role
) -> PreparedRows | None:
    path = view_parquet_path(prepared_root, _view_key(domain, class_id, role))
    if not path.exists():
        return None
    frame: pandas.DataFrame = pandas.read_parquet(path)
    if len(frame) == 0:
        return None
    feature_names = tuple(
        column for column in frame.columns if column not in ("sample_id", "label")
    )
    sample_ids = tuple(str(value) for value in frame["sample_id"])
    features = tuple(
        tuple(float(value) for value in row)
        for row in frame[list(feature_names)].itertuples(index=False)
    )
    labels = tuple(str(value) for value in frame["label"])
    return PreparedRows(sample_ids=sample_ids, features=features, labels=labels)


def dataset_manifest_hash(prepared_root: Path) -> ArtifactDigest:
    parquet_files = tuple(sorted(prepared_root.glob("*.parquet")))
    if not parquet_files:
        return "0" * 64
    hasher = hashlib.sha256()
    for path in parquet_files:
        hasher.update(canonical_bytes(path.name, path.stat().st_size))
    return hasher.hexdigest()


def _tensor_view(
    rows: PreparedRows | None,
) -> tuple[torch.Tensor, torch.Tensor, tuple[ArtifactDigest, ...]] | None:
    if rows is None:
        return None
    features = torch.tensor(rows.features, dtype=torch.float32)
    label_to_index = {class_id.value: index for index, class_id in enumerate(NBAIOT_CLASS_ORDER)}
    labels = torch.tensor([label_to_index[label] for label in rows.labels], dtype=torch.long)
    return features, labels, rows.sample_ids


def _training_seed(
    master_seed: MasterSeed,
    manifest_hash: ArtifactDigest,
    start_checkpoint_identity: ArtifactDigest,
    algorithm_token: CanonicalToken,
    domain: NBaiotDomain,
    round_index: int,
) -> DerivedSeed:
    local_training_namespace_seed = namespace_seed(master_seed, SeedNamespace.LOCAL_TRAINING)
    return local_training_seed(
        local_training_namespace_seed,
        manifest_hash,
        start_checkpoint_identity,
        algorithm_token,
        NBAIOT_DOMAIN_HASH_TOKEN[domain],
        CLEAN_TRAINING_CONDITION_TOKEN,
        round_index,
    )


def _flat_parameters_identity(flat_parameters: torch.Tensor) -> ArtifactDigest:
    return hashlib.sha256(flat_parameters.detach().cpu().numpy().tobytes()).hexdigest()


def train_anchor(
    prepared_root: Path, config: ScientificConfig, master_seed: MasterSeed
) -> RealAnchor | None:
    first_rows = load_prepared_rows(
        prepared_root, NBAIOT_DOMAIN_ORDER[0], NBaiotClass.BENIGN, Role.ANCHOR_TRAIN
    )
    if first_rows is None:
        return None
    input_width = len(first_rows.features[0])
    output_width = len(NBAIOT_CLASS_ORDER)
    manifest_hash = dataset_manifest_hash(prepared_root)
    initialization_seed = namespace_seed(master_seed, SeedNamespace.MODEL_INITIALIZATION)
    seed_job_local_rng_streams(initialization_seed)
    initial_state = FedSIRAClassifier(input_width, output_width).state_dict()
    clients_per_round: list[
        tuple[tuple[torch.Tensor, torch.Tensor, tuple[ArtifactDigest, ...], DerivedSeed], ...]
    ] = []
    for round_index in range(config.model.anchor_fedavg.rounds):
        round_clients: list[
            tuple[torch.Tensor, torch.Tensor, tuple[ArtifactDigest, ...], DerivedSeed]
        ] = []
        for domain in NBAIOT_DOMAIN_ORDER:
            combined_features: list[torch.Tensor] = []
            combined_labels: list[torch.Tensor] = []
            combined_sample_ids: list[ArtifactDigest] = []
            for class_id in NBAIOT_CLASS_ORDER:
                if class_id is NBaiotClass.GAFGYT_COMBO:
                    continue
                tensor_view = _tensor_view(
                    load_prepared_rows(prepared_root, domain, class_id, Role.ANCHOR_TRAIN)
                )
                if tensor_view is None:
                    continue
                features, labels, sample_ids = tensor_view
                combined_features.append(features)
                combined_labels.append(labels)
                combined_sample_ids.extend(sample_ids)
            if not combined_features:
                continue
            training_seed = _training_seed(
                master_seed,
                manifest_hash,
                "anchor-start",
                ANCHOR_TRAINING_ALGORITHM_TOKEN,
                domain,
                round_index,
            )
            round_clients.append(
                (
                    torch.cat(combined_features, dim=0),
                    torch.cat(combined_labels, dim=0),
                    tuple(combined_sample_ids),
                    training_seed,
                )
            )
        if not round_clients:
            return None
        clients_per_round.append(tuple(round_clients))
    final_state, _round_checkpoints = run_anchor_fedavg_training(
        input_width,
        output_width,
        initial_state,
        config.model.optimizer.anchor_and_standard_fl_learning_rate,
        config.model.optimizer,
        config.model.training,
        config.model.anchor_fedavg,
        clients_per_round,
    )
    model = FedSIRAClassifier(input_width, output_width)
    model.load_state_dict(final_state)
    return RealAnchor(
        input_width=input_width,
        output_width=output_width,
        flat_parameters=flatten_trainable_parameters(model),
        dataset_manifest_hash=manifest_hash,
    )


def _combined_post_reference_rows(
    prepared_root: Path, domain: NBaiotDomain, target_role: Role
) -> tuple[torch.Tensor, torch.Tensor, tuple[ArtifactDigest, ...], torch.Tensor] | None:
    target_tensor = _tensor_view(
        load_prepared_rows(prepared_root, domain, NBaiotClass.GAFGYT_COMBO, target_role)
    )
    if target_tensor is None:
        return None
    target_features, target_labels, target_sample_ids = target_tensor
    supported_features: list[torch.Tensor] = [target_features]
    supported_labels: list[torch.Tensor] = [target_labels]
    supported_sample_ids: list[ArtifactDigest] = list(target_sample_ids)
    is_supported: list[torch.Tensor] = [torch.zeros(target_features.shape[0], dtype=torch.bool)]
    for class_id in NBAIOT_CLASS_ORDER:
        if class_id is NBaiotClass.GAFGYT_COMBO:
            continue
        replay_tensor = _tensor_view(
            load_prepared_rows(prepared_root, domain, class_id, Role.POST_REFERENCE_REPLAY)
        )
        if replay_tensor is None:
            continue
        features, labels, sample_ids = replay_tensor
        supported_features.append(features)
        supported_labels.append(labels)
        supported_sample_ids.extend(sample_ids)
        is_supported.append(torch.ones(features.shape[0], dtype=torch.bool))
    return (
        torch.cat(supported_features, dim=0),
        torch.cat(supported_labels, dim=0),
        tuple(supported_sample_ids),
        torch.cat(is_supported, dim=0),
    )


def train_domain_reproduction_delta(
    prepared_root: Path,
    config: ScientificConfig,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    domain: NBaiotDomain,
) -> torch.Tensor | None:
    combined = _combined_post_reference_rows(prepared_root, domain, Role.REPRODUCTION)
    if combined is None:
        return None
    features, labels, sample_ids, is_supported = combined
    anchor_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(anchor_model, anchor.flat_parameters)
    current_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(current_model, anchor.flat_parameters)
    training_seed = _training_seed(
        master_seed,
        anchor.dataset_manifest_hash,
        _flat_parameters_identity(anchor.flat_parameters),
        REPRODUCTION_TRAINING_ALGORITHM_TOKEN,
        domain,
        -1,
    )
    seed_job_local_rng_streams(training_seed)
    optimizer = torch.optim.AdamW(
        current_model.parameters(),
        lr=config.model.optimizer.post_reference_learning_rate,
        betas=config.model.optimizer.betas,
        eps=config.model.optimizer.epsilon,
        weight_decay=config.model.optimizer.weight_decay,
    )
    loss_function = torch.nn.CrossEntropyLoss()
    run_post_reference_training(
        anchor_model,
        current_model,
        optimizer,
        loss_function,
        config.model.training,
        config.model.post_reference,
        features,
        labels,
        is_supported,
        sample_ids,
        training_seed,
        config.model.post_reference.local_epochs,
    )
    return flatten_trainable_parameters(current_model) - anchor.flat_parameters


def evaluate_domain(
    prepared_root: Path,
    anchor: RealAnchor,
    flat_parameters: torch.Tensor,
    domain: NBaiotDomain,
    role: Role,
) -> DomainTargetMetrics | None:
    true_labels: list[CanonicalToken] = []
    predicted_labels: list[CanonicalToken] = []
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, flat_parameters)
    model.eval()
    with torch.no_grad():
        for class_id in NBAIOT_CLASS_ORDER:
            rows = load_prepared_rows(prepared_root, domain, class_id, role)
            tensor_view = _tensor_view(rows)
            if tensor_view is None:
                continue
            features, _labels, _sample_ids = tensor_view
            logits = logits_for_samples(model, features)
            predictions = torch.argmax(logits, dim=-1)
            prediction_indices = tuple(int(value) for value in predictions.detach().cpu().numpy())
            true_labels.extend(class_id.value for _ in range(features.shape[0]))
            predicted_labels.extend(NBAIOT_CLASS_ORDER[index].value for index in prediction_indices)
    if not true_labels:
        return None
    class_tokens = tuple(class_id.value for class_id in NBAIOT_CLASS_ORDER)
    counts_by_class = compute_confusion_counts_by_class(true_labels, predicted_labels, class_tokens)
    f1_by_class = {token: f1_for_class(counts) for token, counts in counts_by_class.items()}
    supported_f1 = {
        token: f1_by_class[token]
        for token in class_tokens
        if token != NBaiotClass.GAFGYT_COMBO.value
    }
    return DomainTargetMetrics(
        target_f1=f1_by_class.get(NBaiotClass.GAFGYT_COMBO.value, MetricResult(None, 0)),
        supported_macro_f1=macro_f1(supported_f1),
        benign_far=benign_false_alarm_rate(true_labels, predicted_labels, NBaiotClass.BENIGN.value),
    )


def non_source_domains(source_domain: NBaiotDomain | None) -> tuple[NBaiotDomain, ...]:
    return tuple(domain for domain in NBAIOT_DOMAIN_ORDER if domain != source_domain)


def certified_domain_delta_committee(
    prepared_root: Path,
    config: ScientificConfig,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    domains: Sequence[NBaiotDomain],
) -> dict[NBaiotDomain, torch.Tensor]:
    deltas: dict[NBaiotDomain, torch.Tensor] = {}
    for domain in domains:
        delta = train_domain_reproduction_delta(prepared_root, config, master_seed, anchor, domain)
        if delta is not None:
            deltas[domain] = delta
    return deltas
