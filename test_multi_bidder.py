"""
Unit Test: Multi-Bidder Comparison Verification (Priority 5)
Tests compliance checking and recommendation logic across N (3+) bidders against a single common tender baseline.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.comparison.bid_comparator import compare_bids
from src.comparison.recommendation import generate_recommendation

def test_three_bidders():
    print("=" * 60)
    print("PRIORITY 5: MULTI-BIDDER COMPARISON & RECOMMENDATION TEST")
    print("=" * 60)

    tender_fields = {
        "completion_period": {"value": "12 months"},
        "performance_security": {"value": "10%"},
        "emd": {"value": "INR 5,00,000"}
    }

    # 3 Bidders:
    # Bidder A: Compliant on all (12 months, 10%, INR 5,00,000)
    # Bidder B: Non-compliant on completion period (15 months), compliant on others
    # Bidder C: Compliant on all (12 months, 10%, INR 5,00,000)
    bidders_list = [
        {
            "bidder_id": "bidder_A",
            "bidder_name": "Bidder A Infrastructure Ltd",
            "bidder_fields": {
                "completion_period": "12 months",
                "performance_security": "10%",
                "emd_submitted": "INR 5,00,000"
            }
        },
        {
            "bidder_id": "bidder_B",
            "bidder_name": "Bidder B Buildcon Pvt Ltd",
            "bidder_fields": {
                "completion_period": "15 months",  # Non-compliant (> 12 months)
                "performance_security": "10%",
                "emd_submitted": "INR 5,00,000"
            }
        },
        {
            "bidder_id": "bidder_C",
            "bidder_name": "Bidder C Engineers & Contractors",
            "bidder_fields": {
                "completion_period": "12 months",
                "performance_security": "10%",
                "emd_submitted": "INR 5,00,000"
            }
        }
    ]

    print("\n1. Running compare_bids with 3 bidders...")
    comp_result = compare_bids(tender_fields, bidders_list)

    assert "field_comparisons" in comp_result
    assert len(comp_result["field_comparisons"]) >= 3, f"Expected at least 3 criteria, got {len(comp_result['field_comparisons'])}"
    assert len(comp_result["bidders"]) == 3, f"Expected 3 bidders, got {len(comp_result['bidders'])}"

    # Check completion period results
    completion_item = next(item for item in comp_result["field_comparisons"] if item["field"] == "completion_period")
    assert completion_item["bidders"]["bidder_A"]["status"] == "COMPLIANT"
    assert completion_item["bidders"]["bidder_B"]["status"] == "NON-COMPLIANT"
    assert completion_item["bidders"]["bidder_C"]["status"] == "COMPLIANT"
    print("  ✓ Field comparison statuses verified across all 3 bidders.")

    # Check differences detection
    assert len(comp_result["differences"]) >= 1
    print("  ✓ Cross-bidder schedule difference correctly detected.")

    print("\n2. Running generate_recommendation...")
    rec = generate_recommendation(comp_result)

    assert rec["recommended_bidder_id"] == "bidder_A"
    assert rec["next_eligible_bidder_id"] == "bidder_C"
    assert rec["bidders"]["bidder_B"]["status"] == "NON-COMPLIANT"
    assert rec["bidders"]["bidder_A"]["status"] == "QUALIFIED"
    assert rec["bidders"]["bidder_C"]["status"] == "QUALIFIED"

    print("  ✓ Recommended Bidder (Rank 1):", rec["recommended_bidder"])
    print("  ✓ Next Eligible Bidder (Rank 2):", rec["next_eligible_bidder"])
    print("  ✓ Disqualified / Non-Compliant Bidder:", rec["bidders"]["bidder_B"]["name"])
    print("\n  Recommendation Text:\n ", rec["recommendation"])

    print("\n" + "=" * 60)
    print("ALL MULTI-BIDDER TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_three_bidders()
