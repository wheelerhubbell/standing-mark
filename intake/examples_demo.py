import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from standing_intake import intake
C = "The published contract names Base mainnet USDC as the payment asset."
for name, s in [("plain sentence", C),
                ("labeled text", "Claim: %s\nEvidence:\nThe payment asset is USDC.\nSource: https://example.test/c" % C),
                ("old nested JSON", {"claim": {"statement": C}, "material": {"source_url": "https://example.test/c", "contract": {"asset": "USDC"}}}),
                ("document, no proposition", "Section 1. The agreement was signed March 3.\nSection 2. Payment is due in 30 days.")]:
    r = intake(s); e = r["examinability"]
    print("%-26s -> %-22s gate=%s" % (name, e["level"], e["quote_gate"]))
    if r["canonical_submissions"]: print("   engine input:", json.dumps(r["canonical_submissions"][0])[:150])
    for d in e["disclosures"]: print("   disclosure:", d[:110])
    if e["missing"]: print("   missing:", e["missing"])
