# FedSIRA Milestones

**Traceability:** Authoritative Roadmap → Roadmap Coverage Inventory → Milestones

The Roadmap Coverage Inventory is the primary milestone-allocation authority. This document allocates all 2,206 inventory requirements exactly once across eight dependency-ordered milestones: 2,051 implementation-bearing requirements and 155 `NON_IMPLEMENTATION` constraints. GitHub implementation issues and milestone-audit issues are intentionally unassigned.

## Milestone Index

| Milestone | Outcome boundary | Implementation-bearing requirements | Non-implementation constraints | Upstream milestone(s) |
|---|---|---:|---:|---|
| M01 — Scientific Configuration, Determinism, and Artifact Foundation | A schema-validated FedSIRA repository and deterministic, provenance-aware execution substrate exists with authoritative configuration, environment, artifact-DAG, recovery, and diagnostic CLI contracts. | 682 | 15 | None |
| M02 — Validated Dataset and Evidence-Role Preparation | N-BaIoT and CICIoT2023 raw inputs are validated and deterministically materialized into leak-free, checksum-traceable roles, splits, scalers, pseudo-domains, and evidence-feasibility artifacts. | 229 | 7 | M01 |
| M03 — Deterministic Model Training and Evaluation Core | The fixed model, anchor and post-reference training, scoring, metric, aggregation, and numerical-validation contracts execute deterministically from prepared evidence roles. | 202 | 2 | M01, M02 |
| M04 — FedSIRA Admission Protocol and Authority Path | The complete source-excluded FedSIRA authority path—claim opening, reproduction, external verification, synthesis, final fresh gate, state machine, and admission artifact—is implemented and invariant-validated. | 288 | 33 | M01, M02, M03 |
| M05 — Adversarial Mechanisms and Baseline Suite | All roadmap-defined attacks, stress transforms, and comparator/baseline methods are implemented under their fixed information, budget, calibration, and execution contracts and pass baseline implementation validation. | 252 | 10 | M01, M02, M03, M04 |
| M06 — Collapse Experiments and Resolved Core | The experiment planner/runner and inferential decision engine execute the four preregistered mechanism-collapse experiments and mechanically materialize the unique Resolved FedSIRA Core. | 183 | 12 | M01, M02, M03, M04, M05 |
| M07 — Confirmatory and Boundary Evidence Program | The Resolved FedSIRA Core is evaluated across the complete confirmatory, ablation, Byzantine robustness, failure-boundary, heterogeneity, delay, efficiency, and secondary-generalization program with complete terminal scientific records. | 103 | 15 | M06 |
| M08 — Claims, Reporting, and Reproducibility Closure | Verified experiment evidence is converted into mechanically derived claim states and manuscript tables/figures under project-completeness, provenance, scope, and third-party reproducibility gates. | 112 | 61 | M01, M06, M07 |

---

# M01 — Scientific Configuration, Determinism, and Artifact Foundation

> **Outcome:** A schema-validated FedSIRA repository and deterministic, provenance-aware execution substrate exists with authoritative configuration, environment, artifact-DAG, recovery, and diagnostic CLI contracts.

## At a Glance

| Field | Value |
|---|---|
| Roadmap scope | `Roadmap preamble; Configuration YAML and repository boundary; §§13–13.3, 19–20, 22–28 (foundation portions), 32 (authority/invalidation), 39 (provenance boundary), 40 (configuration-authority rationale), 43` |
| Requirement ownership | Implementation: REQ-0006; REQ-0591–REQ-0614; REQ-1028–REQ-1053; REQ-1055–REQ-1098; REQ-1100–REQ-1515; REQ-1517–REQ-1529; REQ-1565; REQ-1567–REQ-1576; REQ-1578–REQ-1580; REQ-1582–REQ-1657; REQ-1659–REQ-1660; REQ-1662–REQ-1693; REQ-1744–REQ-1759; REQ-2073–REQ-2077; REQ-2079–REQ-2080; REQ-2087–REQ-2088; REQ-2100–REQ-2103; REQ-2107–REQ-2110; REQ-2207<br>Constraints: REQ-0001–REQ-0002; REQ-1054; REQ-1099; REQ-1516; REQ-1566; REQ-1577; REQ-1581; REQ-1658; REQ-1661; REQ-1940; REQ-1946; REQ-2038; REQ-2078; REQ-2111 |
| Upstream milestones | `None` |
| Implementation issues | `I01`, `I02`, `I03`, `I04`, `I05`, `I06`, `I07`, `I08` |
| Coverage authority | `Roadmap Coverage Inventory` |
| Audit issue | None — no dedicated per-milestone audit issue; verified via `Milestone Audit.md` |
| Audit status | `PENDING` |

## Coverage

The Roadmap Coverage Inventory is the traceability authority for this milestone. Every requirement listed below has this milestone as its single primary milestone owner. `NON_IMPLEMENTATION` requirements are retained as scope, terminology, exclusion, methodological, or claim constraints and do not create fictitious implementation work.

| Roadmap Section | Scope / Work Package | Requirement IDs | Implementation Issue(s) | Verification / Evidence |
|---|---|---|---|---|
| Roadmap preamble; Configuration YAML; repository boundary | Authoritative configuration, project identity, and exact repository/component/output tree | REQ-0006; REQ-1096–REQ-1490; REQ-2087, REQ-2088; REQ-2107 | `I01`, `I02` | Typed immutable configuration/schema tests; exact-key/value checks; repository-tree/architecture checks; fixed-rule non-configurability checks. |
| §§13–13.3 | Master seeds, namespace derivation, canonical serialization, job-local RNG, deterministic ordering, and checkpointed RNG state | REQ-0591–REQ-0614 | `I03` | Hash/seed property tests reproduce exact uint32 values and orders; repeated isolated/parallel-safe jobs preserve semantic identity and RNG outcomes. |
| §§19–19.1 | Runtime timeout, failure classification, cell-phase state, retry, interruption, resume, and evidence-insufficiency semantics | REQ-1028–REQ-1060 | `I04` | Fault-injection and resume fixtures verify one allowed infrastructure retry, scientific-vs-technical outcomes, preserved phase identity, and nearest-valid-artifact recovery. |
| §20 | Reference OS/Python/PyTorch/CUDA/runtime determinism and environment capture | REQ-1061–REQ-1095; REQ-2100–REQ-2103; REQ-2207 | `I05` | Environment/doctor checks validate required versions and deterministic settings; reproducibility fixtures record hardware/runtime identity and detect material mismatches. |
| §§22–23; §§25–27 | Computational/result workspace boundaries, semantic cell identity, artifact DAG, fingerprints, validity/staleness, selective invalidation, reuse, provenance, and producer fingerprints | REQ-1491–REQ-1517; REQ-1565–REQ-1693; REQ-2108 | `I06`, `I07` | Artifact-path/schema and DAG/fingerprint tests exercise workspace boundaries, compatible reuse, material dependency changes, same-identity recomputation, stale-descendant exclusion, atomic publication, and producer/runtime lineage. |
| §§24–24.1; §28; §28.6 | Public `fedsira` command/doctor foundation plus generic serialization, provenance, invalidation, CLI-routing, replacement, recovery, and reuse validation | REQ-1518–REQ-1529; REQ-1744–REQ-1759; REQ-2109, REQ-2110 | `I08` | CLI end-to-end and deterministic unit/integration fixtures verify exact command identity, read-only diagnosis, blocker reporting, replacement/recovery behavior, and rejection of stale/corrupt/mismatched artifacts. |
| §43 | Configuration/observed-fact/derived-fact authority precedence and producer-adjacent dependency-scope rules | REQ-2073–REQ-2080 | `I08` | Schema and provenance tests prove fixed rules cannot become user configuration, raw facts come from manifests, derived facts are computed, and scope changes alter fingerprints. |
| Roadmap preamble; §§32, 39–40 | Cross-cutting scientific-authority, selective-invalidation, provenance-scope, and configuration-authority constraints | REQ-0001–REQ-0002; REQ-1940; REQ-1946; REQ-2038; REQ-2111 | `I01`, `I02`, `I07`, `I08` | Authority/invalidation audit proves roadmap/config inputs remain sole scientific authority, corrections use selective descendant invalidation, generic workflow provenance is not required, and rationale/reference material cannot create new configuration authority. |

### Coverage Rules

- Every mandatory requirement owned by this milestone must remain present in the Roadmap Coverage Inventory.
- Every mandatory implementation-bearing requirement must be mapped to at least one real implementation issue before implementation begins; issue-dependent fields remain `—` until that separate issue-creation phase.
- Every conditional requirement must remain traceable and must be implemented only when its roadmap-defined condition applies.
- Every mapped requirement must have objective verification or evidence consistent with the inventory acceptance-evidence contract.
- Every future implementation issue must reference the exact requirement IDs it satisfies.
- `NON_IMPLEMENTATION` requirements constrain scope, terminology, interpretation, exclusions, or claims but must not be converted into implementation tasks.
- A requirement is not considered covered merely because it falls inside a roadmap section or numeric range assigned to the milestone; the exact IDs in the Coverage table are authoritative for milestone allocation.
- No blocking requirement may remain `UNMAPPED` at the issue level or `AMBIGUOUS` when implementation begins.
- No issue may redefine, weaken, silently reinterpret, duplicate, or extend the authoritative roadmap requirement it implements.

## Dependencies

### Milestone Dependencies

| Milestone | Required Input / Contract | Entry Gate |
|---|---|---|
| `—` | No upstream milestone dependency. | `—` |

### Artifact / Interface Dependencies

| Dependency | Produced By | Required Validation |
|---|---|---|
| `—` | `—` | No upstream artifact/interface dependency. |

Dependency completion alone is not sufficient. Every consumed dependency must be present, valid, provenance-compatible where applicable, non-stale, and compatible with the active roadmap contract.

## Implementation Issues

Implementation issues for this milestone are listed below; each issue's detailed task checklist, acceptance criteria, and required tests are defined in `Issues.md`.

| Order | Issue | Work Package | Roadmap Scope | Requirement Coverage | Depends On |
|---:|---|---|---|---|---|
| 1 | `I01` — Establish FedSIRA Repository Architecture and Project Identity | Create the exact FedSIRA repository/component/workspace structure and project naming boundary that all later scientific code and artifacts rely on. | Roadmap preamble; Configuration YAML — repository boundary | 209 atomic requirements | None (foundational within this milestone chain) |
| 2 | `I02` — Implement Authoritative Immutable Scientific Configuration | Implement the complete authoritative `configs/fedsira.yaml` hierarchy, typed immutable schema, exact fixed values, cross-field validation, and scientific configuration ownership rules. | Configuration YAML; §40 | 193 atomic requirements | `I01` |
| 3 | `I03` — Implement Deterministic Seeds, Hashing, RNG, and Ordering | Implement master-seed namespaces, canonical hash/serialization semantics, job-local RNG ownership, deterministic ordering/ties, and checkpointable randomness. | §13; §13.1; §13.2; §13.3 | 24 atomic requirements | `I02` |
| 4 | `I04` — Implement Failure Classification, Phase State, Retry, and Resume Semantics | Implement scientific-versus-infrastructure failure classification, cell-phase state, bounded technical retry, interruption recovery, evidence insufficiency, and deterministic resume behavior. | §19; §19.1 | 33 atomic requirements | `I01`, `I02` |
| 5 | `I05` — Lock Runtime Environment, GPU Requirements, and Deterministic Execution | Enforce the roadmap reference software/hardware environment, dependency/runtime identity, deterministic PyTorch/CUDA settings, fail-fast hardware checks, and environment provenance. | §20 | 40 atomic requirements | `I01`, `I02` |
| 6 | `I06` — Implement Scientific Artifact DAG, Identity, Lifecycle, Reuse, and Invalidation | Implement workspace/result boundaries, semantic cell identity, scientific execution DAG, artifact families, validity/staleness, atomic publication, selective invalidation, reuse, overwrite, and recovery semantics. | §22; §23; §25; §26; §26.1; §26.2; §26.3; §26.4; §26.5; §26.6 | 124 atomic requirements | `I01`, `I02`, `I03`, `I04` |
| 7 | `I07` — Implement Provenance, Logging, and Producer Dependency Fingerprints | Implement producer-adjacent dependency fingerprints, canonical provenance, content digests, runtime/code lineage, and structured execution logging required for scientific reconstruction. | §27; §27.1; §39 | 34 atomic requirements | `I05`, `I06` |
| 8 | `I08` — Implement CLI Foundation, Doctor, and Generic Artifact Validation | Implement the public `fedsira` command foundation and read-only `doctor`, plus generic serialization, corruption, provenance, reuse, recovery, replacement, and authority-precedence validation. | §24; §24.1; §28.6; §28; §32; §43 | 40 atomic requirements | `I02`, `I05`, `I06`, `I07` |

### Issue Contract

Every milestone issue must:

- reference its exact roadmap section(s);
- list every covered requirement ID;
- contain a detailed implementation checklist;
- define objective acceptance criteria;
- identify required tests;
- identify required artifacts, outputs, or interfaces;
- identify required provenance or manifest updates where applicable;
- identify explicit dependencies on upstream milestones, issues, artifacts, or interfaces;
- preserve roadmap terminology and semantics;
- close only when every mapped requirement and acceptance criterion is satisfied.

## Deliverables

| Deliverable | Source Issue(s) | Required Validation | Downstream Consumer |
|---|---|---|---|
| Typed immutable `configs/fedsira.yaml` schema and resolved-configuration record | `I01`, `I02`, `I03`, `I04`, `I05`, `I06`, `I07`, `I08` | Schema validation passes; exact authoritative keys/values and non-configurable fixed rules are enforced | M02–M08 |
| Exact FedSIRA repository/workspace/results structure and public CLI/doctor foundation | `I01`, `I02`, `I03`, `I04`, `I05`, `I06`, `I07`, `I08` | Architecture and CLI routing tests pass; generated/scientific/read-only boundaries are enforced | M02–M08 |
| Canonical seed/hash/serialization and deterministic execution utilities | `I01`, `I02`, `I03`, `I04`, `I05`, `I06`, `I07`, `I08` | Property tests reproduce required seeds, hashes, orders, and isolated RNG behavior | M02–M08 |
| Reference-environment and dependency-lock provenance capture | `I01`, `I02`, `I03`, `I04`, `I05`, `I06`, `I07`, `I08` | Doctor/environment checks pass and material runtime identities are recorded | M02–M08 |
| Stage-scoped artifact DAG, fingerprints, validity/staleness, reuse, invalidation, and recovery machinery | `I01`, `I02`, `I03`, `I04`, `I05`, `I06`, `I07`, `I08` | DAG/recovery/invalidation fixtures pass with no blanket commit-based invalidation | M02–M08 |
| Foundation validation evidence | `I01`, `I02`, `I03`, `I04`, `I05`, `I06`, `I07`, `I08` | All M01-owned §28 and generic software/provenance tests pass | Milestone audit |

All roadmap-required deliverables for this milestone must appear in this table or be explicitly represented by the requirement-owned artifacts/evidence in the Roadmap Coverage Inventory.

## Entry Criteria

Implementation may begin only when all of the following are true:

- the authoritative Roadmap Coverage Inventory and supplied milestone template are available and internally consistent;
- the repository may be initialized without relying on any upstream milestone artifact.
- every required upstream artifact, interface, schema, manifest, or validation record exists and passes its applicable validation;
- consumed evidence is provenance-compatible and non-stale where provenance applies;
- all roadmap requirements owned by this milestone are present in the Roadmap Coverage Inventory;
- every mandatory implementation-bearing requirement has been assigned to at least one real milestone implementation issue;
- every mapped requirement has an explicit verification or evidence target;
- no blocking requirement is `UNMAPPED` at the issue level;
- no blocking requirement is `AMBIGUOUS`;
- no unresolved roadmap ambiguity would force the implementer to invent a scientific, mathematical, methodological, numerical, architectural, configuration, artifact, or execution decision.

## Exit Criteria

The milestone is complete only when all of the following are true:

- the exact project/configuration/repository authority boundaries are enforceable in code;
- deterministic seed, serialization, ordering, environment, and artifact identities are reproducible;
- stage-scoped artifact reuse, invalidation, staleness, atomic publication, interruption recovery, and diagnostic failure semantics pass their fixtures;
- `fedsira doctor` can diagnose configuration/environment/artifact readiness without modifying scientific state.
- every mandatory implementation-bearing requirement owned by this milestone is satisfied;
- every applicable conditional implementation-bearing requirement is satisfied;
- every relevant `NON_IMPLEMENTATION` constraint assigned to this milestone is demonstrably preserved;
- every mapped implementation issue is closed;
- the Roadmap Coverage Inventory contains no unresolved blocking coverage gap or `AMBIGUOUS` requirement owned by this milestone;
- all required unit, integration, numerical, structural, scientific, and failure-path validations for the owned requirements pass;
- all required deliverables are generated and all required artifacts, interfaces, schemas, manifests, and provenance records are complete, readable, checksum-valid, dependency-compatible, and non-stale;
- the milestone audit is `PASS` with no unresolved blocking finding.

## Acceptance Evidence

| Evidence Area | Required Evidence | Pass Condition |
|---|---|---|
| Requirement coverage | Roadmap Coverage Inventory plus this milestone's Coverage table | All 697 assigned requirements are accounted for exactly once in this milestone; all 682 implementation-bearing requirements have completed implementation evidence before audit. |
| Configuration and architecture | Typed-schema results, resolved configuration, repository-tree checks | All authoritative keys and fixed/non-configurable boundaries match the inventory; repository responsibilities exist exactly as required. |
| Determinism | Seed/hash/order/RNG reproducibility fixtures | Exact expected derivations and repeated semantic identities match across equivalent runs. |
| Environment | Doctor/environment manifest and dependency lock | Reference versions/settings are verified or an explicit blocker is reported. |
| Artifact DAG and provenance | Fingerprint, reuse, invalidation, staleness, atomic-publication, and recovery fixtures | Only material dependency changes invalidate affected descendants; compatible artifacts remain reusable and reconstructible. |
| CLI foundation | `fedsira`/`doctor` end-to-end results | Command identity/routing and read-only diagnosis behavior match the contract. |
| Foundation tests | M01-owned §28 test outputs | All required positive and intentionally invalid fixtures pass with exact expected outcomes. |
| Deliverables | Required milestone outputs and artifact manifests | Every listed deliverable is present, readable, valid, provenance-compatible, and suitable for its declared downstream consumer. |
| Audit | Milestone audit | Final result is `PASS` with no unresolved blocking findings. |

