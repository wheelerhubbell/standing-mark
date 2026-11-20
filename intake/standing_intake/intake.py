"""Universal Intake and Interpretation Layer (additive, deterministic, local).

Sits upstream of the examination engine. Never calls it, never changes it. Takes a submission in
whatever form it arrived, keeps the original, and returns an Intake Record whose layers stay apart:

  source        what the caller submitted (original bytes, hash, caller-supplied fields verbatim)
  extracted     content lifted verbatim from the source, each item traced to a pointer or line
  interpreted   structural readings of the source (which field is the proposition), with the rule used
  inferred      anything the system supplied that the caller did not (defaults). Never evidence.
  canonical     the engine-shape submission, only when justified; every field traced to a layer
  examinability EXAMINABLE | EXAMINABLE_WITH_LIMITS | NOT_EXAMINABLE, with exactly what is missing

Rules: no proposition is invented; provenance and warrant are never manufactured; caller claims of
standing (established_fact, source_grade, signatures) are recorded as caller assertions and ignored;
contradictions and alternatives are preserved, not resolved; deterministic rules only (no model).
"""
import json, hashlib, re
from dataclasses import dataclass

INTAKE_VERSION = "WHP-INTAKE-1.3.0"
MAX_BYTES, MAX_DEPTH = 262144, 64
# WHP-INTAKE-1.2.0 (2026-11-20, operator-approved): the gate keeps no fixed operation list.
# Any operation name is taken as given; the gate may refuse a missing object or a non-string
# operation, never an operation outside a predetermined container.
# WHP-INTAKE-1.3.0 (2026-11-20, operator-approved): distinct conflicting values across the
# proposition alias fields are refused, never silently sorted into roles. The door refuses
# before payment with 400 AMBIGUOUS_INPUT_ALIASES; the intake records NOT_EXAMINABLE.
CLAIM_KEYS = ("claim", "proposition", "statement", "question", "assertion")
# The published input schema's proposition aliases (WHP-INPUT-SCHEMA-1.4.x): distinct values
# across these fields are a caller error. question/assertion are not refusal aliases; a
# distinct value there is preserved as an alternative, matching the live door's alias set.
PROPOSITION_ALIAS_KEYS = ("claim", "text", "prompt", "content", "statement", "proposition")
MATERIAL_KEYS = ("data", "material", "text", "document", "content", "body", "evidence", "record", "payload", "transaction", "event", "prompt", "input")
SOURCE_KEYS = ("source", "source_url", "url", "provenance")
STANDING_ASSERTIONS = {"established_fact", "established", "source_grade", "epistemic_status", "attested", "attestation", "signature",
                       "verified", "authorized", "approved", "standing", "outcome", "determination", "permitted_operations", "trusted"}
LABELS = {"claim": "claim", "proposition": "claim", "question": "claim", "evidence": "material", "material": "material", "data": "material",
          "source": "source", "warrant": "warrant", "operation": "op", "requested operation": "op"}
_label_re = re.compile(r"^\s*(claim|proposition|question|evidence|material|data|source|warrant|requested operation|operation)\s*:\s*(.*)$", re.I)

def sha(b): return hashlib.sha256(b).hexdigest()

@dataclass(frozen=True)
class Original:
    raw: bytes
    sha256: str
    media_type: str

class _Dup(Exception): pass
def _pairs(pairs):
    d = {}
    for k, v in pairs:
        if k in d: raise _Dup(k)
        d[k] = v
    return d

def _depth(o, n=1):
    if n > MAX_DEPTH: return n
    if isinstance(o, dict): return max([_depth(v, n + 1) for v in o.values()] + [n])
    if isinstance(o, list): return max([_depth(v, n + 1) for v in o] + [n])
    return n

def _flatten(o, ptr=""):
    """Verbatim leaf values as (json_pointer, text). Scalars only; order preserved."""
    if isinstance(o, dict):
        for k, v in o.items(): yield from _flatten(v, ptr + "/" + str(k).replace("~", "~0").replace("/", "~1"))
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from _flatten(v, ptr + "/" + str(i))
    elif o is None: return
    else: yield ptr, (json.dumps(o) if isinstance(o, (bool, int, float)) else str(o))

def _lab(ptr, t):
    last = ptr.split("/")[-1]
    return t if last.isdigit() or last in ("text", "data", "content") or ptr.count("/") == 1 else last + ": " + t

def _is_str(v): return isinstance(v, str) and v.strip() != ""

