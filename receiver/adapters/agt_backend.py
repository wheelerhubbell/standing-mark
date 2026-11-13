"""Microsoft Agent Governance Toolkit: evidence backend.

Implements AGT's ExternalPolicyBackend protocol (name, evaluate, healthy). evaluate() builds the
evidence object from a Standing Mark in context["standing_mark"] and passes it to the receiver's
own rule. PolicyDecisionResult.allowed is whatever that rule returns; the kit never sets it from
a finding. The evidence is attached as raw_response["evidence"] and exposed to rules as
context["standing_evidence"] if the receiver chains rules.
"""
import time
try:
    from agentmesh.governance.backend import PolicyDecisionResult
except Exception:  # AGT not importable here: same shape, for local tests
    from dataclasses import dataclass, field
    from typing import Any
    @dataclass
    class PolicyDecisionResult:
        allowed: bool
        reason: str = ""
        backend: str = ""
        latency_ms: float = 0.0
        raw_response: Any = field(default=None, repr=False)
from ._common import evidence_for, require_rule

class StandingEvidenceBackend:
    def __init__(self, receiver, receiver_rule, name="standing-mark-evidence"):
        self._receiver, self._rule, self._name = receiver, require_rule(receiver_rule), name

    @property
    def name(self):
        return self._name

    def evaluate(self, action, context):
        t0 = time.perf_counter()
        ev = evidence_for(self._receiver, context.get("standing_mark"), context.get("expected_proposition"),
                          context.get("request_bytes"))
        verdict = self._rule(action, ev, context)
        allowed = bool(getattr(verdict, "allowed", verdict))
        reason = getattr(verdict, "reason", None) or "decided by the receiving organization's rule; kit supplied evidence only"
        return PolicyDecisionResult(allowed=allowed, reason=reason, backend=self._name,
                                    latency_ms=(time.perf_counter() - t0) * 1000.0, raw_response={"evidence": ev})

    def healthy(self):
        return True
