# Leave-Fault Geometric Median Certificate

The contribution is this decision. The existing FedSIRA lifecycle (proposal screen, quorum, source-identity exclusion, Krum selection, final gate) is the problem scaffold and the comparison baseline. Quorum, Krum, source-identity exclusion, and the final gate are not this algorithm.

The study evaluates the certificate. The study is not the contribution.

## Problem

A post-reference participant names a capability. The proposal identifies which fixed claim is investigated. The proposing source must not receive production authority. Independent domains return an update, a utility report, and a harm report. Up to `f` of those domains may be Byzantine or unreliable. The algorithm admits the capability, rejects it, or leaves it dormant, and, on admission, returns a production update whose source weight is identically zero.

Four objects stay distinct:

| Object | Role in the certificate |
| --- | --- |
| Proposal information | The claim identifier. It selects which capability the evidence is about. It is not a weight. |
| Supporting evidence | Non-source updates, utilities, and harms. |
| Production contribution | The geometric median of leave-`f` coalition means, with participant weights derived from those means. |
| Final authority | Admitted only when the worst leave-`f` certificate clears the configured utility floor and harm ceiling. Otherwise rejected or dormant. The source weight on that authority is 0. |

## Inputs

- Source identity `s`.
- Proposal claim `π`. Information only.
- Source update `u_s`, source utility `q_s`, source harm `h_s`. Recorded. The full mechanism does not put them in a coalition, a mean, a median, or a weight.
- Independent evidence `{(i, u_i, q_i, h_i)}` with `i ≠ s`. Each `u_i` is a vector in `R^d`. Each `q_i` is a utility in `[0, 1]`. Each `h_i` is a harm.
- Configuration `(f, q, τ, η, T, ε)` from `protocol.leave_fault_certificate` in `configs/fedsira.yaml`.

Loaded values used by the executed comparison: `f = 1`, `q = 3`, `τ = 0.8`, `η = 0.02`, `T = 8`, `ε = 1e-8`. `τ` equals the lifecycle median utility floor. `η` equals the lifecycle supported-macro-F1 drop ceiling. `f` equals the lifecycle synthesis fault bound. `q = 2f + 1` is the support rule. It is not the lifecycle's six-domain sample-size rule, and it is not a lowered `τ`.

## Output

- State in `{Admitted, Rejected Admission, Dormant}`.
- Certificate utility `J*` or absent.
- Certificate harm `H*` or absent.
- Production update `w` or absent.
- Source production weight `α_s`.
- Participant weights on the evidence domains that entered the decision. Empty when the state is not Admitted.

## Definitions

Sort the selected evidence by domain id before every combination. Let `N` be that ordered domain set and `n = |N|`.

Under the full mechanism the source row is not in `N`, and

```text
α_s := 0
```

A fault set is any `B ⊂ N` with `|B| = f`. The coalition is `C_B = N \ B`. There are `C(n, f)` such coalitions. Write `m = C(n, f)`.

```text
μ_B = mean { u_i : i ∈ C_B }
U_B = lower median { q_i : i ∈ C_B }
H_B = upper median { h_i : i ∈ C_B }
```

For a sorted length-`k` sample the lower median is the entry at index `(k - 1) // 2` and the upper median is the entry at index `k // 2`. Both are the ordinary median when `k` is odd.

```text
J* = min_B U_B
H* = max_B H_B
```

`w` is the geometric median of the coalition means `{μ_B}`, computed by Weiszfeld for a fixed budget of `T` iterations. The initializer is the coordinate-wise median of those means. If any mean lies at distance at most `ε` from the current point, Weiszfeld returns that nearest mean and stops. Ties break by the smaller mean index, which follows the combination order of the sorted domains.

Participant weights, after admission, map those inverse-distance coefficients back onto coalition members. For each coalition mean,

```text
β_B = 0                         if ||μ_B - w|| ≤ ε
β_B = 1 / ||μ_B - w||           otherwise
```

If every `β_B` is 0, set every `β_B` to 1. For each domain `i ∈ N`,

```text
raw_i = sum { β_B : i ∈ C_B }
weight_i = raw_i / sum_j raw_j
```

The full mechanism then overwrites the source weight with 0. A production vector that happens to equal a copied source vector still has `α_s = 0`, because the source row was not a summand.

## Objective

Choose the production update and the admit / reject / dormant state by the worst leave-`f` coalition, not by the best one and not by a single selected vector:

```text
J* = min_{B ⊂ N, |B| = f} lower-median { q_i : i ∈ N \ B }
H* = max_{B ⊂ N, |B| = f} upper-median { h_i : i ∈ N \ B }
w  = GeoMed { μ_B : B ⊂ N, |B| = f }
```

subject to

```text
α_s = 0
n ≥ q
n ≥ 2f + 1
```

