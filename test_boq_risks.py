import json
from pathlib import Path

from src.boq.boq_validator import (
    analyze_boq_risks
)


boq_path = Path(
    "data/processed/tender_001_boq.json"
)


with open(
    boq_path,
    "r",
    encoding="utf-8"
) as file:

    boq_data = json.load(file)


# Adjust this only if your JSON uses
# a different key for the BOQ rows.
items = boq_data


risks = analyze_boq_risks(
    items
)


print("\nBOQ RISK ANALYSIS")
print("=" * 60)


if not risks:

    print(
        "No BOQ anomalies detected."
    )


for risk in risks:

    print(
        f"\nItem: {risk['item_no']}"
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
        "Issue:",
        risk["issue"]
    )

    print(
        "Description:",
        risk["description"]
    )

    if (
        risk["category"]
        == "Calculation Error"
    ):

        print(
            "Expected Amount:",
            risk["expected_amount"]
        )

        print(
            "Actual Amount:",
            risk["actual_amount"]
        )

        print(
            "Difference:",
            risk["difference"]
        )

        if (
            risk["category"]
            == "Duplicate Item"
        ):

            print(
                "Possible Duplicate Of Item:",
                risk["duplicate_of"]
                )