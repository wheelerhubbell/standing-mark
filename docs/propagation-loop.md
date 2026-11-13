# Discovery-to-evidence loop

1. Discovery: enter through the company developer page, public repository, local MCP instructions or OpenAPI document.
2. Contract: read the live contract and issuer document at time of use. Record the versions and key pin.
3. Integration: install source SDK or local MCP adapter; run the free discovery/local-vector check.
4. Examination: save exact request bytes; obtain a quote only when ready; the caller authorizes and sends the exact USDC amount, then retries identical bytes with the quote and transaction hash. A quote is not a purchase.
5. Independent verification: check the signature locally against the expected key, then apply receiver-side object, question, scope, freshness and policy checks.
6. Evidence: retain original responses and verification output privately. Record test coverage, exclusions and redaction authority.
7. Further distribution: share only a permitted, redacted reproducible example with observed URLs and limitations. No payer names, internal strings, secrets or unsupported adoption claims.

## Evidence register fields

Use one row per destination: destination, fit, mechanism, required materials, authorized scope, source URL, placement URL, checked-at timestamp, state, caveat and next gate.

States are independent: VERIFIED means a source was inspected; PUBLISHED means publicly retrievable; TESTED means specified checks ran; SUBMITTED means delivered for review; ACCEPTED requires the destination's acceptance evidence; NOT ESTABLISHED names missing evidence or a gate. A submitted pull request is not an accepted listing. A source-install MCP adapter is not a hosted MCP endpoint. An A2A description is not a native A2A integration. An HTTP 402 response is not proof of x402 compatibility.

Count owned publications, third-party submissions, accepted listings, tested integration surfaces, independently evidenced external integrations, completed paid examinations and received revenue separately. Never infer users, adoption or revenue from publication counts.
