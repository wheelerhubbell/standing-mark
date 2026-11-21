# One-truth conformance: dependency map and propagation rule

Decision Integrity applies recursively to every public representation of the
system. Machine-readable surfaces (contract, discovery documents, agent card,
OpenAPI, SKILL.md, llms.txt, registry records, schemas, verifiers, this
conformance data) are the primary representation; human prose (press, guides,
how-to pages, spoken descriptions) is derived from them. When prose and a
machine surface disagree, the machine surface under the live contract governs
and the prose is corrected to match. No update may land in one place and
leave another stale: when a source
of truth changes, every dependent surface changes with it, and
`scripts/check_conformance.py` (read-only, GETs only) proves they did.

## Sources of truth (SOT)

| ID | Surface | What it owns |
|---|---|---|
| S1 | `GET /v1/contract` (= `/.well-known/whp-standing.json`) on `api.wheelerhubbellpublishing.com` | routes, payment terms, input schema, publications, changelog |
| S2 | `GET /.well-known/whp-issuer.json` | issuer key and key id |
| S3 | `GET /openapi.json` | machine API description |
| S4 | `GET /health` | liveness, version, environment |
| S5 | `GET /v1/reception/contract` | Standing Reception routes, pinned issuers, guarantees |
| S6 | the two publication pages named in `S1.publications` | governing instruments |

## Dependent surfaces (each derives from a SOT)

| ID | Surface | Derives from | Rule |
|---|---|---|---|
| D1 | `wheelerhubbellpublishing.com/.well-known/whp-standing.json` | S1 | JSON-identical mirror |
| D2 | `decisionintegrity.wheelerhubbellpublishing.com` | S1, S2, S3, S4 | byte-identical alias |
| D3 | site `openapi.json`, repo `openapi.json` | S3 | byte-identical mirrors |
| D4 | site `llms.txt` | S1 + live routes | advertises only resolving routes and current terms |
| D5 | `developers.html` | S1 payment | teaches the current scheme only |
| D6 | press page | S1 | presents no retired endpoint as live |
| D7 | repo docs (payment, quick-start, test-vectors, SKILL) | S1 | current scheme only; retired scheme named retired |
| D8 | agent cards (site + repo) | S1 profile | version matches; no unannotated dead route |
| D9 | every route S1/S3 advertise | S1, S3 | resolves non-404 |
| D10 | MCP registry records | S1 | active records' remotes resolve; none point at retired hosts |
| D11 | reception component | S2 | pinned issuer key == published key id |
| D12 | publications | S1.publications | every named page resolves; alias host serves S5 |
| D13 | npm registry | S1 payment | no current package contradicts the source SDKs |
| D14 | issuer key integrity | S2 vs S1 | key id == sha256(published key); contract names the issuer doc |

## Propagation rule

1. A change lands in exactly one source of truth at a time.
2. In the same change, every dependent surface in the rows above is updated.
3. `python3 scripts/check_conformance.py` is run and must report 0 failures
   before the change is described to anyone as done.
4. A surface that cannot be updated in the same change is entered as a known
   open decision with the exact decision the operator must make; the checker
   reports it as OPEN, never as PASS.
5. The checker is read-only by construction. Any automation that would write
   (auto-sync workflows, self-healing deploys) is a separate proposal
   requiring the operator's specific word.

## Running

```
python3 scripts/check_conformance.py
```

Exit code 0: every check passes or is a declared open decision. Exit code 1:
at least one dependent surface disagrees with its source of truth.

## Release control (added 2026-11-21, upstream correction)

The checker is the examination a release must consume. Decision Integrity
governs the decision to release, not only the description of a bad one.

Release paths and their gates:

| Release path | Mechanism | Gate |
|---|---|---|
| `wheelerhubbell/standing-mark` (SDKs, docs, SKILL, agent card, OpenAPI mirror) | push to `main` is publication | `.github/workflows/conformance.yml` + branch protection |
| `wheelerhubbell/wheelerhubbellpublishing.com` (Pages site: discovery mirror, llms.txt, press, developers, spec, publications) | merge to `main` deploys via GitHub Pages | `.github/workflows/conformance.yml` (runs this checker with `--site-root`) + branch protection |
| Hostinger (`/v1/contract`, well-knowns, openapi on both hosts) | FTPS upload, live immediately | gated indirectly: an unpropagated source-of-truth change turns every repo gate red until dependents catch up; a pre-upload examination wrapper remains a proposal (operator's word) |
| npm / MCP Registry / GitHub Marketplace / x402scan | manual, third-party | watched by D10 and D13; a stale record blocks every repo release until resolved or declared open |

Gate rules:

1. `--gate` mode is the release mode. It exits 1 on any FAIL **and** on any
   unresolved known open decision: a release is not authorized while a
   contradiction is unresolved.
2. Repo surfaces are examined at the release candidate (`--repo-ref` for this
   repo, `--site-root` for the site), so a change that resolves a
   contradiction can pass while one that carries it forward cannot.
3. Branch protection on `main` in both repos requires the `conformance`
   check and a pull request, and applies to administrators: no direct push
   bypasses the examination.
4. `tests/run_adversarial_tests.py` proves the gate offline against the
   November 21 failure shapes (dead advertised route, stale SDK, hosted-MCP
   claim, retired-host registry record, docs/discovery agreeing against
   runtime, offline-only capability presented as live). The workflow runs it
   on every release attempt.
5. The checker remains read-only. Automated writes (auto-sync, self-healing
   deploys, upload wrappers that roll back) remain a separate proposal
   requiring the operator's specific word.
