# Standing Mark quick-start and integration guide

Base URL: `https://decisionintegrity.wheelerhubbellpublishing.com`

Everything below is free except the paid examination retry in step 4. The live contract at `GET /v1/contract` is the source of truth; this guide describes it as of November 20, 2026.

## 0. Install and check the free path

```sh
git clone https://github.com/wheelerhubbell/standing-mark.git
cd standing-mark
python3 scripts/check_discovery.py
```

This checks live discovery, SDK key consistency and local test-vector signatures without calling `/v1/evaluate`. [MCP client setup](../mcp/README.md) and [independent verification commands](verification.md) are available separately. Old SDKs in the publishing-site repository are legacy material, not the current integration path.

## 1. Read the contract

```
GET /v1/contract
```

Returns the profile, the routes, the payment terms (protocol `x402-v2`, scheme `exact`, network `eip155:8453`, USDC asset, fixed price exactly 1.00 USDC, pay_to address, facilitator), the determinism rule, the signed result type and the published issuer key reference.

## 2. Pin the issuer key

```
GET /.well-known/whp-issuer.json
```

The key is Ed25519, SPKI DER base64. Its key id is the lowercase hex SHA-256 of the DER bytes (not of the base64 text). Recompute it locally and compare with `key_id_sha256` before trusting anything signed.

## 3. Request an examination

```
POST /v1/evaluate
Content-Type: application/json

{
  "claim": "The proposition to examine, as a string.",
  "data": "The supporting material the examination reads, as a string.",
  "provenance": {
    "source": "https://example.org/where-the-material-comes-from",
    "evidence": ["A verbatim statement from the material."]
  },
  "warrant": "Why the requested operation is warranted (required at RECOMMEND and above).",
  "requested_operation": "INFORM"
}
```

Submit the claim or proposed action with its supporting material in the accepted input schema. The evaluator reads the proposition from a string `claim` (aliases `text`, `prompt`, `content`, `statement`, `proposition`; otherwise a string `subject`, then `object.id`) and the examination material from `data` (string or object; a `material` field is mapped to `data`). A bare JSON string body is treated as the claim. When no `data` string is supplied, the claim itself is the examined material (an explicit, recorded fallback). `requested_operation` is taken as given: the gate keeps no fixed list and defaults to `INFORM`. A request with no readable proposition is refused `400 NOT_EXAMINABLE` before any payment movement, naming the missing objects. The authoritative field list is `input_schema` in the live contract at `GET /v1/contract` (mirrored in `openapi.json`). Submissions must be strict JSON under the service's canonical rule: safe integers only (no floats, no -0, no integers beyond ±2^53-1), no duplicate object keys, well-formed Unicode, at most 64 levels deep and 262144 bytes. See `docs/rejection-boundary.md`.

An unpaid request is answered `402 Payment Required` with x402 v2 terms: `accepts[0]` carries `scheme` (`exact`), `network` (`eip155:8453`), `asset` (USDC), `amount` (`1000000`, 6 decimals), `payTo`, `maxTimeoutSeconds` and `extra`; the same terms are mirrored in the `payment-required` response header. Unpaid requests consume nothing.

## 4. Pay and retry (the caller's decision)

Sign an EIP-3009 `transferWithAuthorization` for exactly `amount` of USDC on Base to `payTo` (fields `from`, `to`, `value`, `validAfter`, `validBefore`, `nonce`), then retry the identical request body with the x402 v2 envelope in the `payment-signature` (or `x-payment`) header:

```
payment-signature: {"x402Version": 2, "accepted": <the accepts entry from the 402 terms>, "payload": {"signature": "0x...", "authorization": {"from": "...", "to": "...", "value": "1000000", "validAfter": "...", "validBefore": "...", "nonce": "0x..."}}}
```

The facilitator verifies and settles; no customer ETH gas is required. The service returns the signed examination result with a `payment-response` header. A signed authorization settles at most once: a replay returns the delivered result, and a settled but undelivered purchase is re-delivered from its stored record, so no retry can double-charge. Payment buys the examination, not a positive finding: a result can be a Standing Mark (established) or a signed record naming what is not established. Both are correctly delivered examinations.

## 5. Verify the result

Server-side (signature only, per the contract's stated scope):

```
POST /v1/verification
{"envelope": <the signed result>, "public_key": "<SPKI DER base64>"}
```

Offline, independently: run `verification/verify.py` or `verification/verify.js` against the pinned issuer key. They recompute the key pin, check the protected header, re-canonicalize `{"protected": ..., "payload": ...}` under WHP-JCS-I1 and verify the Ed25519 signature. Test vectors are in `docs/test-vectors.md`.

## What verification does and does not establish

- A signed result establishes what the issuer signed.
- Signature verification establishes cryptographic validity, not the substantive correctness of the claim.
- Verification alone does not establish that a key is authoritative for a particular object, current standing, or policy acceptance. Binding an examination to your own question, operation and scope is a receiver-side check.
- An examination does not authorize, execute, pay or settle the proposed transaction.

## SDKs

- Python: `sdk/python/standing_mark.py` (standard library; offline verification needs `cryptography`).
- Node: `sdk/js/standing-mark.js` (standard library only).
- MCP: `mcp/standing_mark_mcp.py` presents the service as four tools to any MCP-capable agent. It is a client-side adapter: the service itself speaks HTTP.

## Keep reusable evidence

See [discovery-to-evidence loop](propagation-loop.md). Keep private payloads and payer identities out of public evidence. Publication and successful test calls are not evidence of external adoption.

For the full optional local-signature checks, install Node.js 18+ and the Python `cryptography` package. The discovery script reports SKIP for an unavailable signature runtime; the stdlib discovery and MCP checks still run.
