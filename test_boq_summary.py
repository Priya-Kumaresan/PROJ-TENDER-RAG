import json

from src.boq.boq_summary import (
    calculate_boq_summary
)


with open(
    "data/processed/tender_001_boq.json",
    "r",
    encoding="utf-8"
) as file:

    items = json.load(file)


summary = calculate_boq_summary(
    items
)


print("\nBOQ FINANCIAL SUMMARY")
print("=" * 60)

print(
    "Quoted Subtotal:",
    summary["quoted_subtotal"]
)

print(
    "Corrected Subtotal:",
    summary["corrected_subtotal"]
)

print(
    "Subtotal Difference:",
    summary["subtotal_difference"]
)

print(
    "GST Rate:",
    summary["gst_rate"]
)

print(
    "Corrected GST:",
    summary["corrected_gst"]
)

print(
    "Corrected Total:",
    summary["corrected_total"]
)

print(
    "Incomplete Items:",
    summary["incomplete_items"]
)

print(
    "GST Rates Found:",
    summary["gst_rates_found"]
)