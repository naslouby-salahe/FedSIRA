# POC results

POCs are diagnostic only and are not model-performance or confirmatory evidence. Temporary scripts and machine-readable output live in the gitignored `docs/audit/pocs/` directory.

## N-BaIoT target-capture role dependence

**Question.** Does the current row-role partition reuse exact target rows, and how much within-capture dependence/role-window shift is visible in the actual raw target streams?

**Method.** Read the nine raw `GAFGYT_COMBO` CSVs directly. For each stream, apply the configured target role fractions, hash exact 115-feature rows across source-proposal/reproduction, reproduction/verification, reproduction/final-gate, and reproduction/report-test pairs, estimate median per-feature lag correlations at lags 1/10/100/1000, and compute descriptive absolute standardized mean differences (SMDs) between source/reproduction and reproduction/report-test windows. No model, outcome, p-value, or confirmatory experiment was run.

**Observed.** The nine files contain 515,156 target rows in total (per-device files: 53,012–59,718 rows; all 115 predictors). Exact row-hash intersections were zero for every inspected role pair in every capture. Median lag-1 feature correlation was 0.681 across captures (range 0.679–0.713); median lag-10 correlation was approximately 0 (range −0.00004–0.0207), and lag-1000 was approximately 0. Across captures, 20–24 of 115 feature-level SMDs exceeded 0.5 between source-proposal and reproduction windows; 23–31 exceeded 0.5 between reproduction and report-test windows. These per-feature descriptors are not inferential tests and do not adjust for correlation.

**Decision.** The split has row-level uniqueness, but role samples within a device/class share one capture, attack execution, acquisition setup, and feature-extraction context. Observed role shifts mean that outcomes could depend on capture segment as well as the capability. This does not demonstrate leakage-driven model results, but it rules out describing the roles as independent capture replications. Roadmap §9.6 now records this boundary. The dataset supports controlled device-proxy replay, not natural deployment time or independent-site replication.

**Next useful evidence.** Inspect device-level and seed-level outcomes by role-window support once the core experiment is authorized; for a cross-capture claim, use data with capture/session identifiers and hold out entire captures. The current release's single target capture per device does not permit such a within-device target-capture split.

## Existing raw-data census reused

The prior raw and prepared-data verification remains the authoritative census: N-BaIoT has 89 selected CSVs (about 8.14 GB), 115 predictors, 11 classes, 9 device proxies, and target support in all 9; CICIoT2023 has 309 selected per-attack shards (about 8.94 GB), one consistent 39-predictor header, 31 canonical classes, and 9 synthetic pseudo-domains. The CIC 39-versus-46 published feature discrepancy is documented and no features are fabricated. Evidence: `docs/.audit/raw-dataset-inventory-verification-20260926.json`, `docs/.audit/ciciot-raw-schema-verification-20260926.json`, and `docs/.audit/final-evidence.md`.

**Interpretation.** Counts make the planned sample-support census feasible, but do not establish independent clients, natural chronology, true out-of-domain behavior, or confirmatory method efficacy. CIC pseudo-domains are not external trust domains.

## Admission-rule probes

These probes call the shipped quorum and Krum functions, or they apply the published conformal finite-sample formula to the configured domain counts. They do not train a model and they are not confirmatory. Script and JSON: gitignored `docs/audit/pocs/admission_rule_poc.py` and `admission_rule_poc.json`. The completed nine-capture overlap POC was not rerun.

**Quorum.** Configured panel 3, required positives 2, Byzantine budget 1. `minimum_honest_positive_count(2, 1)` is 1. `reproduction_row_is_certified` accepts one dissent and rejects a lone positive. The same one-dissent panel fails if the required count is raised to the full panel. A unanimity rule would give the Byzantine verifier a veto. The shipped quorum does not.

**Krum regimes.** `select_krum_update` with five rows and `f_R=1`. A row at 50 against values 0, 0.1, 0.2, and 0.15 is not selected. The center value 4.5 among 0, 3, 6, and 9 is selected. Identity exclusion remains true for a source id outside that committee and false when the selected row's id is the source id. Identity exclusion and payload exclusion are different predicates. An equality veto was not added.

**Conformal floor.** For a loss bounded by 1, conformal risk control still pays `1/(n+1)` when every calibration loss is 0 (Angelopoulos et al., arXiv 2208.02814). At the configured minimum of 6 adequate final-gate domains that floor is about 0.143. At 8 non-source domains it is about 0.111. Alpha 0.05 and 0.10 sit below the floor, and the split-conformal rank fraction `ceil((n+1)(1-alpha))/n` is above 1. Alpha 0.20 is the first probed level a perfect calibrator can meet, and then only with a rank fraction of 1. A conformal final gate is not identifiable at the risk levels that would matter here.

**Nearest role rows, one capture.** `data/raw/N-BaIoT/Danmini_Doorbell/gafgyt_attacks/combo.csv` has 59,718 rows and 115 numeric columns. No non-numeric column and no identifier-like column name. Sixty-four reproduction-window queries were compared with every source-proposal row after per-feature scaling. The minimum squared distance was 12.43, the median of those minima was 28.32, and the exact-zero fraction was 0. This is not a nine-capture scan and it does not replace the earlier hash POC. It does not show a near-copy shortcut on this file for these queries.

**Scaler fit.** `outputs/preprocessing/features/nbaiot_scaler.json` records 320,000 training rows and 115 features. The fit predicate in `datasets/nbaiot/prepare.py` uses anchor-train rows whose class is not the target. Final-gate and report-test rows are not in that fit.

**Decision.** The probes support keeping the current quorum and the current Krum operator, and they support rejecting a conformal gate and a payload veto. They do not estimate malicious admission.

## Historical-subtraction probe

This probe is non-confirmatory. It does not train, and it is not a grid arm. Script and JSON: gitignored `docs/audit/pocs/unlearning_residual_poc.py` and `unlearning_residual_poc.json`.

The question is whether subtracting a retained source update from an average is a stronger admission rule than never putting that source identity in the synthesis inputs. Let `honest` be `(1, 0.5, -0.25)` and `source` be `(3, -2, 5)`. The aggregate is `honest + 0.2 * source`. Subtracting `0.05 * source` leaves a residual whose L2 is 0.9246621131896973, equal to the L2 of `(0.2 - 0.05) * source`. Subtracting the true weight `0.2` returns `honest`. Repeating that exact subtraction after scaling the source payload by 50 still returns `honest`.

Interpretation. FedEraser-style historical subtraction (Liu, Ma, Yang, Wang, and Liu, arXiv 2012.13891) matches identity exclusion only when the subtracted weight is the weight that entered a linear average. A wrong weight leaves a source component that grows with the payload. Identity exclusion does not. The candidate is `REJECTED` in `Scientific Decisions.md`. The result is not a malicious-admission estimate.
