# Independent verification

A signature establishes which key signed an exact object. It does not establish the substantive correctness of a finding, authority to act, or that the object answers the receiver's question.

## Verify an actual result

Save the signed envelope as `signed_result.json`. Keep the original response separately. The verifier expects the envelope object with `protected`, `payload` and `signature`, not an outer HTTP wrapper.

```sh
python3 -m pip install cryptography
python3 verification/verify.py signed_result.json
# Alternative: Node.js, no third-party dependencies
node verification/verify.js signed_result.json
```

By default, each independent verifier fetches the public issuer document over HTTPS, recomputes SHA-256 of the DER key and compares it with `key_id_sha256`, checks the protected header, re-canonicalizes the protected object and payload, then verifies Ed25519 directly over those bytes. The signature calculation is local, although default key discovery uses the network. For fully offline verification, provide the expected SPKI DER base64 key as the second argument from a separately trusted key record.

The current key is published at https://decisionintegrity.wheelerhubbellpublishing.com/.well-known/whp-issuer.json . Fetching a key and its hash together establishes consistency, not an independent identity binding. Receivers should record and approve the expected key through their own trust process and define rotation/revocation handling. The issuer document currently provides no separate revocation URL.

## Free reproducible test, no examination purchase

```sh
python3 verification/verify.py verification/sample-test-key-envelope.json 'MCowBQYDK2VwAyEA11qYAYKxCrfVS/7TyWQHOg7hcvPapiMlrwIaaPcHURo='
node verification/verify.js verification/sample-test-key-envelope.json 'MCowBQYDK2VwAyEA11qYAYKxCrfVS/7TyWQHOg7hcvPapiMlrwIaaPcHURo='
```

Expected: `Ed25519 signature: VALID`. This uses the public RFC 8032 TEST 1 key, never the production issuer. It is not a paid examination or issuer statement. Changing the payload must make verification fail. [Test-vector details](test-vectors.md).

## Receiver checks after cryptographic verification

Compare the signed question, object, scope, requested operation, conditions and finding with the request actually being considered. Check completeness limitations, freshness and the receiver's own policy. A negative or incomplete finding is not permission to proceed; a positive finding is not independent authorization either. The receiving system owns its action decision.

Retain the exact request bytes, request hash, quoted terms, original result, expected issuer key pin, verifier version and output, and the receiver decision. Keep payment hashes and submitted material private unless their disclosure is separately authorized. Publish only a redacted, permissioned integration example, never a payer identity or private payload.
