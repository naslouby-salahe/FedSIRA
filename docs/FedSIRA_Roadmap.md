# FedSIRA — Authoritative Research Roadmap

This roadmap is the standalone scientific and implementation specification for **FedSIRA**. The method, datasets, threat model, numerical configuration, experiments, statistics, claim boundaries, and execution rules are authoritative for the study. Scientific choices are not changed in response to observed results; implementation corrections follow the selective invalidation and rerun rules in Sections 25–27 without altering the scientific contract.

FedSIRA's fixed authority principle is:

> An unsupported post-reference capability first exposed by a potentially Byzantine participant cannot obtain production authority through approval of that participant's model artifact. Production authority requires a fixed source-independent capability claim, clean non-source construction, post-commitment external verification, aggregator-aware reproducibility, source-excluded robust synthesis, and a final fresh admission gate.

The source artifact may assist claim discovery but has zero direct production influence and is never an honest-path reproduction or synthesis input. The project, algorithm, CLI, and manuscript method name are **FedSIRA**.

# 1. Scientific problem, contribution boundary, and claims

## 1.1 Research problem

FedSIRA addresses safe admission of a **post-reference capability** that is initially unsupported by trusted evidence and is first exposed by a potentially Byzantine federated participant.

Before independent post-reference evidence appears, an honest unsupported capability and an adaptive Byzantine mimic can be observationally indistinguishable to the server. FedSIRA therefore does not attempt to infer trust from a more elaborate source-side score. It creates new evidence that the source does not control.

## 1.2 Core authority transition

FedSIRA replaces:

$$
\text{production authority} \leftarrow \text{approval of a source-controlled model}
$$

with:

$$
\text{production authority}
\leftarrow
\text{independent constructibility}
+
\text{cross-domain transportability}
+
\text{direct source-artifact exclusion}.
$$

## 1.3 Required mechanism

For every claim instance FedSIRA must enforce:

1. a clean/current anchor checkpoint;
2. an immutable Capability Claim Contract before reproduction outcomes are observed;
3. zero direct production weight for the source artifact;
4. honest reproduction from the anchor and non-source local evidence only;
5. reproduction commitment before verifier assignment;
6. verifier evidence fresh relative to the reproduction being verified;
7. a declared Byzantine evidence profile;
8. enough certified non-source reproduction rows to satisfy the selected synthesis rule's own admissibility condition;
9. robust synthesis with no explicit source-artifact input;
10. a final fresh gate after synthesis;
11. explicit `Dormant`, `Rejected Claim`, and `Expired` outcomes rather than forced acceptance.

## 1.4 Safe manuscript claims

The manuscript may make only the claims below, and only when the Section 35 claim registry marks the corresponding canonical claim state as supported within its stated scope.

| Claim | Exact claim boundary |
| --- | --- |
| `Unsupported Capability Problem` | Unsupported post-reference capability creates a distinct safety–adaptation problem when the source can be Byzantine and trusted evidence initially contains no positive support. |
| `Pre-Evidence Information Limit` | If the observable pre-independent-evidence transcript has the same distribution in legitimate and Byzantine-mimic worlds, a source-only admission rule cannot distinguish the two beyond its allowed error. |
| `Authority Transition` | FedSIRA changes the authority object from a source-model approval decision to independently constructed and externally re-demonstrated functionality. |
| `Direct Source Exclusion` | The source artifact is never an explicit input to final production synthesis or to the single-reproduction production update when the resolved core uses the single-reproduction path. |
| `Conditional Non-Interference` | Conditional on the same fixed Capability Claim Contract and honest authority-path execution, changing the source artifact does not change honest reproduction or source-excluded production-update computations. |
| `Malicious Source Salvage` | Useful functionality first exposed by a malicious source can be learned without directly deploying that source artifact when enough independent honest domains can construct the same capability. |
| `Proposal Assistance Value` | Proposal assistance has value only when its preregistered comparison materially reduces false launches, reproduction attempts, or post-evidence overhead without violating the specified safety/liveness constraints. |
| `Plurality Necessity` | More than one independent reproduction is necessary only when the preregistered plurality comparison defeats the single-reproduction alternative under the specified rule. |
| `External Verification Necessity` | External reproduction verification is necessary only when its preregistered comparison defeats direct synthesis from the same committed reproduction opportunities under the specified rule. |
| `Mechanism Necessity` | Necessity is component-specific and is stated only for proposal assistance, plurality, or external verification when the corresponding Section 18 survival rule passes; no generic component-necessity claim is inferred from ablations alone. |
| `Byzantine Operating Region` | Security/liveness claims are conditional on the tested `f_R=1`, `f_V=1` primary profile and are not extrapolated above the declared bound. |
| `Safe Dormancy` | A permanent singleton may remain unresolved rather than being falsely authenticated. |
| `Reproducibility Is Not Truth` | Independent reproducibility can still certify a semantically wrong function under shared label error, common spurious structure, or attacker-induced common context. |
| `Capability-Granularity Boundary` | A broad Capability Claim Contract can create false functional equivalence that a root-cause-scoped contract avoids on the specified fixture. |
| `Heterogeneity Boundary` | FedSIRA's liveness/synthesis claim is restricted to the highest tested heterogeneity regime satisfying the Section 35 boundary rule. |
| `Information-Arrival Delay` | Part of admission delay is an information-arrival cost; FedSIRA's post-evidence overhead is separately measurable. |
| `Post-Evidence Efficiency` | Efficiency claims are descriptive measurements under the specified machine/timing contract unless an explicitly specified material comparison is stated. |
| `Secondary Generalization` | The tested mechanism direction extends to the specified CICIoT2023 construction under synthetic pseudo-domains, without implying real administrative independence. |
| `IoT IDS Application` | The tested mechanism applies to the explicitly specified IoT intrusion-detection contexts; no broader deployment claim is implied. |

## 1.5 Forbidden claims

The study must not claim any of the following:

* novelty from client-side validation, reviewer voting, independent local reference models, multiple-model certification, clean retraining, Byzantine quorums, generic robust aggregation, cross-fitting, matched controls, or hypergeometric committee calculations by themselves;
* that reproducibility proves semantic truth, causal correctness, or benevolent origin;
* that administrative independence guarantees independent labels, preprocessing, threat-intelligence feeds, or environmental causes;
* that a Byzantine reproducer cannot copy a source model out of band;
* that the source has zero total causal influence; a proposal may select which predeclared claim is investigated;
* universal liveness for a capability that remains a permanent singleton;
* security above the declared Byzantine bound;
* anonymous/Sybil security;
* privacy guarantees not separately implemented and measured;
* deployment readiness from an offline experimental study;
* robustness outside the tested threat, heterogeneity, data, and context envelopes.

---

# 2. Research questions, hypotheses, and falsification logic

| Research question                                                                           | Confirmatory hypothesis                                                                                                                                             | Mandatory evidence                                                                                  | Failure consequence                                                                                                                   |
| ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Does independent construction create useful evidence unavailable to source-only review?     | Independent reproduction and fresh verification separate legitimate transferable capability from source-only malicious behavior better than source-artifact review. | `Source-Artifact Exclusion Necessity`, `Primary Confirmatory Evaluation`                            | Central authority-transition claim not supported if no material separation exists.                                                    |
| Is proposal-assisted claim opening necessary?                                               | Proposal assistance materially reduces false launches, reproduction attempts, or admission delay without worsening safety/liveness.                                 | `Proposal-Assisted Opening Necessity`                                                               | Remove proposal assistance from the core path if the survival rule fails.                                                             |
| Is more than one reproduction necessary?                                                    | Plurality materially protects against Byzantine reproduction or honest site-specific overfit.                                                                       | `Single-Reproduction Necessity`, robustness experiments                                             | Use the single-reproduction path if plurality fails the survival rule.                                                                |
| Does direct source-artifact exclusion matter?                                               | Source-excluded production reduces hidden post-production backdoor success while retaining the independently reproducible target capability.                        | `Source-Artifact Exclusion Necessity`                                                               | If false, the central source-exclusion motivation is not supported; do not proceed as if it survived.                                 |
| Does external verification/external reproduction verification add value beyond robust aggregation of independent retrains? | external reproduction verification materially prevents at least one declared failure mode that direct Krum aggregation of the same reproduction rows does not.                                     | `External Verification Necessity`, `Compromised-Reproducer Robustness`                                                | Remove external reproduction verification/cross-verification from the core method if the survival rule fails.                                                        |
| What is the Byzantine operating boundary?                                                   | Safety/liveness degrades predictably when compromised reproducer/verifier counts exceed the fixed bound.                                                           | `Compromised-Reproducer Robustness`, `Compromised-Verifier Robustness`, `Byzantine-Bound Violation` | Restrict claims to observed supported region.                                                                                         |
| Does FedSIRA safely abstain when evidence is insufficient?                                  | Permanent singleton evidence remains dormant and liveness resumes once enough independent evidence exists.                                                          | `Evidence Scarcity and Dormancy`                                                                    | Safety/liveness implementation/theory mismatch if acceptance occurs without evidence or progress fails despite satisfied assumptions. |
| What does reproducibility fail to guarantee?                                                | Shared label error, shared preprocessing confounding, and attacker-induced common context can create reproducible but semantically wrong evidence.                  | `Shared Epistemic-Failure Boundary`                                                                 | If not instantiated successfully, retain only a theoretical limitation and do not claim empirical demonstration.                      |
| Can claim under-specification create false equivalence?                                     | A broader claim contract is more likely than a narrow contract to treat different fixes as the same capability.                                                     | `Capability Under-Specification Boundary`                                                            | Narrow claim wording if granularity is not operationally meaningful.                                                                  |
| Can heterogeneity make robust synthesis erase capability?                                   | Increasing honest heterogeneity increases abstention or synthesis washout before it creates a false security guarantee.                                             | `Heterogeneous-Reproduction Boundary`                                                               | Scope liveness/synthesis claims to the surviving heterogeneity region.                                                                |
| What portion of delay is unavoidable evidence arrival?                                      | Evidence-arrival delay and protocol overhead are separately measurable; post-evidence overhead remains operationally bounded.                                       | `Admission-Delay Decomposition`, `Efficiency Measurement`                                           | Limit operational claims if overhead dominates.                                                                                       |
| Does the fixed mechanism generalize?                                                       | The fixed mechanism preserves the primary directional conclusions on a distinct IoT intrusion dataset without retuning core scientific thresholds.                 | `Secondary-Dataset Generalization`                                                                  | Generalization claim becomes `Not Supported`; primary evidence remains unchanged.                                                     |

---

# 3. System model and notation

| Symbol / term           | Definition                                                                                                                                                                    |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| $\mathcal D$            | Authenticated experimental administrative-domain set.                                                                                                                         |
| administrative domain   | One authority for Byzantine accounting. In the primary dataset, one physical IoT device is used as an explicit **domain proxy**, not as proof of organizational independence. |
| $s$                     | Source domain that exposes a proposal-assisted unsupported capability.                                                                                                        |
| $w_a$                   | Fixed clean/current anchor checkpoint.                                                                                                                                       |
| $a_s$                   | Source model artifact; committed but assigned zero direct production weight.                                                                                                  |
| $\mathcal C$            | Fixed Capability Claim Contract.                                                                                                                                             |
| $j$                     | Reproducer domain.                                                                                                                                                            |
| $r_j$                   | Reproduction update from domain $j$.                                                                                                                                          |
| $w_j=w_a+r_j$           | Reproduced model.                                                                                                                                                             |
| $g$                     | Verifier domain.                                                                                                                                                              |
| $V_g(w_j,\mathcal C)$   | `Positive`, `Negative`, or `Abstain` verifier decision.                                                                                                                       |
| $R^{cert}_{\mathcal C}$ | Certified independent reproduction rows.                                                                                                                                      |
| $A$                     | Fixed robust synthesis operator; this roadmap fixes `Krum`.                                                                                                                  |
| $r^*$                   | Source-excluded synthesized production update.                                                                                                                                |
| $f_R$                   | Maximum Byzantine reproduction rows for the primary deterministic profile: **1**.                                                                                             |
| $f_V$                   | Maximum Byzantine verifier in a primary verifier panel: **1**.                                                                                                                |
| $h_V$                   | Minimum guaranteed honest positive verifier support: **1**.                                                                                                                   |
| $q_V$                   | Positive support threshold: **2 of 3** verifier reports.                                                                                                                      |
| $\tau_k$                | First logical evidence cycle with at least $k$ eligible honest non-source evidence holders.                                                                                   |
| $T_{evidence}$          | Information-arrival component of admission delay.                                                                                                                             |
| $T_{assignment}$        | Role-assignment latency after required evidence exists.                                                                                                                       |
| $T_{reproduce}$         | Reproduction-training latency.                                                                                                                                                |
| $T_{verify}$            | External-verification latency.                                                                                                                                                |
| $T_{synthesize}$        | Krum synthesis plus final-gate latency.                                                                                                                                       |

The Byzantine unit is an administrative-domain proxy, never an individual row, packet, or repeated report. Repeated reports from one proxy count once per fixed claim/evidence window.

---

# 4. Threat model, trust assumptions, and explicit boundaries

## 4.1 Primary security setting

* authenticated cross-silo-style federation;
* exactly 9 primary experimental domain proxies;
* one source domain per claim instance;
* up to 1 Byzantine reproduction row inside the primary 5-row synthesis committee;
* up to 1 Byzantine verifier inside each primary 3-verifier panel;
* source and reproducer are excluded from the panel that verifies that reproduction;
* verifier assignment occurs only after the reproduction commitment hash exists;
* unlimited anonymous/Sybil identities are outside scope.

## 4.2 Attacker knowledge

Unless an experiment says otherwise, Byzantine participants know:

* model architecture and training code;
* preprocessing and feature schema;
* the fixed Capability Claim Contract, all thresholds, and the final Krum rule;
* the verifier algorithm;
* the distribution from which role assignments are selected;
* their own local data and all server messages legitimately sent to them.

They do **not** know before commitment:

* the realized post-commitment verifier panel for their reproduction;
* verifier-private fresh sample identities;
* final-gate sample identities.

The source and Byzantine reproducers may collude. A Byzantine reproducer may copy the source update exactly; this is an explicit attack, not an impossible event.

## 4.3 Honest-path assumptions

An honest reproducer:

* receives only the anchor, fixed Capability Claim Contract, its authorized local post-reference data, and fixed training configuration;
* never receives or reads the source artifact as a declared training input;
* cannot change Capability Claim Contract thresholds after seeing outcomes;
* commits its update before verifier assignment.

An honest verifier:

* uses only its designated fresh verifier window;
* never certifies itself;
* reports `Abstain` when evidence minimums are not met;
* evaluates the exact fixed Capability Claim Contract and no post-hoc criterion.

## 4.4 Failure boundaries that must be tested

* permanent singleton evidence;
* shared label corruption;
* shared preprocessing/common-context confounding;
* attacker-induced correlated evidence;
* Byzantine source-copy reproduction;
* honest site-specific overfit;
* heterogeneous incompatible honest reproductions;
* under-specified capability contracts;
* compromised-count violation;
* synthesis washout;
* delayed evidence arrival.

These are part of the scientific program, not optional debugging cases.

---

# 5. Capability Claim Contract

**Configuration authority:** the numerical Capability Claim Contract thresholds and evidence minima are `capability_claim.*`; numerical claim-opening, verification, synthesis, final-gate, and resource limits are the applicable `protocol.*` fields in `configs/fedsira.yaml`. The contract metric definitions, eligibility semantics, ordering rules, and failure behavior are fixed by Sections 5–7 rather than encoded as configuration strings.

Every claim instance is:

$$
\mathcal C=(\mathcal S,\mathcal M,\mathcal K,\Gamma,\Beta,\Omega).
$$

For the primary study the fixed values are:

| Component    | Exact primary definition                                                                                                                                                                              |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| $\mathcal S$ | Select local post-reference `GAFGYT_COMBO` examples plus the designated supported-control replay rows; sample membership is determined only by the immutable split manifest, domain, label, and role. |
| $\mathcal M$ | `GAFGYT_COMBO` one-vs-rest F1 on the designated fresh evaluation population.                                                                                                                          |
| $\mathcal K$ | Supported-label macro-F1 and benign false-positive rate over the 10 non-target classes.                                                                                                               |
| $\Gamma$     | Target F1 $\ge 0.80$ **and** absolute target-F1 gain over anchor $\ge 0.20$. Both conditions are required.                                                                                            |
| $\Beta$      | Supported macro-F1 drop from anchor $\le 0.02$ absolute **and** benign false-alarm-rate increase $\le 0.01$ absolute. Both conditions are required.                                                   |
| $\Omega$     | The fixed N-BaIoT feature schema, nine device-domain proxies, held-out `GAFGYT_COMBO` capability, and the exact replay/split protocol in this roadmap.                                               |

## 5.1 Evidence sufficiency

A domain may issue a non-abstaining reproduction only when its reproduction role contains at least:

* 2,000 target examples; and
* 2,000 supported-control examples in total.

A verifier or final-gate domain is adequate only when the relevant fresh role contains at least:

* 1,000 target examples; and
* 1,000 supported-control examples in total.

Proposal-assisted screening requires at least 500 target examples in its screen role.

When an evidence minimum is not met, the outcome is `Abstain`. Insufficient evidence is never converted to a negative vote or a zero-valued metric.

## 5.2 Contract immutability

The Capability Claim Contract JSON is hashed before any reproduction begins. Any change to selector, target metric, supported metrics, thresholds, or scope creates a **new claim identity** and invalidates downstream artifacts from the earlier claim.

## 5.3 Secondary-dataset claim

The secondary dataset uses the same numerical $\Gamma$ and $\Beta$ thresholds, the same metric definitions, and the same protocol semantics. Only dataset schema, class vocabulary, and target label change as explicitly defined in Section 10. No result from the secondary dataset may be used to retune the primary configuration.

---

# 6. FedSIRA state machine and non-negotiable invariants

## 6.1 States

```text
Candidate Screen       optional proposal-assisted front end or candidate-free adequacy check
Claim Open             immutable Capability Claim Contract exists and opening rule passed
Reproduction Pending   waiting for the next eligible non-source reproduction opportunity
Verification Pending   one committed row exists and its external verification is incomplete
Synthesis Pending      the resolved multi-reproduction path has the required committee, or the resolved single-reproduction path has its production update
Admitted               final fresh gate passed
Dormant                currently insufficient independent evidence to advance
Rejected Claim         adequate evidence contradicts the fixed claim or an adequate final gate fails
Expired                logical evidence-cycle horizon exhausted without terminal admission/rejection
```

`Dormant` is resumable only when the experiment supplies a later logical evidence cycle with newly adequate evidence. `Admitted`, `Rejected Claim`, and `Expired` are terminal.

## 6.2 Resource horizon

A claim may use at most:

* each of the 8 non-source domains once for an **actual scientific reproduction training attempt**; an evidence-inadequate domain that is inspected but not trained is not consumed and may become eligible at a later evidence cycle;
* 30 logical role-assignment/evidence cycles in evidence-arrival experiments.

A domain whose reproduction was trained and committed is consumed for that claim even if its row later fails certification. It is not scientifically retrained until favorable. A pure infrastructure interruption may retry the same semantic cell phase once under Section 19.

If fewer than the required production rows exist after all currently adequate unconsumed domains have been considered, the claim enters `Dormant`. If later cycles make previously unconsumed domains adequate, processing resumes in the original `Reproducer Order`. If all eight domains have actually been trained/committed without satisfying the resolved production rule, the claim remains `Dormant` for the state-trajectory contract and becomes `Expired` at cycle 30; no scientific retry is introduced.

## 6.3 Exact transition and scheduling table

Protocol work is sequential in logical authority order; parallel execution may be used only for engineering acceleration when it preserves the same commitments, timestamps/order relation, and deterministic job identities. The authoritative transition sequence is:

| Current state | Event/guard | Next state | Required action |
| --- | --- | --- | --- |
| start | proposal-assisted mode selected | `Candidate Screen` | commit source artifact, record direct production weight `0.0`, resolve screen domains |
| start | candidate-free mode selected | `Candidate Screen` | resolve the same screen-domain order without reading a source artifact |
| `Candidate Screen` | fewer than 2 screen domains adequate | `Dormant` | record adequacy counts; resume only on later evidence cycle |
| `Candidate Screen` | proposal mode, at least 2 adequate and at least 2 positive | `Claim Open` | publish immutable Capability Claim Contract identity |
| `Candidate Screen` | proposal mode, at least 2 adequate and fewer than 2 positive | `Rejected Claim` | terminal rejection |
| `Candidate Screen` | candidate-free mode, at least 2 adequate and at least 2 adequate domains have anchor target F1 `<0.50` | `Claim Open` | publish immutable Capability Claim Contract identity |
| `Candidate Screen` | candidate-free mode, at least 2 adequate but fewer than 2 satisfy anchor target F1 `<0.50` | `Rejected Claim` | terminal rejection |
| `Claim Open` | opening complete | `Reproduction Pending` | begin/resume scan of unconsumed non-source domains in `Reproducer Order` |
| `Reproduction Pending` | next domain inadequate | `Reproduction Pending` | record reproduction `Abstain`; do not consume domain; continue scan |
| `Reproduction Pending` | next domain adequate | `Verification Pending` when external verification is active; otherwise `Reproduction Pending`/`Synthesis Pending` according to resolved row count | train once from the authoritative start checkpoint, commit immutable update, consume domain |
| `Verification Pending` | fewer than 3 adequate eligible verifiers | `Reproduction Pending` | row is uncertified; record verification insufficiency; continue to next unconsumed reproducer |
| `Verification Pending` | panel complete and row fails 2-of-3 | `Reproduction Pending` | record uncertified committed row; continue |
| `Verification Pending` | panel complete and row passes 2-of-3, but resolved production-row count not reached | `Reproduction Pending` | append certified row; continue |
| `Verification Pending` | panel complete and resolved production-row count reached | `Synthesis Pending` | construct production update according to Section 18.7 resolved-core mapping |
| `Reproduction Pending` | external verification inactive and resolved production-row count reached | `Synthesis Pending` | construct production update from the required committed rows |
| `Reproduction Pending` | no currently adequate unconsumed domain and production-row count not reached | `Dormant` | await later evidence cycle or expiry |
| `Synthesis Pending` | production update/model constructed | `Synthesis Pending` | evaluate final fresh gate; Krum is used only when the resolved path requires plurality |
| `Synthesis Pending` | fewer than 6 adequate final-gate domains | `Dormant` | retain production-update artifact; a later evidence cycle may re-evaluate the same model on newly adequate final-gate roles |
| `Synthesis Pending` | at least 6 adequate final-gate domains and all final-gate predicates pass | `Admitted` | publish admission artifact |
| `Synthesis Pending` | at least 6 adequate final-gate domains and any final-gate predicate fails | `Rejected Claim` | terminal rejection |
| any nonterminal state | logical cycle reaches 30 without another terminal state | `Expired` | terminal expiry |

Reproduction candidates are never reordered by their measured quality. Once the resolved row requirement is reached, later reproducer candidates are not trained for that claim unless an experiment explicitly requires their committed rows as a comparator input.

## 6.4 Invariants

1. The source artifact has direct production weight exactly **0** in every source-excluded FedSIRA path.
2. Honest reproduction APIs reject the source artifact and any source-derived checkpoint as inputs.
3. The source does not verify its own claim.
4. A reproducer does not verify its own reproduction.
5. Verifier assignment timestamp is strictly later than reproduction-commitment timestamp.
6. One administrative-domain proxy contributes at most one independent vote to one verification panel.
7. `Abstain` remains a third outcome and is never coerced to a vote.
8. When plurality/Krum is active, the reproduction count follows Krum's admissibility requirement, not a generic `2f+1` rule.
9. Candidate-free opening remains implemented and executable regardless of the resolved opening mode.
10. When Krum is active, its input contains only the rows allowed by the resolved verification rule and never contains the source artifact.
11. Admission always requires a valid final fresh-gate artifact, including resolved single-reproduction and no-external-verification paths.
12. An experiment may not read report-test rows during training, screening, threshold choice, synthesis, or model selection.
13. The resolved core may remove proposal assistance, plurality, or external verification only through the Section 18.7 mechanical survival rules; direct source exclusion is never silently replaced by source deployment after a negative central result.

---

# 7. Exact FedSIRA procedure

## 7.1 Claim opening

### Proposal-assisted mode

1. Receive and immutably commit source artifact $a_s$.
2. Record direct production weight `0.0`.
3. Run the fixed proposal screen on three post-commitment non-source screen domains.
4. Open the predeclared claim only if at least **2 of 3** adequate screen domains are positive.
5. If fewer than 2 screen domains have adequate evidence, return `Dormant`.
6. If at least 2 are adequate and fewer than 2 are positive, return `Rejected Claim` for the proposal-assisted claim instance.

### Candidate-free mode

Use the same deterministic three-domain screen order but do not read a source model. If fewer than **2** screen domains are adequate, return `Dormant`. If at least **2** are adequate, open the same predeclared claim only when at least **2** adequate screen domains have anchor target F1 below **0.50**. Otherwise return `Rejected Claim`.

## 7.2 Proposal screen

The three screen domains are the first three eligible non-source domains in the deterministic `Screen Domain Order` derived from the master seed.

A screen domain uses a composite, read-only screen view: target rows come only from that domain's `Candidate Screen` target role, while supported controls and supported-retention metrics come only from the same domain's capped `Post-Reference Replay` supported rows. Reuse of those supported replay rows by a later honest reproduction is permitted because proposal screening is an opening/selectivity mechanism rather than final evidence; `Row Verification`, `Final Gate`, and `Report Test` remain disjoint and fresh. No target `Candidate Screen` row is ever reused for training or later verification.

For each screen domain:

1. assign the selected target-screen rows and supported-control rows independently to 5 folds using the `Screen Fold` namespace and the canonical fold rule in Section 13.5;
2. for each held-out fold, calculate anchor per-sample cross-entropy loss for held-out target rows and held-out supported-control rows;
3. use supported-control rows from the other four folds to calculate decile boundaries of supported-control anchor loss;
4. apply those boundaries to the held-out target and held-out supported-control losses, then match every held-out target to one held-out supported-control sample in the same loss decile with closest anchor loss, without replacement within that fold; ties use ascending stable sample ID;
5. concatenate the five held-out-fold match sets and define

$$
\Delta^M=\operatorname{mean}\big[CE(w_a,x)-CE(a_s,x)\big]_{x\in target},
$$

$$
\Delta^C=\operatorname{mean}\big[CE(w_a,x)-CE(a_s,x)\big]_{x\in matched\ control},
$$

$$
A=\Delta^M-\Delta^C.
$$

A screen-domain decision is `Positive` only when all conditions hold:

* $A\ge0.05$ nats/example;
* source target-F1 gain over anchor $\ge0.20$;
* supported macro-F1 drop $\le0.02$;
* benign false-alarm-rate increase $\le0.01$.

The screen is an efficiency/selectivity mechanism, not a security theorem.

## 7.3 Source-independent reproduction

For eligible non-source domain $j$:

$$
r_j=\arg\min_r
L_{CE}(w_a+r;D_j^{target}\cup D_j^{supported})
+\lambda D_{stable}(w_a+r,w_a;D_j^{supported})
+\mu\frac{|r|_2^2}{d},
$$

where:

* $D_{stable}$ is the mean KL divergence `KL(anchor_softmax || reproduction_softmax)` on supported replay rows;
* $\lambda=1.0$;
* $\mu=10^{-5}$;
* $d$ is the number of trainable parameters.

The reproduction starts from $w_a$, uses the training constants in Section 12, and produces an immutable commitment before verifier assignment.

## 7.4 External verification

For each committed reproduction:

* verifier panel size = **3**;
* source and reproducer are ineligible;
* panel members are the first 3 adequate domains in the post-commitment verifier permutation for that row;
* primary deterministic panel bound $f_V=1$;
* required guaranteed honest positive support $h_V=1$;
* positive threshold $q_V=2$.

An adequate honest verifier reports:

* `Positive` when both $\Gamma$ and $\Beta$ pass on its fresh row-verification role;
* `Negative` otherwise;
* `Abstain` when evidence minimums fail.

A reproduction row is certified iff at least **2 of 3** non-abstaining panel reports are `Positive`. If fewer than 3 eligible adequate verifiers can be assigned, that row cannot be certified in the primary deterministic profile.

## 7.5 Reproducibility certificate

The complete multi-reproduction FedSIRA path requires **5 certified reproduction rows**. Reproducer candidates are processed sequentially in the deterministic precommitted `Reproducer Order` using the transition rules in Section 6.3. The first five rows that become certified form the Krum committee. Later rows cannot replace an earlier certified row because their metric values look better.

A domain that is evidence-inadequate is skipped without consuming its one allowed scientific training attempt. A domain that trains and commits is consumed regardless of certification outcome. Processing stops as soon as five certified rows exist. If fewer than five rows are certified after all currently available eligible domains have been processed, synthesis does not run and the claim is `Dormant` until later evidence arrival or expiry. Post-collapse resolved cores that use one reproduction or omit external verification follow the explicit mapping in Section 18.7 rather than pretending to have a five-row certificate.

## 7.6 Robust source-excluded synthesis: Krum

The final synthesis operator is `Krum` with $n=5$, $f_R=1$. This satisfies the Krum worker-count condition $n\ge2f_R+3$.

For update vectors $r_1,\ldots,r_5$:

1. compute all squared Euclidean distances $|r_i-r_j|_2^2$;
2. for each $i$, select its $n-f_R-2=2$ nearest other updates;
3. define Krum score $s_i$ as the sum of those two squared distances;
4. select the update with minimum score;
5. ties are broken by lexicographically ascending reproducer-domain ID;
6. set $r^*=r_{arg\min s_i}$.

The source artifact never enters this input set.

The admissible primary committee region is therefore:

$$
\mathfrak M_{KRUM}(1)=\{n:n\ge5\},
$$

while the confirmatory implementation fixes $n=5$ exactly to prevent post-hoc committee-size choice. The original Krum resilience theorem requires the strict worker-count condition $2f+2<n$ and additionally assumes independent identically distributed honest gradient estimators together with a variance-to-gradient condition (Blanchard et al., 2017; Section 41). FedSIRA therefore imports **only the operator definition and its count admissibility requirement** into the fixed synthesis contract. It does not claim that heterogeneous local-training model deltas automatically satisfy the original Krum convergence theorem. Any empirical Byzantine-safety statement in this roadmap remains conditional on the declared evidence model, external reproduction verification/final-gate logic, and the tested heterogeneity envelope.

## 7.7 Final fresh gate

The resolved production model `w_a + production_update` is evaluated on every adequate non-source domain's `Final Gate` role. On the complete plurality path, `production_update=r^*`; on a resolved single-reproduction path it is the selected non-source reproduction update.

Admission requires all of:

* at least **6 of 8** non-source domains are adequate;
* median adequate-domain target F1 $\ge0.80$;
* minimum adequate-domain target F1 $\ge0.60$;
* macro supported-label F1, pooled by equal domain weight, drops by no more than **0.02** from anchor;
* benign false-alarm rate, pooled by equal domain weight, increases by no more than **0.01**;
* no provenance, path-required verification/certificate, or invariant failure exists. A path that mechanically omits external row verification does not fail merely because no reproduction certificate exists; its resolved-core artifact must instead record that omission explicitly.

Failure with adequate evidence produces `Rejected Claim`. Failure solely because fewer than six domains are adequate produces `Dormant`.

---

# 8. Theory and proof obligations

The manuscript theory must include the following exact results and their assumptions. These results are not allowed to become broader than their premises.

## 8.1 Pre-independent-evidence indistinguishability

If, for legitimate world $H_L$ and Byzantine-mimic world $H_B$, every measurable pre-independent-evidence transcript event has equal probability, then every possibly randomized source-only admission rule has equal acceptance probability in both worlds.

Required empirical boundary check: identify any trusted side information used by the implementation. If such information changes the transcript law, explicitly state that the theorem premise does not apply to that side information.

## 8.2 Independent evidence proposition

Independent reproduction adds distinguishing information only when its observation distribution differs between legitimate and malicious worlds. Equal reproduction/verification observation laws provide no additional statistical distinguishability.

## 8.3 Claim-conditional direct source-artifact non-interference

For two source artifacts opening the same fixed Capability Claim Contract, the honest authority-path computation graph must have no model-input edge from the source artifact to reproduction training or Krum synthesis. The implementation test is a dependency/provenance assertion, not a claim that Byzantine reproducers cannot copy the source.

## 8.4 Honest-support counting

For a verifier panel with at most $f$ Byzantine positive reports and $q$ observed positive reports, at least $q-f$ positives are honest. The primary profile uses $q=2,f=1$, guaranteeing at least one honest positive.

## 8.5 Synthesizer-specific reproduction count

The reproduction count follows the selected robust operator's own admissibility requirement. For the fixed Krum configuration, five certified rows are required for one Byzantine row. A three-row `2f+1` committee is **invalid for Krum** and cannot be presented as an equivalent Krum configuration.

## 8.6 Conditional safety/liveness

False admission risk is conditional on:

* source exclusion;
* the verifier soundness model;
* the Krum threat/geometry assumptions;
* the final-gate soundness model;
* bounded Byzantine administrative control.

Liveness is conditional on enough honest domains eventually obtaining sufficient relevant data, honest reproduction learnability, and fair deterministic role progression through eligible domains.

## 8.7 Independent-evidence delay lower bound

A protocol whose declared safety guarantee requires $k$ honest independent evidence holders cannot safely complete before $\tau_k$ under the same pre-evidence indistinguishability premise.

The empirical delay decomposition is:

$$
T_{admit}=T_{evidence}+T_{assignment}+T_{reproduce}+T_{verify}+T_{synthesize}.
$$

## 8.8 Random-committee contamination calculation

The diagnostic random-committee profile samples 3 verifiers without replacement from 7 eligible non-source/non-reproducer domains with 2 Byzantine domains in the global eligible pool. The exact probability of at least 2 Byzantine verifiers is:

$$
\frac{\binom{2}{2}\binom{5}{1}}{\binom{7}{3}}=\frac{1}{7}\approx0.142857.
$$

The tolerated diagnostic contamination risk is fixed to **0.15**. This profile is explicitly diagnostic; the primary security claim uses the deterministic panel-bound profile.

## 8.9 Conflict-quorum theory

Concurrent conflicting claims are **not** part of the primary implemented admission path. Conflict-quorum intersection may appear only as supporting theory/limitation and cannot be used as empirical security evidence in this study.

---

# 9. Primary dataset and experimental domain construction

**Configuration authority:** `datasets.primary` contains only the primary dataset identifiers, selected target, numerical feasibility thresholds, role intervals, sampling caps, and numerical scaling constants. Fixed class vocabulary, domain-proxy identity, validation behavior, hash tokens, and observed raw-data properties are authoritative in this section and the preprocessing manifests, not in YAML.

## 9.1 Primary dataset

`N-BaIoT` is the primary dataset. Acquisition uses UCI Machine Learning Repository dataset ID **442**, DOI **10.24432/C5RC8J**. The repository's first validated acquisition is fixed by a SHA-256 manifest over every downloaded archive/file. All later execution requires exact checksum identity. The official UCI record documents 7,062,606 instances, nine commercial IoT devices, no missing values, and 115 variables in its variable table; it also states that the malicious data comprise ten attacks from Mirai and BASHLITE/Gafgyt (UCI dataset 442; Section 41).

The validated release is expected to provide 115 numeric network-traffic predictors, benign traffic, and ten botnet attack subtypes from BASHLITE/Gafgyt and Mirai. The nine physical devices are used as experimental domain proxies; actual file presence and per-device attack availability are always taken from the validated raw bytes.

### 9.1.1 Raw release discovery and canonical mapping

The UCI record is the expected release reference, but execution authority is the acquired raw bytes. UCI currently exposes 27 dataset files beneath nine device directories, with per-device `benign_traffic.csv` plus `gafgyt_attacks.rar` and `mirai_attacks.rar` archives where present. The implementation must support the official archive layout and the semantically equivalent already-extracted layout without assuming that every device/attack file is present.

