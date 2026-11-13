---
name: standing-mark
description: Independent paid examination of claims and proposed agent actions, operated by Wheeler Hubbell Publishing. Use when an agent or its operator needs a signed, independently verifiable examination stating what submitted material establishes, what it does not establish, and what remains unknown. Covers discovery, invocation, payment boundaries, response interpretation and independent verification.
---

# Standing Mark

Standing Mark is an independent examination service operated by Wheeler Hubbell Publishing, Inc. A caller submits an exact claim or proposed action with its material; the service examines whether the material establishes the claim under stated bounds and returns a signed result. The service does not execute, authorize, pay or settle, and it is not a notary, a truth oracle or a generic evidence validator. Payment buys the examination, not a positive finding: a signed record that names what is not established is a delivered examination.

## Discovery (free)

- Live contract, the source of truth for schemas, payment terms and limits: `GET https://decisionintegrity.wheelerhubbellpublishing.com/v1/contract`
- Issuer Ed25519 public key: `GET https://decisionintegrity.wheelerhubbellpublishing.com/.well-known/whp-issuer.json`
- OpenAPI 3.1: `https://decisionintegrity.wheelerhubbellpublishing.com/openapi.json`
- Machine-readable discovery: `GET https://decisionintegrity.wheelerhubbellpublishing.com/.well-known/whp-standing.json`
- Free reproducible check (never requests a quote): clone this repository and run `python3 scripts/check_discovery.py`

## Invocation

1. Read the live contract first; treat it as authoritative over any copy, including this file. Its `input_schema` field is the authoritative list of the fields the evaluator reads.
2. `POST /v1/evaluate` with a JSON object in that input schema: the proposition as a string `claim` (or `subject`, or `object.id`), the examination material as a string `data`, plus `provenance.source`, `provenance.evidence` and an authority `warrant` as applicable. With no `data` string, the claim itself is the examined material (a recorded fallback). An object-valued `claim` is not a proposition and no field named `material` is read; a request with no readable proposition and no readable material is examined over zero bytes. An unpaid request returns HTTP 402 with `payment_required` carrying `quote_id`, `amount_units`, `pay_to` and `expires`.
3. Keep the exact request bytes unchanged. The quote ID is bound to the SHA-256 of those bytes; any change requires a new quote.

## Payment boundaries

- Scheme `WHP-BASE-USDC-FLAT-1`: exactly 1.00 USDC (`amount_units` 1000000, 6 decimals) on Base (`eip155:8453`). This scheme is not x402-exact and is not represented as x402.
- The caller authorizes and sends the on-chain transfer itself; the service never holds keys, signs transfers or pays. Each transaction hash is single-use.
- Retry the identical body with headers `X-WHP-Quote` and `X-WHP-Payment-Tx` after the transfer reaches the minimum confirmations in the contract.
- An unpaid quote expires on its own and consumes nothing.

## Response interpretation

- A signed result states what is established, what is not established and what remains unknown. `NOT_ESTABLISHED` with named gaps is a correctly delivered examination, not a failure.
- Result type `WHP-STANDING-MARK-v1`, Ed25519 signature over canonicalization `WHP-JCS-I1`.
- A signature establishes cryptographic validity only. It does not establish the substantive correctness of the claim or authority to act. The receiver applies its own question, object, scope, freshness and policy checks before relying on a result.

## Independent verification

- Online signature check: `POST /v1/verification` with the signed envelope and public key (signature only; it does not authenticate the key or establish object binding).
- Offline: `python3 verification/verify.py <envelope.json> <SPKI DER base64>` or `node verification/verify.js` with the same arguments, using the published issuer key. A free public test vector is at `verification/sample-test-key-envelope.json`.
- Source SDKs for Python and Node live in `sdk/`; a local stdio MCP adapter lives in `mcp/`. There is no hosted MCP endpoint and no published PyPI or npm package.

## Authority

This skill describes an examination interface. It grants no authority, manufactures no consent and executes no action. Retain the private evidence for an examination and distribute only an authorized, redacted example.
