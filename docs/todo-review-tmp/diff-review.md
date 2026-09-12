# Diff review

## Inventory

| View | Unstaged | Staged | Finding |
| --- | --- | --- | --- |
| Native WSL Git | TODO-remediation edits | none | Production TODO comments removed; focused cohesive module extractions added |
| Windows Git over `\\wsl.localhost` | `data/raw` reported modified; `CLAUDE.md` untracked | none | Symlink interoperability false positive; `CLAUDE.md` is globally ignored in WSL |

## Deletion classification

The removed source text is exclusively invalid TODO comments and cohesive code moved from `experiments/handlers.py` and `reporting/figures.py` into dedicated modules. No behavior-bearing code was deleted.

`data/raw` is a tracked symlink rather than deleted code. Native inspection verified it exists and resolves; no remediation is appropriate.
