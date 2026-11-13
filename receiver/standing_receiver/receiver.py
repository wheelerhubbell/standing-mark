"""Standing Receiver: reception integrity.

Authenticates the issuer against keys the receiver pinned, verifies the signature, checks the
record is complete, current and unaltered, detects replay and conflicting redelivery, preserves the
original bytes unmodified, and produces a reception event. Receipt, acceptance, rejection and
authorization stay separate: this class only does reception.
"""
import json, hashlib, time
from dataclasses import dataclass, field
from .verify import verify_envelope, key_id_of
from .evidence import build_evidence, envelope_sha256

REQUIRED = ("mark_id", "issuer", "issued_at", "expires_at", "object_binding", "standing", "submission_hash")

class SeenStore:
    """mark_id -> envelope hash. In memory, or persisted to a JSON file the receiver owns."""
    def __init__(self, path=None):
        self.path, self._d = path, {}
        if path:
            try:
                self._d = json.load(open(path))
            except (OSError, ValueError):
                self._d = {}
    def get(self, mark_id):
        return self._d.get(mark_id)
    def put(self, mark_id, digest):
        self._d[mark_id] = digest
        if self.path:
            json.dump(self._d, open(self.path, "w"), sort_keys=True)

@dataclass
class ReceptionResult:
    checks: dict
    evidence: dict
    event: dict
    original_bytes: bytes
    original_sha256: str
    envelope: object
    state: str

class StandingReceiver:
    def __init__(self, pinned_keys, recipient, seen=None, clock=time.time):
        """pinned_keys: list of SPKI DER base64 keys the receiver approved through its own trust process."""
        self.keys = {key_id_of(k): k for k in pinned_keys}
        self.recipient = recipient
        self.seen = seen if seen is not None else SeenStore()
        self.clock = clock

    def receive(self, original, *, expected_proposition=None, request_bytes=None, issued_envelope_sha256=None):
        raw = original if isinstance(original, (bytes, bytearray)) else (
            original.encode("utf-8") if isinstance(original, str) else json.dumps(original, sort_keys=True).encode("utf-8"))
        raw = bytes(raw)
        try:
            env = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            env = None
        now = int(self.clock())
        checks = {}
        payload = env.get("payload") if isinstance(env, dict) and isinstance(env.get("payload"), dict) else {}
        kid = (env.get("protected") or {}).get("key_id") if isinstance(env, dict) and isinstance(env.get("protected"), dict) else None
        key = self.keys.get(kid)
        checks["ISSUER_PINNED"] = "PASS" if key else "FAIL"
        sig_valid = False
        if key:
            ev = build_evidence(env, key, now=now, expected_proposition=expected_proposition, request_bytes=request_bytes)
            sig_valid = ev["signature"]["valid"]
        else:
            ev = build_evidence(env if isinstance(env, dict) else {}, next(iter(self.keys.values())) if self.keys else "", now=now,
                                expected_proposition=expected_proposition, request_bytes=request_bytes)
            ev["mark_verified"] = False
            ev["problems"].insert(0, "ISSUER_NOT_PINNED")
        checks["SIGNATURE"] = "PASS" if sig_valid else "FAIL"
        checks["COMPLETE"] = "PASS" if all(k in payload for k in REQUIRED) else "FAIL"
        checks["FRESH"] = {"CURRENT": "PASS", "EXPIRED": "FAIL"}.get(ev["freshness"], "NOT_CHECKED")
        digest = envelope_sha256(env) if sig_valid else None
        if issued_envelope_sha256 is None:
            checks["CORRESPONDS_TO_ISSUED"] = "NOT_CHECKED"
        else:
            checks["CORRESPONDS_TO_ISSUED"] = "PASS" if digest == issued_envelope_sha256 else "FAIL"
        mid = payload.get("mark_id")
        if sig_valid and mid:
            prior = self.seen.get(mid)
            if prior is None:
                checks["REPLAY"] = "FIRST_RECEIPT"
                self.seen.put(mid, digest)
            elif prior == digest:
                checks["REPLAY"] = "DUPLICATE_OF_EARLIER_RECEIPT"
            else:
                checks["REPLAY"] = "CONFLICTING_REDELIVERY"
        else:
            checks["REPLAY"] = "NOT_CHECKED"
        failed = [k for k, v in checks.items() if v in ("FAIL", "CONFLICTING_REDELIVERY")]
        if checks["REPLAY"] == "CONFLICTING_REDELIVERY":
            ev["problems"].append("CONFLICTING_REDELIVERY")
        state = "RECEIVED_VERIFIED" if not failed else "RECEIVED_WITH_PROBLEMS"
        orig_hash = hashlib.sha256(raw).hexdigest()
        event = {"event_type": "STANDING_MARK_RECEPTION", "recipient": self.recipient, "received_at": now,
                 "original_sha256": orig_hash, "mark_id": mid, "state": state}
        event["event_id"] = hashlib.sha256((self.recipient + "|" + orig_hash + "|" + str(now)).encode()).hexdigest()
        return ReceptionResult(checks, ev, event, raw, orig_hash, env, state)
