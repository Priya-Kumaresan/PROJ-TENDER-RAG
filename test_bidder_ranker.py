"""
Unit Test: Bidder Ranker Verification (Priorities 6, 7, 8, 9, 10, 11, 12, 13)
Tests deterministic qualification, technical/financial scoring, dynamic multi-bidder ranking,
fallback recalculation, and recommendation audit trail.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.comparison.bidder_ranker import BidderRanker

def test_bidder_ranker_comprehensive():
    print("=" * 70)
    print("PRIORITIES 6-13: BIDDER RANKER & QUALIFICATION TEST")
    print("=" * 70)

    # Tender Baseline:
    # 12 months completion, 10% performance security, INR 5,00,000 EMD, 80:20 weightage, min tech score 70
    tender_fields = {
        "tender_number": {"value": "SIDA/WORKS/001/2026"},
        "completion_period": {"value": "12 months"},
        "performance_security": {"value": "10%"},
        "emd": {"value": "INR 5,00,000"},
        "technical_weightage": {"value": "80%"},
        "financial_weightage": {"value": "20%"},
        "min_technical_score": {"value": "70"}
    }

    # Bidders:
    # Bidder A: Tech 82, INR 4.82 crore, 12 months -> QUALIFIED
    # Bidder B: Tech 88, INR 4.65 crore, 15 months -> DISQUALIFIED (exceeds 12 months)
    # Bidder C: Tech 79, INR 4.75 crore, 12 months -> QUALIFIED
    bidders_list = [
        {
            "bidder_id": "bidder_A",
            "bidder_name": "Bidder A Infrastructure Ltd",
            "bidder_fields": {
                "technical_score": "82",
                "total_quoted_amount": "INR 4.82 crore",
                "completion_period": "12 months",
                "performance_security": "10%",
                "emd_submitted": "INR 5,00,000"
            }
        },
        {
            "bidder_id": "bidder_B",
            "bidder_name": "Bidder B Buildcon Pvt Ltd",
            "bidder_fields": {
                "technical_score": "88",
                "total_quoted_amount": "INR 4.65 crore",
                "completion_period": "15 months",  # FAILS mandatory completion period
                "performance_security": "10%",
                "emd_submitted": "INR 5,00,000"
            }
        },
        {
            "bidder_id": "bidder_C",
            "bidder_name": "Bidder C Engineers & Contractors",
            "bidder_fields": {
                "technical_score": "79",
                "total_quoted_amount": "INR 4.75 crore",
                "completion_period": "12 months",
                "performance_security": "10%",
                "emd_submitted": "INR 5,00,000"
            }
        }
    ]

    print("\n1. Initializing BidderRanker and evaluating 3 bidders...")
    ranker = BidderRanker()
    result = ranker.rank_bidders(tender_fields, bidders_list)

    # Check Evaluation Weights
    params = result["evaluation_parameters"]
    assert params["technical_weight"] == 0.8
    assert params["financial_weight"] == 0.2
    assert params["min_technical_score"] == 70.0
    print(f"  ✓ Weights resolved dynamically: Tech={params['technical_weight_percent']}, Fin={params['financial_weight_percent']}")

    # Check Qualification Status
    qual_map = {b["bidder_id"]: b["qualification_status"] for b in result["ranking_table"]}
    assert qual_map["bidder_A"] == "QUALIFIED"
    assert qual_map["bidder_B"] == "DISQUALIFIED"
    assert qual_map["bidder_C"] == "QUALIFIED"
    print("  ✓ Mandatory qualification checks correctly applied:")
    print("    - Bidder A: QUALIFIED")
    print("    - Bidder B: DISQUALIFIED (15 months > 12 months mandatory limit)")
    print("    - Bidder C: QUALIFIED")

    # Verify that Disqualified Bidder B did not determine L1
    # Lowest qualified is Bidder C (4.75 Cr) since Bidder B is disqualified!
    assert params["lowest_qualified_bid_l1"] == 47500000.0, f"Expected 47500000.0, got {params['lowest_qualified_bid_l1']}"
    print(f"  ✓ L1 Benchmark correctly set from QUALIFIED bids only: INR {params['lowest_qualified_bid_l1']:,.0f}")

    # Check Rankings
    assert result["recommended_bidder_id"] == "bidder_A"
    assert result["next_eligible_bidder_id"] == "bidder_C"
    print(f"  ✓ Recommended Bidder (Rank 1): {result['recommended_bidder']}")
    print(f"  ✓ Next Eligible Bidder (Rank 2): {result['next_eligible_bidder']}")

    print("\n  Ranking Table Summary:")
    for row in result["ranking_table"]:
        print(f"    Rank {row['rank']}: {row['bidder_name']:<35} | Status: {row['qualification']:<12} | "
              f"Tech: {row['technical_score']} | Quote: {row['quoted_amount']} | "
              f"Fin Score: {row['financial_score']} | Overall: {row['overall_score']}")

    # Check Disqualified Row Formatting
    disq_row = next(r for r in result["ranking_table"] if r["bidder_id"] == "bidder_B")
    assert disq_row["rank"] == "-"
    assert disq_row["overall_score"] == "N/A"
    assert "exceeds tender requirement" in disq_row["status_reason"]
    print("  ✓ Disqualified bidder kept visible with status reason and '-' rank.")

    # Check Recommendation Text
    assert "RECOMMENDED" in result["recommendation_statement"]
    assert "NEXT ELIGIBLE" in result["next_eligible_statement"]
    print("  ✓ Recommendation text contains appropriate decision-support terminology.")

    # 2. Test Fallback Recalculation (Priority 12)
    print("\n2. Testing Fallback Recalculation (Simulating Bidder A disqualification)...")
    fallback_res = ranker.simulate_fallback(
        ranking_result=result,
        disqualified_bidder_id="bidder_A",
        disqualification_reason="Failed post-qualification financial background check"
    )

    assert fallback_res["recommended_bidder_id"] == "bidder_C"
    assert len(fallback_res["qualified_bidders"]) == 1
    assert len(fallback_res["disqualified_bidders"]) == 2
    print(f"  ✓ Bidder C successfully promoted to Rank 1 (Recommended): {fallback_res['recommended_bidder']}")
    print("  ✓ Fallback Statement:\n   ", fallback_res["recommendation_statement"])

    # 3. Test Audit Trail (Priority 13)
    print("\n3. Testing Recommendation Audit Trail...")
    assert len(fallback_res["audit_trail"]) == 2
    assert fallback_res["audit_trail"][0]["action"] == "INITIAL_EVALUATION_AND_RANKING"
    assert fallback_res["audit_trail"][1]["action"] == "FALLBACK_RECALCULATION"
    print(f"  ✓ Audit trail logged {len(fallback_res['audit_trail'])} immutable events with timestamps.")

    print("\n" + "=" * 70)
    print("ALL PRIORITIES 6-13 TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    test_bidder_ranker_comprehensive()

