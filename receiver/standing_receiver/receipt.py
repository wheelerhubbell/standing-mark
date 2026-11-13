"""Standing Receipt: the record of an authenticated reception event.

Specification: receiver/docs/standing-receipt.md. This module builds the reception-record payload
from a ReceptionResult and verifies a signed receipt envelope offline. Signing a real receipt is an
act of Wheeler Hubbell Publishing's issuer key and needs a service route that does not exist yet;
that is proposed, not built here.
"""
from dataclasses import dataclass
from .verify import verify_envelope
from .evidence import envelope_sha256

RECEIPT_TYPE = "WHP-STANDING-RECEIPT-v1"
ESTABLISHES = ("AUTHENTICATED_RECEPTION_EVENT", "CORRESPONDENCE_OF_RECEIVED_TO_ISSUED_OBJECT")
DOES_NOT_ESTABLISH = ("RECEIVER_UNDERSTANDING", "RECEIVER_AGREEMENT", "RECEIVER_ACCEPTANCE", "AUTHORIZATION_OF_ANY_ACTION",
                      "SUBSTANTIVE_CORRECTNESS_OF_THE_EXAMINATION")
FORBIDDEN_KEYS = {"accepted", "acceptance", "authorized", "authorization", "approved", "agreed", "allow", "deny", "decision"}

def build_reception_record(result, issuing_authority="Wheeler Hubbell Publishing", recipient_authenticated_by=None, acknowledgment=None):
    """Unsigned receipt payload. The original Mark is referenced by hash and never copied or changed."""
    ev, evt = result.evidence, result.event
    rec = {
        "type": RECEIPT_TYPE,
        "issuing_authority": issuing_authority,
        "mark_ref": {"mark_id": ev["mark"]["mark_id"], "envelope_sha256": ev["mark"]["envelope_sha256"],
                     "issuer_key_id": ev["mark"]["issuer_key_id"]},
        "recipient": {"label": evt["recipient"], "authenticated_by": recipient_authenticated_by},
        "reception_event": {"event_id": evt["event_id"], "received_at": evt["received_at"], "state": evt["state"]},
        "correspondence": {"received_object_sha256": ev["mark"]["envelope_sha256"],
                           "issued_object_check": result.checks["CORRESPONDS_TO_ISSUED"]},
        "verification_evidence": {"checks": dict(result.checks), "problems": list(ev["problems"]),
                                  "kit": "standing-receiver/0.1.0"},
        "establishes": list(ESTABLISHES),
        "does_not_establish": list(DOES_NOT_ESTABLISH),
    }
    if acknowledgment is not None:
        rec["acknowledgment"] = {"kind": "SEPARATE_RECEIVER_RESPONSE", "body": acknowledgment}
    return rec

@dataclass(frozen=True)
class ReceiptCheck:
    valid: bool
    problems: tuple

def _walk_keys(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(o, list):
        for v in o:
            yield from _walk_keys(v)

def verify_receipt(envelope, pinned_public_key_b64, mark_envelope=None):
    sig = verify_envelope(envelope, pinned_public_key_b64, expected_type=RECEIPT_TYPE)
    problems = [] if sig.valid else ["SIGNATURE:" + sig.reason]
    p = envelope.get("payload") if isinstance(envelope, dict) and isinstance(envelope.get("payload"), dict) else {}
    if p.get("type") != RECEIPT_TYPE:
        problems.append("PAYLOAD_TYPE")
    if not set(DOES_NOT_ESTABLISH) <= set(p.get("does_not_establish", [])):
        problems.append("MISSING_LIMITS")
    if not set(p.get("establishes", [])) <= set(ESTABLISHES) or not p.get("establishes"):
        problems.append("OVERCLAIMS")
    # Only inspect keys outside the receiver's separate acknowledgment body.
    scan = {k: v for k, v in p.items() if k != "acknowledgment"}
    if any(k in FORBIDDEN_KEYS for k in _walk_keys(scan)):
        problems.append("CLAIMS_ACCEPTANCE_OR_AUTHORIZATION")
    if mark_envelope is not None:
        if (p.get("mark_ref") or {}).get("envelope_sha256") != envelope_sha256(mark_envelope):
            problems.append("MARK_REF_MISMATCH")
        if (p.get("correspondence") or {}).get("received_object_sha256") != envelope_sha256(mark_envelope):
            problems.append("CORRESPONDENCE_MISMATCH")
    return ReceiptCheck(not problems, tuple(problems))
