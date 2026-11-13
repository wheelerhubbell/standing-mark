"""Request construction in the engine's real input shape.

The examination engine reads:
  claim   - the proposition, as a plain string
  data    - the examination material, as a plain string
  source / provenance.source     - a resolvable source reference (string)
  provenance.evidence            - verbatim supporting statements (list of strings)
  warrant / provenance.authority - needed only for operations that cross the decision boundary
  optional: subject, requested_operation, bounds

A request with no proposition or no material is refused here, before any quote or payment,
because a payment cannot buy an examination of nothing. Nested {"claim": {...}, "material": {...}}
objects are NOT sent as-is; they are rejected, or mapped only by the explicit, reported
from_nested_shape() helper.
"""
import hashlib
from dataclasses import dataclass, field
from .jcs import jcs

MAX_BYTES = 262144
_OPS = ("DESCRIBE", "INFORM", "INQUIRE", "WARN", "RECOMMEND", "EXECUTE")

class RequestError(ValueError):
    def __init__(self, code, message):
        super().__init__("%s: %s" % (code, message))
        self.code = code

@dataclass(frozen=True)
class ExaminationRequest:
    body: dict
    body_bytes: bytes
    request_sha256: str
    proposition: str
    material_bytes: int
    mapping_report: tuple = field(default_factory=tuple)

def _text(name, v, required=True):
    if v is None:
        if required:
            raise RequestError("MISSING_" + name.upper(), "%s is required as a plain string" % name)
        return None
    if not isinstance(v, str):
        raise RequestError("NOT_A_STRING", "%s must be a plain string, got %s. The engine does not read objects here; see from_nested_shape() for the explicit mapping."
                           % (name, type(v).__name__))
    if not v.strip():
        raise RequestError("EMPTY_" + name.upper(), "%s is empty" % name)
    return v

def build_request(*, claim, data, source=None, evidence=(), warrant=None, subject=None,
                  requested_operation="INFORM", bounds=None, mapping_report=()):
    claim = _text("claim", claim)
    data = _text("data", data)
    body = {"claim": claim, "data": data, "requested_operation": requested_operation}
    if requested_operation not in _OPS:
        raise RequestError("BAD_OPERATION", "requested_operation must be one of %s" % ", ".join(_OPS))
    prov = {}
    if source is not None:
        prov["source"] = _text("source", source)
        body["source"] = prov["source"]
    ev = list(evidence or ())
    for e in ev:
        _text("evidence item", e)
    if ev:
        prov["evidence"] = ev
    if warrant is not None:
        body["warrant"] = _text("warrant", warrant)
    if subject is not None:
        body["subject"] = _text("subject", subject)
    if bounds is not None:
        if not isinstance(bounds, dict):
            raise RequestError("BAD_BOUNDS", "bounds must be an object")
        body["bounds"] = bounds
    if prov:
        body["provenance"] = prov
    try:
        raw = jcs(body).encode("utf-8")
    except (ValueError, TypeError) as e:
        raise RequestError("NOT_CANONICAL", "request violates the service's canonical JSON rule: %s" % e)
    if len(raw) > MAX_BYTES:
        raise RequestError("TOO_LARGE", "request is %d bytes, limit %d" % (len(raw), MAX_BYTES))
    return ExaminationRequest(body, raw, hashlib.sha256(raw).hexdigest(), claim,
                              len(data.encode("utf-8")), tuple(mapping_report))

def from_nested_shape(obj, **extra):
    """Explicit client-side mapping of the nested shape the earlier public docs showed.

    Mapped: claim.statement -> claim; material.text|data -> data; material.source_url -> source.
    Anything else in claim or material is NOT silently dropped: it raises, so the caller sees it.
    Returns an ExaminationRequest whose mapping_report lists every move made.
    """
    if not isinstance(obj, dict):
        raise RequestError("BAD_SHAPE", "expected an object")
    report, claim, mat = [], obj.get("claim"), obj.get("material")
    if isinstance(claim, dict):
        extra_keys = sorted(set(claim) - {"statement", "type"})
        if extra_keys:
            raise RequestError("UNMAPPED_CLAIM_FIELDS", "claim fields have no engine meaning: %s" % extra_keys)
        report.append("claim.statement -> claim")
        claim = claim.get("statement")
    data, source = None, extra.pop("source", None)
    if isinstance(mat, dict):
        unknown = sorted(set(mat) - {"text", "data", "source_url", "retrieved_at"})
        if unknown:
            raise RequestError("UNMAPPED_MATERIAL_FIELDS", "material fields have no engine meaning: %s" % unknown)
        data = mat.get("text", mat.get("data"))
        report.append("material.text|data -> data")
        if mat.get("source_url") and source is None:
            source = mat["source_url"]
            report.append("material.source_url -> source")
    elif isinstance(mat, str):
        data = mat
        report.append("material (string) -> data")
    elif "data" in obj:
        data = obj["data"]
    return build_request(claim=claim, data=data, source=source, mapping_report=report, **extra)
