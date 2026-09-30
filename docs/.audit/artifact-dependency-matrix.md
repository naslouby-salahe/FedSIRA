# Artifact dependency and invalidation matrix

This audit was checked against the 22 `ArtifactFamily` members, their publish
functions, `ArtifactDependency` declarations, and Roadmap §§26–28. It is
implementation evidence, not runtime configuration.

Artifact identity is now framed from schema version, slot family/instance/
owner, producer procedure identity, and sorted dependency kind/name/digest
triples. Producer configuration appears as a labelled content dependency only
for the relevant scope. Full configuration provenance remains on execution
records; it is no longer a global artifact-cache key. The artifact schema is
version 4. Git revision is recorded as provenance, not used as a blanket
invalidation input.

| Artifact family | Producer and identity inputs | Change boundary and consumers |
| --- | --- | --- |
| Raw dataset identity | Raw-file inventory/checksums; acquisition procedure | Raw byte/inventory changes replace the affected dataset identity only. |
| Dataset/schema/exclusion manifest | Dataset-file manifest digest; dataset-manifest procedure | Raw inventory or parser/schema procedure changes dataset evidence. |
| Role/split/sample manifest | Dataset manifest and dataset-specific role/sampling/target configuration | Role intervals, caps, domain mapping, or target changes invalidate this dataset's split and its prepared views. |
| Scaler | Raw-file manifest and dataset-specific preprocessing configuration | Scaling, role population, or raw data changes scaler/prepared descendants; unrelated dataset changes are isolated. |
| Prepared role view | Role/split/sample manifest artifact identity; prepared-view procedure | Split identity changes the view. Parquet checksum/size and role metadata are validated against the published sidecar. |
| Anchor checkpoint | Prepared evidence, numerical runtime, anchor training configuration; dataset/seed/stage slot | Dataset, anchor-training, or governing numerical-runtime changes invalidate that anchor and descendants. |
| Source candidate checkpoint | Prepared evidence, numerical runtime, source-training configuration; dataset/seed/stage slot | Source-training inputs or implementation scope invalidate only compatible source candidates and descendants. |
| Reproduction checkpoint | Prepared evidence, numerical runtime, reproduction-training configuration; dataset/seed/stage slot | Reproduction-training inputs or implementation scope invalidate reproduction descendants, not prepared data. |
| Baseline checkpoint | Prepared evidence, numerical runtime, baseline training configuration; dataset/seed/stage slot | Baseline-specific training changes do not invalidate anchors or prepared data. |
| Model score artifact | Model checkpoint, exact role-view digest, class registry, scoring transform, numerical runtime | Scoring changes invalidate scores and their downstream evaluation; checkpoints remain reusable. |
| Screen matching/differential artifact | Anchor, source candidate, prepared evidence, fold seed/count, capability/opening/screen configuration | Proposal-screen changes invalidate matching only and downstream opening evidence. |
| Baseline calibration artifact | Prepared evidence and baseline-calibration configuration | Calibration changes invalidate calibrated baseline products and descendants. |
| Fixed protocol configuration / resolved core | Sorted content digests of the four collapse decisions | A changed collapse decision or resolver procedure changes the resolved core; it is shared as a project prerequisite. |
| Verifier assignment/report | Commitment identity and verification configuration | Verifier panel/decision changes invalidate verifier reports, certificates, and descendants, not committed reproduction rows. |
| Reproduction certificate | Certified row-report identity and verification configuration | Certification changes invalidate certificates and synthesis/final-gate descendants only. |
| Krum synthesized update/model | Certified reproduction-row identity and synthesis configuration | Krum/synthesis changes invalidate synthesis and final-gate descendants, not reproduction training. |
| Final-gate evaluation/decision | Production-model identity, capability contract, and final-gate configuration | Admission-rule changes invalidate final-gate results and later metrics/reports. |
| Domain/seed metric artifact | Prepared evidence and ablation-reference configuration for reference slots; exact execution digest plus content digests for each cell, seed, aggregate, raw state-trajectory, trajectory-fraction, and comparison Parquet for report-evidence slots | A changed ablation prerequisite invalidates only that reference. A changed run-side evidence file changes the metric-evidence artifact identity and invalidates table/figure source data and exports. The trajectory-fraction Parquet is derived during completed-run materialization and carries numerator, denominator, and source semantic cell keys. |
| Statistical comparison/gate artifact | Metric-evidence digest and statistical-analysis configuration (excluding publication rounding) | Statistical changes invalidate comparisons/claim/report descendants; seed metrics and checkpoints remain reusable. |
| Claim-state artifact | Current statistical comparison/gate artifact identities; exact serialized claim summary content; claim-decision procedure identity | Statistical/gate changes or any mechanically derived claim-state change invalidate the claim artifact and project-summary descendants. |
| Table/figure source data | Named report: execution-evidence digest, metric-evidence identity, evidence-file digests, rendered table/figure digests. Project report: deterministic digest of sorted current upstream manifest identities, typed references to those manifests, and rendered table/figure digests. | Data-selection, upstream identity, or rendered-content changes invalidate source data and exports. Project source data is ownerless and publishes only after mandatory report-material coverage passes. |
| Table/figure/report export | Source-data artifact identity and the relative paths of every published report product | Source-data changes invalidate the terminal export; named exports are experiment-owned and project exports are ownerless under `results/project_summary`. Rendering does not invalidate scientific products. |

The common artifact store also verifies complete state, payload length, checksum,
atomic publication, current-pointer identity, and typed artifact-parent edges.
`ArtifactDependencyKind` is included in the hash, so changing a content digest
into an artifact edge cannot preserve the same identity. Tests cover dependency
kind, ordering, producer configuration scopes, one-parent descendant changes,
shared compatible anchor reuse, checksum corruption, and report-render content
identity.

Execution records remain keyed by semantic cell plus current configuration,
code revision, and dataset-manifest provenance. They are not artifact-family
outputs. No scientific execution record was created by this audit.
