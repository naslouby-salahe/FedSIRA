# Enum audit

The audit found that the 530 TODO annotations did not identify actual enum migrations. Closed domains already use existing `StrEnum` types; schema tokens, paths, filenames, digests, user-facing labels, and serialization keys are not uniformly closed domains and must remain boundary text.

Existing closed-domain enums in `src/fedsira/domain/enums.py` include lifecycle, execution, artifact, and scientific-policy concepts. They remain the appropriate internal representations. Any repository-wide raw-string occurrences outside the changed scope require semantic review before conversion; a mechanical migration would be an unrelated redesign.

All 530 annotations have been removed after that classification. No enum-to-string-to-enum adapters or compatibility wrappers were added.
