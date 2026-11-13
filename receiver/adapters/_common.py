"""Shared by the adapters: turn whatever a framework hands over into an evidence object.

The receiver's rule is required and is the only thing that decides. There is no default rule.
"""
from standing_receiver.evidence import absent_evidence

def evidence_for(receiver, mark, expected_proposition=None, request_bytes=None):
    if mark is None:
        return absent_evidence()
    r = receiver.receive(mark, expected_proposition=expected_proposition, request_bytes=request_bytes)
    ev = dict(r.evidence)
    ev["reception"] = {"state": r.state, "checks": r.checks, "event_id": r.event["event_id"], "original_sha256": r.original_sha256}
    return ev

def require_rule(rule):
    if not callable(rule):
        raise TypeError("a receiver_rule callable is required: the receiving organization's own policy decides; the kit has no default")
    return rule