Canonical device-directory mapping is exact after normalizing path separators only:

| Observed official directory | FedSIRA domain proxy |
| --- | --- |
| `Danmini_Doorbell` | Danmini Doorbell |
| `Ennio_Doorbell` | Ennio Doorbell |
| `Ecobee_Thermostat` | Ecobee Thermostat |
| `Philips_B120N10_Baby_Monitor` | Philips Baby Monitor |
| `Provision_PT_737E_Security_Camera` | Provision PT-737E Camera |
| `Provision_PT_838_Security_Camera` | Provision PT-838 Camera |
| `SimpleHome_XCS7_1002_WHT_Security_Camera` | SimpleHome 1002 Camera |
| `SimpleHome_XCS7_1003_WHT_Security_Camera` | SimpleHome 1003 Camera |
| `Samsung_SNH_1011_N_Webcam` | Samsung Webcam |

Within a recognized device directory, `benign_traffic.csv` maps to `BENIGN`. A CSV inside an archive/directory whose canonical attack-family token is `gafgyt` maps by basename token `combo`, `junk`, `scan`, `tcp`, or `udp` to `GAFGYT_COMBO`, `GAFGYT_JUNK`, `GAFGYT_SCAN`, `GAFGYT_TCP`, or `GAFGYT_UDP`. A CSV inside an archive/directory whose canonical attack-family token is `mirai` maps by basename token `ack`, `scan`, `syn`, `udp`, or `udpplain` to `MIRAI_ACK`, `MIRAI_SCAN`, `MIRAI_SYN`, `MIRAI_UDP`, or `MIRAI_UDPPLAIN`. Case is ignored only for these path tokens; punctuation/whitespace is normalized to `_` before token comparison.

RAR archives are extracted read-only into `outputs/cache/preprocessing/` using the Ubuntu 24.04 `unrar` package (`1:7.0.7-1build1`) invoked non-interactively with overwrite disabled. `fedsira doctor` must verify the executable/version before preprocessing whenever a RAR archive is present. The archive SHA-256 is retained as an upstream identity and extracted bytes are separately checksummed. Extraction order never defines scientific order; an already-extracted semantically equivalent layout does not require `unrar`. Unknown device directories, ambiguous attack-family ancestry, unknown attack basenames, duplicate conflicting label mappings, encrypted/corrupt archives, or CSVs whose headers are incompatible with the validated primary predictor schema are `Data Invalid`.

If the acquired release contains more than one CSV shard for one canonical `(domain, class)`, the shards form one canonical class stream ordered by normalized relative path ascending; rows retain original file order inside each shard. If an expected class is absent, it is structurally unavailable. The implementation never fabricates a missing class or silently substitutes an alternate subtype. This rule allows the implementation to adapt to the actual official/raw release while preserving the fixed class contract.

## 9.2 Domain proxies

The primary domain proxy names, in fixed order, are:

1. Danmini Doorbell
2. Ennio Doorbell
3. Ecobee Thermostat
4. Philips Baby Monitor
5. Provision PT-737E Camera
6. Provision PT-838 Camera
7. SimpleHome 1002 Camera
8. SimpleHome 1003 Camera
9. Samsung Webcam

For deterministic hashing only, the domain proxies have these fixed implementation tokens. They are invariants of the fixed sampling/assignment streams, not configurable aliases and not manuscript-facing names:

| Domain proxy | Fixed hash token |
| --- | --- |
| Danmini Doorbell | `DANMINI_DOORBELL` |
| Ennio Doorbell | `ENNIO_DOORBELL` |
| Ecobee Thermostat | `ECOBEE_THERMOSTAT` |
| Philips Baby Monitor | `PHILIPS_BABY_MONITOR` |
| Provision PT-737E Camera | `PROVISION_PT737E_CAMERA` |
| Provision PT-838 Camera | `PROVISION_PT838_CAMERA` |
| SimpleHome 1002 Camera | `SIMPLEHOME_1002_CAMERA` |
| SimpleHome 1003 Camera | `SIMPLEHOME_1003_CAMERA` |
| Samsung Webcam | `SAMSUNG_WEBCAM` |

Whenever a domain identity participates in a deterministic hash, the implementation serializes the fixed token above; user-facing output continues to use the descriptive domain name.

Each proxy counts once for source, reproduction, verifier, and Byzantine accounting. The manuscript must call this a **device-domain proxy construction** and must not claim the dataset establishes nine independent organizations.


## 9.3 Class vocabulary

The primary classifier has 11 output classes in this exact order:

```text
0 BENIGN
1 GAFGYT_COMBO
2 GAFGYT_JUNK
3 GAFGYT_SCAN
4 GAFGYT_TCP
5 GAFGYT_UDP
6 MIRAI_ACK
7 MIRAI_SCAN
8 MIRAI_SYN
9 MIRAI_UDP
10 MIRAI_UDPPLAIN
```

A class file absent for a particular physical device is recorded as structurally unavailable for that device. It is not synthesized merely to make class counts equal.

## 9.4 Post-reference capability

`GAFGYT_COMBO` is the sole primary unsupported capability. It is completely absent from anchor training and anchor validation. It appears only in post-reference roles.

Preprocessing must verify that at least **7 of 9** device proxies have the target stream and that, after source exclusion, at least **6 non-source proxies** can satisfy final-gate evidence minimums and at least **5** can satisfy reproduction minimums. If those conditions fail, primary data validation fails and the confirmatory program is blocked; no target subtype may be silently substituted.

## 9.5 Supported classes

The supported set consists of all 10 non-target labels. Domain-local metrics include only classes with at least 100 report-test examples in that domain. Macro metrics explicitly report the number of included classes.

## 9.6 Controlled replay semantics

The original N-BaIoT malicious files do not provide a timestamp field sufficient for a natural longitudinal post-reference study. Therefore the post-reference experiment uses **controlled disjoint replay order defined by stable row order**. This is an experimental chronology, not a claim that the malicious CSV row order is an authentic deployment timeline.

For benign data, stable file order is likewise preserved; the split manifest, not ad-hoc random splitting, controls evidence roles.

---

# 10. Exact data roles, sampling, and preprocessing

All normalized role intervals are lower-inclusive and upper-exclusive: `[lower, upper)`. Guard gaps shown below are fixed methodological exclusions derived from the adjacent role boundaries and are not independent configuration fields.

**Configuration authority:** `datasets.primary.role_intervals`, `datasets.primary.sampling_caps_per_domain`, and the numerical fields in `datasets.primary.scaling`. Role semantics, fixed role hash tokens, the preprocessing hash domain separator, finite-value/duplicate behavior, and scaling procedure are fixed by this section.

For every canonical `(domain, class)` stream, let shards be ordered by normalized relative path ascending and rows remain in original file order inside each shard. Concatenate those shard orders conceptually without rewriting the raw files. Let `N` be the total stream row count and `i` the zero-based stream-global row index. All normalized role intervals use `u=i/N`; therefore role construction remains deterministic even if the validated release physically shards a class differently.

## 10.1 Supported-class role intervals

For every available supported-class stream in each domain, assign rows by normalized stable row index `(u=i/N)`:

| Interval        | Role                    |
| --------------- | ----------------------- |
| $[0.000,0.395)$ | `Anchor Train`          |
| $[0.395,0.400)$ | guard gap; never used   |
| $[0.400,0.495)$ | `Anchor Validation`     |
| $[0.495,0.500)$ | guard gap               |
| $[0.500,0.645)$ | `Post-Reference Replay` |
| $[0.645,0.650)$ | guard gap               |
| $[0.650,0.745)$ | `Row Verification`      |
| $[0.745,0.750)$ | guard gap               |
| $[0.750,0.845)$ | `Final Gate`            |
| $[0.845,0.850)$ | guard gap               |
| $[0.850,1.000]$ | `Report Test`           |

## 10.2 Target-class role intervals

For every available `GAFGYT_COMBO` stream:

| Interval        | Role               |
| --------------- | ------------------ |
| $[0.000,0.145)$ | `Source Proposal`  |
| $[0.145,0.150)$ | guard gap          |
| $[0.150,0.245)$ | `Candidate Screen` |
| $[0.245,0.250)$ | guard gap          |
| $[0.250,0.445)$ | `Reproduction`     |
| $[0.445,0.450)$ | guard gap          |
| $[0.450,0.595)$ | `Row Verification` |
| $[0.595,0.600)$ | guard gap          |
| $[0.600,0.795)$ | `Final Gate`       |
| $[0.795,0.800)$ | guard gap          |
| $[0.800,1.000]$ | `Report Test`      |

Only the selected source uses its `Source Proposal` target rows for source-candidate training. Non-source `Source Proposal` rows are unused.

For deterministic hashing only, role identities use these fixed tokens:

| Role | Fixed hash token |
| --- | --- |
| `Anchor Train` | `ANCHOR_TRAIN` |
| `Anchor Validation` | `ANCHOR_VALIDATION` |
| `Post-Reference Replay` | `POST_REFERENCE_REPLAY` |
| `Row Verification` | `ROW_VERIFICATION` |
| `Final Gate` | `FINAL_GATE` |
| `Report Test` | `REPORT_TEST` |
| `Source Proposal` | `SOURCE_PROPOSAL` |
| `Candidate Screen` | `CANDIDATE_SCREEN` |
| `Reproduction` | `REPRODUCTION` |

These tokens are fixed implementation invariants. Whenever a role participates in a deterministic hash, the implementation serializes the corresponding token above rather than treating the display name as configurable data.

## 10.3 Deterministic sampling caps

When a role contains more rows than its cap, order rows by:

```text
SHA256(canonical_bytes(dataset_file_sha256, domain_hash_token(domain_id), class_id, role_hash_token(role), original_row_index, preprocessing_sample_order_seed))
```

and take the first rows in ascending digest order. `preprocessing_sample_order_seed` is independent of master seeds because preprocessing is shared across all scenarios. It is the uint32 value **4154850028**, derived exactly as `int.from_bytes(SHA256(UTF8("FedSIRA|preprocess_sample_order|1"))[0:8], "big") mod 2^32`. It is not separately configurable. No confirmatory run may redraw samples.

| Role                              | Per-domain cap                                                                                                                                                    |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Anchor train                      | max 4,000 rows per available supported class                                                                                                                      |
| Anchor validation                 | max 1,000 rows per available supported class                                                                                                                      |
| Source proposal target            | max 4,000 target rows                                                                                                                                             |
| Source proposal supported replay  | max 400 per supported class                                                                                                                                       |
| Candidate screen target           | max 1,000 target rows                                                                                                                                             |
| Candidate matched controls        | supported pool is the same capped `Post-Reference Replay` supported view used by reproduction; exactly 1 held-out-fold control per selected target when available |
| Reproduction target               | max 4,000 target rows                                                                                                                                             |
| Reproduction supported replay     | max 400 per supported class                                                                                                                                       |
| Row-verification target           | max 2,000 target rows                                                                                                                                             |
| Row-verification supported        | max 200 per supported class                                                                                                                                       |
| Final-gate target                 | max 2,000 target rows                                                                                                                                             |
| Final-gate supported              | max 200 per supported class                                                                                                                                       |
| Report-test target                | max 2,000 target rows                                                                                                                                             |
| Report-test benign                | max 2,000 benign rows                                                                                                                                             |
| Report-test other supported class | max 500 rows per class                                                                                                                                            |

When fewer than the cap exist, use all role-eligible rows. Evidence minimums remain binding.

## 10.4 Data validation

* the ordered primary predictor schema is taken from the lexicographically first recognized canonical CSV path after extraction/discovery, after trimming surrounding ASCII whitespace from header names; it must contain exactly 115 unique predictor names, and every other recognized primary CSV must have exactly the same ordered trimmed header;
* all 115 primary predictors must parse as finite numeric values;
* any NaN or infinity causes data validation failure; no imputation is allowed;
* duplicate rows are retained because the dataset records observations, not unique entities;
* labels are derived from canonical file/path semantics and mapped only through the fixed label table;
* no report-test, final-gate, or row-verification sample can appear in training or screening roles;
* guard-gap rows are never used;
* every primary sample receives the immutable identity `sample_id = SHA256(canonical_bytes("NBAIOT_SAMPLE_ID_V1", normalized_relative_csv_path, file_sha256, zero_based_original_row_index))`; the stream-global row index is a role-construction coordinate and is not part of `sample_id`;
* an observed primary feature count other than 115, a predictor-name/order mismatch across canonical CSVs, or a nonnumeric predictor is recorded in the data-validation artifact and is `Data Invalid` because the fixed primary model/class contract assumes one common predictor schema; raw row counts and class availability may differ from documentation and are handled by the stream/availability rules above.
* the four Section 15.1 trigger features `MI_dir_L0.1_weight`, `H_L0.1_weight`, `HH_L0.1_magnitude`, and `HpHp_L0.1_mean` must exist exactly in the validated primary predictor registry; if any is absent, the primary adversarial program is not implementable under the specified attack contract and primary validation returns `Data Invalid` rather than substituting a feature.

## 10.5 Scaling

Compute global feature mean and population standard deviation from **supported-class `Anchor Train` rows only** using aggregated `count`, `sum`, and `sum_of_squares` across domains. Raw rows need not be centralized.

For feature $k$:

$$
\mu_k=\frac{\sum x_k}{N},\qquad
\sigma_k=\sqrt{\frac{\sum x_k^2}{N}-\mu_k^2}.
$$

If $\sigma_k=0$, use scale 1.0. Transform:

$$
z_k=\operatorname{clip}\left(\frac{x_k-\mu_k}{\sigma_k},-10,10\right).
$$

The scaler is fixed by hash and reused everywhere. No target/post-reference data influence scaling.

## 10.6 Preprocessing dependency fingerprint

Preprocessing artifacts use the stage-scoped dependency rules in Sections 25–27. The preprocessing dependency fingerprint includes, as applicable to the specific prepared artifact:

```text
dataset_file_manifest_hash
+ feature_schema_hash
+ class_mapping_hash
+ role_interval_spec
+ sampling_caps
+ preprocessing_sample_order_seed
+ scaling_spec
+ upstream_preparation_artifact_identities
+ preprocessing_producer_component_fingerprint
+ relevant_preprocessing_runtime_dependency_fingerprint
```

A changed material dependency produces a cache miss for the affected preprocessing artifact and its descendants only. Repository commit, output path, logging changes, and unrelated package/code changes are not preprocessing invalidation inputs. Recomputed content is checksummed before atomic publication; if the published parent identity is unchanged, existing descendants remain valid.

---

# 11. Secondary generalization dataset

**Configuration authority:** `datasets.secondary` contains only the secondary dataset identifier, selected target, and pseudo-domain partition salt. The official representation choice, pseudo-domain construction, non-finite handling, no-imputation/no-retuning rules, and reuse of primary role/sampling/evidence semantics are fixed by this section.

`CICIoT2023` is the secondary dataset. Acquisition uses the official Canadian Institute for Cybersecurity release and records the exact downloaded-file SHA-256 manifest. The study uses the official pre-extracted labeled CSV representation from the release's `CSV` directory; PCAPs are not re-feature-engineered for this study.

The target capability is `BACKDOOR_MALWARE`; all other observed canonical attack labels plus benign are supported classes. The official CIC page documents 33 attacks in seven categories over a 105-device topology, explicitly lists `Backdoor malware`, and publishes statistics for 46 predictor features. These are validation expectations, not substitutes for inspecting the acquired CSV bytes. The observed raw CSV shards determine row counts, shard counts, exact file hashes, and the ordered predictor schema used by execution subject to the deterministic rules below.

Because the processed release does not provide a one-row-to-one-organizational-domain mapping suitable for the primary Byzantine claim, this dataset is used only for **data/attack generalization**, not for a new administrative-independence security claim.

## 11.1 Secondary schema, labels, and raw-data adaptation

CSV shards are discovered recursively beneath the acquired official `CSV` dataset directory and ordered by normalized relative path ascending. Every shard must have one common header after trimming surrounding ASCII whitespace from column names. The canonical label column is the unique column whose trimmed case-insensitive name is `label`; zero or more than one such column is `Data Invalid`.

Canonical label tokens are produced by Unicode NFC normalization, trimming, uppercasing, replacing each maximal run of non-alphanumeric characters with `_`, collapsing repeated `_`, and stripping leading/trailing `_`. `BENIGNTRAFFIC` and `BENIGN_TRAFFIC` map to the single class `BENIGN`. `BACKDOOR_MALWARE` must be observed exactly after canonicalization or the secondary program is `Data Invalid`. Any two distinct raw labels that collapse to the same canonical token are allowed only when their normalized textual forms differ solely by case, whitespace, hyphen, or underscore; any other collision is `Data Invalid`.

All non-label columns are candidate predictors. A canonical header token uses the same Unicode-NFC/trim/uppercase/non-alphanumeric-to-underscore normalization defined above for labels. A column is excluded as a row identifier only when both conditions hold: (1) its canonical header token is one of `INDEX`, `ROW_ID`, `ROWID`, or `UNNAMED_0`; and (2) within every shard it is an integer sequence equal to that shard's zero-based or one-based physical row number with no duplicates. All other non-label columns must parse as numeric predictors. Unexpected additional numeric predictors are retained; missing/documentation-different predictors are not silently manufactured. All shards must resolve to the same ordered predictor names. A predictor count other than the official expected 46 is recorded as a documentation discrepancy but may execute when the observed schema is internally consistent and all other validation rules pass.

The canonical output-class registry is deterministic: `BENIGN` first, `BACKDOOR_MALWARE` second, then all remaining observed canonical labels in lexicographically ascending UTF-8 order. The model input dimension is the validated predictor count; the output dimension is the registry length. Both are derived facts.

Before role construction, every predictor is parsed to float64 for validation. Any row containing NaN, positive/negative infinity, or a value that cannot be parsed as a finite number is excluded by deterministic complete-case deletion. Its `stable_row_id`, file identity, original row index, and exclusion reason are written to `outputs/preprocessing/metadata/dataset_exclusions.parquet`; exclusion counts/rates are reported. No imputation, finite-value replacement, feature dropping based on outcomes, or silent schema repair is allowed.

`stable_row_id` is `SHA256(canonical_bytes("CICIOT2023_SAMPLE_ID_V1", normalized_relative_csv_path, file_sha256, zero_based_original_row_index))`. Duplicate feature rows are retained as separate observations because their stable identities differ.

## 11.2 Secondary domain proxies

The pseudo-domain count is derived from the fixed primary domain-proxy count in Section 9.2 and is therefore **9** for this study. For each row with canonical label `y` and `stable_row_id`:

```text
pseudo_domain = HASH_TO_INDEX(
    domain_separator="CIC_IOT_2023_PSEUDO_DOMAIN",
    values=(
        dataset_manifest_hash,
        y,
        stable_row_id,
        datasets.secondary.pseudo_domain_partition_salt,
    ),
    modulus=9,
)
```

`HASH_TO_INDEX` means `int.from_bytes(SHA256(canonical_bytes(domain_separator, *values))[0:8], "big") mod modulus`. The partition salt is `datasets.secondary.pseudo_domain_partition_salt`. These partitions are explicitly synthetic and do not represent organizations or physical devices.

## 11.3 Secondary roles

Within each canonical `label × pseudo_domain` group, order retained rows by `stable_row_id` byte value ascending, then assign the same supported/target normalized role intervals as Sections 10.1 and 10.2 using that group-local index and count. This ordering is the complete secondary chronology rule; physical CSV shard order does not otherwise influence role membership.

The same sampling caps, evidence minima, Capability Claim Contract numerical thresholds, optimizer/training parameters, model family, seed/hash logic, verifier semantics, and applicable synthesis procedure are used without retuning. The secondary dataset fits its **own** scaler from its supported-class `Anchor Train` rows across the nine pseudo-domains using the exact Section 10.5 formula/clip rule; the primary N-BaIoT scaler is never applied to CICIoT2023. If the observed real data cannot satisfy a required target-holder/evidence minimum under these roles, the affected secondary cell is `Evidence Insufficient`/`Dormant` as specified by the protocol; target labels, thresholds, pseudo-domain count, or role intervals are never changed to rescue feasibility.

No primary threshold is retuned from secondary outcomes.

# 12. Model, anchor training, source training, and reproduction training

**Configuration authority:** YAML contains only the numerical optimizer hyperparameters, batch size/gradient clip, anchor training counts/cadences, post-reference training weights/budget, and verifier-aware numerical override under `model.*`. Architecture, initialization, loss/reduction semantics, checkpoint selection, data-role access, participation/aggregation behavior, precision, and other fixed execution semantics are authoritative in this section rather than configurable strings or booleans. Dataset-derived input/output widths and trainable-parameter count remain derived facts.

## 12.1 Base classifier

The model family is a fully connected multiclass MLP. Input and output widths are dataset-derived facts, not configuration duplicates:

```text
Input(D_in)
→ Linear(D_in, 256)
→ LayerNorm(256, eps=1e-5, elementwise_affine=True, bias=True)
→ GELU(approximate="none")
→ Dropout(p=0.10)
→ Linear(256, 128)
→ LayerNorm(128, eps=1e-5, elementwise_affine=True, bias=True)
→ GELU(approximate="none")
→ Dropout(p=0.10)
→ Linear(128, 64)
→ LayerNorm(64, eps=1e-5, elementwise_affine=True, bias=True)
→ GELU(approximate="none")
→ Linear(64, D_out)
```

Expected primary values after raw-data validation are `D_in=115` and `D_out=11`; execution uses the observed validated schema/label registry and fails data validation if the primary release is incompatible with the fixed scientific class contract.

Initialization is fully specified:

* all linear weights: Xavier uniform with gain `1.0`;
* all linear biases: `0.0`;
* LayerNorm scale: `1.0`; LayerNorm bias: `0.0`.

These parameters are explicit so no scientifically consequential PyTorch layer default is inherited implicitly.

## 12.2 Common optimizer and loss constants

Cross-entropy semantics:

* class weights: none;
* reduction: arithmetic mean over the minibatch;
* label smoothing: `0.0`;
* no `ignore_index` is used by the scientific label path.

AdamW semantics:

* learning rate for anchor/standard FL: `1e-3`;
* betas: `(0.9, 0.999)`;
* epsilon: `1e-8`;
* weight decay: `1e-4`;
* `amsgrad=False`;
* `maximize=False`;
* `capturable=False`;
* `differentiable=False`;
* reference execution uses `foreach=False` and `fused=False` so backend selection is not an undocumented execution choice.

Training semantics:

* batch size: `256`;
* retain the final partial minibatch (`drop_last=False`);
* each local/centralized training invocation constructs a fresh AdamW optimizer at the start of that invocation; optimizer state persists across epochs inside that invocation and is checkpointed for recovery, but no AdamW moment state is carried from one FedAvg communication round to the next; each participating client in a new FedAvg round therefore starts from the received global model with a newly constructed optimizer;
* gradient global L2 clipping: `5.0`;
* batch order uses the deterministic hash-order sampler in Section 13 rather than an implicit data-loader RNG default;
* mixed precision: disabled for claim-bearing runs;
* model computation: float32;
* metric/statistical aggregation: float64;
* early stopping: disabled;
* checkpoint selection: final configured round/epoch, never best observed validation performance;
* optimizer gradients are cleared with `set_to_none=True`, fixed as an engineering execution semantic.

## 12.3 Anchor FedAvg

* initial global model: `Model Initialization` namespace;
* rounds: **20**;
* participation: every available one of the nine primary domain proxies each round;
* local epochs per round: **1**;
* client dropout: **0**;
* client aggregation weight: number of scientific training examples actually processed by that client in the round;
* aggregation: sample-count-weighted FedAvg;
* checkpoint cadence: every round;
* evaluation cadence: every round on `Anchor Validation`, descriptive only;
* authoritative anchor: final configured round checkpoint.

The target class is completely absent from anchor training and validation.

## 12.4 Post-reference training contract

The common post-reference budget is read only from `model.post_reference.local_epochs`, `model.optimizer.post_reference_learning_rate`, and `model.training.batch_size`; no experiment or baseline may redefine those values unless its contract names an explicit override.

The source candidate starts from the fixed anchor and uses its `Source Proposal` target rows plus `Post-Reference Replay` supported rows. Honest reproduction starts from the same anchor and uses that domain's `Reproduction` target rows plus `Post-Reference Replay` supported rows.

Both use the reproduction objective from Section 7.3. The displayed objective is the empirical objective; optimization uses the following exact deterministic minibatch procedure:

* construct one combined target+supported training sequence and order it independently in each epoch by Section 13.3; do not stratify, oversample, or duplicate rows merely to form a batch;
* `L_CE` at an optimizer step is the arithmetic-mean cross-entropy over every example in that minibatch; because the combined sequence contains each selected example exactly once per epoch, target and supported examples contribute in proportion to their selected population sizes;
* `D_stable` at an optimizer step is computed only on supported replay examples present in that same minibatch: for each such example compute `KL(anchor_softmax || current_softmax)` at temperature `1.0`, sum across classes, then arithmetic-mean across supported examples in the minibatch; when a minibatch contains zero supported examples, `D_stable=0.0` for that optimizer step and no synthetic/repeated supported row is inserted;
* the delta L2 term is evaluated on the current full trainable-parameter vector at every optimizer step;
* stability weight `lambda=1.0`;
* delta L2 weight `mu=1e-5`;
* delta normalization divisor `d` is the **derived number of trainable parameters**;
* the canonical trainable-parameter vector order is `model.named_parameters()` registration order from Section 12.1; each tensor is flattened in contiguous row-major order and concatenated. The same order is used for deltas, Krum distances, cosine similarity, clipping, and hashes.

The source artifact is not passed to the honest-reproduction code path.

## 12.5 Verifier-aware malicious training override

Only the named `Verifier-Aware Backdoor` attack overrides the common post-reference epoch count to **10** and adds triggered-backdoor loss weight **2.0**. All optimizer parameters not explicitly overridden remain references to the common post-reference configuration.

## 12.6 No test-set tuning

`Row Verification`, `Final Gate`, and `Report Test` are inaccessible to optimizer/model-selection functions by API design. The implementation test suite must demonstrate that attempts to request those roles from a training loader raise an invariant error.

# 13. Role assignment, seeds, security profiles, and deterministic ties

**Configuration authority:** only the actual seed values in `seeds_and_determinism.*` and the numerical verifier/diagnostic/synthesis counts in `protocol.*` are configurable data. Namespace names/tokens, hash serialization, ordering, quantile convention, assignment procedures, and tie-breaking are fixed deterministic rules in this section.

## 13.1 Master seeds

The exact independent master-seed family is:

```text
1103, 1217, 1321, 1427, 1543, 1667, 1777, 1879, 1999, 2081
```

The confirmatory seed count is **derived as the length of this tuple** and is not configured separately.

The fixed analysis/bootstrap and smoke seeds are the resolved values of `seeds_and_determinism.analysis_seed` and `seeds_and_determinism.smoke_seed`. Preprocessing sample ordering is master-seed independent and uses the exact `preprocessing_sample_order_seed` derivation in Section 10.3; it is not a master-seed namespace and is not separately configurable.

## 13.2 Seed namespaces and canonical hash semantics

For master seed `m` and descriptive namespace name `n`, use the fixed namespace-token table below and derive:

```text
digest = SHA256(
    UTF8(
        "FedSIRA|seed_namespace|"
        + decimal(m)
        + "|"
        + stable_hash_token(n)
    )
)
namespace_seed = int.from_bytes(digest[0:8], byteorder="big", signed=False)
                 mod 4294967296
```

The prefix, first-eight-byte extraction, big-endian unsigned interpretation, and modulus are fixed deterministic semantics, not configuration fields. The stable hash token is a cryptographic compatibility input, not the user-facing namespace name.

| Namespace | Fixed hash token |
| --- | --- |
| `Data Split` | `DATA_SPLIT` |
| `Domain Partition` | `DOMAIN_PARTITION` |
| `Model Initialization` | `MODEL_INITIALIZATION` |
| `Client Sampling` | `CLIENT_SAMPLING` |
| `Source Selection` | `SOURCE_SELECTION` |
| `Source Training` | `SOURCE_TRAINING` |
| `Attack Generation` | `ATTACK_GENERATION` |
| `Screen Domain Order` | `SCREEN_DOMAIN_ORDER` |
| `Screen Fold` | `SCREEN_FOLD` |
| `Reproducer Order` | `REPRODUCER_ORDER` |
| `Verifier Assignment` | `VERIFIER_ASSIGNMENT` |
| `Byzantine Selection` | `BYZANTINE_SELECTION` |
| `Local Training` | `LOCAL_TRAINING` |
| `Committee Draw` | `COMMITTEE_DRAW` |
| `Heterogeneity` | `HETEROGENEITY` |

`Bootstrap` is intentionally **not** a master-seed namespace because inferential bootstrap resampling uses the single fixed analysis seed `424242`; keeping both would create duplicate RNG authority.

Every cross-component hash uses canonical UTF-8 serialization with an explicit domain separator and length-prefixed fields. String concatenation without unambiguous framing is forbidden.

A child seed is always derived rather than consumed from a shared mutable RNG. For uint32 parent seed `p` and ordered identity fields `v_1,...,v_k`:

```text
DERIVE_UINT32(separator, p, v_1, ..., v_k) =
    int.from_bytes(
        SHA256(canonical_bytes(separator, p, v_1, ..., v_k))[0:8],
        byteorder="big", signed=False,
    ) mod 4294967296
```

Scientific training jobs use isolated RNG streams. `local_training_seed` is `DERIVE_UINT32("LOCAL_TRAINING_JOB", LocalTrainingNamespaceSeed, dataset_manifest_hash, start_checkpoint_identity, training_algorithm_token, domain_hash_token, scientific_training_condition_token, round_index_or_minus_one)`. `scientific_training_condition_token` contains only training-relevant semantics such as clean/source/reproduction/baseline identity, attack/heterogeneity transform, and strength; experiment names that do not change training are excluded. A source-training job analogously derives its seed from the `Source Training` namespace. Model initialization uses only the `Model Initialization` namespace seed plus the dataset/model-schema identity.

Before the first stochastic operation of a training job, Python `random`, NumPy, and PyTorch CPU/CUDA RNGs are seeded from that job's derived seed. Dropout consumes only that job-local PyTorch stream. Parallel scheduling is not allowed to change RNG outcomes: scientific training jobs either execute sequentially or in isolated worker processes initialized with their own derived seed.

## 13.3 Deterministic ordering instead of hidden RNG defaults

Where the roadmap says “permutation”, “first eligible”, or “hash order”, order candidate item IDs by ascending SHA-256 digest of:

```text
(domain_separator, namespace_seed, canonical_item_id)
```

with canonical item ID as the final tie-breaker. This rule is used for source order, screen-domain order, reproducer order, verifier candidate order, compromised-domain selection, feature selection, and deterministic sampling where a section does not define a stronger role-specific hash.

Training minibatch order for epoch `e` is the ascending hash order of:

```text
(
    "LOCAL_TRAINING_BATCH_ORDER",
    local_training_seed,
    e,
    sample_id,
)
```

Epoch numbering is zero-based within a training invocation. For FedAvg, every communication round is a new local invocation and its single local epoch is `e=0`; the round index is already part of `local_training_seed`. For a 5- or 10-epoch post-reference invocation, `e=0..4` or `e=0..9`. This avoids undocumented dependence on data-loader shuffle algorithms. Stochastic model initialization and dropout use the specified PyTorch version and the job-specific derived seeds; their RNG states are checkpointed.

## 13.4 Source selection

For each seed, order the nine domain IDs with `Source Selection`. The first domain with an available target stream is the source. No source is reselected because an outcome is unfavorable.

For the useful+backdoor scenario the source must also contain `GAFGYT_UDP`. If the first target-bearing source lacks the carrier, choose the next domain in the **same precomputed order** satisfying both structural requirements. This is feasibility selection before model outcomes exist.

## 13.5 Proposal-screen fold and matching semantics

`Screen Fold` supplies the previously unnamed `screen_fold_seed`. The screen target population is the selected `Candidate Screen` target view; the supported-control population is the same capped `Post-Reference Replay` supported view available to that domain under the common replay cap. Fold assignment for every row in either population is exactly:

```text
SHA256(domain-separated canonical bytes of (sample_id, screen_fold_seed)) mod 5
```

For held-out fold `h`, decile boundaries are quantiles `0.1, ..., 0.9` of supported-control anchor losses from folds other than `h`, using the fixed Hyndman–Fan type-7/linear quantile convention. Those boundaries bin both held-out target losses and held-out supported-control losses. Matching occurs only within held-out fold `h` and within the same decile; each supported control may be used at most once in that fold. Across all five folds, every selected target must receive exactly one unique matched control. A screen domain is adequate only when it has the configured minimum target evidence and this complete matching exists. If any fold cannot be matched without replacement, the screen report is `Abstain`; target rows are never silently dropped to make matching feasible.

## 13.6 Primary deterministic verifier profile

The configured primary profile is:

```text
verifier_panel_size = 3
max_byzantine_verifiers_per_panel = 1
required_positive_reports = 2
```

`guaranteed_honest_positive_reports` is **derived** as `required_positive_reports - max_byzantine_verifiers_per_panel = 1` and is not independently configured.

Within-bound adversarial scenarios select compromised verifier identities first using `Byzantine Selection`, then construct each panel from the post-commitment verifier order while enforcing the configured bound. Above-bound experiments deliberately select the required compromised count first and then fill remaining panel slots from adequate honest domains. Source and row reproducer remain ineligible.

## 13.7 Diagnostic random verifier profile

The diagnostic profile samples a 3-member panel without replacement from the seven eligible non-source/non-reproducer domains using `Committee Draw` hash order after commitment. The experiment condition supplies the compromised verifier count `b ∈ {0,1,2}`; the first `b` eligible identities in `Byzantine Selection` order are compromised before the panel draw. The positive threshold is two.

For a seven-domain pool, the probability of at least two compromised panel members is the hypergeometric quantity

$$
P_{\ge2}(b)=\frac{\sum_{x=2}^{\min(3,b)}\binom{b}{x}\binom{7-b}{3-x}}{\binom{7}{3}}.
$$

It equals `0` for `b=0` or `b=1` and exactly `1/7` for `b=2`. The tolerated diagnostic risk `0.15` applies to the `b=2` probability-calibration condition. The random profile never replaces the deterministic panel-bound security profile.

## 13.8 Compromised reproducer selection

For a requested compromised-reproducer count `k`, the compromised identities are the first `k` attack-feasible non-source domains in `Reproducer Order`. The attack transformation must be feasible on each selected domain; otherwise that planned cell is scientifically `Evidence Insufficient`/infeasible according to the experiment contract rather than silently substituting another attack carrier after outcomes are observed.

## 13.9 Role reuse and deterministic ties

A domain may verify multiple different reproduction rows. It may not verify its own row, and the source may not verify any row for its claim. A domain contributes at most one vote per row.

Tie rules:

* Krum score: ascending reproducer-domain ID;
* Krum neighbor distance: ascending reproducer-domain ID;
* candidate-screen matching: ascending stable sample ID;
* quantiles: type-7/linear interpolation;
* DBSCAN cluster comparison uses canonical member tuples, never library-assigned numeric cluster labels;
* deterministic order ties never depend on outcome metrics.

# 14. Final-gate and admission artifact semantics

An admission artifact is valid only if it contains immutable identities for:

* anchor checkpoint;
* source commitment when proposal-assisted;
* Capability Claim Contract;
* reproducer assignment order;
* every reproduction commitment required by the resolved production path;
* every verifier assignment/report required by the resolved verification path, or an explicit `External Verification Not Used` marker when the resolved path omits it;
* Krum configuration and input update hashes when plurality/Krum is active, or the single selected reproduction-update identity when the resolved path uses one reproduction;
* the source-excluded production update;
* final-gate sample manifest, score/evaluation artifacts, and metrics;
* seed bundle;
* semantic experiment-cell key and current Section 19 cell-phase identity;
* the dependency fingerprints of every upstream scientific artifact;
* the producer-component fingerprints and relevant runtime/dependency signatures needed to reproduce those artifacts;
* repository commit, full dependency lock, and environment/hardware record as provenance snapshots.

