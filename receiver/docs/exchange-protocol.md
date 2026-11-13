# Decision Integrity Exchange Protocol (v1, draft)

The protocol connects issuance, reception, preservation and verification without letting any step change an earlier object.

## Identity

Every object has an id: `sha256:` followed by the lowercase hex SHA-256 of its WHP-JCS-I1 canonical bytes. Equal content gives equal id. A changed byte gives a different id.

## Objects and events

| Kind | What it is | May follow |
|---|---|---|
| `request` | The submitted question and material | none |
| `mark` | The signed result issued for a request | `request` |
| `reception_event` | A receiver's record that it received a Mark | `mark` |
| `receipt` | A Standing Receipt for that reception | `reception_event` |
| `receiver_response` | The receiver's own response (acknowledgment, acceptance, rejection, dispute) | `receipt`, `reception_event`, `mark` |

Each record is `{kind, object_id, prior_ids, object}`. `prior_ids` point to earlier records only.

## Rules

1. No record is edited. A correction is a new record that links to the old one.
2. A verifier recomputes every `object_id` from the carried object. A mismatch is `OBJECT_ALTERED`.
3. Every non-request record links to an earlier record (`UNLINKED`, `PRIOR_MISSING`).
4. Links must follow the table (`ILLEGAL_LINK`). A receipt cannot link straight to a request.
5. Reception preserves the original Mark bytes exactly as received.
6. The separation stands: examination is not issuance, issuance is not reception, receipt is not acceptance, acceptance is not authorization. `receiver_response` is the only place a receiver's acceptance or rejection lives, and it is the receiver's own statement.

Reference implementation: `standing_receiver/exchange.py`. Vectors: `conformance/vectors.json` (`chain`).
