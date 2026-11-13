# Standing Receipt specification (v1, draft)

A Standing Receipt is a distinct record of an authenticated reception event for one Standing Mark. It is its own object with its own evidence. It never alters, wraps or replaces the Mark.

## Authority

Wheeler Hubbell Publishing is authoritative for the reception record it issues and the evidence behind it. External organizations remain authoritative for what they understand, accept, reject, dispute or do.

## Payload (type `WHP-STANDING-RECEIPT-v1`)

| Field | Meaning |
|---|---|
| `type` | `WHP-STANDING-RECEIPT-v1` |
| `issuing_authority` | `Wheeler Hubbell Publishing` |
| `mark_ref` | `mark_id`, `envelope_sha256` (SHA-256 of the Mark envelope's WHP-JCS-I1 bytes), `issuer_key_id` |
| `recipient` | `label`, and `authenticated_by` (how the recipient was authenticated, or null) |
| `reception_event` | `event_id`, `received_at`, `state` (`RECEIVED_VERIFIED` or `RECEIVED_WITH_PROBLEMS`) |
| `correspondence` | `received_object_sha256` and `issued_object_check` (`PASS`, `FAIL` or `NOT_CHECKED`) |
| `verification_evidence` | the receiver checks and problems, and the kit version |
| `establishes` | only `AUTHENTICATED_RECEPTION_EVENT` and `CORRESPONDENCE_OF_RECEIVED_TO_ISSUED_OBJECT` |
| `does_not_establish` | must include `RECEIVER_UNDERSTANDING`, `RECEIVER_AGREEMENT`, `RECEIVER_ACCEPTANCE`, `AUTHORIZATION_OF_ANY_ACTION`, `SUBSTANTIVE_CORRECTNESS_OF_THE_EXAMINATION` |
| `acknowledgment` | optional. A receiver's own response, carried as a separate object (`SEPARATE_RECEIVER_RESPONSE`). It is the receiver's statement, not an acceptance established by the receipt |

The envelope is `{protected, payload, signature}` with Ed25519 over the WHP-JCS-I1 bytes of `{"protected", "payload"}`, the same profile as a Mark. The protected header `type` is `WHP-STANDING-RECEIPT-v1`.

## Verification rules

A verifier must reject a receipt whose signature fails against the pinned key, whose payload type is wrong, whose `does_not_establish` omits a required item, whose `establishes` contains anything outside the two permitted values, or that carries a field claiming acceptance, authorization, approval, agreement, allow, deny or decision outside the separate `acknowledgment`. If the Mark is available, `mark_ref.envelope_sha256` and `correspondence.received_object_sha256` must equal its hash.

## Status

Implemented in this kit: payload construction from a reception result, and offline verification. Not built: issuance of a signed receipt by Wheeler Hubbell Publishing. That needs a new service route using the issuer key, which changes live behavior and is not authorized.