class _Rec:
    def __init__(self, original):
        self.o = original
        self.source = {"original_sha256": original.sha256, "bytes": len(original.raw), "media_type": original.media_type, "caller_fields": {}}
        self.extracted, self.interpreted, self.inferred, self.issues = [], [], [], []
        self.contradictions, self.alternatives, self.ignored, self.canonical_trace = [], [], [], {}
        self.claim = self.data = self.src = self.warrant = self.op = None
        self.evidence, self.multi = [], []
        self.passthrough = None; self.fb_key = None
    def ext(self, kind, text, pointer, rule):
        i = "x%d" % (len(self.extracted) + 1); self.extracted.append({"id": i, "kind": kind, "text": text, "pointer": pointer, "rule": rule}); return i
    def interp(self, what, ref, rule): self.interpreted.append({"what": what, "from": ref, "rule": rule})
    def infer(self, what, value, why): self.inferred.append({"what": what, "value": value, "why": why, "is_evidence": False})
    def issue(self, code, detail): self.issues.append({"code": code, "detail": detail})

def _guess_media(raw):
    s = raw.lstrip()[:1]
    return "application/json" if s in (b"{", b"[") else "text/plain"

def _from_json(r, obj):
    if isinstance(obj, list):  # evidence package: list of items
        r.interp("submission is an evidence package (list)", "", "R-PKG-LIST")
        obj = {"items": obj}
    if isinstance(obj, str):
        if not obj.strip(): r.issue("EMPTY_SUBMISSION", "top-level JSON string is empty"); return
        r.claim = obj
        r.canonical_trace["claim"] = r.ext("proposition", obj, "/", "R-JSON-TOP-STRING")
        r.interp("proposition is the top-level JSON string (the documented bare-string shape)", "/", "R-JSON-TOP-STRING")
        return
    if not isinstance(obj, dict):
        r.issue("UNSUPPORTED_SHAPE", "top-level JSON is a scalar"); return
    if obj.get("version") == "WHP-STANDING-SUBMISSION-v1" and isinstance(obj.get("nodes"), list) and obj["nodes"]:
        r.passthrough = obj
        r.interp("submission is already an engine-native WHP-STANDING-SUBMISSION-v1 object; passed through unchanged", "", "R-SUBMISSION-V1-PASSTHROUGH")
        return
    for k in obj:
        if k.lower() in STANDING_ASSERTIONS:
            r.source["caller_fields"][k] = obj[k]; r.ignored.append({"field": k, "reason": "caller assertion of standing; recorded, never evidence"})
    # proposition alias conflict: refused, never sorted into roles (R-JSON-ALIAS-CONFLICT-REFUSED)
    alias_vals = [(k, obj[k].strip()) for k in PROPOSITION_ALIAS_KEYS if _is_str(obj.get(k))]
    if len({v for _, v in alias_vals}) > 1:
        r.issue("AMBIGUOUS_INPUT_ALIASES", "distinct conflicting values across proposition alias fields (%s); supply one proposition field or make every alias carry the same value" % ", ".join("/" + k for k, _ in alias_vals))
        r.interp("conflicting proposition aliases refused; no value is assigned a role", "", "R-JSON-ALIAS-CONFLICT-REFUSED")
        return
    # proposition(s)
    cand = [(k, obj[k]) for k in CLAIM_KEYS if k in obj]
    for k, v in cand:
        if _is_str(v):
            if r.claim is None:
                r.claim = v; i = r.ext("proposition", v, "/" + k, "R-JSON-CLAIM-STRING"); r.canonical_trace["claim"] = i
                r.interp("proposition is the caller's %s string" % k, "/" + k, "R-JSON-CLAIM-STRING")
            elif v != r.claim: r.alternatives.append({"kind": "proposition", "pointer": "/" + k, "text": v})
        elif isinstance(v, dict) and _is_str(v.get("statement")):
            if r.claim is None:
                r.claim = v["statement"]; i = r.ext("proposition", r.claim, "/%s/statement" % k, "R-JSON-CLAIM-NESTED"); r.canonical_trace["claim"] = i
                r.interp("proposition is claim.statement (previously documented nested shape)", "/%s/statement" % k, "R-JSON-CLAIM-NESTED")
            extra = [x for x in v if x not in ("statement", "type")]
            for x in extra: r.ext("claim_attribute", json.dumps(v[x]), "/%s/%s" % (k, x), "R-NOT-CLAIM-TEXT")
        elif isinstance(v, list):
            strs = [x for x in v if _is_str(x)]
            for n, x in enumerate(strs): r.multi.append((x, "/%s/%d" % (k, n)))
        elif v is not None and not (isinstance(v, str)):
            r.issue("PROPOSITION_NOT_TEXT", "/%s is %s, not text" % (k, type(v).__name__))
    if len(r.multi) > 1:
        for x, p in r.multi: r.ext("proposition", x, p, "R-JSON-CLAIM-LIST")
        r.interp("%d separate propositions supplied by the caller; each is examined separately" % len(r.multi), "", "R-MULTI-PROPOSITION")
    elif len(r.multi) == 1 and r.claim is None:
        r.claim = r.multi[0][0]; r.canonical_trace["claim"] = r.ext("proposition", r.claim, r.multi[0][1], "R-JSON-CLAIM-LIST")
    r.fb_key = None
    if r.claim is None and not r.multi and not r.issues:
        for k in ("data", "text", "prompt", "content", "input"):
            if _is_str(obj.get(k)):
                r.claim = obj[k]; r.fb_key = k; r.canonical_trace["claim"] = r.ext("proposition", r.claim, "/" + k, "R-JSON-PROPOSITION-FALLBACK")
                r.interp("no claim field; the string in %s is read as the proposition (the examination engine's documented fallback order: data, text, prompt, content, input)" % k, "/" + k, "R-JSON-PROPOSITION-FALLBACK")
                break
    if r.claim is None and not r.multi and not r.issues:
        # Contract precedence (WHP-INPUT-SCHEMA-1.4.0): claim aliases (claim, text, prompt,
        # content, statement, proposition) beat subject; subject beats object.id.
        has_alias = any(_is_str(obj.get(k)) for k in ("text", "prompt", "content"))
        if not has_alias:
            subj = obj.get("subject"); ob = obj.get("object")
            if _is_str(subj):
                r.claim = subj; r.canonical_trace["claim"] = r.ext("proposition", subj, "/subject", "R-JSON-SUBJECT")
                r.interp("no claim alias string; the subject string is mapped to the proposition", "/subject", "R-JSON-SUBJECT")
            elif isinstance(ob, dict) and _is_str(ob.get("id")):
                r.claim = ob["id"]; r.canonical_trace["claim"] = r.ext("proposition", r.claim, "/object/id", "R-JSON-OBJECT-ID")
                r.interp("no claim alias or subject string; object.id is the proposition", "/object/id", "R-JSON-OBJECT-ID")
    # material
    parts = []
    for k in MATERIAL_KEYS:
        if k in obj and not (k in CLAIM_KEYS and obj[k] is r.claim) and k != r.fb_key:
            v = obj[k]
            if _is_str(v):
                parts.append((("/" + k), v))
            elif isinstance(v, (dict, list)):
                for ptr, t in _flatten(v, "/" + k): parts.append((ptr, _lab(ptr, t)))
    if "items" in obj: 
        for ptr, t in _flatten(obj["items"], "/items"): parts.append((ptr, _lab(ptr, t)))
    if "files" in obj and isinstance(obj["files"], list):
        for n, f in enumerate(obj["files"]):
            if isinstance(f, dict) and _is_str(f.get("text")): parts.append(("/files/%d/text" % n, f["text"]))
    # source / warrant / operation (caller-supplied only)
    for k in ("source", "source_url", "url"):
        if _is_str(obj.get(k)) and r.src is None: r.src = obj[k]; r.canonical_trace["source"] = r.ext("source", r.src, "/" + k, "R-JSON-SOURCE")
    prov = obj.get("provenance")
    if isinstance(prov, dict):
        if _is_str(prov.get("source")) and r.src is None: r.src = prov["source"]; r.canonical_trace["source"] = r.ext("source", r.src, "/provenance/source", "R-JSON-SOURCE")
        if isinstance(prov.get("evidence"), list): r.evidence = [e for e in prov["evidence"] if _is_str(e)]
        if _is_str(prov.get("authority")) and not _is_str(obj.get("warrant")): r.warrant = prov["authority"]
    mat = obj.get("material")
    if isinstance(mat, dict) and _is_str(mat.get("source_url")) and r.src is None:
        r.src = mat["source_url"]; r.canonical_trace["source"] = r.ext("source", r.src, "/material/source_url", "R-JSON-SOURCE")
    if _is_str(obj.get("warrant")): r.warrant = obj["warrant"]
    if r.warrant: r.canonical_trace["warrant"] = r.ext("warrant", r.warrant, "/warrant", "R-JSON-WARRANT")
    for k in ("requested_operation", "operation"):
        if k in obj: r.op = obj[k]
    # contradictions: same final key with different scalar values across the material
    seen = {}
    for ptr, t in _flatten(obj.get("items", obj.get("material", obj.get("data", {}))) if not isinstance(obj.get("data"), str) else {}, ""):
        key = ptr.split("/")[-1]
        if not key.isdigit(): seen.setdefault(key, []).append((ptr, t))
    for key, vals in seen.items():
        if len({t for _, t in vals}) > 1: r.contradictions.append({"key": key, "values": [{"pointer": p, "text": t} for p, t in vals]})
    r.parts = [(p, t) for p, t in parts if not (p.endswith('/source_url') and r.src is not None and r.src in t)]

