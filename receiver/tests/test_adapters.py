import json, asyncio, importlib.util, os, pytest
from standing_receiver import StandingReceiver
from standing_receiver import testing as T

CLAIM = "The published contract names Base mainnet USDC as the payment asset."
def rcv(): return StandingReceiver([T.TEST_PUBLIC_B64], "adapter-test", clock=lambda: 1050)
def good(outcome="TRANSITION_ALLOWED", **kw): return T.synthetic_mark(CLAIM, 313, outcome=outcome, issued_at=1000, lifetime=100, **kw)

def seen_by_rule(box):
    """A receiver rule that records the evidence it was handed. The rule here is a test stub, not kit logic."""
    def rule(*a):
        box.append(a[-1] if not isinstance(a[-1], dict) or "evidence_version" in a[-1] else a[1]); return RESULT["v"]
    return rule
RESULT = {"v": True}

# ---------- Microsoft AGT ----------
def _agt_protocol():
    p = os.path.expanduser("~/agt/agent-governance-python/agent-mesh/src/agentmesh/governance/backend.py")
    if not os.path.exists(p): pytest.skip("AGT checkout not present")
    spec = importlib.util.spec_from_file_location("agt_backend_real", p); m = importlib.util.module_from_spec(spec)
    import sys; sys.modules["agt_backend_real"] = m; spec.loader.exec_module(m); return m

def test_agt_backend_satisfies_the_real_protocol_and_registry():
    from adapters.agt_backend import StandingEvidenceBackend
    agt = _agt_protocol()
    b = StandingEvidenceBackend(rcv(), lambda action, ev, ctx: True)
    assert isinstance(b, agt.ExternalPolicyBackend)
    agt.BackendRegistry.register(b)
    assert agt.BackendRegistry.get("standing-mark-evidence") is b and b.healthy()
    agt.BackendRegistry.unregister("standing-mark-evidence")

@pytest.mark.parametrize("outcome", ["TRANSITION_ALLOWED", "NOT_ESTABLISHED", "BOUNDED_DETERMINATION"])
@pytest.mark.parametrize("rule_says", [True, False])
def test_agt_allowed_equals_the_receivers_rule_never_the_finding(outcome, rule_says):
    from adapters.agt_backend import StandingEvidenceBackend
    b = StandingEvidenceBackend(rcv(), lambda action, ev, ctx: rule_says)
    d = b.evaluate("export", {"standing_mark": good(outcome)})
    assert d.allowed is rule_says
    assert d.raw_response["evidence"]["examination"]["outcome"] == outcome

def test_agt_rule_sees_evidence_including_absence_and_forgery():
    from adapters.agt_backend import StandingEvidenceBackend
    got = []
    b = StandingEvidenceBackend(rcv(), lambda a, ev, c: got.append(ev) or False)
    b.evaluate("export", {})
    forged = good(); forged["payload"]["standing"]["outcome"] = "FORGED"
    b.evaluate("export", {"standing_mark": forged})
    assert got[0]["problems"] == ["NO_MARK_SUPPLIED"] and got[0]["mark_verified"] is False
    assert got[1]["mark_verified"] is False and got[1]["reception"]["state"] == "RECEIVED_WITH_PROBLEMS"

def test_agt_requires_a_rule():
    from adapters.agt_backend import StandingEvidenceBackend
    with pytest.raises(TypeError): StandingEvidenceBackend(rcv(), None)

# ---------- OpenAI Agents SDK ----------
def _guard_data(args, tool="send_funds"):
    from agents.tool_context import ToolContext
    from agents.guardrail import ToolInputGuardrailData  # noqa
    return None

def _run_guard(guard, args, tool="send_funds"):
    from types import SimpleNamespace
    data = SimpleNamespace(context=SimpleNamespace(tool_name=tool, tool_arguments=json.dumps(args)), agent=None)
    return asyncio.run(guard.run(data)) if hasattr(guard, "run") else guard.guardrail_function(data)

def test_openai_guardrail_carries_evidence_and_rule_decides():
    from adapters.openai_agents_guardrail import standing_evidence_guardrail
    from agents import ToolInputGuardrail
    for verdict in (True, False):
        g = standing_evidence_guardrail(rcv(), lambda tool, args: (args.get("mark"), CLAIM), lambda tool, args, ev: verdict)
        assert isinstance(g, ToolInputGuardrail)
        out = _run_guard(g, {"mark": good("NOT_ESTABLISHED")})
        assert out.behavior["type"] == ("allow" if verdict else "reject_content")
        assert out.output_info["examination"]["outcome"] == "NOT_ESTABLISHED" and out.output_info["binding"]["question_match"] == "MATCH"

