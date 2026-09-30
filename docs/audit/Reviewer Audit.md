# Reviewer audit and novelty boundary

## Closest prior work

The components are not individually novel. The closest literature families are:

| Work | Overlap with FedSIRA | Remaining distinction and claim limit |
|---|---|---|
| [FedReview](https://arxiv.org/abs/2402.16934) | Peer review/voting to reject poisoned FL updates. | Reviews submitted updates; it does not make clean-anchor reconstruction of a newly proposed capability the production authority object. This rules out novelty from “reviewer voting.” |
| [FLShield](https://doi.org/10.1109/SP54263.2024.00141) | Uses participants’ benign data to validate local models before aggregation. | A close validation defense, but its focus is filtering ongoing-round local models, not the source-excluded new-capability admission lifecycle. Avoid broad “first participant validation” claims. |
| [SureFED](https://arxiv.org/abs/2308.02747) | Independent clean local references inspect incoming models using uncertainty. | It uses clean references for Byzantine robustness; it does not define committed non-source reconstruction, fresh post-commit verification, and source-excluded production admission as FedSIRA does. |
| [FLCert](https://doi.org/10.1109/TIFS.2022.3212174) | Multiple federated models and a malicious-client certificate. | Prior art for certified ensembles and group training; not a new-capability authority transition. |
| [FLTrust](https://arxiv.org/abs/2012.13995) and [FedREDefense](https://openreview.net/pdf?id=Wjq2bS7fTK) | Trusted-reference or reconstruction-based update filtering. | They assess ordinary submitted updates; FedSIRA's proposed differentiator is independent capability construction and source-excluded authority. |
| [Krum](https://papers.nips.cc/paper_files/paper/2017/hash/f4b9ec30ad9f68f89b29639786cb62ef-Abstract.html) | Robust synthesis of participant updates. Score is the sum of squared distances to the `n - f - 2` nearest other vectors. | Established operator, not a contribution. Do not transfer Krum convergence guarantees to heterogeneous local-training deltas; state only the implemented count condition and empirical results. |
| [A little is enough](https://arxiv.org/abs/1902.06156) and [convergence is not enough](https://proceedings.mlr.press/v80/mhamdi18a.html) | In-ball or small-magnitude poisoning evades geometric aggregators, including Krum. | Occupies the attack against Krum. FedSIRA does not claim Krum rejects an in-ball payload. The cheap vector POC reproduces that selection. |
| [Bucketing](https://arxiv.org/abs/2006.09365) and [SpectralKrum](https://arxiv.org/abs/2512.11760) | Robust aggregation when honest updates are heterogeneous or low-rank. | Occupied aggregator replacements. They are not a source-excluded capability-admission lifecycle. Not promoted. |
| [Conformal risk control](https://arxiv.org/abs/2208.02814), selective classification, and [SCoRE](https://arxiv.org/abs/2603.24704) | Finite-sample abstention or risk control for a monotone bounded loss. | Occupied threshold theory. At 6 and 8 calibration domains the `1/(n+1)` floor is about 0.143 and 0.111, so alpha 0.05 and 0.10 are vacuous. Not promoted. |
| [Federated Class-Incremental Learning / GLFC](https://openaccess.thecvf.com/content/CVPR2022/html/Dong_Federated_Class-Incremental_Learning_CVPR_2022_paper.html) | Learns new classes across federated participants. | New-class learning/forgetting is prior art. FedSIRA's distinction is adversarial authorization of an unsupported capability, not class-incremental learning alone. |
| [FedEraser](https://arxiv.org/abs/2012.13891) | Reconstructs an unlearned model by calibrating retained historical client updates. | Occupies removal of a client who already entered the aggregate. A wrong subtracted weight leaves a residual proportional to the payload. Identity exclusion never depends on that weight. Not promoted. |
| [FedRISC-IIoT](https://www.sciencedirect.com/science/article/abs/pii/S0167739X26002748) | Reputation-driven client selection plus layered robust aggregation for industrial IoT. | Filters and reweights ongoing clients. It does not admit a new capability from a clean anchor with proposal weight 0. Not promoted. |
| [HPoT](https://doi.org/10.1038/s41598-026-49902-4) | Hierarchical proof-of-trust and reputation-weighted participation, tolerating up to floor(N/3) Byzantine nodes. | Occupied trust-weighted aggregation. Not a source-excluded capability admission rule. Not promoted. |
| [ZTA-FL](https://arxiv.org/abs/2512.23809) | TPM attestation before a round, then SHAP-weighted aggregation. | Occupied attestation-plus-weighting of ongoing agents. Not promoted. |
| [Sentinel](https://arxiv.org/abs/2509.00634) | TEE remote attestation of local training; a failed client is left out of that round's aggregate. | Occupied exclusion of an unattested update. It does not construct the production checkpoint from non-source evidence after a proposal of weight 0. Not promoted. |

This is a focused closest-work audit, not a systematic literature review or proof of priority. The promoted decision is the **Leave-Fault Geometric Median Certificate** (`docs/algorithms/leave-fault-geometric-median-certificate.md`). The proposer may reveal which fixed capability to assess. The certificate gives that source production weight 0, scores every leave-`f` coalition of independent evidence by a lower-median utility and an upper-median harm, and sets the production update to the geometric median of the coalition means. The lifecycle, including quorum, Krum, source-identity exclusion, and the final gate, is the baseline. Do not use “first” without a documented systematic search.

## Skeptical reviewer objections

| Objection | Status | Highest-value response |
|---|---|---|
| Why FL; would one retrain solve it? | Needs final experiment. | Compare one independent retrain and multiple retrains + direct Krum against the same rows, evidence budget, and final gate. |
| Are “independent” domains really independent? | Legitimate scope limitation. | N-BaIoT has device proxies within one release/lab context; CIC domains are label-hashed pseudo-domains. State this plainly. For stronger claims, add distinct capture/site data. |
| Is this a natural new attack after deployment? | Not supported by this data. | The N-BaIoT role order is controlled disjoint replay from file order, with no absolute timestamps. Call it a synthetic post-reference construction. |
| Is the evaluation vulnerable to capture shortcuts? | Needs analysis; the POC found role shifts. | No model sees file/role IDs, but target roles share captures and role distributions shift. Check device-wise outcomes and add capture/session-held-out evidence if available. |
| Does the feature-space backdoor exist in raw traffic? | Not tested; limitation. | Describe as feature-space injection. Do not call it packet/flow-realizable absent a raw-network construction. |
| Does reproducibility prove truth? | No; known limitation. | Keep shared-label, spurious-context, and under-specification boundaries as limitations/diagnostics, not truth certification. |
| Does plurality or verification matter? | Unknown. | Use same committed opportunities for direct-Krum and verified methods; report component necessity only when its preregistered paired comparison survives. |
| Are many thresholds/gates arbitrary? | Needs rationale. | Separate validity gates from utility margins. Report effect sizes and intervals for all valid cells; null/small effects are results. |
| Is the study underpowered or overbuilt? | Needs variance evidence; high risk. | Ten seeds and 1,989 planned cells have no empirical variance/power estimate. Pilot only the narrow core and estimate paired-seed variance before locking expensive expansion. |
| Can a favorable subset hide failures? | Partly addressed in roadmap. | Preserve all registered eligible conditions, outcomes, `NA`, dormancy, rejection, and seed denominators; do not select only favorable devices/strengths. |
| Can missing diagnostics invalidate the central result? | Design risk. | Separate primary evidence readiness from exploratory claims. Mark unrun secondary claims `Not Tested`; do not make the whole report depend on them. |

## Recommended wording

If the confirmatory evidence supports it: “We introduce the Leave-Fault Geometric Median Certificate, a source-independent algorithm for safely admitting a post-reference capability under unreliable or Byzantine evidence. The proposal can identify what to assess. The certificate admits only when every leave-`f` coalition of independent evidence still clears the utility and harm certificate, and the production update is the geometric median of those coalition means. The source production weight is 0. The evaluation is bounded to the stated feature-space threat model and device-proxy replay construction.”

Do not imply that this proves semantic truth, benign origin, organizational independence, raw-traffic attack realizability, security beyond the tested bound, or deployment readiness.

## Candidate decision

`PROMOTED`: Leave-Fault Geometric Median Certificate. The earlier lifecycle-only stop is withdrawn. The lifecycle remains the baseline in `Scientific Decisions.md`. Conformal risk control, unanimity, a geometric source-payload veto, SpectralKrum or bucketing, SureFED-style uncertainty inspection, historical subtraction of a retained source update, and reputation-weighted or attested aggregation of ongoing clients stay rejected for the reasons recorded there. Krum, the coordinate-wise median, Bulyan, a clipped sequential test, covariance intersection, and Yager combination were compared on the controlled worlds and were not promoted; the separation is in the algorithm specification. This audit did not execute the 1,989-cell grid; that compute is an `EXTERNAL_RESOURCE_BOUNDARY`, and no performance result is reported from it. The historical one-cell data-validation record has performance outcomes `NA` and is not confirmatory evidence. The ordinary-FL ancestry repair is a validity fix of the §17.3 endpoint. It is not the certificate.

## Reviewer A — novelty

Objection. The lifecycle is Krum, a majority vote, and a threshold, already covered by FedReview, FLTrust, conformal abstention, FedEraser, or a 2026 reputation and attestation defense.

Evidence. FedReview, FLShield, SureFED, FLCert, and FLTrust score or vote on submitted updates. Conformal risk control and SCoRE calibrate an abstention threshold under exchangeability. Krum, bucketing, and SpectralKrum select among gradient vectors. FedEraser subtracts or recalibrates a client who already entered the history. FedRISC-IIoT, HPoT, ZTA-FL, and Sentinel weight, attest, or drop ongoing clients. The admission object here is a checkpoint built from a clean anchor after the source identity has been kept out of synthesis. The POCs show the conformal alternative is vacuous at 6–8 domains, that a payload veto would collapse the source-copy contrast, and that a wrong unlearning weight leaves a source residual while identity exclusion does not.

Fix. The formal specification is the Leave-Fault Geometric Median Certificate. Krum, quorum, and the final gate stay baseline components. Wording still forbids a “first” claim. The certificate is separated from Krum, the coordinate-wise median, Bulyan, sequential tests, covariance intersection, and Yager combination in the algorithm specification.

Verification. The candidate section of this file and `Scientific Decisions.md` name the rejected alternatives and the occupied papers. `tests/scientific/test_source_artifact_exclusion.py` calls the shipped quorum and Krum functions.

Residual risk. A paper outside this focused search could still share the lifecycle. That is why the project does not claim priority. A systematic review remains out of scope.

## Reviewer B — methodology

Objection. Role windows leak the decision, the quorum hides a Byzantine veto or a free pass, and Krum’s geometry is being treated as a theorem about device heterogeneity.

Evidence. The earlier nine-capture hash POC found zero exact row overlap and large within-capture shift. This pass scanned all source-proposal rows of `Danmini_Doorbell/gafgyt_attacks/combo.csv` (59,718 rows, 115 numeric columns, no identifier-like column) against 64 reproduction-window queries: minimum squared distance 12.43 after per-feature scaling, median of those minima 28.32, exact-zero fraction 0. The published scaler records 320,000 training rows and 115 features; `datasets/nbaiot/prepare.py` fits those moments on anchor-train rows whose class is not the target. The shipped quorum certifies one dissent and rejects a lone positive. The in-ball vector is selected by the shipped Krum.

Fix. Claims stay on paired master seeds and device-proxy replay. The quorum is documented as `q = f_V + 1`, honest lower bound 1, not unanimity and not two honest positives. Krum convergence is not cited for heterogeneous deltas. Conformal alpha 0.05 and 0.10 are outside the claim set. No confounder found here was left as a mere manuscript limitation when a code or wording repair existed. The shared-capture dependence cannot be removed from this release.

Verification. POC figures are in `POC Results.md`. The scientific tests assert the quorum and both Krum regimes.

Residual risk. Nearest-neighbor evidence is one capture and 64 queries, not all nine files. Role windows remain one capture. The confirmatory paired-seed estimates do not exist until the grid runs. Those two limits are structural and an external resource boundary.

## Reviewer C — systems and reproducibility

Objection. Source exclusion was a vacuous call, and malicious admission was then still a method name. The certified ensemble was listed as an ordinary-client attack while its trainer ignored the designated client. The payload check on the production path is passed `None`.

Evidence. That call did not observe `_last_committee_deltas` or the single-verifier updates. `validate_production_checkpoint_excludes_source(production_checkpoint, None)` cannot fire.

Fix. Full FedSIRA and One Independent Retrain now call `require_source_identity_excluded_from_synthesis` on `_last_synthesis_row_ids`, which both the single-verifier and the multi-row branches record. A present source identity raises. The payload comparison stays unwired on purpose: an equality veto would make the source-copy experiment true by construction. Honest synthesis still passes `use_source_delta_for_source_domain=False` and `force_first_row_to_source_delta=False`. `report` still fails closed. Ordinary-client model replacement, including the certified ensemble, is selected by `_model_replacement_training_args` and stored only when that client's update is accepted into the aggregate. A designated client who is not accepted scores malicious admission 0. The clean source is not added to the compromised set for that ordinary-client attack. Krum records the client only when the selected row is that client. Density records the client only when trimming retains it. Reconstruction records the client only when the filter accepts the update.

Verification. `tests/scientific/test_source_artifact_exclusion.py` calls the shipped guard, asserts the handler source contains that call and the row-id field, and no longer contains `source_row_id=None`. `tests/scientific/test_ordinary_fl_attack_ancestry.py` calls `model_replacement_client_state`, `clients_retained_by_trimmed_mean`, the shipped selector, and the shipped FedAvg and ensemble baseline cells. `tests/unit/reporting/test_malicious_admission_aggregate.py` calls `materialize_experiment_evidence` and rejects a lone fractional indicator and the compensating pair 0.5 and 1.5 before the rate is computed. `tests/scientific/test_ordinary_fl_attack_ancestry.py` drives client review, sanitization, recovery, and independent local reference under One Byzantine Post-Reference Participant through `_execute_baseline_cell`. Each admits only the clean source and scores malicious admission 0. The same client-review path under Useful Backdoored Source — 5% scores 1.

Residual risk. The `None` payload argument remains. It is not an exclusion mechanism. Identity exclusion is the mechanism. Re-attack after the fix does not find a second unwired honest-path insertion of the source identity. Claim-bearing outputs are still absent, so artifact lineage for those outputs stays unexercised by a real grid.

## Re-attack after the fixes

Reviewer A, repeated. Replacing Krum or adding conformal risk control would move the project into prior art that the POCs show either answers a different question or cannot certify alpha 0.05 here. The lifecycle sentence survives that attack only with the boundaries above.

Reviewer B, repeated. The Danmini distances and the anchor-train scaler fit do not create organizational or temporal identification. They do remove exact-copy and identifier-column explanations for that probed capture. The design still generalizes only to the declared proxy construction.

Reviewer C, repeated. The guard now sees the ids the cell just produced. A stale three-domain prefix cannot satisfy the handler check. No second dead production call with an empty source id remains in `handlers.py`. The certified ensemble trainer now takes the same optional attack arguments as the other ordinary-client trainers and records an accepted compromised client before the ensemble gate. Re-attack does not find a second ordinary-client method that is named in the attack tuple and then ignores the designated client. Claim-bearing outputs are still absent, so artifact lineage for those outputs stays unexercised by a real grid.
