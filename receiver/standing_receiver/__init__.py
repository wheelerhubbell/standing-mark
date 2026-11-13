"""Standing Receiving Kit (common core).

Wheeler Hubbell Publishing's open receiving-side code for Standing Mark results.
It builds requests in the examination service's real input shape, verifies signed
results offline against a key the receiver pinned, and returns plain evidence.

The kit never allows, denies, accepts or authorizes anything. The receiving
organization's own policy decides. See receiver/README.md.
"""
from .request import build_request, from_nested_shape, RequestError, ExaminationRequest
from .verify import verify_envelope, SignatureResult
from .evidence import build_evidence, KIT_STATEMENT
from .receiver import StandingReceiver, SeenStore, ReceptionResult
from .receipt import build_reception_record, verify_receipt, ReceiptCheck
from .exchange import object_id, link, verify_chain
from .client import ExaminationClient, QuoteRequired

__version__ = "0.1.1"
