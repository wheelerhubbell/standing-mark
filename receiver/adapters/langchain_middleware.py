"""LangChain / LangGraph: agent middleware carrying Standing Mark evidence.

Wraps tool calls. locate_mark(tool_call) -> mark or (mark, expected_proposition) or None.
receiver_rule(tool_call, evidence) -> True to run the tool, False to return a tool error message to
the model. No default rule; the kit does not decide. Evidence is stored in the tool message's
artifact-free metadata via additional_kwargs["standing_evidence"] when the tool runs.
"""
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from ._common import evidence_for, require_rule

class StandingEvidenceMiddleware(AgentMiddleware):
    def __init__(self, receiver, locate_mark, receiver_rule, hold_message="Held by the receiving organization's policy."):
        super().__init__()
        self._receiver, self._locate, self._rule, self._msg = receiver, locate_mark, require_rule(receiver_rule), hold_message

    def _evidence(self, request):
        found = self._locate(request.tool_call)
        mark, expected = found if isinstance(found, tuple) else (found, None)
        return evidence_for(self._receiver, mark, expected)

    def _held(self, request, ev):
        return ToolMessage(content=self._msg, tool_call_id=request.tool_call["id"], name=request.tool_call["name"],
                           status="error", additional_kwargs={"standing_evidence": ev})

    def wrap_tool_call(self, request, handler):
        ev = self._evidence(request)
        if not self._rule(request.tool_call, ev):
            return self._held(request, ev)
        result = handler(request)
        if isinstance(result, ToolMessage):
            result.additional_kwargs["standing_evidence"] = ev
        return result

    async def awrap_tool_call(self, request, handler):
        ev = self._evidence(request)
        if not self._rule(request.tool_call, ev):
            return self._held(request, ev)
        result = await handler(request)
        if isinstance(result, ToolMessage):
            result.additional_kwargs["standing_evidence"] = ev
        return result
