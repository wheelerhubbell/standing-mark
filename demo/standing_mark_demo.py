#!/usr/bin/env python3
"""Standing Mark reproducible demonstration.

Shows, step by step:
  1. An agent (or its operator) reads the live service contract.
  2. The verifier pins the published issuer key.
  3. An agent submits a proposed action for examination.
  4. The service answers with a price quote bound to the exact request bytes (402).
  5. (Prepared, not run without a payment decision) pay the quote on Base and retry
     with X-WHP-Quote / X-WHP-Payment-Tx to receive the signed examination result.
  6. An independent verifier checks a signed result: server-side signature check
     (POST /v1/verification) and offline key pinning + Ed25519 verification.

Standard library only for steps 1-5. Step 6 offline signature verification uses the
'cryptography' package when available. No wallet, no keys, no spending is performed
by this script unless the operator supplies a real quote id and transaction hash via
environment variables WHP_QUOTE_ID and WHP_PAYMENT_TX.
"""
import json, os, sys, hashlib, urllib.request, urllib.error

BASE = "https://decisionintegrity.wheelerhubbellpublishing.com"

PROPOSED_ACTION = {
    "claim": {
        "type": "proposed_action",
        "actor": "demo-agent-1",
        "action": "transfer 250.00 USDC to supplier 0xExample",
        "warrant": "Purchase order PO-1042 approved by operations on 2026-11-12",
        "conditions": ["amount <= 300 USDC", "destination on approved supplier list"]
    },
    "material": {
        "purchase_order": "PO-1042, 250.00 USDC, supplier 0xExample, approved 2026-11-12",
        "supplier_list": ["0xExample"]
    }
}

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.loads(r.read().decode())

def post(path, body, headers=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **(headers or {})},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try: return e.code, json.loads(raw)
        except json.JSONDecodeError: return e.code, {"raw": raw}

def _jcs_str(s):
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"': out.append('\\"')
        elif ch == '\\': out.append('\\\\')
        elif ch == '\b': out.append('\\b')
        elif ch == '\t': out.append('\\t')
        elif ch == '\n': out.append('\\n')
        elif ch == '\f': out.append('\\f')
        elif ch == '\r': out.append('\\r')
        elif o < 0x20: out.append('\\u%04x' % o)
        else: out.append(ch)
    out.append('"')
    return ''.join(out)

def jcs(v):
    """WHP-JCS-I1 canonical form (see verification/verify.py for the documented version)."""
    if v is None: return "null"
    if v is True: return "true"
    if v is False: return "false"
    if isinstance(v, bool): raise TypeError
    if isinstance(v, int):
        if abs(v) > 9007199254740991: raise ValueError("unsafe integer: rejected by WHP-JCS-I1")
        return str(v)
    if isinstance(v, float): raise ValueError("floating-point token: rejected by WHP-JCS-I1")
    if isinstance(v, str): return _jcs_str(v)
    if isinstance(v, list): return "[" + ",".join(jcs(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ",".join(_jcs_str(k) + ":" + jcs(x) for k, x in sorted(v.items(), key=lambda kv: kv[0].encode("utf-16-be"))) + "}"
    raise TypeError(type(v))

def step(n, text):
    print(f"\n=== Step {n}: {text} ===")

def main():
    step(1, "Read the live contract")
    contract = get("/v1/contract")
    print("profile:", contract["profile"])
    print("payment scheme:", contract["payment"]["scheme"], "| not_x402_exact:", contract["payment"]["not_x402_exact"])
    print("signed type:", contract["signed_type"], "| determinism:", contract["determinism"])

    step(2, "Pin the published issuer key")
    issuer = get("/.well-known/whp-issuer.json")
    key_b64 = issuer["public_key"]
    import base64
    kid = hashlib.sha256(base64.b64decode(key_b64)).hexdigest()
    print("published key_id:", issuer["key_id_sha256"])
    print("recomputed key_id:", kid, "| match:", kid == issuer["key_id_sha256"])
    assert kid == issuer["key_id_sha256"], "issuer key id does not match the published key"

    step(3, "An agent submits a proposed action for examination")
    print(json.dumps(PROPOSED_ACTION, indent=2)[:400], "...")

    step(4, "Unpaid request: the service quotes a price bound to the exact bytes")
    status, body = post("/v1/evaluate", PROPOSED_ACTION)
    print("HTTP", status, json.dumps(body, indent=2)[:600])
    if status != 402:
        print("unexpected status; contract changed? re-read /v1/contract"); sys.exit(1)
    quote = body.get("payment_required", {})
    qid = quote.get("quote_id")
    print("quote_id:", qid, "| amount_units:", quote.get("amount_units"),
          "| pay_to:", quote.get("pay_to"), "| expires:", quote.get("expires"))

    step(5, "Payment (prepared; runs only when the operator supplies a real payment)")
    qid_env, tx_env = os.environ.get("WHP_QUOTE_ID"), os.environ.get("WHP_PAYMENT_TX")
    if qid_env and tx_env:
        status, result = post("/v1/evaluate", PROPOSED_ACTION,
                              {"X-WHP-Quote": qid_env, "X-WHP-Payment-Tx": tx_env})
        print("HTTP", status)
        if status == 200:
            with open("signed_result.json", "w") as f: json.dump(result, f, indent=2)
            print("signed result saved to signed_result.json")
        else:
            print(json.dumps(result, indent=2)[:600]); sys.exit(1)
    else:
        print("skipped: set WHP_QUOTE_ID and WHP_PAYMENT_TX to run the paid step.")
        print("(The quote above expires on its own; nothing is consumed.)")

    step(6, "Independent verification of a signed result")
    path = "signed_result.json"
    if not os.path.exists(path):
        print("no signed_result.json present; provide a signed result file to verify.")
        print("server-side check: POST the result to /v1/verification (signature only).")
        return
    result = json.load(open(path))
    status, verdict = post("/v1/verification", {"envelope": result, "public_key": key_b64})
    print("server-side verification: HTTP", status, json.dumps(verdict, indent=2)[:400])
    try:
        from cryptography.hazmat.primitives.serialization import load_der_public_key
        import base64 as b64
        pk = load_der_public_key(b64.b64decode(key_b64))
        sig = b64.b64decode(result["signature"])
        signed_bytes = jcs({"protected": result["protected"], "payload": result["payload"]}).encode("utf-8")
        pk.verify(sig, signed_bytes)
        print("offline Ed25519 verification: VALID against pinned key", kid[:12], "...")
    except ImportError:
        print("offline check skipped: install 'cryptography' for offline Ed25519 verification")
    except Exception as e:
        print("offline Ed25519 verification: FAILED -", type(e).__name__, e)
    print("\nWhat was established: the signature on the result, against the published issuer key.")
    print("What was not established: object binding and policy acceptance remain the receiver's own checks.")

if __name__ == "__main__":
    main()
