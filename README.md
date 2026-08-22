# FedSIRA

FedSIRA is a federated scientific admission protocol study evaluating capability claims under Byzantine reproduction and verification. The full scientific, experimental, execution, reporting, and reproducibility specification lives in `docs/Roadmap.md` and is authoritative over this implementation.

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
fedsira report [<name>] [--overwrite]
```
