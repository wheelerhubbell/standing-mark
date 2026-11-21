---
name: standing-mark
description: Independent paid examination of claims and proposed agent actions, operated by Wheeler Hubbell Publishing. Use when an agent or its operator needs a signed, independently verifiable examination stating what submitted material establishes, what it does not establish, and what remains unknown. Covers discovery, invocation, payment boundaries, response interpretation and independent verification.
---

# Standing Mark

Standing Mark is an independent examination service operated by Wheeler Hubbell Publishing, Inc. A caller submits an exact claim or proposed action with its material; the service examines whether the material establishes the claim under stated bounds and returns a signed result. The service does not execute, authorize, pay or settle, and it is not a notary, a truth oracle or a generic evidence validator. Payment buys the examination, not a positive finding: a signed record that names what is not established is a delivered examination.

## Governing publications

- Decision Integrity Standard No. 001, Version 1.0: https://wheelerhubbellpublishing.com/publications/decision-integrity-standard-no-001-v1-0.html
- Receiving Boundary Rule No. 001, Version 1.0: https://wheelerhubbellpublishing.com/publications/receiving-boundary-rule-no-001-v1-0.html

The Standard defines the examination. The Standing Mark service operates the examination institution. The Receiving Boundary Rule is an adoptable instrument by which an independent receiving institution can require a verified examination before accepting designated consequential propositions; the receiving institution retains its own authority and responsibility.

## Discovery (free)

- Live contract, the source of truth for schemas, payment terms and limits: `GET https://api.wheelerhubbellpublishing.com/v1/contract`
- Issuer Ed25519 public key: `GET https://api.wheelerhubbellpublishing.com/.well-known/whp-issuer.json`
- OpenAPI 3.1: `https://api.wheelerhubbellpublishing.com/openapi.json`
- Machine-readable discovery: `GET https://api.wheelerhubbellpublishing.com/.well-known/whp-standing.json`
- Free reproducible check (never requests a quote): clone this repository and run `python3 scripts/check_discovery.py`

## Invocation

1. Read the live contract first; treat it as authoritative over any copy, including this file. Its `input_schema` field is the authoritative list of the fields the evaluator reads.
2. `POST /v1/evaluate` with a JSON object in that input schema: the proposition as a string `claim` (aliases `text`, `prompt`, `content`, `statement`, `proposition`; otherwise a string `subject`, then `object.id`), the examination material as a string or object `data` (a `material` field is mapped to `data`), plus `provenance.source`, `provenance.evidence` and an authority `warrant` as applicable. A bare JSON string body is treated as the claim. With no `data` string, the claim itself is the examined material (a recorded fallback). `requested_operation` is taken as given; the gate keeps no fixed list and defaults to `INFORM`. A request with no readable proposition is refused `400 NOT_EXAMINABLE` before any payment movement, naming the missing objects. An unpaid request returns HTTP 402 with x402 v2 payment terms (mirrored in the `payment-required` response header).
3. Keep the exact request bytes unchanged on retry; the payment authorization and the delivery record are bound to the request.

## Payment boundaries

- Scheme x402 v2 `exact`: exactly 1.00 USDC (`amount` 1000000, 6 decimals) on Base (`eip155:8453`) to the published `pay_to`.
- The caller signs an EIP-3009 `transferWithAuthorization`; the facilitator submits the transaction, so no customer ETH gas is required. The service never holds keys or initiates transfers. A signed authorization settles at most once.
- Retry the identical body with the x402 v2 envelope in the `payment-signature` (or `x-payment`) header: `{"x402Version": 2, "accepted": <the accepts entry from the 402 terms>, "payload": {"signature": "0x...", "authorization": {"from","to","value","validAfter","validBefore","nonce"}}}` (raw JSON, Base64 JSON or Base64URL JSON).
- A replayed authorization returns the delivered result; a settled but undelivered purchase is re-delivered from its stored record. No retry can double-charge.

## Response interpretation

- A signed result states what is established, what is not established and what remains unknown. `NOT_ESTABLISHED` with named gaps is a correctly delivered examination, not a failure.
- Result type `WHP-STANDING-MARK-v1`, Ed25519 signature over canonicalization `WHP-JCS-I1`.
- A signature establishes cryptographic validity only. It does not establish the substantive correctness of the claim or authority to act. The receiver applies its own question, object, scope, freshness and policy checks before relying on a result.

## Independent verification

- Online signature check: the live contract lists `POST /v1/verification` (signature only; it does not authenticate the key or establish object binding), but that route is not currently deployed (it returns 404, observed 2026-11-21). Use the offline verifier until the contract and the route agree.
- Offline: `python3 verification/verify.py <envelope.json> <SPKI DER base64>` or `node verification/verify.js` with the same arguments, using the published issuer key. A free public test vector is at `verification/sample-test-key-envelope.json`.
- Source SDKs for Python and Node live in `sdk/`; a local stdio MCP adapter lives in `mcp/`. There is no hosted MCP endpoint and no published PyPI package. An outdated npm package (`@wheelerhubbell/whp-standing-client`, 0.2.4, published 2026-10-17) predates the November 2026 payment migration and is not compatible with the live service; use the source SDKs here instead.

## Authority

This skill describes an examination interface. It grants no authority, manufactures no consent and executes no action. Retain the private evidence for an examination and distribute only an authorized, redacted example.
