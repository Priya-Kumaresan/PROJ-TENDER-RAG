import json
from pathlib import Path

from src.risk.risk_analyzer import (
    TenderRiskAnalyzer
)

from src.risk.risk_explainer import (
    RiskExplainer
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
        "\nLLM Analysis:"
    )

    explanation = explainer.explain(
        risk
    )

    print(explanation)

    print("\n" + "-" * 70)