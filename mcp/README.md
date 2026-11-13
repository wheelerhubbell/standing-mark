# Standing Mark MCP adapter

A local stdio adapter for the HTTP examination service operated by Wheeler Hubbell Publishing, Inc. Python 3.9+ is sufficient; no third-party runtime packages, API key or new account are needed to read the contract and issuer key. Paid examinations require a caller-authorized USDC transfer on Base.

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
- `standing_request_examination` accepts `{"claim": <the complete request object>}`. Without payment headers it requests a quote, not a paid examination. Keep the complete object unchanged on retry.
- `standing_verify` accepts `{"result": {"envelope": <signed envelope>, "public_key": "<SPKI DER base64>"}}`. This checks a signature only.
- Only after the caller has authorized and sent the exact transfer, set `WHP_QUOTE_ID` and `WHP_PAYMENT_TX` for the identical examination retry. The adapter never holds keys, signs transfers or pays.

Run the free discovery/local-vector check, which never calls `/v1/evaluate`:

```sh
python3 scripts/check_discovery.py
```

There is no hosted `/mcp` endpoint in the production service. The checked-in `server.json` is source-install discovery metadata, not a claim of a published package or accepted registry record. No PyPI package is advertised.

See [quick-start](../docs/quick-start.md), [payment](../docs/payment.md) and [independent verification](../docs/verification.md).
