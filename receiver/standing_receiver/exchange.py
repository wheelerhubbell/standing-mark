"""Decision Integrity Exchange Protocol: identity and linkage of exchanged objects.

Every object keeps its identity (SHA-256 of its WHP-JCS-I1 bytes). Every event is its own object.
Records link to earlier records by id; nothing is edited in place. Specification:
receiver/docs/exchange-protocol.md.
"""
import hashlib
from .jcs import jcs

KINDS = ("request", "mark", "reception_event", "receipt", "receiver_response")
_AFTER = {"request": (), "mark": ("request",), "reception_event": ("mark",), "receipt": ("reception_event",),
          "receiver_response": ("receipt", "reception_event", "mark")}

def object_id(obj):
    return "sha256:" + hashlib.sha256(jcs(obj).encode("utf-8")).hexdigest()

def link(kind, obj, prior_ids=()):
    if kind not in KINDS:
        raise ValueError("unknown kind " + kind)
    return {"kind": kind, "object_id": object_id(obj), "prior_ids": list(prior_ids), "object": obj}

def verify_chain(records):
    """Returns a list of problems; empty means ids match content, links point backward, kinds follow the protocol."""
    problems, seen = [], {}
    for i, r in enumerate(records):
        if object_id(r["object"]) != r["object_id"]:
            problems.append("%d:OBJECT_ALTERED" % i)
        for p in r["prior_ids"]:
            if p not in seen:
                problems.append("%d:PRIOR_MISSING" % i)
            elif seen[p] not in _AFTER[r["kind"]]:
                problems.append("%d:ILLEGAL_LINK %s->%s" % (i, seen[p], r["kind"]))
        if r["kind"] != "request" and not r["prior_ids"]:
            problems.append("%d:UNLINKED" % i)
        seen[r["object_id"]] = r["kind"]
    return problems
