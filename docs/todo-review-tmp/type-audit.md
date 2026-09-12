# Type audit

## Scope and conclusion

There are no changed APIs in the current native working tree, so no type-contract migration is pending. Existing domain types and enums were inventoried from `src/fedsira/domain/types.py` and `src/fedsira/domain/enums.py` before deciding whether any new types were needed. None were introduced.

| Type/Alias family | Semantic meaning | Underlying representation | Current usages | Valid? | Action |
| --- | --- | --- | --- | --- | --- |
| Domain models | structured domain values | frozen Pydantic models | domain/workflow boundaries | Yes | Preserve |
| Tensor domain models | tensor-bearing structures | Pydantic models | learning/evaluation | Yes | Preserve |
| Enumerations | closed domain identities and lifecycle states | `Enum`/`StrEnum` classes | domain and workflows | Yes | Preserve |

No primitive leak was introduced by an uncommitted change, and no aliases were changed or added.

## Pre-existing baseline finding

The broader discovery scan found 585 marker matches in `src` and `tests`, including 530 `TODO: should be enum` comments in `src`. `git blame` shows representative comments were introduced by committed revisions `73199ebb` and `4bae1643`, not the current working tree. This is substantial committed technical debt, outside the forensic-diff scope; it is not safe to mechanically convert all strings because several are serialization, filesystem, display, or external-library boundary values.
