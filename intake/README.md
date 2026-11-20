# Universal Intake (WHP-INTAKE-1.0.0)

A deterministic layer that sits upstream of the examination engine. It takes a submission in whatever form it arrives, keeps the original and its SHA-256, and returns an Intake Record that keeps source, extracted, interpreted and inferred content apart. It emits the engine's flat submission shape only when that is justified, and says what is missing otherwise. No model is used. It does not examine, decide or authorize anything.

## Status (labels are literal)

| Item | Status |
|---|---|
| Python reference implementation (`standing_intake/`) | published, tested (`cd intake && python -m pytest`) |
| PHP reference port (`php/src/DiIntakeUniversal.php`) | published; byte-for-byte parity with the Python reference on the fixtures in `php/tests` (`php php/tests/parity_test.php`) |
| Live service | The live door runs this layer (WHP-INTAKE-1.3.0 since 2026-11-20): distinct conflicting values across the proposition alias fields are refused with 400 AMBIGUOUS_INPUT_ALIASES before any payment movement. Check `GET /v1/contract` for what the service accepts. |

## Use

```python
from standing_intake import intake
record = intake("Claim: The invoice total is 120.00.\nEvidence:\nInvoice line items sum to 120.00.")
record["examinability"]["level"]   # EXAMINABLE | EXAMINABLE_WITH_LIMITS | NOT_EXAMINABLE
record["canonical_submissions"]    # engine-shape objects, each field traced to an extracted item
```

Documents: [specification](docs/universal-intake-spec.md), [compatibility and migration](docs/compatibility-and-migration.md). Payment is unchanged: a flat 1.00 USDC per examination.
