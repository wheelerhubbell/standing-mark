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
- Server-side: `POST /v1/verification` with `verification/verification-request-example.json`. Expected: HTTP 200, `"valid": true`, `recordSha256` `92f81fa2c020bb904a125bfd38eebfe1f150af373fb3fd38784a1615db89729a`.
- Tamper check: change any payload byte; expected: `"valid": false` with `Ed25519 signature verification failed over WHP-JCS-I1 canonical payload`.

## Vector 3 — live quote shape

An unpaid `POST /v1/evaluate` returns HTTP 402 with `error` `PAYMENT_REQUIRED` and `payment_required` carrying `scheme` (`WHP-BASE-USDC-QUOTE-1`), `network` (`eip155:8453`), `asset`, `pay_to`, `price_floor_units` (1000000), `decimals` (6), `min_confirmations` (5), `quote_id`, `amount_units` (1000001-1009999) and `expires` (epoch seconds). Observed November 13, 2026: amounts 1001125-1008482 across four requests. Unpaid quotes self-expire.

## Reproducing

`demo/standing_mark_demo.py` runs vectors 1 and 3 live and vector 2 offline, printing what each step establishes and what it does not.