def _from_text(r, text):
    lines = text.split("\n"); cur = None; buckets = {"claim": [], "material": [], "source": [], "warrant": [], "op": []}; labeled = False; unl = []
    for n, ln in enumerate(lines):
        m = _label_re.match(ln)
        if m:
            labeled = True; cur = LABELS[m.group(1).lower()]
            if m.group(2).strip(): buckets[cur].append((n, m.group(2).strip()))
        elif ln.strip():
            (buckets[cur] if cur else unl).append((n, ln.strip()))
    if labeled:
        r.interp("labeled sections (Claim/Evidence/Source/...) read by label", "", "R-TEXT-LABELS")
        cl = buckets["claim"]
        if cl:
            r.claim = " ".join(t for _, t in cl); r.canonical_trace["claim"] = r.ext("proposition", r.claim, "lines %d-%d" % (cl[0][0] + 1, cl[-1][0] + 1), "R-TEXT-LABEL-CLAIM")
        r.parts = [("line %d" % (n + 1), t) for n, t in buckets["material"] + unl]
        if buckets["source"]: r.src = buckets["source"][0][1]; r.canonical_trace["source"] = r.ext("source", r.src, "line %d" % (buckets["source"][0][0] + 1), "R-TEXT-LABEL-SOURCE")
        if buckets["warrant"]: r.warrant = " ".join(t for _, t in buckets["warrant"]); r.canonical_trace["warrant"] = r.ext("warrant", r.warrant, "labeled", "R-TEXT-LABEL-WARRANT")
        if buckets["op"]: r.op = buckets["op"][0][1].upper()
    else:
        stmts = [t for _, t in unl]
        r.parts = []
        if len(stmts) == 1 and len(stmts[0]) < 600:
            r.claim = stmts[0]; r.canonical_trace["claim"] = r.ext("proposition", r.claim, "line 1", "R-TEXT-SINGLE-STATEMENT")
            r.interp("a lone statement is read as the proposition; no material accompanies it", "line 1", "R-TEXT-SINGLE-STATEMENT")
        elif stmts:
            r.interp("unlabeled multi-line text is read as material; no proposition is identified", "", "R-TEXT-DOCUMENT")
            r.parts = [("line %d" % (n + 1), t) for n, t in unl]
            for n, t in unl[:5]:
                if t.endswith(("?",)): r.alternatives.append({"kind": "candidate_proposition_inferred", "pointer": "line %d" % (n + 1), "text": t, "selected": False})

