"""Offline signature verification against a key the receiver pinned.

No network. The receiver supplies the expected issuer public key (SPKI DER base64) from its own
trust process. Establishes: the pinned key signed this exact object. Does not establish: that the
finding is correct, that it answers the receiver's question, current standing, or authorization.
"""
import base64, hashlib
from dataclasses import dataclass
from .jcs import jcs

MARK_TYPE = "WHP-STANDING-MARK-v1"

@dataclass(frozen=True)
class SignatureResult:
    valid: bool
    key_id: str
    reason: str

def key_id_of(public_key_b64):
    return hashlib.sha256(base64.b64decode(public_key_b64)).hexdigest()

def verify_envelope(envelope, pinned_public_key_b64, expected_type=MARK_TYPE):
    """Never raises on a bad envelope; returns SignatureResult(valid, key_id, reason)."""
    try:
        kid = key_id_of(pinned_public_key_b64)
    except Exception:
        return SignatureResult(False, "", "PINNED_KEY_UNREADABLE")
    try:
        prot, payload, sig = envelope["protected"], envelope["payload"], envelope["signature"]
    except (TypeError, KeyError):
        return SignatureResult(False, kid, "ENVELOPE_INCOMPLETE")
    if not isinstance(prot, dict):
        return SignatureResult(False, kid, "ENVELOPE_INCOMPLETE")
    if prot.get("algorithm") != "Ed25519":
        return SignatureResult(False, kid, "ALGORITHM_MISMATCH")
    if prot.get("canonicalization") != "WHP-JCS-I1":
        return SignatureResult(False, kid, "CANONICALIZATION_MISMATCH")
    if expected_type and prot.get("type") != expected_type:
        return SignatureResult(False, kid, "TYPE_MISMATCH")
    if prot.get("key_id") != kid:
        return SignatureResult(False, kid, "KEY_NOT_PINNED")
    try:
        from cryptography.hazmat.primitives.serialization import load_der_public_key
        from cryptography.exceptions import InvalidSignature
    except ImportError:
        return SignatureResult(False, kid, "CRYPTOGRAPHY_PACKAGE_MISSING")
    try:
        signing = jcs({"protected": prot, "payload": payload}).encode("utf-8")
        load_der_public_key(base64.b64decode(pinned_public_key_b64)).verify(base64.b64decode(sig), signing)
    except InvalidSignature:
        return SignatureResult(False, kid, "SIGNATURE_INVALID")
    except Exception:
        return SignatureResult(False, kid, "ENVELOPE_UNCANONICALIZABLE")
    return SignatureResult(True, kid, "OK")