## Milestone Audit

**Audit issue:** `—`

**Status:** `PENDING`

The milestone audit is the final completion gate. It must independently verify:

- complete roadmap coverage for all requirements owned by the milestone;
- exact requirement-to-issue traceability once real implementation issues exist;
- closure of every mandatory implementation issue;
- completion and passing status of all required tests and validations;
- existence and validity of all required deliverables;
- completeness and validity of required provenance and manifests;
- absence of stale or incompatible evidence;
- preservation of all applicable `NON_IMPLEMENTATION` constraints;
- absence of unresolved blocking findings;
- readiness of milestone outputs for all declared downstream consumers.

The audit must end in exactly one result:

- `PASS` — every completion condition is satisfied.
- `FAIL` — one or more blocking conditions remain.

A milestone is not complete until the audit result is `PASS`.

## Scope Boundary

- This milestone implements only the roadmap implementation-bearing requirements explicitly assigned to it and preserves the `NON_IMPLEMENTATION` constraints explicitly assigned to it.
- The authoritative roadmap remains the source of scientific, mathematical, methodological, architectural, numerical, configuration, artifact, execution, reporting, and claim requirements.
- This milestone may organize implementation work but may not redefine, weaken, strengthen, extend, or silently reinterpret the roadmap.
- Detailed implementation checklists belong in future implementation issues.
- Detailed verification checklists belong in the future milestone audit issue.
- Work outside this milestone's mapped roadmap scope must not be added unless the roadmap or Roadmap Coverage Inventory is explicitly updated first.

---

# M02 — Validated Dataset and Evidence-Role Preparation

> **Outcome:** N-BaIoT and CICIoT2023 raw inputs are validated and deterministically materialized into leak-free, checksum-traceable roles, splits, scalers, pseudo-domains, and evidence-feasibility artifacts.

## At a Glance

| Field | Value |
|---|---|
| Roadmap scope | `§5.3 (secondary-data lock); §§9–11; §24.2; §28.1; §30.1; §32 (preprocess authority); §40 (dataset rationale)` |
| Requirement ownership | Implementation: REQ-0299–REQ-0350; REQ-0352–REQ-0370; REQ-0372–REQ-0375; REQ-0377–REQ-0472; REQ-0474–REQ-0501; REQ-0503–REQ-0509; REQ-1530–REQ-1536; REQ-1694–REQ-1705; REQ-1783–REQ-1786<br>Constraints: REQ-0137; REQ-0371; REQ-0510–REQ-0511; REQ-1941; REQ-2047–REQ-2048 |
| Upstream milestones | `M01` |
| Implementation issues | `I09`, `I10`, `I11`, `I12`, `I13` |
| Coverage authority | `Roadmap Coverage Inventory` |
| Audit issue | None — no dedicated per-milestone audit issue; verified via `Milestone Audit.md` |
| Audit status | `PENDING` |

## Coverage

The Roadmap Coverage Inventory is the traceability authority for this milestone. Every requirement listed below has this milestone as its single primary milestone owner. `NON_IMPLEMENTATION` requirements are retained as scope, terminology, exclusion, methodological, or claim constraints and do not create fictitious implementation work.

| Roadmap Section | Scope / Work Package | Requirement IDs | Implementation Issue(s) | Verification / Evidence |
|---|---|---|---|---|
| §9 | N-BaIoT acquisition identity, loader/layout recognition, domain/class registries, structural availability, target/support feasibility, and raw validation | REQ-0299–REQ-0350; REQ-0352–REQ-0370; REQ-0372–REQ-0375; REQ-0377 | `I09` | Raw-layout valid/invalid fixtures; exact SHA-256 inventory; canonical mapping and availability manifest; `Data Invalid` reasons; primary feasibility counts. |
| §10 | Primary stream ordering, role intervals/guard gaps, deterministic caps, sample IDs, predictor schema, leakage barriers, scaler, and preprocessing fingerprints | REQ-0378–REQ-0465 | `I10` | Deterministic split/cap/sample-ID/scaler fixtures; exact role/sample manifests; no leakage; finite 115-feature schema; identical rerun hashes. |
| §11 | CICIoT2023 validation, label/header canonicalization, predictor handling, deterministic pseudo-domains, role reuse, finite filtering, and fixed generalization preparation | REQ-0466–REQ-0472; REQ-0474–REQ-0501; REQ-0503–REQ-0509 | `I11` | Secondary raw/file/schema/label manifests; collision/nonfinite fixtures; pseudo-domain determinism; target/support availability and exact prepared-view hashes. |
| §24.2 | `fedsira preprocess` dataset selection, preprocessing materialization, reuse, failure, and status behavior | REQ-1530–REQ-1536 | `I12` | CLI end-to-end runs on valid, already-complete, stale, and invalid raw-input fixtures produce the prescribed artifacts/status without unrelated recomputation. |
| §28.1 | Dataset identity, checksums, canonical mapping, split/role/cap/scaler determinism, leakage, feasibility, and invalid-data tests | REQ-1694–REQ-1705 | `I13` | All required data/preprocessing tests pass; invalid fixtures fail closed with exact reason; reruns regenerate identical semantic artifacts. |
| §30.1 | `Data and Domain Evidence Validation` validation cell and blocking gate | REQ-1783–REQ-1786 | `I13` | One terminal validation record covers primary plus secondary preparation; required target-holder/reproducer/final-gate counts and leakage/schema/finite checks pass or block scientifically. |
| §5.3; §§9–11; §32; §40 | Dataset/preprocessing lock constraints: permitted secondary differences, fixed feasibility targets, no outcome-driven retuning, raw-byte authority, and dataset-role rationale | REQ-0137; REQ-0371; REQ-0510–REQ-0511; REQ-1941; REQ-2047–REQ-2048 | `I09`, `I11`, `I13` | Preprocess/data-validation records prove only permitted secondary differences are used, fixed targets/thresholds/pseudo-domain/role intervals are not outcome-retuned, observed facts come from validated raw bytes, and dataset-role rationales remain scope limits rather than new authority. |

### Coverage Rules

- Every mandatory requirement owned by this milestone must remain present in the Roadmap Coverage Inventory.
- Every mandatory implementation-bearing requirement must be mapped to at least one real implementation issue before implementation begins; issue-dependent fields remain `—` until that separate issue-creation phase.
- Every conditional requirement must remain traceable and must be implemented only when its roadmap-defined condition applies.
- Every mapped requirement must have objective verification or evidence consistent with the inventory acceptance-evidence contract.
- Every future implementation issue must reference the exact requirement IDs it satisfies.
- `NON_IMPLEMENTATION` requirements constrain scope, terminology, interpretation, exclusions, or claims but must not be converted into implementation tasks.
- A requirement is not considered covered merely because it falls inside a roadmap section or numeric range assigned to the milestone; the exact IDs in the Coverage table are authoritative for milestone allocation.
- No blocking requirement may remain `UNMAPPED` at the issue level or `AMBIGUOUS` when implementation begins.
- No issue may redefine, weaken, silently reinterpret, duplicate, or extend the authoritative roadmap requirement it implements.

## Dependencies

### Milestone Dependencies

| Milestone | Required Input / Contract | Entry Gate |
|---|---|---|
| M01 — Scientific Configuration, Determinism, and Artifact Foundation | Typed dataset configuration, canonical hashing/serialization, workspace/artifact schemas, provenance rules, and doctor/runtime contract | `Complete + audit PASS` |

### Artifact / Interface Dependencies

| Dependency | Produced By | Required Validation |
|---|---|---|
| Resolved authoritative configuration and fixed dataset-related constants | M01 | Typed-schema validation and configuration fingerprint match |
| Canonical hash/serialization and artifact-publication interfaces | M01 | Determinism/property tests and artifact schema validation pass |
| `data/raw` immutable input boundary and preprocessing workspace | M01 | Repository-boundary/immutability checks pass |

Dependency completion alone is not sufficient. Every consumed dependency must be present, valid, provenance-compatible where applicable, non-stale, and compatible with the active roadmap contract.

## Implementation Issues

Implementation issues for this milestone are listed below; each issue's detailed task checklist, acceptance criteria, and required tests are defined in `Issues.md`.

| Order | Issue | Work Package | Roadmap Scope | Requirement Coverage | Depends On |
|---:|---|---|---|---|---|
| 1 | `I09` — Validate N-BaIoT Raw Data, Domains, Classes, and Evidence Feasibility | Implement N-BaIoT raw release discovery, canonical mapping, checksums, domain/class registries, structural validation, target/support availability, and evidence-feasibility facts. | §9; §9.1; §9.1.1; §9.2; §9.3; §9.4; §9.5; §9.6 | 77 atomic requirements | `I08` |
| 2 | `I10` — Materialize Deterministic N-BaIoT Roles, Splits, Samples, and Scaling | Implement chronological role construction, guard gaps, deterministic caps/sample IDs, leakage barriers, predictor validation, scaling, manifests, and preprocessing fingerprints for the primary dataset. | §10; §10.1; §10.2; §10.3; §10.4; §10.5; §10.6 | 88 atomic requirements | `I03`, `I06`, `I09` |
| 3 | `I11` — Prepare CICIoT2023 Secondary Dataset and Deterministic Pseudo-Domains | Implement secondary raw/schema/label validation, canonicalization, finite predictor handling, deterministic pseudo-domain construction, role reuse, and fixed generalization preparation without retuning primary science. | §5.3; §11; §11.1; §11.2; §11.3; §40 | 47 atomic requirements | `I03`, `I06`, `I08` |
| 4 | `I12` — Implement Preprocess CLI and Provenance-Aware Dataset Materialization | Implement `fedsira preprocess` selection, materialization, overwrite/reuse, failure/status behavior, and production of validated dataset artifacts for both datasets. | §24.2 | 7 atomic requirements | `I08`, `I09`, `I10`, `I11` |
| 5 | `I13` — Implement Data and Domain Validation Test Gate | Implement the complete §28.1 dataset validation suite and the blocking `Data and Domain Evidence Validation` experiment/gate. | §28.1; §30.1; §32 | 17 atomic requirements | `I09`, `I10`, `I11`, `I12` |

### Issue Contract

Every milestone issue must:

- reference its exact roadmap section(s);
- list every covered requirement ID;
- contain a detailed implementation checklist;
- define objective acceptance criteria;
- identify required tests;
- identify required artifacts, outputs, or interfaces;
- identify required provenance or manifest updates where applicable;
- identify explicit dependencies on upstream milestones, issues, artifacts, or interfaces;
- preserve roadmap terminology and semantics;
- close only when every mapped requirement and acceptance criterion is satisfied.

## Deliverables

| Deliverable | Source Issue(s) | Required Validation | Downstream Consumer |
|---|---|---|---|
| Primary N-BaIoT raw identity, schema, domain, class, and availability manifests | `I09`, `I10`, `I11`, `I12`, `I13` | Raw checksums and observed facts validate against exact loader/mapping rules; discrepancies are explicitly recorded | M03–M07 |
| Primary prepared role/split/sample manifests and scaler artifact | `I09`, `I10`, `I11`, `I12`, `I13` | Intervals, guard gaps, caps, sample IDs, finite schema, scaling, and leakage checks pass deterministically | M03–M07 |
| Secondary CICIoT2023 raw/label/schema and pseudo-domain preparation artifacts | `I09`, `I10`, `I11`, `I12`, `I13` | Canonicalization, predictor, nonfinite, pseudo-domain, role, and target/support checks pass | M07 |
| Preprocessing feasibility and validation evidence | `I09`, `I10`, `I11`, `I12`, `I13` | `Data and Domain Evidence Validation` reaches a valid terminal state with exact evidence counts or correctly blocks | M03–M08 |
| `fedsira preprocess` execution evidence | `I09`, `I10`, `I11`, `I12`, `I13` | CLI produces/reuses only valid preprocessing descendants and reports exact blockers | Milestone audit |

All roadmap-required deliverables for this milestone must appear in this table or be explicitly represented by the requirement-owned artifacts/evidence in the Roadmap Coverage Inventory.

## Entry Criteria

Implementation may begin only when all of the following are true:

- M01 is complete and its milestone audit is `PASS`;
- required raw inputs are identifiable through the immutable `data/raw` boundary;
- dataset-related authoritative configuration resolves successfully.
- every required upstream artifact, interface, schema, manifest, or validation record exists and passes its applicable validation;
- consumed evidence is provenance-compatible and non-stale where provenance applies;
- all roadmap requirements owned by this milestone are present in the Roadmap Coverage Inventory;
- every mandatory implementation-bearing requirement has been assigned to at least one real milestone implementation issue;
- every mapped requirement has an explicit verification or evidence target;
- no blocking requirement is `UNMAPPED` at the issue level;
- no blocking requirement is `AMBIGUOUS`;
- no unresolved roadmap ambiguity would force the implementer to invent a scientific, mathematical, methodological, numerical, architectural, configuration, artifact, or execution decision.

## Exit Criteria

The milestone is complete only when all of the following are true:

- primary and secondary raw identities, schemas, labels/domains, availability, and checksums are validated from actual bytes;
- all role/split/cap/sample/scaler artifacts are deterministic, leak-free, checksum-valid, and provenance-compatible;
- primary confirmatory feasibility gates are satisfied or the program is correctly blocked as `Data Invalid`;
- `Data and Domain Evidence Validation` has its required terminal record.
- every mandatory implementation-bearing requirement owned by this milestone is satisfied;
- every applicable conditional implementation-bearing requirement is satisfied;
- every relevant `NON_IMPLEMENTATION` constraint assigned to this milestone is demonstrably preserved;
- every mapped implementation issue is closed;
- the Roadmap Coverage Inventory contains no unresolved blocking coverage gap or `AMBIGUOUS` requirement owned by this milestone;
- all required unit, integration, numerical, structural, scientific, and failure-path validations for the owned requirements pass;
- all required deliverables are generated and all required artifacts, interfaces, schemas, manifests, and provenance records are complete, readable, checksum-valid, dependency-compatible, and non-stale;
- the milestone audit is `PASS` with no unresolved blocking finding.

## Acceptance Evidence

| Evidence Area | Required Evidence | Pass Condition |
|---|---|---|
| Requirement coverage | Roadmap Coverage Inventory plus this milestone's Coverage table | All 236 assigned requirements are accounted for exactly once in this milestone; all 229 implementation-bearing requirements have completed implementation evidence before audit. |
| Raw-data identity | File/archive SHA-256 manifests and canonical mapping inventories | Every consumed raw file/shard is identified; unknown/ambiguous/corrupt mappings fail with the prescribed `Data Invalid` reason. |
| Prepared roles and leakage | Split/role/sample manifests and leakage audit | Role intervals, guard gaps, freshness/disjointness, caps, and sample identities match the fixed contract with no forbidden reuse. |
| Feature/scaler integrity | Schema registry and scaler artifact | Primary predictor registry is valid and finite; scaling uses only permitted anchor data and reproduces identical hashes. |
| Secondary preparation | CICIoT2023 schema/label/pseudo-domain manifests | Canonical target/support labels and deterministic pseudo-domains are valid without retuning primary semantics. |
| Feasibility gate | `Data and Domain Evidence Validation` terminal record | All roadmap-defined primary evidence-count gates pass; otherwise downstream scientific execution is blocked. |
| Preprocess CLI/tests | CLI logs/status plus §28.1 test results | All valid and intentionally invalid preprocessing fixtures behave exactly as specified. |
| Deliverables | Required milestone outputs and artifact manifests | Every listed deliverable is present, readable, valid, provenance-compatible, and suitable for its declared downstream consumer. |
| Audit | Milestone audit | Final result is `PASS` with no unresolved blocking findings. |

## Milestone Audit

**Audit issue:** `—`

**Status:** `PENDING`

The milestone audit is the final completion gate. It must independently verify:

- complete roadmap coverage for all requirements owned by the milestone;
- exact requirement-to-issue traceability once real implementation issues exist;
- closure of every mandatory implementation issue;
- completion and passing status of all required tests and validations;
- existence and validity of all required deliverables;
- completeness and validity of required provenance and manifests;
- absence of stale or incompatible evidence;
- preservation of all applicable `NON_IMPLEMENTATION` constraints;
- absence of unresolved blocking findings;
- readiness of milestone outputs for all declared downstream consumers.

The audit must end in exactly one result:

- `PASS` — every completion condition is satisfied.
- `FAIL` — one or more blocking conditions remain.

A milestone is not complete until the audit result is `PASS`.

## Scope Boundary

- This milestone implements only the roadmap implementation-bearing requirements explicitly assigned to it and preserves the `NON_IMPLEMENTATION` constraints explicitly assigned to it.
- The authoritative roadmap remains the source of scientific, mathematical, methodological, architectural, numerical, configuration, artifact, execution, reporting, and claim requirements.
- This milestone may organize implementation work but may not redefine, weaken, strengthen, extend, or silently reinterpret the roadmap.
- Detailed implementation checklists belong in future implementation issues.
- Detailed verification checklists belong in the future milestone audit issue.
- Work outside this milestone's mapped roadmap scope must not be added unless the roadmap or Roadmap Coverage Inventory is explicitly updated first.

---

# M03 — Deterministic Model Training and Evaluation Core

> **Outcome:** The fixed model, anchor and post-reference training, scoring, metric, aggregation, and numerical-validation contracts execute deterministically from prepared evidence roles.

## At a Glance

