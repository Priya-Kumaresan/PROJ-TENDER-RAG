import json
from pathlib import Path

from src.risk.risk_analyzer import (
    TenderRiskAnalyzer
)


json_path = Path(
    "data/processed/tender_001_pdf.json"
)


with open(
    json_path,
    "r",
    encoding="utf-8"
) as file:

    pdf_data = json.load(file)


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