## Decision

```text
if n < q or n < 2f + 1:     Dormant, and w is absent
else if J* ≥ τ and H* ≤ η:  Admitted, and return w with α_s = 0
else:                        Rejected Admission, and w is absent
```

`J*` and `H*` are reported on rejection. They are absent when support is insufficient.

## Algorithm

1. Drop the source row. Set `α_s = 0`.
2. Sort the remaining evidence by domain id. Reject duplicate domains, an empty panel, an empty update, or a dimension mismatch.
3. If `n < q` or `n < 2f + 1`, return Dormant.
4. Enumerate every fault set of size `f` in combination order.
5. For each fault set, form the coalition mean, the lower-median utility, and the upper-median harm.
6. Set `J*` to the minimum coalition utility and `H*` to the maximum coalition harm.
7. If `J* < τ` or `H* > η`, return Rejected Admission with `w` absent.
8. Set `w` to the Weiszfeld geometric median of the coalition means.
9. Assign inverse-distance coalition weights, map them onto members, and renormalize.
10. Return Admitted, `w`, `J*`, `H*`, and `α_s = 0`.

## Pseudocode

```text
Algorithm 1: Leave-Fault Geometric Median Certificate

Input: source s, claim π, source record (u_s, q_s, h_s),
       evidence {(i, u_i, q_i, h_i)}, configuration (f, q, τ, η, T, ε)
Output: state, J*, H*, w, α_s, participant weights

1:  E ← { (i, u_i, q_i, h_i) : i ≠ s }          ▷ π names the claim; u_s is not an addend
2:  sort E by domain id
3:  α_s ← 0
4:  if E is empty, ragged, or contains a repeated domain then fail
5:  n ← |E|
6:  if n < q or n < 2f + 1 then
7:      return Dormant, J* absent, H* absent, w absent, α_s = 0
8:  for each B ⊂ domains(E) with |B| = f, in combination order do
9:      C ← domains(E) \ B
10:     μ_B ← mean { u_i : i ∈ C }
11:    U_B ← lower median { q_i : i ∈ C }
12:    H_B ← upper median { h_i : i ∈ C }
13: J* ← min U_B
14: H* ← max H_B
15: if J* < τ or H* > η then
16:     return Rejected Admission, J*, H*, w absent, α_s = 0
17: w ← Weiszfeld({μ_B}, iterations = T, tolerance = ε,
                initializer = coordinate-wise median of {μ_B})
18: weights ← renormalized member sums of inverse-distance coefficients of {μ_B} about w
19: return Admitted, J*, H*, w, α_s = 0, weights
```

`Weiszfeld` is deterministic. At each iteration it computes Euclidean distances from the current point to every coalition mean. A distance of at most `ε` returns the nearest mean and stops. Otherwise the next point is the inverse-distance weighted mean of the coalition means. After `T` iterations it returns the current point. No random source is used. The same input and the same configuration produce the same state, the same `J*`, the same `H*`, and the same `w`.

## Complexity

Let `n` be the number of non-source evidence rows, `d` the update dimension, `f` the fault bound, and `T` the iteration budget.

- Time. `C(n, f)` coalitions. Each mean and each order statistic reads `O(n)` scalars of width `d` or width 1. Weiszfeld then spends `O(T · C(n, f) · d)`. The bound is `O(C(n, f) · n · d · T)`.
- Memory. The coalition means dominate: `O(C(n, f) · d)`.
- Communication. Each non-source domain sends one vector and two scalars. The source sends the claim identifier and no authority payload. The authority payload from the source is 0. Communication is `O(n(d + 2))` plus the claim id.

For the executed profile `f = 1` and `n ≤ 7`, `C(n, 1) = n`, so the decision is linear in the panel.

## Hyperparameters

| Symbol | Configuration field | Meaning |
| --- | --- | --- |
| `f` | `fault_bound` | How many evidence domains are removed in every coalition. The claim is stated at this bound, which is the synthesis fault bound. |
| `q` | `minimum_support` | Smallest panel that may leave Dormant. Required to be at least `2f + 1`. |
| `τ` | `utility_floor` | Worst leave-`f` lower-median utility required for admission. Set equal to the lifecycle median floor. |
| `η` | `harm_ceiling` | Worst leave-`f` upper-median harm allowed for admission. Set equal to the lifecycle harm ceiling. |
| `T` | `weiszfeld_iterations` | Fixed Weiszfeld budget. |
| `ε` | `weiszfeld_epsilon` | Coincidence tolerance for the Weiszfeld early stop and for production-vector equality. |

## Invariants

