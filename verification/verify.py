#!/usr/bin/env python3
"""Independent offline verification of a signed Standing Mark result.

Checks, with no trust in the service:
  1. The published issuer key pins to its published key id (SHA-256 of SPKI DER).
  2. The envelope's protected header names the pinned key, Ed25519 and WHP-JCS-I1.
  3. The Ed25519 signature verifies over the WHP-JCS-I1 canonical bytes of
     {"protected": ..., "payload": ...} against the pinned key.

What this establishes: the signature on the exact bound object, by the pinned key.
What it does not establish: object binding to your question, policy acceptance,
current standing, or that the key is authoritative for a given object. Those are
receiver-side checks (see docs/quick-start.md).

Usage: python3 verify.py signed-result.json [expected-public-key-spki-base64]
Without the second argument the issuer key is pinned from the live issuer document.
Pass the published RFC 8032 TEST 1 key for the test fixture vector.
Requires: Python 3.9+ and the 'cryptography' package.
"""
import sys, json, hashlib, base64, urllib.request

ISSUER_URL = "https://decisionintegrity.wheelerhubbellpublishing.com/.well-known/whp-issuer.json"

def utf16_order(s):
    return s.encode("utf-16-be")

def jcs_string(s):
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
        elif 0xD800 <= o <= 0xDFFF: raise ValueError("unpaired surrogate: rejected by WHP-JCS-I1")
        else: out.append(ch)
    out.append('"')
    return ''.join(out)

def jcs(v):
    if v is None: return "null"
    if v is True: return "true"
    if v is False: return "false"
    if isinstance(v, int):
        if abs(v) > 9007199254740991: raise ValueError("unsafe integer: rejected by WHP-JCS-I1")
        return str(v)
    if isinstance(v, float): raise ValueError("floating-point token: rejected by WHP-JCS-I1")
    if isinstance(v, str): return jcs_string(v)
    if isinstance(v, list): return "[" + ",".join(jcs(x) for x in v) + "]"
    if isinstance(v, dict):
        items = sorted(v.items(), key=lambda kv: utf16_order(kv[0]))
        return "{" + ",".join(jcs_string(k) + ":" + jcs(x) for k, x in items) + "}"
    raise TypeError(type(v))

def main(path, expected_key_b64=None):
    env = json.load(open(path))
    if expected_key_b64:
        pk_der = base64.b64decode(expected_key_b64)
        kid = hashlib.sha256(pk_der).hexdigest()
        print("expected key pinned from argument:", kid)
    else:
        issuer = json.loads(urllib.request.urlopen(ISSUER_URL, timeout=30).read().decode())
        pk_der = base64.b64decode(issuer["public_key"])
        kid = hashlib.sha256(pk_der).hexdigest()
        assert kid == issuer["key_id_sha256"], "published key does not pin to published key id"
        print("issuer key pinned:", kid)

    prot = env["protected"]
    assert prot.get("algorithm") == "Ed25519", "unexpected algorithm"
    assert prot.get("canonicalization") == "WHP-JCS-I1", "unexpected canonicalization"
    assert prot.get("key_id") == kid, "envelope names a different key than the pinned issuer key"
    print("protected header names the pinned key, Ed25519, WHP-JCS-I1")

    signing_bytes = jcs({"protected": env["protected"], "payload": env["payload"]}).encode("utf-8")
    from cryptography.hazmat.primitives.serialization import load_der_public_key
    load_der_public_key(pk_der).verify(base64.b64decode(env["signature"]), signing_bytes)
    print("Ed25519 signature: VALID over", len(signing_bytes), "canonical bytes")
    print()
    print("Established: the pinned issuer key signed this exact object.")
    print("Not established: object binding to your own question, current standing, policy acceptance.")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "signed_result.json", sys.argv[2] if len(sys.argv) > 2 else None)
