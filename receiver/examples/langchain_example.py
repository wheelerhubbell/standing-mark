"""LangChain / LangGraph: add the middleware to an agent. Synthetic TEST fixture; no model call is made."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from standing_receiver import StandingReceiver, testing as T
from adapters.langchain_middleware import StandingEvidenceMiddleware
mw = StandingEvidenceMiddleware(StandingReceiver([T.TEST_PUBLIC_B64], "langchain-example"),
                                locate_mark=lambda tc: tc["args"].get("standing_mark"),
                                receiver_rule=lambda tc, ev: ev["mark_verified"])             # receiver's own rule
agent = create_agent(GenericFakeChatModel(messages=iter([])), tools=[], middleware=[mw])
print("agent built with", type(mw).__name__)
