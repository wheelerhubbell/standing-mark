import json, hashlib, copy, pytest
from standing_receiver import *
from standing_receiver import testing as T
from standing_receiver.evidence import envelope_sha256, absent_evidence

CLAIM = "The published contract names Base mainnet USDC as the payment asset."
DATA = "The payment asset is USDC.\nThe price is exactly 1.00 USDC."

# ---- request construction (the empty-examination defect, pinned) ----
def test_request_is_engine_shape_and_counts_material():
    r = build_request(claim=CLAIM, data=DATA, source="https://example.test/c", evidence=["The price is exactly 1.00 USDC."])
    assert isinstance(r.body["claim"], str) and isinstance(r.body["data"], str)
    assert r.material_bytes == len(DATA.encode()) > 0
    assert json.loads(r.body_bytes) == r.body
    assert r.request_sha256 == hashlib.sha256(r.body_bytes).hexdigest()

def test_request_bytes_are_deterministic():
    a = build_request(claim=CLAIM, data=DATA); b = build_request(data=DATA, claim=CLAIM)
    assert a.body_bytes == b.body_bytes

@pytest.mark.parametrize("kw,code", [
    (dict(claim={"statement": "x"}, data=DATA), "NOT_A_STRING"),
    (dict(claim=CLAIM, data={"text": "x"}), "NOT_A_STRING"),
    (dict(claim="", data=DATA), "EMPTY_CLAIM"),
    (dict(claim=CLAIM, data="   "), "EMPTY_DATA"),
    (dict(claim=None, data=DATA), "MISSING_CLAIM"),
    (dict(claim=CLAIM, data=None), "MISSING_DATA"),
    (dict(claim=CLAIM, data=DATA, bounds={"valid_from": 1.5}), "NOT_CANONICAL"),
    (dict(claim=CLAIM, data="x" * 262144), "TOO_LARGE"),
    (dict(claim=CLAIM, data=DATA, requested_operation="APPROVE"), "BAD_OPERATION"),
])
def test_empty_or_wrong_shape_is_refused_before_any_quote(kw, code):
    with pytest.raises(RequestError) as e:
        build_request(**kw)
    assert e.value.code == code

def test_nested_shape_mapping_is_explicit_and_reported():
    nested = {"claim": {"type": "factual_claim", "statement": CLAIM}, "material": {"text": DATA, "source_url": "https://example.test/c"}}
    r = from_nested_shape(nested)
    assert r.body["claim"] == CLAIM and r.body["data"] == DATA and r.body["source"] == "https://example.test/c"
    assert "claim.statement -> claim" in r.mapping_report

def test_nested_shape_never_drops_unknown_fields_silently():
    with pytest.raises(RequestError) as e:
        from_nested_shape({"claim": {"statement": CLAIM, "weight": "high"}, "material": {"text": DATA}})
    assert e.value.code == "UNMAPPED_CLAIM_FIELDS"
    with pytest.raises(RequestError) as e:
        from_nested_shape({"claim": {"statement": CLAIM}, "material": {"published_contract": {"price": "1.00"}}})
    assert e.value.code == "UNMAPPED_MATERIAL_FIELDS"   # the earlier documented nested request shape: refused, not emptied

def test_earlier_documented_nested_shape_is_refused():
    paid_shape = {"claim": {"type": "factual_claim", "statement": CLAIM},
                  "material": {"source_url": "u", "retrieved_at": "t", "published_contract": {"a": "b"}}}
    with pytest.raises(RequestError):
        from_nested_shape(paid_shape)

def test_corrected_fixture_shape_builds():
    fx = json.load(open("/downloads/corrected-fixture-f3db14d1.json")) if False else None
    r = build_request(claim=CLAIM, data=DATA, source="https://decisionintegrity.example/v1/contract", warrant="Operator-published contract",
                      evidence=["The price is exactly 1.00 USDC."], bounds={"jurisdiction": "wheeler-hubbell-publishing", "scope": "whp-sovereign-standing", "valid_from": 1794591652, "valid_until": 1794678112})
    assert r.material_bytes > 0

