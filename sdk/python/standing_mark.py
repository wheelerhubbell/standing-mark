"""Standing Mark client SDK (Python, standard library only).

Covers the free surface: read the contract, read and pin the issuer key,
request an examination quote (402), and check signed results remotely and
offline. The paid retry is the caller's decision: this SDK never pays.

Docs: docs/quick-start.md. Live contract is the source of truth:
https://decisionintegrity.wheelerhubbellpublishing.com/v1/contract
"""
import json, hashlib, base64, urllib.request, urllib.error

DEFAULT_BASE = "https://decisionintegrity.wheelerhubbellpublishing.com"

class QuoteRequired(Exception):
    """An unpaid examination request was answered with a price quote."""
    def __init__(self, quote, raw):
        super().__init__("payment required: %s units to %s, quote %s"
                         % (quote.get("amount_units"), quote.get("pay_to"), quote.get("quote_id")))
        self.quote = quote
        self.raw = raw

def _req(method, base, path, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(base + path, data=data, method=method,
                               headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read().decode())
        except ValueError: return e.code, {"error": "unparsable body"}

class StandingMark:
    def __init__(self, base=DEFAULT_BASE):
        self.base = base.rstrip("/")

    def contract(self):
        """The live contract: routes, payment terms, limits. Read at time of use."""
        return _req("GET", self.base, "/v1/contract")[1]

    def issuer(self):
        """Published issuer identity (Ed25519 SPKI DER base64 + key id)."""
        return _req("GET", self.base, "/.well-known/whp-issuer.json")[1]

    def pinned_key(self):
        """Fetch the issuer key and pin it: returns (spki_der_bytes, key_id)."""
        iss = self.issuer()
        der = base64.b64decode(iss["public_key"])
        kid = hashlib.sha256(der).hexdigest()
        if kid != iss["key_id_sha256"]:
            raise ValueError("published key does not pin to published key id")
        return der, kid

    def request_examination(self, claim, quote_id=None, payment_tx=None):
        """Submit an examination request (dict in the accepted input schema: string "claim" proposition, string "data" material, provenance, warrant; see GET /v1/contract input_schema). Unpaid: raises QuoteRequired
        with the quote (bound to the exact request bytes). With quote_id and
        payment_tx after paying the quote on Base: returns the signed result."""
        headers = {}
        if quote_id and payment_tx:
            headers = {"X-WHP-Quote": quote_id, "X-WHP-Payment-Tx": payment_tx}
        status, body = _req("POST", self.base, "/v1/evaluate", claim, headers)
        if status == 402:
            raise QuoteRequired(body.get("payment_required", {}), body)
        if status != 200:
            raise RuntimeError("examination failed: HTTP %s %s" % (status, body))
        return body

    def verify_remote(self, signed_result, public_key_b64=None):
        """Server-side signature check (signature only; see contract scope)."""
        iss = self.issuer() if public_key_b64 is None else None
        body = {"envelope": signed_result,
                "public_key": public_key_b64 or iss["public_key"]}
        return _req("POST", self.base, "/v1/verification", body)[1]

    def verify_local(self, signed_result):
        """Offline Ed25519 check against the pinned issuer key.
        Requires the 'cryptography' package. Establishes the signature only."""
        try:
            from .jcs import jcs  # WHP-JCS-I1 canonical bytes
        except ImportError:
            from jcs import jcs  # single-file use
        der, kid = self.pinned_key()
        prot = signed_result.get("protected", {})
        if prot.get("key_id") != kid or prot.get("algorithm") != "Ed25519" \
           or prot.get("canonicalization") != "WHP-JCS-I1":
            raise ValueError("protected header does not match the pinned key and method")
        signing = jcs({"protected": signed_result["protected"],
                       "payload": signed_result["payload"]}).encode("utf-8")
        from cryptography.hazmat.primitives.serialization import load_der_public_key
        load_der_public_key(der).verify(base64.b64decode(signed_result["signature"]), signing)
        return True
