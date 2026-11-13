# Submission rejection boundary

The service canonicalizes submissions under WHP-JCS-I1. WHP-JCS-I1 admits null, booleans, well-formed Unicode strings, arrays, objects, and safe integers in [-9007199254740991, 9007199254740991]. The following are rejected before ordinary JSON decoding can discard their identity:

| Rejected input | Reason |
|---|---|
| Floating-point tokens (`0.5`) | not a safe integer (`INTEGER_TOKEN_REQUIRED`) |
| Negative zero (`-0`) | not a safe integer (`INTEGER_TOKEN_REQUIRED`) |
| Integers beyond ±2^53-1 | unsafe (`INTEGER_REQUIRED`) |
| Duplicate object keys | ambiguous (`DUPLICATE_JSON_KEY`) |
| Unpaired surrogates | not well-formed Unicode (fails closed) |

Depth limit 64; intake text cap 262144 bytes; UTF-8 without BOM. Object member names sort by UTF-16 code units; strings use ECMAScript JSON escaping, preserving non-ASCII and U+2028/U+2029 literally; arrays preserve order; no whitespace is inserted.

These rejections are the contract working as specified, not a compatibility gap: a signature is meaningful only over bytes whose meaning is unique. A historical Node implementation accepted five such inputs (the five cases above); the current service refuses them, and the refusal is the conforming behavior.

Practical guidance: send integers for amounts (atomic units, not decimal floats), keep object keys unique, and submit valid UTF-8.