# ---- client never reaches a quote with an empty request, never pays ----
class FakeTransport:
    def __init__(self, responses): self.responses, self.calls = list(responses), []
    def __call__(self, m, url, body, headers):
        self.calls.append((m, url, body, headers)); return self.responses.pop(0)

def test_client_refuses_raw_dict_and_sends_exact_bytes():
    t = FakeTransport([(402, {"payment_required": {"quote_id": "q1", "amount_units": 1000000}})])
    c = ExaminationClient("https://svc.test", t)
    with pytest.raises(TypeError):
        c.submit({"claim": {}, "material": {}})
    assert t.calls == []
    r = build_request(claim=CLAIM, data=DATA)
    with pytest.raises(QuoteRequired) as e:
        c.submit(r, expected_amount_units=1000000)
    assert t.calls[0][2] == r.body_bytes and e.value.quote["quote_id"] == "q1"

def test_client_refuses_unexpected_quote_amount():
    t = FakeTransport([(402, {"payment_required": {"quote_id": "q1", "amount_units": 2000000}})])
    with pytest.raises(RuntimeError):
        ExaminationClient("https://svc.test", t).submit(build_request(claim=CLAIM, data=DATA), expected_amount_units=1000000)

# ---- offline verification ----
def mark(**kw):
    return T.synthetic_mark(CLAIM, kw.pop("material_bytes", 313), **kw)

def test_valid_signature_and_tamper_detection():
    m = mark()
    assert verify_envelope(m, T.TEST_PUBLIC_B64).valid
    t = copy.deepcopy(m); t["payload"]["standing"]["outcome"] = "TRANSITION_ALLOWED "
    assert verify_envelope(t, T.TEST_PUBLIC_B64).reason == "SIGNATURE_INVALID"

def test_wrong_pin_wrong_type_and_incomplete():
    m = mark()
    other = "MCowBQYDK2VwAyEAcpFVUj6xDgsUsKJK2r2rLk6R+te2lghdHE8jvjl9SBk="
    assert verify_envelope(m, other).reason == "KEY_NOT_PINNED"
    assert verify_envelope(m, T.TEST_PUBLIC_B64, expected_type="OTHER").reason == "TYPE_MISMATCH"
    assert verify_envelope({"payload": {}}, T.TEST_PUBLIC_B64).reason == "ENVELOPE_INCOMPLETE"
    assert verify_envelope(None, T.TEST_PUBLIC_B64).reason == "ENVELOPE_INCOMPLETE"

def test_repo_sample_vector_still_verifies():
    import os
    p = os.path.join(os.path.dirname(__file__), "..", "..", "verification", "sample-test-key-envelope.json")
    env = json.load(open(p))
    assert verify_envelope(env, T.TEST_PUBLIC_B64, expected_type=None).valid   # independent check against the public vector

# ---- evidence: carries findings as stated, decides nothing ----
FORBIDDEN = {"allow", "allowed", "deny", "denied", "decision", "authorized", "authorization", "accepted", "approve", "approved"}
def keys(o):
    if isinstance(o, dict):
        for k, v in o.items(): yield k; yield from keys(v)
    elif isinstance(o, list):
        for v in o: yield from keys(v)

@pytest.mark.parametrize("outcome", ["TRANSITION_ALLOWED", "NOT_ESTABLISHED", "BOUNDED_DETERMINATION", "TRANSITION_DENIED"])
def test_evidence_never_maps_finding_to_a_verdict(outcome):
    ev = build_evidence(mark(outcome=outcome), T.TEST_PUBLIC_B64)
    assert ev["examination"]["outcome"] == outcome
    assert not (set(k.lower() for k in keys(ev)) & FORBIDDEN)
    assert "does not allow, deny" in ev["kit_statement"]
    assert ev["mark_verified"] is True

