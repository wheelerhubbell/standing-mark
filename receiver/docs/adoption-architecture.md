# Adoption architecture

How a receiving system incorporates a Standing Mark without ceding any authority.

## The slot

Agent runtimes and policy layers already have a hook before an action: OpenAI Agents SDK tool input guardrails, LangChain agent middleware around tool calls, Microsoft Agent Governance Toolkit policy backends. Each asks something to say proceed, hold or reject. None of them carries a signed examination of the grounds for the action. The kit fills that slot as evidence, once, behind three thin adapters.

## Path of one action

1. The caller builds a request in the service's real shape (`build_request`). Empty or wrongly shaped requests never reach a quote.
2. The caller, or a platform paying on the caller's behalf, pays the flat 1.00 USDC and receives a signed result. The kit never pays.
3. The result travels with the action. At the hook, the adapter calls the Standing Receiver: issuer pinned, signature, completeness, freshness, alteration, replay, original preserved.
4. The adapter passes the evidence object to the receiver's own rule. The rule returns proceed or hold. The kit does not.
5. Optionally a reception record and exchange chain are kept for audit.

## Who decides what

| Question | Decided by |
|---|---|
| Was the examination done as stated and signed by the pinned key | Standing Receiver check |
| What the finding says | Wheeler Hubbell Publishing's signed result, reported verbatim |
| Whether a finding permits the action | The receiving organization's rule |
| Whether the receiver accepted or authorized anything | The receiver, in its own `receiver_response` |

## Commercial model

Caller pays 1.00 USDC per examination. A platform may pay on its callers' behalf at the same price. The kit and the verifier are free and open. No account, key or new payment mechanism is added.

## Discovery routes already in place (not adoption)

Official MCP Registry record, SKILL.md and A2A card in the standing-mark repository, open directory submissions. These make the service findable. They are not evidence that anyone uses it.

## Not built here

Hosted MCP endpoint, AWS and Docker listings, Bazaar extension, package-registry distribution, hosted receipt issuance.
