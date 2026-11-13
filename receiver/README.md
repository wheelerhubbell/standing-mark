# Standing Receiving Kit

Open receiving-side code from Wheeler Hubbell Publishing for Standing Mark results. Version 0.1.0 (local release candidate).

A system that is about to act asks a hook "should this proceed?". Standing Mark answers a narrower question: here is a signed, dated examination of the grounds, bound to the exact material examined. This kit puts that result where the hook already exists and hands the receiving system plain evidence. The receiving system's own policy decides.

## Four layers, four owners

| Layer | What it is | Owner |
|---|---|---|
| Decision Integrity | The method for examining the standing of a claim, record or proposed action | Wheeler Hubbell Publishing |
| Standing Mark | The paid examination service: material in, signed result out. 1.00 USDC flat, paid by the caller | Wheeler Hubbell Publishing |
| Receiving kit (this directory) | Builds requests, verifies results offline, reports evidence, records reception | Wheeler Hubbell Publishing, open source |
| Receiver policy | What a result permits inside your system | The receiving organization, always |

## What the kit does not do

It does not allow, deny, accept or authorize anything. A result of `NOT_ESTABLISHED` or a bounded determination is a delivered examination and is reported as stated, never mapped to allow or deny. Every adapter requires the receiver to supply its own rule; there is no default. A reception record establishes that a result was received and matches what was issued. It does not establish understanding, agreement, acceptance or authorization.

## 60-second demonstration

```sh
python3 -m pip install cryptography
python3 receiver/examples/demo_60s.py
```

Offline. No payment, no network call, no live service. It uses synthetic test fixtures signed with the public RFC 8032 TEST 1 key, so it proves the kit's behavior, not anything about the live service.

## Pieces

| Piece | Where |
|---|---|
| Request construction in the service's real input shape, refused locally when proposition or material is missing | `standing_receiver/request.py` |
| Offline signature verification against a key you pin | `standing_receiver/verify.py` |
| Evidence object | `standing_receiver/evidence.py` |
| Standing Receiver (issuer pinning, signature, completeness, freshness, alteration, replay, original preserved) | `standing_receiver/receiver.py` |
| Standing Receipt record and verifier | `standing_receiver/receipt.py`, [spec](docs/standing-receipt.md) |
| Exchange protocol (object identity and linkage) | `standing_receiver/exchange.py`, [spec](docs/exchange-protocol.md) |
| Client that never pays | `standing_receiver/client.py` |
| Adapters: Microsoft Agent Governance Toolkit, OpenAI Agents SDK, LangChain/LangGraph | `adapters/` |
| Conformance vectors with two independent implementations (Python kit, Node.js verifier) | `conformance/`, [spec](docs/conformance.md) |

## Request shape

The service reads the proposition from `claim` and the material from `data`, both plain strings, with an optional `source`, `provenance.evidence` (list of strings), `warrant`, `subject`, `requested_operation` and `bounds`. Objects under `claim` or `material` are not read. `build_request()` refuses them, and refuses an empty proposition or empty material, before any quote is requested.

## Tests

```sh
python3 -m pip install cryptography pytest openai-agents langchain langgraph
python3 -m pytest receiver -q
python3 receiver/conformance/run.py
node receiver/conformance/run.js
```

Publication of this kit and any adoption by an external organization are separate facts from its existence. Nothing in this directory claims either.