| Field | Value |
|---|---|
| Roadmap scope | `§3 (latency metrics); §12; §17; §§28.2, 28.5` |
| Requirement ownership | Implementation: REQ-0077; REQ-0512–REQ-0533; REQ-0535–REQ-0590; REQ-0834–REQ-0880; REQ-0882–REQ-0930; REQ-1706–REQ-1714; REQ-1736–REQ-1743; REQ-2090–REQ-2099<br>Constraints: REQ-0534; REQ-0881 |
| Upstream milestones | `M01, M02` |
| Implementation issues | `I14`, `I15`, `I16`, `I17`, `I18` |
| Coverage authority | `Roadmap Coverage Inventory` |
| Audit issue | None — no dedicated per-milestone audit issue; verified via `Milestone Audit.md` |
| Audit status | `PENDING` |

## Coverage

The Roadmap Coverage Inventory is the traceability authority for this milestone. Every requirement listed below has this milestone as its single primary milestone owner. `NON_IMPLEMENTATION` requirements are retained as scope, terminology, exclusion, methodological, or claim constraints and do not create fictitious implementation work.

| Roadmap Section | Scope / Work Package | Requirement IDs | Implementation Issue(s) | Verification / Evidence |
|---|---|---|---|---|
| §§12–12.2 | Fixed model architecture, initialization, loss, AdamW, batching, precision, clipping, optimizer lifecycle, and no-best-checkpoint contract | REQ-0512–REQ-0533; REQ-0535–REQ-0558; REQ-2094–REQ-2098 | `I14` | Architecture/parameter-count tests plus deterministic one-batch/short-run training fixtures verify exact constants, float modes, optimizer semantics, and finite outputs. |
| §§12.3–12.6 | Anchor FedAvg, source candidate, honest reproduction objective/budgets, canonical parameter vector, attack override boundary, and forbidden evaluation-role training access | REQ-0559–REQ-0590; REQ-2099 | `I15` | Deterministic anchor/post-reference fixtures verify start checkpoints, data roles, objective terms, per-round optimizer reset, checkpoints, parameter order, and fail-closed role access. |
| §3; §§17–17.4 | Canonical admission-delay components plus confusion-derived utility, equal-domain aggregation, target/support/benign, admission/certification, and attack-rate metric definitions | REQ-0077; REQ-0834–REQ-0873; REQ-2090–REQ-2093 | `I16` | Hand-calculated labels/predictions and timing fixtures assert exact numerators, denominators, units, orientation, aggregation order, structural `NA`, and full-precision persistence. |
| §§17.5–17.8 | Security, liveness, source-exclusion, backdoor, verifier, timing/resource and protocol-specific evaluation semantics | REQ-0874–REQ-0917 | `I17` | Fixed prediction/protocol fixtures produce exact ASR/MAR/LAR, worst-domain, certificate/admission, timing/resource, and final-gate/report-test behavior. |
| §§17.9–17.10 | Defined-domain thresholds, `NA`/Dormant/Abstain handling, matched-clean references, false-equivalence diagnostics, and descriptive uncertainty inputs | REQ-0918–REQ-0930 | `I16`, `I17` | Boundary fixtures verify zero-denominator `NA`, minimum defined-domain counts, matched-reference identity, stored numerators/denominators, and no pseudoreplication. |
| §§28.2, 28.5 | Model/training numerical checks and hand-calculated metric/statistical-unit tests | REQ-1706–REQ-1714; REQ-1736–REQ-1743 | `I18` | All forward/backward, checkpoint, deterministic training, confusion-metric, aggregation, zero-denominator, and numerical fixtures pass. |
| §12.1 | Model-specification constraint preventing scientifically consequential PyTorch defaults from being inherited implicitly | REQ-0534 | `I14` | Model-construction/architecture evidence shows every scientifically consequential Section 12 layer setting is explicit rather than inherited from unspecified PyTorch defaults. |

### Coverage Rules

- Every mandatory requirement owned by this milestone must remain present in the Roadmap Coverage Inventory.
- Every mandatory implementation-bearing requirement must be mapped to at least one real implementation issue before implementation begins; issue-dependent fields remain `—` until that separate issue-creation phase.
- Every conditional requirement must remain traceable and must be implemented only when its roadmap-defined condition applies.
- Every mapped requirement must have objective verification or evidence consistent with the inventory acceptance-evidence contract.
- Every future implementation issue must reference the exact requirement IDs it satisfies.
- `NON_IMPLEMENTATION` requirements constrain scope, terminology, interpretation, exclusions, or claims but must not be converted into implementation tasks.
- A requirement is not considered covered merely because it falls inside a roadmap section or numeric range assigned to the milestone; the exact IDs in the Coverage table are authoritative for milestone allocation.
- No blocking requirement may remain `UNMAPPED` at the issue level or `AMBIGUOUS` when implementation begins.
- No issue may redefine, weaken, silently reinterpret, duplicate, or extend the authoritative roadmap requirement it implements.

## Dependencies

### Milestone Dependencies

| Milestone | Required Input / Contract | Entry Gate |
|---|---|---|
| M01 — Scientific Configuration, Determinism, and Artifact Foundation | Model/training configuration, seed derivation, artifact/checkpoint schemas, deterministic runtime | `Complete + audit PASS` |
| M02 — Validated Dataset and Evidence-Role Preparation | Prepared role views, sample identities, feature/class schemas, scaler, and data-feasibility evidence | `Complete + audit PASS` |

### Artifact / Interface Dependencies

| Dependency | Produced By | Required Validation |
|---|---|---|
| Prepared primary/secondary data views, split/role manifests, and scaler | M02 | Checksum-valid, leak-free, schema-valid, provenance-compatible |
| Resolved model/training configuration and job-local deterministic seed interface | M01 | Configuration fingerprint and seed derivation tests pass |
| Checkpoint/artifact publication and provenance interfaces | M01 | Atomic publication, identity, dependency, and recovery validation pass |

Dependency completion alone is not sufficient. Every consumed dependency must be present, valid, provenance-compatible where applicable, non-stale, and compatible with the active roadmap contract.

## Implementation Issues

Implementation issues for this milestone are listed below; each issue's detailed task checklist, acceptance criteria, and required tests are defined in `Issues.md`.

| Order | Issue | Work Package | Roadmap Scope | Requirement Coverage | Depends On |
|---:|---|---|---|---|---|
| 1 | `I14` — Implement Fixed Model Architecture and Training Primitives | Implement the exact classifier architecture, initialization, loss, AdamW, batching, precision, clipping, optimizer lifecycle, parameter representation, and prohibition on implicit consequential defaults. | §12; §12.1; §12.2 | 52 atomic requirements | `I02`, `I03`, `I05`, `I13` |
| 2 | `I15` — Implement Anchor, Source, and Independent Reproduction Training | Implement deterministic anchor FedAvg, post-reference source candidate training, honest reproduction from anchor/non-source evidence, fixed budgets/objectives, malicious-training override boundary, and no test-role tuning. | §12.3; §12.4; §12.5; §12.6 | 33 atomic requirements | `I06`, `I10`, `I11`, `I14` |
| 3 | `I16` — Implement Core Classification, Capability, Security, and Admission Metrics | Implement confusion-derived classification metrics, target/support/benign contract metrics, equal-domain aggregation, admission/certification rates, backdoor/security metrics, and canonical delay components. | §3; §17.1; §17; §17.2; §17.3; §17.4; §17.10 | 52 atomic requirements | `I02`, `I10`, `I14` |
| 4 | `I17` — Implement Screening, Distribution, Delay, Efficiency, and Missing-Metric Semantics | Implement candidate-screen, cross-domain distribution, delay/resource/communication metrics, evaluation populations, matched-clean references, NA/undefined handling, false-equivalence diagnostics, and descriptive uncertainty inputs. | §17.5; §17.6; §17.7; §17.8; §17.9 | 50 atomic requirements | `I06`, `I16` |
| 5 | `I18` — Validate Model, FL, Metric, and Statistical Numerics | Implement deterministic model/training numerical tests and hand-calculated metric/statistical validation required by §§28.2 and 28.5. | §28.2; §28.5 | 17 atomic requirements | `I14`, `I15`, `I16`, `I17` |

### Issue Contract

Every milestone issue must:

- reference its exact roadmap section(s);
- list every covered requirement ID;
- contain a detailed implementation checklist;
- define objective acceptance criteria;
- identify required tests;
- identify required artifacts, outputs, or interfaces;
- identify required provenance or manifest updates where applicable;
- identify explicit dependencies on upstream milestones, issues, artifacts, or interfaces;
- preserve roadmap terminology and semantics;
- close only when every mapped requirement and acceptance criterion is satisfied.

## Deliverables

| Deliverable | Source Issue(s) | Required Validation | Downstream Consumer |
|---|---|---|---|
| Fixed model implementation and architecture/parameter registry | `I14`, `I15`, `I16`, `I17`, `I18` | Architecture and initialization tests match the roadmap-defined shape/defaults exactly | M04–M07 |
| Authoritative anchor checkpoints and training manifests | `I14`, `I15`, `I16`, `I17`, `I18` | FedAvg rounds, client weighting, validation, final-checkpoint selection, seeds, optimizer/RNG recovery, and target exclusion validate | M04–M07 |
| Source-candidate and honest-reproduction training engine | `I14`, `I15`, `I16`, `I17`, `I18` | Objective, budgets, role restrictions, parameter ordering, source firewall, and checkpoint manifests pass deterministic fixtures | M04–M07 |
| Scoring/evaluation and metric library with full-precision machine-readable records | `I14`, `I15`, `I16`, `I17`, `I18` | Hand-computed metric, aggregation, missingness, and protocol-specific evaluation tests pass | M04–M08 |
| Model/metric numerical validation evidence | `I14`, `I15`, `I16`, `I17`, `I18` | All M03-owned §28 fixtures pass with finite and deterministic outputs | Milestone audit |

All roadmap-required deliverables for this milestone must appear in this table or be explicitly represented by the requirement-owned artifacts/evidence in the Roadmap Coverage Inventory.

## Entry Criteria

Implementation may begin only when all of the following are true:

- M01 and M02 are complete and their milestone audits are `PASS`;
- prepared datasets, feature/class registries, role manifests, scaler identities, and evidence-feasibility artifacts are valid;
- the deterministic training/runtime configuration and seed interfaces are available.
- every required upstream artifact, interface, schema, manifest, or validation record exists and passes its applicable validation;
- consumed evidence is provenance-compatible and non-stale where provenance applies;
- all roadmap requirements owned by this milestone are present in the Roadmap Coverage Inventory;
- every mandatory implementation-bearing requirement has been assigned to at least one real milestone implementation issue;
- every mapped requirement has an explicit verification or evidence target;
- no blocking requirement is `UNMAPPED` at the issue level;
- no blocking requirement is `AMBIGUOUS`;
- no unresolved roadmap ambiguity would force the implementer to invent a scientific, mathematical, methodological, numerical, architectural, configuration, artifact, or execution decision.

## Exit Criteria

The milestone is complete only when all of the following are true:

- the fixed model and all training paths execute with exact roadmap-defined numerical semantics;
- the authoritative anchor and post-reference update artifacts are deterministic and recoverable;
- training APIs cannot consume forbidden fresh-evaluation roles or source artifacts on honest reproduction paths;
- all required metrics and aggregation/missingness rules are numerically verified and machine-readable.
- every mandatory implementation-bearing requirement owned by this milestone is satisfied;
- every applicable conditional implementation-bearing requirement is satisfied;
- every relevant `NON_IMPLEMENTATION` constraint assigned to this milestone is demonstrably preserved;
- every mapped implementation issue is closed;
- the Roadmap Coverage Inventory contains no unresolved blocking coverage gap or `AMBIGUOUS` requirement owned by this milestone;
- all required unit, integration, numerical, structural, scientific, and failure-path validations for the owned requirements pass;
- all required deliverables are generated and all required artifacts, interfaces, schemas, manifests, and provenance records are complete, readable, checksum-valid, dependency-compatible, and non-stale;
- the milestone audit is `PASS` with no unresolved blocking finding.

## Acceptance Evidence

| Evidence Area | Required Evidence | Pass Condition |
|---|---|---|
| Requirement coverage | Roadmap Coverage Inventory plus this milestone's Coverage table | All 204 assigned requirements are accounted for exactly once in this milestone; all 202 implementation-bearing requirements have completed implementation evidence before audit. |
| Model architecture | Architecture/initialization/parameter-count fixtures | Exact layer/parameter/default contract is satisfied with no implicit scientifically consequential defaults. |
| Training determinism | Anchor/source/reproduction training manifests and repeated-run hashes | Same authoritative inputs/seeds produce matching checkpoints/updates within roadmap tolerance and recoverable optimizer/RNG state. |
| Training firewalls | Forbidden-role/source-input tests | Row Verification, Final Gate, Report Test, and prohibited source artifacts are rejected by the relevant training API. |
| Metric correctness | Hand-calculated metric fixtures | Numerators, denominators, orientation, aggregation and `NA` semantics match exact expected values. |
| Evaluation records | Machine-readable score/evaluation artifacts | Populations, sample identities, full-precision metrics and structural outcomes are complete and provenance-linked. |
| Numerical tests | M03-owned §28 results | All required finite forward/backward, training, and metric tests pass. |
| Deliverables | Required milestone outputs and artifact manifests | Every listed deliverable is present, readable, valid, provenance-compatible, and suitable for its declared downstream consumer. |
| Audit | Milestone audit | Final result is `PASS` with no unresolved blocking findings. |

## Milestone Audit

**Audit issue:** `—`

**Status:** `PENDING`

The milestone audit is the final completion gate. It must independently verify:

- complete roadmap coverage for all requirements owned by the milestone;
- exact requirement-to-issue traceability once real implementation issues exist;
- closure of every mandatory implementation issue;
- completion and passing status of all required tests and validations;
- existence and validity of all required deliverables;
- completeness and validity of required provenance and manifests;
- absence of stale or incompatible evidence;
- preservation of all applicable `NON_IMPLEMENTATION` constraints;
- absence of unresolved blocking findings;
- readiness of milestone outputs for all declared downstream consumers.

The audit must end in exactly one result:

- `PASS` — every completion condition is satisfied.
- `FAIL` — one or more blocking conditions remain.

A milestone is not complete until the audit result is `PASS`.

## Scope Boundary

- This milestone implements only the roadmap implementation-bearing requirements explicitly assigned to it and preserves the `NON_IMPLEMENTATION` constraints explicitly assigned to it.
- The authoritative roadmap remains the source of scientific, mathematical, methodological, architectural, numerical, configuration, artifact, execution, reporting, and claim requirements.
- This milestone may organize implementation work but may not redefine, weaken, strengthen, extend, or silently reinterpret the roadmap.
- Detailed implementation checklists belong in future implementation issues.
- Detailed verification checklists belong in the future milestone audit issue.
- Work outside this milestone's mapped roadmap scope must not be added unless the roadmap or Roadmap Coverage Inventory is explicitly updated first.

---

# M04 — FedSIRA Admission Protocol and Authority Path

> **Outcome:** The complete source-excluded FedSIRA authority path—claim opening, reproduction, external verification, synthesis, final fresh gate, state machine, and admission artifact—is implemented and invariant-validated.

## At a Glance

| Field | Value |
|---|---|
| Roadmap scope | `Roadmap preamble (source-authority principle); §§1.1–1.3; §§3–8 (implementation/threat-model portions); §§13.4–13.9; §14; §24.4; §§28.3–28.4; §30.2; §40 (Krum rationale)` |
| Requirement ownership | Implementation: REQ-0007–REQ-0017; REQ-0060; REQ-0062–REQ-0076; REQ-0079; REQ-0081–REQ-0086; REQ-0094–REQ-0096; REQ-0099–REQ-0106; REQ-0118–REQ-0136; REQ-0139–REQ-0153; REQ-0155–REQ-0195; REQ-0197–REQ-0227; REQ-0229–REQ-0240; REQ-0242–REQ-0265; REQ-0268–REQ-0280; REQ-0282–REQ-0283; REQ-0285–REQ-0288; REQ-0291–REQ-0295; REQ-0615; REQ-0617; REQ-0619–REQ-0637; REQ-0639–REQ-0647; REQ-0649–REQ-0668; REQ-1541; REQ-1543–REQ-1544; REQ-1715–REQ-1735; REQ-1787–REQ-1789<br>Constraints: REQ-0003–REQ-0005; REQ-0061; REQ-0078; REQ-0080; REQ-0087–REQ-0093; REQ-0097; REQ-0154; REQ-0228; REQ-0266–REQ-0267; REQ-0281; REQ-0284; REQ-0296–REQ-0297; REQ-0616; REQ-0618; REQ-0638; REQ-0648; REQ-1542; REQ-2049; REQ-2081–REQ-2085 |
| Upstream milestones | `M01, M02, M03` |
| Implementation issues | `I19`, `I20`, `I21`, `I22`, `I23`, `I24`, `I25`, `I26` |
| Coverage authority | `Roadmap Coverage Inventory` |
| Audit issue | None — no dedicated per-milestone audit issue; verified via `Milestone Audit.md` |
| Audit status | `PENDING` |

## Coverage

The Roadmap Coverage Inventory is the traceability authority for this milestone. Every requirement listed below has this milestone as its single primary milestone owner. `NON_IMPLEMENTATION` requirements are retained as scope, terminology, exclusion, methodological, or claim constraints and do not create fictitious implementation work.

Stable-ID note: the explicit `REQ-0240` / `REQ-0242` split is intentional. Preserved gap `REQ-0241` reflects the repeated `h_V=1` restatement already covered by `REQ-0074`, so no M04 protocol requirement is omitted.

