#!/usr/bin/env python3
"""60-second offline demonstration of the Standing Receiving Kit.

No network, no payment, no live service. Marks are synthetic TEST fixtures signed with the public
RFC 8032 TEST 1 key. Nothing here is an examination by Wheeler Hubbell Publishing.
Run:  python3 examples/demo_60s.py      (needs the 'cryptography' package)
"""
import json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from standing_receiver import *
from standing_receiver import testing as T
t0 = time.time()
def h(s): print("\n== " + s)
CLAIM = "The published contract names Base mainnet USDC as the payment asset."
DATA = "The payment asset is USDC.\nThe price is exactly 1.00 USDC."

h("1. Build the request in the engine's real shape (before any quote or payment)")
for label, kw in (("nested object claim (the shape older docs showed)", dict(claim={"statement": CLAIM}, data=DATA)),
                  ("empty material", dict(claim=CLAIM, data=""))):
    try: build_request(**kw)
    except RequestError as e: print("  refused locally: %-48s -> %s" % (label, e.code))
req = build_request(claim=CLAIM, data=DATA, source="https://example.test/contract")
print("  accepted: %d material bytes, request sha256 %s..." % (req.material_bytes, req.request_sha256[:16]))

h("2. A signed result arrives (synthetic TEST fixture)")
mark = T.synthetic_mark(CLAIM, req.material_bytes, outcome="NOT_ESTABLISHED", issued_at=int(t0), request_bytes=req.body_bytes)
print("  outcome as stated by the result:", mark["payload"]["standing"]["outcome"])

h("3. Standing Receiver: verify offline against a key the receiver pinned")
rx = StandingReceiver([T.TEST_PUBLIC_B64], "demo-recipient")
res = rx.receive(json.dumps(mark).encode(), expected_proposition=CLAIM, request_bytes=req.body_bytes)
print("  state:", res.state); print("  checks:", json.dumps(res.checks))

h("4. Evidence object handed to the receiving system (no allow/deny anywhere in it)")
ev = res.evidence
print(json.dumps({k: ev[k] for k in ("mark_verified", "freshness", "substantive_examination", "problems")}, indent=2))
print("  finding as stated:", ev["examination"]["outcome"], "| kit_statement:", ev["kit_statement"][:70] + "...")

h("5. The receiver's own rule decides (this rule is the demo's, not the kit's)")
def my_rule(evidence): return evidence["mark_verified"] and evidence["substantive_examination"]["status"] == "SUBSTANTIVE" and evidence["examination"]["outcome"] == "TRANSITION_ALLOWED"
print("  receiver rule says proceed?", my_rule(ev), "(NOT_ESTABLISHED is a delivered examination; this receiver's rule requires an established one)")

h("6. Reception record and exchange chain")
rec = build_reception_record(res)
print("  establishes:       ", rec["establishes"]); print("  does not establish:", rec["does_not_establish"][:3], "...")
a = link("request", req.body); b = link("mark", mark, [a["object_id"]]); c = link("reception_event", res.event, [b["object_id"]]); d = link("receipt", rec, [c["object_id"]])
print("  chain problems:", verify_chain([a, b, c, d]) or "none")
mark["payload"]["standing"]["outcome"] = "TRANSITION_ALLOWED"
print("  after altering the original mark, receiver reports:", StandingReceiver([T.TEST_PUBLIC_B64], "demo-recipient").receive(mark).checks["SIGNATURE"])
print("\nDone in %.2fs. Synthetic fixtures only; no examination was purchased." % (time.time() - t0))
