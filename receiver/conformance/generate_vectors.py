"""Generate conformance/vectors.json from the RFC 8032 TEST 1 key. Ed25519 is deterministic, so output is stable."""
import json, os, sys, copy, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from standing_receiver import testing as T, build_request, build_reception_record, StandingReceiver
from standing_receiver.exchange import object_id, link
from standing_receiver.jcs import jcs

CLAIM = "The published contract names Base mainnet USDC as the payment asset."
DATA = "The payment asset is USDC.\nThe price is exactly 1.00 USDC."
m = lambda **k: T.synthetic_mark(CLAIM, k.pop("mb", 313), issued_at=1000, lifetime=100, **k)
V = {"suite": "standing-receiver-conformance/1", "test_key_spki_b64": T.TEST_PUBLIC_B64,
     "note": "All objects are synthetic TEST fixtures signed with the public RFC 8032 TEST 1 key. They are not issuer statements.",
     "jcs": [], "object_id": [], "signature": [], "request": [], "evidence": [], "receipt": [], "chain": []}
for v in [{"a": 1, "b": [1, 2, None, True]}, {"z": "é\u2028\n\"", "a": {"y": 0, "x": -7}}, {"b": 1, "a": 2, "": 3}]:
    V["jcs"].append({"input": v, "expected": jcs(v)})
    V["object_id"].append({"input": v, "expected": object_id(v)})
good = m()
tamper = copy.deepcopy(good); tamper["payload"]["issued_at"] = 1001
V["signature"] = [
    {"id": "valid", "envelope": good, "pinned": T.TEST_PUBLIC_B64, "expected": {"valid": True, "reason": "OK"}},
    {"id": "tampered", "envelope": tamper, "pinned": T.TEST_PUBLIC_B64, "expected": {"valid": False, "reason": "SIGNATURE_INVALID"}},
    {"id": "wrong_pin", "envelope": good, "pinned": "MCowBQYDK2VwAyEAcpFVUj6xDgsUsKJK2r2rLk6R+te2lghdHE8jvjl9SBk=", "expected": {"valid": False, "reason": "KEY_NOT_PINNED"}},
    {"id": "wrong_type", "envelope": good, "pinned": T.TEST_PUBLIC_B64, "expected_type": "OTHER", "expected": {"valid": False, "reason": "TYPE_MISMATCH"}},
    {"id": "incomplete", "envelope": {"payload": {}}, "pinned": T.TEST_PUBLIC_B64, "expected": {"valid": False, "reason": "ENVELOPE_INCOMPLETE"}},
]
ok = dict(claim=CLAIM, data=DATA)
V["request"] = [
    {"id": "valid", "input": ok, "expected": {"ok": True, "body_jcs": build_request(**ok).body_bytes.decode(), "material_bytes": len(DATA.encode())}},
    {"id": "object_claim", "input": {"claim": {"statement": CLAIM}, "data": DATA}, "expected": {"ok": False, "code": "NOT_A_STRING"}},
    {"id": "empty_data", "input": {"claim": CLAIM, "data": "  "}, "expected": {"ok": False, "code": "EMPTY_DATA"}},
    {"id": "missing_claim", "input": {"data": DATA}, "expected": {"ok": False, "code": "MISSING_CLAIM"}},
]
def ev(id_, env, now=None, **kw):
    V["evidence"].append({"id": id_, "envelope": env, "pinned": T.TEST_PUBLIC_B64, "now": now, **kw})