- Evidence order does not change the decision. Combinations follow the domain-id sort.
- Changing `u_s`, `q_s`, or `h_s` does not change `w`, `J*`, `H*`, the state, or `α_s` while source exclusion is on.
- `α_s = 0` on every full-mechanism output, including Admitted.
- `J*` equals the minimum leave-`f` lower median of the non-source utilities.
- A leave-`f` coalition of size `k = n - f` has lower median at sorted index `(k - 1) // 2`. At `n = 7` and `f = 1`, that size is 6 and the index is 2. One low report occupies index 0 of every coalition that keeps it, so that coalition's lower median remains the high utility and `J*` stays at `τ`.
- The same input and configuration produce the same output. There is no seed inside the decision. The screen seed affects only the lifecycle and quorum baselines, which use screen order.

## Boundary conditions

- The correctness claim stops at `f` compromised evidence domains. A larger compromised set is outside the claim.
- `n < q` or `n < 2f + 1` is Dormant, including a two-domain panel when `q = 3`.
- At `n = 7` and `f = 1`, two low reports still leave `J*` at the high utility. The worst coalition keeps both lows and drops one high report. Sorted index 2 of that size-6 coalition is the high utility, so the state is Admitted when the remaining reports sit on `τ`. `J*` equals a low report only when the worst coalition contains at least three low reports, because index 2 is then a low value.
- A useful capability that only two of seven domains support has five low reports. The worst leave-1 coalition still has a low value at index 2, so the certificate rejects it. Raising `f` to cover that minority would exceed the declared bound. The certificate does not do that.
- If every non-source vector is identical, `w` equals that vector. It may also equal a copied source vector. `α_s` remains 0.

## Failure conditions

- Repeated domain ids, an empty evidence tuple, an empty update, or ragged dimensions raise.
- The geometric-median arm always returns a point when the support check has passed, because the coalition-mean set is non-empty.
- The without-geometric-median ablation returns Dormant when its Krum committee is inadmissible (`n < 2f + 3`). That ablation is not the algorithm.
- Honest disagreement that survives every leave-`f` deletion is a rejection, not an exception.

## Limiting case

Set `f = 0`, keep source exclusion, and keep the lower median. There is one coalition, the full non-source panel. Its mean is the mean of the non-source updates. Weiszfeld is initialized at that single point and returns it because the distance is 0. `J*` is the lower median of the non-source utilities, and `H*` is their upper-median harm. Admission is that lower-median mean gate. This is the named reduction: the non-source lower-median mean gate. It is not the lifecycle, and it is not Krum.

## Ablations

Each ablation removes one mechanism. The full mechanism is the algorithm. An ablation is a comparison arm.

| Arm | What is removed | What the executed cases show |
| --- | --- | --- |
| Without source exclusion | The source row enters `N` and can receive positive weight. | On the all-honest panel, moving the source update moves the production update and the source weight is positive. The full mechanism keeps the same production update and weight 0. |
| Without worst case | `f` is treated as 0, so only the full panel is scored. Support still uses `q`. | Conflicting evidence, which the full mechanism rejects at `J* = 0.1`, is admitted. The optimistic existence rule fails the same way. |
| Without geometric median | `w` is the Krum selection of the raw non-source vectors, with a one-hot weight on the first matching domain. | On the in-geometry panel the production update equals the malicious vector. The full mechanism admits the same panel with a production update that does not. |
| Without lower median | Coalition utility is the arithmetic mean. Harm stays the upper median. | The sharp quality gap, whose worst lower median is below `τ`, is admitted by the mean. The full mechanism rejects it. |

The certificate does not claim a diversity term, a reliability weight, an uncertainty term, or a sequential boundary. Those belong to candidates that were not promoted.

## Relationship to the FedSIRA lifecycle

The lifecycle remains executable as the baseline arm. On the synthetic comparison it opens a screen, requires the configured count of adequate non-source domains, selects one non-source vector with Krum at the same `f`, and applies the median, minimum-domain, and harm bars. The certificate replaces that chain with Algorithm 1.

Two lifecycle failures are the reason for the replacement, at the same `f`, the same `τ`, and the same `η`, with source weight 0 on both arms:

- In-geometry selection. Seven non-source vectors include a strategically placed malicious vector. Krum returns that vector, the final gate passes, and the lifecycle admits with the malicious vector as the entire production update. The certificate admits with `J* = 0.8` and a production update that is not that vector.
- Single low report. One of seven utility reports is low and the rest sit on the floor `τ`. The lifecycle minimum-domain bar rejects the panel. The certificate's worst leave-`f` lower median remains `τ`, so it admits. Replacing the minimum-domain bar is a different rule. `τ` is not lowered and `f` is not raised.

The lifecycle's six-domain sample-size check is a separate baseline predicate. The certificate's support predicate is `n ≥ max(q, 2f + 1)`. On the two-domain panel both the lifecycle and the certificate stay dormant.

