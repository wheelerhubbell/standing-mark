"""TEST-ONLY helpers: sign synthetic objects with the published RFC 8032 TEST 1 key.

Never an issuer key. Fixtures made here are labeled environment TEST and prove nothing about the
live service. Requires the 'cryptography' package.
"""
import base64, hashlib, time
from .jcs import jcs

TEST_PRIVATE_HEX = "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
TEST_PUBLIC_B64 = "MCowBQYDK2VwAyEA11qYAYKxCrfVS/7TyWQHOg7hcvPapiMlrwIaaPcHURo="
TEST_KEY_ID = hashlib.sha256(base64.b64decode(TEST_PUBLIC_B64)).hexdigest()

def sign(payload, typ):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    sk = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(TEST_PRIVATE_HEX))
    prot = {"algorithm": "Ed25519", "canonicalization": "WHP-JCS-I1", "key_id": TEST_KEY_ID, "type": typ}
    sig = sk.sign(jcs({"protected": prot, "payload": payload}).encode("utf-8"))
    return {"protected": prot, "payload": payload, "signature": base64.b64encode(sig).decode()}

def synthetic_mark(proposition, material_bytes, *, outcome="TRANSITION_ALLOWED", mark_id="WHP-SM-TEST-0001", issued_at=None,
                   lifetime=86400, request_bytes=None, fallback=False, ops=("DESCRIBE", "INFORM")):
    issued_at = int(time.time()) if issued_at is None else issued_at
    payload = {"mark_id": mark_id, "issuer": "Wheeler Hubbell Publishing", "issuer_key_id": TEST_KEY_ID, "environment": "TEST",
               "issued_at": issued_at, "expires_at": issued_at + lifetime, "submission_hash": "0" * 64,
               "finding_disposition": "NEGATIVE_STANDING_FINDING" if outcome == "NOT_ESTABLISHED" else "POSITIVE_STANDING_FINDING",
               "integration_rule": "Synthetic test fixture. Not an issuer statement.",
               "standing": {"outcome": outcome, "permitted_operations": list(ops) if outcome != "NOT_ESTABLISHED" else ["DESCRIBE"],
                            "components": {"SOURCE": "ESTABLISHED" if outcome != "NOT_ESTABLISHED" else "NOT_ESTABLISHED"},
                            "bounds": {"jurisdiction": "wheeler-hubbell-publishing", "scope": "whp-sovereign-standing"}},
               "object_binding": {"examined_question": proposition,
                                  "examined_material": {"bytes": material_bytes, "fallback": fallback, "field": "data", "sha256": "0" * 64},
                                  "requested_operation": "INFORM",
                                  "submitted_bytes_sha256": __import__("standing_receiver.evidence", fromlist=["x"]).submitted_digest(request_bytes) if request_bytes else "0" * 64}}
    return sign(payload, "WHP-STANDING-MARK-v1")
