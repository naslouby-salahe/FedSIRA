import pandas

from fedsira.datasets.ciciot2023.preprocessing import (
    assign_pseudo_domains,
    compute_stable_row_id,
    resolve_predictor_columns,
)
from fedsira.datasets.ciciot2023.schema import PSEUDO_DOMAIN_COUNT


def test_compute_stable_row_id_is_a_sha256_hex_digest() -> None:
    digest = compute_stable_row_id("a/b.csv", "a" * 64, 0)
    assert len(digest) == 64
    bytes.fromhex(digest)


def test_compute_stable_row_id_changes_with_row_index() -> None:
    first = compute_stable_row_id("a/b.csv", "a" * 64, 0)
    second = compute_stable_row_id("a/b.csv", "a" * 64, 1)
    assert first != second


def test_resolve_predictor_columns_excludes_label_and_true_row_index() -> None:
    header = ("index", "feature_a", "feature_b", "Label")
    sample = pandas.DataFrame({"index": [0, 1, 2], "feature_a": [1.0, 2.0, 3.0]})
    predictors = resolve_predictor_columns(header, "Label", sample)
    assert predictors == ("feature_a", "feature_b")


def test_resolve_predictor_columns_keeps_a_non_sequential_index_like_column() -> None:
    header = ("index", "feature_a", "Label")
    sample = pandas.DataFrame({"index": [5, 1, 9]})
    predictors = resolve_predictor_columns(header, "Label", sample)
    assert "index" in predictors


def test_assign_pseudo_domains_returns_values_within_the_pseudo_domain_count() -> None:
    domains = assign_pseudo_domains("a" * 64, "BACKDOOR_MALWARE", ("b" * 64, "c" * 64), 730201)
    assert len(domains) == 2
    assert all(0 <= domain < PSEUDO_DOMAIN_COUNT for domain in domains)


def test_assign_pseudo_domains_is_deterministic() -> None:
    args = ("a" * 64, "BACKDOOR_MALWARE", ("b" * 64,), 730201)
    assert assign_pseudo_domains(*args) == assign_pseudo_domains(*args)