def intake(submission, media_type=None):
    """submission: bytes, str or already-parsed JSON. Returns the Intake Record (dict)."""
    if isinstance(submission, (dict, list)): raw = json.dumps(submission, ensure_ascii=False).encode("utf-8")
    elif isinstance(submission, str): raw = submission.encode("utf-8")
    else: raw = bytes(submission)
    o = Original(raw, sha(raw), media_type or _guess_media(raw)); r = _Rec(o); r.parts = []
    obj = None; text = None
    if len(raw) > MAX_BYTES: r.issue("TOO_LARGE", "%d bytes, limit %d" % (len(raw), MAX_BYTES))
    elif not raw.strip(): r.issue("EMPTY_SUBMISSION", "no content")
    else:
        try: text = raw.decode("utf-8")
        except UnicodeDecodeError: r.issue("NOT_UTF8", "submission is not valid UTF-8; original preserved")
        if text is not None:
            if o.media_type == "application/json":
                try:
                    obj = json.loads(text, object_pairs_hook=_pairs, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
                    if _depth(obj) > MAX_DEPTH: r.issue("TOO_DEEP", "nesting over %d" % MAX_DEPTH); obj = None
                except _Dup as e: r.issue("DUPLICATE_KEY", str(e))
                except ValueError: r.issue("MALFORMED_JSON", "not parseable as JSON"); 
            if obj is not None: _from_json(r, obj)
            elif not r.issues: _from_text(r, text)
    # material text
    statements = [t for _, t in r.parts]
    for p, t in r.parts: r.ext("material", t, p, "R-MATERIAL")
    if statements: r.data = "\n".join(statements)
    if r.evidence and not r.data: r.data = "\n".join(r.evidence)
    # operation
    op = r.op
    if op is None: op = "INFORM"; r.infer("requested_operation", "INFORM", "caller named none; INFORM is the least consequential default")
    elif not isinstance(op, str): r.issue("UNSUPPORTED_OPERATION", "requested operation %r is not a string; operation names are taken as given" % (op,)); op = None
    # missing / examinability
    missing = []
    if not r.claim and len(r.multi) < 2: missing.append("PROPOSITION")
    if not r.data: missing.append("MATERIAL")
    if r.src is None: missing.append("SOURCE_REFERENCE(optional: examination will name an unresolved source)")
    hard = [i["code"] for i in r.issues]
    blocking = [m for m in missing if not m.startswith("SOURCE")]
    if hard or (blocking and r.claim is None and not r.multi): level = "NOT_EXAMINABLE"
    elif "MATERIAL" in blocking: level = "EXAMINABLE_WITH_LIMITS"
    else: level = "EXAMINABLE"
    if level == "NOT_EXAMINABLE" and not (hard or blocking): level = "NOT_EXAMINABLE"
    if "PROPOSITION" in blocking and not hard: level = "NOT_EXAMINABLE"
    notes = []
    if level == "EXAMINABLE_WITH_LIMITS": notes.append("Proposition without separate material: the engine examines the proposition text alone (fallback). Not a substantive examination of supporting material.")
    if r.contradictions: notes.append("Submitted material contradicts itself on: %s. Both values are preserved; neither is selected." % ", ".join(c["key"] for c in r.contradictions))
    if r.ignored: notes.append("Caller assertions of standing were recorded and ignored: %s." % ", ".join(i["field"] for i in r.ignored))
    if "SOURCE_REFERENCE(optional: examination will name an unresolved source)" in missing: notes.append("No source reference was supplied; none was manufactured. Expect the examination to name the source as unresolved.")
    canon = []
    if level != "NOT_EXAMINABLE" and op:
        claims = [r.claim] if r.claim else [x for x, _ in r.multi]
        for c in claims:
            b = {"claim": c, "requested_operation": op}
            if r.data: b["data"] = r.data
            if r.src: b["source"] = r.src; b["provenance"] = {"source": r.src, **({"evidence": r.evidence} if r.evidence else {})}
            elif r.evidence: b["provenance"] = {"evidence": r.evidence}
            if r.warrant: b["warrant"] = r.warrant
            canon.append(b)
    elif level != "NOT_EXAMINABLE": level = "NOT_EXAMINABLE"
    if r.passthrough is not None:
        missing = []; level = "EXAMINABLE"; canon = [r.passthrough]
        notes.append("Engine-native submission passed through unchanged; intake did not inspect its nodes. The examination decides what is established.")
    cj = [json.dumps(c, sort_keys=True, separators=(",", ":"), ensure_ascii=False) for c in canon]
    record = {
        "intake_version": INTAKE_VERSION,
        "source": r.source, "extracted": r.extracted, "interpreted": r.interpreted, "inferred": r.inferred,
        "canonical_trace": r.canonical_trace,
        "preserved": {"contradictions": r.contradictions, "alternatives": r.alternatives, "ignored_caller_assertions": r.ignored},
        "examinability": {"level": level, "missing": missing, "issues": r.issues, "disclosures": notes,
                          "quote_gate": {"NOT_EXAMINABLE": "NO_QUOTE", "EXAMINABLE_WITH_LIMITS": "QUOTE_ONLY_WITH_DISCLOSURE_AND_INFORMED_CHOICE", "EXAMINABLE": "QUOTE_ALLOWED"}[level]},
        "canonical_submissions": canon,
        "canonical_sha256": [sha(c.encode("utf-8")) for c in cj],
        "does_not_establish": ["correctness of the proposition", "truth of any submitted material", "authenticity of any source", "authority of any party", "any standing: that is the engine's examination"],
    }
    record["record_sha256"] = sha(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    return record
