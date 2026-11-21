# Signing and verification test vectors

Signed results are type `WHP-STANDING-MARK-v1`: Ed25519 over the WHP-JCS-I1 canonical bytes of `{"protected": ..., "payload": ...}`. The public key is SPKI DER base64; the key id is the lowercase hex SHA-256 of the DER bytes. Signing bytes are signed directly, not hashed first. Signatures are standard base64 of 64 bytes.

## Vector 1 — issuer key pin

- Published key (SPKI DER base64): `MCowBQYDK2VwAyEAcpFVUj6xDgsUsKJK2r2rLk6R+te2lghdHE8jvjl9SBk=`
- Expected key id: `dc872cabbbb942860cb2c4ac97a2a514245e54d69aa8515e80a7ec634c67076f`
- Procedure: base64-decode, SHA-256 the DER bytes, hex-encode, compare.
- Source: `GET /.well-known/whp-issuer.json` (also named in `GET /v1/contract`).

## Vector 2 — signed envelope, public test key

`verification/sample-test-key-envelope.json` is a signed envelope made with the published RFC 8032 TEST 1 key (key id `06e3fd8fda29bb60ab59557de61edb0aecdb231134be30e75b455f8e1b792fa9`). It is test material, not an issuer statement.

- Offline: `python3 verification/verify.py verification/sample-test-key-envelope.json MCowBQYDK2VwAyEA11qYAYKxCrfVS/7TyWQHOg7hcvPapiMlrwIaaPcHURo=` or the same arguments to `node verification/verify.js`. Expected: `Ed25519 signature: VALID`.
- Server-side: the live contract lists `POST /v1/verification` for a signature-only check. That route is not currently deployed (it returns 404, observed 2026-11-21); use the offline verifier above until the contract and the route agree.
- Tamper check: change any payload byte; expected: `"valid": false` with `Ed25519 signature verification failed over WHP-JCS-I1 canonical payload`.

## Vector 3 — live 402 terms shape

An unpaid `POST /v1/evaluate` returns HTTP 402 with an x402 v2 body (observed live 2026-11-21): `x402Version` `2`, `error` `Payment required`, a `resource` object naming the door URL, and `accepts` carrying one entry with `scheme` `exact`, `network` `eip155:8453`, `asset` `0x833589fcd6edb6e08f4c7c32d4f71b54bda02913` (USDC on Base), `amount` `"1000000"` (exactly 1.00 USDC), `payTo` `0x1050eddd8282623b0c263ed6bdbd42370bbc28d3`, `maxTimeoutSeconds` `300` and `extra.assetTransferMethod` `eip3009`. The same terms are mirrored in the `payment-required` response header. The caller signs an EIP-3009 `transferWithAuthorization` for exactly those terms and retries the identical body with the x402 v2 envelope in the `payment-signature` (or `x-payment`) header; the facilitator settles, and no customer ETH gas is required.

## Reproducing

`demo/standing_mark_demo.py` runs vectors 1 and 3 live and vector 2 offline, printing what each step establishes and what it does not.
