# Pinned-library and custom-utility review

Scope: production utilities whose implementation could plausibly duplicate
behavior already provided by a pinned runtime dependency. Scientific rules are
not considered replaceable solely because a library has a similarly named
function.

| Area | Current implementation | Candidate dependency | Disposition |
|---|---|---|---|
| Large raw CSV discovery, projection, filtering, hashing, and Parquet materialization | N-BaIoT and CICIoT2023 adapters construct DuckDB relations and stream Parquet outputs. | pandas, pyarrow | Keep DuckDB. The CIC release is 17 GiB; materializing full frames would increase memory use and duplicate SQL already used for deterministic IDs, role assignment, and preparation. |
| Dataset identity, row IDs, sample ordering, and derived seeds | Shared framed SHA-256 and named seed derivation in `runtime.py` and dataset modules. | hashlib, NumPy | Keep the explicit framing and namespace rules; generic hashing or random helpers would not encode the locked identity contract. |
| Classification metrics | Scikit-learn supplies standard accuracy/F1/AUROC/AUPRC primitives where valid; FedSIRA handles undefined denominators, class support, and domain pooling. | scikit-learn, NumPy | Existing split is intentional: library primitives cover standard definitions; domain-specific aggregation and `NA` reasons remain explicit. |
| Paired inference, materiality, bootstrap, and type-7 quantiles | `evaluation/statistics.py` implements the locked exact sign-flip enumeration, deterministic seed bootstrap, and fixed quantile semantics; statsmodels supplies Holm adjustment. | SciPy, statsmodels, NumPy | Keep the explicit procedures. Replacing them with generic test/bootstrap defaults could alter pairing, sidedness, resampling unit, exact enumeration, or analysis-seed behavior. |
| Artifact schemas and validation | Pydantic domain models plus SHA-256 content/dependency identities and atomic publication in `artifacts/store.py`. | Pydantic, hashlib | Already uses the pinned validation and hashing primitives; custom code is the artifact lifecycle contract, not generic schema boilerplate. |
| Manuscript tables and figures | Python CSV writer and Matplotlib; NumPy only for rendering support. | pandas, Matplotlib, NumPy | Keep presentation-specific serialization and layout. No duplicate general-purpose chart or dataframe framework exists. |

No safely interchangeable custom general-purpose implementation was found in
this inventory. The remaining larger module-boundary and scientific-formula
duplication questions are tracked separately under ARCH-001 and ARCH-002.