| Roadmap Section | Scope / Work Package | Requirement IDs | Implementation Issue(s) | Verification / Evidence |
|---|---|---|---|---|
| §1.3; §§5–6 | Immutable Capability Claim Contract, evidence minima, state vocabulary/transitions, attempt consumption, dormancy/resume/expiry, source exclusion, final-gate and resolved-path invariants | REQ-0007–REQ-0017; REQ-0118–REQ-0136; REQ-0139–REQ-0153; REQ-0155–REQ-0195 | `I19` | State-machine and boundary fixtures exercise every transition, success/failure threshold, consumed/unconsumed attempt, terminal/resumable state, and exact protocol record. |
| §§3–4; §8 | FedSIRA notation and authority math, authenticated nine-domain federation roles, Byzantine bounds/pre-commitment secrecy, verifier/Krum admissibility, information-limit propositions, source-noninterference graph property, delay decomposition, and diagnostic committee probability | REQ-0060; REQ-0062–REQ-0076; REQ-0079; REQ-0081–REQ-0086; REQ-0094–REQ-0096; REQ-0099–REQ-0106; REQ-0280; REQ-0282, REQ-0283; REQ-0285–REQ-0288; REQ-0291–REQ-0295 | `I20`, `I23` | Role/threat and hand-calculated/property fixtures verify source/reproducer/verifier exclusions, private fresh evidence, one-vote accounting, formulas/counts/bounds, `1/7` diagnostic probability, Krum admissibility, and source-edge exclusion. |
| §§7.1–7.2; §§13.4–13.5 | Proposal-assisted and candidate-free opening, deterministic source/screen order, cross-fold matched-control screen, differential calculation, adequacy and opening/rejection/dormancy rules | REQ-0197–REQ-0227; REQ-0615; REQ-0617; REQ-0619–REQ-0628 | `I21` | Deterministic screen fixtures reproduce folds, type-7 deciles, matching/ties, ΔM/ΔC/A, threshold boundaries, source-zero-weight commitment, and exact opening state. |
| §§7.3–7.5; §§13.6–13.9 | Honest reproduction commitment, verifier-panel assignment, Positive/Negative/Abstain votes, certification, row consumption/order, five-row committee, Byzantine/random diagnostic assignment rules | REQ-0229–REQ-0240; REQ-0242–REQ-0256; REQ-0629–REQ-0637; REQ-0639–REQ-0647 | `I22`, `I23` | Training/commitment/panel fixtures verify post-commitment timestamps, exclusions, 3-panel/2-positive semantics, inadequate-panel failure, deterministic order, and first-five certified-row behavior. |
| §§7.6–7.7 | Krum `n=5,f_R=1`, canonical distances/ties, source-free production update, single-row mapping, production model, final fresh-gate adequacy/predicates/outcomes | REQ-0257–REQ-0265; REQ-0268–REQ-0279 | `I24`, `I25` | Hand-computed Krum vectors and final-gate boundary fixtures verify selected update, no source input, ≥6 adequate domains, target/support/benign predicates, and Dormant/Rejected/Admitted outcomes. |
| §14 | Immutable admission artifact, upstream commitments/certificates/synthesis/final-gate lineage, seed/cell/phase identity, producer/runtime provenance, and production-model identity | REQ-0649–REQ-0668 | `I25` | Artifact lifecycle/schema tests validate every mandatory field/hash/dependency and reject missing, corrupt, stale, source-contaminated, or incompatible admission artifacts. |
| §24.4; §§28.3–28.4; §30.2 | `fedsira smoke`, protocol/security invariants, theorem/count checks, and `Protocol Invariant Validation` gate | REQ-1541–REQ-1544; REQ-1715–REQ-1735; REQ-1787–REQ-1789 | `I26` | Smoke and invariant suites pass all prescribed valid/invalid fixtures; source weight cannot become nonzero; Krum/panel/count/state/provenance invariants hold before scientific runs. |
| Roadmap preamble; §§1.1–1.2, 3–8, 13; §40 | Authority-path, authenticated cross-silo threat-model, source/reproducer knowledge and collusion, deterministic selection, theorem-scope, and Krum-interpretation constraints | REQ-0003–REQ-0005; REQ-0061; REQ-0078; REQ-0080; REQ-0087–REQ-0093; REQ-0097; REQ-0154; REQ-0228; REQ-0266–REQ-0267; REQ-0281; REQ-0284; REQ-0296–REQ-0297; REQ-0616; REQ-0618; REQ-0638; REQ-0648; REQ-2049; REQ-2081–REQ-2085 | `I19`, `I20`, `I21`, `I23`, `I24` | Threat-model, state-machine, provenance, selection-order, and synthesis evidence preserves source-artifact exclusion, authenticated cross-silo/domain accounting, declared Byzantine knowledge/collusion, deterministic pre-outcome selection, and the exact conditional Krum/theorem scope. |

### Coverage Rules

- Every mandatory requirement owned by this milestone must remain present in the Roadmap Coverage Inventory.
- Every mandatory implementation-bearing requirement must be mapped to at least one real implementation issue before implementation begins; issue-dependent fields remain `—` until that separate issue-creation phase.
- Every conditional requirement must remain traceable and must be implemented only when its roadmap-defined condition applies.
- Every mapped requirement must have objective verification or evidence consistent with the inventory acceptance-evidence contract.
- Every future implementation issue must reference the exact requirement IDs it satisfies.
- `NON_IMPLEMENTATION` requirements constrain scope, terminology, interpretation, exclusions, or claims but must not be converted into implementation tasks.
- A requirement is not considered covered merely because it falls inside a roadmap section or numeric range assigned to the milestone; the exact IDs in the Coverage table are authoritative for milestone allocation.
- No blocking requirement may remain `UNMAPPED` at the issue level or `AMBIGUOUS` when implementation begins.
- No issue may redefine, weaken, silently reinterpret, duplicate, or extend the authoritative roadmap requirement it implements.

## Dependencies

### Milestone Dependencies

| Milestone | Required Input / Contract | Entry Gate |
|---|---|---|
| M01 — Scientific Configuration, Determinism, and Artifact Foundation | Deterministic identity/ordering, artifact/provenance/state/recovery contracts, and fixed protocol configuration | `Complete + audit PASS` |
| M02 — Validated Dataset and Evidence-Role Preparation | Fresh role-specific evidence views, sample identities, domain registry, and feasibility manifests | `Complete + audit PASS` |
| M03 — Deterministic Model Training and Evaluation Core | Anchor/source/reproduction training, scoring, metrics, checkpoint/update representation, and evaluation APIs | `Complete + audit PASS` |

### Artifact / Interface Dependencies

| Dependency | Produced By | Required Validation |
|---|---|---|
| Authoritative anchor checkpoint and model/update representation | M03 | Checkpoint hash, model schema, parameter order, and training provenance validate |
| Role/split/sample/evidence manifests | M02 | Freshness, disjointness, adequacy, domain identity, and checksum checks pass |
| Canonical deterministic assignment/hash/provenance interfaces | M01 | Seed/order/timestamp/fingerprint invariants pass |

Dependency completion alone is not sufficient. Every consumed dependency must be present, valid, provenance-compatible where applicable, non-stale, and compatible with the active roadmap contract.

## Implementation Issues

Implementation issues for this milestone are listed below; each issue's detailed task checklist, acceptance criteria, and required tests are defined in `Issues.md`.

| Order | Issue | Work Package | Roadmap Scope | Requirement Coverage | Depends On |
|---:|---|---|---|---|---|
| 1 | `I19` — Implement Capability Claim Contract and FedSIRA State Machine | Implement the immutable Capability Claim Contract, evidence sufficiency, claim identity, state vocabulary/transitions, resource horizon, attempt consumption, dormancy/resume/expiry, and non-negotiable authority-path invariants. | Roadmap preamble; §1.1; §1.2; §1.3; §5; §5.1; §5.2; §5.3; §6.1; §6.2; §6.3; §6.4 | 95 atomic requirements | `I02`, `I06`, `I18` |
| 2 | `I20` — Encode Threat Model, Authority Mathematics, and Theory Checks | Encode the authenticated-domain threat assumptions and implement executable mathematical/counting checks for source exclusion, verifier/Krum admissibility, information limits, non-interference structure, delay lower bound, and diagnostic committee probabilities. | §3; §4.1; §4.2; §4.3; §8; §40 | 61 atomic requirements | `I16`, `I17`, `I19` |
| 3 | `I21` — Implement Claim Opening and Proposal-Assisted Screening | Implement proposal-assisted and candidate-free opening, deterministic source/screen selection, matched-control cross-fold screening, adequacy, differential decisions, and Open/Rejected/Dormant outcomes. | §7.1; §7.2; §7.2; §13.9; §13.4; §13.5 | 46 atomic requirements | `I10`, `I15`, `I16`, `I19` |
| 4 | `I22` — Implement Source-Independent Reproduction Commitment Path | Implement authority-path reproduction opportunity scheduling, honest non-source reproduction invocation, commitment hashing before verifier assignment, consumption semantics, and reproducibility-row identity. | §7.3 | 8 atomic requirements | `I06`, `I15`, `I21` |
| 5 | `I23` — Implement External Verification and Reproducibility Certification | Implement post-commitment verifier assignment, freshness and exclusion rules, Positive/Negative/Abstain evaluation, deterministic Byzantine/diagnostic profiles, certification thresholds, and certified-row ordering. | §3; §7.4; §7.4; §7.5; §13.6; §13.7; §13.8; §13.9 | 40 atomic requirements | `I03`, `I17`, `I22` |
| 6 | `I24` — Implement Source-Excluded Krum and Single-Reproduction Production Update | Implement canonical Krum with `n=5,f_R=1`, admissibility, distances/tie rules, source-free synthesis, and the resolved single-reproduction production-update mapping. | §7.6 | 11 atomic requirements | `I15`, `I23` |
| 7 | `I25` — Implement Final Fresh Gate and Immutable Admission Artifact | Implement the post-synthesis fresh final gate, adequacy and claim predicates, terminal outcomes, production-model identity, and immutable admission artifact with complete upstream lineage. | §7.7; §14 | 32 atomic requirements | `I06`, `I17`, `I24` |
| 8 | `I26` — Implement Protocol Smoke, Invariant, and Mathematical Validation Gate | Implement `fedsira smoke`, all protocol/security invariant fixtures, mathematical/counting checks, and the blocking `Protocol Invariant Validation` experiment. | §24.4; §28.3; §28.4; §30.2 | 28 atomic requirements | `I18`, `I19`, `I20`, `I21`, `I22`, `I23`, `I24`, `I25` |

### Issue Contract

Every milestone issue must:

- reference its exact roadmap section(s);
- list every covered requirement ID;
- contain a detailed implementation checklist;
- define objective acceptance criteria;
- identify required tests;
- identify required artifacts, outputs, or interfaces;
- identify required provenance or manifest updates where applicable;
- identify explicit dependencies on upstream milestones, issues, artifacts, or interfaces;
- preserve roadmap terminology and semantics;
- close only when every mapped requirement and acceptance criterion is satisfied.

## Deliverables

| Deliverable | Source Issue(s) | Required Validation | Downstream Consumer |
|---|---|---|---|
| Immutable Capability Claim Contract identity and protocol state machine | `I19`, `I20`, `I21`, `I22`, `I23`, `I24`, `I25`, `I26` | Contract hashing/invalidation and exhaustive transition fixtures pass | M05–M08 |
| Proposal-assisted and candidate-free opening artifacts | `I19`, `I20`, `I21`, `I22`, `I23`, `I24`, `I25`, `I26` | Screen matching, metrics, thresholds, source-zero-weight commitment, and opening outcomes validate | M06–M07 |
| Reproduction commitment, verifier assignment/report, certification, and committee artifacts | `I19`, `I20`, `I21`, `I22`, `I23`, `I24`, `I25`, `I26` | Post-commitment ordering, freshness, exclusions, votes, adequacy, and row-consumption rules pass | M05–M07 |
| Source-excluded Krum/single-reproduction production-update and final-gate artifacts | `I19`, `I20`, `I21`, `I22`, `I23`, `I24`, `I25`, `I26` | Krum math/path mapping and all final-gate predicates/outcomes pass | M05–M08 |
| Complete admission artifact and authority-path provenance | `I19`, `I20`, `I21`, `I22`, `I23`, `I24`, `I25`, `I26` | Every required identity/dependency/provenance field is present and valid with no source checkpoint used as production checkpoint | M06–M08 |
| Protocol smoke/invariant validation evidence | `I19`, `I20`, `I21`, `I22`, `I23`, `I24`, `I25`, `I26` | `fedsira smoke` and `Protocol Invariant Validation` pass every required invariant | M05–M08 |

All roadmap-required deliverables for this milestone must appear in this table or be explicitly represented by the requirement-owned artifacts/evidence in the Roadmap Coverage Inventory.

## Entry Criteria

Implementation may begin only when all of the following are true:

- M01–M03 are complete and their milestone audits are `PASS`;
- validated domain/role manifests and the authoritative anchor/training/evaluation interfaces are available;
- protocol configuration and deterministic assignment primitives resolve without ambiguity.
- every required upstream artifact, interface, schema, manifest, or validation record exists and passes its applicable validation;
- consumed evidence is provenance-compatible and non-stale where provenance applies;
- all roadmap requirements owned by this milestone are present in the Roadmap Coverage Inventory;
- every mandatory implementation-bearing requirement has been assigned to at least one real milestone implementation issue;
- every mapped requirement has an explicit verification or evidence target;
- no blocking requirement is `UNMAPPED` at the issue level;
- no blocking requirement is `AMBIGUOUS`;
- no unresolved roadmap ambiguity would force the implementer to invent a scientific, mathematical, methodological, numerical, architectural, configuration, artifact, or execution decision.

## Exit Criteria

The milestone is complete only when all of the following are true:

- every roadmap-defined authority-path state and transition is executable with exact failure/resume/terminal semantics;
- proposal/candidate-free opening, reproduction, verification, Krum or resolved single-row synthesis, and final gate produce immutable machine-readable artifacts;
- the source artifact has zero direct production weight and no model-input edge into honest reproduction or source-excluded synthesis;
- `Protocol Invariant Validation` passes and blocks scientific runs on any invariant failure.
- every mandatory implementation-bearing requirement owned by this milestone is satisfied;
- every applicable conditional implementation-bearing requirement is satisfied;
- every relevant `NON_IMPLEMENTATION` constraint assigned to this milestone is demonstrably preserved;
- every mapped implementation issue is closed;
- the Roadmap Coverage Inventory contains no unresolved blocking coverage gap or `AMBIGUOUS` requirement owned by this milestone;
- all required unit, integration, numerical, structural, scientific, and failure-path validations for the owned requirements pass;
- all required deliverables are generated and all required artifacts, interfaces, schemas, manifests, and provenance records are complete, readable, checksum-valid, dependency-compatible, and non-stale;
- the milestone audit is `PASS` with no unresolved blocking finding.

## Acceptance Evidence

| Evidence Area | Required Evidence | Pass Condition |
|---|---|---|
| Requirement coverage | Roadmap Coverage Inventory plus this milestone's Coverage table | All 321 assigned requirements are accounted for exactly once in this milestone; all 288 implementation-bearing requirements have completed implementation evidence before audit. |
| State machine | Exhaustive transition and evidence-boundary fixtures | Every state/transition, attempt-consumption rule, Dormant resume, Rejected/Expired terminality, and final-gate outcome matches the contract. |
| Opening | Screen/source-order/matching artifacts | Proposal-assisted and candidate-free paths use exact evidence, folds, matching, thresholds and opening outcomes. |
| Reproduction and verification | Commitment/panel/report/certificate records | Training starts from anchor, commitment precedes assignment, panels are eligible/fresh, and certification follows exact Positive/Negative/Abstain rules. |
| Synthesis and final gate | Krum/single-row synthesis plus final-gate records | Production update excludes source input and all Krum/admission predicates evaluate at full precision with exact boundary behavior. |
| Authority-path provenance | Admission artifact dependency graph | All required commitments, identities, timestamps, hashes, producer/runtime fingerprints and final evidence are complete and non-stale. |
| Protocol validation | Smoke/§28/§30.2 outputs | All prescribed invariant, theorem/count, and intentionally invalid cases pass/fail for the specified reason. |
| Deliverables | Required milestone outputs and artifact manifests | Every listed deliverable is present, readable, valid, provenance-compatible, and suitable for its declared downstream consumer. |
| Audit | Milestone audit | Final result is `PASS` with no unresolved blocking findings. |

## Milestone Audit

**Audit issue:** `—`

**Status:** `PENDING`

The milestone audit is the final completion gate. It must independently verify:

- complete roadmap coverage for all requirements owned by the milestone;
- exact requirement-to-issue traceability once real implementation issues exist;
- closure of every mandatory implementation issue;
- completion and passing status of all required tests and validations;
- existence and validity of all required deliverables;
- completeness and validity of required provenance and manifests;
- absence of stale or incompatible evidence;
- preservation of all applicable `NON_IMPLEMENTATION` constraints;
- absence of unresolved blocking findings;
- readiness of milestone outputs for all declared downstream consumers.

The audit must end in exactly one result:

- `PASS` — every completion condition is satisfied.
- `FAIL` — one or more blocking conditions remain.

A milestone is not complete until the audit result is `PASS`.

## Scope Boundary

- This milestone implements only the roadmap implementation-bearing requirements explicitly assigned to it and preserves the `NON_IMPLEMENTATION` constraints explicitly assigned to it.
- The authoritative roadmap remains the source of scientific, mathematical, methodological, architectural, numerical, configuration, artifact, execution, reporting, and claim requirements.
- This milestone may organize implementation work but may not redefine, weaken, strengthen, extend, or silently reinterpret the roadmap.
- Detailed implementation checklists belong in future implementation issues.
- Detailed verification checklists belong in the future milestone audit issue.
- Work outside this milestone's mapped roadmap scope must not be added unless the roadmap or Roadmap Coverage Inventory is explicitly updated first.

---

# M05 — Adversarial Mechanisms and Baseline Suite

> **Outcome:** All roadmap-defined attacks, stress transforms, and comparator/baseline methods are implemented under their fixed information, budget, calibration, and execution contracts and pass baseline implementation validation.

## At a Glance

