# FedSIRA

FedSIRA introduces the Leave-Fault Geometric Median Certificate, a source-independent algorithm for admitting a post-reference capability under unreliable or Byzantine evidence. The proposal identifies the capability. The certificate gives the source production weight 0, scores every leave-`f` coalition of independent evidence by a lower-median utility and an upper-median harm, and sets the production update to the geometric median of those coalition means. The source-excluded admission lifecycle is the baseline in that comparison.

The specification is `docs/algorithms/leave-fault-geometric-median-certificate.md`. The execution protocol and the certificate statement are in `docs/Roadmap.md`. The candidate comparison and the claim boundaries are in `docs/audit/Scientific Decisions.md`. Malicious admission on the ordinary federated baselines and the certified ensemble still follows accepted-contributor ancestry: a compromised update counts only when the admitted checkpoint depends on it.

N-BaIoT devices are device-domain proxies. Role windows are controlled row-order replay of one capture per device and class. CICIoT2023 contributes synthetic label-conditioned pseudo-domains and a 39-feature representation. These partitions support the stated mechanism comparison. They do not establish organizational independence, natural post-deployment time, raw-traffic trigger realizability, formal privacy, or deployment readiness.

## Setup

```
uv sync
```

Requires the reference environment locked in `uv.lock` (Python 3.11.9, PyTorch 2.9.0, CUDA 12.8; see `docs/Roadmap.md` Section 20).

## Reproducibility

All scientific configuration is owned by `configs/fedsira.yaml`. Execution is deterministic: seeds, hashing, ordering, and runtime behavior are fixed by the roadmap and validated by `fedsira doctor` before any scientific command runs.

## CLI usage

```
fedsira doctor
fedsira preprocess ["N-BaIoT"|"CICIoT2023"] [--overwrite]
fedsira plan
fedsira smoke [--overwrite]
fedsira run <name> [--overwrite]
fedsira status
fedsira report [<name>] [--overwrite]
```
