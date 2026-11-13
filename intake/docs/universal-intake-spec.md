# Universal Intake and Interpretation: specification (WHP-INTAKE-1.0.0, draft)

Wheeler Hubbell Publishing. Additive layer upstream of the examination engine. The engine, its findings, the signed Mark and the flat 1.00 USDC payment are unchanged.

## 1. Position

Intake receives what the caller has, keeps it, reads it by deterministic rules, and hands the engine the flat shape it already reads (`claim`, `data`, `source`, `provenance`, `warrant`, `requested_operation`). It never examines, never grades, never promotes. Reception does not establish correctness; interpretation does not establish truth; extraction does not establish authenticity; normalization does not establish authority.

## 2. The five layers (never merged)

| Layer | Contents | Is evidence? |
|---|---|---|
| source | original bytes, sha256, media type, caller fields kept verbatim | it is the submission |
| extracted | text lifted verbatim from the source, each with a pointer (JSON pointer or line) and a rule id | yes, as the caller's own material |
| interpreted | which part is the proposition, which is material, with the rule used | no, a reading |
| inferred | anything the caller did not say (for example the default operation INFORM) | never |
| examined | the engine's result, bound by the Mark | the engine's conclusion |

## 3. Reception

Accepted: plain text; labeled text (`Claim:`, `Evidence:`, `Source:`, `Warrant:`, `Operation:`); JSON in the engine shape, the previously documented nested shape (`claim.statement`, `material.*`), flat JSON with synonym keys (`proposition`, `question`, `statement`, `evidence`, `text`, `content`, `prompt`, `input`, `url`); lists and `items`/`files[].text` packages; machine-agent payloads as JSON. The original is retained as an immutable object identified by its sha256.

Refused with the original preserved (`NOT_EXAMINABLE`): empty, over 262144 bytes, not UTF-8, malformed JSON (including NaN), duplicate keys, nesting over 64, scalar JSON, non-text proposition, unsupported requested operation.

## 4. Interpretation rules (all deterministic, versioned by WHP-INTAKE-1.0.0)

R-JSON-CLAIM-STRING, R-JSON-CLAIM-NESTED, R-JSON-CLAIM-LIST, R-JSON-PROPOSITION-FALLBACK (no claim field: first string among data, text, prompt, content, input; examinable with limits), R-SUBMISSION-V1-PASSTHROUGH (an engine-native WHP-STANDING-SUBMISSION-v1 object is passed through unchanged), R-MULTI-PROPOSITION, R-JSON-SOURCE, R-JSON-WARRANT, R-TEXT-LABELS, R-TEXT-SINGLE-STATEMENT, R-TEXT-DOCUMENT, R-PKG-LIST, R-MATERIAL. Nested material is flattened to verbatim `leaf-name: value` lines with pointers kept. No semantic model is used. A future semantic interpreter may add rules only as `interpreted` or `inferred` output with its own rule id and version; it may not write to `extracted`.

Never done: inventing a proposition; choosing a candidate proposition (candidates are listed with `selected: false`); manufacturing a source or warrant; resolving a contradiction; reading caller-supplied standing fields (`established_fact`, `source_grade`, `epistemic_status`, `attestation`, `signature`, `verified`, `authorized`, `outcome`, `permitted_operations`, and similar). Those are recorded under `source.caller_fields` and `preserved.ignored_caller_assertions`, and never reach the canonical submission. Text inside material that addresses the system is material.

Contradictions (same field name, different values across submitted items) and alternative proposition fields are preserved and disclosed. Several explicit propositions become several separate examinations.

## 5. Examinability and the payment gate

| Level | Meaning | Quote gate |
|---|---|---|
| EXAMINABLE | proposition and material present | quote allowed |
| EXAMINABLE_WITH_LIMITS | proposition only; the engine examines the proposition text alone (fallback) | quote only with the disclosure shown and the caller's informed choice |
| NOT_EXAMINABLE | no proposition, or a refusal issue | no quote; missing items listed; original preserved |

A caller is therefore not charged for an examination the service already knows it cannot perform, without disclosure and choice. The price, scheme and payment steps are unchanged. Whether the gate runs at the 402 stage or as a free pre-check route is a deployment decision (see report).

## 6. Intake Record and result binding

The record carries `intake_version`, the five layers, `canonical_trace` (each canonical field points to an extracted item), `canonical_submissions`, `canonical_sha256`, `does_not_establish` and `record_sha256`. Same input gives the same record. Binding facts verified in service source: `submitted_bytes_sha256` is the SHA-256 of the WHP-JCS-I1 canonical parsed payload (bare strings hashed without quotes), not the raw HTTP body; the quote's `payload_sha` is the raw-body hash; `examined_material.sha256` binds what the engine examined. Intake adds nothing to the signed Mark unless a separate `source_object` digest is authorized (decision 2 in the report).

## 7. Result presentation

A response should state: what was submitted (source sha256), what was examined (examined_material), the transformations (interpreted rule ids), remaining limits (`disclosures`, engine `limitations`), what the Mark establishes and does not (the Mark's own integration rule plus `does_not_establish`).