| Field | Value |
|---|---|
| Roadmap scope | `§4.2 (source-copy feasibility); §§15–16; §30.3; §32 (baseline lock)` |
| Requirement ownership | Implementation: REQ-0098; REQ-0669–REQ-0690; REQ-0692–REQ-0698; REQ-0700–REQ-0710; REQ-0712–REQ-0722; REQ-0724–REQ-0772; REQ-0774–REQ-0777; REQ-0779–REQ-0831; REQ-0833; REQ-1790–REQ-1792; REQ-2104; REQ-2112–REQ-2150; REQ-2152–REQ-2201<br>Constraints: REQ-0691; REQ-0699; REQ-0711; REQ-0723; REQ-0773; REQ-0778; REQ-0832; REQ-1942; REQ-2151; REQ-2202 |
| Upstream milestones | `M01, M02, M03, M04` |
| Implementation issues | `I27`, `I28`, `I29`, `I30`, `I31`, `I32` |
| Coverage authority | `Roadmap Coverage Inventory` |
| Audit issue | None — no dedicated per-milestone audit issue; verified via `Milestone Audit.md` |
| Audit status | `PENDING` |

## Coverage

The Roadmap Coverage Inventory is the traceability authority for this milestone. Every requirement listed below has this milestone as its single primary milestone owner. `NON_IMPLEMENTATION` requirements are retained as scope, terminology, exclusion, methodological, or claim constraints and do not create fictitious implementation work.

| Roadmap Section | Scope / Work Package | Requirement IDs | Implementation Issue(s) | Verification / Evidence |
|---|---|---|---|---|
| §4.2; §§15–15.7 | Adversarial role/scenario library including source copy, model-replacement and verifier-aware backdoor behavior, evidence-oracle corruption, trigger construction, compromised-role selection, and attack manifests | REQ-0098; REQ-0669–REQ-0732 | `I27`, `I28` | Deterministic attack fixtures assert exact compromised identities, carrier eligibility, transform parameters/rows, update construction, source-copy equality, backdoor objective, and infeasible-cell outcomes. |
| §§15.8–15.10 | Evidence-arrival schedules, heterogeneity/site-shift/quantity transforms, shared epistemic failures, capability under-specification, correlated-context and other fixed boundary/stress fixtures | REQ-0733–REQ-0774 | `I27`, `I29` | Transform manifests reproduce exact schedules/strengths/affected identities and preserve sample/role lineage; boundary fixtures produce prescribed feasible/infeasible scientific states. |
| §§16–16.2 | Baseline registry, common information/budget/fairness contract, and core/simple comparator methods | REQ-0775–REQ-0794; REQ-2112–REQ-2151 | `I30` | Per-baseline contract tests verify exact inputs, data access, training budget, calibration/tuning prohibition, update/production path, deterministic identities, and common output schema. |
| §§16.3–16.5 | Advanced robust aggregation, review, reconstruction, sanitization, recovery, clustering/ensemble/reference baselines and fixed baseline-specific fixtures/parameters | REQ-0795–REQ-0833; REQ-2104; REQ-2152–REQ-2202 | `I30`, `I31` | Algorithm/property fixtures and benign/adversarial baseline fixtures verify exact baseline mechanics, calibration artifacts, deterministic tie handling, invalidity rules, and no outcome-dependent substitutions. |
| §30.3 | Seventeen-cell `Baseline Implementation Validation` at engineering seed 900001 | REQ-1790–REQ-1792 | `I32` | `fedsira run`/validation execution produces exactly 17 terminal validation records; each baseline yields finite/common metrics, follows its mechanism path, and uses no test-role tuning. |
| §32 | Baseline scientific-lock constraint requiring fixed algorithms, information, budgets, calibration thresholds, and explicit invalid/incompatible outcomes | REQ-1942 | `I30` | Baseline registry and execution manifests prove algorithms, information, budgets, calibration thresholds, and invalid/incompatible outcomes remain fixed and are reported rather than substituted after results. |

### Coverage Rules

- Every mandatory requirement owned by this milestone must remain present in the Roadmap Coverage Inventory.
- Every mandatory implementation-bearing requirement must be mapped to at least one real implementation issue before implementation begins; issue-dependent fields remain `—` until that separate issue-creation phase.
- Every conditional requirement must remain traceable and must be implemented only when its roadmap-defined condition applies.
- Every mapped requirement must have objective verification or evidence consistent with the inventory acceptance-evidence contract.
- Every future implementation issue must reference the exact requirement IDs it satisfies.
- `NON_IMPLEMENTATION` requirements constrain scope, terminology, interpretation, exclusions, or claims but must not be converted into implementation tasks.
- A requirement is not considered covered merely because it falls inside a roadmap section or numeric range assigned to the milestone; the exact IDs in the Coverage table are authoritative for milestone allocation.
- No blocking requirement may remain `UNMAPPED` at the issue level or `AMBIGUOUS` when implementation begins.
- No issue may redefine, weaken, silently reinterpret, duplicate, or extend the authoritative roadmap requirement it implements.

## Dependencies

### Milestone Dependencies

| Milestone | Required Input / Contract | Entry Gate |
|---|---|---|
| M01 — Scientific Configuration, Determinism, and Artifact Foundation | Deterministic identities, artifact/provenance framework, exact configured attack/baseline parameters | `Complete + audit PASS` |
| M02 — Validated Dataset and Evidence-Role Preparation | Prepared role views, trigger-feature registry, domain/class identities, secondary-compatible data interfaces | `Complete + audit PASS` |
| M03 — Deterministic Model Training and Evaluation Core | Model/update/training/scoring/metric primitives and checkpoint representation | `Complete + audit PASS` |
| M04 — FedSIRA Admission Protocol and Authority Path | Source/reproducer/verifier/synthesis interfaces needed by protocol-targeted attacks and FedSIRA-relative comparator fixtures | `Complete + audit PASS` |

### Artifact / Interface Dependencies

| Dependency | Produced By | Required Validation |
|---|---|---|
| Prepared role views and trigger-feature/schema registry | M02 | Data/schema/leakage and feature-existence validation pass |
| Model/update/training/scoring primitives | M03 | Deterministic model/training/metric tests pass |
| Authority-path assignments, commitments, verifier and synthesis interfaces | M04 | Protocol invariant validation passes |

Dependency completion alone is not sufficient. Every consumed dependency must be present, valid, provenance-compatible where applicable, non-stale, and compatible with the active roadmap contract.

## Implementation Issues

Implementation issues for this milestone are listed below; each issue's detailed task checklist, acceptance criteria, and required tests are defined in `Issues.md`.

| Order | Issue | Work Package | Roadmap Scope | Requirement Coverage | Depends On |
|---:|---|---|---|---|---|
| 1 | `I27` — Implement Byzantine Source, Reproducer, and Verifier Attack Library | Implement the fixed adversarial role/scenario registry: useful hidden-backdoor source, Source Copy, model-replacement and verifier-aware reproduction attacks, Byzantine verifier behavior, compromised-role selection, triggers, and attack manifests. | §4.2; §15; §15.1; §15.2 Source Copy; §15.2 Model-Replacement Backdoor; §15.2 Verifier-Aware Backdoor; §15.3; §15.10 | 56 atomic requirements | `I15`, `I17`, `I26` |
| 2 | `I28` — Implement Epistemic-Failure and Capability-Granularity Boundary Transforms | Implement shared label-error, shared spurious-feature, attacker-induced common-context, and capability under-specification fixtures with fixed root-cause/cardinality semantics. | §15.4; §15.5; §15.6; §15.7 | 27 atomic requirements | `I10`, `I11`, `I27` |
| 3 | `I29` — Implement Evidence-Arrival and Honest-Heterogeneity Stress Transforms | Implement fixed evidence-arrival schedules, natural/quantity-skew/feature-shift heterogeneity regimes, deterministic transformation identities, controlled-episode completion rules, and stress manifests. | §15.8; §15.9; §15.10 | 24 atomic requirements | `I03`, `I10`, `I11`, `I28` |
| 4 | `I30` — Implement Core Baselines and Comparator Fairness Contracts | Implement the baseline registry common budgets/information rules and the core/simple comparators, including local-only, centralized, FedAvg, review/retrain, candidate-free, direct-Krum, and coordinate-median alternatives under matched fairness. | §16; §16.1; §16.2 `Local-Only Reference`; §16.2 `Centralized Reference`; §16.2 `FedAvg Reference`; §16.2 `Client Review with Direct Source Admission`; §16.2 `Client Review then One Independent Retrain`; §16.2 `One Independent Retrain`; §16.2 `Candidate-Free Full Path`; §16.2 `Multiple Retrains with Direct Krum`; §16.2 `Three-Row Coordinate-Median Alternative`; §16.4; §32 | 64 atomic requirements | `I15`, `I16`, `I17`, `I26` |
| 5 | `I31` — Implement Prior-Art Baselines and Baseline-Specific Validation Fixtures | Implement advanced certified-ensemble, local-reference, reconstruction-filter, density-cluster, continual-assessment, recovery, sanitization, and Krum-reference baselines plus all fixed calibration/completion/ablation fixtures. | §16.3 `Multiple-Model Certified Ensemble`; §16.3 `Independent Local Reference with Source Admission`; §16.3 `Update Reconstruction Filter`; §16.3 `Density-Cluster Trimmed Mean`; §16.3 `Secure Continual Assessment Reference`; §16.3 `Recovery after Source Admission`; §16.3 `Source-Update Sanitization Reference`; §16.3 `Krum Robust Aggregation Reference`; §16.5 Review-style; §16.5 Ensemble; §16.5 Reconstruction; §16.5 Density; §16.5 Recovery; §16.5 Sanitization; §16.5 Parameter Similarity; §16.5 Same Context; §16.5 Source Release; §16.5 Fixture map | 88 atomic requirements | `I16`, `I17`, `I27`, `I30` |
| 6 | `I32` — Execute Baseline Implementation Validation | Implement and execute the exact seventeen-cell `Baseline Implementation Validation` at engineering seed 900001, preserving invalid/incompatible outcomes as scientific evidence. | §30.3 | 3 atomic requirements | `I27`, `I28`, `I29`, `I30`, `I31` |

### Issue Contract

Every milestone issue must:

- reference its exact roadmap section(s);
- list every covered requirement ID;
- contain a detailed implementation checklist;
- define objective acceptance criteria;
- identify required tests;
- identify required artifacts, outputs, or interfaces;
- identify required provenance or manifest updates where applicable;
- identify explicit dependencies on upstream milestones, issues, artifacts, or interfaces;
- preserve roadmap terminology and semantics;
- close only when every mapped requirement and acceptance criterion is satisfied.

## Deliverables

| Deliverable | Source Issue(s) | Required Validation | Downstream Consumer |
|---|---|---|---|
| Deterministic adversarial attack and compromised-role transform library | `I27`, `I28`, `I29`, `I30`, `I31`, `I32` | Attack manifests and unit/property tests reproduce exact identities, parameters, rows and update effects | M06–M07 |
| Deterministic evidence-arrival, heterogeneity, shared-failure, and capability-granularity stress fixtures | `I27`, `I28`, `I29`, `I30`, `I31`, `I32` | Transform/schedule manifests validate exact strengths, role lineage, and scientific feasibility semantics | M07 |
| Complete 17-method baseline/comparator registry and implementations | `I27`, `I28`, `I29`, `I30`, `I31`, `I32` | Baseline-specific algorithm/input/budget/calibration tests pass with common machine-readable outputs | M06–M07 |
| Reusable baseline calibration/checkpoint/update artifacts | `I27`, `I28`, `I29`, `I30`, `I31`, `I32` | Artifact schemas, checksums, fingerprints and no-test-tuning rules validate | M06–M07 |
| `Baseline Implementation Validation` evidence | `I27`, `I28`, `I29`, `I30`, `I31`, `I32` | Exactly 17 validation cells terminate validly or as the roadmap-prescribed Invalid state; no silent replacement occurs | M06 |

All roadmap-required deliverables for this milestone must appear in this table or be explicitly represented by the requirement-owned artifacts/evidence in the Roadmap Coverage Inventory.

## Entry Criteria

Implementation may begin only when all of the following are true:

- M01–M04 are complete and their milestone audits are `PASS`;
- prepared datasets, model/training/evaluation primitives, and protocol interfaces are stable and provenance-compatible;
- all attack-required features/data carriers and baseline-required inputs have deterministic feasibility semantics.
- every required upstream artifact, interface, schema, manifest, or validation record exists and passes its applicable validation;
- consumed evidence is provenance-compatible and non-stale where provenance applies;
- all roadmap requirements owned by this milestone are present in the Roadmap Coverage Inventory;
- every mandatory implementation-bearing requirement has been assigned to at least one real milestone implementation issue;
- every mapped requirement has an explicit verification or evidence target;
- no blocking requirement is `UNMAPPED` at the issue level;
- no blocking requirement is `AMBIGUOUS`;
- no unresolved roadmap ambiguity would force the implementer to invent a scientific, mathematical, methodological, numerical, architectural, configuration, artifact, or execution decision.

## Exit Criteria

The milestone is complete only when all of the following are true:

- every named attack/stress transformation has an exact deterministic implementation and manifest;
- every Section 16 baseline has a fixed executable implementation or the prescribed Invalid behavior, with no post-result substitution;
- all attack/baseline information-access, budget, calibration and test-role restrictions are enforced;
- `Baseline Implementation Validation` contains exactly the required terminal cells and blocks downstream comparisons on invalid unsupported substitutions.
- every mandatory implementation-bearing requirement owned by this milestone is satisfied;
- every applicable conditional implementation-bearing requirement is satisfied;
- every relevant `NON_IMPLEMENTATION` constraint assigned to this milestone is demonstrably preserved;
- every mapped implementation issue is closed;
- the Roadmap Coverage Inventory contains no unresolved blocking coverage gap or `AMBIGUOUS` requirement owned by this milestone;
- all required unit, integration, numerical, structural, scientific, and failure-path validations for the owned requirements pass;
- all required deliverables are generated and all required artifacts, interfaces, schemas, manifests, and provenance records are complete, readable, checksum-valid, dependency-compatible, and non-stale;
- the milestone audit is `PASS` with no unresolved blocking finding.

## Acceptance Evidence

| Evidence Area | Required Evidence | Pass Condition |
|---|---|---|
| Requirement coverage | Roadmap Coverage Inventory plus this milestone's Coverage table | All 262 assigned requirements are accounted for exactly once in this milestone; all 252 implementation-bearing requirements have completed implementation evidence before audit. |
| Attack correctness | Attack/transform unit fixtures and manifests | Compromised identities, carrier rules, trigger/poison/update parameters, source-copy equality, and infeasibility outcomes match the roadmap. |
| Stress/boundary transforms | Schedule/heterogeneity/shared-failure manifests | Every strength/regime/schedule is deterministic, provenance-linked, and preserves role/evidence semantics. |
| Baseline contracts | Per-baseline algorithm/input/budget/calibration fixtures | All 17 methods implement exact fixed mechanics and access only permitted information/roles. |
| Baseline numerical behavior | Benign/adversarial engineering fixtures | Outputs are finite where required, mechanism path is exercised, and expected invalid conditions fail explicitly. |
| Validation registry | `Baseline Implementation Validation` index | Exactly 17 engineering-seed validation cells are present with terminal status and common metrics; no confirmatory inference uses the engineering seed. |
| Deliverables | Required milestone outputs and artifact manifests | Every listed deliverable is present, readable, valid, provenance-compatible, and suitable for its declared downstream consumer. |
| Audit | Milestone audit | Final result is `PASS` with no unresolved blocking findings. |

## Milestone Audit

**Audit issue:** `—`

**Status:** `PENDING`

The milestone audit is the final completion gate. It must independently verify:

- complete roadmap coverage for all requirements owned by the milestone;
- exact requirement-to-issue traceability once real implementation issues exist;
- closure of every mandatory implementation issue;
- completion and passing status of all required tests and validations;
- existence and validity of all required deliverables;
- completeness and validity of required provenance and manifests;
- absence of stale or incompatible evidence;
- preservation of all applicable `NON_IMPLEMENTATION` constraints;
- absence of unresolved blocking findings;
- readiness of milestone outputs for all declared downstream consumers.

The audit must end in exactly one result:

- `PASS` — every completion condition is satisfied.
- `FAIL` — one or more blocking conditions remain.

A milestone is not complete until the audit result is `PASS`.

## Scope Boundary

- This milestone implements only the roadmap implementation-bearing requirements explicitly assigned to it and preserves the `NON_IMPLEMENTATION` constraints explicitly assigned to it.
- The authoritative roadmap remains the source of scientific, mathematical, methodological, architectural, numerical, configuration, artifact, execution, reporting, and claim requirements.
- This milestone may organize implementation work but may not redefine, weaken, strengthen, extend, or silently reinterpret the roadmap.
- Detailed implementation checklists belong in future implementation issues.
- Detailed verification checklists belong in the future milestone audit issue.
- Work outside this milestone's mapped roadmap scope must not be added unless the roadmap or Roadmap Coverage Inventory is explicitly updated first.

---

# M06 — Collapse Experiments and Resolved Core

> **Outcome:** The experiment planner/runner and inferential decision engine execute the four preregistered mechanism-collapse experiments and mechanically materialize the unique Resolved FedSIRA Core.

## At a Glance

| Field | Value |
|---|---|
| Roadmap scope | `§2 (mechanism-collapse questions); §6.4 (mechanical survival constraint); §18 except §18.10; §§24.3, 24.5; §§29–31 through §30.8; §32 (collapse lock); §40 (inferential-unit rationale)` |
| Requirement ownership | Implementation: REQ-0049–REQ-0052; REQ-0931–REQ-0957; REQ-0959–REQ-0978; REQ-0980–REQ-0983; REQ-0985–REQ-0994; REQ-0996–REQ-1019; REQ-1537–REQ-1540; REQ-1545–REQ-1557; REQ-1760–REQ-1777; REQ-1780–REQ-1782; REQ-1793–REQ-1807; REQ-1809–REQ-1820; REQ-1914–REQ-1939; REQ-2105–REQ-2106; REQ-2203<br>Constraints: REQ-0196; REQ-0958; REQ-0979; REQ-0984; REQ-0995; REQ-1558; REQ-1778–REQ-1779; REQ-1808; REQ-1821; REQ-1943; REQ-2050 |
| Upstream milestones | `M01, M02, M03, M04, M05` |
| Implementation issues | `I33`, `I34`, `I35`, `I36`, `I37`, `I38`, `I39`, `I40` |
| Coverage authority | `Roadmap Coverage Inventory` |
| Audit issue | None — no dedicated per-milestone audit issue; verified via `Milestone Audit.md` |
| Audit status | `PENDING` |

