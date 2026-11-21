#!/usr/bin/env python3
"""Capture the live surfaces the conformance checker reads into offline fixtures.

Read-only: performs the same unauthenticated GETs as the checker and stores
each body (plus its HTTP status) under tests/fixtures/base using the checker's
own fixture_path() mapping, so the adversarial gate tests run offline against a
known-coherent snapshot. Re-run only to refresh the snapshot deliberately.
"""
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import check_conformance as cc  # noqa: E402

OUTDIR = os.path.join(os.path.dirname(__file__), "fixtures", "base")

URLS = [
    # sources of truth (S1-S5) and the routes the contract/OpenAPI advertise (D9)
    f"{cc.API}/v1/contract",
    f"{cc.API}/.well-known/whp-issuer.json",
    f"{cc.API}/openapi.json",
    f"{cc.API}/health",
    f"{cc.API}/v1/reception/contract",
    f"{cc.API}/.well-known/whp-standing.json",
    f"{cc.API}/v1/evaluate",
    f"{cc.API}/v1/verification",
    # site dependents (D1, D3, D4, D5, D6, D8, D12)
    f"{cc.SITE}/.well-known/whp-standing.json",
    f"{cc.SITE}/openapi.json",
    f"{cc.SITE}/llms.txt",
    f"{cc.SITE}/developers.html",
    f"{cc.SITE}/press/the-standing-mark-is-live.html",
    f"{cc.SITE}/agent-card-description.json",
    f"{cc.SITE}/publications/decision-integrity-standard-no-001-v1-0.html",
    f"{cc.SITE}/publications/receiving-boundary-rule-no-001-v1-0.html",
    # alias host (D2, D12)
    f"{cc.ALIAS}/v1/contract",
    f"{cc.ALIAS}/.well-known/whp-issuer.json",
    f"{cc.ALIAS}/openapi.json",
    f"{cc.ALIAS}/v1/reception/contract",
    # standing-mark repo surfaces at main (D3, D7, D8)
    f"{cc.RAW_SM}/openapi.json?ref=main",
    f"{cc.RAW_SM}/docs/payment.md?ref=main",
    f"{cc.RAW_SM}/docs/quick-start.md?ref=main",
    f"{cc.RAW_SM}/docs/test-vectors.md?ref=main",
    f"{cc.RAW_SM}/SKILL.md?ref=main",
    f"{cc.RAW_SM}/a2a/agent-card.json?ref=main",
    # external registries (D10, D13)
    cc.REGISTRY,
    cc.NPM,
]


def main():
    cc.FIXTURE_DIR = OUTDIR  # fixture_path() writes under the snapshot dir
    os.makedirs(OUTDIR, exist_ok=True)
    for url in URLS:
        req = urllib.request.Request(url, headers={
            "User-Agent": "whp-conformance-fixture-capture/1.0",
            "Accept": "application/vnd.github.raw",
        })
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                status, body = r.status, r.read()
        except urllib.error.HTTPError as e:
            status, body = e.code, (e.read() if e.fp else b"")
        fp = cc.fixture_path(url)
        with open(fp, "wb") as f:
            f.write(body)
        with open(fp + ".status", "w") as f:
            f.write(str(status))
        print(f"{status} {url}")
    print(f"captured {len(URLS)} surfaces into {OUTDIR}")


if __name__ == "__main__":
    main()