def test_not_established_over_real_material_is_a_delivered_examination():
    ev = build_evidence(mark(outcome="NOT_ESTABLISHED"), T.TEST_PUBLIC_B64)
    assert ev["substantive_examination"]["status"] == "SUBSTANTIVE" and ev["problems"] == []

def test_zero_byte_examination_is_flagged_not_substantive():
    for kw in (dict(material_bytes=0), dict(material_bytes=1, fallback=True)):
        ev = build_evidence(mark(outcome="NOT_ESTABLISHED", **kw), T.TEST_PUBLIC_B64)
        assert ev["substantive_examination"]["status"] == "NOT_SUBSTANTIVE"
        assert "EXAMINATION_NOT_SUBSTANTIVE" in ev["problems"] and ev["mark_verified"]

def test_freshness_question_and_request_binding():
    req = build_request(claim=CLAIM, data=DATA)
    m = mark(issued_at=1000, lifetime=100, request_bytes=req.body_bytes)
    assert build_evidence(m, T.TEST_PUBLIC_B64, now=1050)["freshness"] == "CURRENT"
    e = build_evidence(m, T.TEST_PUBLIC_B64, now=1100, expected_proposition=CLAIM, request_bytes=req.body_bytes)
    assert e["freshness"] == "EXPIRED" and "EXPIRED" in e["problems"]
    assert e["binding"]["question_match"] == "MATCH" and e["binding"]["request_bytes"] == "CORRESPONDS"
    e = build_evidence(m, T.TEST_PUBLIC_B64, now=1050, expected_proposition="a different question", request_bytes=b"other")
    assert {"QUESTION_MISMATCH", "SUBMITTED_PAYLOAD_DOES_NOT_CORRESPOND"} <= set(e["problems"])

def test_unverified_mark_is_reported_unverified():
    t = mark(); t["payload"]["standing"]["outcome"] = "X"
    ev = build_evidence(t, T.TEST_PUBLIC_B64)
    assert ev["mark_verified"] is False and "SIGNATURE:SIGNATURE_INVALID" in ev["problems"]

# ---- Standing Receiver ----
def rx(clock=lambda: 1050): return StandingReceiver([T.TEST_PUBLIC_B64], "recipient-A", clock=clock)

def test_receive_preserves_original_bytes_unmodified():
    m = mark(issued_at=1000, lifetime=100)
    raw = json.dumps(m, indent=3).encode()          # odd formatting on purpose
    r = rx().receive(raw)
    assert r.original_bytes == raw and r.original_sha256 == hashlib.sha256(raw).hexdigest()
    assert r.state == "RECEIVED_VERIFIED" and r.checks["REPLAY"] == "FIRST_RECEIPT"

def test_issuer_not_pinned():
    r = StandingReceiver(["MCowBQYDK2VwAyEAcpFVUj6xDgsUsKJK2r2rLk6R+te2lghdHE8jvjl9SBk="], "A", clock=lambda: 1050).receive(mark(issued_at=1000))
    assert r.checks["ISSUER_PINNED"] == "FAIL" and r.state == "RECEIVED_WITH_PROBLEMS" and not r.evidence["mark_verified"]
    assert "ISSUER_NOT_PINNED" in r.evidence["problems"]

def test_alteration_expiry_incomplete_garbage():
    m = mark(issued_at=1000, lifetime=100); alt = copy.deepcopy(m); alt["payload"]["issued_at"] = 1001
    assert rx().receive(alt).checks["SIGNATURE"] == "FAIL"
    assert rx(lambda: 5000).receive(m).checks["FRESH"] == "FAIL"
    inc = T.sign({"mark_id": "x"}, "WHP-STANDING-MARK-v1")
    assert rx().receive(inc).checks["COMPLETE"] == "FAIL"
    g = rx().receive(b"not json")
    assert g.state == "RECEIVED_WITH_PROBLEMS" and g.checks["SIGNATURE"] == "FAIL"