def test_openai_guardrail_without_mark_still_defers_to_rule():
    from adapters.openai_agents_guardrail import standing_evidence_guardrail
    seen = []
    g = standing_evidence_guardrail(rcv(), lambda t, a: None, lambda t, a, ev: seen.append(ev) or False)
    out = _run_guard(g, {})
    assert seen[0]["problems"] == ["NO_MARK_SUPPLIED"] and out.behavior["type"] == "reject_content"

def test_openai_guardrail_runs_inside_a_real_function_tool():
    """Attach to an actual FunctionTool and invoke the SDK's own guardrail path."""
    from agents import function_tool
    from adapters.openai_agents_guardrail import standing_evidence_guardrail
    g = standing_evidence_guardrail(rcv(), lambda t, a: a.get("mark"), lambda t, a, ev: ev["mark_verified"])
    @function_tool(tool_input_guardrails=[g])
    def move(amount: int, mark: str = "") -> str:
        """Move funds."""
        return "moved"
    assert move.tool_input_guardrails == [g]

def test_openai_requires_rule():
    from adapters.openai_agents_guardrail import standing_evidence_guardrail
    with pytest.raises(TypeError): standing_evidence_guardrail(rcv(), lambda t, a: None, None)

# ---------- LangChain / LangGraph ----------
def _lc_request(args):
    from types import SimpleNamespace
    return SimpleNamespace(tool_call={"name": "send_funds", "args": args, "id": "call_1"})

def test_langchain_middleware_runs_tool_with_evidence_when_rule_says_so():
    from langchain_core.messages import ToolMessage
    from adapters.langchain_middleware import StandingEvidenceMiddleware
    mw = StandingEvidenceMiddleware(rcv(), lambda tc: (tc["args"].get("mark"), CLAIM), lambda tc, ev: True)
    res = mw.wrap_tool_call(_lc_request({"mark": good()}), lambda r: ToolMessage(content="ok", tool_call_id="call_1", name="send_funds"))
    assert res.content == "ok" and res.additional_kwargs["standing_evidence"]["examination"]["outcome"] == "TRANSITION_ALLOWED"

def test_langchain_middleware_holds_when_rule_says_so_and_never_calls_tool():
    from adapters.langchain_middleware import StandingEvidenceMiddleware
    called = []
    mw = StandingEvidenceMiddleware(rcv(), lambda tc: tc["args"].get("mark"), lambda tc, ev: False)
    res = mw.wrap_tool_call(_lc_request({"mark": good("TRANSITION_ALLOWED")}), lambda r: called.append(1))
    assert called == [] and res.status == "error"
    assert res.additional_kwargs["standing_evidence"]["examination"]["outcome"] == "TRANSITION_ALLOWED"   # a positive finding did not force a run

def test_langchain_async_path():
    from langchain_core.messages import ToolMessage
    from adapters.langchain_middleware import StandingEvidenceMiddleware
    mw = StandingEvidenceMiddleware(rcv(), lambda tc: tc["args"].get("mark"), lambda tc, ev: ev["mark_verified"])
    async def h(r): return ToolMessage(content="ok", tool_call_id="call_1", name="send_funds")
    assert asyncio.run(mw.awrap_tool_call(_lc_request({"mark": good()}), h)).content == "ok"
    assert asyncio.run(mw.awrap_tool_call(_lc_request({}), h)).status == "error"

def test_langchain_middleware_is_accepted_by_create_agent():
    from langchain.agents import create_agent
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
    from adapters.langchain_middleware import StandingEvidenceMiddleware
    mw = StandingEvidenceMiddleware(rcv(), lambda tc: None, lambda tc, ev: False)
    agent = create_agent(GenericFakeChatModel(messages=iter([])), tools=[], middleware=[mw])
    assert agent is not None

def test_langchain_requires_rule():
    from adapters.langchain_middleware import StandingEvidenceMiddleware
    with pytest.raises(TypeError): StandingEvidenceMiddleware(rcv(), lambda tc: None, None)
