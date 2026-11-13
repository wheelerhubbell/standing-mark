"""OpenAI Agents SDK: attach the guardrail to a function tool. Synthetic TEST fixture; no model call is made."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents import function_tool
from standing_receiver import StandingReceiver, testing as T
from adapters.openai_agents_guardrail import standing_evidence_guardrail
guard = standing_evidence_guardrail(StandingReceiver([T.TEST_PUBLIC_B64], "agents-example"),
                                    locate_mark=lambda tool, args: args.get("standing_mark"),
                                    receiver_rule=lambda tool, args, ev: ev["mark_verified"])   # receiver's own rule
@function_tool(tool_input_guardrails=[guard])
def release_payment(invoice_id: str, standing_mark: str = "") -> str:
    """Release a payment."""
    return "released " + invoice_id
print("tool", release_payment.name, "has", len(release_payment.tool_input_guardrails), "input guardrail(s)")
