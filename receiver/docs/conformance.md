# Independent verification and conformance

`conformance/vectors.json` holds 29 cases generated from the public RFC 8032 TEST 1 key. Ed25519 signing is deterministic, so regenerating them (`conformance/generate_vectors.py`) yields identical bytes. The objects are synthetic test fixtures, not issuer statements.

| Group | What a conforming implementation must reproduce |
|---|---|
| `jcs` | WHP-JCS-I1 canonical text for each input |
| `object_id` | `sha256:` ids of canonical bytes |
| `signature` | valid, tampered, wrong pin, wrong type, incomplete: exact `valid` and `reason` |
| `request` | accepted request bytes and material byte count; refusal codes for object claim, empty material, missing claim |
| `evidence` | `mark_verified`, stated outcome, substantive-examination status, freshness, problems |
| `receipt` | valid, claims acceptance, wrong mark: exact problems |
| `binding` | `submitted_bytes_sha256` equals SHA-256 of the WHP-JCS-I1 canonical parsed payload (or the string itself for a bare-string body), never the raw HTTP body hash |
| `chain` | valid, altered, illegal link: exact problems |

Two implementations share no code and pass all cases: the Python kit (`conformance/run.py`) and a Node.js verifier using only built-ins (`conformance/run.js`). A third implementation passes by running the same vectors.

## Limits of this suite

It proves the kit's behavior on synthetic fixtures. It does not prove behavior against a live result from the service, which is assumed to follow the published result format. The first authorized live result should be added as a vector.
