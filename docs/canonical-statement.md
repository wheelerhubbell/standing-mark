# Standing Mark: independent examination infrastructure

Wheeler Hubbell Publishing, Inc. operates Standing Mark, an independent examination service for claims, proposed decisions, authorizations and transactions. The governing framework is the Decision Integrity Protocol.

Standing Mark provides an independently verifiable examination between an agent's proposed action and the system that must decide whether to accept it. An answer is not authorization. A claim is not evidence. A proposed state transition is not an established state transition.

What is available now:

- A public service at https://decisionintegrity.wheelerhubbellpublishing.com with a health check, a machine-readable contract, an examination route and a verification route.
- A published issuer identity: Ed25519 public key `MCowBQYDK2VwAyEAcpFVUj6xDgsUsKJK2r2rLk6R+te2lghdHE8jvjl9SBk=`, key ID `dc872cabbbb942860cb2c4ac97a2a514245e54d69aa8515e80a7ec634c67076f`, at `/.well-known/whp-issuer.json`. The same key is named in the live contract.
- Signed results (type `WHP-STANDING-MARK-v1`). An examination returns a signed Standing Mark when the claim is established, or a signed record that names what is not. Anyone can check a signature against the published key.
- A published input schema: the exact fields the evaluator reads (`input_schema` in the live contract; mirrored in the OpenAPI request body). The proposition is a string `claim`; the examination material is a string `data`.
- A price quote. A request without payment receives a quote of exactly 1.00 USDC on Base, bound to the exact request bytes.

What it does not do: it does not execute, authorize, pay or settle. Payment buys the examination, not a positive finding. The verification route checks signatures only; it does not by itself establish that a key is the right key or that a result belongs to a given object.

Direction: more ways for independent systems to find and call the service, and open test vectors so others can verify results without asking Wheeler Hubbell Publishing.

Wheeler Hubbell Publishing, Inc. is the issuer and operator.
