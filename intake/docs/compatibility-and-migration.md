# Compatibility and migration

Verified by tests in `intake/tests/test_intake.py` (local; the PHP engine was not run by this layer).

| Existing caller | Result |
|---|---|
| Engine shape (`claim` string, `data` string, `source`, `warrant`, `requested_operation`) | canonical output equals the input fields; test `test_existing_engine_shape_passes_through_unchanged` |
| Previously documented nested shape (the earlier published nested request) | now yields a proposition and material instead of zero bytes; test `test_earlier_nested_request_shape_is_now_examinable_not_empty` |
| Bare string / array bodies the door accepts today | a lone statement is a proposition with limits; unlabeled multi-line text is material with no proposition and is NOT_EXAMINABLE |
| Callers whose request is already valid | unchanged at the engine, because intake would hand the engine the same flat fields |

Behavior differences to disclose: (1) submissions the engine accepts today but intake rates NOT_EXAMINABLE (unlabeled document with no proposition) would get no quote instead of an empty examination, by design; (2) `requested_operation` is no longer regex-guessed: absent means INFORM, labeled as inferred; (3) the engine's own text-field fallbacks (`text`, `prompt`, `content`, `input`, `data.claim|summary`) are treated as material or proposition per the rules above, not as hidden proposition sources.

Migration: ship behind a default-OFF flag; shadow-compare intake output against the engine's current normalization on a corpus before enabling; enable one flag at a time on the owner's word. Nothing in this repository enables anything.