## Coverage

The Roadmap Coverage Inventory is the traceability authority for this milestone. Every requirement listed below has this milestone as its single primary milestone owner. `NON_IMPLEMENTATION` requirements are retained as scope, terminology, exclusion, methodological, or claim constraints and do not create fictitious implementation work.

| Roadmap Section | Scope / Work Package | Requirement IDs | Implementation Issue(s) | Verification / Evidence |
|---|---|---|---|---|
| §2 | Preregistered proposal-assistance, plurality, direct source-exclusion, and external-verification necessity questions | REQ-0049–REQ-0052 | `I36`, `I37`, `I38`, `I39` | Experiment plan links each RQ contract to its exact collapse experiment, metrics, survival rule, and failure consequence. |
| §§18–18.6, 18.8–18.9 | Seed-level pairing, exact sign-flip superiority/non-inferiority tests, Holm families, paired effects, bootstrap CIs, materiality, missingness/technical-failure rules, and canonical comparison registry | REQ-0931–REQ-0969; REQ-0996–REQ-1019; REQ-2105, REQ-2106 | `I33` | Hand-computed/exhaustive fixtures verify 1024 sign assignments, one-sided shifted nulls, Holm ordering, 10,000-resample CIs, full-precision decisions, pair-count/inconclusive handling and canonical comparison names. |
| §18.7 | Mechanical survival rules for proposal assistance, plurality, direct source exclusion, external verification, and complete eight-case resolved-core mapping | REQ-0970–REQ-0995 | `I34` | Decision-rule fixtures exercise pass/fail boundaries and all P/R/V mappings; four decision artifacts deterministically yield one source-excluded Resolved FedSIRA Core with no manual override. |
| §§24.3, 24.5; §§29, 30, 31 | Read-only `plan`, exact-name `run`, dependency-ordered execution workflow, semantic cell registry/counts, validity/completion accounting, reuse/recovery, and invalid-baseline preservation | REQ-1537–REQ-1540; REQ-1545–REQ-1558; REQ-1760–REQ-1782; REQ-1914–REQ-1939; REQ-2203 | `I35` | CLI/plan tests materialize exact nominal cell counts and prerequisites; run/resume fixtures preserve identities; completed/invalid/failed/evidence-insufficient counts remain explicit and no unplanned cells appear. |
| §§30.4–30.5 | `Proposal-Assisted Opening Necessity` and `Single-Reproduction Necessity` matrices | REQ-1793–REQ-1803 | `I36`, `I37` | Completed indices contain exactly 80 and 60 planned cells with exact modes/episodes/conditions/seeds, required metrics/statistics and preregistered collapse decisions. |
| §§30.6–30.7 | `Source-Artifact Exclusion Necessity` and `External Verification Necessity` matrices | REQ-1804–REQ-1814 | `I38`, `I39` | Completed indices contain exactly 60 and 80 planned cells with exact methods/scenarios/conditions/seeds, required metrics/statistics and central/survival decisions. |
| §30.8 | Collapse synthesis, deterministic decision application, Resolved FedSIRA Core artifact, and downstream dependency freeze | REQ-1815–REQ-1821 | `I40` | All four collapse statistics/constraints exist; Section 18.7 rules execute automatically; one resolved-core artifact records surviving opening/plurality/verification/source-exclusion mapping and provenance. |
| §6.4; §32; §40 | Mechanical collapse/survival and inferential-unit constraints preventing post-outcome mechanism selection or statistical pseudoreplication | REQ-0196; REQ-1943; REQ-2050 | `I34`, `I40` | Collapse-decision and statistical records prove only preregistered survival rules can alter the resolved core, the seed is the inferential unit, and no post-outcome mechanism selection or pseudoreplication occurs. |

### Coverage Rules

- Every mandatory requirement owned by this milestone must remain present in the Roadmap Coverage Inventory.
- Every mandatory implementation-bearing requirement must be mapped to at least one real implementation issue before implementation begins; issue-dependent fields remain `—` until that separate issue-creation phase.
- Every conditional requirement must remain traceable and must be implemented only when its roadmap-defined condition applies.
- Every mapped requirement must have objective verification or evidence consistent with the inventory acceptance-evidence contract.
- Every future implementation issue must reference the exact requirement IDs it satisfies.
- `NON_IMPLEMENTATION` requirements constrain scope, terminology, interpretation, exclusions, or claims but must not be converted into implementation tasks.
- A requirement is not considered covered merely because it falls inside a roadmap section or numeric range assigned to the milestone; the exact IDs in the Coverage table are authoritative for milestone allocation.
- No blocking requirement may remain `UNMAPPED` at the issue level or `AMBIGUOUS` when implementation begins.
- No issue may redefine, weaken, silently reinterpret, duplicate, or extend the authoritative roadmap requirement it implements.

## Dependencies

### Milestone Dependencies

| Milestone | Required Input / Contract | Entry Gate |
|---|---|---|
| M01 — Scientific Configuration, Determinism, and Artifact Foundation | Semantic cell/artifact/recovery/provenance substrate and execution environment | `Complete + audit PASS` |
| M02 — Validated Dataset and Evidence-Role Preparation | Validated primary/secondary preparation and data-feasibility gate | `Complete + audit PASS` |
| M03 — Deterministic Model Training and Evaluation Core | Training, scoring, metrics, seed-level aggregation and evaluation artifacts | `Complete + audit PASS` |
| M04 — FedSIRA Admission Protocol and Authority Path | Full and alternative authority-path mechanics, protocol validation, admission/failure artifacts | `Complete + audit PASS` |
| M05 — Adversarial Mechanisms and Baseline Suite | Validated comparator methods, attack/stress fixtures, and baseline artifacts | `Complete + audit PASS` |

### Artifact / Interface Dependencies

| Dependency | Produced By | Required Validation |
|---|---|---|
| Protocol and baseline validation gates | M04, M05 | `Protocol Invariant Validation` and 17-cell baseline validation are complete and valid |
| Prepared data, anchor/training/metric artifacts | M02, M03 | Active identities are checksum-valid, non-stale, and compatible with planned cells |
| Semantic cell/artifact DAG and recovery machinery | M01 | Plan/run identities, reuse, invalidation, retry and resume tests pass |

Dependency completion alone is not sufficient. Every consumed dependency must be present, valid, provenance-compatible where applicable, non-stale, and compatible with the active roadmap contract.

## Implementation Issues

Implementation issues for this milestone are listed below; each issue's detailed task checklist, acceptance criteria, and required tests are defined in `Issues.md`.

| Order | Issue | Work Package | Roadmap Scope | Requirement Coverage | Depends On |
|---:|---|---|---|---|---|
| 1 | `I33` — Implement Paired Statistical Inference and Canonical Comparison Registry | Implement seed-level pairing, exact sign-flip superiority/non-inferiority tests, Holm families, effects, bootstrap confidence intervals, materiality, failed-pair rules, and canonical comparison identities. | §18; §18.1; §18.2; §18.3; §18.4; §18.5; §18.6; §18.8; §18.9; §18.9 Family 10 | 65 atomic requirements | `I18`, `I32` |
| 2 | `I34` — Implement Mechanical Collapse Survival Rules and Resolved-Core Decision Logic | Implement preregistered survival rules for proposal assistance, plurality, direct source exclusion, and external verification plus the complete eight-case mechanical resolved-core mapping. | §6.4; §18.7 Proposal; §18.7 Plurality; §18.7 Source exclusion; §18.7 External verification; §18.7 Resolved core; §18.7 Resolved core mapping | 27 atomic requirements | `I19`, `I33` |
| 3 | `I35` — Implement Experiment Planner, Runner, Execution Order, and Cell Registry | Implement read-only planning, exact-name experiment execution, dependency-ordered workflow, semantic cell enumeration/counts, completion accounting, reuse/recovery, and invalid-baseline preservation. | §24.3; §24.5; §29; §30; §31 | 68 atomic requirements | `I08`, `I13`, `I18`, `I26`, `I32`, `I33` |
| 4 | `I36` — Run Proposal-Assisted Opening Necessity Experiment | Implement and execute the preregistered `Proposal-Assisted Opening Necessity` matrix and produce the paired evidence consumed by its survival rule. | §2; §30.4 | 7 atomic requirements | `I32`, `I34`, `I35` |
| 5 | `I37` — Run Single-Reproduction Necessity Experiment | Implement and execute the preregistered `Single-Reproduction Necessity` matrix comparing plurality against the fixed single-reproduction alternative. | §2; §30.5 | 6 atomic requirements | `I32`, `I34`, `I35` |
| 6 | `I38` — Run Source-Artifact Exclusion Necessity Experiment | Implement and execute the preregistered `Source-Artifact Exclusion Necessity` matrix testing the central source-exclusion claim under matched evidence. | §2; §30.6 | 6 atomic requirements | `I32`, `I34`, `I35` |
| 7 | `I39` — Run External Verification Necessity Experiment | Implement and execute the preregistered `External Verification Necessity` matrix against direct synthesis from the same committed reproduction opportunities. | §2; §30.7 | 7 atomic requirements | `I32`, `I34`, `I35` |
| 8 | `I40` — Materialize the Resolved FedSIRA Core | Apply the four collapse decisions mechanically, materialize the unique Resolved FedSIRA Core artifact, and bind all downstream scientific dependencies to that resolved-core artifact identity. | §30.8; §32; §40 | 9 atomic requirements | `I34`, `I36`, `I37`, `I38`, `I39` |

### Issue Contract

Every milestone issue must:

- reference its exact roadmap section(s);
- list every covered requirement ID;
- contain a detailed implementation checklist;
- define objective acceptance criteria;
- identify required tests;
- identify required artifacts, outputs, or interfaces;
- identify required provenance or manifest updates where applicable;
- identify explicit dependencies on upstream milestones, issues, artifacts, or interfaces;
- preserve roadmap terminology and semantics;
- close only when every mapped requirement and acceptance criterion is satisfied.

## Deliverables

| Deliverable | Source Issue(s) | Required Validation | Downstream Consumer |
|---|---|---|---|
| Canonical experiment planner, semantic-cell registry, exact-name runner, and dependency/recovery execution workflow | `I33`, `I34`, `I35`, `I36`, `I37`, `I38`, `I39`, `I40` | `plan` counts/identities and run/resume/reuse tests match Sections 29–31 with no unplanned or silently dropped cells | M07–M08 |
| Statistical/comparison engine and claim-family artifacts | `I33`, `I34`, `I35`, `I36`, `I37`, `I38`, `I39`, `I40` | Exact sign-flip, non-inferiority, Holm, paired-effect, bootstrap and missingness fixtures pass at full precision | M07–M08 |
| Proposal-assisted opening and plurality collapse result sets | `I33`, `I34`, `I35`, `I36`, `I37`, `I38`, `I39`, `I40` | Exactly 80 + 60 planned terminal cell records with required metrics/statistics and decision artifacts | M07 |
| Source-exclusion and external-verification collapse result sets | `I33`, `I34`, `I35`, `I36`, `I37`, `I38`, `I39`, `I40` | Exactly 60 + 80 planned terminal cell records with required metrics/statistics and decision artifacts | M07–M08 |
| Resolved FedSIRA Core artifact | `I33`, `I34`, `I35`, `I36`, `I37`, `I38`, `I39`, `I40` | All four survival decisions and the exact Section 18.7 mapping are machine-derived, source-excluded, immutable and provenance-complete | M07–M08 |
| Plan/completion accounting artifact | `I33`, `I34`, `I35`, `I36`, `I37`, `I38`, `I39`, `I40` | Nominal/executable/completed/failed-invalid/evidence-insufficient counts reconcile to the authoritative Section 31 registry | M07–M08 |

All roadmap-required deliverables for this milestone must appear in this table or be explicitly represented by the requirement-owned artifacts/evidence in the Roadmap Coverage Inventory.

## Entry Criteria

Implementation may begin only when all of the following are true:

- M01–M05 are complete and their milestone audits are `PASS`;
- data/protocol/baseline validation gates are complete and compatible with the active semantic plan;
- all collapse methods, attacks, metrics, statistical parameters, and exact master seeds are fixed before outcomes are observed.
- every required upstream artifact, interface, schema, manifest, or validation record exists and passes its applicable validation;
- consumed evidence is provenance-compatible and non-stale where provenance applies;
- all roadmap requirements owned by this milestone are present in the Roadmap Coverage Inventory;
- every mandatory implementation-bearing requirement has been assigned to at least one real milestone implementation issue;
- every mapped requirement has an explicit verification or evidence target;
- no blocking requirement is `UNMAPPED` at the issue level;
- no blocking requirement is `AMBIGUOUS`;
- no unresolved roadmap ambiguity would force the implementer to invent a scientific, mathematical, methodological, numerical, architectural, configuration, artifact, or execution decision.

## Exit Criteria

The milestone is complete only when all of the following are true:

- the plan contains the exact authoritative semantic cell registry and count categories without unplanned or outcome-dropped cells;
- all four collapse experiment matrices have their required terminal outcomes, metrics, inferential artifacts, multiplicity results, and decision records;
- Section 18.7 survival rules are applied mechanically with no manual mechanism choice;
- exactly one provenance-complete Resolved FedSIRA Core is materialized and ready as the mandatory downstream contract.
- every mandatory implementation-bearing requirement owned by this milestone is satisfied;
- every applicable conditional implementation-bearing requirement is satisfied;
- every relevant `NON_IMPLEMENTATION` constraint assigned to this milestone is demonstrably preserved;
- every mapped implementation issue is closed;
- the Roadmap Coverage Inventory contains no unresolved blocking coverage gap or `AMBIGUOUS` requirement owned by this milestone;
- all required unit, integration, numerical, structural, scientific, and failure-path validations for the owned requirements pass;
- all required deliverables are generated and all required artifacts, interfaces, schemas, manifests, and provenance records are complete, readable, checksum-valid, dependency-compatible, and non-stale;
- the milestone audit is `PASS` with no unresolved blocking finding.

## Acceptance Evidence

| Evidence Area | Required Evidence | Pass Condition |
|---|---|---|
| Requirement coverage | Roadmap Coverage Inventory plus this milestone's Coverage table | All 195 assigned requirements are accounted for exactly once in this milestone; all 183 implementation-bearing requirements have completed implementation evidence before audit. |
| Planning/orchestration | `fedsira plan` registry/counts and run/resume execution records | Nominal and executable cell identities/counts match Sections 30–31; invalid/failed/evidence-insufficient cells remain represented. |
| Statistical engine | Exact-test/Holm/bootstrap/effect fixtures | All test statistics, p-values, CIs, effects, family membership, missingness and full-precision decisions match hand/exhaustive expectations. |
| Collapse experiments | Completed §30.4–30.7 experiment indices | Exact 80/60/60/80 matrices are complete with prescribed methods, scenarios, seeds, metrics, statistics and terminal states. |
| Collapse decisions | Four mechanism decision artifacts | Proposal/plurality/source-exclusion/external-verification rules satisfy exact statistical/material thresholds and failure consequences. |
| Resolved core | Resolved FedSIRA Core artifact | All P/R/V mapping fields and source-exclusion invariant are mechanically derived, immutable, checksum-valid and lineage-complete. |
| Recovery/completeness | Interruption/reuse/count reconciliation fixtures | No scientific identity changes on resume/reuse; one permitted infrastructure retry is enforced and cell accounting remains complete. |
| Deliverables | Required milestone outputs and artifact manifests | Every listed deliverable is present, readable, valid, provenance-compatible, and suitable for its declared downstream consumer. |
| Audit | Milestone audit | Final result is `PASS` with no unresolved blocking findings. |

## Milestone Audit

**Audit issue:** `—`

**Status:** `PENDING`

The milestone audit is the final completion gate. It must independently verify:

- complete roadmap coverage for all requirements owned by the milestone;
- exact requirement-to-issue traceability once real implementation issues exist;
- closure of every mandatory implementation issue;
- completion and passing status of all required tests and validations;
- existence and validity of all required deliverables;
- completeness and validity of required provenance and manifests;
- absence of stale or incompatible evidence;
- preservation of all applicable `NON_IMPLEMENTATION` constraints;
- absence of unresolved blocking findings;
- readiness of milestone outputs for all declared downstream consumers.

The audit must end in exactly one result:

- `PASS` — every completion condition is satisfied.
- `FAIL` — one or more blocking conditions remain.

A milestone is not complete until the audit result is `PASS`.

## Scope Boundary

- This milestone implements only the roadmap implementation-bearing requirements explicitly assigned to it and preserves the `NON_IMPLEMENTATION` constraints explicitly assigned to it.
- The authoritative roadmap remains the source of scientific, mathematical, methodological, architectural, numerical, configuration, artifact, execution, reporting, and claim requirements.
- This milestone may organize implementation work but may not redefine, weaken, strengthen, extend, or silently reinterpret the roadmap.
- Detailed implementation checklists belong in future implementation issues.
- Detailed verification checklists belong in the future milestone audit issue.
- Work outside this milestone's mapped roadmap scope must not be added unless the roadmap or Roadmap Coverage Inventory is explicitly updated first.

---

# M07 — Confirmatory and Boundary Evidence Program

> **Outcome:** The Resolved FedSIRA Core is evaluated across the complete confirmatory, ablation, Byzantine robustness, failure-boundary, heterogeneity, delay, efficiency, and secondary-generalization program with complete terminal scientific records.

## At a Glance

