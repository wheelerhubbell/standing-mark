#!/usr/bin/env python3
"""Adversarial tests for the reflexive enforcement-surface audit (offline).

Each case copies the captured live enforcement snapshot
(tests/fixtures/enforcement/live, captured from the GitHub API on 2026-11-21)
and injects one unexamined administrative transition: a deleted protection, a
flipped enforce_admins, a renamed required check, a missing tag ruleset, a
bypass actor, an enabled force-push, a restored archived repo. The audit must
refuse (exit 1) and name the drift. The control case proves the captured live
state conforms to enforcement/spec.json.

Run: python3 tests/run_enforcement_audit_tests.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(ROOT, "tests", "fixtures", "enforcement", "live")
AUDIT = os.path.join(ROOT, "scripts", "audit_enforcement.py")


def copy_snapshot(work):
    dst = os.path.join(work, "state")
    shutil.copytree(LIVE, dst)
    return dst


def load(state, repo, name):
    with open(os.path.join(state, repo, name), "r", encoding="utf-8") as f:
        return json.load(f)


def store(state, repo, name, body):
    with open(os.path.join(state, repo, name), "w", encoding="utf-8") as f:
        json.dump(body, f, indent=2)


def run_audit(state):
    return subprocess.run(
        [sys.executable, AUDIT, "--state-dir", state],
        capture_output=True, text=True,
    )


CASES = []


def case(fn):
    CASES.append(fn)
    return fn


@case
def control_live_snapshot_conforms(state):
    return 0, "0 drift"


@case
def protection_deleted(state):
    os.remove(os.path.join(state, "standing-mark", "protection.json"))
    return 1, "branch protection ABSENT"


@case
def enforce_admins_flipped(state):
    p = load(state, "standing-gate", "protection.json")
    p["enforce_admins"]["enabled"] = False
    store(state, "standing-gate", "protection.json", p)
    return 1, "enforce_admins"


@case
def required_check_removed(state):
    p = load(state, "whp-sentinel-template", "protection.json")
    p["required_status_checks"]["checks"] = []
    store(state, "whp-sentinel-template", "protection.json", p)
    return 1, "required checks"


@case
def tag_ruleset_absent(state):
    for f in os.listdir(os.path.join(state, "standing-gate")):
        if f.startswith("ruleset-"):
            os.remove(os.path.join(state, "standing-gate", f))
    return 1, "tag ruleset 'Standing Mark release tags are sealed' ABSENT"


@case
def tag_ruleset_bypass_actor_added(state):
    r = load(state, "wheelerhubbell.github.io", "ruleset-27811646.json")
    r["bypass_actors"] = [{"actor_id": 1, "actor_type": "OrganizationAdmin", "bypass_mode": "always"}]
    store(state, "wheelerhubbell.github.io", "ruleset-27811646.json", r)
    return 1, "bypass actors"


@case
def force_push_enabled(state):
    p = load(state, "wheelerhubbell.github.io", "protection.json")
    p["allow_force_pushes"]["enabled"] = True
    store(state, "wheelerhubbell.github.io", "protection.json", p)
    return 1, "allow_force_pushes"


@case
def archived_repo_restored(state):
    p = load(state, "WHPStanding", "repo.json")
    p["archived"] = False
    store(state, "WHPStanding", "repo.json", p)
    return 1, "archived"


def main():
    failures = 0
    for fn in CASES:
        work = tempfile.mkdtemp(prefix="enf-audit-")
        try:
            state = copy_snapshot(work)
            want_code, want_text = fn(state)
            res = run_audit(state)
            ok = res.returncode == want_code and want_text in (res.stdout + res.stderr)
            print("%s %s (exit %d, wanted %d and %r)" % ("PASS" if ok else "FAIL", fn.__name__, res.returncode, want_code, want_text))
            if not ok:
                failures += 1
                print(res.stdout)
                print(res.stderr)
        finally:
            shutil.rmtree(work, ignore_errors=True)
    if failures:
        print("%d/%d enforcement audit cases FAILED" % (failures, len(CASES)))
        return 1
    print("%d/%d enforcement audit cases behave as required" % (len(CASES), len(CASES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
