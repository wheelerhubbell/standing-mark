"""Plain evidence object handed to the receiving system.

Carries what the signed result says, verbatim, and the checks the kit could make. It contains no
allow, deny, accept or authorize field, and the kit never derives one. NOT_ESTABLISHED and bounded
results are delivered examinations and are reported as stated.
"""
import hashlib
from .verify import verify_envelope
from .jcs import jcs

EVIDENCE_VERSION = "standing-receiver-evidence/1"
KIT_STATEMENT = ("This object is evidence supplied to the receiving system. The kit does not allow, deny, "
                 "accept or authorize any action. The receiving system's own policy decides.")

def submitted_digest(request_bytes):
    """Digest the service records as object_binding.submitted_bytes_sha256 for a request body (raw bytes in)."""
    import json
    try:
        v = json.loads(request_bytes.decode("utf-8"))
    except ValueError:
        return None
    if isinstance(v, str): return hashlib.sha256(v.encode("utf-8")).hexdigest()
    if v is None: return hashlib.sha256(b"").hexdigest()
    return hashlib.sha256(jcs(v).encode("utf-8")).hexdigest()

def envelope_sha256(envelope):
    return hashlib.sha256(jcs(envelope).encode("utf-8")).hexdigest()

def _g(d, *path):
    for p in path:
        if not isinstance(d, dict) or p not in d:
            return None
        d = d[p]
    return d

def substantive(payload):
    """Did the examination actually receive material? Reported, never inferred into a verdict."""
    em = _g(payload, "object_binding", "examined_material")
    q = _g(payload, "object_binding", "examined_question")
    if not isinstance(em, dict) or "bytes" not in em:
        return {"status": "UNKNOWN", "examined_bytes": None, "fallback": None, "field": None, "has_question": q is not None}
    ok = isinstance(em["bytes"], int) and em["bytes"] > 0 and em.get("fallback") is False and bool(q)
    return {"status": "SUBSTANTIVE" if ok else "NOT_SUBSTANTIVE", "examined_bytes": em["bytes"],
            "fallback": em.get("fallback"), "field": em.get("field"), "has_question": bool(q)}

def build_evidence(envelope, pinned_public_key_b64, *, now=None, expected_proposition=None, request_bytes=None):
    sig = verify_envelope(envelope, pinned_public_key_b64)
    payload = envelope.get("payload") if isinstance(envelope, dict) and isinstance(envelope.get("payload"), dict) else {}
    problems = [] if sig.valid else ["SIGNATURE:" + sig.reason]
    exp = payload.get("expires_at")
    if now is None or not isinstance(exp, int):
        freshness = "NOT_CHECKED"
    else:
        freshness = "CURRENT" if now < exp else "EXPIRED"
        if freshness == "EXPIRED":
            problems.append("EXPIRED")
    sub = substantive(payload)
    if sub["status"] != "SUBSTANTIVE":
        problems.append("EXAMINATION_" + sub["status"])
    qm = "NOT_CHECKED"
    if expected_proposition is not None:
        qm = "MATCH" if _g(payload, "object_binding", "examined_question") == expected_proposition else "MISMATCH"
        if qm == "MISMATCH":
            problems.append("QUESTION_MISMATCH")
    rb = "NOT_CHECKED"
    if request_bytes is not None:
        # Verified in service source (Nov 13): submitted_bytes_sha256 is SHA-256 of the WHP-JCS-I1 canonical form of the
        # PARSED payload (object/array), or of the string itself for a bare-string body. It is not the raw HTTP body hash.
        rb = "CORRESPONDS" if submitted_digest(request_bytes) == _g(payload, "object_binding", "submitted_bytes_sha256") else "DOES_NOT_CORRESPOND"
        if rb == "DOES_NOT_CORRESPOND":
            problems.append("SUBMITTED_PAYLOAD_DOES_NOT_CORRESPOND")
    standing = payload.get("standing") if isinstance(payload.get("standing"), dict) else {}
    return {
        "evidence_version": EVIDENCE_VERSION,
        "kit_statement": KIT_STATEMENT,
        "mark_verified": sig.valid,
        "signature": {"valid": sig.valid, "reason": sig.reason, "pinned_key_id": sig.key_id},
        "mark": {"mark_id": payload.get("mark_id"), "issuer": payload.get("issuer"), "issuer_key_id": payload.get("issuer_key_id"),
                 "environment": payload.get("environment"), "issued_at": payload.get("issued_at"),
                 "expires_at": exp, "envelope_sha256": envelope_sha256(envelope) if sig.reason not in ("ENVELOPE_INCOMPLETE", "ENVELOPE_UNCANONICALIZABLE") else None},
        "freshness": freshness,
        "examination": {"outcome": standing.get("outcome"), "finding_disposition": payload.get("finding_disposition"),
                        "permitted_operations": standing.get("permitted_operations"),
                        "components": standing.get("components"), "scope": standing.get("bounds"),
                        "requested_operation": _g(payload, "object_binding", "requested_operation"),
                        "issuer_integration_rule": payload.get("integration_rule")},
        "substantive_examination": sub,
        "binding": {"examined_question": _g(payload, "object_binding", "examined_question"),
                    "submitted_bytes_sha256": _g(payload, "object_binding", "submitted_bytes_sha256"), "submitted_digest_meaning": "sha256 of WHP-JCS-I1 canonical parsed payload, not raw request bytes",
                    "submission_hash": payload.get("submission_hash"),
                    "question_match": qm, "request_bytes": rb},
        "problems": problems,
        "not_established_by_this_object": ["substantive correctness of the finding", "authority to act",
                                           "receiver acceptance", "current standing after issuance"],
    }

def absent_evidence(reason="NO_MARK_SUPPLIED"):
    """Evidence object for a call that carried no Standing Mark. Still only evidence: the receiver's policy decides what absence means."""
    return {"evidence_version": EVIDENCE_VERSION, "kit_statement": KIT_STATEMENT, "mark_verified": False,
            "signature": {"valid": False, "reason": reason, "pinned_key_id": None}, "mark": None, "freshness": "NOT_CHECKED",
            "examination": None, "substantive_examination": {"status": "UNKNOWN"}, "binding": None, "problems": [reason],
            "not_established_by_this_object": ["any examination, because none was supplied"]}
