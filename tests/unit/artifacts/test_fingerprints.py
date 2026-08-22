from fedsira.artifacts.fingerprints import compute_artifact_dependency_fingerprint


def fingerprint(
    schema_version: str = "1",
    scientific_configuration_subset: str = "config-a",
    dataset_split_view_identities: str = "dataset-a",
    semantic_coordinates_and_seed_namespaces: str = "coords-a",
    upstream_artifact_identities: tuple[str, ...] = ("a" * 64,),
    producer_component_fingerprint: str = "b" * 64,
    external_dependency_fingerprint: str = "c" * 64,
) -> str:
    return compute_artifact_dependency_fingerprint(
        schema_version,
        scientific_configuration_subset,
        dataset_split_view_identities,
        semantic_coordinates_and_seed_namespaces,
        upstream_artifact_identities,
        producer_component_fingerprint,
        external_dependency_fingerprint,
    )


def test_fingerprint_is_deterministic() -> None:
    assert fingerprint() == fingerprint()


def test_fingerprint_is_a_sha256_hex_digest() -> None:
    digest = fingerprint()
    assert len(digest) == 64
    bytes.fromhex(digest)


def test_fingerprint_changes_with_upstream_identity() -> None:
    assert fingerprint() != fingerprint(upstream_artifact_identities=("d" * 64,))


def test_fingerprint_changes_with_producer_component_fingerprint() -> None:
    assert fingerprint() != fingerprint(producer_component_fingerprint="f" * 64)


def test_fingerprint_changes_with_config_subset() -> None:
    assert fingerprint() != fingerprint(scientific_configuration_subset="config-b")


def test_fingerprint_changes_with_external_dependency_fingerprint() -> None:
    assert fingerprint() != fingerprint(external_dependency_fingerprint="e" * 64)


def test_fingerprint_is_unambiguously_length_prefixed_across_field_boundaries() -> None:
    combined = fingerprint(scientific_configuration_subset="ab", dataset_split_view_identities="")
    split = fingerprint(scientific_configuration_subset="a", dataset_split_view_identities="b")
    assert combined != split