ev("allowed_finding_substantive", good, 1050, expected={"mark_verified": True, "outcome": "TRANSITION_ALLOWED", "substantive": "SUBSTANTIVE", "freshness": "CURRENT", "problems": []})
ev("not_established_substantive", m(outcome="NOT_ESTABLISHED"), 1050, expected={"mark_verified": True, "outcome": "NOT_ESTABLISHED", "substantive": "SUBSTANTIVE", "freshness": "CURRENT", "problems": []})
ev("zero_bytes", m(outcome="NOT_ESTABLISHED", mb=0), 1050, expected={"mark_verified": True, "outcome": "NOT_ESTABLISHED", "substantive": "NOT_SUBSTANTIVE", "freshness": "CURRENT", "problems": ["EXAMINATION_NOT_SUBSTANTIVE"]})
ev("expired", good, 1100, expected={"mark_verified": True, "outcome": "TRANSITION_ALLOWED", "substantive": "SUBSTANTIVE", "freshness": "EXPIRED", "problems": ["EXPIRED"]})
ev("tampered", tamper, 1050, expected={"mark_verified": False, "outcome": "TRANSITION_ALLOWED", "substantive": "SUBSTANTIVE", "freshness": "CURRENT", "problems": ["SIGNATURE:SIGNATURE_INVALID"]})
rxr = StandingReceiver([T.TEST_PUBLIC_B64], "conformance-recipient", clock=lambda: 1050)
res = rxr.receive(good)
rec = build_reception_record(res)
rec_env = T.sign(rec, "WHP-STANDING-RECEIPT-v1")
bad = copy.deepcopy(rec); bad["accepted"] = True
V["receipt"] = [
    {"id": "valid", "receipt": rec_env, "mark": good, "pinned": T.TEST_PUBLIC_B64, "expected": {"valid": True, "problems": []}},
    {"id": "claims_acceptance", "receipt": T.sign(bad, "WHP-STANDING-RECEIPT-v1"), "mark": good, "pinned": T.TEST_PUBLIC_B64, "expected": {"valid": False, "problems": ["CLAIMS_ACCEPTANCE_OR_AUTHORIZATION"]}},
    {"id": "wrong_mark", "receipt": rec_env, "mark": m(mark_id="WHP-SM-TEST-0002"), "pinned": T.TEST_PUBLIC_B64, "expected": {"valid": False, "problems": ["MARK_REF_MISMATCH", "CORRESPONDENCE_MISMATCH"]}},
]
req = build_request(**ok)
a = link("request", req.body); b = link("mark", good, [a["object_id"]]); c = link("reception_event", res.event, [b["object_id"]]); d = link("receipt", rec, [c["object_id"]])
chain = [a, b, c, d]; altered = copy.deepcopy(chain); altered[1]["object"]["payload"]["issued_at"] = 1
V["chain"] = [{"id": "valid", "records": chain, "expected": []},
              {"id": "altered", "records": altered, "expected": ["1:OBJECT_ALTERED"]},
              {"id": "illegal_link", "records": [a, link("receipt", rec, [a["object_id"]])], "expected": ["1:ILLEGAL_LINK request->receipt"]}]
import json as _j
body = {"claim": CLAIM, "data": DATA}
canon_body = build_request(**ok).body_bytes   # includes requested_operation
pretty = _j.dumps(_j.loads(canon_body), indent=3, sort_keys=False)
bm = T.synthetic_mark(CLAIM, 58, issued_at=1000, lifetime=100, request_bytes=canon_body)
V["binding"] = [
    {"id": "canonical_and_pretty_same_payload", "mark": bm, "pinned": T.TEST_PUBLIC_B64, "request": pretty, "expected": "CORRESPONDS"},
    {"id": "different_payload", "mark": bm, "pinned": T.TEST_PUBLIC_B64, "request": '{"claim":"other","data":"x"}', "expected": "DOES_NOT_CORRESPOND"},
    {"id": "bare_string_hashed_without_quotes", "mark": T.synthetic_mark("bare", 4, issued_at=1000, request_bytes=b'"bare"'), "pinned": T.TEST_PUBLIC_B64, "request": '"bare"', "expected": "CORRESPONDS"},
]
json.dump(V, open(os.path.join(os.path.dirname(__file__), "vectors.json"), "w"), indent=1, sort_keys=True, ensure_ascii=False)
print("vectors written")
