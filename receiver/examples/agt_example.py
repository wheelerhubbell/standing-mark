"""Microsoft AGT: register the evidence backend. The receiver's rule is the only decider. Synthetic TEST fixture."""
import os, sys, importlib.util
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from standing_receiver import StandingReceiver, testing as T
from adapters.agt_backend import StandingEvidenceBackend
def policy(action, evidence, context):          # the receiving organization's rule
    return evidence["mark_verified"] and evidence["freshness"] != "EXPIRED"
backend = StandingEvidenceBackend(StandingReceiver([T.TEST_PUBLIC_B64], "agt-example"), policy)
mark = T.synthetic_mark("Invoice 42 matches PO 42.", 120, outcome="BOUNDED_DETERMINATION")
d = backend.evaluate("export", {"standing_mark": mark})
print("allowed:", d.allowed, "| finding carried as evidence:", d.raw_response["evidence"]["examination"]["outcome"])
