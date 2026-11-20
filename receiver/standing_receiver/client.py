"""Calls the Standing Mark service. Never pays, never retries a quote on its own.

Unpaid submit raises PaymentRequired carrying the x402 v2 terms (accepts[0]). The caller (or a platform
paying on the caller's behalf) signs an EIP-3009 authorization for exactly those terms and calls submit
again with the x402 v2 envelope as payment_signature (sent in the payment-signature header). Tests use an injected
transport; nothing here runs against the live service unless a caller points it there.
"""
import json, urllib.request, urllib.error
from .request import ExaminationRequest

DEFAULT_BASE = "https://api.wheelerhubbellpublishing.com"
KIT_CLIENT_ID = "standing-receiver-kit/0.1.1"

class PaymentRequired(Exception):
    def __init__(self, terms):
        super().__init__("payment required: %s units of %s on %s" % (terms.get("amount"), terms.get("asset"), terms.get("network")))
        self.terms = terms

QuoteRequired = PaymentRequired  # name kept for callers written against earlier releases

def _urllib_transport(method, url, body, headers):
    r = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except ValueError:
            return e.code, {"error": "unparsable body"}

class ExaminationClient:
    def __init__(self, base=DEFAULT_BASE, transport=None):
        self.base, self.transport = base.rstrip("/"), transport or _urllib_transport

    def submit(self, request, payment_signature=None, expected_amount_units=None):
        if not isinstance(request, ExaminationRequest):
            raise TypeError("submit() takes an ExaminationRequest from build_request(); raw dicts are refused so an empty request cannot reach a quote")
        headers = {"Content-Type": "application/json", "X-Client": KIT_CLIENT_ID}
        if payment_signature:
            headers["payment-signature"] = payment_signature
        status, body = self.transport("POST", self.base + "/v1/evaluate", request.body_bytes, headers)
        if status == 402:
            q = (body.get("accepts") or [{}])[0]
            if expected_amount_units is not None and str(q.get("amount")) != str(expected_amount_units):
                raise RuntimeError("payment amount %r differs from the expected %r; refusing" % (q.get("amount"), expected_amount_units))
            raise PaymentRequired(q)
        if status != 200:
            raise RuntimeError("examination failed: HTTP %s %s" % (status, body))
        return body
