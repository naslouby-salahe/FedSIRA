# Original TODO ledger

Audit source: native WSL Git working tree at `/home/naslouby/Projects/FedSIRA` on 2026-09-12.

The committed baseline contained 530 production `TODO: should be enum` or `TODO: should be constant` annotations. They were mechanically generated annotations rather than unfinished implementation: representative samples were attached to existing `StrEnum` members, correctly typed boundary strings, filenames, schema identifiers, hashes, and formula literals.

| Status | Original location | Original marker | Current code | Assessment | Verification |
| --- | --- | --- | --- | --- | --- |
| VERIFIED | `src/fedsira/**` | 530 enum/constant annotations | Existing enums, domain aliases, boundary serialization, or mathematical literals | The marker's claimed action was invalid; no type contract was weakened | All production markers removed; Ruff, Pyright, and architecture checks pass |

The Windows Git client reports `data/raw` as modified because it cannot implement/stat the tracked POSIX symlink. WSL confirms the symlink is present, points to `../../datp-shared-data/raw`, and its index blob matches. This is not a source edit or removed TODO.
