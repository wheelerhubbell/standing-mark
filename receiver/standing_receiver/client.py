"""Calls the Standing Mark service. Never pays, never retries a quote on its own.

Unpaid submit raises QuoteRequired. The caller (or a platform paying on the caller's behalf) pays
the quote and calls submit again with the quote id and transaction hash. Tests use an injected
transport; nothing here runs against the live service unless a caller points it there.
"""
import json, urllib.request, urllib.error
from .request import ExaminationRequest

DEFAULT_BASE = "https://api.wheelerhubbellpublishing.com"
KIT_CLIENT_ID = "standing-receiver-kit/0.1.1"

class QuoteRequired(Exception):
    def __init__(self, quote):
        super().__init__("payment required: %s units, quote %s" % (quote.get("amount_units"), quote.get("quote_id")))
        self.quote = quote

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

    def submit(self, request, quote_id=None, payment_tx=None, expected_amount_units=None):
        if not isinstance(request, ExaminationRequest):
            raise TypeError("submit() takes an ExaminationRequest from build_request(); raw dicts are refused so an empty request cannot reach a quote")
        headers = {"Content-Type": "application/json", "X-Client": KIT_CLIENT_ID}
        if quote_id and payment_tx:
            headers.update({"X-WHP-Quote": quote_id, "X-WHP-Payment-Tx": payment_tx})
        status, body = self.transport("POST", self.base + "/v1/evaluate", request.body_bytes, headers)
        if status == 402:
            q = body.get("payment_required", {})
            if expected_amount_units is not None and q.get("amount_units") != expected_amount_units:
                raise RuntimeError("quote amount %r differs from the expected %r; refusing" % (q.get("amount_units"), expected_amount_units))
            raise QuoteRequired(q)
        if status != 200:
            raise RuntimeError("examination failed: HTTP %s %s" % (status, body))
        return body