The synthetic lifecycle gate is a stand-in for the shipped final-gate predicates: median utility, minimum domain utility, and mean harm. It is not a neural-network evaluation. The opening predicate used by the quorum and lifecycle arms reads the configured capability-contract gain floor. A quorum that already rejects a weak panel would also be rejected by a stricter opening rule.

## Relationship to prior algorithms

Prior art is the start of the separation, not a reason to keep the lifecycle as the contribution.

1. Krum (Blanchard, El Mhamdi, Guerraoui, Stainer, 2017) selects the submitted vector with the smallest sum of squared distances to its `n - f - 2` nearest neighbors. Its objective is one-round robust aggregation. It returns one submitted vector, so an attacker inside the honest geometry is installed. It has no admit / reject / dormant certificate and no source-authority constraint. The FedSIRA extension scores every leave-`f` coalition by a lower median, admits only the worst of those scores, and sets the production update to the geometric median of the coalition means. The source row is not eligible for that median. On the executed in-geometry panel, Krum's production update equals the malicious vector and the certificate's does not.

2. Coordinate-wise median (Yin, Chen, Kannan, Bartlett, 2018) and Bulyan (El Mhamdi, Guerraoui, Rouault, 2018) aggregate one training round. A coordinate-wise median of the raw vectors can equal an attacker who sits at the median coordinate. Classical Bulyan needs `n ≥ 4f + 3` and then averages coordinates near the median. The adapted comparator used here keeps the `n - 2f` lowest Krum scores when the Krum committee is admissible, then takes the coordinate-wise median. That adaptation emits the attacker on the fault-bound panel's coordinate median and does not emit it from Bulyan at `n = 7`, `f = 1`. Neither method decides an authority transition or forces `α_s = 0`. The certificate's production update on that fault-bound panel does not equal the attacker, while the coordinate-wise median of the raw vectors does.

3. The geometric median and the Weiszfeld iteration are a location estimator. Here they map an already certified set of coalition means to one production vector. The decision object is `(J*, H*, state)`, not the location estimator. Removing the geometric median and substituting Krum restores malicious selection, which is why the estimator is load-bearing and why it is not sufficient by itself.

4. Wald's sequential probability ratio test, and Huber's robust sequential tests, assume i.i.d. stochastic observations and return no production update. The clipped sequential candidate restricts each increment to `1 / (f + 1)` and excludes the source. On the executed panels it admits the single-low useful case, and it also admits the two-domain panel (`clipped sum = 1`) where the certificate is dormant. It cannot complete an authority transfer.

5. Covariance intersection (Julier and Uhlmann) fuses two states under unknown correlation. The exploratory arm treats each non-source report as a sensor whose variance grows with harm and falls with utility. A confident report dominates. On the single-low panel the fused utility is about `0.786`, below `τ`, so the arm rejects the case the certificate admits. It also admits the two-domain panel.

6. Dempster-Shafer combination, and Yager's rule that assigns conflict to uncertainty, combine independent masses. The exploratory arm caps each report's committed mass at `1 / (f + 1)` and does not combine a source mass. On the executed conflicting panel the admit mass is about `0.531`, so the arm admits a panel the certificate rejects at `J* = 0.1`. It also admits the two-domain panel and returns no production update.

Optimistic leave-`f` selection admits when some coalition's lower median passes, and deploys that coalition's mean. It is the existence twin of the certificate's minimum. On the executed conflicting, sharp-gap, and disagreeing panels it admits. The certificate rejects all three. That contrast is why the objective is the minimum.

## Executed selection, same safeguards

The promoted arm and the lifecycle use `f = 1`, `τ = 0.8`, `η = 0.02`, and source production weight 0. The exploratory arms that admit the single-low panel either return no production update, admit a two-domain panel, or admit a conflicting panel. The certificate admits the in-geometry panel without installing the malicious vector, admits the single-low panel at `J* = 0.8`, rejects the conflicting panel at `J* = 0.1`, and stays dormant at `n = 2`.

Quorum admits the weak-opening panel and the honest-minority panel. The lifecycle and the certificate reject the weak-opening panel. The honest minority of two highs among seven lows is also rejected by the certificate. That rejection is a declared boundary at `f = 1`, not a missed win: recovering it would require treating more than `f` lows as faults.

## Production mapping

`decide_leave_fault_certificate` in `src/fedsira/protocol/leave_fault_certificate.py` is the decision. `fedsira run "Leave-Fault Certificate Validation"` builds one cell per admission-decision arm and controlled world, calls `execute_leave_fault_validation_cell`, and that handler calls `admission_comparison_records`, which calls `decide_leave_fault_certificate` for the certificate and for each ablation. The cell artifact records the admission input, the state, and the source production weight. Hyperparameters are read from `LeaveFaultCertificateConfig`. The world name is used only to construct the synthetic case. The decision function does not branch on the world or on a desired outcome.
