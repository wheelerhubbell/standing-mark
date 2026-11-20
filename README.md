# Standing Mark developer assets

Standing Mark is an independent examination service operated by Wheeler Hubbell Publishing, Inc. It examines claims and proposed actions and returns a signed result stating what is established and what is not. It does not execute, authorize, pay or settle.

[Company website](https://wheelerhubbellpublishing.com) | [Developer onboarding](https://wheelerhubbellpublishing.com/developers.html) | [Live OpenAPI](https://decisionintegrity.wheelerhubbellpublishing.com/openapi.json) | [Quick-start](docs/quick-start.md) | [Independent verification](docs/verification.md)

Live service: https://decisionintegrity.wheelerhubbellpublishing.com

Start with the quick-start, install a source SDK or the [local MCP adapter](mcp/README.md), and run `python3 scripts/check_discovery.py`. That free check never requests an examination quote. The [evidence loop](docs/propagation-loop.md) explains how to retain a result and reuse a permitted integration example.

- Live contract (source of truth): `GET /v1/contract`
- Discovery: `GET /.well-known/whp-standing.json`
- Issuer key: `GET /.well-known/whp-issuer.json`
- Health: `GET /health`

This repository holds the public developer assets for the service:

| Asset | Path |
|---|---|
| OpenAPI 3.1 specification | `openapi.json` |
| Postman collection | `postman/standing-mark.postman_collection.json` |
| Quick-start and integration guide | `docs/quick-start.md` |
| Payment mechanism | `docs/payment.md` |
| Signing and verification test vectors | `docs/test-vectors.md`, `verification/` |
| Independent offline verifiers | `verification/verify.py`, `verification/verify.js` |
| Python SDK | `sdk/python/` |
| JavaScript (Node) SDK | `sdk/js/` |
| MCP adapter (stdio, client-side) | `mcp/` |
| A2A agent card | `a2a/agent-card.json` |
| Reproducible demonstration | `demo/standing_mark_demo.py` |
| Submission rejection boundary | `docs/rejection-boundary.md` |
| Standing Receiving Kit 0.1.1 (receiver, receipt record, exchange protocol, adapters) | `receiver/` |
| Universal Intake reference implementation, Python and PHP (WHP-INTAKE-1.2.0; the live door runs this intake) | `intake/` |

Payment buys an examination, not a positive finding. Results are signed (type `WHP-STANDING-MARK-v1`, Ed25519, canonicalization `WHP-JCS-I1`) and anyone can verify a signature against the published issuer key. Signature verification establishes cryptographic validity, not the substantive correctness of a claim.

The payment scheme is x402 v2 (`exact`): exactly 1.00 USDC on Base per examination. An unpaid request returns HTTP 402 with the x402 v2 terms (mirrored in the `payment-required` header); the caller signs an EIP-3009 `transferWithAuthorization` to the published `pay_to` address and retries the identical body with the envelope in the `payment-signature` (or `x-payment`) header. The facilitator submits the transaction, so no customer ETH gas is required. A signed authorization settles at most once and a replay returns the delivered result without a second charge.

The A2A card is descriptive only: the service does not implement native A2A transport. The MCP adapter installs from source; no hosted MCP endpoint or published PyPI package is claimed.
