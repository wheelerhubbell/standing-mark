#!/usr/bin/env python3
"""Reflexive enforcement-surface audit (read-only).

Decision Integrity applies to the mechanisms that enforce Decision Integrity.
The branch protections and tag rulesets that make examination a necessary
condition of release are administrative controls; a change to them is itself a
consequential transition and must not pass unexamined. This audit compares the
live GitHub administrative surface of every controlled repo against the
examined declaration in enforcement/spec.json and refuses (exit 1) on any
divergence. It performs GETs only and never writes anything.

What it catches: a protection deleted, a required check renamed or dropped,
enforce_admins switched off, force-push or deletion enabled, a tag ruleset
removed or weakened, a bypass actor added, an archived repo restored. Each of
those is an unexamined change to the conditions governing release authority.

Modes:
  --live        fetch current state from the GitHub API. Needs a token with
                read-only Administration on the audited repos, passed in the
                WHP_ENFORCEMENT_AUDIT_TOKEN (or GH_TOKEN) environment variable.
                The token is read from the environment, never from argv, and
                is never printed.
  --state-dir D offline mode: read pre-fetched API JSON from D, laid out as
                D/<repo>/protection.json, D/<repo>/repo.json,
                D/<repo>/ruleset-<id>.json. Used by the offline test suite.

Exit code 0 when the live administrative surface matches the spec exactly;
1 on any drift, missing state, or failed fetch. A failed examination
authorizes nothing.
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC_PATH = os.path.join(ROOT, "enforcement", "spec.json")

API = "https://api.github.com"


def load_spec():
    with open(SPEC_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class LiveFetcher:
    def __init__(self, token):
        self.token = token

    def get(self, path):
        req = urllib.request.Request(
            API + path,
            headers={
                "Authorization": "Bearer " + self.token,
                "Accept": "application/vnd.github+json",
                "User-Agent": "whp-enforcement-audit",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8")), resp.status
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read().decode("utf-8"))
            except Exception:
                body = {}
            return body, e.code


class DirFetcher:
    def __init__(self, root):
        self.root = root

    def get(self, path):
        # /repos/{owner}/{repo}/branches/main/protection -> <repo>/protection.json
        # /repos/{owner}/{repo} -> <repo>/repo.json
        # /repos/{owner}/{repo}/rulesets -> list of <repo>/ruleset-*.json
        parts = path.strip("/").split("/")
        repo = parts[2]
        base = os.path.join(self.root, repo)
        if path.endswith("/protection"):
            p = os.path.join(base, "protection.json")
            if not os.path.exists(p):
                return {"message": "Branch not protected"}, 404
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f), 200
        if path.endswith("/rulesets"):
            out = []
            if os.path.isdir(base):
                for name in sorted(os.listdir(base)):
                    if name.startswith("ruleset-") and name.endswith(".json"):
                        with open(os.path.join(base, name), "r", encoding="utf-8") as f:
                            out.append(json.load(f))
            return out, 200
        if len(parts) == 5 and parts[3] == "rulesets":
            p = os.path.join(base, "ruleset-%s.json" % parts[4])
            if not os.path.exists(p):
                return {"message": "Not Found"}, 404
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f), 200
        if len(parts) == 3:
            p = os.path.join(base, "repo.json")
            if not os.path.exists(p):
                return {"message": "Not Found"}, 404
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f), 200
        raise ValueError("unsupported path: " + path)


def audit_repo(repo, spec, fetch, drift):
    owner, name = repo.split("/")
    body, status = fetch.get("/repos/%s/%s/branches/%s/protection" % (owner, name, spec["branch"]))
    if status != 200:
        drift.append("%s: branch protection ABSENT on %s (API status %s)" % (repo, spec["branch"], status))
        return
    checks = sorted(c.get("context") for c in body.get("required_status_checks", {}).get("checks", []))
    if checks != sorted(spec["required_checks"]):
        drift.append("%s: required checks are %s, spec requires %s" % (repo, checks, sorted(spec["required_checks"])))
    if body.get("enforce_admins", {}).get("enabled") is not spec["enforce_admins"]:
        drift.append("%s: enforce_admins=%s, spec requires %s" % (repo, body.get("enforce_admins", {}).get("enabled"), spec["enforce_admins"]))
    pr_required = body.get("required_pull_request_reviews") is not None
    if pr_required is not spec["require_pull_request"]:
        drift.append("%s: pull-request requirement=%s, spec requires %s" % (repo, pr_required, spec["require_pull_request"]))
    if body.get("allow_force_pushes", {}).get("enabled") is not spec["allow_force_pushes"]:
        drift.append("%s: allow_force_pushes=%s, spec requires %s" % (repo, body.get("allow_force_pushes", {}).get("enabled"), spec["allow_force_pushes"]))
    if body.get("allow_deletions", {}).get("enabled") is not spec["allow_deletions"]:
        drift.append("%s: allow_deletions=%s, spec requires %s" % (repo, body.get("allow_deletions", {}).get("enabled"), spec["allow_deletions"]))


def audit_tag_ruleset(repo, rspec, fetch, drift):
    owner, name = repo.split("/")
    body, status = fetch.get("/repos/%s/%s/rulesets" % (owner, name))
    if status != 200:
        drift.append("%s: rulesets unreadable (API status %s)" % (repo, status))
        return
    match = None
    for rs in body if isinstance(body, list) else []:
        if rs.get("target") == "tag" and rs.get("name") == rspec["name"]:
            match = rs
            break
    if match is None:
        drift.append("%s: tag ruleset '%s' ABSENT" % (repo, rspec["name"]))
        return
    if "rules" not in match and "id" in match:
        # the list endpoint returns summaries; fetch the full ruleset
        match, status = fetch.get("/repos/%s/%s/rulesets/%s" % (owner, name, match["id"]))
        if status != 200:
            drift.append("%s: tag ruleset '%s' unreadable (API status %s)" % (repo, rspec["name"], status))
            return
    if match.get("enforcement") != rspec["enforcement"]:
        drift.append("%s: tag ruleset enforcement=%s, spec requires %s" % (repo, match.get("enforcement"), rspec["enforcement"]))
    include = match.get("conditions", {}).get("ref_name", {}).get("include", [])
    if sorted(include) != sorted(rspec["include_refs"]):
        drift.append("%s: tag ruleset includes %s, spec requires %s" % (repo, include, rspec["include_refs"]))
    rules = sorted(r.get("type") for r in match.get("rules", []))
    if rules != sorted(rspec["rules"]):
        drift.append("%s: tag ruleset rules %s, spec requires %s" % (repo, rules, sorted(rspec["rules"])))
    bypass = match.get("bypass_actors", [])
    if len(bypass) != rspec["bypass_actors"]:
        drift.append("%s: tag ruleset has %d bypass actors, spec requires 0" % (repo, len(bypass)))


def audit_archived(repo, fetch, drift):
    body, status = fetch.get("/repos/" + repo)
    if status != 200:
        drift.append("%s: repo unreadable (API status %s)" % (repo, status))
        return
    if body.get("archived") is not True:
        drift.append("%s: archived=%s, spec requires true" % (repo, body.get("archived")))


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--live", action="store_true")
    src.add_argument("--state-dir")
    args = ap.parse_args()

    if args.live:
        token = os.environ.get("WHP_ENFORCEMENT_AUDIT_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            print("REFUSED: no audit token in WHP_ENFORCEMENT_AUDIT_TOKEN/GH_TOKEN; a failed examination authorizes nothing")
            return 1
        fetch = LiveFetcher(token)
    else:
        fetch = DirFetcher(args.state_dir)

    spec = load_spec()
    drift = []
    for repo, rspec in spec["repos"].items():
        audit_repo(repo, rspec, fetch, drift)
    for repo, rspec in spec["tag_rulesets"].items():
        audit_tag_ruleset(repo, rspec, fetch, drift)
    for repo in spec["archived_repos"]:
        audit_archived(repo, fetch, drift)

    total = len(spec["repos"]) + len(spec["tag_rulesets"]) + len(spec["archived_repos"])
    if drift:
        print("ENFORCEMENT DRIFT: %d unexamined transition(s) on the administrative surface:" % len(drift))
        for d in drift:
            print("  DRIFT " + d)
        print("Examination result: FAIL. No authorization issued.")
        return 1
    print("Enforcement surface conforms to enforcement/spec.json (%d controlled items examined, 0 drift)." % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
