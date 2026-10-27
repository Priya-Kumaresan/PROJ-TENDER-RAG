import json
import sys
from pathlib import Path

from src.risk.risk_analyzer import (
    TenderRiskAnalyzer
)

from src.risk.risk_explainer import (
    RiskExplainer
)

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Attempt to load processed tender JSON from standard paths
possible_paths = [
    Path("data/processed/tender_001/tender.json"),
    Path("data/processed/tender_001_pdf.json")
]

pdf_data = None
for p in possible_paths:
    if p.exists():
        with open(p, "r", encoding="utf-8") as file:
            pdf_data = json.load(file)
            print(f"Loaded tender data from: {p}")
            break

# If neither file exists yet, provide standard synthetic tender data
if pdf_data is None:
    print("No processed JSON found on disk. Using synthetic baseline tender data...")
    pdf_data = {
        "tender_fields": {
            "tender_number": {"value": "SIDA/WORKS/001/2026", "page": 1, "evidence": "Tender No: SIDA/WORKS/001/2026"},
            "emd": {"value": "INR 5,00,000", "page": 2, "evidence": "Earnest Money Deposit of INR 5,00,000"},
            "performance_security": {"value": "10%", "page": 2, "evidence": "Performance Security equal to 10% of accepted contract value"},
            "completion_period": {"value": "12 months", "page": 2, "evidence": "Must be completed within 12 months"}
        }
    }


analyzer = TenderRiskAnalyzer()
explainer = RiskExplainer()


risks = analyzer.analyze(
    pdf_data
)


print("\nHYBRID TENDER RISK ANALYSIS")
print("=" * 70)


for risk in risks:

    print(
        f"\n{risk['risk_id']} - "
        f"{risk['title']}"
    )

    print(
        "Category:",
        risk["category"]
    )

    print(
        "Severity:",
        risk["severity"]
    )

    print(
        "Page:",
        risk["page"]
    )

    print(
        "\nTender Evidence:"
    )

    print(
        risk["evidence"]
    )

    print(
        "\nLLM / Hybrid Analysis:"
    )

    explanation = explainer.explain(
        risk
    )

    print(explanation)

    print("\n" + "-" * 70)

print("\n" + "=" * 70)
print(f"TEST PASSED: Hybrid risk analysis completed for {len(risks)} risks.")
print("=" * 70)
