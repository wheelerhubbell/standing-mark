# The payment mechanism: WHP-BASE-USDC-QUOTE-1

The live contract at `GET /v1/contract` is authoritative. Summary as of November 13, 2026:

- Scheme: `WHP-BASE-USDC-QUOTE-1`. This is not x402-exact and is not represented as x402.
- Network: `eip155:8453` (Base). Asset: USDC `0x833589fcd6edb6e08f4c7c32d4f71b54bda02913`, 6 decimals.
- Price: 1.000001 to 1.009999 USDC per examination, subject to operator approval. The exact amount is per-quote.
- Minimum confirmations: 5.

## Request binding

The quote is bound to the exact request bytes. `POST /v1/evaluate` without payment returns 402 with `payment_required.quote_id`, `amount_units`, `pay_to` and `expires`. The same bytes always price within the declared range; different bytes get their own quote. To complete, retry the identical body with `X-WHP-Quote` and `X-WHP-Payment-Tx` (the on-chain transaction hash). A quote that is not paid expires on its own and consumes nothing.

## Economic rule

Payment compensates the examination work regardless of outcome: a signed record that names what is not established is a delivered examination, not a failed purchase. One payment issues at most one signed result.
