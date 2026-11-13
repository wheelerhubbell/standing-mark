"""Run the vectors against the Python kit: python3 conformance/run.py"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from standing_receiver import *
from standing_receiver.jcs import jcs
V = json.load(open(os.path.join(os.path.dirname(__file__), "vectors.json")))
fail = 0
def check(name, got, want):
    global fail
    if got != want: fail += 1; print("FAIL", name, "\n  got ", got, "\n  want", want)
for i, c in enumerate(V["jcs"]): check("jcs%d" % i, jcs(c["input"]), c["expected"])
for i, c in enumerate(V["object_id"]): check("oid%d" % i, object_id(c["input"]), c["expected"])
for c in V["signature"]:
    r = verify_envelope(c["envelope"], c["pinned"], **({"expected_type": c["expected_type"]} if "expected_type" in c else {}))
    check("sig:" + c["id"], {"valid": r.valid, "reason": r.reason}, c["expected"])
for c in V["request"]:
    try: r = build_request(claim=c["input"].get("claim"), data=c["input"].get("data")); got = {"ok": True, "body_jcs": r.body_bytes.decode(), "material_bytes": r.material_bytes}
    except RequestError as e: got = {"ok": False, "code": e.code}
    check("req:" + c["id"], got, c["expected"])
for c in V["evidence"]:
    e = build_evidence(c["envelope"], c["pinned"], now=c["now"])
    check("ev:" + c["id"], {"mark_verified": e["mark_verified"], "outcome": e["examination"]["outcome"], "substantive": e["substantive_examination"]["status"], "freshness": e["freshness"], "problems": e["problems"]}, c["expected"])
for c in V["receipt"]:
    r = verify_receipt(c["receipt"], c["pinned"], c["mark"]); check("rcpt:" + c["id"], {"valid": r.valid, "problems": list(r.problems)}, c["expected"])
for c in V["chain"]: check("chain:" + c["id"], verify_chain(c["records"]), c["expected"])
for c in V["binding"]:
    e = build_evidence(c["mark"], c["pinned"], now=1050, request_bytes=c["request"].encode()); check("bind:" + c["id"], e["binding"]["request_bytes"], c["expected"])
n = sum(len(V[k]) for k in V if isinstance(V[k], list))
print("python kit: %d conformance cases, %d failed" % (n, fail)); sys.exit(1 if fail else 0)
