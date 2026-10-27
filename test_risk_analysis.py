import json
import sys
from pathlib import Path

from src.risk.risk_analyzer import (
    TenderRiskAnalyzer
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

# If neither file exists yet, provide standard synthetic tender data (SIDA/WORKS/001/2026)
if pdf_data is None:
    print("No processed JSON found on disk. Using synthetic baseline tender data (SIDA/WORKS/001/2026)...")
    pdf_data = {
        "tender_fields": {
            "tender_number": {"value": "SIDA/WORKS/001/2026", "page": 1, "evidence": "Tender No: SIDA/WORKS/001/2026"},
            "organisation": {"value": "Sample Infrastructure Development Authority", "page": 1, "evidence": "Organisation: SIDA"},
            "project_name": {"value": "Construction of Administrative and Training Building", "page": 1, "evidence": "Project: Admin Building"},
            "proposal_validity": {"value": "180 days", "page": 1, "evidence": "Proposal Validity: 180 days"},
            "emd": {"value": "INR 5,00,000", "page": 2, "evidence": "Earnest Money Deposit: INR 5,00,000"},
            "performance_security": {"value": "10% of accepted contract value", "page": 2, "evidence": "Performance Security equal to 10% of the accepted contract value"},
            "completion_period": {"value": "12 months", "page": 2, "evidence": "completed within 12 months"},
            "liquidated_damages": {"rate": "0.5%", "maximum": "10%", "page": 3, "evidence": "liquidated damages shall be levied at 0.5% up to maximum of 10%"},
            "eligibility": {"value": "Minimum technical score: 70/100", "page": 4, "evidence": "Mandatory technical qualification score: 70 marks"}
        }
    }


analyzer = TenderRiskAnalyzer()

risks = analyzer.analyze(
    pdf_data
)


print(
    "\nTENDER RISK ANALYSIS"
)

print(
    "=" * 60
)


for risk in risks:

    print(
        f"\n{risk['risk_id']}"
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
        "Risk:",
        risk["title"]
    )

    print(
        "Description:",
        risk["description"]
    )

    print(
        "Page:",
        risk["page"]
    )

    print(
        "Evidence:",
        risk["evidence"]
    )

assert len(risks) > 0, "No risks detected!"
print("\n" + "=" * 60)
print(f"TEST PASSED: Successfully detected and structured {len(risks)} tender risks.")
print("=" * 60)
