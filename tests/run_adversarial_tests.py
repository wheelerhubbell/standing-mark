#!/usr/bin/env python3
"""Adversarial release-gate tests (offline).

Each case copies the captured coherent snapshot (tests/fixtures/base), injects
one of the November 21 failure shapes, and proves the conformance examination
in --gate mode refuses release authorization (exit 1) and names the check that
blocks. The control case proves the snapshot itself is coherent: advisory mode
passes it, and gate mode passes it with the one operator-decided contradiction
(npm, D13) still reported as DECIDED, nothing hidden.

Run: python3 tests/run_adversarial_tests.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "tests", "fixtures", "base")
CHECKER = os.path.join(ROOT, "scripts", "check_conformance.py")

sys.path.insert(0, os.path.join(ROOT, "scripts"))
import check_conformance as cc  # noqa: E402

cc.FIXTURE_DIR = BASE  # so fixture_path() names snapshot files


def fp(url):
    return cc.fixture_path(url)


def load(url):
    with open(fp(url), "rb") as f:
        return f.read()


def store(work, url, body, status=None):
    dst = os.path.join(work, os.path.relpath(fp(url), BASE))
    with open(dst, "wb") as f:
        f.write(body if isinstance(body, bytes) else body.encode())
    if status is not None:
        with open(dst + ".status", "w") as f:
            f.write(str(status))


def contract_with_extra_route(work, extra):
    """Add an advertised route to S1 and to every mirror of S1, so docs and
    discovery agree with one another; only runtime disagrees."""
    for url in (f"{cc.API}/v1/contract",
                f"{cc.API}/.well-known/whp-standing.json",
                f"{cc.SITE}/.well-known/whp-standing.json",
                f"{cc.ALIAS}/v1/contract"):
        c = json.loads(load(url))
        c["routes"].update(extra)
        store(work, url, json.dumps(c))


def run_gate(work, gate=True):
    env = dict(os.environ, WHP_CONFORMANCE_FIXTURE_DIR=work)
    cmd = [sys.executable, CHECKER] + (["--gate"] if gate else [])
    return subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=120)


CASES = []


def case(name, mutation, expect, gate=True):
    CASES.append((name, mutation, expect, gate))


# --- control: the unmodified snapshot ---
case("control: coherent snapshot passes advisory mode",
     lambda w: None,
     [("exit", 0), ("has", "0 FAIL")], gate=False)
case("control: gate passes and still reports the decided npm contradiction",
     lambda w: None,
     [("exit", 0), ("has", "D13 npm @wheelerhubbell/whp-standing-client"), ("has", "DECIDED"),
      ("has", "POST -> HTTP 400"), ("has", "0 FAIL"), ("has", "0 known open operator decisions")])

# --- adversarial case 1: contract advertises a route runtime does not serve ---
case("contract lists a route the deployment 404s",
     lambda w: contract_with_extra_route(w, {"audit": {"method": "POST", "path": "/v1/audit"}}),
     [("exit", 1), ("has", "D9 route /v1/audit"), ("has", "FAIL")])

# --- adversarial case 2: SDK predates the current payment protocol ---
def stale_npm(w):
    n = json.loads(load(cc.NPM))
    latest = n["dist-tags"]["latest"]
    n["time"][latest] = "2026-10-01T00:00:00.000Z"
    store(w, cc.NPM, json.dumps(n))

case("npm SDK predates the 2026-11-16 payment migration: decided, reported, not blocking",
     stale_npm,
     [("exit", 0), ("has", "D13 npm @wheelerhubbell/whp-standing-client"), ("has", "DECIDED"), ("has", "0 FAIL")])

# --- adversarial case 3: press presents hosted MCP access that does not exist ---
def press_mcp(w):
    body = load(f"{cc.SITE}/press/the-standing-mark-is-live.html").decode()
    body += '<p>MCP Server: <code>POST https://api.wheelerhubbellpublishing.com/mcp</code></p>'
    store(w, f"{cc.SITE}/press/the-standing-mark-is-live.html", body)

case("press page advertises a hosted MCP endpoint",
     press_mcp,
     [("exit", 1), ("has", "D6"), ("has", "FAIL")])

# --- adversarial case 4: active registry record points at a retired endpoint ---
def registry_retired(w):
    reg = json.loads(load(cc.REGISTRY))
    entry = reg["servers"][0]
    entry["server"]["version"] = "9.9.9"
    entry["_meta"]["io.modelcontextprotocol.registry/official"]["status"] = "active"
    entry["server"]["remotes"] = [{"type": "streamable-http",
                                   "url": "https://standing-guard-service.lovable.app/mcp"}]
    store(w, cc.REGISTRY, json.dumps(reg))

case("active MCP registry record points at a retired host",
     registry_retired,
     [("exit", 1), ("has", "D10"), ("has", "FAIL")])

# --- adversarial case 5: docs and discovery agree with each other, contradict runtime ---
case("discovery mirror matches contract but runtime contradicts both",
     lambda w: contract_with_extra_route(w, {"audit": {"method": "POST", "path": "/v1/audit"}}),
     [("exit", 1), ("has", "D1"), ("has", "D9 route /v1/audit"), ("has", "FAIL")])

# --- adversarial case 6: capability presented as live when only offline exists ---
def llms_dead_route(w):
    body = load(f"{cc.SITE}/llms.txt").decode()
    body += "\nSignature check: POST https://api.wheelerhubbellpublishing.com/v1/audit\n"
    store(w, f"{cc.SITE}/llms.txt", body)

case("llms.txt presents a nonexistent route as live",
     llms_dead_route,
     [("exit", 1), ("has", "D4"), ("has", "FAIL")])


def main():
    failures = 0
    for name, mutate, expect, gate in CASES:
        work = tempfile.mkdtemp(prefix="whp-gate-test-")
        try:
            shutil.copytree(BASE, work, dirs_exist_ok=True)
            mutate(work)
            r = run_gate(work, gate=gate)
            problems = []
            for kind, val in expect:
                if kind == "exit" and r.returncode != val:
                    problems.append(f"exit {r.returncode} != {val}")
                if kind == "has" and val not in r.stdout:
                    problems.append(f"missing {val!r}")
                if kind == "absent" and val in r.stdout:
                    problems.append(f"unexpected {val!r}")
            if problems:
                failures += 1
                print(f"BLOCKED-TEST FAIL  {name}: {'; '.join(problems)}")
                print("  --- checker output tail ---")
                print("  " + "\n  ".join(r.stdout.strip().splitlines()[-8:]))
            else:
                print(f"blocked as required  {name}")
        finally:
            shutil.rmtree(work, ignore_errors=True)
    print(f"\n{len(CASES)} adversarial cases: {len(CASES)-failures} blocked as required, {failures} test failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