The repository commit and full dependency lock are recorded for reconstruction and audit, but they are not blanket cache keys. Reuse validity follows the stage-scoped dependency rules in Sections 25–27. A commit change that does not alter an artifact's material producer code, scientific configuration, relevant runtime dependencies, or upstream artifact identities does not invalidate that artifact.

The production model is `anchor + production_update`. On a plurality path, `production_update` is the Krum-selected update; on a single-reproduction path it is the selected honest/non-source reproduction update. The source checkpoint cannot be the production checkpoint and cannot be copied into the source-excluded production path by server code.

# 15. Adversarial and diagnostic transformation registry

**Configuration authority:** `attacks_and_boundaries.*` contains only numerical attack strengths/grids and genuine categorical experiment-grid choices. Trigger feature/label definitions, transformation procedures, row-selection rules, cardinality formula, evidence-arrival schedules, and attack semantics are fixed by this section; transformed-row counts are derived, never configured.

## 15.1 Useful + hidden-backdoor source

The source must simultaneously learn the legitimate target `GAFGYT_COMBO` and an unrelated hidden trigger on supported `GAFGYT_UDP` traffic.

Trigger features, after fixed standardization, are:

```text
MI_dir_L0.1_weight
H_L0.1_weight
HH_L0.1_magnitude
HpHp_L0.1_mean
```

Trigger transform: set each of the four standardized feature values to **+6.0** after clipping/scaling and before model input.

Attack target: triggered `GAFGYT_UDP` examples are relabeled `BENIGN` for malicious source training.

Confirmatory poison fraction: **5%** of source supported-replay `GAFGYT_UDP` rows, selected by attack hash order. Selected rows are **replaced in the source training view** by their triggered, `BENIGN`-relabeled versions; the corresponding clean rows are not also retained, so poisoning does not increase the scientific training-example count.

Robustness poison-fraction sweep: **1%, 5%, 10%**, using the same replacement semantics.

Post-production ASR population: clean `Report Test` `GAFGYT_UDP` rows with the trigger applied and original ground-truth label retained. ASR is the proportion predicted `BENIGN`.

## 15.2 Byzantine reproduction strategies

### `Source Copy`

For a one-shot reproduction-based method, submit the exact source update vector `a_s - w_a` as the reproduction update. The row is Byzantine by construction. For an ordinary multi-round FL/robust-aggregation method whose attack condition is mapped to `Source Copy`, the compromised client submits the exact committed source **model** as its local model in every affected round; equivalently its round delta is `a_s - w_current`. This preserves the meaning “copy the source artifact” even after the global checkpoint has moved. No local optimizer step is performed for the copied update.

### `Model-Replacement Backdoor`

For a reproduction-based method, select 10% of that malicious domain's capped `Post-Reference Replay` `GAFGYT_UDP` rows by `Attack Generation` hash order. Replace those rows in the malicious training view by triggered copies relabeled `BENIGN`, retain all other legitimate target/supported rows, train from the anchor for the standard **5 epochs**, and multiply the resulting full model-delta vector by **5.0** before commitment. The clean originals of poisoned rows are not duplicated. If the domain has no eligible `GAFGYT_UDP` carrier or the cardinality rule yields zero rows, the attack is `Evidence Insufficient`.

For a multi-round ordinary FL/robust-aggregation method, the same selected poisoned view is used in every post-reference round. The malicious client starts from that round's received global checkpoint, trains exactly the method's ordinary **1 local epoch**, and scales that round's resulting delta by **5.0** before submission. Thus a five-round post-reference FL baseline still uses five malicious local epochs total; the attack does not silently multiply its training budget.

### `Verifier-Aware Backdoor`

Use the same **10%** `GAFGYT_UDP` carrier subset and `Attack Generation` ordering as `Model-Replacement Backdoor`, but do not replace or remove the clean originals from `L_legitimate`. Instead generate triggered `BENIGN`-target copies of the selected carrier rows only for the auxiliary backdoor term and train from the anchor for **10 epochs** with:

$$
L=L_{legitimate}+2.0L_{triggered\ backdoor}.
$$

`L_legitimate` is the exact Section 12.4 clean reproduction objective, including the supported-stability regularizer. `L_triggered backdoor` is mean cross-entropy on the triggered auxiliary copies. At each optimizer step it is evaluated on the triggered copies corresponding to carrier rows appearing in the clean minibatch; if none appear, that term is `0.0` for the step. The attacker knows the verifier predicate but not realized verifier identities/samples before commitment. No model-replacement scaling is applied. In an ordinary FL/robust-aggregation baseline, the attack still uses the explicitly specified 10-epoch local override only when that experiment names `Verifier-Aware Backdoor`; this intentionally exceeds the common five-local-epoch budget as the roadmap's declared verifier-aware attack strength.

Compromised reproducer counts are **0, 1, 2**. The declared primary bound is 1.

## 15.3 Byzantine verifier behavior

Two diagnostic modes are implemented:

* `False Positive`: vote `Positive` on a malicious/failed row whenever called;
* `False Negative`: vote `Negative` on an honest row whenever called.

Verifier compromise counts tested per 3-member panel are **0, 1, 2**. Count 2 is explicitly above the declared primary bound.

## 15.4 Shared label-error boundary

For strength $p\in\{0.05,0.10,0.20\}$, select a fraction $p$ of `BENIGN` rows from the supported `Post-Reference Replay` view used by reproduction, and from the supported `Row Verification` and `Final Gate` views, in every affected honest non-source domain using `Attack Generation` hash order. Relabel those selected rows `GAFGYT_COMBO` in the **corrupted operational evidence oracle**. `Report Test` retains clean benign truth.

Evidence adequacy in this boundary experiment is computed from the labels visible to the corrupted operational oracle: relabeled benign rows count toward target evidence and no longer count toward supported-control evidence. This is intentional because the fixture tests a shared labeling failure rather than merely a post-evaluation relabel.

This fixture represents a shared threat-intelligence/labeling failure. It tests whether independent honest construction can reproduce the same wrong target under a common bad oracle.

## 15.5 Shared spurious-feature boundary

For strength $p\in\{0.25,0.50,1.00\}$, set `MI_dir_L0.1_weight=+6.0` on fraction $p$ of target `Reproduction`, `Row Verification`, and `Final Gate` rows across all affected honest non-source domains. The marker is absent from clean target `Report Test` rows.

For the diagnostic benign oracle in each domain, let `m=floor(p * n_target_report)` where `n_target_report` is that domain's selected target `Report Test` count. Select the first `m` target `Report Test` rows by `Attack Generation` hash order, compute their anchor cross-entropy losses, and match them one-to-one without replacement to benign `Report Test` rows using the same anchor-loss decile/nearest-loss procedure as Section 7.2, with type-7 deciles computed from the full benign report-test pool and ascending `sample_id` ties. If complete matching is impossible, that domain's diagnostic marker metric is `NA` with reason `Insufficient Matched Benign Report-Test Controls`; the operational protocol outcome remains valid. Apply the marker only to the matched benign copies for diagnostic scoring; the stored clean report-test view is never modified.

This tests reliance on a cross-domain spurious marker.

## 15.6 Attacker-induced common-context boundary

For strength $p\in\{0.25,0.50,1.00\}$, apply the full four-feature trigger to fraction $p$ of target `Reproduction`, `Row Verification`, and `Final Gate` evidence across honest non-source domains without changing labels. The triggered benign `Report Test` diagnostic population is constructed by the exact cardinality and anchor-loss matching rule in Section 15.5 and receives the full four-feature trigger. The clean report-test rows remain immutable and are scored separately. This represents a real common context induced by an external attacker rather than source-model parameter inheritance.

## 15.7 Capability under-specification fixture

Create two distinct root-cause strata from post-reference target evidence:

* `Root Cause A`: rows for which `int.from_bytes(SHA256(canonical_bytes("CAPABILITY_ROOT_CAUSE", sample_id))[0:8], "big") mod 2 = 0`;
* `Root Cause B`: rows for which the same value is `1`.

For `Root Cause A`, apply a +3.0 standardized shift to `MI_dir_L0.1_weight`; for `Root Cause B`, apply a +3.0 shift to `HpHp_L0.1_mean`. The marker is applied consistently to the corresponding stratum in every post-reference claim-bearing role listed in Section 15.10.

Compare three predeclared contracts:

1. `Broad Target Only`: both root causes are in-scope target rows;
2. `Root-Cause A Scoped`: only Root Cause A rows are in-scope target rows; Root Cause B target rows are excluded from this claim's target training/evidence/verification/final-gate pools rather than relabeled as supported;
3. `Root-Cause B Scoped`: only Root Cause B rows are in-scope target rows; Root Cause A target rows are excluded analogously.

Supported classes remain the ten non-target labels for all three contracts. Evidence minima apply to the in-scope target stratum after mixture construction. The excluded opposite root cause remains available only to the experiment's separate diagnostic root-cause report-test metrics, never as a supported-control class.

The purpose is not to invent a new mechanism; it tests whether Capability Claim Contract granularity is necessary for meaningful functional sameness.

## 15.8 Evidence-arrival schedules

Logical cycles are integers 0 through 12 for measurement; resource expiry remains cycle 30.

| Schedule              | Eligible non-source target-evidence holders by cycle                 |
| --------------------- | -------------------------------------------------------------------- |
| `Permanent Singleton` | 0 at every cycle                                                     |
| `One Honest Holder`   | 0 at cycle 0; 1 from cycle 2 onward                                  |
| `Gradual to Quorum`   | 0 at cycle 0; 1 at cycle 2; 3 at cycle 4; 5 at cycle 6; 8 at cycle 8 |
| `Immediate Quorum`    | all eligible non-source holders at cycle 0                           |

For every schedule, holders are the first `k` structurally target-capable non-source domains in the fixed `Reproducer Order`, where `k` is the table's holder count at that cycle; the set grows monotonically. When a non-source domain becomes a holder, its target `Candidate Screen`, `Reproduction`, `Row Verification`, and `Final Gate` roles become available from that cycle onward. Supported roles are available from cycle 0. The source's `Source Proposal` role is available from cycle 0 because the schedule models **independent non-source** evidence arrival. `Report Test` is an offline clean oracle and is not gated by logical evidence cycles.

Define `T_reproduction_evidence` as the first cycle at which the resolved method's reproduction-row requirement can be satisfied in principle: five holders for a five-row path and one holder for a single-reproduction path, additionally requiring enough holders to form any required verifier panel after source/reproducer exclusion. Define `T_evidence` for the delay decomposition as the first cycle at which **all non-source evidence required for possible terminal admission** is available, including claim opening, reproduction/verifier requirements, and the final-gate minimum of six adequate non-source domains. Therefore `Gradual to Quorum` has five-holder `T_reproduction_evidence=6` for the full Krum path but `T_evidence=8`; `Immediate Quorum` has both values `0`; schedules that never satisfy the method-specific requirement have `NA/∞` and cannot enter a finite wall-clock total.

## 15.9 Honest heterogeneity regimes

The primary natural device distributions are the reference. Additional stress regimes are:

### `Natural`

No extra transformation.

### `Quantity Skew`

Multiply each domain's post-reference target and supported sample caps by the vector:

```text
1.00, 0.90, 0.80, 0.70, 0.60, 0.50, 0.40, 0.30, 0.20
```

assigned once to **all nine domain proxies** by ascending `Heterogeneity`-namespace hash order over the fixed domain tokens. The first domain receives `1.00`, the second `0.90`, ..., the ninth `0.20`. Source exclusion merely removes the source's already-assigned multiplier; the remaining eight are not reindexed. Multiply each applicable post-reference cap and round down to an integer. Evidence minimums still apply and may cause `Abstain`.

### `Feature Shift ±0.5`

Choose the first 10 feature names ordered by `SHA256(canonical_bytes("HETEROGENEITY_FEATURE_ORDER", heterogeneity_namespace_seed, feature_name))`, ties by feature name. For each selected `(domain, feature)`, compute `d=SHA256(canonical_bytes("HETEROGENEITY_FEATURE_SIGN", heterogeneity_namespace_seed, domain_hash_token, feature_name))`; use `+` when `d[-1] & 1 = 1` and `-` otherwise, then add the resulting `±0.5` standardized units to all post-reference roles of that domain.

### `Feature Shift ±1.0`

Identical to the previous regime with $\pm1.0$ standardized-unit shifts.

These are stress tests; they do not alter anchor training.

---

## 15.10 Transformation cardinality, root-cause, and controlled-episode completion rules

Every fraction-based transformation uses the same cardinality rule unless a section gives an exact count:

```text
m = floor(fraction * eligible_population_size)
```

For any positive fraction with `m=0`, the cell is `Evidence Insufficient` for that transformation; the implementation does not silently force one transformed row. Selected rows are the first `m` rows in `Attack Generation` hash order. This fixes poison-count rounding for 1%, 5%, 10%, 20%, 25%, 50%, and 100% transformations.

Shared label-error, shared spurious-feature, and attacker-induced common-context fixtures affect **all honest non-source domains that have structurally eligible rows in that role**. The corrupted operational roles are those used by reproduction, row verification, and final admission. `Report Test` remains a clean oracle unless the experiment explicitly labels an oracle transformation; therefore operational evidence and clean truth remain separable.

The two-root-cause under-specification fixture is applied consistently to target rows in every post-reference claim-bearing role (`Source Proposal`, `Candidate Screen`, `Reproduction`, `Row Verification`, `Final Gate`, `Report Test`). Root-cause A/B membership is derived by hash parity and remains immutable across roles. The feature shifts are applied after fixed standardization and before model input. For the exact mixtures:

* `Balanced 50/50`: let `k=min(n_A,n_B)` and select `k` rows from each stratum by hash order;
* `A-Dominant 80/20`: let `k=min(floor(n_A/4), n_B)` and select `4k` A rows plus `k` B rows by hash order.

Thus 50/50 and 80/20 are exact derived cardinalities; no separate sample counts are configured.

`false_same_capability_certification_rate` is defined only for the `Broad Target Only` contract because only that contract asserts equivalence across both root-cause strata. A broad-contract certified row is a false-same-capability certification when, on the same fresh verifier evidence, exactly one of the counterfactual A-scoped or B-scoped Capability Claim Contract predicates passes and the other fails. The denominator is the number of broad-contract certified rows; zero denominator is `NA`. Scoped contracts report their own certified yield and root-cause performance but do **not** receive an artificial false-equivalence rate. Section 35 tests the seed-level broad false-equivalence rate against zero with the specified material threshold rather than comparing it to an undefined scoped rate.

The proposal-collapse controlled episodes are fully instantiated before execution:

* `Legitimate Target Capability`: standard clean source adaptation on `GAFGYT_COMBO` plus supported replay.
* `Generic Hard Supported Examples`: no target rows are supplied to source adaptation. For each supported class, use the highest anchor-cross-entropy decile of source `Post-Reference Replay` rows, with the same configured per-class replay cap; train the source candidate under the post-reference budget on those true supported labels. The fixed claim is still `GAFGYT_COMBO`.
* `Irrelevant Source Improvement`: before confirmatory outcomes, choose the non-target, non-benign supported class with the largest mean anchor cross-entropy on source `Anchor Validation` (ties ascending class ID); adapt only on that class's source `Post-Reference Replay` rows plus the ordinary supported-stability replay. The fixed claim remains `GAFGYT_COMBO`.
* `Useful Backdoored Source — 5%`: Section 15.1 exactly.

These negative episodes are deterministic and do not tune a new target after observing the source model.

For `Shared Epistemic-Failure Boundary`, “clean-oracle degradation is material” uses the numerical thresholds in `attacks_and_boundaries.clean_oracle_materiality`: at least one of the target-F1 decrease, supported-macro-F1 drop, or benign-false-alarm-rate increase thresholds is exceeded relative to the matched uncorrupted cell.

# 16. Baseline contracts

**Configuration authority:** `baselines.*` contains only baseline-specific numerical budgets, thresholds, and counts. Baseline identities, mechanism definitions, shared-budget derivations, distance/quantile procedures, review semantics, and the validation fixture map are fixed by this section and are not configuration prose.

All baselines use the same fixed preprocessing, domain mapping, anchor checkpoint, model architecture, seed pairing, report-test populations, and primary metrics unless the baseline's scientific mechanism requires a documented difference. No baseline may use report-test or final-gate rows for tuning.

The baseline registry deliberately separates **mechanism-faithful common-framework adaptations** from direct paper-result reproduction. This study compares mechanisms under one common experimental substrate; it does not claim to reproduce every published paper's original benchmark number.

## 16.1 Common budget rules

* Standard FL baselines: 20 rounds, 1 local epoch/round, full participation where their mechanism permits it.
* Post-reference one-retrain or recovery step: at most 5 local epochs per participating domain unless a baseline contract below states otherwise.
* FedSIRA's additional reproductions/verifications are not artificially hidden; their extra compute/communication is measured.
* Baselines do not receive extra target labels, extra post-reference windows, extra tuning seeds, or access to source-private data beyond what their declared mechanism receives.
* Thresholds are fixed from anchor-validation or other explicitly allowed pre-execution data only.

For any ordinary post-reference FL baseline that trains multiple domains in rounds, the source domain's target view is its capped `Source Proposal` target rows and every non-source domain's target view is its capped `Reproduction` target rows; all domains use their capped `Post-Reference Replay` supported rows. A domain with no available target view participates with supported replay only when the baseline contract allows full participation. This rule is the common post-reference data-access contract for `FedAvg Reference`, `Secure Continual Assessment Reference`, recovery FedAvg, the FLCert-style group adaptation, filtering/clustering baselines, and `Krum Robust Aggregation Reference` unless a baseline section states a stricter source-exclusion rule.

## 16.2 Core and mechanism baselines

### `Local-Only Reference`

Each domain trains the base MLP for 20 epochs on its own `Anchor Train` supported data. No federation. The final local checkpoint is evaluated only on that domain's report population. Purpose: establish no-sharing reference.

### `Centralized Reference`

Pool the same capped anchor-training rows centrally, train the same base MLP for 20 epochs using AdamW and batch 256, and evaluate using identical report roles. This is a context upper/reference control, not a security equivalent.

### `FedAvg Reference`

The exact 20-round anchor FedAvg protocol. For post-reference adaptation, ordinary FedAvg fine-tunes 5 rounds with one local epoch per eligible domain using post-reference data, including the source when the scenario makes it available. Purpose: standard collaborative control.

### `Client Review with Direct Source Admission`

Mechanism-faithful source-review baseline:

1. source trains the candidate as specified;
2. assign 3 non-source reviewers after source commitment;
3. each reviewer evaluates the fixed Capability Claim Contract on the composite screen view defined in Section 7.2: target `Candidate Screen` rows plus supported `Post-Reference Replay` screen-control rows;
4. source artifact is admitted directly when at least 2 of 3 reviewers are positive;
5. production model is the source candidate itself.

This intentionally tests review of a source-controlled model rather than independent construction.

### `Client Review then One Independent Retrain`

Run `Client Review with Direct Source Admission`; if review passes, discard the source weights for training and select the first eligible non-source reproducer in the precommitted order. Train one clean reproduction for 5 epochs and require one fresh verifier to pass the Capability Claim Contract. Production is that one reproduction. Purpose: predeclared review→retrain composition with minimal plurality.

### `One Independent Retrain`

No source review. Select the first eligible non-source reproducer, train one clean reproduction, and require one fresh non-source verifier. Production is that reproduction if the verifier passes. Purpose: minimum constructive alternative.

### `Candidate-Free Full Path`

Open the claim from confirmed anchor failure and then execute the exact downstream FedSIRA reproduction, verifier, five-row certificate, Krum synthesis, and final-gate path. Only claim opening differs.

### `Multiple Retrains with Direct Krum`

Generate exactly the same candidate reproduction rows and deterministic 5-row committee opportunity as FedSIRA, but do **not** externally certify rows. Once the first 5 non-abstaining committed reproduction rows exist, run the exact same Krum operator and final fresh gate. Purpose: isolate the value of cross-verification/external reproduction verification.

### `Three-Row Coordinate-Median Alternative`

Diagnostic alternative for the generic `2f+1=3` comparison. With 3 reproduction rows and assumed $f=1$, output the coordinate-wise median. This is a different synthesis operator and must never be described as a 3-row Krum variant. It exists only to show the cost/behavior of a different operator with a different admissibility structure.

## 16.3 Prior-art family representatives

### `Multiple-Model Certified Ensemble`

FLCert-style mechanism representative:

* split the 9 domains into 3 deterministic disjoint groups of 3 using `Domain Partition` seed;
* train one 20-round FedAvg model per group with all group members participating;
* inference uses majority vote over the 3 model argmax class predictions; if all three argmax labels differ, compute the arithmetic mean of the three softmax probabilities for each of those three tied labels, choose the tied label with highest mean probability, and break any remaining exact tie by lowest class index;
* post-reference target adaptation uses the same 5-epoch local budget within each group.

Purpose: compare to multiple separately trained models plus ensemble certification without the FedSIRA capability-admission lifecycle.

### `Independent Local Reference with Source Admission`

SureFED-style mechanism representative:

* each reviewer has a local reference model trained for 20 epochs on its own anchor data;
* after source commitment, 3 reviewers compare source-candidate Capability Claim Contract behavior with their clean local reference behavior on the composite screen view from Section 7.2;
* a reviewer votes positive only if the source candidate satisfies the fixed target/support Capability Claim Contract on that screen view and does not exceed the local reference supported harm;
* 2 of 3 votes admit the **source artifact**.

Purpose: test independent clean local reference models as trust evidence while keeping the production object source-controlled.

### `Update Reconstruction Filter`

FedREDefense-style mechanism representative:

* for every standard FL client update, reconstruct a plausible update by one local epoch on all capped domain `Anchor Validation` rows as specified in Section 16.5;
* reconstruction error is squared L2 distance between submitted and reconstructed update, normalized by submitted-update squared norm plus $10^{-12}$;
* rejection threshold is the **95th percentile** of reconstruction errors from known-honest calibration updates generated before confirmatory attack execution;
* accepted updates enter sample-count-weighted FedAvg.

The threshold is fixed once from calibration and is never recalculated from attack/test outcomes.

### `Density-Cluster Trimmed Mean`

FedDBC-style IoT collusion-defense representative:

1. L2-normalize submitted update vectors;
2. compute pairwise cosine distance;
3. DBSCAN with `eps=0.25`, `min_samples=2`;
4. select the largest non-noise cluster; ties choose the cluster with smallest mean pairwise cosine distance, then lowest cluster label;
5. aggregate selected raw updates with coordinate-wise trimmed mean removing one largest and one smallest coordinate when cluster size $\ge3$, otherwise arithmetic mean.

Purpose: direct IoT/collusion defense comparator. It is a common-framework mechanism adaptation, not a claim of reproducing publisher-reported numbers.

### `Secure Continual Assessment Reference`

Secure federated continual-learning family representative:

* confirmed anchor target failure triggers 3-reviewer benign-task assessment;
* 2 of 3 positive reviewers authorize 5 post-reference FedAvg rounds over all eligible domains, including the source;
* production is the resulting FedAvg model.

This tests “assess whether a new task is benign, then continue learning” without source-excluded reproduction certification.

### `Recovery after Source Admission`

Recovery-family representative:

1. source artifact is admitted after `Client Review with Direct Source Admission`;
2. evaluate the fresh `Row Verification` window;
3. if the ordinary supported Capability Claim Contract fails or the fresh triggered-ASR diagnostic exceeds the preattack threshold calibrated in Section 16.5, roll back to the anchor;
4. retrain 5 epochs using non-source reproduction evidence pooled through standard FedAvg;
5. apply the same final fresh gate.

This intentionally models repair after source influence, contrasting with FedSIRA's pre-authority construction.

### `Source-Update Sanitization Reference`

Useful-information-preservation family representative:

* calculate per-coordinate absolute clipping bounds from known-honest anchor-validation updates as the 95th percentile of absolute coordinate values;
* clip the source update coordinate-wise to those bounds;
* apply the clipped source update to the anchor;
* require 2-of-3 client review before production.

Purpose: test sanitizing/retaining useful source information rather than excluding the source artifact.

### `Krum Robust Aggregation Reference`

Standard robust-aggregation reference using Krum with `(n=5,f=1)`, identical score/tie semantics to FedSIRA but with ordinary round-level client updates and no capability-specific external reproduction verification. Post-reference adaptation is exactly **5 communication rounds × 1 local epoch**. In each round:

1. determine the five participants before local training. In a clean condition, order all post-reference-eligible domains by `Client Sampling` hash order for `(master_seed, round_index)` and take the first five. In a condition with a designated compromised ordinary-FL participant, place that preselected compromised domain in the five-member set, then fill the remaining four positions with the first eligible uncompromised domains in the same order; this feasibility inclusion is based only on the declared attack condition, never outcome metrics;
2. every selected participant starts from the current global model and trains one local epoch under the common post-reference data contract;
3. apply the declared malicious round-update transformation, if any, after local training;
4. run Krum on exactly those five submitted deltas and set the next global model to `current_global + krum_selected_delta`.

Participant selection is recomputed deterministically per round from the round index. If fewer than five eligible domains exist, the cell is `Evidence Insufficient`. The final round-5 checkpoint is the production object evaluated by the experiment.

## 16.4 Baseline fairness

Every comparator must use the predeclared information access, architecture, training/post-reference budget, calibration evidence, source-artifact access, aggregation/synthesis rule, and evaluation roles defined in this section. Any scientifically meaningful deviation from the shared protocol must be explicit before primary results. A technically incompatible baseline remains `Invalid`; it is never silently replaced after outcomes are visible.

---

## 16.5 Baseline implementation completion rules

The common-framework prior-art representatives are intentionally adaptations, not publisher-number reproductions. Their previously implicit mechanics are specified here:

### Review-style baselines

Any 3-reviewer baseline uses the same post-commitment adequate-reviewer ordering as `Verifier Assignment`, excludes the source, and requires exactly 2 positive reports. Fewer than 3 adequate reviewers yields `Dormant`; three adequate reviewers with fewer than 2 positives yields `Rejected Claim`.

For `Client Review then One Independent Retrain` and `One Independent Retrain`, the single fresh verifier is the first adequate eligible domain in the post-commitment `Verifier Assignment` order, excluding the source and reproducer. It uses the ordinary Capability Claim Contract: positive admits; negative rejects; if no adequate eligible verifier exists after scanning the fixed order, the result is `Dormant`.

`Independent Local Reference with Source Admission` uses the local reference as an additional non-inferiority constraint: reviewer positivity requires the source candidate to pass the ordinary target Capability Claim Contract and to have supported macro-F1 no more than `0.02` below that reviewer's local reference and benign false-alarm rate no more than `0.01` above that reference.

`Secure Continual Assessment Reference` uses the same 3-reviewer Capability Claim Contract assessment of the committed source candidate to authorize continued learning; if authorized, it executes exactly 5 FedAvg rounds × 1 local epoch over all eligible domains including the source.

### FLCert-style ensemble

The ensemble group count is the configured numerical value `baselines.multiple_model_certified_ensemble_group_count`; group size is derived from the validated nine-domain primary population. Group membership is deterministic by `Domain Partition`. Post-reference adaptation is exactly 5 FedAvg rounds × 1 local epoch within each group, preserving the common five-local-epoch budget. If a group has no target-bearing eligible member, its adaptation round contains supported data only; no synthetic target rows are introduced.

### Reconstruction-filter calibration

`Update Reconstruction Filter` uses **all capped `Anchor Validation` rows** for the domain-specific one-epoch reconstruction step; there is no hidden distilled-subset size. For a submitted client delta from round `r`, the reconstructed client starts from the exact same round-start global checkpoint and trains one fresh-optimizer local epoch on that client's `Anchor Validation` rows using the ordinary anchor optimizer contract; reconstruction error compares the submitted and reconstructed deltas relative to that common start checkpoint. Known-honest calibration errors are generated for every client update in every one of the 20 anchor rounds, giving the derived calibration count `primary_domain_count × anchor_round_count = 180` when all nine domains are present. The rejection percentile is `baselines.reconstruction_filter.calibration_percentile`; the type-7 quantile procedure is fixed by Sections 13 and 18. Accepted submitted deltas are reweighted by their scientific sample counts over the accepted set only. If all updates are rejected in a post-reference round, the global model remains unchanged for that round and the no-op is recorded.

### Density-cluster baseline

DBSCAN is called with `metric="precomputed"` on the explicitly computed cosine-distance matrix, `eps=0.25`, `min_samples=2`, and no sample weights. Cosine distance is defined as `1-cos(u,v)` when both update norms are positive, `0` when both updates are exactly zero, and `1` when exactly one update is zero; zero vectors therefore remain deterministic rather than relying on a library-specific normalization convention. Non-noise clusters are canonicalized by their lexicographically sorted member-domain tuple. Largest-cluster ties use lowest mean within-cluster cosine distance, then lexicographically smallest member tuple. If no non-noise cluster exists, the round is a recorded no-op; no fallback aggregation over rejected/noise updates is permitted.

### Recovery baseline

`Recovery after Source Admission` calibrates its backdoor alarm before confirmatory attack execution. On the fixed anchor, apply the fixed Section 15.1 trigger to available `GAFGYT_UDP` `Anchor Validation` rows per domain; compute each domain's triggered-to-`BENIGN` rate; set the alarm threshold to the type-7 95th percentile across defined domain rates. Fresh `Row Verification` triggers rollback when either supported-retention constraint fails on that window—supported macro-F1 drop from anchor exceeds `0.02` or benign-FAR increase exceeds `0.01`—or triggered-to-`BENIGN` rate exceeds this fixed threshold. The recovery detector does not use the target-F1 predicate as a rollback trigger. Recovery itself is exactly 5 FedAvg rounds × 1 local epoch over eligible non-source reproduction data, followed by the standard final gate.

### Source-update sanitization

Per-coordinate clipping bounds are calibrated from the same derived set of 180 known-honest anchor-round client updates; for each coordinate use the type-7 95th percentile of absolute update magnitude. Reviewers evaluate the **clipped candidate** (`anchor + clipped_source_delta`), not the unclipped source model.

### Parameter-similarity ablation

`Parameter-Similarity Certification` operates after five committed non-source reproduction rows exist. For each row, compute cosine similarity to the arithmetic mean of the other four rows. If either vector has zero L2 norm, similarity is `NA` and that row is not certified. Otherwise a row is certified when similarity is at least `0.90`. No certification is attempted with fewer than five committed rows.

### Same-context verifier ablation

For each reproducer, compute its anchor-train standardized feature-mean vector and every eligible verifier's corresponding vector. Choose the three adequate eligible verifiers with smallest Euclidean distance to the reproducer vector; ties use ascending domain ID.

### Source-release-after-certificate ablation

The source artifact is treated as the candidate under **one ordinary 3-member external verifier panel**, followed by the standard final gate. This ablation does not manufacture five independent source rows and is not described as a Krum/external reproduction verification reproduction certificate. The existing descriptive variant name refers to full external functional checking, not five-row independence.

### Baseline validation fixture map

The 17 baseline-validation cells are exactly one cell per baseline. The fixture is predeclared by mechanism family rather than chosen after results:

* ordinary utility references (`Local-Only Reference`, `Centralized Reference`, `FedAvg Reference`, `One Independent Retrain`, `Candidate-Free Full Path`, `Multiple-Model Certified Ensemble`): `Legitimate Target Capability`;
* source-authority/review/recovery/sanitization references: `Useful Backdoored Source — 5%`;
* robust-update/filtering references (`Multiple Retrains with Direct Krum`, `Three-Row Coordinate-Median Alternative`, `Update Reconstruction Filter`, `Density-Cluster Trimmed Mean`, `Krum Robust Aggregation Reference`): one `Model-Replacement Backdoor` compromised update authority; reproduction-based methods map it to the first attack-feasible reproducer, while ordinary-FL/filtering/clustering methods map it to the first attack-feasible post-reference client;
* `Independent Local Reference with Source Admission` and `Secure Continual Assessment Reference`: `Useful Backdoored Source — 5%`.

This fixture map is authoritative for baseline validation; the implementation encodes it as the Section 16 contract and never chooses a fixture based on observed performance.

# 17. Metric registry and mathematical definitions

All metric functions live in one registry and return both value and denominator metadata. Stored metrics use float64 and are never rounded before comparisons.

Let $TP_c,FP_c,FN_c,TN_c$ denote one-vs-rest counts for class $c$.

## 17.1 Classification metrics

### Accuracy

$$
Accuracy=\frac{\sum_c TP_c}{N}.
$$

Range ([0,1]); higher is better.

### Precision for class $c$

$$
Precision_c=\frac{TP_c}{TP_c+FP_c}.
$$

If denominator is zero, value is `NA`.

### Recall / true-positive rate for class $c$

$$
Recall_c=TPR_c=\frac{TP_c}{TP_c+FN_c}.
$$

If denominator is zero, `NA`.

### False-positive rate

$$
FPR_c=\frac{FP_c}{FP_c+TN_c}.
$$

### False-negative rate

$$
FNR_c=\frac{FN_c}{FN_c+TP_c}.
$$

### True-negative rate

$$
TNR_c=\frac{TN_c}{TN_c+FP_c}=1-FPR_c.
$$

### F1 for class $c$

$$
F1_c=\frac{2TP_c}{2TP_c+FP_c+FN_c}.
$$

If the denominator is zero, `NA`.

### Balanced Accuracy

For multiclass reporting:

$$
BalancedAccuracy=\frac{1}{|C_{valid}|}\sum_{c\in C_{valid}}Recall_c.
$$

### Macro-F1

$$
MacroF1=\frac{1}{|C_{valid}|}\sum_{c\in C_{valid}}F1_c.
$$

Classes with undefined F1 are excluded and the valid-class count is reported. Macro-F1 is never weighted by support.

### Weighted F1

$$
WeightedF1=\frac{\sum_{c\in C_{valid}}n_cF1_c}{\sum_{c\in C_{valid}}n_c}.
$$

### Target F1

Primary claim-bearing capability metric:

$$
TargetF1=F1_{GAFGYT_COMBO}.
$$

Secondary target is `BACKDOOR_MALWARE` with the same definition.

### AUROC

One-vs-rest area under the ROC curve computed from unrounded softmax probability of the class. Multiclass `Macro AUROC` is the unweighted mean across classes with both positive and negative examples.

### AUPRC

One-vs-rest area under the precision-recall curve using trapezoidal integration over recall-sorted operating points. `Macro AUPRC` is the equal-class mean over defined classes.

AUROC/AUPRC are descriptive secondary metrics, not primary claim-selection criteria.

## 17.2 Capability Claim Contract metrics

### Target capability gain

$$
\Delta_{target}=TargetF1(w)-TargetF1(w_a).
$$

Higher is better.

### Supported macro-F1 harm

$$
H_{macro}=MacroF1_{supported}(w_a)-MacroF1_{supported}(w).
$$

Lower is better; negative values mean improvement. Capability Claim Contract requires $H_{macro}\le0.02$.

### Benign false-alarm-rate increase

The IDS false-alarm rate on benign traffic is **not** the one-vs-rest FPR of the `BENIGN` class. It is:

