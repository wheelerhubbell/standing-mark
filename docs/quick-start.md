# Standing Mark quick-start and integration guide

Base URL: `https://decisionintegrity.wheelerhubbellpublishing.com`

Everything below is free except the paid examination retry in step 4. The live contract at `GET /v1/contract` is the source of truth; this guide describes it as of November 13, 2026.

## 1. Read the contract

```
GET /v1/contract
```

Returns the profile, the four routes, the payment terms (scheme `WHP-BASE-USDC-QUOTE-1`, network `eip155:8453`, USDC asset, price range 1.000001 to 1.009999 USDC, pay_to address, minimum 5 confirmations), the determinism rule, the signed result type and the published issuer key reference.

## 2. Pin the issuer key

```
GET /.well-known/whp-issuer.json
```

The key is Ed25519, SPKI DER base64. Its key id is the lowercase hex SHA-256 of the DER bytes (not of the base64 text). Recompute it locally and compare with `key_id_sha256` before trusting anything signed.

## 3. Request an examination

```
POST /v1/evaluate
Content-Type: application/json

{"claim": {...}, "material": {...}}
```

Submit the claim or proposed action with its supporting material. Submissions must be strict JSON under the service's canonical rule: safe integers only (no floats, no -0, no integers beyond ±2^53-1), no duplicate object keys, well-formed Unicode, at most 64 levels deep and 262144 bytes. See `docs/rejection-boundary.md`.

An unpaid request is answered `402 PAYMENT_REQUIRED` with a quote under `payment_required`: `quote_id`, `amount_units` (USDC atomic units, 6 decimals), `pay_to`, `expires` (epoch seconds). The quote is bound to the exact request bytes; changing one byte produces a different quote. Quotes self-expire; an unpaid quote consumes nothing.

## 4. Pay and retry (the caller's decision)

Pay exactly `amount_units` of USDC on Base to `pay_to`, wait for at least 5 confirmations, then retry the identical request body with headers:

```
X-WHP-Quote: <quote_id>
X-WHP-Payment-Tx: <Base transaction hash>
```

The service returns the signed examination result. Payment buys the examination, not a positive finding: a result can be a Standing Mark (established) or a signed record naming what is not established. Both are correctly delivered examinations.

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
