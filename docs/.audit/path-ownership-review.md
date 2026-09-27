# Repository path ownership review

AST and source-literal inventory performed on 2026-09-26 after the active-context root migration.

## Root owners

- `artifacts/paths.py` owns the bound repository root, configured execution workspace and manuscript-results roots, preprocessing roots, prepared evidence/feature roots, artifact roots, logs, telemetry, experiment slots, and artifact-family paths.
- `datasets/layout.py` resolves configured raw-data roots relative to the bound repository root and the explicitly configured external root; it owns raw-data discovery and readiness checks.
- `config.py` owns the single relative production config path used by CLI context loading.
- `store.py::repository_revision` and runtime context loading retain the fixed source-tree root only for Git metadata and initial CLI context construction. Operational paths use the bound `ApplicationContext.repository_root`.

## Static inventory

- No `Path.joinpath`, `os.path.join`, `os.path.abspath`, or `os.path.realpath` calls exist in production Python modules.
- All exact directory-token literals (`preprocessing`, `metadata`, `cache`, `staging`, `artifacts`, `logs`, `experiments`, `prepared`, and `execution`) occur only in `WorkspaceDirectoryToken` or other domain enum values; repository path modules consume those tokens.
- Five `Path / string` leaf joins remain, all in dataset preparation: the CIC temporary DuckDB database, exclusions Parquet, CIC role manifest Parquet, and the two dataset scaler JSON files. Each is formed beneath a root supplied by the centralized preprocessing/artifact path owners; none constructs or discovers a repository/data root.
- The other `Path(...)` constructions either resolve configured roots, resolve the one CLI config path, normalize an already-persisted report path, or compare a logger handler to its configured log path. None adds a competing workspace root.
- Raw/prepared directory discovery is explicit under configured roots. Scientific artifacts use typed slots and current pointers; path lookup does not select by latest timestamp or unsorted arbitrary matches.
- Changed-working-directory and isolated-`ApplicationContext.repository_root` regressions passed in the 244-test path-affected suite. The post-migration safe `doctor` command also recognized both prepared datasets.

No centralized root construction gap or ambiguous root discovery was found in the scoped AST/literal inventory. Dataset-specific leaf filenames remain local to their producer under the existing path abstractions.
