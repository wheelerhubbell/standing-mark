#!/usr/bin/env python3
# standing_mark_mcp.py - MCP stdio adapter for Standing Mark. Stdlib only.
import json, os, sys, urllib.request, urllib.error

BASE = os.environ.get("WHP_BASE", "https://decisionintegrity.wheelerhubbellpublishing.com")

TOOLS = [
  {"name": "standing_contract", "description": "Read the live Standing Mark contract: routes, payment terms, limits.",
   "inputSchema": {"type": "object", "properties": {}}},
  {"name": "standing_issuer", "description": "Read the published issuer identity (Ed25519 key).",
   "inputSchema": {"type": "object", "properties": {}}},
  {"name": "standing_request_examination", "description": "Submit a claim or proposed action (JSON object) for examination. Unpaid calls return a price quote (402) bound to the exact bytes. After paying the quote on Base, set WHP_QUOTE_ID and WHP_PAYMENT_TX and repeat to receive the signed result.",
   "inputSchema": {"type": "object", "properties": {"claim": {"type": "object"}}, "required": ["claim"]}},
  {"name": "standing_verify", "description": "Check a signed Standing Mark result (signature only). Pass {\"envelope\": <signed result>, \"public_key\": <SPKI DER base64 from standing_issuer>}.",
   "inputSchema": {"type": "object", "properties": {"result": {"type": "object"}}, "required": ["result"]}},
]

def http(method, path, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
        headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read().decode())
        except Exception: return e.code, {"error": str(e)}

def call(name, args):
    if name == "standing_contract": return http("GET", "/v1/contract")[1]
    if name == "standing_issuer": return http("GET", "/.well-known/whp-issuer.json")[1]
    if name == "standing_request_examination":
        h = {}
        if os.environ.get("WHP_QUOTE_ID") and os.environ.get("WHP_PAYMENT_TX"):
            h = {"X-WHP-Quote": os.environ["WHP_QUOTE_ID"], "X-WHP-Payment-Tx": os.environ["WHP_PAYMENT_TX"]}
        return http("POST", "/v1/evaluate", args["claim"], h)[1]
    if name == "standing_verify": return http("POST", "/v1/verification", args["result"])[1]
    return {"error": "unknown tool"}

def reply(rid, result=None, error=None):
    out = {"jsonrpc": "2.0", "id": rid}
    if error: out["error"] = {"code": -32603, "message": str(error)}
    else: out["result"] = result
    sys.stdout.write(json.dumps(out) + "\n"); sys.stdout.flush()

for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try: msg = json.loads(line)
    except Exception: continue
    m, rid = msg.get("method"), msg.get("id")
    if m == "initialize":
        reply(rid, {"protocolVersion": msg.get("params", {}).get("protocolVersion", "2025-06-18"),
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "standing-mark", "version": "1.0.0"}})
    elif m == "notifications/initialized":
        pass
    elif m == "tools/list":
        reply(rid, {"tools": TOOLS})
    elif m == "tools/call":
        p = msg.get("params", {})
        try: res = call(p.get("name"), p.get("arguments", {}) or {})
        except Exception as e: reply(rid, error=e); continue
        reply(rid, {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]})
    elif rid is not None:
        reply(rid, error="method not supported: %s" % m)