| Field | Value |
|---|---|
| Roadmap scope | `§2 (post-collapse research questions); §4.4; §5.3 (secondary no-retune constraint); §§30.9–30.20; §32 (post-core freeze); §36` |
| Requirement ownership | Implementation: REQ-0048; REQ-0053–REQ-0059; REQ-0107–REQ-0117; REQ-1822–REQ-1825; REQ-1827–REQ-1857; REQ-1859–REQ-1865; REQ-1867–REQ-1872; REQ-1874–REQ-1877; REQ-1879–REQ-1884; REQ-1886–REQ-1889; REQ-1891–REQ-1897; REQ-1899–REQ-1900; REQ-1902–REQ-1912; REQ-2016–REQ-2017<br>Constraints: REQ-0138; REQ-1826; REQ-1858; REQ-1866; REQ-1873; REQ-1878; REQ-1885; REQ-1890; REQ-1898; REQ-1901; REQ-1913; REQ-1944–REQ-1945; REQ-2014–REQ-2015 |
| Upstream milestones | `M06` |
| Implementation issues | `I41`, `I42`, `I43`, `I44`, `I45`, `I46`, `I47` |
| Coverage authority | `Roadmap Coverage Inventory` |
| Audit issue | None — no dedicated per-milestone audit issue; verified via `Milestone Audit.md` |
| Audit status | `PENDING` |

## Coverage

The Roadmap Coverage Inventory is the traceability authority for this milestone. Every requirement listed below has this milestone as its single primary milestone owner. `NON_IMPLEMENTATION` requirements are retained as scope, terminology, exclusion, methodological, or claim constraints and do not create fictitious implementation work.

| Roadmap Section | Scope / Work Package | Requirement IDs | Implementation Issue(s) | Verification / Evidence |
|---|---|---|---|---|
| §2; §4.4 | Primary authority-transition, Byzantine operating region, safe dormancy, reproducibility limitation, capability granularity, heterogeneity, delay/efficiency, secondary-generalization questions and mandatory failure-boundary obligations | REQ-0048; REQ-0053–REQ-0059; REQ-0107–REQ-0117 | `I41`, `I43`, `I44`, `I45`, `I46`, `I47` | Plan-to-RQ trace verifies every named experiment/condition is present and no required boundary is treated as optional debugging coverage. |
| §30.9 | `Primary Confirmatory Evaluation` | REQ-1822–REQ-1830 | `I41` | Exactly 420 terminal cells (`14 methods × 3 scenarios × 10 seeds`) with exact method/scenario registries, required metrics/comparisons and no unplanned substitutions. |
| §30.10 | Eighteen-variant `Mechanism Ablation` with matched Full FedSIRA references | REQ-1831–REQ-1858 | `I42` | Exactly 180 semantic cells plus computationally reused matched references; each variant uses the specified changed mechanism only, primary metric, invalidity rule and comparison family. |
| §§30.11–30.13 | Compromised-reproducer, compromised-verifier, random diagnostic, and Byzantine-bound-violation robustness | REQ-1859–REQ-1878 | `I43` | Exact 280/100/80 cell matrices preserve within-/above-bound identities, profiles, attack feasibility, MAR/LAR/utility metrics and scope-restricting outcomes. |
| §§30.14–30.17 | Evidence scarcity/dormancy, shared epistemic failure, capability under-specification, and heterogeneous-reproduction boundary studies | REQ-1879–REQ-1894 | `I44`, `I45` | Exact 40/90/60/160 cell matrices with prescribed schedules/failure strengths/granularities/regimes, matched-clean references, terminal states, and boundary metrics. |
| §§30.18–30.19 | Admission-delay decomposition and descriptive efficiency measurement | REQ-1895–REQ-1906 | `I46` | Exactly 120 delay cells and 60 efficiency timing cells; T_evidence remains logical cycles separate from post-evidence timing; prescribed repetitions/seeds/resource metrics are complete. |
| §30.20 | CICIoT2023 secondary-dataset generalization | REQ-1907–REQ-1913 | `I47` | Exactly 100 cells (`5 methods × 2 scenarios × 10 seeds`) use fixed primary protocol thresholds/semantics, secondary target/support preparation, required metrics/statistics, and synthetic-domain claim limitation. |
| §36 | Complete scientific result-set invariants and experiment-completion definition | REQ-2014–REQ-2017 | `I47` | Result-set audit proves every planned Section 30 cell retains a terminal scientific/technical record, required metrics/statistics/gates exist, reused artifacts do not change logical cells, and no favorable-subset filtering occurred. |
| §5.3; §32 | Post-core scientific-freeze constraints preventing secondary outcomes, unfavorable cells, or collapse results from retuning or replacing the resolved experiment program | REQ-0138; REQ-1944–REQ-1945 | `I47` | Resolved-core fingerprints and terminal experiment records prove secondary/post-core outcomes do not retune or replace the resolved program, unfavorable/null cells remain included, and no new method, threshold, dataset, baseline, seed, or attack is introduced. |

### Coverage Rules

- Every mandatory requirement owned by this milestone must remain present in the Roadmap Coverage Inventory.
- Every mandatory implementation-bearing requirement must be mapped to at least one real implementation issue before implementation begins; issue-dependent fields remain `—` until that separate issue-creation phase.
- Every conditional requirement must remain traceable and must be implemented only when its roadmap-defined condition applies.
- Every mapped requirement must have objective verification or evidence consistent with the inventory acceptance-evidence contract.
- Every future implementation issue must reference the exact requirement IDs it satisfies.
- `NON_IMPLEMENTATION` requirements constrain scope, terminology, interpretation, exclusions, or claims but must not be converted into implementation tasks.
- A requirement is not considered covered merely because it falls inside a roadmap section or numeric range assigned to the milestone; the exact IDs in the Coverage table are authoritative for milestone allocation.
- No blocking requirement may remain `UNMAPPED` at the issue level or `AMBIGUOUS` when implementation begins.
- No issue may redefine, weaken, silently reinterpret, duplicate, or extend the authoritative roadmap requirement it implements.

## Dependencies

### Milestone Dependencies

| Milestone | Required Input / Contract | Entry Gate |
|---|---|---|
| M02 — Validated Dataset and Evidence-Role Preparation | Validated role views, sample identities, and feasibility evidence consumed directly by `I47` | `Complete + audit PASS` |
| M03 — Deterministic Model Training and Evaluation Core | Training, scoring, and evaluation primitives consumed directly by `I46` | `Complete + audit PASS` |
| M05 — Adversarial Mechanisms and Baseline Suite | Attack, stress-transform, and comparator/baseline implementations consumed directly by `I43`/`I46` | `Complete + audit PASS` |
| M06 — Collapse Experiments and Resolved Core | Immutable Resolved FedSIRA Core, planner/runner, statistical/comparison engine, collapse decisions, and authoritative semantic-cell registry | `Complete + audit PASS` |

### Artifact / Interface Dependencies

| Dependency | Produced By | Required Validation |
|---|---|---|
| Resolved FedSIRA Core and collapse decision artifacts | M06 | Complete, checksum-valid, source-excluded, non-stale, and compatible with all downstream cells |
| Validated baseline/attack/stress implementations | M05 | Baseline validation complete; transform manifests and feasibility rules pass |
| Prepared primary/secondary data and model/metric artifacts | M02, M03 | Dataset/program validity and active artifact lineage pass |
| Protocol admission/failure artifacts and invariant suite | M04 | Protocol validation remains `PASS` under the active resolved path |

Dependency completion alone is not sufficient. Every consumed dependency must be present, valid, provenance-compatible where applicable, non-stale, and compatible with the active roadmap contract.

## Implementation Issues

Implementation issues for this milestone are listed below; each issue's detailed task checklist, acceptance criteria, and required tests are defined in `Issues.md`.

| Order | Issue | Work Package | Roadmap Scope | Requirement Coverage | Depends On |
|---:|---|---|---|---|---|
| 1 | `I41` — Run Primary Confirmatory Evaluation | Execute the Resolved FedSIRA Core across the exact primary confirmatory matrix and produce complete authority-transition/security-utility evidence. | §2; §30.9 | 10 atomic requirements | `I40` |
| 2 | `I42` — Run Mechanism Ablation Program | Execute all eighteen preregistered mechanism-ablation variants with matched Full FedSIRA references and preserve confirmatory versus diagnostic interpretation. | §30.10 | 28 atomic requirements | `I40`, `I41` |
| 3 | `I43` — Run Byzantine Reproducer, Verifier, and Bound-Violation Robustness | Execute compromised-reproducer, compromised-verifier, random diagnostic, and above-bound robustness matrices under the declared Byzantine profiles. | §2; §30.11; §30.12; §30.13 | 21 atomic requirements | `I27`, `I31`, `I40`, `I42` |
| 4 | `I44` — Run Dormancy, Epistemic-Failure, and Capability Under-Specification Boundaries | Execute evidence-scarcity/dormancy, shared epistemic-failure, correlated-context, and capability-granularity boundary studies with explicit safe-abstention and false-equivalence outcomes. | §2; §4.4; §30.14; §30.15; §30.16 | 26 atomic requirements | `I28`, `I29`, `I40`, `I43` |
| 5 | `I45` — Run Heterogeneous-Reproduction Boundary Study | Execute the ordered honest-heterogeneity regimes and determine the highest supported liveness/synthesis region without post-hoc retuning. | §2; §30.17 | 5 atomic requirements | `I29`, `I40`, `I44` |
| 6 | `I46` — Run Admission-Delay and Efficiency Measurements | Execute admission-delay decomposition and descriptive resource/communication/timing measurements, separating information-arrival cost from protocol overhead. | §2; §30.18; §30.19 | 13 atomic requirements | `I17`, `I29`, `I40`, `I45` |
| 7 | `I47` — Run Secondary Generalization and Close the Scientific Result Set | Execute the locked CICIoT2023 generalization program, then enforce complete result-set invariants and experiment-completion definitions across the full scientific program. | §2; §5.3; §30.20; §32; §36 | 15 atomic requirements | `I11`, `I40`, `I41`, `I46` |

### Issue Contract

Every milestone issue must:

- reference its exact roadmap section(s);
- list every covered requirement ID;
- contain a detailed implementation checklist;
- define objective acceptance criteria;
- identify required tests;
- identify required artifacts, outputs, or interfaces;
- identify required provenance or manifest updates where applicable;
- identify explicit dependencies on upstream milestones, issues, artifacts, or interfaces;
- preserve roadmap terminology and semantics;
- close only when every mapped requirement and acceptance criterion is satisfied.

## Deliverables

| Deliverable | Source Issue(s) | Required Validation | Downstream Consumer |
|---|---|---|---|
| Primary Confirmatory Evaluation result set | `I41`, `I42`, `I43`, `I44`, `I45`, `I46`, `I47` | Exactly 420 planned terminal cells with complete seed-level/domain-level evidence and registered comparisons | M08 |
| Mechanism Ablation result set | `I41`, `I42`, `I43`, `I44`, `I45`, `I46`, `I47` | Exactly 180 semantic cells with matched Full FedSIRA prerequisites and variant-specific evidence | M08 |
| Byzantine robustness and bound-violation result sets | `I41`, `I42`, `I43`, `I44`, `I45`, `I46`, `I47` | Exactly 280 + 100 + 80 planned terminal cells with declared within/above-bound conditions and robustness metrics | M08 |
| Failure-boundary and heterogeneity result sets | `I41`, `I42`, `I43`, `I44`, `I45`, `I46`, `I47` | Exactly 40 + 90 + 60 + 160 planned terminal cells with required matched references, boundary outcomes, and metrics | M08 |
| Admission-delay and efficiency result sets | `I41`, `I42`, `I43`, `I44`, `I45`, `I46`, `I47` | Exactly 120 delay cells and 60 timing cells with correct logical-cycle/time/resource separation and repetition semantics | M08 |
| Secondary generalization result set | `I41`, `I42`, `I43`, `I44`, `I45`, `I46`, `I47` | Exactly 100 planned cells with fixed primary semantics and secondary-specific data identity | M08 |
| Complete Section 30 scientific result-set index | `I41`, `I42`, `I43`, `I44`, `I45`, `I46`, `I47` | Every planned cell has a terminal record and required evidence lineage; no favorable subset, seed replacement, or silent baseline substitution | M08 |

All roadmap-required deliverables for this milestone must appear in this table or be explicitly represented by the requirement-owned artifacts/evidence in the Roadmap Coverage Inventory.

## Entry Criteria

Implementation may begin only when all of the following are true:

- M06 is complete and its milestone audit is `PASS`;
- the Resolved FedSIRA Core is immutable, checksum-valid, source-excluded, non-stale, and all collapse decisions are frozen;
- the authoritative post-collapse semantic-cell plan and all required validated attacks/baselines/data artifacts are available.
- every required upstream artifact, interface, schema, manifest, or validation record exists and passes its applicable validation;
- consumed evidence is provenance-compatible and non-stale where provenance applies;
- all roadmap requirements owned by this milestone are present in the Roadmap Coverage Inventory;
- every mandatory implementation-bearing requirement has been assigned to at least one real milestone implementation issue;
- every mapped requirement has an explicit verification or evidence target;
- no blocking requirement is `UNMAPPED` at the issue level;
- no blocking requirement is `AMBIGUOUS`;
- no unresolved roadmap ambiguity would force the implementer to invent a scientific, mathematical, methodological, numerical, architectural, configuration, artifact, or execution decision.

## Exit Criteria

The milestone is complete only when all of the following are true:

- every §30.9–§30.20 planned cell has the roadmap-prescribed terminal scientific/technical record without outcome-based removal or replacement;
- all confirmatory, ablation, robustness, failure-boundary, heterogeneity, timing/efficiency, and secondary metrics/statistics are complete where defined;
- within-bound and above-bound evidence, Dormant/Abstain/Rejected/Expired/null outcomes, and structural `NA` values remain explicit scientific results;
- the complete Section 30 result-set invariant in §36 passes with no stale or incompatible evidence.
- every mandatory implementation-bearing requirement owned by this milestone is satisfied;
- every applicable conditional implementation-bearing requirement is satisfied;
- every relevant `NON_IMPLEMENTATION` constraint assigned to this milestone is demonstrably preserved;
- every mapped implementation issue is closed;
- the Roadmap Coverage Inventory contains no unresolved blocking coverage gap or `AMBIGUOUS` requirement owned by this milestone;
- all required unit, integration, numerical, structural, scientific, and failure-path validations for the owned requirements pass;
- all required deliverables are generated and all required artifacts, interfaces, schemas, manifests, and provenance records are complete, readable, checksum-valid, dependency-compatible, and non-stale;
- the milestone audit is `PASS` with no unresolved blocking finding.

## Acceptance Evidence

| Evidence Area | Required Evidence | Pass Condition |
|---|---|---|
| Requirement coverage | Roadmap Coverage Inventory plus this milestone's Coverage table | All 118 assigned requirements are accounted for exactly once in this milestone; all 103 implementation-bearing requirements have completed implementation evidence before audit. |
| Primary confirmatory | §30.9 experiment index and comparison artifacts | Exactly 420 planned cells are accounted for with exact methods/scenarios/seeds and required metrics/statistics. |
| Ablation | §30.10 index plus matched-reference lineage | Exactly 180 semantic cells are present; matched Full FedSIRA artifacts are reused without changing cell count or non-ablated settings. |
| Byzantine robustness | §§30.11–30.13 indices | All 460 planned robustness/bound cells are represented with exact compromised-role counts/profiles and required utility/security outcomes. |
| Failure/heterogeneity boundaries | §§30.14–30.17 indices | All 350 planned boundary cells are represented with exact schedules/strengths/granularities/regimes and matched reference semantics. |
| Delay/efficiency | §§30.18–30.19 timing/resource artifacts | All 180 planned cells/repetitions are present; T_evidence and post-evidence time are not conflated; descriptive resource summaries use prescribed repetitions. |
| Secondary generalization | §30.20 index/statistics | Exactly 100 cells use fixed primary thresholds/protocol semantics and required secondary comparisons without administrative-independence extrapolation. |
| Complete result set | §36 completeness record | Every planned Section 30 cell remains in the logical result set with required terminal status/evidence and no outcome-dependent filtering. |
| Deliverables | Required milestone outputs and artifact manifests | Every listed deliverable is present, readable, valid, provenance-compatible, and suitable for its declared downstream consumer. |
| Audit | Milestone audit | Final result is `PASS` with no unresolved blocking findings. |

## Milestone Audit

**Audit issue:** `—`

**Status:** `PENDING`

The milestone audit is the final completion gate. It must independently verify:

- complete roadmap coverage for all requirements owned by the milestone;
- exact requirement-to-issue traceability once real implementation issues exist;
- closure of every mandatory implementation issue;
- completion and passing status of all required tests and validations;
- existence and validity of all required deliverables;
- completeness and validity of required provenance and manifests;
- absence of stale or incompatible evidence;
- preservation of all applicable `NON_IMPLEMENTATION` constraints;
- absence of unresolved blocking findings;
- readiness of milestone outputs for all declared downstream consumers.

The audit must end in exactly one result:

- `PASS` — every completion condition is satisfied.
- `FAIL` — one or more blocking conditions remain.

A milestone is not complete until the audit result is `PASS`.

## Scope Boundary

- This milestone implements only the roadmap implementation-bearing requirements explicitly assigned to it and preserves the `NON_IMPLEMENTATION` constraints explicitly assigned to it.
- The authoritative roadmap remains the source of scientific, mathematical, methodological, architectural, numerical, configuration, artifact, execution, reporting, and claim requirements.
- This milestone may organize implementation work but may not redefine, weaken, strengthen, extend, or silently reinterpret the roadmap.
- Detailed implementation checklists belong in future implementation issues.
- Detailed verification checklists belong in the future milestone audit issue.
- Work outside this milestone's mapped roadmap scope must not be added unless the roadmap or Roadmap Coverage Inventory is explicitly updated first.

---

# M08 — Claims, Reporting, and Reproducibility Closure

> **Outcome:** Verified experiment evidence is converted into mechanically derived claim states and manuscript tables/figures under project-completeness, provenance, scope, and third-party reproducibility gates.

## At a Glance