def test_duplicate_and_conflicting_redelivery(tmp_path):
    store = SeenStore(str(tmp_path / "seen.json"))
    r1 = StandingReceiver([T.TEST_PUBLIC_B64], "A", store, clock=lambda: 1050)
    m = mark(issued_at=1000, lifetime=100)
    assert r1.receive(m).checks["REPLAY"] == "FIRST_RECEIPT"
    assert r1.receive(m).checks["REPLAY"] == "DUPLICATE_OF_EARLIER_RECEIPT"
    r2 = StandingReceiver([T.TEST_PUBLIC_B64], "A", SeenStore(str(tmp_path / "seen.json")), clock=lambda: 1050)   # persisted
    assert r2.receive(m).checks["REPLAY"] == "DUPLICATE_OF_EARLIER_RECEIPT"
    other = mark(issued_at=1001, lifetime=100)       # same mark_id, different signed content
    r = r2.receive(other)
    assert r.checks["REPLAY"] == "CONFLICTING_REDELIVERY" and r.state == "RECEIVED_WITH_PROBLEMS"

def test_forgery_does_not_poison_seen_store():
    store = SeenStore(); r = StandingReceiver([T.TEST_PUBLIC_B64], "A", store, clock=lambda: 1050)
    forged = mark(issued_at=1000); forged["payload"]["standing"]["outcome"] = "FORGED"
    r.receive(forged)
    assert store.get("WHP-SM-TEST-0001") is None

def test_correspondence_to_issued_object():
    m = mark(issued_at=1000, lifetime=100)
    assert rx().receive(m, issued_envelope_sha256=envelope_sha256(m)).checks["CORRESPONDS_TO_ISSUED"] == "PASS"
    assert rx().receive(m, issued_envelope_sha256="0" * 64).checks["CORRESPONDS_TO_ISSUED"] == "FAIL"

# ---- Standing Receipt ----
def signed_receipt(result, **kw):
    return T.sign(build_reception_record(result, **kw), "WHP-STANDING-RECEIPT-v1")

def test_receipt_roundtrip_and_limits():
    m = mark(issued_at=1000, lifetime=100); r = rx().receive(m)
    rec = build_reception_record(r)
    assert rec["establishes"] == ["AUTHENTICATED_RECEPTION_EVENT", "CORRESPONDENCE_OF_RECEIVED_TO_ISSUED_OBJECT"]
    assert "RECEIVER_ACCEPTANCE" in rec["does_not_establish"] and "AUTHORIZATION_OF_ANY_ACTION" in rec["does_not_establish"]
    env = signed_receipt(r)
    assert verify_receipt(env, T.TEST_PUBLIC_B64, m).valid

def test_receipt_original_mark_not_mutated():
    m = mark(issued_at=1000, lifetime=100); before = envelope_sha256(m)
    r = rx().receive(m); build_reception_record(r)
    assert envelope_sha256(m) == before

def test_receipt_rejects_overclaims_and_wrong_mark():
    m = mark(issued_at=1000, lifetime=100); r = rx().receive(m)
    rec = build_reception_record(r); rec["accepted"] = True
    assert "CLAIMS_ACCEPTANCE_OR_AUTHORIZATION" in verify_receipt(T.sign(rec, "WHP-STANDING-RECEIPT-v1"), T.TEST_PUBLIC_B64).problems
    rec = build_reception_record(r); rec["establishes"].append("RECEIVER_ACCEPTANCE")
    assert "OVERCLAIMS" in verify_receipt(T.sign(rec, "WHP-STANDING-RECEIPT-v1"), T.TEST_PUBLIC_B64).problems
    rec = build_reception_record(r); rec["does_not_establish"] = []
    assert "MISSING_LIMITS" in verify_receipt(T.sign(rec, "WHP-STANDING-RECEIPT-v1"), T.TEST_PUBLIC_B64).problems
    other = mark(issued_at=1000, lifetime=100, mark_id="WHP-SM-TEST-0002")
    assert "MARK_REF_MISMATCH" in verify_receipt(signed_receipt(r), T.TEST_PUBLIC_B64, other).problems

