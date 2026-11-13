# Standing Mark — developer assets

Standing Mark is an independent examination service operated by Wheeler Hubbell Publishing, Inc. It examines claims and proposed actions and returns a signed result stating what is established and what is not. It does not execute, authorize, pay or settle.

Live service: https://decisionintegrity.wheelerhubbellpublishing.com

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

Payment buys an examination, not a positive finding. Results are signed (type `WHP-STANDING-MARK-v1`, Ed25519, canonicalization `WHP-JCS-I1`) and anyone can verify a signature against the published issuer key. Signature verification establishes cryptographic validity, not the substantive correctness of a claim.

The payment scheme is `WHP-BASE-USDC-QUOTE-1` (a price quote in USDC on Base, bound to the exact request bytes). It is not x402-exact and is not represented as x402.