| Field | Value |
|---|---|
| Roadmap scope | `Roadmap preamble (manuscript naming); §§1.4–1.5; claim/reporting constraints in §§8–11; §18.10; §24.6; §§33–35; §§37–42` |
| Requirement ownership | Implementation: REQ-1020–REQ-1027; REQ-1559–REQ-1564; REQ-1947–REQ-1986; REQ-1995–REQ-2013; REQ-2018–REQ-2037; REQ-2039–REQ-2046; REQ-2065–REQ-2071; REQ-2089; REQ-2204–REQ-2206<br>Constraints: REQ-0018–REQ-0047; REQ-0289–REQ-0290; REQ-0298; REQ-0351; REQ-0376; REQ-0473; REQ-0502; REQ-1987–REQ-1994; REQ-2051–REQ-2064; REQ-2072; REQ-2086 |
| Upstream milestones | `M01, M06, M07` |
| Implementation issues | `I48`, `I49`, `I50`, `I51`, `I52`, `I53` |
| Coverage authority | `Roadmap Coverage Inventory` |
| Audit issue | None — no dedicated per-milestone audit issue; verified via `Milestone Audit.md` |
| Audit status | `PENDING` |

## Coverage

The Roadmap Coverage Inventory is the traceability authority for this milestone. Every requirement listed below has this milestone as its single primary milestone owner. `NON_IMPLEMENTATION` requirements are retained as scope, terminology, exclusion, methodological, or claim constraints and do not create fictitious implementation work.

| Roadmap Section | Scope / Work Package | Requirement IDs | Implementation Issue(s) | Verification / Evidence |
|---|---|---|---|---|
| Roadmap preamble; §§1.4–1.5; claim constraints in §§8–11; §41 | Manuscript naming, canonical claim/scope/exclusion boundaries, dataset/generalization wording limits, and external reference-register traceability | REQ-0018–REQ-0047; REQ-0289–REQ-0290; REQ-0298; REQ-0351; REQ-0376; REQ-0473; REQ-0502; REQ-2051–REQ-2064; REQ-2086; REQ-2089 | `I48`, `I50`, `I53` | Claim/scope checks trace every assigned boundary to its roadmap reference, reject unauthorized extrapolation, preserve exact manuscript method naming, and retain the reference register without creating new scientific authority. |
| §18.10 | Publication rounding/formatting while preserving full-precision decision values | REQ-1020–REQ-1027 | `I50` | Formatting tests verify F1/rates/effects/CIs/p-values/seconds/IEC bytes exactly; decision artifacts are shown to originate from unrounded values. |
| §24.6; §38 | Read-only `fedsira report`, verified `outputs/` to compact `results/` materialization, report dependency fingerprints, and exclusion/read-back rules | REQ-1559–REQ-1564; REQ-2029–REQ-2035 | `I50` | CLI/reporting tests prove no scientific recomputation, block on incomplete/stale evidence, enforce destinations and exclusions, prevent `results/` scientific reads, and limit invalidation to reporting descendants. |
| §33 | Mandatory manuscript tables, schemas, ordering, aggregation and source-data lineage | REQ-1947–REQ-1969; REQ-2205 | `I51` | `fedsira report` generates every named table from verified machine-readable data; schema/order/rounding/source-lineage tests pass with no manual scientific-value transcription. |
| §34 | Mandatory manuscript figures and required encodings | REQ-1970–REQ-1984; REQ-2206 | `I52` | Report/figure tests generate every named figure from verified source-data artifacts with exact axes/aggregation/CI/timing semantics and provenance. |
| §35 | Exact claim IDs/state vocabulary, evidence-to-claim mapping, support thresholds, partial/conditional/null/not-supported logic, and claim-boundary enforcement | REQ-1985–REQ-2013; REQ-2204 | `I48` | Claim fixtures cover every state boundary and required evidence combination; registry emits only allowed claim IDs/states and uses exact non-stale supporting artifacts. |
| §37 | Read-only project scientific-completeness verifier | REQ-2018–REQ-2028 | `I49` | Completeness fixtures verify exact plan count, terminal-cell coverage, active artifact validity/lineage, required metrics/statistics/comparisons/claims, report-source readiness, manuscript-number traceability, and first-blocker diagnosis. |
| §39 | Third-party reconstruction and manuscript-reporting readiness contract | REQ-2036, REQ-2037; REQ-2039–REQ-2046 | `I53` | Clean reconstruction fixture uses reconstruction commit, dependency lock, raw identities, config, deterministic derivations and semantic plan to regenerate/verify active evidence and detect material mismatches. |
| §42 | Cross-project implementation/readiness gate prior to final scientific reporting | REQ-2065–REQ-2072 | `I53` | Readiness verifier confirms config authority, preprocess/smoke/baseline/experiment executability, artifact DAG/reuse/recovery, metrics/statistics, and doctor blocker diagnosis while preserving §39 as final scientific-completion authority. |

### Coverage Rules

- Every mandatory requirement owned by this milestone must remain present in the Roadmap Coverage Inventory.
- Every mandatory implementation-bearing requirement must be mapped to at least one real implementation issue before implementation begins; issue-dependent fields remain `—` until that separate issue-creation phase.
- Every conditional requirement must remain traceable and must be implemented only when its roadmap-defined condition applies.
- Every mapped requirement must have objective verification or evidence consistent with the inventory acceptance-evidence contract.
- Every future implementation issue must reference the exact requirement IDs it satisfies.
- `NON_IMPLEMENTATION` requirements constrain scope, terminology, interpretation, exclusions, or claims but must not be converted into implementation tasks.
- A requirement is not considered covered merely because it falls inside a roadmap section or numeric range assigned to the milestone; the exact IDs in the Coverage table are authoritative for milestone allocation.
- No blocking requirement may remain `UNMAPPED` at the issue level or `AMBIGUOUS` when implementation begins.
- No issue may redefine, weaken, silently reinterpret, duplicate, or extend the authoritative roadmap requirement it implements.

## Dependencies

### Milestone Dependencies

| Milestone | Required Input / Contract | Entry Gate |
|---|---|---|
| M01 — Scientific Configuration, Determinism, and Artifact Foundation | Results/output boundaries, provenance/fingerprint/reconstruction contracts, report destination structure and authoritative configuration | `Complete + audit PASS` |
| M06 — Collapse Experiments and Resolved Core | Statistical engine, comparison artifacts, collapse decisions and Resolved FedSIRA Core | `Complete + audit PASS` |
| M07 — Confirmatory and Boundary Evidence Program | Complete Section 30 result set and all confirmatory/robustness/boundary/secondary evidence | `Complete + audit PASS` |

### Artifact / Interface Dependencies

| Dependency | Produced By | Required Validation |
|---|---|---|
| Complete Section 30 scientific result-set index | M07 | Every planned cell has valid terminal status and required non-stale metric/statistical/gate lineage |
| Statistical/comparison and collapse-decision artifacts | M06 | Exact tests, Holm families, CIs/effects/materiality and resolved-core lineage validate |
| Project artifact/provenance DAG and results boundary | M01 | All active ancestors are checksum-valid, dependency-compatible and reconstructible |

Dependency completion alone is not sufficient. Every consumed dependency must be present, valid, provenance-compatible where applicable, non-stale, and compatible with the active roadmap contract.

## Implementation Issues

Implementation issues for this milestone are listed below; each issue's detailed task checklist, acceptance criteria, and required tests are defined in `Issues.md`.

| Order | Issue | Work Package | Roadmap Scope | Requirement Coverage | Depends On |
|---:|---|---|---|---|---|
| 1 | `I48` — Implement Canonical Claim-Support Registry and Claim Gating | Implement exact claim IDs/states, evidence-to-claim mappings, support/partial/conditional/null/not-supported logic, boundary enforcement, and report-time claim blocking. | §1.4; §1.5; §8; §9.2; §9.6; §11; §11.2; §35; §35.1; §35.2 `Unsupported Capability Problem`; §35.2 `Pre-Evidence Information Limit`; §35.2 `Authority Transition`; §35.2 `Direct Source Exclusion`; §35.2 `Conditional Non-Interference`; §35.2 `Malicious Source Salvage`; §35.2 `Proposal Assistance Value`; §35.2 `Plurality Necessity`; §35.2 `External Verification Necessity`; §35.2 `Mechanism Necessity`; §35.2 `Byzantine Operating Region`; §35.2 `Safe Dormancy`; §35.2 `Reproducibility Is Not Truth`; §35.2 `Capability-Granularity Boundary`; §35.2 `Heterogeneity Boundary`; §35.2 `Information-Arrival Delay`; §35.2 `Post-Evidence Efficiency`; §35.2 `Secondary Generalization`; §35.2 `IoT IDS Application` | 68 atomic requirements | `I33`, `I40`, `I47` |
| 2 | `I49` — Implement Read-Only Scientific Completeness Verification | Implement the project scientific-completeness verifier over expected cells, evidence integrity/provenance, Resolved FedSIRA Core, statistics, and claim-state prerequisites without scientific recomputation. | §37 | 11 atomic requirements | `I06`, `I47`, `I48` |
| 3 | `I50` — Implement Verified Reporting Materialization and Publication Rounding | Implement manuscript method identity, read-only `fedsira report`, verified `outputs/` to compact `results/` materialization, dependency fingerprints/read-back rules, and publication rounding that never changes full-precision decisions. | Roadmap preamble; §18.10; §24.6; §38 | 22 atomic requirements | `I07`, `I48`, `I49` |
| 4 | `I51` — Generate Mandatory Manuscript Tables from Verified Evidence | Implement every required protocol/result/statistical/claim table with exact schema, ordering, aggregation, rounding, and machine-readable source lineage. | §33; §33.1–33.2; §33.2 Primary Results; §33.2 Source-Exclusion Results; §33.3 | 24 atomic requirements | `I48`, `I50` |
| 5 | `I52` — Generate Mandatory Manuscript Figures from Verified Evidence | Implement every required FedSIRA manuscript figure with exact encodings and verified artifact-backed data sources. | §34 | 16 atomic requirements | `I48`, `I50` |
| 6 | `I53` — Close Third-Party Reproducibility and Implementation Readiness | Implement the reference-register traceability, third-party reconstruction/manuscript-readiness contract, and cross-project implementation-completion gate required before final scientific reporting. | §39; §41; §42 | 32 atomic requirements | `I48`, `I49`, `I50`, `I51`, `I52` |

### Issue Contract

Every milestone issue must:

- reference its exact roadmap section(s);
- list every covered requirement ID;
- contain a detailed implementation checklist;
- define objective acceptance criteria;
- identify required tests;
- identify required artifacts, outputs, or interfaces;
- identify required provenance or manifest updates where applicable;
- identify explicit dependencies on upstream milestones, issues, artifacts, or interfaces;
- preserve roadmap terminology and semantics;
- close only when every mapped requirement and acceptance criterion is satisfied.

## Deliverables

| Deliverable | Source Issue(s) | Required Validation | Downstream Consumer |
|---|---|---|---|
| Machine-derived final claim registry | `I48`, `I49`, `I50`, `I51`, `I52`, `I53` | Only Section 35 claim IDs/states are emitted; each state has exact supporting evidence and scope/limitation lineage | Manuscript/report consumers |
| Mandatory Section 33 manuscript tables | `I48`, `I49`, `I50`, `I51`, `I52`, `I53` | All named tables generated from verified machine-readable evidence with exact schemas/order/rounding and source lineage | Manuscript |
| Mandatory Section 34 manuscript figures | `I48`, `I49`, `I50`, `I51`, `I52`, `I53` | All named figures generated from verified source-data artifacts with required encodings and provenance | Manuscript |
| `fedsira report` and compact verified `results/` tree | `I48`, `I49`, `I50`, `I51`, `I52`, `I53` | Read-only completeness gate passes; exports contain no stale/failed/debug/temp data and never feed scientific execution | Manuscript/release |
| Project scientific-completeness record | `I48`, `I49`, `I50`, `I51`, `I52`, `I53` | Section 37 checks pass for plan, terminal cells, active artifacts, metrics/statistics/comparisons/claims, report sources and manuscript-number traceability | Milestone audit |
| Third-party reconstruction/reproducibility evidence | `I48`, `I49`, `I50`, `I51`, `I52`, `I53` | Section 39 reconstruction/readiness checks reproduce or verify complete active lineage from fixed inputs and detect material mismatches | Milestone audit/release |

All roadmap-required deliverables for this milestone must appear in this table or be explicitly represented by the requirement-owned artifacts/evidence in the Roadmap Coverage Inventory.

## Entry Criteria

Implementation may begin only when all of the following are true:

- M01, M06, and M07 are complete and their milestone audits are `PASS`;
- the complete Section 30 result-set index, Resolved FedSIRA Core, statistical/comparison artifacts, and active provenance DAG are valid and non-stale;
- all manuscript-facing products can be derived without introducing new scientific computation or manual value transcription.
- every required upstream artifact, interface, schema, manifest, or validation record exists and passes its applicable validation;
- consumed evidence is provenance-compatible and non-stale where provenance applies;
- all roadmap requirements owned by this milestone are present in the Roadmap Coverage Inventory;
- every mandatory implementation-bearing requirement has been assigned to at least one real milestone implementation issue;
- every mapped requirement has an explicit verification or evidence target;
- no blocking requirement is `UNMAPPED` at the issue level;
- no blocking requirement is `AMBIGUOUS`;
- no unresolved roadmap ambiguity would force the implementer to invent a scientific, mathematical, methodological, numerical, architectural, configuration, artifact, or execution decision.

## Exit Criteria

The milestone is complete only when all of the following are true:

- the read-only scientific-completeness verifier passes every Section 37 condition;
- all mandatory tables, figures, source-data products, and claim states are generated solely from verified active evidence;
- every manuscript-facing number is traceable to exact data, role/split, seed, producer/runtime dependency, and upstream artifact lineage;
- claim wording/states obey all roadmap claim boundaries and do not extrapolate beyond tested evidence;
- the Section 39 third-party reconstruction/manuscript-readiness contract passes.
- every mandatory implementation-bearing requirement owned by this milestone is satisfied;
- every applicable conditional implementation-bearing requirement is satisfied;
- every relevant `NON_IMPLEMENTATION` constraint assigned to this milestone is demonstrably preserved;
- every mapped implementation issue is closed;
- the Roadmap Coverage Inventory contains no unresolved blocking coverage gap or `AMBIGUOUS` requirement owned by this milestone;
- all required unit, integration, numerical, structural, scientific, and failure-path validations for the owned requirements pass;
- all required deliverables are generated and all required artifacts, interfaces, schemas, manifests, and provenance records are complete, readable, checksum-valid, dependency-compatible, and non-stale;
- the milestone audit is `PASS` with no unresolved blocking finding.

## Acceptance Evidence

| Evidence Area | Required Evidence | Pass Condition |
|---|---|---|
| Requirement coverage | Roadmap Coverage Inventory plus this milestone's Coverage table | All 173 assigned requirements are accounted for exactly once in this milestone; all 112 implementation-bearing requirements have completed implementation evidence before audit. |
| Scope and claim boundaries | Claim/scope traceability registry | Every applicable non-implementation boundary is linked and no generated claim/report text exceeds its permitted scope. |
| Claim derivation | Section 35 claim registry and boundary fixtures | Only exact claim IDs/states occur; each state follows its mandated evidence, materiality, statistical, safety and scope rules. |
| Tables | Generated Section 33 tables plus source-data lineage | Every named table satisfies required schema/order/aggregation/rounding and contains no manually transcribed scientific values. |
| Figures | Generated Section 34 figures plus source-data lineage | Every named figure satisfies required encoding/aggregation/CI/timing semantics and originates from verified machine-readable data. |
| Scientific completeness | Section 37 verifier output | Plan counts, terminal cells, artifacts, lineage, metrics, statistics, comparisons, claims and reporting sources are complete and non-stale; otherwise reporting is blocked. |
| Report behavior | `fedsira report` end-to-end evidence | No scientific recomputation occurs; only verified exports are materialized under the prescribed `results/` boundaries. |
| Reproducibility | Section 39 clean reconstruction/readiness evidence | A third party can reconstruct/verify the study from the declared fixed inputs and material fingerprints; material mismatches are detected. |
| Implementation readiness | Section 42 gate evidence | All prerequisite implementation/data/protocol/baseline/experiment/statistical capabilities are executable and diagnostically checkable without creating new authority. |
| Deliverables | Required milestone outputs and artifact manifests | Every listed deliverable is present, readable, valid, provenance-compatible, and suitable for its declared downstream consumer. |
| Audit | Milestone audit | Final result is `PASS` with no unresolved blocking findings. |

## Milestone Audit

**Audit issue:** `—`

**Status:** `PENDING`

The milestone audit is the final completion gate. It must independently verify:

- complete roadmap coverage for all requirements owned by the milestone;
- exact requirement-to-issue traceability once real implementation issues exist;
- closure of every mandatory implementation issue;
- completion and passing status of all required tests and validations;
- existence and validity of all required deliverables;
- completeness and validity of required provenance and manifests;
- absence of stale or incompatible evidence;
- preservation of all applicable `NON_IMPLEMENTATION` constraints;
- absence of unresolved blocking findings;
- readiness of milestone outputs for all declared downstream consumers.

The audit must end in exactly one result:

- `PASS` — every completion condition is satisfied.
- `FAIL` — one or more blocking conditions remain.

A milestone is not complete until the audit result is `PASS`.

## Scope Boundary

- This milestone implements only the roadmap implementation-bearing requirements explicitly assigned to it and preserves the `NON_IMPLEMENTATION` constraints explicitly assigned to it.
- The authoritative roadmap remains the source of scientific, mathematical, methodological, architectural, numerical, configuration, artifact, execution, reporting, and claim requirements.
- This milestone may organize implementation work but may not redefine, weaken, strengthen, extend, or silently reinterpret the roadmap.
- Detailed implementation checklists belong in future implementation issues.
- Detailed verification checklists belong in the future milestone audit issue.
- Work outside this milestone's mapped roadmap scope must not be added unless the roadmap or Roadmap Coverage Inventory is explicitly updated first.