def test_receiver_acknowledgment_is_a_separate_object_not_acceptance():
    r = rx().receive(mark(issued_at=1000, lifetime=100))
    env = signed_receipt(r, acknowledgment={"text": "Received; our policy team will review."})
    c = verify_receipt(env, T.TEST_PUBLIC_B64)
    assert c.valid and env["payload"]["acknowledgment"]["kind"] == "SEPARATE_RECEIVER_RESPONSE"

def test_receipt_signature_tamper():
    r = rx().receive(mark(issued_at=1000, lifetime=100)); env = signed_receipt(r)
    env["payload"]["recipient"]["label"] = "someone-else"
    assert not verify_receipt(env, T.TEST_PUBLIC_B64).valid

def test_receipt_of_unverified_mark_records_the_problem():
    forged = mark(issued_at=1000); forged["payload"]["standing"]["outcome"] = "FORGED"
    r = rx().receive(forged); rec = build_reception_record(r)
    assert rec["reception_event"]["state"] == "RECEIVED_WITH_PROBLEMS" and rec["verification_evidence"]["checks"]["SIGNATURE"] == "FAIL"

# ---- Exchange protocol ----
def test_chain_identity_and_no_mutation():
    req = build_request(claim=CLAIM, data=DATA); m = mark(issued_at=1000, lifetime=100, request_bytes=req.body_bytes)
    r = rx().receive(m); rec = build_reception_record(r)
    a = link("request", req.body)
    b = link("mark", m, [a["object_id"]])
    c = link("reception_event", r.event, [b["object_id"]])
    d = link("receipt", rec, [c["object_id"]])
    chain = [a, b, c, d]
    assert verify_chain(chain) == []
    b2 = copy.deepcopy(chain); b2[1]["object"]["payload"]["issued_at"] = 1
    assert "1:OBJECT_ALTERED" in verify_chain(b2)
    bad = [a, link("receipt", rec, [a["object_id"]])]
    assert any("ILLEGAL_LINK" in p for p in verify_chain(bad))
    assert any("UNLINKED" in p for p in verify_chain([a, link("mark", m)]))
    assert any("PRIOR_MISSING" in p for p in verify_chain([link("mark", m, ["sha256:00"])]))

def test_object_id_is_key_order_independent():
    assert object_id({"a": 1, "b": [1, 2]}) == object_id({"b": [1, 2], "a": 1})

def test_binding_is_canonical_payload_not_raw_bytes():
    req = build_request(claim=CLAIM, data=DATA)
    m = mark(issued_at=1000, lifetime=100, request_bytes=req.body_bytes)
    reformatted = json.dumps(req.body, indent=4, sort_keys=False).encode()        # different raw bytes, same parsed payload
    assert reformatted != req.body_bytes
    assert build_evidence(m, T.TEST_PUBLIC_B64, now=1050, request_bytes=reformatted)["binding"]["request_bytes"] == "CORRESPONDS"
    assert hashlib.sha256(reformatted).hexdigest() != m["payload"]["object_binding"]["submitted_bytes_sha256"]   # raw hash would never match
    assert build_evidence(m, T.TEST_PUBLIC_B64, now=1050, request_bytes=b'{"claim":"other","data":"x"}')["binding"]["request_bytes"] == "DOES_NOT_CORRESPOND"
    s = json.dumps("bare string").encode(); m2 = T.synthetic_mark("bare string", 11, issued_at=1000, request_bytes=s)
    assert m2["payload"]["object_binding"]["submitted_bytes_sha256"] == hashlib.sha256(b"bare string").hexdigest()   # no JSON quotes
