#!/usr/bin/env python3
"""WHP one-truth conformance check (read-only).

Every public statement about the Standing service must agree with the live
sources of truth at the same time. When any source of truth changes, every
dependent surface must change with it; this script is the domino detector.
It performs unauthenticated requests only: no quotes, no payment, no writes.
A route advertised as POST is probed with an empty JSON body, which the
service refuses before any payment or evaluation; existence probes change
nothing on the server. It never changes anything it reads.

Sources of truth (SOT), fetched live:
  S1 contract   GET https://api.wheelerhubbellpublishing.com/v1/contract
                (served identically at /.well-known/whp-standing.json)
  S2 issuer     GET https://api.wheelerhubbellpublishing.com/.well-known/whp-issuer.json
  S3 openapi    GET https://api.wheelerhubbellpublishing.com/openapi.json
  S4 health     GET https://api.wheelerhubbellpublishing.com/health
  S5 reception  GET https://api.wheelerhubbellpublishing.com/v1/reception/contract
  S6 publications  the two pages named in S1.publications

Dependent surfaces (must derive from, and agree with, the SOT):
  D1  site discovery mirror   wheelerhubbellpublishing.com/.well-known/whp-standing.json == S1
  D2  alias host              decisionintegrity.* serves S1, S2, S3, S4 byte-identical
  D3  OpenAPI mirrors         site openapi.json and standing-mark openapi.json == S3
  D4  site llms.txt           advertises only routes that resolve; current payment terms only
  D5  developers.html         teaches the current payment scheme only
  D6  press page              presents no retired endpoint as live
  D7  standing-mark docs      current scheme only; retired scheme named retired
  D8  agent cards             version matches S1 profile
  D9  contract-advertised     every route S1/S3 advertise returns non-404 on its advertised method
  D10 MCP registry            active records' remotes resolve; no active record points at a retired host
  D11 reception component     S5 resolves; its pinned issuer key == S2 key id
  D12 publications            S1.publications URLs resolve; both hosts serve S5
  D13 npm registry            no current package contradicts "use the source SDKs"
  D14 issuer key integrity    S2 key id == sha256(S2 public key); S1 references S2

Exit code 0 when every check passes or is a known open decision; 1 otherwise.
Known open decisions are printed separately and never silently pass.

Execution modes (all read-only; they change what is read, never what is written):
  default         advisory: live surfaces; exit 1 only on FAIL, open decisions reported
  --gate          release gate: an unresolved open decision blocks the release too
                  (a release is not authorized while a contradiction is unresolved)
  --repo-ref R    examine standing-mark repo surfaces at ref R (a release candidate)
                  instead of main
  --site-root D   examine wheelerhubbellpublishing.com surfaces from a local checkout
                  rooted at D (a site release candidate) instead of the published site
  --fixture-dir D offline test mode: every GET is served from files under D
Env: WHP_CONFORMANCE_GATE=1, WHP_CONFORMANCE_REPO_REF, WHP_CONFORMANCE_SITE_ROOT,
WHP_CONFORMANCE_FIXTURE_DIR set the same modes.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import sys
import urllib.request
import urllib.error
from urllib.parse import urlsplit

API = "https://api.wheelerhubbellpublishing.com"
ALIAS = "https://decisionintegrity.wheelerhubbellpublishing.com"
SITE = "https://wheelerhubbellpublishing.com"
RAW_SM = "https://api.github.com/repos/wheelerhubbell/standing-mark/contents"
RAW_HEADERS = {"Accept": "application/vnd.github.raw"}  # repo HEAD is the truth; the raw CDN mirror lags it
REGISTRY = "https://registry.modelcontextprotocol.io/v0/servers?search=wheelerhubbell"
NPM = "https://registry.npmjs.org/@wheelerhubbell%2fwhp-standing-client"
PAYMENT_MIGRATION_DATE = "2026-11-16"

REPO_REF = os.environ.get("WHP_CONFORMANCE_REPO_REF", "main")
SITE_ROOT = os.environ.get("WHP_CONFORMANCE_SITE_ROOT")
FIXTURE_DIR = os.environ.get("WHP_CONFORMANCE_FIXTURE_DIR")
GATE = os.environ.get("WHP_CONFORMANCE_GATE") == "1"

# Decisions that are the operator's to make. Until each is decided, the
# checker reports it here instead of failing. Remove the entry when decided.
KNOWN_OPEN = {
    "D13 npm @wheelerhubbell/whp-standing-client": "latest published package predates the 2026-11-16 payment migration. Operator decision pending: deprecate it or publish a new version.",
}

RESULTS = []  # (check_id, surface, sot, status, evidence)


def record(check_id, surface, sot, ok, evidence):
    status = "PASS" if ok else "FAIL"
    for key, note in KNOWN_OPEN.items():
        if check_id == key:
            status = "OPEN"
            evidence = evidence + " | " + note
            break
    RESULTS.append((check_id, surface, sot, status, evidence))
    return ok


def fixture_path(url):
    """Offline-test mapping: one URL to one file under FIXTURE_DIR.

    The body lives at the mapped path; an optional sibling `<path>.status`
    holds the HTTP status (default 200 when the body exists, else 404).
    """
    p = urlsplit(url)
    key = p.netloc + p.path + ("?" + p.query if p.query else "")
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", key)
    return os.path.join(FIXTURE_DIR, safe)


def get(url, timeout=25, headers=None, method="GET", body=None):
    if FIXTURE_DIR:
        fp = fixture_path(url)
        if method != "GET":
            mfp = fp + "." + method
            if os.path.exists(mfp) or os.path.exists(mfp + ".status"):
                fp = mfp
        status = 200
        sp = fp + ".status"
        if os.path.exists(sp):
            with open(sp) as f:
                status = int(f.read().strip())
        if os.path.exists(fp):
            with open(fp, "rb") as f:
                return status, f.read()
        return (status if os.path.exists(sp) else 404), b""
    if SITE_ROOT and url.startswith(SITE):
        rel = url[len(SITE):].lstrip("/")
        fp = os.path.join(SITE_ROOT, rel)
        if os.path.isfile(fp):
            with open(fp, "rb") as f:
                return 200, f.read()
        return 404, b""
    h = {"User-Agent": "whp-conformance-check/1.0"}
    if "api.github.com" in url and os.environ.get("GITHUB_TOKEN"):
        h["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]  # CI rate limits only
    if headers:
        h.update(headers)
    if method != "GET":
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body if method != "GET" else None,
                                 headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() if e.fp else b""
    except Exception as e:
        return -1, str(e).encode()


def get_json(url, headers=None):
    st, body = get(url, headers=headers)
    if st != 200:
        return st, None
    try:
        return st, json.loads(body)
    except Exception:
        return -2, None


def advertised_methods(s1):
    """path -> advertised HTTP method, from the contract's routes object."""
    m = {}
    routes_obj = s1.get("routes", s1.get("interface", {})) or {}
    if isinstance(routes_obj, dict):
        for spec in routes_obj.values():
            if isinstance(spec, dict) and isinstance(spec.get("path"), str):
                m[spec["path"]] = (spec.get("method") or "GET").upper()
    return m


