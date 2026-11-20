# Standing Mark MCP adapter

A local stdio adapter for the HTTP examination service operated by Wheeler Hubbell Publishing, Inc. Python 3.9+ is sufficient; no third-party runtime packages, API key or new account are needed to read the contract and issuer key. Paid examinations use x402 v2 (`exact`): exactly 1.00 USDC on Base, an EIP-3009 `transferWithAuthorization` the caller signs; the facilitator submits the transaction, so no customer ETH gas is required.

## Install from source

```sh
git clone https://github.com/wheelerhubbell/standing-mark.git
cd standing-mark
python3 mcp/standing_mark_mcp.py
```

In an MCP client, use the absolute local path after cloning:

```json
{
  "mcpServers": {
    "standing-mark": {
      "command": "python3",
      "args": ["/absolute/path/to/standing-mark/mcp/standing_mark_mcp.py"]
    }
  }
}
```

The adapter reads newline-delimited JSON-RPC on stdin and writes responses to stdout. It exposes `standing_contract`, `standing_issuer`, `standing_request_examination` and `standing_verify`.

- `standing_contract` and `standing_issuer` accept `{}` and perform free GETs.
- `standing_request_examination` accepts the examination request directly: `{"claim": "<the proposition, as a string>", "data": "<the examination material, as a string>", "provenance": {"source": ..., "evidence": [...]}, "warrant": ..., "requested_operation": "INFORM"}`. The accepted input schema is `input_schema` in the live contract. Without a payment header the answer is the 402 x402 v2 terms, not a paid examination. Keep the complete object unchanged on retry.
- `standing_verify` accepts `{"result": {"envelope": <signed envelope>, "public_key": "<SPKI DER base64>"}}`. This checks a signature only.
- Payment retry: the caller signs the EIP-3009 authorization and supplies the x402 v2 envelope for the identical retry. The adapter never holds keys, signs authorizations or pays. Note: the adapter's retired `WHP_QUOTE_ID`/`WHP_PAYMENT_TX` retry path (scheme `WHP-BASE-USDC-FLAT-1`) is not accepted by the live service; the paid-retry helper is being updated to x402 v2.

Run the free discovery/local-vector check, which never calls `/v1/evaluate`:

```sh
python3 scripts/check_discovery.py
```

There is no hosted `/mcp` endpoint in the production service. The checked-in `server.json` is source-install discovery metadata, not a claim of a published package or accepted registry record. No PyPI package is advertised.

See [quick-start](../docs/quick-start.md), [payment](../docs/payment.md) and [independent verification](../docs/verification.md).

For the full optional local-signature checks, install Node.js 18+ and the Python `cryptography` package. The discovery script reports SKIP for an unavailable signature runtime; the stdlib discovery and MCP checks still run.
