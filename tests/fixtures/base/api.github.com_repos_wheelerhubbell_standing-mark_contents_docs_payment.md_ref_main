# The payment mechanism: x402 v2 (exact)

The live contract at `GET /v1/contract` is authoritative. Summary as of November 20, 2026:

- Protocol: `x402-v2`, scheme `exact`.
- Network: `eip155:8453` (Base). Asset: USDC `0x833589fcd6edb6e08f4c7c32d4f71b54bda02913`, 6 decimals.
- Price: exactly 1.00 USDC per examination (`amount` 1000000, exact match).
- Facilitator: `https://facilitator.payai.network`. The customer signs; the facilitator submits the transaction, so no customer ETH gas is required.

## Request binding

`POST /v1/evaluate` without payment returns 402 with the x402 v2 terms (`accepts[0]`: scheme, network, asset, amount, payTo, maxTimeoutSeconds, extra), mirrored in the `payment-required` response header. To complete, sign an EIP-3009 `transferWithAuthorization` (`from`, `to`, `value`, `validAfter`, `validBefore`, `nonce`) and retry the identical body with the envelope `{"x402Version": 2, "accepted": <the accepts entry>, "payload": {"signature": "0x...", "authorization": {...}}}` in the `payment-signature` (or `x-payment`) header (raw JSON, Base64 JSON or Base64URL JSON). The service verifies then settles through the facilitator and returns the signed result with a `payment-response` header. A signed EIP-3009 authorization settles at most once and the facilitator `/settle` is idempotent for an identical body, so a retry cannot double-charge. Delivery state is stored by authorization nonce: a replayed authorization returns the delivered result, and a settled but undelivered purchase is re-delivered from its stored record.

## Economic rule

Payment compensates the examination work regardless of outcome: a signed record that names what is not established is a delivered examination, not a failed purchase. One payment issues at most one signed result.

## Retired scheme

The pre-2026-11-16 scheme `WHP-BASE-USDC-FLAT-1` (caller-sent transfer, `X-WHP-Quote` and `X-WHP-Payment-Tx` headers) is retired and is not accepted by the live service.