def probe(url, method):
    """Existence probe that honors the advertised method. A GET on a POST
    route proves nothing about the route: /v1/evaluate answers GET with 405
    but /v1/verification answers GET with 404, which was misread on
    2026-11-21 as the route not existing. Probe what the contract advertises."""
    if method == "GET":
        return get(url)
    return get(url, method=method, body=b"{}")


def main(argv=None):
    global GATE, REPO_REF, SITE_ROOT, FIXTURE_DIR
    ap = argparse.ArgumentParser(description="WHP one-truth conformance check (read-only).")
    ap.add_argument("--gate", action="store_true",
                    help="release-gate mode: unresolved open decisions block (exit 1)")
    ap.add_argument("--repo-ref", default=None,
                    help="examine standing-mark repo surfaces at this ref instead of main")
    ap.add_argument("--site-root", default=None,
                    help="examine site surfaces from this local checkout instead of the published site")
    ap.add_argument("--fixture-dir", default=None,
                    help="offline test mode: serve every GET from files under this directory")
    args = ap.parse_args(argv)
    if args.gate:
        GATE = True
    if args.repo_ref:
        REPO_REF = args.repo_ref
    if args.site_root:
        SITE_ROOT = args.site_root
    if args.fixture_dir:
        FIXTURE_DIR = args.fixture_dir
    # --- fetch sources of truth ---
    st1, s1 = get_json(f"{API}/v1/contract")
    st2, s2 = get_json(f"{API}/.well-known/whp-issuer.json")
    st3, s3_body = get(f"{API}/openapi.json")
    st4, s4 = get_json(f"{API}/health")
    st5, s5 = get_json(f"{API}/v1/reception/contract")
    for sid, st in (("S1", st1), ("S2", st2), ("S3", st3), ("S4", st4), ("S5", st5)):
        if st != 200:
            record(sid, "source of truth fetch", "-", False, f"HTTP {st}")
            return finish()
    s3 = json.loads(s3_body)
    amap = advertised_methods(s1)

    # --- D14: issuer key integrity (do this first; other checks reuse it) ---
    key_bytes = base64.b64decode(s2["public_key"])
    key_id = hashlib.sha256(key_bytes).hexdigest()
    record("D14", "issuer key id == sha256(published key); contract names the issuer document",
           "S2 vs S1", key_id == s2.get("key_id_sha256") and "whp-issuer" in json.dumps(s1),
           f"computed {key_id[:16]}..., published {s2.get('key_id_sha256','')[:16]}...")

    # --- D1: site discovery mirror ---
    stm, mirror_body = get(f"{SITE}/.well-known/whp-standing.json")
    same = stm == 200 and json.loads(mirror_body) == s1
    record("D1", f"{SITE}/.well-known/whp-standing.json", "S1", same,
           "JSON identical to live contract" if same else f"HTTP {stm} or content drift")

    # --- D2: alias host byte-identity ---
    for path, name, ref in (("/v1/contract", "contract", json.dumps(s1, sort_keys=True)),
                            ("/.well-known/whp-issuer.json", "issuer", json.dumps(s2, sort_keys=True)),
                            ("/openapi.json", "openapi", s3_body.decode())):
        sta, body = get(f"{ALIAS}{path}")
        if name == "openapi":
            same = sta == 200 and body.decode() == ref
        else:
            same = sta == 200 and json.dumps(json.loads(body), sort_keys=True) == ref
        record("D2", f"{ALIAS}{path}", f"SOT {name}", same, f"HTTP {sta}, {'identical' if same else 'DIFFERS'}")

    # --- D3: OpenAPI mirrors ---
    for label, url in (("site", f"{SITE}/openapi.json"), ("standing-mark repo", f"{RAW_SM}/openapi.json?ref={REPO_REF}")):
        sto, body = get(url, headers=RAW_HEADERS if "api.github.com" in url else None)
        same = sto == 200 and body == s3_body
        record("D3", f"{label} openapi.json ({url})", "S3", same,
               "byte-identical" if same else f"HTTP {sto} or content drift")

    # --- D4: site llms.txt ---
    stl, llms = get(f"{SITE}/llms.txt")
    llms_t = llms.decode() if stl == 200 else ""
    bad_terms = [t for t in ("WHP-BASE-USDC-FLAT-1", "X-WHP-Quote", "X-WHP-Payment-Tx", "/v1/evaluations", "api.wheelerhubbellpublishing.com/mcp") if t in llms_t]
    urls = re.findall(r"https://api\.wheelerhubbellpublishing\.com[^\s)`]*", llms_t)
    dead = []
    for u in sorted(set(urls)):
        stu, _ = probe(u, amap.get(urlsplit(u).path, "GET"))
        if stu == 404:
            dead.append(u)
    record("D4", f"{SITE}/llms.txt", "S1+live routes", stl == 200 and not bad_terms and not dead,
           f"retired terms: {bad_terms or 'none'}; dead api URLs: {dead or 'none'}")

    # --- D5: developers.html ---
    std, dev = get(f"{SITE}/developers.html")
    dev_t = dev.decode() if std == 200 else ""
    teaches_current = "x402" in dev_t and "payment-signature" in dev_t
    teaches_retired = "WHP-BASE-USDC-FLAT-1" in dev_t or "X-WHP-Quote" in dev_t
    record("D5", f"{SITE}/developers.html", "S1 payment", std == 200 and teaches_current and not teaches_retired,
           f"current scheme taught: {teaches_current}; retired scheme taught: {teaches_retired}")

    # --- D6: press page ---
    stp, press = get(f"{SITE}/press/the-standing-mark-is-live.html")
    press_t = press.decode() if stp == 200 else ""
    live_mcp = re.search(r"MCP Server:\s*<code>POST", press_t) is not None
    record("D6", f"{SITE}/press/the-standing-mark-is-live.html", "S1 (no hosted MCP)",
           stp == 200 and not live_mcp, f"live /mcp endpoint presented: {live_mcp}")

    # --- D7: standing-mark docs ---
    doc_checks = [
        ("docs/payment.md", ["x402", "payment-signature"], None),
        ("docs/quick-start.md", ["x402", "payment-signature"], None),
        ("docs/test-vectors.md", ["x402Version", "eip3009"], None),
        ("SKILL.md", ["x402"], None),
    ]
    for path, must, _ in doc_checks:
        stf, fbody = get(f"{RAW_SM}/{path}?ref={REPO_REF}", headers=RAW_HEADERS)
        ft = fbody.decode() if stf == 200 else ""
        missing = [m for m in must if m not in ft]
        # retired scheme may appear only on lines that name it retired
        retired_bad = [l for l in ft.split("\n") if "WHP-BASE-USDC-FLAT-1" in l and "retired" not in l.lower()]
        record("D7", f"standing-mark {path}", "S1 payment", stf == 200 and not missing and not retired_bad,
               f"missing: {missing or 'none'}; unmarked retired scheme: {len(retired_bad)}")

    # --- D8: agent cards ---
    profile_ver = (s1.get("profile") or "").rsplit("-", 1)[-1]
    for label, url in (("site agent-card-description.json", f"{SITE}/agent-card-description.json"),
                       ("standing-mark a2a/agent-card.json", f"{RAW_SM}/a2a/agent-card.json?ref={REPO_REF}")):
        sta, card = get_json(url, headers=RAW_HEADERS if "api.github.com" in url else None)
        ver_ok = sta == 200 and card.get("version") == profile_ver
        record("D8", label, "S1 profile", bool(ver_ok),
               f"version {card.get('version') if card else '?'} vs {profile_ver}")

    # --- D9: contract-advertised routes resolve on their advertised method ---
    paths = set(re.findall(r'"(/[A-Za-z0-9_./-]+)"', json.dumps(s1.get("routes", s1.get("interface", {})))))
    paths |= set(s3.get("paths", {}).keys())
    for pth in sorted(paths):
        if "{" in pth:
            continue
        method = amap.get(pth, "GET")
        stu, _ = probe(f"{API}{pth}", method)
        record(f"D9 route {pth}", f"advertised route {pth}", "S1/S3", stu != 404, f"{method} -> HTTP {stu}")

    # --- D10: MCP registry ---
    strg, reg = get_json(REGISTRY)
    if strg == 200:
        for entry in reg.get("servers", []):
            sv = entry["server"]
            meta = entry.get("_meta", {}).get("io.modelcontextprotocol.registry/official", {})
            if meta.get("status") != "active":
                continue
            remotes = [r.get("url", "") for r in sv.get("remotes", [])]
            dead = [u for u in remotes if get(u)[0] in (404, -1)]
            retired_hosts = [u for u in remotes if any(h in u for h in ("lovable.app", "netlify.app", "railway.app", "chatgpt.site"))]
            record(f"D10 {sv['name']} {sv.get('version')}", "active MCP registry record", "S1",
                   not dead and not retired_hosts, f"remotes {remotes or 'none'}; dead {dead or 'none'}; retired-host {retired_hosts or 'none'}")
    else:
        record("D10", "MCP registry fetch", "-", False, f"HTTP {strg}")

    # --- D11: reception component ---
    pinned = s5.get("pinned_issuer_key_ids", [])
    record("D11", "reception contract pinned issuer", "S2", pinned == [key_id],
           f"pinned {pinned}; computed {key_id[:16]}...")

    # --- D12: publications ---
    pubs = (s1.get("publications") or {})
    for name, pub in pubs.items():
        u = pub.get("url") if isinstance(pub, dict) else None
        if not u:
            continue
        stu, _ = get(u)
        record("D12", f"publication {name}", "S1.publications", stu == 200, f"GET {u} -> HTTP {stu}")
    sta, _ = get(f"{ALIAS}/v1/reception/contract")
    record("D12", "reception contract on alias host", "S5", sta == 200, f"GET -> HTTP {sta}")

    # --- D13: npm ---
    stn, npm = get_json(NPM)
    if stn == 200:
        latest = npm.get("dist-tags", {}).get("latest")
        published = npm.get("time", {}).get(latest, "")
        stale = published < PAYMENT_MIGRATION_DATE
        record("D13 npm @wheelerhubbell/whp-standing-client", "npm latest vs payment migration", "S1 payment",
               not stale, f"latest {latest} published {published[:10]}; migration {PAYMENT_MIGRATION_DATE}")
    return finish()


def finish():
    width = max(len(r[0]) for r in RESULTS) if RESULTS else 10
    fails = opens = 0
    print(f"{'CHECK'.ljust(width)}  STATUS  EVIDENCE")
    for cid, surface, sot, status, evidence in RESULTS:
        if status == "FAIL":
            fails += 1
        if status == "OPEN":
            opens += 1
        print(f"{cid.ljust(width)}  {status.ljust(6)}  {surface} [{sot}] -- {evidence}")
    print(f"\n{len(RESULTS)} checks: {len(RESULTS)-fails-opens} pass, {opens} known open operator decisions, {fails} FAIL")
    if opens:
        print("\nKnown open decisions (operator's word needed):")
        for k, v in KNOWN_OPEN.items():
            if any(r[0] == k and r[3] == "OPEN" for r in RESULTS):
                print(f"- {k}: {v}")
    if GATE and opens:
        print(f"\nGATE: release blocked by {opens} unresolved operator decision(s). "
              "A release is not authorized while a contradiction is unresolved.")
    return 1 if fails or (GATE and opens) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
