"""OpenAI Agents SDK: tool input guardrail carrying Standing Mark evidence.

locate_mark(tool_name, arguments_dict) -> Standing Mark (dict/str/bytes) or None, or a tuple
(mark, expected_proposition). receiver_rule(tool_name, arguments, evidence) -> True to let the tool
run, False to reject, or a ToolGuardrailFunctionOutput for full control. The guardrail has no
default and never derives a verdict from a finding. Evidence is returned in output_info.
"""
import json
from agents import ToolGuardrailFunctionOutput, ToolInputGuardrail
from ._common import evidence_for, require_rule

def standing_evidence_guardrail(receiver, locate_mark, receiver_rule, reject_message="Held by the receiving organization's policy.", name="standing_mark_evidence"):
    require_rule(receiver_rule)
    def _fn(data):
        raw = getattr(data.context, "tool_arguments", None) or "{}"
        try:
            args = json.loads(raw) if isinstance(raw, str) else dict(raw)
        except ValueError:
            args = {}
        found = locate_mark(data.context.tool_name, args)
        mark, expected = found if isinstance(found, tuple) else (found, None)
        ev = evidence_for(receiver, mark, expected)
        verdict = receiver_rule(data.context.tool_name, args, ev)
        if isinstance(verdict, ToolGuardrailFunctionOutput):
            verdict.output_info = verdict.output_info if verdict.output_info is not None else ev
            return verdict
        if verdict:
            return ToolGuardrailFunctionOutput.allow(output_info=ev)
        return ToolGuardrailFunctionOutput.reject_content(reject_message, output_info=ev)
    return ToolInputGuardrail(guardrail_function=_fn, name=name)