$$
BenignFAR(w)=\frac{\#\{y=BENIGN\ \land\ \hat y\neq BENIGN\}}{\#\{y=BENIGN\}}.
$$

The Capability Claim Contract change is:

$$
\Delta BenignFAR=BenignFAR(w)-BenignFAR(w_a).
$$

Lower is better; Capability Claim Contract requires $\Delta BenignFAR\le0.01$. Generic one-vs-rest `FPR_c` remains available as a class metric but is never substituted for benign false alarms.

## 17.3 Security and admission metrics

### Attack Success Rate

For triggered supported-attack examples whose ground-truth class remains `GAFGYT_UDP`:

$$
ASR=\frac{\#\{\hat y=BENIGN\}}{\#\{triggered\ GAFGYT\_UDP\ examples\}}.
$$

Compute ASR within each non-source domain with a defined `GAFGYT_UDP` report-test population, then equal-weight the defined domain ASRs for the seed-level metric. It is `NA` when the scenario/dataset has no specified trigger or no defined carrier population.

### Malicious admission rate

`malicious_admission` is a per-seed binary provenance/security outcome, not a synonym for ordinary claim admission. It is defined only when the scenario contains a predeclared compromised source, reproducer, verifier-assisted malicious row, or ordinary-FL client update. It equals `1` iff the method reaches `Admitted` **and** the admitted production object has a nonzero authority-path dependency on a compromised production contributor under the following exact rules:

* direct source deployment, clipped/sanitized source deployment, or any source-derived production update from a compromised source => compromised production contributor;
* a single-reproduction production model => compromised iff the selected reproduction row is compromised;
* Krum => compromised iff the Krum-selected row is compromised; presence of a rejected/nonselected malicious row alone does not count;
* FedAvg, ensemble/group FedAvg, reconstruction-filtered FedAvg, density-cluster aggregation, or another averaging baseline => compromised iff at least one accepted compromised post-reference client update receives nonzero aggregation/ensemble ancestry in the final production checkpoint;
* a rollback to the clean anchor followed solely by source-excluded honest recovery removes prior source/update ancestry; the recovered production object is not marked compromised solely because an earlier discarded artifact was malicious;
* a compromised verifier does not by itself create malicious admission. It contributes to `malicious_admission=1` only when its behavior enables a compromised production row/object to become admitted.

Then

$$
MAR=\frac{\sum malicious\_admission}{\#\{eligible\ seed\ instances\ with\ a\ malicious-authority\ fixture\}}.
$$

Cells without a malicious-authority fixture report MAR as `NA`, not zero.

### Legitimate admission rate

`legitimate_admission` is defined when the scientific scenario contains the real target capability, including scenarios where that legitimate capability is first exposed by a malicious/backdoored source. It equals `1` iff the protocol terminal outcome is `Admitted`, otherwise `0` for `Dormant`, `Rejected Claim`, or `Expired`. Generic-hard-supported and irrelevant-source-improvement proposal episodes do not contain the target capability and therefore have `legitimate_admission=NA`.

$$
LAR=\frac{\sum legitimate\_admission}{\#\{eligible\ seed\ instances\ containing\ the\ legitimate\ target\ capability\}}.
$$

A scenario may legitimately have **both** LAR and MAR defined: for example, `Useful Backdoored Source — 5%` contains useful target functionality while also containing a compromised source authority object. LAR measures availability; MAR measures whether compromised authority reaches production.

### Abstention/dormancy rate

Every report must distinguish:

* verifier abstention rate = abstaining verifier reports / assigned verifier reports;
* reproduction abstention rate = evidence-insufficient reproduction opportunities / assigned reproduction opportunities;
* dormant claim rate = claim instances ending `Dormant` at the evaluation horizon / eligible claims.

## 17.4 Cross-domain distribution metrics

### Worst-domain target F1

Minimum defined target F1 across adequate honest domains.

### 10th-percentile domain target F1

Hyndman–Fan type 7 / linear interpolation percentile at 0.10 over adequate-domain target F1 values.

### Domain disparity

$$
Disparity=max(TargetF1_d)-min(TargetF1_d).
$$

### IQR

$$
IQR=Q_{0.75}-Q_{0.25},
$$

using type-7/linear quantiles.

### Coefficient of variation

For a positive-valued metric vector $x$:

$$
CV=\frac{s(x)}{\bar x},
$$

where $s$ is sample standard deviation with `ddof=1`. If $\bar x=0$, `NA`.

## 17.5 Candidate-screen metrics

A proposal instance has a post-execution **clean proposal oracle** only for evaluating screen selectivity; the oracle is never available to opening/training. Evaluate the committed source candidate on the clean `Report Test` roles of all non-source domains using the same target/support metric definitions and equal-domain aggregation as Section 17.8. The source proposal is `oracle-valid` iff the aggregate target F1 is at least `0.80`, target-F1 gain over the anchor is at least `0.20`, supported macro-F1 drop is at most `0.02`, and benign-FAR increase is at most `0.01`. At least 80% of the eight expected non-source domains must have the required defined oracle metrics; otherwise the oracle label is `NA`.

* **false launch rate:** proposal-assisted claim instances for which opening launches at least one actual downstream reproduction-training attempt while the clean proposal oracle is `oracle-invalid`, divided by proposal instances with an adequate screen decision and defined clean proposal oracle;
* **reproduction attempts:** number of distinct domains for which scientific reproduction training actually starts before terminal state; an evidence-inadequate inspected domain is an abstention opportunity but not a training attempt;
* **proposal-screen differential `A`:** Section 7.2.

## 17.6 Delay metrics

Measured in two forms: logical evidence cycles and real wall-clock seconds. `T_evidence` is the method-specific admission-readiness cycle defined in Section 15.8; `T_reproduction_evidence` is additionally reported for the reproduction-row lower-bound analysis. Logical cycles are never added numerically to wall-clock seconds. The decomposition is represented as the ordered pair

```text
logical_information_arrival = T_evidence cycles
post_evidence_wall_clock_seconds = T_assignment + T_reproduce + T_verify + T_synthesize
```

and the symbolic study equation remains

$$
T_{admit}=T_{evidence}+T_{assignment}+T_{reproduce}+T_{verify}+T_{synthesize}
$$

with unit metadata attached to every component. A deployment-specific cycle duration would be required before constructing a single numeric total in seconds.

Because Section 6.3 defines a sequential authority path, timer intervals do not overlap:

* `T_assignment`: monotonic elapsed seconds from the first post-evidence protocol action until the first required training/evaluation compute segment begins, plus subsequent pure role/panel/committee-selection intervals between compute segments; it excludes model training, scoring, and final-gate evaluation;
* `T_reproduce`: monotonic elapsed seconds spent in required source-independent reproduction/local-update training on the protocol critical path, from training-call entry through committed-update publication;
* `T_verify`: elapsed seconds from each post-commitment verifier-assignment publication through completion/publication of the verifier reports required to decide that row, including verifier scoring and metric computation; sum these sequential intervals for the method; it is `0` when the resolved method omits external verification;
* `T_synthesize`: elapsed seconds from production-row set completion through production-update construction and completion of the final fresh gate. It includes Krum when plurality is active; on a single-reproduction path it includes only production-update selection/validation plus final-gate evaluation.

Post-evidence overhead is:

$$
T_{post}=T_{assignment}+T_{reproduce}+T_{verify}+T_{synthesize}.
$$

## 17.7 Efficiency and communication metrics

* reproducer GPU time: sum of CUDA-event elapsed seconds across reproduction/local-update training jobs included in the measured method execution;
* verifier GPU/CPU time: elapsed compute seconds by verifier evaluation jobs;
* server synthesis time: production-update construction plus final-gate server/evaluator elapsed seconds;
* wall-clock runtime: monotonic elapsed seconds from the first post-reference method action after prepared data and the anchor are loaded until the terminal method artifact is published; preprocessing and anchor construction are excluded;
* peak GPU memory: maximum allocated CUDA bytes per process during the measured execution;
* peak host RSS: maximum resident-set bytes during the measured execution;
* persistent storage bytes: sizes of persistent artifacts newly generated by the measured execution under `outputs/` at completion, excluding shared pre-existing inputs.

Communication accounting is conceptual client/server protocol serialization and does not depend on whether the reference implementation uses one OS process or multiple processes. For accounting, extra implementation/logging metadata is ignored. Every counted message has exactly the base metadata fields `schema`, `message_type`, `dataset_manifest_hash`, `semantic_cell_key_hash`, `master_seed`, `round_index`, `sender`, `receiver`, `claim_contract_hash`, and `payload_tensor_count`. `schema` is the literal `FEDSIRA_COMM_V1`; inapplicable scalar fields are JSON `null`; domain identities use fixed domain tokens and server uses `SERVER`. `message_type` is one of `SOURCE_COMMITMENT`, `MODEL_DISTRIBUTION`, `UPDATE_SUBMISSION`, `CLAIM_CONTRACT`, `REVIEW_ASSIGNMENT`, `REVIEW_REPORT`, `VERIFIER_ASSIGNMENT`, `VERIFIER_REPORT`, `FINAL_GATE_ASSIGNMENT`, `FINAL_GATE_REPORT`, or `DECISION`. A model carried with review/verifier/final-gate assignment is part of that assignment message rather than a second metadata message.

Every cross-boundary scientific message is serialized by the following canonical envelope solely for byte accounting:

1. metadata is UTF-8 canonical JSON with keys sorted lexicographically, separators `,` and `:` with no insignificant whitespace, integers in decimal, finite floats in Python/JSON shortest round-trip decimal form, and strings exactly as canonical IDs;
2. prefix metadata with an unsigned 64-bit big-endian metadata-byte length;
3. each tensor payload is converted to contiguous little-endian scientific dtype (`float32` for model/update tensors), preceded by canonical JSON tensor metadata containing `name`, `dtype`, `shape`, and `nbytes`, itself prefixed by an unsigned 64-bit big-endian length;
4. concatenate tensor fields in lexicographically ascending tensor name order; no compression is applied for the accounting representation.

Count every semantic cross-boundary action used by the method with the message type above: source commitment upload; server model distribution; client update submission; Capability Claim Contract transmission; review/verifier/final-gate assignment (including the candidate/production model tensor when evaluation requires it); corresponding reports; and one terminal decision. A broadcast to `k` domains is `k` messages. Model tensors are named `model.<canonical_parameter_name>` and updates `update.<canonical_parameter_name>` in the Section 12 parameter registry. Local filesystem writes are excluded. `communication bytes` is the sum of envelope bytes in both directions. `model transmissions` counts only messages containing at least one model/checkpoint/update tensor payload; metadata-only messages contribute bytes but not a model transmission.

For efficiency runs, peak GPU memory is `torch.cuda.max_memory_allocated()` after the prescribed counter reset. Peak host RSS is measured in the dedicated single-process timing worker as `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss × 1024` bytes on Ubuntu/Linux; all measured method computation is sequential inside that worker, so child-process RSS aggregation is not an implementation choice.

## 17.8 Aggregation and evaluation populations

For claim-bearing production-model report metrics on the primary dataset, the expected evaluation set is the **eight non-source domain proxies** selected for that seed. The source's report-test rows are excluded from method-comparison seed aggregates so every method is evaluated on the same source-independent population. For the secondary dataset the expected set is analogously the eight non-source pseudo-domains.

1. compute class metrics within each expected non-source domain;
2. apply role/metric adequacy rules within that domain;
3. equal-weight defined domain values to obtain the seed-level metric;
4. use seed-level values as independent inference units.

`Worst-domain target F1`, P10 target F1, disparity, and heterogeneity boundary metrics use only adequate **honest** non-source domains, as stated in Section 17.4; a domain designated compromised by the scenario is excluded from those honest-domain distribution summaries but remains in ordinary clean-oracle report summaries unless the metric definition explicitly says otherwise. ASR follows the equal-domain carrier rule in Section 17.3. Final-gate decision metrics use the stronger Section 7.7 adequacy rule and are not replaced by this report-test aggregation rule.

Offline `Report Test` evaluation is performed by the experimental evaluator from the immutable role data. A domain's Byzantine reproducer/verifier designation does not let it falsify report-test labels or final-gate score computation unless the experiment explicitly applies an evidence-oracle corruption from Section 15.

Client/domain observations are repeated measures and are never treated as independent inferential replicates.

## 17.9 Missing and undefined metric policy

* Zero denominator => `NA`, never 0.
* For ordinary primary/secondary report-test equal-domain aggregates, the expected domain count is eight after source exclusion and the generic 80% rule therefore requires at least **7** defined domains (`ceil(0.8×8)=7`).
* A seed-level equal-domain aggregate is valid only if at least the required number of expected domains has defined values, unless the experiment's scientific outcome is explicitly evidence insufficiency.
* Scientific `Dormant`/`Abstain` outcomes are analyzed as outcomes, not missing values.
* A predeclared statistical comparison whose seed metric is structurally `NA` by design is not a comparison-family member. A comparison-family member that becomes undefined because of scientific/technical missingness follows Section 18.8 and cannot support a claim.
* Technical missing runs follow Section 19.

---

## 17.10 Additional specified metrics

### Clean-oracle degradation

For every `Shared Epistemic-Failure Boundary` cell, the matched uncorrupted reference is the `Resolved FedSIRA Core × Legitimate Unsupported Capability × same master_seed` cell from `Primary Confirmatory Evaluation`. The reference is valid only when dataset, source, anchor, role manifests, non-source assignments, resolved core, and all non-corruption training semantics match; otherwise the boundary execution materializes the same uncorrupted scientific object as a shared prerequisite artifact without adding a new experiment cell.

On the untouched `Report Test` oracle, report corrupted-minus-reference target-F1 delta, supported-macro-F1 delta, and benign-FAR delta separately. Do not collapse them into an undocumented scalar.

### False same-capability certification rate

Defined for the broad contract in Section 15.10. Numerator and denominator are both persisted. Zero broad-certified rows => `NA`. Scoped contracts report `NA` for this metric with reason `No Cross-Root-Cause Equivalence Assertion`.

### Descriptive confidence intervals for method summaries

When a figure/table shows a 95% CI around a single method's seed-level mean rather than a paired difference, use the same 10,000-resample, seed-level percentile bootstrap and fixed analysis seed as Section 18.5, but resample the method's seed values rather than paired differences. These CIs are descriptive and do not replace paired inferential tests. Raw method result tables additionally report sample SD across defined seed values.

### Protocol-specific aggregation sufficiency

The generic 80% defined-domain rule applies only when an experiment/metric has no stronger protocol-specific evidence threshold. Final-gate metrics use the explicit final-gate adequacy rule (`>=6` adequate non-source domains); verifier/reproducer decisions use their own evidence minima. The generic rule must never silently override a protocol gate with a different predeclared denominator.

# 18. Statistical analysis protocol

**Configuration authority:** `metrics_and_statistics.*` contains only numerical aggregation/statistical parameters, materiality/completion thresholds, and publication-format values; `seeds_and_determinism.analysis_seed` supplies the inferential resampling seed. Test definitions, sidedness, quantile/resampling semantics, multiplicity families/method, tie rules, and all collapse/survival actions are fixed by this section rather than encoded as YAML procedure strings.

## 18.1 Experimental unit and pairing

The independent confirmatory experimental unit is the **master-seed scenario instance**. There are 10 planned master seeds.

Pairing key:

```text
(dataset, experiment_name, scientific_scenario, master_seed)
```

Methods compared within one scenario share source/domain/attack/evidence-role seeds. Domain rows within a seed are not independent samples.

## 18.2 Primary hypothesis tests

For paired superiority comparisons use a **two-sided exact paired sign-flip permutation test** on seed-level differences.

For $n=10$, enumerate all $2^{10}=1024$ sign assignments. Test statistic is mean paired difference. The exact p-value is:

$$
p=\frac{\#\{|\bar d_{perm}|\ge|\bar d_{obs}|\}}{2^n}.
$$

Zero differences remain in the vector. They are not discarded.

For a directional non-inferiority requirement with benefit-oriented difference $d_i=method-reference$ and allowed degradation margin $m>0$, test the one-sided null that the mean difference is $\le-m$ using exact sign-flip permutations on $d_i+m$. Statistical code must report the exact null orientation in the result artifact.

## 18.3 Alpha and multiplicity

* family-wise significance level: **0.05**;
* correction: **Holm step-down** within each predefined claim family; ties in raw p-values are ordered by canonical comparison name for deterministic serialization;
* no global correction across unrelated claim families;
* both raw and Holm-adjusted p-values are stored.

Claim families are:

1. proposal-screen necessity;
2. plurality necessity;
3. source-exclusion central claim;
4. external reproduction verification necessity;
5. primary baseline superiority;
6. reproducer robustness;
7. verifier robustness;
8. mechanism ablation;
9. heterogeneity/failure-boundary secondary comparisons;
10. secondary generalization.

## 18.4 Effect sizes

Every paired comparison reports:

* mean paired difference in native units;
* median paired difference;
* paired standardized effect

$$
d_z=\frac{\bar d}{s_d}
$$

using sample SD `ddof=1`.

If $s_d=0$: report `+INF` or `-INF` when the nonzero mean has that sign, and `0` when all differences are zero. Do not fabricate a finite value.

## 18.5 Confidence intervals

Report a **95% percentile bootstrap CI** for the mean paired difference:

* resampling unit: complete master-seed pair;
* resamples: **10,000**;
* bootstrap seed: **424242**;
* sample size per resample: number of complete pairs;
* resample with replacement;
* CI endpoints: 2.5th and 97.5th percentiles using type-7/linear interpolation.

The bootstrap CI is descriptive/supporting; exact permutation tests determine p-values.

## 18.6 Materiality criteria

A claim requires both its inferential rule and its practical materiality rule.

| Outcome                                  |                       Material threshold |
| ---------------------------------------- | ---------------------------------------: |
| Target F1 gain                           |                  at least +0.02 absolute |
| Supported macro-F1 non-inferiority       | degradation no worse than -0.02 absolute |
| Benign false-alarm-rate non-inferiority  |    increase no worse than +0.01 absolute |
| ASR reduction for source-exclusion claim |                  at least -0.20 absolute |
| Malicious-admission reduction            |                  at least -0.10 absolute |
| Legitimate-admission non-inferiority     | degradation no worse than -0.05 absolute |
| Worst-domain target-F1 gain              |                  at least +0.05 absolute |
| False-launch reduction                   |                  at least -0.15 absolute |
| Reproduction-attempt reduction           |                    at least 25% relative |
| Post-evidence-overhead reduction         |                    at least 20% relative |

Relative reduction with reference value 0 is undefined and cannot be used as the sole support criterion.

## 18.7 Collapse/survival rules

### Proposal assistance survives only if

At least one of these passes Holm-adjusted $p<0.05$ and its material threshold:

* false-launch reduction $\ge0.15$ absolute;
* reproduction-attempt reduction $\ge25%$ relative;
* post-evidence-overhead reduction $\ge20%$ relative;

and simultaneously:

* legitimate-admission degradation $\le0.05$;
* malicious-admission rate does not worsen by more than 0.02 absolute.

Otherwise the core method uses candidate-free opening; proposal assistance remains only a reported negative/diagnostic result.

### Plurality survives only if

Against `One Independent Retrain`, in at least one preregistered site-specific-overfit or Byzantine-reproducer condition:

* malicious admission decreases by at least 0.10 **or** worst-domain target F1 increases by at least 0.05;
* Holm-adjusted $p<0.05$;
* legitimate-admission degradation $\le0.05$;
* supported macro-F1 harm remains within 0.02.

Otherwise the single-reproduction path becomes the simplest surviving core path.

### Direct source exclusion survives only if

Against the predeclared closest source-influence comparator `Source-Update Sanitization Reference` in the useful+backdoor scenario:

* post-production ASR decreases by at least 0.20;
* adjusted $p<0.05$;
* target F1 is non-inferior within 0.02;
* supported macro-F1 and benign false-alarm rate satisfies the Capability Claim Contract.

Failure means the central contribution is `Not Supported`; no later favorable robustness cell may override this gate.

### external reproduction verification survives only if

Against `Multiple Retrains with Direct Krum` using the same candidate reproduction rows, at least one preregistered failure condition shows:

* malicious admission reduction $\ge0.10$ or worst-domain target-F1 increase $\ge0.05$;
* adjusted $p<0.05$;
* legitimate-admission degradation $\le0.05$.

Otherwise cross-verification/external reproduction verification is removed from the simplest surviving core method.

### Mechanical resolved-core construction

After all four collapse decision artifacts exist, `experiments/collapse.py` creates one deterministic `Resolved FedSIRA Core` artifact. There is no operator choice and no outcome-dependent redesign. The direct source-exclusion gate controls the support state of the central source-exclusion claims but **does not authorize source deployment**; the resolved FedSIRA characterization path remains source-excluded even when that central claim is `Not Supported`.

Let `P` be proposal-assistance survival, `R` plurality survival, and `V` external-verification survival. The resolved procedure is exactly:

| `P` | `R` | `V` | Opening | Reproduction requirement | Row verification | Production update | Final gate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pass | pass | pass | proposal-assisted | first 5 certified non-source rows | ordinary 3-verifier, 2-of-3 certification for each row | Krum over first 5 certified rows | required |
| fail | pass | pass | candidate-free | first 5 certified non-source rows | ordinary 3-verifier, 2-of-3 certification for each row | Krum over first 5 certified rows | required |
| pass | pass | fail | proposal-assisted | first 5 adequate committed non-source rows | none | Krum over first 5 committed rows | required |
| fail | pass | fail | candidate-free | first 5 adequate committed non-source rows | none | Krum over first 5 committed rows | required |
| pass | fail | pass | proposal-assisted | first adequate non-source row that passes one fresh verifier | one verifier: first adequate eligible verifier in post-commitment `Verifier Assignment` order; `Positive` required | that reproduction update directly | required |
| fail | fail | pass | candidate-free | first adequate non-source row that passes one fresh verifier | same one-verifier rule | that reproduction update directly | required |
| pass | fail | fail | proposal-assisted | first adequate committed non-source row | none | that reproduction update directly | required |
| fail | fail | fail | candidate-free | first adequate committed non-source row | none | that reproduction update directly | required |

For the one-verifier resolved path, an inadequate verifier opportunity is skipped without a vote; if no adequate eligible verifier exists, the claim is `Dormant`. An adequate negative verifier rejects that reproduction row and processing continues to the next unconsumed reproducer. The first positive verified row is the production update.

The Section 6 state machine interprets `Synthesis Pending` generically as “production update ready for final gate”; Krum-specific invariants apply only to `R=pass`. This mapping is also the only authority for post-collapse ablations and downstream `Resolved FedSIRA Core` experiment cells.

## 18.8 Failed-run and incomplete-pair rule

A technical run may have one same-cell-phase infrastructure retry. After that:

* the planned seed remains missing for technical reasons;
* it is never replaced with a new seed;
* the failure appears in all run-count and reporting tables.

For a predeclared paired comparison:

* if 10 or 9 complete seed pairs exist, analyze complete pairs and report exact `n`;
* if fewer than 9 complete pairs exist, the comparison state is `Inconclusive Technical` and cannot support a claim;
* no imputation or seed replacement is allowed.

Scientifically infeasible cells caused by insufficient evidence are valid scientific outcomes. Binary terminal outcomes such as LAR/MAR may remain defined; continuous metrics that cannot exist are `NA` with reason.

Multiplicity families are declared before execution. A predeclared family member that becomes `Inconclusive Technical` or lacks enough defined pairs is retained in the family manifest with **raw p-value `1.0` for Holm adjustment only**, while its comparison state remains `Inconclusive Technical`/`Undefined` and it cannot support a claim. This conservative rule prevents missing executions from reducing the multiplicity burden. Metrics that are structurally not applicable by the experiment definition are not family members in the first place.

## 18.9 Exact comparison registry

Only the comparisons generated by this registry are claim-bearing inferential tests. Other displayed differences are descriptive unless a later experiment section explicitly points back to one of these registry rules. Canonical comparison names are:

```text
{family}|{experiment}|{scenario}|{method}__vs__{reference}|{metric}|{test_kind}
```

For a higher-is-better outcome, benefit-oriented difference is `method - reference`. For a lower-is-better outcome (`ASR`, `MAR`, supported harm, benign-FAR increase, false launch, attempts, overhead), benefit-oriented difference is `reference - method`. Superiority uses the two-sided exact sign-flip p-value from Section 18.2 and then checks the expected sign/materiality. Non-inferiority uses the one-sided shifted sign-flip test from Section 18.2.

### Family 1 — proposal-screen necessity

Method is `Proposal-Assisted`; reference is `Candidate-Free`. Generate:

* false-launch superiority for `Generic Hard Supported Examples` and `Irrelevant Source Improvement`, material threshold `0.15` absolute;
* reproduction-attempt and post-evidence-overhead superiority for each of the four Section 30.4 episodes, using the `25%` and `20%` relative material thresholds respectively;
* legitimate-admission non-inferiority on `Legitimate Target Capability` with margin `0.05`;
* malicious-admission non-inferiority on `Useful Backdoored Source — 5%` with margin `0.02` for the proposal-survival safety constraint.

The survival rule uses only the first three effect types as potential positive evidence and the latter two as constraints.

### Family 2 — plurality necessity

Method is `Full Plurality Path`; reference is `One Independent Retrain`. In `Honest Site-Specific Feature Shift — 1.0` and `One Byzantine Source-Copy Reproducer`, test malicious-admission superiority (`0.10`) when MAR is defined and worst-domain-target-F1 superiority (`0.05`). The legitimate-admission degradation (`<=0.05`) and supported-harm (`<=0.02`) requirements are paired full-precision constraint checks for all three conditions and do not add separate p-values.

### Family 3 — source-exclusion central claim

Method is `Full FedSIRA`; reference is `Source-Update Sanitization Reference`; scenario is `Useful Backdoored Source — 5%`. The sole superiority test is ASR with required reduction `0.20`. Target-F1 non-inferiority within `0.02`, supported-harm `<=0.02`, and benign-FAR increase `<=0.01` are mandatory full-precision constraints.

### Family 4 — external reproduction verification necessity

Method is `Full FedSIRA`; reference is `Multiple Retrains with Direct Krum`. In each failure condition `Honest Site-Specific Feature Shift — 1.0`, `One Byzantine Source-Copy Reproducer`, and `One Verifier-Aware Backdoor Reproducer`, test MAR superiority (`0.10`) when defined and worst-domain-target-F1 superiority (`0.05`). `Legitimate Transferable Capability` supplies the legitimate-admission degradation constraint (`<=0.05`); it is not itself a positive survival comparison.

### Family 5 — primary baseline comparisons

For each of the 13 non-FedSIRA methods in Section 30.9 and each primary scenario, method is `Resolved FedSIRA Core` and reference is that comparator. Generate: target-F1 superiority (`0.02` material threshold); legitimate-admission non-inferiority (`0.05`) wherever LAR is defined; supported-harm non-inferiority (`0.02`); benign-FAR-increase non-inferiority (`0.01`); MAR superiority (`0.10`) wherever MAR is defined; and ASR superiority (`0.20`) only where the scenario/method pair has the N-BaIoT trigger metric defined. All applicable raw p-values share the single primary-baseline Holm family.

### Family 6 — compromised-reproducer robustness

Within each non-`CLEAN` Section 30.11 condition, method is `Resolved FedSIRA Core` and references are `One Independent Retrain`, `Multiple Retrains with Direct Krum`, and `Krum Robust Aggregation Reference`. Test MAR superiority (`0.10`) when defined, target-F1 superiority (`0.02`), and ASR superiority (`0.20`) when the condition defines a trigger. `CLEAN` generates LAR and target-F1 non-inferiority checks against each comparator with margins `0.05` and `0.02`.

### Family 7 — compromised-verifier robustness

Within each verifier profile, reference condition is `All Honest`. For `One False Positive` and `Two False Positives`, compare condition vs reference using the increase in MAR as the harm-oriented effect; for deterministic serialization the benefit difference is `MAR_all_honest - MAR_condition`, with material deterioration `0.10`. For `One False Negative` and `Two False Negatives`, compare LAR with benefit difference `LAR_condition - LAR_all_honest` and non-inferiority margin `0.05`; dormant-rate differences are descriptive. Random-profile contamination frequency is compared to the exact hypergeometric probability descriptively, not with a seed-level significance test.

### Family 8 — mechanism ablation

Every Section 30.10 variant consumes a matched `Full FedSIRA` reference artifact with the same scenario, seed, source, data roles, and non-ablated transforms. The variant's exact primary metric is specified in Section 30.10. Superiority/harm orientation follows the metric orientation above. The `Generic Three-Row Threshold` invalid Krum branch has no p-value; its separately labeled coordinate-median diagnostic supplies the comparison metric. All applicable ablation p-values share one Holm family.

### Family 9 — heterogeneity and failure boundaries

Generate the following and no other claim-bearing tests in this family:

* `Shared Epistemic-Failure Boundary`: each corrupted cell vs its Section 17.10 matched uncorrupted reference for clean target F1, supported-macro-F1 harm, and benign-FAR increase; use two-sided exact paired tests and the `attacks_and_boundaries.clean_oracle_materiality` thresholds;
* `Capability Under-Specification Boundary`: for each mixture, test the seed-level `Broad Target Only` false-same-capability certification rate against a paired all-zero reference vector using the two-sided exact sign-flip test; materiality requires mean rate at least `0.10`; scoped contracts have no false-equivalence test;
* `Heterogeneous-Reproduction Boundary`: for every method and each non-`Natural` regime, compare to the same method/seed under `Natural` for LAR and worst-domain target F1; the Section 35 boundary uses absolute degradation `<=0.05` on both metrics.

Evidence-scarcity state invariants, delay decomposition, and efficiency repetitions are descriptive/property evidence and do not add p-values.

### Family 10 — secondary generalization

For each of the two Section 30.20 scenarios, method is `Resolved FedSIRA Core` and references are `One Independent Retrain` and `Multiple Retrains with Direct Krum`. Generate one-sided target-F1 non-inferiority tests with margin `0.02` and one-sided MAR non-inferiority tests with margin `0.05` where MAR is defined. Both test types enter the same secondary-generalization Holm family. Section 35 requires every applicable adjusted p-value to be `<0.05` together with the material margins.

## 18.10 Rounding

Stored values are unrounded. Publication formatting only:

* F1/accuracy/rates: 3 decimals;
* percentages: 1 decimal place after conversion to percentage units;
* effect sizes: 3 decimals;
* confidence-interval bounds: same decimals as metric;
* p-values: 4 significant digits; display `<0.0001` below that threshold;
* seconds: 2 decimals;
* byte sizes: IEC units with 2 decimals.

Decision rules always use full-precision values.

---

# 19. Failure, null-result, and completion semantics

**Configuration authority:** runtime timeouts come from `runtime.timeouts_seconds`, the automatic infrastructure retry count comes from `runtime.automatic_infrastructure_retries_per_cell_phase`, and logical evidence-cycle limits come from `protocol.resource_horizon`. Failure meanings, retry eligibility, publication semantics, and recovery behavior are fixed by this section.

Execution state and scientific protocol outcome are distinct. A valid experiment that falsifies its hypothesis is scientifically complete; `Admitted`, `Dormant`, `Rejected Claim`, `Expired`, and `Abstain` remain protocol outcomes rather than software failure states.

A scientific cell uses the fixed execution-phase enum below; each phase instance has lifecycle state `Planned`, `Running`, `Completed`, `Failed`, or `Invalid`. An experiment state is exactly `Not Started`, `Blocked`, `Ready`, `Running`, `Completed`, `Failed`, or `Invalid`.

| Failure class                 | Meaning and scientific consequence                                                                                  |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `Configuration Invalid`       | Fixed configuration is inconsistent or out of range; affected execution is invalid.                                |
| `Data Invalid`                | Dataset identity, schema, nonfinite-value, role, leakage, or split validation fails; dependent science is blocked.  |
| `Invariant Violation`         | A source-exclusion, freshness, role, certificate, or provenance invariant fails; affected evidence is unusable.     |
| `Implementation Error`        | Deterministic software failure; no scientific result is produced.                                                   |
| `Numerical Failure`           | NaN/Inf or invalid numerical state despite the fixed safeguards; no post-hoc optimizer change is allowed.          |
| `Infrastructure Interruption` | External runtime interruption unrelated to scientific outcome; one same-cell-phase automatic recovery is permitted. |
| `Timeout`                     | Fixed timeout exceeded; no protocol or model change is authorized by the timeout.                                  |
| `Evidence Insufficient`       | Scientific evidence minimum is not met; execution may complete with `Abstain` or `Dormant`.                         |
| `Assumption Violation`        | Deliberate above-bound or diagnostic condition; valid only as boundary evidence.                                    |

## 19.1 Scientific cell-phase boundaries

The retry/timeout unit `scientific cell phase` is one of:

```text
PREPARE
TRAIN
SCORE
PROTOCOL_EVALUATION
METRIC_AGGREGATION
STATISTICAL_ANALYSIS
```

* `PREPARE`: resolve/validate semantic cell inputs, data views, assignments, prerequisite artifacts, and attack/boundary transforms; no model optimization occurs.
* `TRAIN`: all training/update producers owned by the cell, including source/reproduction/baseline local training and checkpoint publication. Epoch/round recovery boundaries belong here.
* `SCORE`: model inference producing reusable logits/probabilities/predictions/losses.
* `PROTOCOL_EVALUATION`: screen matching, verifier decisions, certification, production-update construction, final-gate evaluation, and terminal protocol outcome.
* `METRIC_AGGREGATION`: domain/seed metric construction and adequacy/NA validation.
* `STATISTICAL_ANALYSIS`: experiment-level paired tests, CIs, effects, multiplicity, materiality, collapse/core-resolution decisions, and claim-state inputs after all required seed cells are present.

A timeout/retry applies to one phase instance only. `fedsira report` is not a scientific cell phase; its export operation uses `runtime.timeouts_seconds.experiment_analysis_or_report` and never triggers scientific recomputation.

Reference timeouts are 2 hours per dataset preprocessing operation, 2 hours per scientific cell phase, 30 minutes per experiment-level statistical analysis/report operation, and 30 minutes for project/export verification. Only `Infrastructure Interruption` permits an automatic same-artifact recovery attempt, at most once, using the identical semantic cell, phase, seeds, scientific configuration, and hash-valid checkpoint lineage. Scientific, numerical, data, or invariant failures are never automatically repeated until favorable.

A later operator invocation after an implementation correction is not a new scientific observation and is not an outcome-driven retry. The command first validates all existing upstream artifacts, preserves every compatible completed artifact, invalidates only artifacts whose material producer dependency changed and their descendants, and resumes from the nearest valid boundary. An `Implementation Error` in scoring, metrics, statistics, or reporting therefore does not authorize retraining when the training artifacts remain valid.

Recovery checkpoints are implementation artifacts, not extra scientific observations. Anchor/FedAvg round checkpoints already required by the training contract are resumable boundaries. Post-reference local training must additionally persist exact recoverable state at completed epoch boundaries, including model, optimizer, RNG, sampler position needed for deterministic continuation, and upstream identities. A resumed trajectory must be prediction-equivalent to uninterrupted execution within the Section 20 tolerance; otherwise the resumed artifact is invalid and the affected training stage is recomputed from its nearest earlier valid checkpoint.

No crashed or incomplete producer output is reusable. Payloads are written to staging, validated and checksummed, and only then atomically published as `Complete`. A manifest, marker, database/index row, or directory left in `Running`, staging, partial, failed, or checksum-mismatched state is never an input to downstream science.

# 20. Reference software and hardware environment

**Configuration authority:** `runtime.data_loader` supplies the small runtime loader settings and `runtime.same_environment_absolute_metric_tolerance` supplies the numerical reproducibility tolerance. The reference software versions, hardware class, deterministic backend behavior, and environment failure semantics below are fixed reproducibility requirements, not user-selectable YAML options.

The reproducibility reference environment is:

```text
OS: Ubuntu 24.04 LTS (native or WSL2 Linux userspace)
Python: 3.11.9
PyTorch: 2.9.0
CUDA runtime for reference GPU runs: 12.8
NumPy: 2.1.3
pandas: 2.2.3
SciPy: 1.14.1
scikit-learn: 1.5.2
pyarrow: 17.0.0
pydantic: 2.9.2
Typer: 0.12.5
Rich: 13.9.4
Matplotlib: 3.9.2
statsmodels: 0.14.4
pytest: 8.3.3
```

The checked dependency lock file is authoritative if package resolver metadata requires a compatible patch dependency.

Reference confirmatory hardware and required system utility:

```text
GPU: NVIDIA GeForce RTX 5060 Ti, 16 GB VRAM
CPU RAM: at least 32 GB
Free storage before full workflow: at least 100 GB
GPU count: 1
N-BaIoT RAR extractor when archives are present: Ubuntu `unrar` 1:7.0.7-1build1
```

All claim-bearing paired method comparisons must run on the same fixed hardware class. Efficiency comparisons must run on the same physical machine and with no concurrent scientific training job.

The complete reference environment and dependency lock remain the reproducibility snapshot for the study. Artifact reuse is nevertheless stage-scoped: an existing artifact is invalidated by an environment/dependency change only when that component is declared capable of changing the artifact's producer output. A change limited to CLI presentation, reporting, diagnostics, or another unrelated dependency does not invalidate a compatible training, scoring, metric, or statistical artifact. Any fresh producer execution must still satisfy the reference requirements relevant to that producer and the deterministic contract below.

Determinism settings:

* for a master-seed scientific subprocess, `PYTHONHASHSEED` is the decimal uint32 master seed itself (`1103`, ..., `2081`); for smoke it is `900001`; preprocessing/report-only subprocesses use `0`. The launcher sets it before Python process initialization; scientific ordering never relies on Python hash iteration even with this setting;
* `torch.use_deterministic_algorithms(True, warn_only=False)` is mandatory for claim-bearing execution; the PyTorch API contract specifies that with `warn_only=False`, an operation lacking a deterministic implementation raises instead of silently continuing (PyTorch deterministic-algorithms documentation; Section 41).
* `torch.backends.cudnn.deterministic=True`;
* `torch.backends.cudnn.benchmark=False`;
* `CUBLAS_WORKSPACE_CONFIG=:4096:8` is set before CUDA context creation for the reference CUDA workflow;
* TF32 is disabled for confirmatory runs;
* all RNG states are saved in hash-valid recovery checkpoints.

There is no warning-only or nondeterministic fallback for claim-bearing cells. If the specified reference environment cannot execute the scientific graph under these deterministic settings, `fedsira doctor` blocks claim-bearing execution as `Configuration Invalid`. Same-environment smoke reproducibility must additionally remain within `runtime.same_environment_absolute_metric_tolerance`, fixed at `1e-6`.

---

# Configuration YAML

`configs/fedsira.yaml` is the single authoritative configuration-data file for the study. It contains only values that must be supplied to execution: dataset/target identifiers, numerical thresholds and budgets, sampling/split intervals, experiment-strength grids, actual seeds, paths, runtime limits, and a small number of genuine categorical grid/format selections. The implementation loads it through a typed, immutable schema. `configs/tests.yml` contains test-only fixture values, and `configs/smoke.yml` contains reduced deterministic smoke values; neither has scientific authority.

Presence in YAML does not authorize post-hoc tuning. Claim-bearing configuration values are governed by the authoritative roadmap contracts; experiment-grid categories may be traversed only where Section 30 declares them, and runtime/path values may vary only where the execution contract permits variation without changing scientific identity.

The YAML is **not** the authority for fixed algorithms, architecture definitions, formulas, ordering/tie procedures, validation/failure semantics, baseline identities, experiment definitions, reporting requirements, claim wording/states, deterministic hash procedures, or provenance rules. Those are authoritative in the scientific/execution sections that define them. Fixed numerical literals that are intrinsic to such a definition may therefore appear only in that defining section; they are not hidden defaults and are not configurable merely because software must implement them.

Derived values are computed from their primitive configured or observed inputs and are never represented by `*_from`, `reuse_*`, formula strings, or a YAML dependency language. Observed dataset/environment facts and generated provenance remain manifests or execution records rather than configuration. Fixed hash tokens and separators needed to preserve deterministic streams are defined explicitly in Sections 9–13 as implementation invariants rather than user-modifiable configuration.

The implementation repository boundary is:

```text
fedsira/
│
├── README.md                                      # Project overview, setup, scientific scope, reproducibility expectations, and public CLI usage.
├── pyproject.toml                                 # Python package metadata, exact runtime requirements, tooling configuration, and `fedsira` CLI entry point.
├── uv.lock                                        # Exact resolved Python dependency lock for the reference environment.
├── noxfile.py                                     # Reproducible linting, typing, architecture-check, test, and validation sessions.
├── Makefile                                       # Short developer-facing commands for common repository workflows.
├── .gitignore                                     # Excludes generated computational workspace, caches, local environments, and transient files.
│
├── configs/
│   ├── fedsira.yaml                               # Single authoritative roadmap-defined configuration-data file for scientific and runtime values.
│   ├── tests.yml                                  # Test-only fixture/configuration values with no scientific authority.
│   └── smoke.yml                                  # Reduced deterministic smoke configuration that never contributes manuscript evidence.
│
├── data/
│   └── raw -> /external/datasets                  # Immutable symlink to externally managed raw datasets; raw bytes are never modified.
│
├── outputs/                                       # Complete generated computational workspace; normally Git-ignored and permitted to contain large artifacts.
│   │
│   ├── preprocessing/
│   │   ├── inventories/                           # Raw-file inventories, checksum inventories, observed schemas, labels, domains, and availability summaries.
│   │   ├── validation/                            # Data-validity, feasibility, leakage, finite-value, exclusion, and deterministic-regeneration evidence.
│   │   ├── prepared/                              # Deterministic role-specific prepared data views used by later computation.
│   │   ├── splits/                                # Immutable role/split/sample manifests, guard-gap assignments, and pseudo-domain partitions.
│   │   ├── features/                              # Fixed scaler artifacts, feature schemas, class registries, and feature-derived preparation products.
│   │   └── metadata/                              # Dataset identities, exclusions, preparation fingerprints, and reusable preprocessing provenance.
│   │
│   ├── artifacts/                                 # Project-wide reusable scientific artifacts whose dependency fingerprints permit cross-experiment reuse.
│   │   ├── models/                                # Shared anchors, round checkpoints, source candidates, reproductions, and other reusable model artifacts.
│   │   ├── scores/                                # Reusable per-sample logits, probabilities, predictions, losses, and deterministic score shards.
│   │   ├── fitted/                                # Reusable fitted scientific objects such as scalers and baseline calibration/threshold products.
│   │   ├── baselines/                             # Reusable baseline checkpoints, update artifacts, calibration products, and shared baseline intermediates.
│   │   └── derived/                               # Reusable commitments, verifier products, certificates, synthesis products, and other derived artifacts.
│   │
│   ├── experiments/
│   │   └── <descriptive-experiment-name>/
│   │       ├── artifacts/
│   │       │   ├── fitted/                        # Experiment-specific fitted objects that are not scientifically reusable outside this experiment.
│   │       │   ├── predictions/                   # Heavy experiment-specific prediction and score products retained for downstream evaluation.
│   │       │   └── derived/                       # Experiment-specific assignments, certificates, synthesized updates, protocol states, and derived arrays.
│   │       │
│   │       ├── evaluations/
│   │       │   ├── records/                       # Detailed protocol/domain/sample evaluation records and terminal scientific outcomes.
│   │       │   ├── comparisons/                   # Computational comparison inputs and paired method/condition evaluation records.
│   │       │   └── aggregates/                    # Domain-, condition-, and seed-level evaluated aggregates used by metric/statistical producers.
│   │       │
│   │       ├── metrics/
│   │       │   ├── per_seed/                      # Authoritative seed-level metrics used as inferential units.
│   │       │   ├── per_condition/                 # Condition-level metric collections and completeness/adequacy records.
│   │       │   └── aggregate/                     # Computed experiment-wide metric summaries retained as computational evidence.
│   │       │
│   │       ├── statistics/
│   │       │   ├── tests/                         # Exact paired sign-flip and non-inferiority test artifacts.
│   │       │   ├── confidence_intervals/          # Bootstrap resampling results and confidence-interval artifacts.
│   │       │   ├── effects/                       # Mean/median differences, paired effect sizes, and materiality calculations.
│   │       │   └── multiplicity/                  # Holm-family inputs, adjusted p-values, and deterministic multiplicity decisions.
│   │       │
│   │       ├── checkpoints/
│   │       │   ├── training/                      # Recoverable model, optimizer, RNG, sampler, and completed-epoch/round training states.
│   │       │   └── execution/                     # Experiment/cell-phase recovery boundaries and resumable execution state.
│   │       │
│   │       ├── diagnostics/
│   │       │   ├── scientific/                    # Invariant, evidence-sufficiency, claim-contract, boundary, and protocol diagnostics.
│   │       │   ├── numerical/                     # NaN/Inf, deterministic-tolerance, metric, and numerical-stability diagnostics.
│   │       │   └── runtime/                       # Timing, memory, communication, storage, hardware, and execution-performance diagnostics.
│   │       │
│   │       ├── logs/
│   │       │   ├── execution/                     # Structured execution logs used only for diagnosis, never as scientific result storage.
│   │       │   └── failures/                      # Structured technical failure, timeout, interruption, and invalidation logs.
│   │       │
│   │       └── provenance/
│   │           ├── configuration/                 # Fixed configuration subsets and resolved scientific configuration identities.
│   │           ├── data/                          # Dataset, split, prepared-view, scaler, and upstream data identities.
│   │           ├── seeds/                         # Master-seed bundles, namespace seeds, deterministic assignments, and phase identities.
│   │           ├── code/                          # Producer-component fingerprints and reconstruction commit metadata.
│   │           ├── environment/                   # Hardware, OS, CUDA, runtime, determinism, and execution-environment records.
│   │           └── dependencies/                  # Relevant producer dependency fingerprints plus full reconstruction dependency-snapshot identity.
│   │
│   └── cache/
│       ├── preprocessing/                          # Non-authoritative acceleration cache for deterministic preprocessing work.
│       ├── models/                                 # Non-authoritative reusable model-loading or transformation cache.
│       ├── evaluation/                             # Non-authoritative evaluation/scoring acceleration cache.
│       ├── analysis/                               # Non-authoritative statistical or rendering-preparation cache.
│       └── staging/                                # Temporary atomic-write staging; incomplete/staged content is never reusable evidence, validated content is promoted to canonical locations, and abandoned content is disposable.
│
├── results/                                       # Compact verified manuscript-facing evidence; never used as computational input.
│   │
│   ├── experiments/
│   │   └── <descriptive-experiment-name>/
│   │       ├── figures/
│   │       │   ├── main/                          # Main-paper figures derived only from verified completed evidence.
│   │       │   └── supplementary/                 # Compact supplementary figures derived from verified completed evidence.
│   │       │
│   │       ├── tables/
│   │       │   ├── main/                          # Main-paper tables generated from verified scientific artifacts.
│   │       │   └── supplementary/                 # Supplementary manuscript tables and compact supporting evidence.
│   │       │
│   │       ├── metrics/
│   │       │   ├── primary/                       # Compact verified primary metric summaries used by the manuscript.
│   │       │   ├── secondary/                     # Compact verified secondary/descriptive metric summaries.
│   │       │   └── summary/                       # Compact experiment-level metric summaries and completeness counts.
│   │       │
│   │       └── statistics/
│   │           ├── tests/                         # Compact verified raw and adjusted inferential test results.
│   │           ├── confidence_intervals/          # Final manuscript-facing confidence-interval summaries.
│   │           ├── effects/                       # Final paired effect-size and materiality summaries.
│   │           └── multiplicity/                  # Final Holm-adjustment and claim-family decision summaries.
│   │
│   └── project_summary/
│       ├── figures/
│       │   ├── main/                              # Cross-experiment main-paper figures required by the roadmap.
│       │   └── supplementary/                     # Cross-experiment supplementary figures.
│       │
│       ├── tables/
│       │   ├── main/                              # Cross-experiment protocol, result, statistical, and claim-support tables.
│       │   └── supplementary/                     # Compact supplementary project-wide tables.
│       │
│       ├── metrics/
│       │   ├── primary/                           # Final compact project-wide primary scientific metric summaries.
│       │   └── summary/                           # Compact overall metric, completion, boundary, and evidence summaries.
│       │
│       ├── statistics/
│       │   ├── comparisons/                       # Final cross-experiment paired-comparison and decision summaries.
│       │   ├── confidence_intervals/              # Final cross-experiment confidence-interval summaries.
│       │   ├── effects/                           # Final project-wide effect-size and materiality summaries.
│       │   └── multiplicity/                      # Final claim-family Holm correction summaries.
│       │
│       ├── claim_registry/                        # Final manuscript-facing claim states, scopes, required evidence, and support decisions; never computational state.
│       │
│       └── reproducibility/
│           ├── configuration/                     # Compact final fixed scientific configuration identities and dependency summaries.
│           ├── datasets/                          # Compact dataset/checksum/schema/split identities needed for manuscript reproducibility.
│           ├── seeds/                             # Final master-seed and deterministic-assignment summaries.
│           ├── software/                          # Compact reference software, dependency-lock, and component-fingerprint summaries.
│           └── execution/                         # Final experiment counts, cell completion, and artifact-validity summaries.
│
├── docs/
│   └── Roadmap.md                                 # Authoritative scientific, experimental, execution, reporting, and reproducibility specification.
│
├── src/
│   └── fedsira/
│       ├── __init__.py                            # Package identity and intentionally minimal public Python API.
│       │
│       ├── domain/
│       │   ├── __init__.py                        # Exposes only stable cross-package FedSIRA domain concepts shared by multiple scientific subsystems.
│       │   ├── enums.py                           # Defines shared roadmap-required identities and states such as protocol outcomes, execution phases, artifact lifecycle states, experiment states, and claim states.
│       │   └── records.py                         # Defines stable cross-package identities/keys such as domain, experiment, capability, semantic-cell, and seed-bundle records without storage or package-specific behavior.
│       │
│       ├── config/
│       │   ├── __init__.py                        # Exposes typed configuration objects and public configuration helpers.
│       │   ├── schema.py                          # Immutable typed representation of values supplied by `configs/fedsira.yaml`.
│       │   ├── loading.py                         # Loads `configs/fedsira.yaml` and constructs its typed immutable representation.
│       │   └── validation.py                      # Enforces configuration ranges, consistency, and roadmap-defined cross-field constraints.
│       │
│       ├── datasets/
│       │   ├── __init__.py                        # Exposes shared dataset contracts and concrete dataset packages.
│       │   ├── common.py                          # Shared dataset/sample structures, canonical serialization rules, and data contracts that remain dataset-oriented.
│       │   ├── roles.py                           # Implements supported/target role intervals, guard gaps, role eligibility, and role-access restrictions.
│       │   ├── sampling.py                        # Implements immutable sample IDs, deterministic hash ordering, sampling caps, and transformation selection.
│       │   ├── scaling.py                         # Fits and applies the supported-anchor-training-only global standardization contract.
│       │   │
│       │   ├── nbaiot/
│       │   │   ├── __init__.py                    # Exposes the N-BaIoT dataset implementation.
│       │   │   ├── acquisition.py                 # Discovers N-BaIoT raw files and records immutable file/checksum identity.
│       │   │   ├── schema.py                      # Owns fixed N-BaIoT device proxies, class vocabulary, feature expectations, and path-label semantics.
│       │   │   ├── preprocessing.py               # Parses N-BaIoT and materializes deterministic canonical role-specific prepared data.
│       │   │   └── validation.py                  # Enforces primary schema, finite-value, target-holder, evidence-feasibility, and leakage requirements.
│       │   │
│       │   └── ciciot2023/
│       │       ├── __init__.py                    # Exposes the CICIoT2023 secondary-dataset implementation.
│       │       ├── acquisition.py                 # Discovers official CICIoT2023 CSV files and records immutable file/checksum identity.
│       │       ├── schema.py                      # Validates/derives predictor schema, canonical labels, target class, and non-predictive identifiers.
│       │       ├── preprocessing.py               # Performs complete-case filtering, deterministic pseudo-domain partitioning, roles, and prepared views.
│       │       └── validation.py                  # Enforces secondary schema consistency, exclusions, target validity, pseudo-domain, and leakage contracts.
│       │
│       ├── models/
│       │   ├── __init__.py                        # Exposes the roadmap-defined model family.
│       │   └── mlp.py                             # Implements the exact multiclass MLP architecture, initialization, and derived input/output dimensions.
│       │
│       ├── learning/
│       │   ├── __init__.py                        # Exposes shared centralized/federated training functionality.
│       │   ├── training.py                        # Implements deterministic minibatching, AdamW, cross-entropy, regularization, clipping, and epoch mechanics.
│       │   ├── federated.py                       # Implements sample-weighted FedAvg participation, local training, update collection, and aggregation rounds.
│       │   ├── anchor.py                          # Owns supported-only 20-round anchor FedAvg training and authoritative final-round checkpoint selection.
│       │   ├── post_reference.py                  # Implements source-candidate and honest-reproduction training from the fixed anchor.
│       │   ├── aggregation.py                     # Implements FedAvg, Krum, coordinate median, trimmed mean, and shared aggregation mathematics.
│       │   └── scoring.py                         # Produces reusable per-sample logits, probabilities, predictions, and losses from fixed model artifacts.
│       │
│       ├── protocol/
│       │   ├── __init__.py                        # Exposes the FedSIRA scientific admission protocol.
│       │   ├── claim_contract.py                  # Constructs, hashes, validates immutability of, evaluates, and validates Capability Claim Contracts.
│       │   ├── state_machine.py                   # Implements legal FedSIRA protocol transitions, dormancy, rejection, expiry, and transition invariants.
│       │   ├── opening.py                         # Implements proposal-assisted screening and candidate-free claim opening.
│       │   ├── reproduction.py                    # Controls deterministic reproducer assignment, source-independent training inputs, and immutable commitments.
│       │   ├── verification.py                    # Implements post-commitment verifier selection, adequacy, voting, certification, and Byzantine verifier profiles.
│       │   ├── synthesis.py                       # Constructs the five-certified-row certificate and performs source-excluded Krum synthesis.
│       │   ├── admission.py                       # Implements the final fresh gate and authoritative admission/dormancy/rejection decision.
│       │   └── theory.py                          # Implements executable mathematical checks corresponding to count, bound, delay, and non-interference obligations.
│       │
│       ├── attacks/
│       │   ├── __init__.py                        # Exposes the roadmap-defined adversarial transformations while remaining distinct from failure-boundary fixtures.
│       │   ├── source_backdoor.py                 # Implements useful hidden-backdoor source training, trigger construction, poisoning, and ASR evaluation transforms.
│       │   ├── reproduction.py                    # Implements Source Copy, Model-Replacement Backdoor, and Verifier-Aware Backdoor reproduction attacks.
│       │   └── verification.py                    # Implements False Positive and False Negative Byzantine verifier behavior.
│       │
│       ├── boundaries/
│       │   ├── __init__.py                        # Exposes scientific failure-boundary and stress-test constructions separately from adversarial attack mechanisms.
│       │   ├── epistemic_failure.py               # Implements shared label error, shared spurious feature, and attacker-induced common-context fixtures.
│       │   ├── capability_granularity.py          # Implements A/B root-cause strata, scoped contracts, mixtures, and false-same-capability certification logic.
│       │   ├── heterogeneity.py                   # Implements quantity skew and deterministic ±0.5/±1.0 feature-shift regimes.
│       │   └── evidence_arrival.py                # Implements permanent-singleton, one-holder, gradual-quorum, and immediate-quorum schedules.
│       │
│       ├── baselines/
│       │   ├── __init__.py                        # Exposes all roadmap-defined comparison methods.
│       │   ├── registry.py                        # Defines the fixed Section 16 baseline identities and mechanism contracts.
│       │   ├── references.py                      # Implements local-only, centralized, FedAvg, continual-assessment, and other straightforward references.
│       │   ├── independent_retraining.py          # Implements one-retrain, review-then-retrain, direct-Krum-retrain, and related constructive alternatives.
│       │   ├── source_authority.py                 # Implements direct source review/admission, sanitization, independent-reference, and recovery baselines.
│       │   ├── robust_aggregation.py              # Implements Krum reference, coordinate median, reconstruction filtering, and density-cluster trimmed mean.
│       │   ├── certified_ensemble.py              # Implements deterministic three-group multiple-model certified ensemble behavior.
│       │   └── calibration.py                     # Produces fixed pre-execution baseline calibration thresholds and parameter-similarity prerequisites.
│       │
│       ├── experiments/
│       │   ├── __init__.py                        # Exposes experiment definitions, planning, execution, and collapse functionality.
│       │   ├── registry.py                        # Defines the complete descriptive Section 30 experiment registry and all fixed matrices.
│       │   ├── planning.py                        # Resolves canonical experiment order, prerequisites, semantic cells, phases, blocked cells, and count invariants.
│       │   ├── execution.py                       # Executes planned cells through the artifact DAG with selective reuse, invalidation, recovery, and completion semantics.
│       │   ├── collapse.py                        # Applies preregistered proposal, plurality, source-exclusion, and external-verification survival rules.
│       │   └── validation.py                      # Validates experiment definitions, legal conditions, phase obligations, dependencies, counts, and completion.
│       │
│       ├── evaluation/
│       │   ├── __init__.py                        # Exposes metric records, metric computation, aggregation, and evaluation validation.
│       │   ├── records.py                         # Defines evaluation-specific domain/seed/denominator/outcome/metric records that do not belong in the cross-cutting domain package.
│       │   ├── metrics.py                         # Implements the complete classification, capability, security, distribution, delay, and efficiency metric registry.
│       │   ├── aggregation.py                     # Implements equal-domain/equal-seed aggregation, adequacy rules, NA handling, and repeated-measure constraints.
│       │   └── validation.py                      # Enforces role legality, denominator validity, protocol-specific sufficiency, and metric/evaluation invariants.
│       │
│       ├── analysis/
│       │   ├── __init__.py                        # Exposes statistical comparison and claim-state analysis.
│       │   ├── statistics.py                      # Implements exact sign-flip tests, non-inferiority tests, Holm adjustment, bootstrap CIs, effects, and type-7 quantiles.
│       │   ├── comparisons.py                     # Executes predeclared method comparisons, pairing, materiality, completion, and collapse-support decisions.
│       │   └── claims.py                          # Mechanically derives roadmap-defined final claim states and scopes from verified completed verified scientific evidence.
│       │
│       ├── artifacts/
│       │   ├── __init__.py                        # Exposes the scientific artifact lifecycle and dependency-DAG infrastructure.
│       │   ├── records.py                         # Defines artifact-specific manifests, checksums, dependency records, and storage metadata around shared domain identities/states.
│       │   ├── paths.py                           # Maps computational artifact types only into `outputs/` and verified export products only into `results/`.
│       │   ├── fingerprints.py                    # Computes stage-scoped dependency, producer-component, runtime, and upstream-identity fingerprints.
│       │   ├── graph.py                           # Maintains artifact dependencies, cross-experiment reuse, stale descendants, and selective invalidation.
│       │   ├── storage.py                         # Handles staging, checksum verification, atomic publication, replacement, retirement, and active artifact selection.
│       │   ├── provenance.py                      # Captures configuration, data, seed, code, environment, dependency, and reconstruction lineage.
│       │   └── validation.py                      # Rejects stale, corrupt, partial, incompatible, provenance-invalid, or phase-invalid computational artifacts.
│       │
│       ├── runtime/
│       │   ├── __init__.py                        # Exposes deterministic execution, environment validation, recovery, state, logging, and timing helpers.
│       │   ├── determinism.py                     # Implements seed namespaces, canonical hashing, batch ordering, RNG state, and fail-closed PyTorch determinism.
│       │   ├── environment.py                     # Validates reference software, CUDA, hardware, storage, and deterministic-runtime requirements.
│       │   ├── state.py                           # Manages runtime progress, failure details, project-stage progression, and resumable boundaries using shared lifecycle identities.
│       │   ├── recovery.py                        # Restores hash-valid checkpoints and enforces the single permitted infrastructure recovery attempt.
│       │   ├── timing.py                          # Measures monotonic/CUDA timings, memory, communication, transmissions, storage, and efficiency repetitions.
│       │   └── logging.py                         # Provides structured diagnostic logging without making logs authoritative scientific evidence.
│       │
│       ├── reporting/
│       │   ├── __init__.py                        # Exposes verified evidence materialization from `outputs/` into `results/`.
│       │   ├── verification.py                    # Confirms that exports depend only on complete verified output artifacts and that `results/` is never an execution dependency.
│       │   ├── tables.py                          # Renders mandatory roadmap tables from compact verified metric/statistical/claim inputs.
│       │   ├── figures.py                         # Renders mandatory roadmap figures and the deterministic FedSIRA protocol schematic.
│       │   └── export.py                          # Materializes compact manuscript-facing evidence into `results/` without scientific recomputation.
│       │
│       └── cli/
│           ├── __init__.py                        # Exposes the public CLI package.
│           ├── main.py                            # Defines the Typer `fedsira` application and the fixed public command surface.
│           └── commands/
│               ├── __init__.py                    # Exposes the six public roadmap-defined CLI commands.
│               ├── doctor.py                      # Read-only diagnosis of environment, data, artifacts, experiments, and next valid action.
│               ├── preprocess.py                  # Executes deterministic dataset preparation and publishes reusable preprocessing artifacts under `outputs/`.
│               ├── plan.py                        # Resolves and displays experiment matrices, dependencies, phases, blocked conditions, and exact plan counts.
│               ├── smoke.py                       # Executes the deterministic protocol/invariant validation suite without creating manuscript evidence.
│               ├── run.py                         # Executes one named experiment's scientific lifecycle and analysis.
│               └── report.py                      # Exports verified compact evidence from `outputs/` to `results/` without rerunning scientific computation.
│
└── tests/
    ├── conftest.py
    │
    ├── architecture/
    │   ├── test_structure.py
    │   ├── test_dependencies.py
    │   ├── test_framework_confinement.py
    │   ├── test_code_contracts.py
    │   ├── test_config_contracts.py
    │   └── test_output_result_boundaries.py
    │
    ├── unit/
    │   ├── domain/
    │   │   ├── test_enums.py
    │   │   └── test_records.py
    │   │
    │   ├── config/
    │   │   ├── test_loading.py
    │   │   └── test_validation.py
    │   │
    │   ├── datasets/
    │   │   ├── test_roles.py
    │   │   ├── test_sampling.py
    │   │   ├── test_scaling.py
    │   │   ├── nbaiot/
    │   │   │   ├── test_schema.py
    │   │   │   └── test_preprocessing.py
    │   │   └── ciciot2023/
    │   │       ├── test_schema.py
    │   │       └── test_preprocessing.py
    │   │
    │   ├── models/
    │   │   └── test_mlp.py
    │   │
    │   ├── learning/
    │   │   ├── test_training.py
    │   │   ├── test_federated.py
    │   │   ├── test_anchor.py
    │   │   ├── test_post_reference.py
    │   │   ├── test_aggregation.py
    │   │   └── test_scoring.py
    │   │
    │   ├── protocol/
    │   │   ├── test_claim_contract.py
    │   │   ├── test_state_machine.py
    │   │   ├── test_opening.py
    │   │   ├── test_reproduction.py
    │   │   ├── test_verification.py
    │   │   ├── test_synthesis.py
    │   │   ├── test_admission.py
    │   │   └── test_theory.py
    │   │
    │   ├── attacks/
    │   │   ├── test_source_backdoor.py
    │   │   ├── test_reproduction_attacks.py
    │   │   └── test_verifier_attacks.py
    │   │
    │   ├── boundaries/
    │   │   ├── test_epistemic_failure.py
    │   │   ├── test_capability_granularity.py
    │   │   ├── test_heterogeneity.py
    │   │   └── test_evidence_arrival.py
    │   │
    │   ├── baselines/
    │   │   ├── test_registry.py
    │   │   ├── test_references.py
    │   │   ├── test_source_authority.py
    │   │   ├── test_independent_retraining.py
    │   │   ├── test_robust_aggregation.py
    │   │   ├── test_certified_ensemble.py
    │   │   └── test_calibration.py
    │   │
    │   ├── experiments/
    │   │   ├── test_registry.py
    │   │   ├── test_planning.py
    │   │   ├── test_execution.py
    │   │   ├── test_collapse.py
    │   │   └── test_validation.py
    │   │
    │   ├── evaluation/
    │   │   ├── test_records.py
    │   │   ├── test_metrics.py
    │   │   ├── test_aggregation.py
    │   │   └── test_validation.py
    │   │
    │   ├── analysis/
    │   │   ├── test_statistics.py
    │   │   ├── test_comparisons.py
    │   │   └── test_claims.py
    │   │
    │   ├── artifacts/
    │   │   ├── test_records.py
    │   │   ├── test_paths.py
    │   │   ├── test_fingerprints.py
    │   │   ├── test_graph.py
    │   │   ├── test_storage.py
    │   │   ├── test_provenance.py
    │   │   └── test_validation.py
    │   │
    │   ├── runtime/
    │   │   ├── test_determinism.py
    │   │   ├── test_environment.py
    │   │   ├── test_state.py
    │   │   ├── test_recovery.py
    │   │   └── test_timing.py
    │   │
    │   ├── reporting/
    │   │   ├── test_verification.py
    │   │   ├── test_tables.py
    │   │   ├── test_figures.py
    │   │   └── test_export.py
    │   │
    │   └── cli/
    │       └── test_commands.py
    │
    ├── scientific/
    │   ├── test_data_invariants.py
    │   ├── test_source_artifact_exclusion.py
    │   ├── test_verification_and_certificate.py
    │   ├── test_krum_contract.py
    │   ├── test_statistical_contracts.py
    │   ├── test_experiment_contracts.py
    │   ├── test_claim_boundaries.py
    │
    ├── integration/
    │   ├── datasets/
    │   │   └── test_preprocessing_pipeline.py
    │   ├── learning/
    │   │   └── test_anchor_and_reproduction.py
    │   ├── protocol/
    │   │   └── test_fedsira_admission_path.py
    │   ├── experiments/
    │   │   └── test_plan_and_execution.py
    │   ├── artifacts/
    │   │   └── test_reuse_invalidation_recovery.py
    │   └── reporting/
    │       └── test_verified_materialization.py
    │
    ├── e2e/
    │   ├── test_preprocess_plan_smoke.py
    │   ├── test_run_status_report.py
    │   ├── test_reuse_recovery_overwrite.py
    │
    └── smoke/
        └── test_smoke.py
```

The complete configuration file is:

```yaml
datasets:
  primary:
    name: N-BaIoT
    uci_dataset_id: 442
    doi: 10.24432/C5RC8J
    target_class: GAFGYT_COMBO
    minimum_target_holding_domains: 7
    supported_metric_minimum_report_examples_per_class: 100
    role_intervals:
      supported:
        Anchor Train:
        - 0.0
        - 0.395
        Anchor Validation:
        - 0.4
        - 0.495
        Post-Reference Replay:
        - 0.5
        - 0.645
        Row Verification:
        - 0.65
        - 0.745
        Final Gate:
        - 0.75
        - 0.845
        Report Test:
        - 0.85
        - 1.0
      target:
        Source Proposal:
        - 0.0
        - 0.145
        Candidate Screen:
        - 0.15
        - 0.245
        Reproduction:
        - 0.25
        - 0.445
        Row Verification:
        - 0.45
        - 0.595
        Final Gate:
        - 0.6
        - 0.795
        Report Test:
        - 0.8
        - 1.0
    sampling_caps_per_domain:
      anchor_train_per_supported_class: 4000
      anchor_validation_per_supported_class: 1000
      source_proposal_target: 4000
      source_proposal_supported_replay_per_supported_class: 400
      candidate_screen_target: 1000
      reproduction_target: 4000
      reproduction_supported_replay_per_supported_class: 400
      row_verification_target: 2000
      row_verification_supported_per_supported_class: 200
      final_gate_target: 2000
      final_gate_supported_per_supported_class: 200
      report_test_target: 2000
      report_test_benign: 2000
      report_test_other_supported_per_class: 500
    scaling:
      zero_standard_deviation_scale: 1.0
      clip_min: -10.0
      clip_max: 10.0
  secondary:
    name: CICIoT2023
    target_class: BACKDOOR_MALWARE
    pseudo_domain_partition_salt: 730201
capability_claim:
  target_f1_minimum: 0.8
  target_f1_gain_over_anchor_minimum: 0.2
  supported_macro_f1_drop_maximum: 0.02
  benign_false_alarm_rate_increase_maximum: 0.01
  candidate_free_anchor_target_f1_maximum: 0.5
  evidence_minima:
    reproduction_target_examples: 2000
    reproduction_supported_control_examples: 2000
    verification_target_examples: 1000
    verification_supported_control_examples: 1000
    proposal_screen_target_examples: 500
protocol:
  claim_opening:
    screen_domains: 3
    required_positive_screen_domains: 2
    candidate_free_required_adequate_domains: 2
  proposal_screen:
    fold_count: 5
    differential_minimum_nats_per_example: 0.05
    matched_controls_per_target: 1
  resource_horizon:
    maximum_logical_evidence_cycles: 30
    measurement_cycle_start: 0
    measurement_cycle_end: 12
  verification:
    panel_size: 3
    maximum_byzantine_verifiers_per_panel: 1
    required_positive_reports: 2
  synthesis:
    committee_size: 5
    maximum_byzantine_reproduction_rows: 1
  final_gate:
    minimum_adequate_non_source_domains: 6
    median_target_f1_minimum: 0.8
    minimum_domain_target_f1: 0.6
    supported_macro_f1_drop_maximum: 0.02
    benign_false_alarm_rate_increase_maximum: 0.01
  diagnostic_random_verifier_profile:
    byzantine_domain_count: 2
    panel_size: 3
    required_positive_reports: 2
    tolerated_contamination_risk: 0.15
model:
  optimizer:
    anchor_and_standard_fl_learning_rate: 0.001
    post_reference_learning_rate: 0.0005
    betas:
    - 0.9
    - 0.999
    epsilon: 1.0e-08
    weight_decay: 0.0001
  training:
    batch_size: 256
    gradient_global_l2_clip: 5.0
  anchor_fedavg:
    rounds: 20
    local_epochs_per_round: 1
    client_dropout: 0.0
    checkpoint_cadence_rounds: 1
    evaluation_cadence_rounds: 1
  post_reference:
    local_epochs: 5
    stability_kl_temperature: 1.0
    stability_weight: 1.0
    delta_l2_weight: 1.0e-05
  verifier_aware_backdoor_override:
    local_epochs: 10
    triggered_backdoor_loss_weight: 2.0
seeds_and_determinism:
  master_seeds:
  - 1103
  - 1217
  - 1321
  - 1427
  - 1543
  - 1667
  - 1777
  - 1879
  - 1999
  - 2081
  analysis_seed: 424242
  smoke_seed: 900001
attacks_and_boundaries:
  hidden_source_backdoor:
    trigger_value_after_standardization: 6.0
    confirmatory_poison_fraction: 0.05
    poison_fraction_sweep:
    - 0.01
    - 0.05
    - 0.1
  byzantine_reproduction:
    compromised_counts:
    - 0
    - 1
    - 2
    model_replacement:
      poison_fraction: 0.1
      delta_scale: 5.0
    verifier_aware:
      delta_scale: 1.0
  byzantine_verifier:
    compromise_counts:
    - 0
    - 1
    - 2
    behaviors:
    - False Positive
    - False Negative
  shared_label_error:
    strengths:
    - 0.05
    - 0.1
    - 0.2
  shared_spurious_feature:
    strengths:
    - 0.25
    - 0.5
    - 1.0
    value_after_standardization: 6.0
  attacker_induced_common_context:
    strengths:
    - 0.25
    - 0.5
    - 1.0
  capability_under_specification:
    root_cause_hash_modulus: 2
    shift_value_after_standardization: 3.0
    contracts:
    - Broad Target Only
    - Root-Cause A Scoped
    - Root-Cause B Scoped
    mixtures:
    - Balanced 50/50
    - A-Dominant 80/20
  heterogeneity:
    quantity_skew_multipliers:
    - 1.0
    - 0.9
    - 0.8
    - 0.7
    - 0.6
    - 0.5
    - 0.4
    - 0.3
    - 0.2
    feature_shift_selected_feature_count: 10
    feature_shift_magnitudes:
    - 0.5
    - 1.0
  clean_oracle_materiality:
    target_f1_decrease: 0.02
    supported_macro_f1_drop: 0.02
    benign_false_alarm_rate_increase: 0.01
baselines:
  local_only_reference_epochs: 20
  centralized_reference_epochs: 20
  fedavg_post_reference_rounds: 5
  multiple_model_certified_ensemble_group_count: 3
  reconstruction_filter:
    reconstruction_local_epochs: 1
    normalization_epsilon: 1.0e-12
    calibration_percentile: 95.0
  density_cluster_trimmed_mean:
    dbscan_epsilon: 0.25
    dbscan_min_samples: 2
    trim_each_tail_count: 1
    minimum_cluster_size_for_trimming: 3
  secure_continual_assessment_post_reference_rounds: 5
  recovery_after_source_admission:
    backdoor_alarm_percentile: 95.0
    recovery_rounds: 5
  source_update_sanitization:
    coordinate_bound_percentile: 95.0
  parameter_similarity:
    required_committed_rows: 5
    cosine_similarity_minimum: 0.9
  three_row_coordinate_median:
    row_count: 3
    assumed_byzantine_rows: 1
metrics_and_statistics:
  metric_aggregation:
    generic_defined_domain_fraction_minimum: 0.8
  multiplicity:
    family_wise_alpha: 0.05
  bootstrap:
    confidence_level: 0.95
    resamples: 10000
  materiality:
    target_f1_gain_minimum: 0.02
    supported_macro_f1_noninferiority_margin: 0.02
    benign_false_alarm_rate_noninferiority_margin: 0.01
    source_exclusion_asr_reduction_minimum: 0.2
    malicious_admission_reduction_minimum: 0.1
    legitimate_admission_noninferiority_margin: 0.05
    worst_domain_target_f1_gain_minimum: 0.05
    false_launch_reduction_minimum: 0.15
    reproduction_attempt_relative_reduction_minimum: 0.25
    post_evidence_overhead_relative_reduction_minimum: 0.2
    proposal_malicious_admission_worsening_maximum: 0.02
  technical_completion:
    minimum_complete_pairs_for_claim_support: 9
  publication_rounding:
    f1_accuracy_rates_decimals: 3
    percentage_decimals: 1
    effect_size_decimals: 3
    p_value_significant_digits: 4
    p_value_display_floor: 0.0001
    seconds_decimals: 2
    byte_units: IEC
    byte_decimals: 2
runtime:
  repository_layout:
    source: src/fedsira
    tests: tests
    raw_data: data/raw
    external_data: /external/datasets
    execution_workspace: outputs
    manuscript_results: results
  data_loader:
    workers: 0
    pin_memory: true
    persistent_workers: false
  timeouts_seconds:
    dataset_preprocessing: 7200
    scientific_cell_phase: 7200
    experiment_analysis_or_report: 1800
    final_export_verification: 1800
  automatic_infrastructure_retries_per_cell_phase: 1
  timing:
    warmup_forward_passes: 1
  same_environment_absolute_metric_tolerance: 1.0e-06
claim_support_thresholds:
  byzantine_operating_region:
    maximum_malicious_admissions_within_bound: 0
  safe_dormancy:
    maximum_permanent_singleton_admissions: 0
  capability_granularity_boundary:
    false_same_capability_certification_rate_minimum: 0.1
  heterogeneity_boundary:
    legitimate_admission_change_from_natural_maximum: 0.05
    worst_domain_target_f1_change_from_natural_maximum: 0.05
  secondary_generalization:
    target_f1_noninferiority_margin: 0.02
    malicious_admission_worsening_maximum: 0.05
validation_tolerances:
  random_committee_probability_absolute: 1.0e-12
  delay_component_sum_seconds_absolute: 1.0e-09
```

The typed loader may expose enums and immutable objects generated from this YAML, but generated objects are representations of configuration data rather than a second authority. Fixed methodology is implemented from the corresponding roadmap contracts; raw-data manifests, observed values, derived quantities, artifact identities, dependency fingerprints, and runtime measurements are not hand-configured values.


# 22. `outputs/` execution workspace

`outputs/` is the complete generated computational workspace used to resume, diagnose, validate, analyze, trace, and reproduce the study. Its repository-level structure is fixed by the project tree and has four structural scopes:

* `outputs/preprocessing/` contains raw-file/schema inventories, preprocessing validation evidence, deterministic prepared role views, immutable split/sample manifests, fixed feature/scaler products, exclusions, dataset identities, preparation fingerprints, and preprocessing provenance.
* `outputs/artifacts/` contains project-wide reusable scientific artifacts whose dependency fingerprints permit cross-experiment reuse: reusable models/checkpoints, score shards, fitted scientific objects, baseline intermediates, and derived protocol/certificate/synthesis products.
* `outputs/experiments/<descriptive-experiment-name>/` contains experiment-specific artifacts, evaluations, metrics, statistics, checkpoints, diagnostics, logs, and provenance that are not promoted to a project-wide reusable location.
* `outputs/cache/` contains only non-authoritative acceleration caches and `outputs/cache/staging/` for temporary atomic-write staging. Cache or staging content is never scientific evidence.

Scientific artifacts are immutable after publication. A producer writes payloads to `outputs/cache/staging/`, verifies payload checksums and its manifest, and atomically publishes the validated artifact to its canonical `outputs/preprocessing/`, `outputs/artifacts/`, or `outputs/experiments/<descriptive-experiment-name>/` location as `Complete`. Only `Complete` artifacts may be selected for scientific reads. Staging, failed, partial, checksum-mismatched, `Stale`, or retired artifacts are excluded.

Before any mutating command continues, it validates referenced artifact manifests and the dependency graph and removes stale descendants from active selection. Inactive diagnostic history may be retained only without making it selectable as scientific evidence. A stale descendant may never remain active beside a regenerated parent.

Expensive artifacts are shared across experiments, methods, and semantic cells under `outputs/artifacts/` whenever their Section 26 dependency fingerprint is identical. Experiment-specific products remain under the owning `outputs/experiments/<descriptive-experiment-name>/` subtree. Filesystem path, experiment that first requested a reusable artifact, timestamp, run UUID, or repository commit alone does not prevent reuse.

Structured execution logs belong under `outputs/experiments/<descriptive-experiment-name>/logs/execution/`; technical failure/interruption records belong under `outputs/experiments/<descriptive-experiment-name>/logs/failures/`; scientific, numerical, and runtime diagnostics belong under the corresponding `diagnostics/` subdirectories. Logs and diagnostics are never authoritative result storage. Scientific evaluations, metrics, and statistics are stored in their designated machine-readable experiment directories rather than reconstructed from logs.

# 23. `results/` manuscript-facing evidence

`results/` contains only compact verified manuscript-facing evidence materialized by `fedsira report`. It is never a computational input to preprocessing, training, scoring, evaluation, metrics, statistics, claim decisions, or execution recovery.

Its fixed structure is:

```text
results/
├── experiments/
│   └── <descriptive-experiment-name>/
│       ├── figures/
│       │   ├── main/
│       │   └── supplementary/
│       ├── tables/
│       │   ├── main/
│       │   └── supplementary/
│       ├── metrics/
│       │   ├── primary/
│       │   ├── secondary/
│       │   └── summary/
│       └── statistics/
│           ├── tests/
│           ├── confidence_intervals/
│           ├── effects/
│           └── multiplicity/
└── project_summary/
    ├── figures/
    │   ├── main/
    │   └── supplementary/
    ├── tables/
    │   ├── main/
    │   └── supplementary/
    ├── metrics/
    │   ├── primary/
    │   └── summary/
    ├── statistics/
    │   ├── comparisons/
    │   ├── confidence_intervals/
    │   ├── effects/
    │   └── multiplicity/
    ├── claim_registry/
    └── reproducibility/
        ├── configuration/
        ├── datasets/
        ├── seeds/
        ├── software/
        └── execution/
```

Experiment-owned figures, tables, compact metric summaries, and compact statistical summaries are exported under `results/experiments/<descriptive-experiment-name>/`. Genuine cross-experiment figures, tables, metrics, statistics, final claim states, and reproducibility summaries are exported under `results/project_summary/`.

Each materialized export records the exact completed `outputs/` artifact identities from which it was rendered. Reporting source-data products remain computational evidence under `outputs/`; `results/` contains only the compact export categories defined above. If any source identity changes, only the affected export and its reporting descendants become stale. A change to figure styling, table rendering, caption generation, or report layout does not invalidate training, scores, metrics, or statistics.

The exact internal filenames are implementation choices unless Sections 33–35 require a named scientific table, figure, metric, statistic, claim, or reproducibility product. `results/` must exclude caches, debug logs, failed/invalid runs, stale exports, overwrite archives, temporary files, and incomplete scientific evidence.

# 24. Public CLI contract

The public executable is `fedsira`. The complete operator interface is:

```bash
fedsira doctor
fedsira preprocess ["N-BaIoT"|"CICIoT2023"] [--overwrite]
fedsira plan
fedsira smoke [--overwrite]
fedsira run <experiment name> [--overwrite]
fedsira report [<experiment name>] [--overwrite]
```

No public command exposes method, baseline, attack, seed, scientific cell-phase, or scientific-parameter overrides. Those are resolved from the authoritative registries.

Every mutating command follows the same execution rule:

```text
validate existing artifacts
→ reuse compatible artifacts
→ identify and deactivate stale descendants
→ recompute only missing/invalidated producers
→ continue from the nearest valid artifact
→ atomically publish completed outputs
```

Dependency validity is stage-scoped as defined in Sections 25–27. No command treats a repository commit change by itself as a reason to rebuild all scientific evidence.

## 24.1 `fedsira doctor`

`doctor` is the authoritative read-only project, dataset, artifact, and experiment status command. It reports environment/configuration health; raw and preprocessed dataset readiness; artifact validity/stale-descendant status; each experiment's state, progress, nearest resumable boundary, blockers, failures/invalid cells, and report-export state; whether the four collapse decisions and `Resolved FedSIRA Core` artifact are complete; the current Section 29 project stage; and the next valid action. It writes no scientific artifact and does not repair or delete artifacts.

## 24.2 `fedsira preprocess ["N-BaIoT"|"CICIoT2023"]`

With a dataset identity, preprocess exactly that dataset; without one, preprocess all roadmap datasets requiring preprocessing. Preprocessing performs Sections 9–11, including raw identity/schema validation, canonicalization, archive/shard discovery, role/split construction, scaling, sampling caps, feasibility checks, leakage checks, and dataset/domain manifests. Raw source files are never modified.

A valid prepared-data artifact, split/role manifest, scaler, or deterministic prepared view is reused independently when its own dependency fingerprint matches. Reprocessing a dataset does not force retraining if the resulting upstream artifact identities are unchanged.

`--overwrite` forces rematerialization of preprocessing-owned artifacts under the same specified contract. Publication is atomic. If recomputed logical content and scientific identities are unchanged, existing descendants remain valid; if a published parent identity changes, only its descendants are marked stale.

## 24.3 `fedsira plan`

`plan` is read-only. It resolves canonical experiment order, dependencies, datasets, methods, conditions, seeds, expected Section 31 cell counts, blocked conditions, required matched-reference prerequisites, and reusable artifact families. Before collapse completion it shows post-core cells as dependent on the unresolved core; after all four collapse decisions exist it displays the mechanically derived core mapping. It does not create a user-managed plan or accept overwrite.

## 24.4 `fedsira smoke`

`smoke` runs the deterministic scientific invariant suite in Section 28. Smoke evidence validates implementation/protocol correctness but never enters manuscript statistics. An exact valid smoke result is reused.

`--overwrite` reruns the smoke suite only. It does not invalidate scientific artifacts unless the rerun discovers a true invariant/configuration defect that makes a scientific artifact invalid under Sections 25–27.

## 24.5 `fedsira run <experiment name>`

`<experiment name>` is the exact descriptive experiment name from Section 30. One invocation owns the complete scientific lifecycle for that experiment: prerequisite validation, planned cell execution, metric computation, statistical analysis, confidence intervals/effect sizes, multiplicity correction, scientific gates, invariant verification, provenance verification, and experiment completion.

Before executing a cell, `run` resolves its artifact DAG. Prepared data, split/scaler artifacts, anchors, source candidates, honest or malicious training checkpoints, model scores, calibration products, verifier/final-gate evaluations, and other intermediates are reused whenever their actual dependency fingerprints match, even if first produced for another experiment. Experiment identity is included in an artifact fingerprint only when the experiment definition changes the artifact's scientific semantics.

For collapse experiments, once the fourth required decision becomes complete, `run` also materializes/validates the deterministic `Resolved FedSIRA Core` artifact from Section 18.7. Post-core experiments refuse execution while that prerequisite is absent or stale.

If a later cell fails, already completed independent cells and shared upstream artifacts remain valid. After code/configuration is corrected, a later invocation recomputes only the first affected artifact and descendants. A metrics-code correction may reuse scores; a scoring-code correction may reuse checkpoints; a training-code correction may reuse prepared data and unaffected anchors; a reporting correction never reruns scientific computation.

Analysis/statistics/protocol verification are internal parts of `run`; there is no separate public analysis or verification command. A scientifically unfavorable/null result is still `Completed`. Technical execution failure is `Failed`; leakage, invariant, provenance, or authoritative-configuration violation is `Invalid`.

If every required artifact for the experiment is validly complete, `run` returns a successful already-completed message and creates no duplicate observation.

`--overwrite` deliberately recomputes artifacts owned by the requested experiment under the same authoritative scientific contract but does not recursively rebuild compatible shared prerequisites. Each replacement is staged and atomically activated. If a recomputed artifact has the same dependency/content identity as the active artifact, downstream artifacts remain valid; otherwise only descendants become stale. `--overwrite` never creates a second logical scientific observation.

## 24.6 `fedsira report [<experiment name>]`

`report` performs no scientific training, scoring, metric computation, or inferential recomputation. With an experiment identity it verifies that experiment's required scientific artifacts and materializes the applicable Section 33–34 exports. Without an experiment identity it first performs project-completion verification: Section 31 nominal/completion counts, all required experiment terminal states, invariant/leakage checks, artifact-DAG validity, Section 18 statistical/multiplicity artifacts, and Section 35 claim states must be internally consistent before project-summary exports are produced.

Matching exports are reused when their reporting dependency fingerprint matches. `--overwrite` rematerializes only reporting artifacts and never causes preprocessing, training, scoring, evaluation, metric, or statistical recomputation. A stale report descendant is removed from the active result set before replacement.

The authoritative execution order is Section 29; operator commands do not need to be repeated under individual experiment definitions.

# 25. Semantic identity, rerun, overwrite, and selective invalidation semantics

A scientific cell is identified only by the semantic coordinates that distinguish a planned condition: experiment, dataset, method, scenario, master seed, source/attack condition, heterogeneity regime, ablation/sensitivity setting, and any other experiment-declared grid coordinate. Deterministically derived facts, timestamps, machines, hashes, output paths, UUIDs, and recovery attempts are not scientific coordinates.

Artifact identity is finer-grained than cell identity. A cell may consume artifacts produced for another cell or experiment when the artifact's actual dependencies are identical. Conversely, two artifacts in the same cell are independently invalidated when they depend on different code/configuration/upstream scopes.

For an already completed matching cell, `run` validates all expected artifacts and their dependency fingerprints and skips every valid producer. It does not create a second active record, run ID, timestamped duplicate, or extra scientific observation.

An artifact dependency fingerprint is SHA-256 over canonical serialization of only the material dependencies declared for that artifact type:

```text
artifact_schema/version
+ relevant scientific-configuration subset
+ relevant observed dataset/split/view identities
+ relevant semantic coordinates and seed namespace values
+ exact upstream artifact identities
+ producer-component implementation fingerprint
+ relevant external runtime/dependency fingerprint
```

The producer-component fingerprint covers the local code units that implement that producer and their declared transitive scientific helpers. The relevant external dependency fingerprint includes only libraries/runtime components capable of changing that producer's scientific output. The full repository commit, full dependency lock, machine path, timestamps, logging configuration, comments, documentation, tests, unrelated CLI code, and unrelated package versions are provenance fields, not universal invalidation inputs.

A producer's declared dependency scope is part of its artifact schema and is tested by Section 28. Changing that scope is itself a producer-schema change and invalidates artifacts of that type.

Selective invalidation is transitive only downstream. When a complete parent artifact changes identity, the active artifact graph marks exactly its descendants stale before any new downstream read. Unrelated branches remain complete and reusable.

An infrastructure interruption may resume the same unchanged Section 19 scientific cell phase once from the nearest hash-valid recovery checkpoint. It does not create an additional seed or condition. After a genuine implementation correction, rerunning the same experiment is permitted under the unchanged scientific plan: the corrected producer-component fingerprint invalidates only affected artifacts and descendants, while compatible upstream science remains reusable.

`--overwrite` is explicit recomputation, not scientific redesign. It recomputes the requested command's owned products under the same authoritative inputs and may reuse compatible shared parents. Atomic replacement occurs only after the new artifact is complete and verified. A retained old payload is diagnostic history only and can never remain simultaneously active.

Completed active metric stores contain at most one authoritative row per declared semantic key.

# 26. Scientific artifact contract

Authoritative numeric result/statistical data are stored in machine-readable tabular form, preferably Parquet; JSON artifacts use typed schemas. The roadmap does not prescribe a general workflow engine or a field-by-field software manifest. It does require the following scientific artifact boundaries because they determine reuse, recovery, and invalidation.

## 26.1 Scientific execution graph

All experiments resolve onto this acyclic scientific graph:

```text
raw inputs
→ dataset preparation
→ preprocessing / roles / splits / scaling
→ training / checkpoints
→ scoring
→ calibration / threshold artifacts where applicable
→ protocol evaluation / metrics
→ statistical analysis / claim decisions
→ tables / figures / reporting
```

Protocol-specific artifacts such as source commitments, verifier assignments/reports, reproduction certificates, Krum synthesis, and final-gate decisions attach to the corresponding training/scoring/evaluation nodes. They never bypass their declared upstream identities.

The normal execution path is always:

```text
validate existing artifacts
→ reuse compatible artifacts
→ mark stale descendants inactive
→ recompute missing or affected nodes only
→ continue execution
```

## 26.2 Artifact validity and lifecycle

Every reusable scientific artifact has one producer type and may have many consumers. It is valid only when:

1. its semantic key is well-formed for that artifact type;
2. its dependency fingerprint matches the currently resolved dependencies;
3. every referenced upstream artifact is itself `Complete` and hash-valid;
4. every payload checksum matches the manifest;
5. its producer finished successfully and atomically published the complete manifest;
6. no active ancestor identity has changed since publication.

The lifecycle is:

```text
Staging → Complete → Stale/Retired
```

`Failed`, interrupted, partial, or checksum-mismatched staging data never becomes `Complete`. Only `Complete` artifacts may be consumed. `Stale` and `Retired` artifacts are diagnostic history only.

## 26.3 Reusable artifact families

| Artifact family                                    | Clear producer                           | Material dependencies                                                                                                                                                                         | Primary consumers and reuse boundary                                                                                                                    |
| -------------------------------------------------- | ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Raw dataset identity                               | `preprocess` acquisition/validation path | exact raw bytes/file hashes and raw-manifest schema                                                                                                                                           | all preparation; reused until raw identity changes                                                                                                      |
| Canonical dataset/schema/exclusion manifest        | dataset preparation                      | raw identity, parser/label/schema/nonfinite rules, preparation component fingerprint                                                                                                          | role/split/scaler construction; a parser/schema change invalidates preparation descendants but not unrelated datasets                                   |
| Role/split/sample manifest                         | preprocessing                            | canonical dataset identity, role intervals, guard gaps, domain partitioning, sampling caps/order seed, target/support mapping, split component fingerprint                                    | all training/evaluation views; reused across all experiments with the same protocol                                                                     |
| Scaler                                             | preprocessing                            | supported `Anchor Train` rows, scaling formula, feature schema, scaling component fingerprint                                                                                                 | all model inputs for that dataset/protocol                                                                                                              |
| Prepared role view                                 | preprocessing                            | role/split manifest, scaler, deterministic transformation-independent view definition                                                                                                         | training/scoring; role-specific views are independently reusable                                                                                        |
| Anchor checkpoint and round checkpoints            | anchor training                          | prepared anchor views, model definition/init, anchor optimizer/training contract, master-seed namespaces, relevant PyTorch/CUDA deterministic runtime, training component fingerprint         | source training, reproductions, baselines, scoring; shared across experiments when identical                                                            |
| Source candidate checkpoint/update                 | source training                          | anchor identity, source domain, source/scenario/attack training data view, Capability Claim Contract-relevant training config, attack transform when applicable, seeds, training component/runtime fingerprint      | proposal screen, source-authority baselines, malicious source scenarios                                                                                 |
| Honest or Byzantine reproduction checkpoint/update | reproduction training/attack producer    | anchor identity, reproducer, exact reproduction view, training objective/config, attack strategy/strength if any, seeds, relevant training/attack component/runtime fingerprint               | external reproduction verification, direct-Krum comparators, robustness, ablations; the same row is reused when these dependencies match                                               |
| Standard FL/baseline checkpoint/update             | baseline trainer                         | exact baseline algorithm, prepared views, anchor/start model, budget, attack condition, seeds, baseline-training component/runtime fingerprint                                                | baseline scoring/evaluation; no reuse across scientifically different baseline algorithms                                                               |
| Model score artifact                               | scoring producer                         | exact model/checkpoint identity, exact sample/view identity, scoring transform, output-class registry, scoring component fingerprint, relevant numerical runtime                              | screen calculations, verifier/final/report metrics; checkpoint remains valid when only metric code changes                                              |
| Screen matching/differential artifact              | proposal-screen calibration producer     | anchor/source score artifacts, screen folds, matching/quantile rule, Capability Claim Contract screen constants, calibration component fingerprint                                                                  | proposal opening decision; reusable across experiments with identical source/screen semantics                                                           |
| Baseline calibration artifact                      | named baseline calibration producer      | exact calibration score/update population, calibration rule and percentile, relevant baseline config and calibration component fingerprint                                                    | `Update Reconstruction Filter`, `Recovery after Source Admission`, `Source-Update Sanitization Reference`; each calibration type is independently keyed |
| Fixed Capability Claim Contract/Krum/protocol configuration              | Configuration YAML           | Sections 5–7 and 13 constants                                                                                                                                                                 | all protocol decisions; fixed thresholds are configuration, not learned calibration outputs                                                             |
| Verifier assignment/report                         | external reproduction verification evaluator                            | committed reproduction identity, Capability Claim Contract identity, eligible-domain state, verifier-order seed, exact row-verification score artifact, verifier behavior profile, evaluation component fingerprint | reproduction certificate                                                                                                                                |
| Reproduction certificate                           | certificate producer                     | certified-row reports/commitments and certificate rule                                                                                                                                        | Krum synthesis; reused only for the same five certified row identities/order semantics                                                                  |
| Krum synthesized update/model                      | synthesis producer                       | five certified/noncertified input row identities as required by method, Krum config, synthesis component fingerprint                                                                          | final gate, report-test scoring                                                                                                                         |
| Final-gate evaluation/decision                     | final-gate evaluator                     | synthesized/production model identity, exact final-gate score artifacts, domain adequacy, Capability Claim Contract/final-gate rules, evaluation component fingerprint                                              | admission outcome, metrics, claims                                                                                                                      |
| Domain/seed metric artifact                        | metric registry                          | score/evaluation artifacts, exact metric definitions, aggregation rules, adequacy/NA rules, metric component fingerprint                                                                      | statistics, tables, figures; a metric-code change need not invalidate models or scores                                                                  |
| Statistical comparison/gate artifact               | analysis producer                        | exact seed-level metrics, pairing set, comparison definition, test/sidedness, Holm family, bootstrap seed/resamples, materiality rule, analysis component fingerprint                         | claim registry, tables, figures                                                                                                                         |
| Claim-state artifact                               | claim-decision producer                  | mandatory statistical/gate artifacts and Section 35 rule                                                                                                                                      | project summary/report                                                                                                                                  |
| Table/figure source data                           | reporting source-data producer           | exact verified metric/statistical/claim identities and table/figure data-selection spec                                                                                                       | renderers; stored as derived computational artifacts under `outputs/artifacts/derived/` or the owning `outputs/experiments/<descriptive-experiment-name>/artifacts/derived/` according to reuse scope                  |
| Table/figure/report export                         | `report`                                 | source-data identities, formatting/rendering specification, reporting component/dependency fingerprint                                                                                        | manuscript-facing `results/experiments/<descriptive-experiment-name>/` or `results/project_summary/` only                                                                                                            |

A score artifact contains per-sample model outputs needed by downstream metrics, including logits/probabilities/predictions and losses when required by the screen/calibration definition. The implementation may shard large score artifacts deterministically; a complete score artifact is publishable only when every declared shard is complete and its aggregate manifest verifies.

## 26.4 Selective invalidation boundaries

The following are the minimum invalidation rules. A change may invalidate a narrower subset when the artifact type declares a narrower true dependency, but it may never preserve an artifact whose material dependency changed.

| Change                                                                                                                                                                                                                    | Recompute from                                  | Preserve when otherwise compatible                                                              |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Raw dataset bytes/file identity, raw parser semantics, canonical label mapping, predictor inclusion/exclusion, or secondary complete-case rule                                                                            | affected dataset preparation                    | all artifacts for unrelated datasets                                                            |
| Role intervals, guard gaps, sampling caps/order, domain/pseudo-domain partition, target/support role mapping, scaler formula or scaler source population                                                                  | affected preprocessing/split/scaler artifacts   | raw identity; unrelated dataset artifacts                                                       |
| Model architecture/init, training objective, optimizer/budget, training-role data, seed stream used by training, attack transform used during training, or training implementation/runtime capable of changing parameters | affected checkpoint/update                      | prepared data/splits/scaler and unrelated trained models                                        |
| Scoring transform, model-to-output code, class-output interpretation, or scoring runtime capable of changing predictions/losses                                                                                           | affected score artifacts                        | checkpoints and upstream data                                                                   |
| Screen matching/quantile logic or a learned baseline calibration rule/population                                                                                                                                          | affected calibration artifact                   | checkpoints and reusable scores if unchanged                                                    |
| Capability Claim Contract/final-gate/verifier decision implementation or metric definition/aggregation/adequacy logic                                                                                                                           | affected protocol evaluation or metric artifact | checkpoints and scores unless scoring itself changed                                            |
| Statistical test, sidedness, Holm family implementation, bootstrap implementation/seed/resample rule, materiality logic, or pairing logic                                                                                 | affected statistical/claim artifact             | all training, scores, evaluations, and seed metrics                                             |
| Table/figure data-selection specification                                                                                                                                                                                 | affected source-data/report product             | scientific metrics/statistics                                                                   |
| Plot style, layout, table renderer, caption/template, output format                                                                                                                                                       | affected report export only                     | all scientific artifacts and report source data                                                 |
| Timing instrumentation, physical machine, CPU-thread profile, CUDA timing method, or concurrent-load condition                                                                                                            | affected efficiency/timing artifact only        | non-timing scientific model/metric artifacts unless a separate material dependency also changed |

A repository commit hash is never by itself a recomputation boundary. The full dependency lock is likewise not a blanket invalidation key: only relevant dependency versions declared by the producer are fingerprinted for reuse. The complete commit and lock remain recorded for provenance and reconstruction.

Changes to documentation, comments, tests, CI, logging, `doctor`/`plan` presentation, filesystem paths, compression/containerization that preserves logical payloads, report formatting, or code wholly outside a producer's declared component dependency scope do **not** invalidate scientific artifacts.

## 26.5 Experiment dependency and reuse map

The Section 30 experiment definitions are authoritative for scientific semantics and counts. This table fixes their execution-level artifact flow without changing any experiment.

| Experiment/stage | Required reusable inputs | Principal owned outputs and downstream consumers |
| --- | --- | --- |
| `Data and Domain Evidence Validation` | raw dataset identities | canonical dataset/schema/exclusion manifests, split/role manifests, scaler, feasibility/leakage evidence → every later stage |
| `Protocol Invariant Validation` | processed schema plus deterministic fixtures | smoke/invariant evidence → blocks or permits scientific execution; never manuscript statistics |
| `Baseline Implementation Validation` | prepared data, anchors, matching baseline calibrations/checkpoints | engineering validation cells → permits baseline use |
| `Proposal-Assisted Opening Necessity` | prepared data, anchor, episode-specific source candidates, screen scores/matching, compatible reproductions/evaluations | proposal metrics/statistics and survival decision |
| `Single-Reproduction Necessity` | prepared data, anchor, condition-specific reproduction rows/scores/evaluations | plurality metrics/statistics and survival decision |
| `Source-Artifact Exclusion Necessity` | prepared data, anchor, shared scenario/source candidate, compatible source/reproduction/baseline artifacts | source-exclusion statistics/gate and claim input |
| `External Verification Necessity` | same precommitted reproduction opportunities/rows for both methods | verifier/certificate and direct-Krum paths, metrics/statistics, survival decision |
| Resolved-core derivation | four collapse decision artifacts | `Resolved FedSIRA Core` identity/mapping → all Sections 30.9–30.20 |
| `Primary Confirmatory Evaluation` | resolved core, prepared data, shared anchors, exact compatible training/score artifacts | primary evaluation/metric/statistical artifacts → claims/tables/figures |
| `Mechanism Ablation` | full-reference matched prerequisite plus reusable non-ablated parents | variant-specific stage/descendants and ablation statistics |
| `Compromised-Reproducer Robustness` | prepared data, anchor, clean rows reusable across attack-count cells where identities match | malicious row variants, verification/Krum/final evaluations, robustness metrics/statistics |
| `Compromised-Verifier Robustness` | committed reproduction rows/scores unaffected by verifier behavior | verifier reports onward; verifier compromise does not retrain reproductions |
| `Byzantine-Bound Violation` | compatible clean/malicious rows and verifier evidence | bound-specific certification/synthesis/evaluation metrics |
| `Evidence Scarcity and Dormancy` | prepared data, anchor, holder-specific reproduction artifacts once holder becomes eligible | state trajectory/certificate timing; valid holder artifacts persist across cycles |
| `Shared Epistemic-Failure Boundary` | prepared clean base views, anchor, matched uncorrupted reference | strength-specific transformed views and affected descendants; clean oracle retained |
| `Capability Under-Specification Boundary` | root-cause prepared views, anchor, reusable training artifacts where contract scope does not alter training | contract-specific verification/certification/final metrics |
| `Heterogeneous-Reproduction Boundary` | prepared base data, anchor | regime-specific views/reproductions onward; natural artifacts shared wherever exact |
| `Admission-Delay Decomposition` | prepared data, anchor, compatible artifacts not inside measured wall-clock segment | logical-state/timing decomposition artifacts |
| `Efficiency Measurement` | already-preprocessed data and specified method definitions | five intentionally repeated timed executions per method-seed; measured segments are deliberately recomputed |
| `Secondary-Dataset Generalization` | secondary prepared data, secondary anchors, resolved core | secondary protocol/evaluation/statistics → generalization claim |
| `report` | verified completed metric/statistical/claim/source-data identities | compact manuscript-facing results; no scientific recomputation |

## 26.6 Cross-experiment reuse rules

Reuse is permitted across experiment names when the consumed artifact would be scientifically identical if recomputed. In particular:

* the same prepared dataset, split/role manifest, scaler, and anchor checkpoint are not retrained per experiment;
* a source candidate for the same dataset, seed, source, scenario/attack, prepared views, and training contract is trained once per matching artifact identity and may serve every compatible method/experiment;
* a clean reproduction row for the same anchor, domain, role view, objective, seed, heterogeneity/attack condition, and training implementation is trained once per matching artifact identity and may feed FedSIRA external reproduction verification, direct-Krum comparisons, ablations, or robustness cells;
* verifier compromise changes invalidate verifier reports/certificates and descendants, not the underlying committed reproduction row;
* changes to Krum or final-gate rules invalidate synthesis/final evaluation and descendants, not reproduction training;
* metric/statistical/reporting changes never trigger model retraining unless they also change a true training dependency;
* report-test scoring can be reused across multiple metrics/figures when the model and exact report population are identical.

Scientific independence requirements override cache reuse. Distinct master seeds, distinct semantic transformations, and distinct training algorithms are not collapsed merely because outputs happen to be numerically equal.

The implementation must retain all scientifically meaningful objects needed by this study: dataset/preprocessing/split/domain identity and leakage validation; seed bundle and semantic cell identity; claim/Capability Claim Contract and evidence state; source/reproducer/verifier/final-gate assignments; domain- and seed-level metrics; paired statistics/effects/CIs/multiplicity/materiality decisions; technical versus scientific terminal outcomes; final claim state; and table/figure source data. Logs are never result storage.

# 27. Logging, provenance, and dependency fingerprints

Logging is diagnostic and may use any structured format that preserves enough context to diagnose failures; exact event fields and filenames are implementation choices within `outputs/experiments/<descriptive-experiment-name>/logs/execution/` and `outputs/experiments/<descriptive-experiment-name>/logs/failures/`.

Every manuscript-facing number must be reproducibly traceable to completed scientific evidence: the owning experiment/cell and producer/cell-phase identities, applicable configuration subset, dataset and split/domain identities, seeds, upstream artifact identities, producer-component fingerprints, relevant runtime/dependency signatures, and the statistical analysis that produced the reported value.

For reconstruction, each artifact also records the repository commit, full dependency lock identity, environment/hardware record, and creation context. These broad provenance records do not replace stage-scoped dependency fingerprints and do not cause blanket invalidation.

## 27.1 Producer-component and external-dependency fingerprint construction

Producer fingerprints are computed from executable scientific code semantics rather than whole-repository commits. For each artifact family, `artifacts/fingerprints.py` starts from the entry modules below and recursively includes every runtime `fedsira.*` module imported by those modules, excluding imports guarded solely by `TYPE_CHECKING`, tests, reporting-only modules not imported by the producer, and package `__init__.py` files that contain no executable statements beyond imports/version constants. Dynamic imports in scientific producer code are forbidden.

| Artifact family | Producer entry modules | Relevant external dependency identity |
| --- | --- | --- |
| raw/schema/exclusion manifest | dataset-specific `acquisition.py`, `schema.py`, `validation.py` | Python, pandas, NumPy, archive reader used for acquired format |
| role/split/sample/prepared/scaler | `datasets/roles.py`, `sampling.py`, `scaling.py`, dataset-specific `preprocessing.py` | Python, pandas, NumPy, pyarrow |
| anchor/FedAvg checkpoints | `models/mlp.py`, `learning/training.py`, `federated.py`, `anchor.py`, `runtime/determinism.py` | Python, PyTorch, CUDA/cuDNN runtime identity, NumPy |
| source/reproduction checkpoints | `models/mlp.py`, `learning/training.py`, `post_reference.py`, applicable `attacks/*.py`, `runtime/determinism.py` | Python, PyTorch, CUDA/cuDNN runtime identity, NumPy |
| baseline checkpoint/calibration | applicable `baselines/*.py`, shared `learning/*.py`, `runtime/determinism.py` | Python, PyTorch where trained, NumPy, SciPy/scikit-learn where used |
| model scores | `models/mlp.py`, `learning/scoring.py` | Python, PyTorch, CUDA runtime identity, NumPy |
| opening/verifier/certificate/synthesis/final gate | applicable `protocol/*.py`, `evaluation/metrics.py`, `learning/aggregation.py` | Python, NumPy, SciPy/scikit-learn only when imported by the resolved producer |
| boundary transformation | applicable `boundaries/*.py`, `attacks/*.py`, `datasets/sampling.py` | Python, NumPy, pandas/pyarrow for materialization |
| metric artifact | `evaluation/metrics.py`, `evaluation/aggregation.py`, `evaluation/validation.py` | Python, NumPy, scikit-learn only for metrics actually using it |
| statistical/comparison artifact | `analysis/statistics.py`, `analysis/comparisons.py` | Python, NumPy, SciPy, statsmodels where imported |
| claim-state artifact | `analysis/claims.py`, `analysis/comparisons.py` | Python, NumPy |
| report source/export | applicable `reporting/*.py` | Python, pandas, pyarrow, Matplotlib for figures |

For every included Python source module, parse with the reference Python version, remove location metadata, remove module/class/function docstring expressions, and serialize `ast.dump(tree, annotate_fields=True, include_attributes=False)` as UTF-8. Comments and formatting never enter the AST. The component fingerprint is SHA-256 over canonical length-prefixed `(normalized_relative_path, normalized_ast_dump)` pairs sorted by relative path, plus the artifact producer-schema version. Consequently comments/docstrings/formatting do not invalidate science, while executable literals, imports, control flow, formulas, and dependency-scope changes do. Syntax-invalid or dynamically generated scientific source is `Configuration Invalid`.

The external-dependency fingerprint includes the exact version/build identity for packages in the table's relevant set that are actually imported by the transitive producer closure **and for any declared external executable actually invoked by that producer**; for N-BaIoT acquisition this includes the Section 9.1.1 `unrar` version whenever RAR extraction is used. For CUDA-producing components it additionally includes PyTorch CUDA build, CUDA runtime, cuDNN version, GPU compute capability, and deterministic backend flags. The complete `uv.lock`, OS/hardware record, and repository commit remain broad provenance snapshots but are not universal cache keys.

Architecture tests must verify that each scientific producer's runtime import closure is reproducible and that importing a new local/external scientific dependency changes the corresponding component/dependency fingerprint before an old artifact can be selected.

Provenance validation must distinguish:

* **scientific/configuration mismatch** — invalidate the affected producer and descendants;
* **dataset/split/upstream mismatch** — invalidate the affected producer and descendants;
* **material producer-code/runtime mismatch** — invalidate the affected producer and descendants;
* **non-material repository/dependency change** — record the new provenance context but preserve the artifact;
* **partial/stale payload** — reject immediately.

The active dependency graph is derived from immutable upstream artifact identities. When a producer is republished with a different identity, descendants are marked stale before they can be read. Incomplete, stale, or technically invalid evidence can never substitute for required completed verified evidence.

# 28. Validation and smoke-test contract

**Configuration authority:** only the numerical tolerances in `validation_tolerances` and any numerical scientific/runtime configuration keys explicitly referenced by a test. The tests, invalid fixtures, expected failure classes, and invariant semantics themselves are fixed by this section.

`fedsira smoke`, authoritative preprocessing validation, and the internal prerequisite checks of `fedsira run` must collectively prove all of the following before baseline validation begins.

## 28.1 Data tests

* exact raw-file checksum capture;
* deterministic role regeneration;
* no cross-role sample overlap;
* no target sample in anchor roles;
* scaler fit uses only supported anchor-training rows;
* guard-gap rows never appear downstream;
* source/reproducer/verifier/final/report roles are disjoint;
* structural missing classes are recorded rather than fabricated;
* repeated preprocessing produces the same content hashes;
* primary `sample_id` and the master-seed-independent preprocessing sample-order seed match the exact Section 10 canonical-hash fixtures;
* N-BaIoT archive and already-extracted layouts resolve to the same canonical `(domain,class,sample)` identities when their extracted CSV bytes are identical;
* CICIoT2023 label normalization, identifier exclusion, stable-row ordering, pseudo-domain assignment, and group-local role intervals match hand fixtures.

## 28.2 Model/FL tests

* one-batch forward/backward finite;
* one-round FedAvg matches a hand-computed weighted average fixture;
* checkpoint restore reproduces predictions within `1e-6` absolute tolerance;
* data-loader seed affects only intended shuffling;
* final-round selection is enforced;
* report-test loader cannot be requested by training code;
* AdamW state persists across epochs inside one invocation but resets between FedAvg rounds;
* isolated child-seed derivation makes identical training jobs bitwise-identical regardless of execution scheduling;
* a post-reference minibatch with no supported rows sets only the KL term to zero and still computes CE/L2 exactly as Section 12.4.

## 28.3 Protocol invariant tests

* source direct production weight cannot become nonzero;
* honest reproduction constructor has no source-artifact parameter;
* source cannot be verifier;
* reproducer cannot self-certify;
* verifier assignment before commitment throws an invariant error;
* duplicate authority vote is rejected;
* Capability Claim Contract mutation after reproduction begins is rejected;
* `Abstain` cannot be cast to boolean vote;
* fewer than five certified rows cannot call primary Krum synthesis;
* source update hash cannot appear in final Krum input manifest;
* final admission without final-gate artifact is impossible;
* source-copy Byzantine fixture is accepted as an attack input but labeled Byzantine;
* every legal and illegal Section 6.3 state transition has an explicit fixture, including candidate-free adequate rejection and Dormant resumption;
* all eight `(P,R,V)` Section 18.7 collapse combinations resolve to exactly the specified opening/reproduction/verification/production-update path;
* source/backdoor replacement poisoning preserves training-set cardinality, while the verifier-aware auxiliary-trigger construction preserves the clean originals as specified;
* the communication-accounting serializer yields identical bytes for semantically identical messages independent of Python dictionary insertion order.

## 28.4 Mathematical tests

* primary panel `2 positives, f_V=1` implies at least one honest positive;
* Krum requires `n>=2f+3`; `n=3,f=1` is rejected;
* Krum nearest-neighbor and tie rules match hand fixtures;
* random-committee exact probability is `0` for compromised-verifier counts 0/1 and `1/7` for count 2 within `1e-12`;
* post-evidence wall-clock components satisfy `T_post = T_assignment + T_reproduce + T_verify + T_synthesize` within `1e-9` seconds for a synthetic timer fixture; logical `T_evidence` is checked separately and is never added to seconds.

## 28.5 Metric/statistical tests

* confusion-derived metrics match hand calculations;
* zero denominators return `NA` plus reason;
* type-7 quantiles match NumPy `method="linear"` fixtures;
* sample SD uses `ddof=1`;
* exact sign-flip test enumerates exactly 1024 assignments at `n=10`;
* Holm adjustment matches an independent hand fixture;
* 10,000 bootstrap draws are deterministic under seed 424242;
* client rows never become independent inferential observations.

Generic software tests must additionally cover deterministic serialization/config loading, CLI routing, artifact replacement, failure diagnosis, and completed-cell reuse. These are implementation-quality requirements and are not separate scientific invariants.

## 28.6 Artifact reuse and recovery tests

The implementation-quality suite must additionally prove:

* a repository-only documentation/comment/test change leaves scientific artifact fingerprints unchanged;
* changing preprocessing logic invalidates the affected prepared artifacts and all scientific descendants, but not the other dataset;
* changing training logic invalidates affected checkpoints/scores/metrics/statistics/reports while preserving compatible prepared data;
* changing scoring logic invalidates scores and descendants while preserving checkpoints;
* changing metric logic invalidates metrics/statistics/reports while preserving scores and checkpoints;
* changing statistical logic invalidates statistics/claim/report products while preserving seed metrics;
* changing only figure/table rendering invalidates only reporting artifacts;
* changing one parent identity marks exactly its transitive descendants stale and removes them from active selection;
* a staged/crashed/checksum-corrupt artifact is never accepted as complete;
* rerunning an already complete experiment performs zero scientific recomputation when all required fingerprints match;
* a resumed deterministic training trajectory from a recovery checkpoint satisfies the Section 20 prediction tolerance against uninterrupted execution;
* `--overwrite` cannot create duplicate logical observations and does not rebuild compatible shared prerequisites;
* identical reusable artifacts requested by two experiments resolve to one canonical artifact identity;
* executable-code AST changes alter only the producer families whose transitive component scope includes the changed module, while comment/docstring-only changes leave the component fingerprint unchanged.

# 29. Authoritative execution sequence

**Authoritative execution order:** the table below is the fixed scientific execution sequence. It is not duplicated as a YAML list; implementation orchestration must encode this order directly and may use configuration only for the values consumed by each stage.

| Order | Stage | Blocking condition |
| ---: | --- | --- |
| 1 | `doctor` readiness diagnosis | specified environment/configuration is valid and required raw inputs are identifiable |
| 2 | Preprocessing and data/domain validation | Sections 9–11 schema, identity, split, leakage, target/evidence feasibility, and deterministic preprocessing checks pass |
| 3 | Protocol/invariant smoke | Section 28 scientific invariants and intentionally invalid fixtures behave exactly as specified |
| 4 | Baseline implementation validation | all Section 16 baselines are validated or explicitly `Invalid` before claim-bearing use |
| 5 | Four mechanism-collapse experiments | Section 18 survival rules have complete required evidence |
| 6 | Resolved-core derivation | all four collapse decision artifacts exist; the Section 18.7 mapping automatically materializes `Resolved FedSIRA Core` |
| 7 | Primary confirmatory evaluation | resolved-core artifact and all prerequisites are valid |
| 8 | Mechanism ablations | all 18 specified variants and their matched full-reference prerequisites execute |
| 9 | Byzantine robustness and bound violations | reproducer, verifier, and above-bound matrices execute |
| 10 | Evidence and scientific failure boundaries | scarcity, epistemic, under-specification, and heterogeneity programs execute |
| 11 | Delay and efficiency | logical evidence delay and post-evidence operational cost are measured with the specified methodology |
| 12 | Secondary generalization | the resolved mechanism is evaluated without core retuning |
| 13 | Project statistical/claim completion | every experiment's required metrics/tests/multiplicity/materiality artifacts exist and Section 35 claim states are mechanically derivable |
| 14 | `report` project verification and export | Section 31 counts, invariants, provenance, artifact-DAG validity, claim states, and required Section 33–34 source products validate |

The resolved-core artifact is a deterministic derived scientific artifact, not an operator-managed planning step. Once all four collapse experiments are complete, the next `fedsira run`/`doctor` resolution pass creates or validates it automatically from the four decision artifacts.

The sequence is a scientific ordering constraint, not a requirement to recompute earlier stages. At every stage the implementation first validates and reuses compatible artifacts from Sections 25–27. Failure of one later experiment leaves earlier completed experiments and shared parents intact. After a repair, execution resumes from the first stale or missing dependency in the affected branch.

A technical failure blocks only dependent science. A valid null or boundary result does not become a software failure and cannot be used to retune the method. If a collapse gate rejects a central mechanism claim, later characterization may continue but cannot resurrect that rejected claim through post-hoc selection.

# 30. Experiment registry

**Authoritative experiment registry:** this section defines the complete experiment identities, methods, conditions, seeds, dependencies, metrics, interpretation, and failure consequences. These fixed scientific matrices are not duplicated in YAML; numerical values used by their cells come from the applicable configuration keys.

Scientific execution experiments below use their descriptive name as the positional identity in `fedsira run <experiment name>`. The data/domain validation contract in Section 30.1 is owned by `preprocess`, and the protocol-invariant validation contract in Section 30.2 is owned by `smoke`. No opaque experiment number is used as an experiment identity.

## 30.1 `Data and Domain Evidence Validation`

**Class:** `Validation`
**Runs:** 1 primary validation run plus secondary preprocessing/data-validation coverage inside the same lifecycle; no inferential seed.

**Purpose:** prove that exact datasets, features, labels, domain proxies, role intervals, evidence minimums, and leakage constraints are implementable.

**Inputs:** raw dataset manifests, Sections 9–11 data contract.
**Actions:** raw-data identity validation, role construction, scaling, sample-cap application, evidence-feasibility count, leakage audit.
**Pass:** primary target available on at least 7 device proxies, at least 5 non-source reproduction-adequate proxies and 6 final-gate-adequate proxies can exist after source exclusion, no leakage/schema/finite-value failure.
**Failure:** `Data Invalid`; primary scientific program blocked.

## 30.2 `Protocol Invariant Validation`

**Class:** `Validation`
**Runs:** 1 aggregated smoke suite.

**Purpose:** establish executable state-machine, external reproduction verification, Krum, source-firewall, metric, statistics, identity, and provenance correctness before scientific runs.

**Inputs:** deterministic tiny fixtures and processed schema.
**Pass:** every Section 28 required test passes; all intentionally invalid cases fail for the correct reason.
**Failure:** block all scientific runs.

## 30.3 `Baseline Implementation Validation`

**Class:** `Validation`
**Runs:** 17 baseline validation cells.

**Methods:** every baseline in Section 16.
**Scenario:** one benign sanity case plus the minimum mechanism-specific adversarial fixture where required.
**Seed:** fixed engineering seed `900001`; not part of confirmatory inference.
**Pass:** finite model/output, expected mechanism path executed, common metrics generated, no test-role tuning.

## 30.4 `Proposal-Assisted Opening Necessity`

**Class:** `Exploratory` with preregistered collapse decision.
**Runs:** `2 opening modes × 4 episodes × 10 seeds = 80`.

**Opening modes:**

* `Proposal-Assisted`;
* `Candidate-Free`.

**Episodes:**

1. `Legitimate Target Capability`;
2. `Generic Hard Supported Examples` — high anchor loss from supported classes but no target capability;
3. `Irrelevant Source Improvement` — source improves a supported class, not the fixed target;
4. `Useful Backdoored Source — 5%`.

**Controls:** downstream reproduction/external reproduction verification/Krum/final path identical between opening modes.
**Primary metrics:** false-launch rate, reproduction attempts, post-evidence overhead, legitimate admission, malicious admission.
**Statistics:** Section 18 proposal-screen family.
**Interpretation:** apply proposal-survival rule exactly.
**Failure semantics:** no material proposal advantage is a scientific null and removes proposal assistance from the simplest core; it does not invalidate source-independent admission.

## 30.5 `Single-Reproduction Necessity`

**Class:** `Exploratory` with preregistered collapse decision.
**Runs:** `2 methods × 3 conditions × 10 seeds = 60`.

**Methods:** `One Independent Retrain`, `Full Plurality Path`.
**Conditions:**

* `Legitimate Transferable Capability`;
* `Honest Site-Specific Feature Shift — 1.0`;
* `One Byzantine Source-Copy Reproducer`.

Condition semantics are exact: `Legitimate Transferable Capability` is the clean Section 15.10 `Legitimate Target Capability`; `Honest Site-Specific Feature Shift — 1.0` is that same clean capability under Section 15.9 `Feature Shift ±1.0`; `One Byzantine Source-Copy Reproducer` uses `Useful Backdoored Source — 5%` plus the first attack-feasible non-source domain in `Reproducer Order` submitting `Source Copy`, with all other participants honest.

**Primary metrics:** malicious admission, legitimate admission, target F1, supported harm, worst-domain target F1.
**Statistics:** plurality claim family.
**Decision:** apply Section 18 plurality-survival rule.

## 30.6 `Source-Artifact Exclusion Necessity`

**Class:** `Exploratory` with central preregistered collapse gate.
**Runs:** `6 methods × 1 scenario × 10 seeds = 60`.

**Scenario:** `Useful Backdoored Source — 5%` from Section 15.1.

**Methods:**

1. `Full FedSIRA`;
2. `Client Review with Direct Source Admission`;
3. `Client Review then One Independent Retrain`;
4. `One Independent Retrain`;
5. `Source-Update Sanitization Reference`;
6. `Recovery after Source Admission`.

**Primary metrics:** post-production ASR, target F1, supported macro-F1 harm, benign false-alarm-rate increase.
**Secondary:** malicious/legitimate admission, per-class recall.
**Statistics:** source-exclusion claim family.
**Decision:** apply Section 18 central source-exclusion survival rule.
**Failure:** if source exclusion does not meet the exact ASR/materiality/non-inferiority rule, mark `Direct Source Exclusion` and `Malicious Source Salvage` `Not Supported`. Later experiments may continue only as characterization/negative evidence.

## 30.7 `External Verification Necessity`

**Class:** `Exploratory` with preregistered collapse decision.
**Runs:** `2 methods × 4 conditions × 10 seeds = 80`.

**Methods:** `Full FedSIRA`; `Multiple Retrains with Direct Krum`.
**Conditions:**

* `Legitimate Transferable Capability`;
* `Honest Site-Specific Feature Shift — 1.0`;
* `One Byzantine Source-Copy Reproducer`;
* `One Verifier-Aware Backdoor Reproducer`.

The first three condition names have the exact semantics specified in Section 30.5. `One Verifier-Aware Backdoor Reproducer` uses a clean `Legitimate Target Capability` source plus the first attack-feasible non-source domain in `Reproducer Order` executing the Section 15.2 verifier-aware attack; all other participants are honest.

The two methods receive the same precommitted reproduction opportunities. FedSIRA filters by external verification; direct Krum takes the first five non-abstaining commitments.

**Primary metrics:** malicious admission, legitimate admission, target F1, supported harm, worst-domain F1.
**Decision:** Section 18 external-verification survival rule.

## 30.8 Resolved core after collapse

After Sections 30.4–30.7 are complete:

1. compute every specified collapse statistic and constraint;
2. apply Section 18.7 survival rules without manual override;
3. materialize the deterministic `Resolved FedSIRA Core` artifact using the complete Section 18.7 mapping;
4. record its opening mode, reproduction count, row-verification mode, production-update rule, final-gate rule, source-exclusion status, and identities of the four decision artifacts;
5. materialize/validate the downstream experiment plan against that resolved core;
6. do not add, retune, or substitute a mechanism in response to collapse outcomes.

If the direct source-exclusion central gate fails, `Direct Source Exclusion` and `Malicious Source Salvage` are `Not Supported` under Section 35. The resolved FedSIRA path remains source-excluded for characterization; failure of the contribution gate does not authorize deployment of the source artifact.

## 30.9 `Primary Confirmatory Evaluation`

**Class:** `Confirmatory`
**Runs:** `14 methods × 3 scenarios × 10 seeds = 420`.

**Methods:**

```text
Resolved FedSIRA Core
FedAvg Reference
Client Review with Direct Source Admission
Client Review then One Independent Retrain
One Independent Retrain
Multiple Retrains with Direct Krum
Multiple-Model Certified Ensemble
Independent Local Reference with Source Admission
Update Reconstruction Filter
Density-Cluster Trimmed Mean
Secure Continual Assessment Reference
Recovery after Source Admission
Source-Update Sanitization Reference
Krum Robust Aggregation Reference
```

**Scenarios:**

1. `Legitimate Unsupported Capability`;
2. `Useful Backdoored Source — 5%`;
3. `One Byzantine Post-Reference Participant`.

For `One Byzantine Post-Reference Participant`, every seed contains the legitimate target capability and one declared Byzantine authority participant. The attack mapping is fixed by mechanism family:

* source-admission/sanitization/recovery methods: the selected source uses `Useful Backdoored Source — 5%`; that source artifact/update is the compromised authority object;
* reproduction-based methods: the selected source uses `Useful Backdoored Source — 5%`, and the first attack-feasible non-source compromised reproducer submits `Source Copy`;
* ordinary FL/filtering/clustering/robust-aggregation methods: the first attack-feasible post-reference client chosen by `Byzantine Selection` executes `Model-Replacement Backdoor` under the round-level semantics in Section 15.2.

Thus the scenario is distinct from `Useful Backdoored Source — 5%`: source-excluded reproduction methods additionally face a compromised post-reference reproducer, while ordinary FL methods face a compromised client update. Attack feasibility is determined before model outcomes.

**Controlled variables:** same data roles, source/attack seed, base model, anchor, report populations, training cap, and metric code.
**Primary metrics:** target F1, supported macro-F1 harm, benign false-alarm-rate increase, and legitimate admission wherever the legitimate capability is present; malicious admission wherever the scenario supplies a compromised authority fixture; ASR in `Useful Backdoored Source — 5%` and any method/scenario pair whose specified attack uses the N-BaIoT trigger. Structurally inapplicable metrics are `NA`, not zero.
**Secondary:** Macro-F1, weighted F1, AUROC/AUPRC, worst-domain/P10 F1, abstention, runtime/communication descriptive metrics.
**Statistics:** exact Section 18 plan; no new tests.
**Interpretation:** results support only claims that pass both statistical and materiality conditions.

## 30.10 `Mechanism Ablation`

**Class:** `Ablation`  
**Runs:** `18 variants × 10 seeds = 180`.

Each variant is one semantic experiment cell per seed. Every non-`Full FedSIRA` cell consumes a matched `Full FedSIRA` reference artifact with the **same** scenario, master seed, source, data roles, attack/heterogeneity transform, and all non-ablated settings. If an identical full-reference artifact already exists in another experiment it is reused; otherwise it is materialized as a shared prerequisite scientific artifact and does **not** create another Section 30 experiment cell. This preserves the 180-cell experiment count while making every paired comparison well-defined.

| Variant | Exact implementation | Scenario | Claim-bearing ablation metric |
| --- | --- | --- | --- |
| `Full FedSIRA` | complete Sections 7.1–7.7 multi-reproduction path, independent of which optional components were removed from the downstream resolved core | `Useful Backdoored Source — 5%` | reference ASR |
| `No Proposal Screen` | candidate-free opening; downstream complete path | `Mixed Legitimate/Irrelevant Proposal Episode` | reproduction attempts |
| `Raw Target-F1 Screen Only` | screen positive when target-F1 gain `>=0.20` and supported constraints pass; no loss differential/matching | `Generic Hard Supported Examples` | false launch rate |
| `No Matched Control` | use `ΔM>=0.05` nats/example plus target/support conditions; omit `ΔC` | `Generic Hard Supported Examples` | false launch rate |
| `Source Release after Peer Review` | deploy source artifact after 2-of-3 review | `Useful Backdoored Source — 5%` | ASR |
| `Source Release after Full External Check` | source artifact itself receives one ordinary 3-member external verifier panel plus final gate, then source artifact is deployed; no independent rows are fabricated | `Useful Backdoored Source — 5%` | ASR |
| `One Independent Reproduction` | first clean reproduction + one fresh verifier + final gate | `Honest Site-Specific Feature Shift — 1.0` | worst-domain target F1 |
| `Multiple Reproductions without Cross-Verification` | first five adequate committed rows → Krum → final gate | `One Malicious Reproducer` | MAR |
| `Same-Context Verification Only` | choose 3 adequate eligible verifiers with smallest anchor-train standardized feature-mean distance to reproducer | `Natural` | legitimate admission |
| `No Origin Exclusion` | source may occupy first reproduction slot using its source update and may verify other rows; source still cannot self-verify | `Useful Backdoored Source — 5%` | ASR |
| `Parameter-Similarity Certification` | Section 16.5 cosine-similarity certification; no functional verifier Capability Claim Contract | `Feature Shift ±1.0` | legitimate admission |
| `Candidate-Free Reproduction` | candidate-free opening; otherwise complete path | `Legitimate Target Capability` | post-evidence overhead |
| `Direct Krum of Retrains` | same reproduction opportunities, no external row verification | `One Verifier-Aware Backdoor Reproducer` | MAR |
| `Generic Three-Row Threshold` | Krum `n=3,f=1` branch must be `Invalid`; separately execute the three-row coordinate-median diagnostic | `One Malicious Reproducer` | coordinate-median diagnostic MAR |
| `Random Committee Profile` | use Section 13.7 random verifier profile with one compromised false-positive verifier | `One Compromised Verifier` | MAR |
| `No Final Synthesis Gate` | after Krum, admit immediately without final fresh evidence | `Feature Shift ±1.0` | worst-domain target F1 |
| `Byzantine Reproducer Copies Source` | force one reproduction row to exact source update | `Useful Backdoored Source — 5%` | ASR |
| `Capability-Contract Granularity` | execute broad, A-scoped, and B-scoped contracts on the root-cause fixture | `Under-Specification Fixture` | broad false-same-capability certification rate |

Scenario completion rules:

* `Mixed Legitimate/Irrelevant Proposal Episode` contains exactly two claim instances under the same master seed: one Section 15.10 `Legitimate Target Capability` instance and one `Irrelevant Source Improvement` instance. Reproduction attempts/post-evidence overhead are the arithmetic mean of the two instance values; LAR is defined only on the legitimate instance and false launch only on the irrelevant instance.
* `One Malicious Reproducer` means one `Model-Replacement Backdoor` reproducer on an otherwise clean `Legitimate Target Capability` background.
* `Natural` means `Legitimate Target Capability`, all-honest participants, and the `Natural` heterogeneity regime.
* `Feature Shift ±1.0` and `Honest Site-Specific Feature Shift — 1.0` both mean the all-honest legitimate target capability with the Section 15.9 `Feature Shift ±1.0` transformation.
* `One Compromised Verifier` means one `False Positive` verifier plus exactly one `Model-Replacement Backdoor` reproduction row; all other reproducers/verifiers are honest.
* `Under-Specification Fixture` uses the Section 15.10 `Balanced 50/50` mixture; the separate Section 30.16 experiment evaluates both mixtures.

All variants also report target F1 and supported harm. Statistics use Family 8 in Section 18.9. The `Full FedSIRA` row is the explicit reference cell; it has no self-comparison p-value. An ablation may refute a component interpretation but cannot alter the already resolved downstream core.

## 30.11 `Compromised-Reproducer Robustness`

**Class:** `Robustness`
**Runs:** `4 methods × 7 conditions × 10 seeds = 280`.

**Methods:** `Resolved FedSIRA Core`, `One Independent Retrain`, `Multiple Retrains with Direct Krum`, `Krum Robust Aggregation Reference`.

**Conditions:**

```text
CLEAN
One Source Copy
One Model-Replacement Backdoor
One Verifier-Aware Backdoor
Two Source Copies
Two Model-Replacement Backdoors
Two Verifier-Aware Backdoors
```

Fixture semantics are exact:

* `CLEAN`: clean `Legitimate Target Capability` source and no compromised reproducer; ASR is `NA`;
* `One/Two Source Copy`: the source is `Useful Backdoored Source — 5%`; the first one/two attack-feasible non-source domains in `Reproducer Order` are compromised and submit `Source Copy`;
* `One/Two Model-Replacement Backdoor`: source is clean `Legitimate Target Capability`; first one/two attack-feasible non-source domains use Section 15.2 model replacement;
* `One/Two Verifier-Aware Backdoor`: source is clean `Legitimate Target Capability`; first one/two attack-feasible non-source domains use Section 15.2 verifier-aware training.

The declared compromised count describes the contaminated candidate pool. A method that consumes fewer reproduction rows, especially `One Independent Retrain`, may encounter at most the number of compromised rows it actually selects; the result artifact records both declared pool compromise count and realized compromised rows consumed. `Krum Robust Aggregation Reference` maps these same compromised identities to its ordinary-FL participant set; for `Source Copy` it submits the exact source model as the malicious local model each round as specified in Section 15.2.

**Primary metrics:** malicious admission, ASR where defined, target F1, supported harm.
**Secondary:** external reproduction verification yield, Krum-selected row identity, abstention, worst-domain F1.
**Interpretation:** one compromised row is within the declared empirical FedSIRA profile; two is above `protocol.synthesis.maximum_byzantine_reproduction_rows`. The original Krum theorem is not claimed to hold automatically under these heterogeneous reproduction updates; security wording must remain conditional on the tested profile and Section 8 assumptions.

## 30.12 `Compromised-Verifier Robustness`

**Class:** `Robustness`
**Runs:** `2 verifier profiles × 5 conditions × 10 seeds = 100`.

**Profiles:** `Deterministic Bound`, `Random-Committee Diagnostic`.

**Conditions:**

```text
All Honest
One False Positive
Two False Positives
One False Negative
Two False Negatives
```

Verifier fixtures are:

* `All Honest`: all reproduction rows and verifiers honest on `Legitimate Target Capability`;
* `One/Two False Positives`: exactly one `Model-Replacement Backdoor` reproduction row is present, and the condition's one/two compromised verifiers vote `Positive` on that malicious row and otherwise follow the declared Byzantine behavior;
* `One/Two False Negatives`: all reproduction rows are honest and the condition's one/two compromised verifiers vote `Negative` when called on an honest row.

For `Deterministic Bound`, panels are constructed with Section 13.6's exact count enforcement. For `Random-Committee Diagnostic`, the condition's actual compromise count `b=0,1,2` is used in Section 13.7; the exact at-least-two-compromised probability is 0, 0, and `1/7` respectively.

**Primary metrics:** malicious admission for false-positive cases; legitimate admission/dormancy for false-negative cases.  
**Secondary:** certified-row yield, verifier abstention, exact random-panel contamination frequency.  
**Interpretation:** deterministic profile supports security wording only at 0/1 compromised verifier; random profile is probability-calibration evidence only.

## 30.13 `Byzantine-Bound Violation`

**Class:** `Failure Boundary`
**Runs:** `2 methods × 4 bound conditions × 10 seeds = 80`.

**Methods:** `Resolved FedSIRA Core`, `Multiple Retrains with Direct Krum`.

**Conditions:**

```text
One Byzantine Reproducer — Within Bound
Two Byzantine Reproducers — Above Bound
One Byzantine Verifier — Within Bound
Two Byzantine Verifiers — Above Bound
```

`One/Two Byzantine Reproducer` uses one/two `Model-Replacement Backdoor` reproduction rows with all verifier panels honest. `One/Two Byzantine Verifier` uses exactly one `Model-Replacement Backdoor` reproduction row plus one/two `False Positive` compromised verifiers; all other rows/verifiers are honest. These choices isolate the count-bound dimension while keeping the malicious payload fixed.

**Purpose:** demonstrate claimed-region versus above-bound behavior directly.
**Success meaning:** not “performance always good”; the expected result is deterioration or loss of guarantee above bound.

## 30.14 `Evidence Scarcity and Dormancy`

**Class:** `Failure Boundary`
**Runs:** `4 schedules × 10 seeds = 40`.

**Schedules:** Section 15.8.
**Method:** resolved FedSIRA only.
**Metrics:** state by logical cycle, time-to-first-reproduction, `T_evidence`, time-to-certificate, terminal protocol outcome.
**Required behavior:** permanent singleton never admits; a five-row resolved path cannot form its reproduction committee before `T_reproduction_evidence`, and no method may admit before its method-specific `T_evidence`, which includes the six-domain final-gate requirement. `Gradual to Quorum` therefore may construct a five-row committee at cycle 6 but may not admit before cycle 8.

## 30.15 `Shared Epistemic-Failure Boundary`

**Class:** `Failure Boundary`
**Runs:** `3 failure types × 3 strengths × 10 seeds = 90`.

**Failure types/strengths:**

* shared label/threat-intelligence error: 5%, 10%, 20%;
* shared spurious feature: 25%, 50%, 100%;
* attacker-induced common context: 25%, 50%, 100%.

**Method:** resolved FedSIRA.
**Primary metrics:** certificate/admission rate under corrupted operational evidence; clean-oracle target F1, supported harm, and benign FAR; clean-oracle deltas use the exact matched uncorrupted reference in Section 17.10.
**Interpretation:** a case where the method certifies a reproducible but wrong function is a **required limitation result**, not an implementation failure.

## 30.16 `Capability Under-Specification Boundary`

**Class:** `Failure Boundary`
**Runs:** `3 Capability Claim Contract granularities × 2 root-cause mixtures × 10 seeds = 60`.

**Capability Claim Contract granularities:** broad target, A-scoped, B-scoped.
**Mixtures:** `Balanced 50/50`, `A-Dominant 80/20`.
**Metrics:** cross-domain verifier agreement, certified-row yield, final target F1 separately on root causes A/B, and `false_same_capability_certification_rate` for `Broad Target Only`; scoped-contract rows report that metric as `NA` by Section 15.10. Family 9 tests the broad seed-level rate against zero for each mixture.
**Interpretation:** broad-claim failure limits what “same capability” means; no parameter-similarity mechanism may be added after observing it.

## 30.17 `Heterogeneous-Reproduction Boundary`

**Class:** `Robustness`
**Runs:** `4 methods × 4 regimes × 10 seeds = 160`.

**Methods:** `Resolved FedSIRA Core`, `One Independent Retrain`, `Multiple Retrains with Direct Krum`, `Krum Robust Aggregation Reference`.
**Regimes:** `Natural`, `Quantity Skew`, `Feature Shift ±0.5`, `Feature Shift ±1.0`.

**Primary metrics:** target F1, worst-domain F1, legitimate admission, dormancy.
**Secondary:** update pairwise distance, Krum-selected row, certified yield.
**Interpretation:** identify the tested heterogeneity range in which synthesis/reproduction remains viable.

## 30.18 `Admission-Delay Decomposition`

**Class:** `Diagnostic`
**Runs:** `3 methods × 4 schedules × 10 seeds = 120`.

**Methods:** `Resolved FedSIRA Core`, `One Independent Retrain`, `Multiple Retrains with Direct Krum`.
**Schedules:** all four Section 15.8 schedules.
**Metrics:** `T_evidence` logical cycles, wall-clock post-evidence components, total attempts, terminal state.
**Interpretation:** never report `T_evidence` as FedSIRA compute overhead.

## 30.19 `Efficiency Measurement`

**Class:** `Diagnostic`
**Runs:** `4 methods × 3 master seeds × 5 timing repetitions = 60`.

**Methods:** `Resolved FedSIRA Core`, `One Independent Retrain`, `Multiple Retrains with Direct Krum`, `Client Review with Direct Source Admission`.
**Seeds:** 1103, 1217, 1321 only.
**Timing repetitions:** 5 per method-seed cell on the same machine. Repetitions are not inferential seed units.

Each timing repetition executes in a dedicated single-process timing worker and writes repetition-owned diagnostic payloads beneath `outputs/experiments/Efficiency Measurement/diagnostics/runtime/repetitions/<method>/<master-seed>/<repetition-index>/`; these payloads are never reusable scientific parents. `persistent storage bytes` for a repetition is the recursive sum of regular-file sizes in that repetition directory at completion, excluding symlinks/references to pre-existing shared inputs.

Before each timed repetition:

* load already-preprocessed data;
* synchronize CUDA;
* run one unreported warm-up forward pass;
* clear CUDA peak-memory counters;
* do not clear OS filesystem cache;
* ensure no concurrent scientific GPU job.

Report median and IQR over the five timing repetitions for each seed, then descriptive median across the three seed medians. Do not run significance tests on timing repetitions.

**Metrics:** wall-clock, GPU time, peak GPU memory, host RSS, communication bytes, transmissions, storage.

## 30.20 `Secondary-Dataset Generalization`

**Class:** `Generalization`
**Runs:** `5 methods × 2 scenarios × 10 seeds = 100`.

**Methods:** `Resolved FedSIRA Core`, `One Independent Retrain`, `Multiple Retrains with Direct Krum`, `Client Review with Direct Source Admission`, `FedAvg Reference`.

**Scenarios:**

* `Legitimate Backdoor-Malware Capability`;
* `One Byzantine Source-Copy Reproducer`.

The second scenario is an **authority/provenance attack without an invented secondary trigger**. The selected source is declared Byzantine but trains the ordinary secondary post-reference objective on `BACKDOOR_MALWARE` plus supported replay. The first attack-feasible non-source reproducer is Byzantine and submits the exact source update (`Source Copy`). For `Client Review with Direct Source Admission`, the compromised source artifact itself is the authority object. For `FedAvg Reference`, the designated compromised post-reference client submits the exact source **model** as its local model in each round, i.e. its submitted round delta is `source_model - current_global`. No N-BaIoT-specific four-feature trigger or ASR is defined on CICIoT2023. Malicious admission is therefore the Section 17.3 compromised-authority provenance outcome, while target/support metrics measure whether the copied functionality remains useful.

**Primary metrics:** secondary target F1/gain, supported macro-F1 harm, benign false-alarm-rate increase, malicious/legitimate admission.
**Statistics:** same 10-seed paired exact tests and Holm family; same material thresholds.
**Claim limit:** supports cross-dataset mechanism direction only; synthetic pseudo-domains cannot validate real administrative independence.

# 31. Exact experiment-count contract

Before execution, read-only `fedsira plan` must resolve and display this count table exactly for the no-invalid-baseline path. These are planned semantic scientific cells, not opaque run IDs.

| Program block | Planned cells |
| --- | ---: |
| Data/domain/evidence validation | 1 |
| Protocol invariant validation | 1 |
| Baseline implementation validation | 17 |
| Proposal-assisted opening necessity | 80 |
| Single-reproduction necessity | 60 |
| Source-artifact exclusion necessity | 60 |
| External reproduction verification necessity | 80 |
| **Pre-core subtotal** | **299** |
| Primary confirmatory evaluation | 420 |
| Mechanism ablation | 180 |
| Compromised reproducer robustness | 280 |
| Compromised verifier robustness | 100 |
| Byzantine-bound violation | 80 |
| Evidence scarcity/dormancy | 40 |
| Shared epistemic failure boundary | 90 |
| Capability under-specification boundary | 60 |
| Heterogeneous reproduction boundary | 160 |
| Admission-delay decomposition | 120 |
| Efficiency measurement | 60 |
| Secondary-dataset generalization | 100 |
| **Post-core subtotal** | **1,690** |
| **Complete scientific plan** | **1,989** |

Matched `Full FedSIRA` prerequisite artifacts required by Section 30.10 are computational dependencies, not additional Section 30 semantic cells; when scientifically identical to another experiment's artifact they are reused. Timing repetitions are already included in the declared 60 `Efficiency Measurement` cells exactly as Section 30.19 defines them.

If a baseline is `Invalid` during validation, its downstream planned cells remain part of the nominal plan as invalid rather than disappearing after outcomes are visible. `plan` must distinguish nominal, executable-valid, completed, failed/invalid, and scientifically evidence-insufficient counts.

# 32. Scientific authority and no-post-hoc-selection boundaries

The roadmap, its configuration values, deterministic derivation rules, experiment matrices, collapse actions, statistical comparisons, reporting products, and claim rules are the study's scientific authority. Execution does not create a second mechanism-selection or parameter-selection stage.

The following boundaries are mandatory:

1. Dataset identities, observed schemas, file hashes, class availability, and role/evidence counts are established by `preprocess` from the actual raw bytes under Sections 9–11. Documentation expectations may be contradicted by the bytes; the discrepancy is recorded and the explicit validation/adaptation rule is followed rather than silently changing the scientific target.
2. Baseline algorithms, information access, calibrated thresholds, and budgets are those in Section 16. A baseline that is incompatible or invalid is reported as such and is not replaced after seeing results.
3. The four collapse experiments use only the seeds, scenarios, material thresholds, tests, Holm families, and actions already specified. Their outputs mechanically produce the Section 18.7 `Resolved FedSIRA Core`; there is no manual mechanism choice.
4. Post-core experiments use that resolved core and the Section 30 matrices exactly. A collapse result can narrow/remove a mechanism claim but cannot authorize a new method, threshold, dataset, baseline, seed, or attack choice.
5. A valid null or unfavorable result remains part of the result set. Seeds are not replaced; planned cells are not removed because of their outcomes; report-test/final-gate evidence is never used to retune training or claim thresholds.
6. A genuine implementation defect is corrected under Sections 25–27: only the affected producer artifacts and descendants are invalidated and rerun. Compatible upstream scientific artifacts remain reusable. Correcting implementation does not authorize a scientific change.

These are ordinary specification and no-post-hoc-selection rules, not a separate execution phase.

# 33. Required manuscript tables

**Authoritative reporting contract:** the mandatory table names, semantics, columns, ordering, and scientific content are fixed here rather than duplicated as YAML strings.

Every final table is generated by `fedsira report` from verified machine-readable result/statistical data; scientific values are never manually transcribed. Experiment-owned tables are materialized under `results/experiments/<descriptive-experiment-name>/tables/main/` or `tables/supplementary/`; cross-experiment tables are materialized under `results/project_summary/tables/main/` or `tables/supplementary/`. The table contents below are mandatory; exact filenames and rendering format are implementation choices.

## 33.1 Protocol tables

### `Dataset and Domain Protocol`

**Rows:** `N-BaIoT`, `CICIoT2023`.
**Columns:** dataset, source identifier, file-manifest hash, raw rows, retained feature count, canonical class count, target class, domain-proxy count, proxy semantics, target holders, evidence-minimum rule, split/replay semantics, primary/secondary role.
**Ordering:** primary then secondary.

### `Primary Domain Statistics`

**Rows:** nine primary domain proxies.
**Columns:** domain ID, device type, target availability, each role's target count, supported role counts, reproduction eligibility, verifier eligibility, final-gate eligibility, report-test rows.
**Ordering:** domain order in Section 9.2.

### `Model and Training Protocol`

**Rows:** anchor, source candidate, honest reproduction.
**Columns:** architecture, initialization, loss, optimizer, learning rate, batch size, epochs/rounds, regularizers, data roles, checkpoint rule, gradient clip.

### `Security and Capability-Contract Protocol`

**Rows:** deterministic verifier profile, random diagnostic verifier profile, Krum synthesis, final gate.
**Columns:** profile, $f_R$, $f_V$, panel size, positive threshold, certified-row requirement, Krum `n`, Krum nearest-neighbor count, target threshold, supported-F1 margin, benign-FPR margin, evidence minimum, scope.

### `Baseline Protocol`

**Rows:** all 17 Section 16 baselines.
**Columns:** method, mechanism family, source artifact deployed yes/no, independent retraining count, external verification yes/no, aggregation/synthesis, training budget, tuning data, production object, implementation status.

### `Experiment Plan`

**Rows:** one descriptive experiment.
**Columns:** experiment name, class, methods, scenarios/variants, seeds, nominal run count, primary metrics, claim family, prerequisite, downstream role.
**Ordering:** Section 30 order.

### `Metric and Statistics Protocol`

**Rows:** every claim-bearing metric/comparison family.
**Columns:** metric, mathematical orientation, aggregation unit, undefined rule, primary/secondary role, effect threshold, test, sidedness, alpha, multiplicity family, CI method.

## 33.2 Result tables

### `Primary Results`

**Rows:** method × primary scenario.
**Columns:** method, scenario, target F1 mean, target F1 95% CI, supported macro-F1 harm, benign false-alarm-rate increase, ASR where defined, malicious admission, legitimate admission, worst-domain target F1, complete seed count.
**Aggregation:** equal seed weight after seed-level domain aggregation.
**Uncertainty:** 95% bootstrap CI across paired seed units for claim-bearing differences; raw method summaries show mean ± sample SD.
**Ordering:** resolved FedSIRA first, then mechanism baselines in Section 30.9 order.

### `Source-Exclusion Results`

**Rows:** six methods from `Source-Artifact Exclusion Necessity`.
**Columns:** post-production ASR, ASR difference vs FedSIRA, adjusted p, 95% CI, target F1, target non-inferiority pass, supported-F1 harm, benign-FPR increase, source-exclusion gate outcome.
**Ordering:** FedSIRA then increasing ASR.

### `Collapse Decisions`

**Rows:** proposal assistance, plurality, direct source exclusion, external reproduction verification.
**Columns:** mechanism, comparator, primary material effect, adjusted p, liveness/safety constraint, survival rule, observed outcome, core action.
**No manual narrative override field is permitted.**

### `Ablation Results`

**Rows:** 18 ablation variants.
**Columns:** variant, targeted mechanism, scenario, primary metric, difference from full reference, adjusted p, materiality pass, target F1, supported harm, ASR/malicious admission when relevant, interpretation.
**Ordering:** Section 30.10 order.

### `Byzantine Robustness`

**Rows:** method × compromised-reproducer condition and verifier profile × verifier condition.
**Columns:** bound status (`Within Bound`/`Above Bound`), compromised count, strategy, malicious admission, legitimate admission, ASR, target F1, certified yield, dormant rate, complete seeds.
**Ordering:** within-bound before above-bound, count ascending.

### `Failure Boundaries`

**Rows:** scarcity schedule, epistemic failure type/strength, under-specification condition, heterogeneity regime.
**Columns:** boundary family, condition, strength, admission/dormancy, target F1, worst-domain F1, claim implication; `clean_oracle_error` is populated only for the three `Shared Epistemic-Failure Boundary` failure types and is `NA` with reason `Not an Epistemic-Oracle Experiment` for the other boundary families.
**Purpose:** prevent favorable main results from hiding known boundaries.

### `Delay and Efficiency`

**Rows:** method × schedule for delay, method for efficiency.
**Columns:** `T_evidence`, assignment, reproduction, verification, synthesis, post-evidence overhead, wall-clock runtime, GPU time, peak GPU memory, host RSS, communication bytes, transmissions, storage.
**Timing display:** median [IQR] over 5 repetitions for timing cells.

### `Generalization Results`

**Rows:** five methods × two secondary scenarios.
**Columns:** target F1/gain, supported harm, benign false-alarm-rate increase, malicious/legitimate admission, paired effect vs FedSIRA, adjusted p, materiality pass.
**Claim label:** `Data/Attack Generalization Only` printed in table footnote metadata.

### `Statistical Summary`

**Rows:** one predeclared comparison.
**Columns:** claim, comparison, metric, direction, margin, n pairs, mean difference, median difference, paired $d_z$, raw p, Holm p, 95% CI, materiality threshold, statistical pass, materiality pass, final comparison state.

### `Claim Support`

**Rows:** one manuscript claim.
**Columns:** claim, exact scoped claim, evidence experiments, primary metric, required comparison, claim state, supporting table, supporting figure, valid scope, forbidden extrapolation.

## 33.3 Table rounding/significance display

Use Section 18.10 formatting. Statistical significance is displayed by exact adjusted p-value; no star-only encoding. Significance stars are disabled; numeric raw and adjusted p-values are the only significance encoding.

---

# 34. Required manuscript figures

**Authoritative reporting contract:** the mandatory figure names, semantics, and required encodings are fixed here rather than duplicated as YAML strings.

Every required figure is generated from verified machine-readable result/statistical data; scientific values are never manually transcribed. Experiment-owned figures are materialized under `results/experiments/<descriptive-experiment-name>/figures/main/` or `figures/supplementary/`; cross-experiment figures are materialized under `results/project_summary/figures/main/` or `figures/supplementary/`. The contents below are mandatory; exact filenames are implementation choices.

## 34.1 `FedSIRA Protocol Schematic`

**Question:** what changes authority from source model to independent evidence?
**Type:** deterministic schematic, not data plot.
**Content:** source commitment with zero direct weight → fixed Capability Claim Contract → non-source reproduction → post-commitment verifier panels → five-row external reproduction verification → Krum → final fresh gate → admission/dormancy/rejection.
**Manuscript role:** method overview.

## 34.2 `Primary Security–Utility Tradeoff`

**Question:** does resolved FedSIRA improve source/security outcomes without destroying target capability?
**Type:** paired-effect forest plot.
**Y-axis:** method comparison.
**X-axis:** primary paired effect, one panel/file per metric to avoid mixed scales.
**Metrics:** target F1 difference, ASR difference, malicious-admission difference.
**Uncertainty:** 95% bootstrap CI.
**Sorting:** method order from `Primary Results`.

## 34.3 `Useful Backdoored Source`

**Question:** can useful capability be retained while hidden source backdoor is excluded?
**Type:** scatter plot.
**X-axis:** post-production ASR.
**Y-axis:** target F1.
**Point:** method seed mean; error bars 95% CI of method summary.
**Annotations:** Capability Claim Contract target-F1 threshold 0.80 and ASR direction.

## 34.4 `Collapse Decision Effects`

**Question:** which optional mechanisms survived?
**Type:** four-row forest plot.
**Rows:** proposal assistance, plurality, source exclusion, external reproduction verification.
**X-axis:** each mechanism's predeclared primary material effect normalized by its material threshold; 1.0 means exactly material.
**Annotation:** adjusted p and `Survives`/`Removed`/`Central Not Supported`.

## 34.5 `Compromised-Reproducer Boundary`

**Type:** line plot.
**X-axis:** compromised reproducer count 0/1/2.
**Y-axis:** malicious admission rate; separate figure file for ASR if needed.
**Groups:** attack strategy and method.
**Uncertainty:** seed bootstrap 95% CI.
**Vertical annotation:** declared bound at 1.

## 34.6 `Compromised-Verifier Boundary`

**X-axis:** compromised verifier count 0/1/2.
**Y-axis:** malicious admission for false-positive mode and legitimate admission for false-negative mode, saved as separate final figures.
**Groups:** deterministic vs random diagnostic profile.
**Annotation:** deterministic bound at 1 and random-profile exact contamination risk.

## 34.7 `Evidence-Arrival State Trajectory`

**Type:** step plot.
**X-axis:** logical evidence cycle.
**Y-axis:** fraction of seed instances in `Dormant`, `Verification Pending`, `Admitted`, `Expired`; one panel per schedule.
**Purpose:** show safe dormancy and evidence-arrival lower-bound behavior.

## 34.8 `Shared Epistemic Failure`

**Type:** line plot.
**X-axis:** corruption/confound strength.
**Y-axis:** clean-oracle error/admission rate.
**Groups:** shared failure type.
**Purpose:** visibly bound reproducibility versus truth.

## 34.9 `Capability-Granularity Boundary`

**Type:** grouped bars/points.
**X-axis:** Capability Claim Contract granularity.
**Y-axis:** false same-capability certification rate and per-root-cause target F1 in separate figures.
**Groups:** root-cause mixture.

## 34.10 `Heterogeneity Synthesis Boundary`

**Type:** line/point plot.
**X-axis:** ordered heterogeneity regime.
**Y-axis:** legitimate admission and worst-domain target F1 in separate figures.
**Groups:** FedSIRA, one retrain, direct Krum, Krum reference.

## 34.11 `Admission-Delay Decomposition`

**Type:** stacked bars.
**X-axis:** method × evidence schedule.
**Stack:** assignment, reproduce, verify, synthesize wall-clock components.
**Separate annotation:** `T_evidence` logical cycles, not stacked as seconds.
**Purpose:** separate information arrival from protocol overhead.

## 34.12 `Efficiency Profile`

Produce separate plots for:

* wall-clock post-evidence runtime;
* communication bytes;
* peak GPU memory.

**X-axis:** method.
**Y-axis:** metric.
**Uncertainty:** median [IQR] over timing repetitions; no inferential p-value.

## 34.13 `Secondary Generalization`

**Type:** paired effect forest plot.
**X-axis:** target-F1 effect vs each predeclared simple comparator.
**Groups:** secondary scenarios.
**Annotation:** synthetic-domain limitation.

---

# 35. Claim-support registry

**Configuration authority:** only additional quantitative claim-support boundaries that are not already shared statistical/materiality fields are in `claim_support_thresholds`. Claim-state vocabulary, evidence logic, scope, failure semantics, and forbidden extrapolations are fixed by this section rather than stored as YAML strings.

The claim inventory in this section is the authoritative one-to-one implementation of the safe manuscript claims in Section 1.4. `analysis/claims.py` emits exactly these claim IDs and no additional scientific claim IDs.

Final claim states are exactly:

```text
Supported
Partially Supported
Conditional
Mechanism Only
Null Result
Not Supported
Not Tested
```

## 35.1 State semantics

* `Supported`: all mandatory evidence, material thresholds, safety/non-inferiority constraints, and statistical rules pass within the exact declared scope.
* `Partially Supported`: only a strict prespecified subset of scope/metrics passes; manuscript wording must be narrowed to that subset.
* `Conditional`: evidence supports the claim only inside an explicitly tested operating boundary.
* `Mechanism Only`: a mechanism effect is demonstrated, but the main outcome claim is not supported.
* `Null Result`: the required experiment completed correctly and the predeclared effect was not materially/statistically different.
* `Not Supported`: required valid evidence contradicts or fails the claim-support rule.
* `Not Tested`: required evidence did not execute validly or a prerequisite made the claim impossible to test.

`Inconclusive Technical` is a comparison state, not a manuscript claim state; affected claims become `Not Tested` unless other prespecified complete evidence independently satisfies the full claim contract.

## 35.2 Exact claim rules

### `Unsupported Capability Problem`

**Evidence:** primary preprocessing/data validation plus the primary anchor/report manifests.
**Minimum support:** `GAFGYT_COMBO` is absent from every `Anchor Train` and `Anchor Validation` sample, present in the validated post-reference target roles required by the study, and the source-Byzantine scenarios execute under the Section 4 threat model.
**Failure:** target leakage into anchor roles, missing target evidence that blocks the primary study, or an implementation that does not instantiate the declared source-Byzantine setting.
**Scope:** the constructed unsupported-capability problem in the tested IoT IDS datasets; no universal claim about all federated tasks.

### `Pre-Evidence Information Limit`

**Evidence:** formal proof plus executable transcript fixture demonstrating no trusted positive post-reference support before independent evidence arrives.
**Minimum support:** proof assumptions explicitly map to the implementation and any trusted side information is declared. No empirical superiority p-value is required.
**Failure:** implementation uses trusted side information that changes the transcript law without narrowing the theorem premise.
**Scope:** only transcript models satisfying the equal-distribution premise.
**Forbidden extrapolation:** “no federated method can ever detect an unseen attack.”

### `Authority Transition`

**Evidence:** protocol invariant validation, `Source-Artifact Exclusion Necessity`, and `Primary Confirmatory Evaluation`.
**Minimum support:** zero source-artifact production-input provenance violations across completed source-excluded FedSIRA cells, plus at least one `Legitimate Unsupported Capability` master-seed instance with a valid `Admitted` production model created through the resolved non-source authority path.
**Failure:** the source artifact becomes an honest-path production input, or no valid legitimate admission is observed in at least 9 complete primary seed instances.
**Scope:** FedSIRA's tested authority path.

### `Direct Source Exclusion`

**Evidence:** Section 28 source-firewall tests plus every completed source-excluded FedSIRA production manifest.
**Minimum support:** zero explicit source-artifact or source-derived-checkpoint identities appear in honest reproduction training inputs or source-excluded synthesis/production inputs.
**Failure:** any such provenance violation.
**State:** this structural claim may be `Supported` even if the central performance comparison is a null result.

### `Conditional Non-Interference`

**Evidence:** Section 8.3 theorem plus the deterministic property fixture below.
**Fixture:** construct one `Claim Open` instance with a fixed anchor, fixed Capability Claim Contract, fixed non-source prepared views, assignments, and seeds. Commit two distinct, architecture-compatible source artifacts: fixture A has a zero source delta; fixture B has the same delta except the first coordinate of the canonical Section 12 parameter vector is `+0.001`. Neither source artifact is exposed to the honest authority path.
**Minimum support:** the ordered identities and content hashes of every honest reproduction update and the resulting non-source production update are exactly identical between fixture A and fixture B. Source-commitment/provenance records are allowed to differ.
**Failure:** any honest reproduction or production-update payload differs.
**Forbidden extrapolation:** this does not imply that Byzantine reproducers cannot copy the source out of band.

### `Malicious Source Salvage`

**Evidence:** `Source-Artifact Exclusion Necessity` and the `Useful Backdoored Source — 5%` scenario in `Primary Confirmatory Evaluation`.
**Minimum support:** the exact Section 18 direct-source-exclusion survival rule passes; target-F1 non-inferiority and supported/benign constraints pass; and at least one legitimate target-capability instance reaches `Admitted` without deploying the source artifact.
**Failure:** the central source-exclusion gate fails.
**Scope:** the tested source backdoor and target capability only.

### `Proposal Assistance Value`

**Evidence:** `Proposal-Assisted Opening Necessity`.
**Minimum support:** the Section 18 proposal-survival rule passes.
**Failure:** otherwise `Null Result`; the resolved core uses candidate-free opening.
**Scope:** discovery/efficiency only; proposal assistance is never treated as a necessary security theorem.

### `Plurality Necessity`

**Evidence:** `Single-Reproduction Necessity`.
**Minimum support:** the Section 18 plurality-survival rule passes in at least one prespecified site-shift or Byzantine-reproducer condition.
**Failure:** `Not Supported`; the resolved core uses the single-reproduction path.

### `External Verification Necessity`

**Evidence:** `External Verification Necessity`.
**Minimum support:** the Section 18 external-verification survival rule passes.
**Failure:** `Not Supported`; the resolved core uses the corresponding path without external reproduction verification.

### `Mechanism Necessity`

**Evidence:** `Proposal Assistance Value`, `Plurality Necessity`, and `External Verification Necessity`.
**Decision:** `Supported` only if all three are `Supported`; `Partially Supported` when one or two are `Supported`; `Null Result` when all three validly fail their survival rule; `Not Tested` if any required necessity experiment is technically inconclusive and the remaining evidence does not determine the full state.
**Scope:** only these three preregistered component-necessity questions; direct source exclusion has its own central claim.

### `Byzantine Operating Region`

**Evidence:** `Compromised-Reproducer Robustness`, `Compromised-Verifier Robustness`, and `Byzantine-Bound Violation`.
**Minimum support:** every complete within-bound malicious reproducer/verifier seed instance for the resolved FedSIRA path has `malicious_admission=0`, with at least 9 complete seed instances per claim-bearing comparison and legitimate target/support metrics evaluable. Above-bound results are reported descriptively and do not need to fail.
**State:** `Conditional` when the within-bound rule passes.
**Scope:** deterministic `f_R=1`, `f_V=1` profile; random-committee results remain diagnostic.

### `Safe Dormancy`

**Evidence:** `Evidence Scarcity and Dormancy`.
**Minimum support:** zero `Admitted` outcomes for `Permanent Singleton` across all 10 scientific seed instances, and no method admission before its Section 15.8 method-specific `T_evidence`; gradual/immediate schedules progress once their deterministic evidence and final-gate eligibility conditions are satisfied.
**Failure:** any pre-evidence admission or persistent non-progression despite satisfied eligibility and no technical failure.

### `Reproducibility Is Not Truth`

**Evidence:** `Shared Epistemic-Failure Boundary`.
**Minimum support:** at least one predeclared shared-failure fixture produces certification/admission while at least one clean-oracle degradation metric exceeds its configured material threshold relative to the exact uncorrupted reference cell.
**If not observed:** the theoretical limitation remains valid but the empirical claim is `Not Supported`.

### `Capability-Granularity Boundary`

**Evidence:** `Capability Under-Specification Boundary`.
**Minimum support:** for at least one root-cause mixture, the mean broad-contract `false_same_capability_certification_rate` is at least `claim_support_thresholds.capability_granularity_boundary.false_same_capability_certification_rate_minimum` and its Family 9 exact paired test against zero is Holm-adjusted `p<0.05`.
**Scoped contracts:** the false-same-capability rate is structurally `NA`; their A/B target metrics and certification yields are reported as descriptive mechanism evidence.
**Otherwise:** `Null Result`.

### `Heterogeneity Boundary`

**Evidence:** `Heterogeneous-Reproduction Boundary`.
**Minimum support:** identify the highest tested regime, in the declared order `Natural < Quantity Skew < Feature Shift ±0.5 < Feature Shift ±1.0`, for which the resolved FedSIRA method's legitimate-admission change from `Natural` is no worse than `0.05` absolute and worst-domain target-F1 loss from `Natural` is no worse than `0.05` absolute, using complete paired seed data.
**State:** `Conditional`.
**Scope:** only through that highest passing tested regime.

### `Information-Arrival Delay`

**Evidence:** Section 8.7 theorem, `Evidence Scarcity and Dormancy`, and `Admission-Delay Decomposition`.
**Minimum support:** no admission occurs before the method-specific `T_evidence`; for the five-row path, synthesis also never occurs before `T_reproduction_evidence`; wall-clock post-evidence components are recorded separately.
**Forbidden extrapolation:** logical cycles are not converted into real deployment time without an externally supplied deployment cycle duration.

### `Post-Evidence Efficiency`

**Evidence:** `Efficiency Measurement`.
**Minimum support:** all prescribed repetitions complete and the descriptive median/IQR resource measures are valid. No superiority state is inferred from timing repetitions.
**State:** `Supported` means the measurement claim is supported, not that FedSIRA is faster or cheaper than every comparator.

### `Secondary Generalization`

**Evidence:** `Secondary-Dataset Generalization`.
**Minimum support:** for both secondary scenarios, resolved FedSIRA is target-F1 non-inferior within `0.02` and malicious admission is not worse by more than `0.05` relative to each of `One Independent Retrain` and `Multiple Retrains with Direct Krum`; the applicable Family 10 adjusted p-values are `<0.05`.
**State:** `Supported` only for data/attack generalization under the deterministic pseudo-domain construction; never for real administrative independence.

### `IoT IDS Application`

**Evidence:** valid execution of the primary N-BaIoT program and, where available, the secondary CICIoT2023 generalization program.
**Minimum support:** `Supported` when both dataset programs complete validly and their claim boundaries are respected; `Partially Supported` when the primary program completes validly but the secondary program is `Not Tested` for data-availability/schema reasons; `Not Supported` when the primary IoT IDS program itself is invalid.
**Scope:** only the validated raw releases, target definitions, proxy constructions, and tested conditions in this roadmap.

# 36. Result-set and no-post-hoc-selection rule

The scientific result set is the complete Section 30 experiment plan, not a favorable subset. No planned completed cell is included or excluded because of its outcome; failed seeds are never replaced; invalid baselines are not silently substituted; primary metrics/tests/margins are not changed; and the four collapse experiments support only their prespecified mechanical decisions.

Artifact reuse never changes the logical result set. Reusing one valid anchor, source candidate, reproduction row, score artifact, or calibration product across compatible cells is computational reuse of the same declared scientific object, not removal of planned cells or inferential repetition. Each planned cell retains its own required terminal outcome and metric/statistical record.

An experiment is complete only when all required cells have valid terminal scientific outcomes, required metrics/statistics and claim/gate decisions exist, scientific invariants pass, and claim-bearing evidence is traceable through a complete non-stale artifact lineage to the exact data/configuration/seed/implementation dependencies.

# 37. Scientific completeness verification

Scientific completeness verification is a read-only validation step performed automatically by `fedsira report` before project-summary materialization. It does not rerun experiments, alter scientific choices, create a new execution phase, or create a second observation.

The verification must confirm:

1. the Section 31 planned-cell count is exactly satisfied by the active semantic-cell registry, with every cell represented by exactly one scientific terminal record;
2. every required preprocessing, model, protocol, evaluation, metric, statistical, comparison, and claim artifact is `Complete`, checksum-valid, dependency-compatible, and reachable through the active artifact DAG;
3. no active scientific artifact has a stale or invalid ancestor;
4. every required comparison has the prescribed complete-pair state and every Holm family has deterministic membership and adjustment artifacts;
5. all Section 28 scientific invariants and leakage barriers passed for the active producer identities;
6. all Section 35 claim states are mechanically derivable from valid evidence with no manual override;
7. each Section 33–34 reporting source-data artifact resolves to valid scientific inputs;
8. every manuscript-facing number is traceable to the exact dataset, role/split manifest, seed bundle, producer-component fingerprint, relevant dependency/runtime signature, and upstream artifact identities.

If any condition fails, project-summary reporting is `Blocked`; `fedsira doctor` reports the first missing, stale, invalid, or incomplete dependency and the next valid command. Experiment-specific reporting may still materialize an individually complete experiment whose own dependencies pass verification.

# 38. Manuscript-facing result materialization

`fedsira report` exports only completed verified scientific evidence. All metrics, inferential statistics, confidence intervals, multiplicity decisions, materiality gates, scientific invariants, and provenance checks have already been completed by `run`.

The named tables in Section 33, figures in Section 34, and claim states in Section 35 are mandatory. They must be generated from authoritative machine-readable `outputs/` metric/statistical/claim evidence, never from manually transcribed values or parsed logs. Experiment-owned exports are materialized under `results/experiments/<descriptive-experiment-name>/`; cross-experiment products are generated once under `results/project_summary/` rather than duplicated across experiment exports. Final claim-state exports belong under `results/project_summary/claim_registry/`, and compact reconstruction summaries belong under the applicable `results/project_summary/reproducibility/` subdirectories.

Table/figure source-data products remain computational artifacts under `outputs/artifacts/derived/` or the owning experiment's `outputs/experiments/<descriptive-experiment-name>/artifacts/derived/` location according to their reuse scope. `results/` contains only the compact verified render/export products defined in Section 23 and is never read back by scientific execution.

Reporting artifacts have their own dependency fingerprints. A reporting-code or formatting change rematerializes only the affected table/figure/report descendants. It cannot invalidate the scientific metric/statistical artifacts from which they are rendered.

Final exports exclude caches, debug logs, failed/invalid/stale runs, overwritten archives, temporary files, and incomplete analysis.

# 39. Reproducibility and study-completion contract

A third party must be able to reproduce the study from the recorded reconstruction commit, complete dependency lock, stage-scoped producer-component fingerprints, exact raw-data identities, single schema-validated `configs/fedsira.yaml`, fixed deterministic contracts in Sections 9–13, descriptive CLI sequence, fixed Section 30 experiment plan, and immutable upstream artifact identities.

Reproducibility requires traceability sufficient to detect dataset/split, configuration, seed, material producer-code/runtime, cell-phase, or upstream-artifact mismatch. It must also distinguish these from unrelated repository or dependency changes that do not affect a producer. A prescribed generic workflow-engine provenance schema is not required.

The study is ready for manuscript reporting only when:

* all required Section 30 cells reach valid scientific terminal states, including legitimate `Abstain`, `Dormant`, `Rejected Claim`, `Expired`, null, and boundary outcomes where prescribed;
* the Section 31 count invariant and Section 37 scientific completeness verification are satisfied;
* required metrics, statistics, effects, confidence intervals, multiplicity and materiality decisions exist;
* every scientific invariant and data-leakage barrier passes;
* every active artifact lineage is complete, hash-valid, dependency-compatible, and free of active stale descendants;
* final claim states are mechanically determined by Section 35;
* every manuscript-facing number is traceable to the fixed scientific lineage;
* all Section 33–34 products can be generated without manually transcribing scientific values.

# 40. Methodological rationale for fixed execution choices

These rationales explain fixed choices already specified elsewhere; they do not create additional configuration authority.

* **Primary dataset — N-BaIoT:** nine commercial-device identities support a natural heterogeneous device-proxy federation, and a Gafgyt subtype can be withheld as the post-reference capability. Device identities are experimental domain proxies, not evidence of organizational independence.
* **Secondary dataset — CICIoT2023:** a distinct large-scale IoT attack corpus with a `Backdoor Malware` subtype supports cross-dataset mechanism-direction testing. Deterministic pseudo-domains support data/attack generalization only.
* **Robust synthesis — Krum with $n=5,f=1$:** the operator supplies an explicit synthesizer-specific worker-count requirement and prevents replacing that requirement with a generic `2f+1` rule. The original Krum convergence theorem is not automatically claimed for heterogeneous local-training deltas.
* **Inference — exact paired seed-level sign-flip tests, Holm correction, paired effects, and 10,000-resample bootstrap CIs:** the fixed 10-seed paired design makes the seed the inferential unit and prevents client/domain pseudoreplication.

# 41. Source and method reference register

These references justify externally grounded dataset/methodology choices and prior-art baseline families. They are not additional project planning documents.

* Meidan, Y., Bohadana, M., Mathov, Y., Mirsky, Y., Breitenbacher, D., Shabtai, A., Elovici, Y. **N-BaIoT: Network-based Detection of IoT Botnet Attacks Using Deep Autoencoders.** IEEE Pervasive Computing, 2018. UCI dataset DOI: `10.24432/C5RC8J`; official dataset record: `https://archive.ics.uci.edu/dataset/442/detection+of+iot+botnet+attacks+n+baiot`.
* Ubuntu Packages. **`unrar` package for Ubuntu 24.04 LTS (noble), version `1:7.0.7-1build1`.** `https://packages.ubuntu.com/search?keywords=unrar`. The utility is an execution dependency only when the official N-BaIoT RAR archives, rather than an already-extracted equivalent layout, are supplied.
* Neto, E. C. P. et al. **CICIoT2023: A Real-Time Dataset and Benchmark for Large-Scale Attacks in IoT Environment.** Sensors 23(13):5941, 2023. Official dataset page: `https://www.unb.ca/cic/datasets/iotdataset-2023.html`.
* Blanchard, P., El Mhamdi, E., Guerraoui, R., Stainer, J. **Machine Learning with Adversaries: Byzantine Tolerant Gradient Descent.** NeurIPS, 2017. Krum definition and admissibility source. Official paper: `https://papers.neurips.cc/paper/6617-machine-learning-with-adversaries-byzantine-tolerant-gradient-descent`.
* Yin, D., Chen, Y., Ramchandran, K., Bartlett, P. **Byzantine-Robust Distributed Learning: Towards Optimal Statistical Rates.** ICML, 2018. Median/trimmed-mean robust learning reference.
* Cao, X., Zhang, Z., Jia, J., Gong, N. Z. **FLCert: Provably Secure Federated Learning Against Poisoning Attacks.** IEEE TIFS, 2022.
* Heydaribeni, N. et al. **SureFED: Robust Federated Learning via Uncertainty-Aware Inward and Outward Inspection.** 2023.
* Xie, Y., Fang, M., Gong, N. Z. **FedREDefense: Defending against Model Poisoning Attacks for Federated Learning using Model Update Reconstruction Error.** ICML, 2024.
* Zhao, L. et al. **Shielding Collaborative Learning: Mitigating Poisoning Attacks through Client-Side Detection.**
* Zheng, T., Li, B. **FedReview: A Review Mechanism for Rejecting Poisoned Updates in Federated Learning.**
* Latif, N., Ma, W., Ahmad, H. B. **FedDBC: A density-based defense against collusion attacks in federated intrusion detection for IoT networks.** Computer Networks, 2026.
* PyTorch. **`torch.use_deterministic_algorithms` API documentation.** Reference used for the fail-closed deterministic-execution contract: `https://docs.pytorch.org/docs/stable/generated/torch.use_deterministic_algorithms.html`.
* Relevant secure continual-learning, recovery, and suspicious-update preservation families are represented through the common-framework baseline contracts in Section 16; those runs compare mechanisms under this study's data and budget rather than asserting reproduction of the original papers' reported benchmark numbers.

---

# 42. Implementation-completion rule

Implementation readiness is satisfied when the single schema-validated `configs/fedsira.yaml` supplies every value that is genuinely configuration data, every fixed scientific/execution rule is implemented from its authoritative roadmap section without hidden defaults, preprocessing and smoke validation pass, every Section 16 baseline and Section 30 experiment is executable without inventing a scientific choice, the stage artifact DAG and producer dependency scopes in Sections 25–27 are implemented, completed reruns are idempotent, compatible expensive artifacts are reused across cells/experiments, stale descendants are automatically excluded, recovery resumes from the nearest valid artifact, overwrite/recovery cannot create duplicate scientific observations, all claim-bearing metrics/statistics implement Sections 17–18, and `doctor` can identify any remaining data, artifact, experiment, or evidence blocker.

This is an implementation gate only. Final scientific study completion is defined once in Section 39.

# 43. Configuration derivation and precedence

Configuration precedence deliberately separates data from specification.

The precedence order is:

1. the relevant scientific/execution section of this roadmap for fixed algorithms, architecture, formulas, preprocessing/validation semantics, ordering/ties, baseline and experiment definitions, authority/no-post-hoc-selection rules, failure behavior, artifact semantics, reporting requirements, and claim logic;
2. `configs/fedsira.yaml` for values that are genuinely supplied configuration data: dataset/target identifiers, numerical parameters and thresholds, split/sampling intervals, experiment-strength grids, actual seeds, paths, runtime limits, and genuine categorical selections;
3. validated raw-data manifests for observed release facts that cannot be known before acquisition;
4. deterministic derivation functions for values computable from configured, fixed-specification, and observed inputs;
5. runtime measurements and immutable artifact manifests for observed efficiency/resource quantities, realized producer identities, dependency fingerprints, and hashes.

Typed Python models, enums, resolved experiment objects, generated manifests, and CLI registries are validated implementations or representations of these authorities and may not override them. A fixed scientific rule is not converted into user-configurable behavior merely because software represents it with an enum, constant, or registry entry.

Derived facts are never independently configured. This includes model input/output widths from validated schemas/class registries, trainable parameter count, non-source domain count, Krum count admissibility and nearest-neighbor count where derivable, guaranteed honest verifier positives, secondary pseudo-domain count, ensemble group size, random-panel contamination probability, transformation row counts, evidence-role row counts, equal-domain/equal-class weights, semantic-cell fingerprints, artifact dependency fingerprints, artifact identities, transitive stale-descendant sets, and the Section 31 cell/phase totals.

Raw dataset facts that can vary by release or local bytes—file/shard counts, row counts, exact file hashes, observed feature/label inventories, target availability by domain, nonfinite-row exclusions, and per-role evidence sufficiency—are materialized by `preprocess`. Official expectations remain validation expectations; actual validated bytes determine execution. Observed insufficiency leads to the scientific blocked/`Abstain`/`Dormant` behavior already defined, never to a post-hoc change in thresholds or sample requirements.

Artifact-type dependency scopes remain implementation metadata adjacent to each producer. They identify which YAML fields, fixed roadmap rules, observed inputs, upstream artifacts, implementation components, and external dependencies materially determine the artifact. A scope change changes the artifact schema/component fingerprint and invalidates that artifact type as required by Sections 25–27; it does not create a second configuration authority.
