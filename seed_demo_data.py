"""
Demo Dataset Seeder
Populates data/processed/tender_001 with the complete dissertation sample dataset
so that all 7 Streamlit dashboard modules are immediately populated and interactive.
"""

import json
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.comparison.bid_comparator import compare_bids
from src.comparison.bidder_ranker import BidderRanker, save_ranking_results
from src.comparison.recommendation import generate_recommendation

OUTPUT_DIR = Path("data/processed/tender_001")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 1. Common Tender Data
tender_fields = {
    "tender_number": {
        "value": "SIDA/WORKS/001/2026",
        "page": 1,
        "evidence": "Tender No: SIDA/WORKS/001/2026"
    },
    "organisation": {
        "value": "Special Infrastructure Development Authority",
        "page": 1,
        "evidence": "Organisation: Special Infrastructure Development Authority"
    },
    "project_name": {
        "value": "Construction of Regional Transit Hub and Administrative Facility",
        "page": 1,
        "evidence": "Project: Construction of Regional Transit Hub and Administrative Facility"
    },
    "completion_period": {
        "value": "12 months",
        "page": 2,
        "evidence": "completed within 12 months from the date of handover of site"
    },
    "emd": {
        "value": "INR 5,00,000",
        "page": 2,
        "evidence": "Earnest Money Deposit (EMD) of INR 5,00,000 in the form of Bank Guarantee"
    },
    "performance_security": {
        "value": "10%",
        "page": 2,
        "evidence": "Performance Security equal to 10% of the accepted contract value"
    },
    "proposal_validity": {
        "value": "180 days",
        "page": 1,
        "evidence": "Proposal Validity: 180 days from the deadline of bid submission"
    },
    "min_technical_score": {
        "value": "70",
        "page": 3,
        "evidence": "mandatory minimum qualifying technical score is 70 marks"
    },
    "technical_weightage": {
        "value": "80%",
        "page": 3,
        "evidence": "Quality and Cost Based Selection (QCBS) with 80% Technical Weightage"
    },
    "financial_weightage": {
        "value": "20%",
        "page": 3,
        "evidence": "20% Financial Weightage"
    },
    "liquidated_damages": {
        "rate": "0.5%",
        "maximum": "10%",
        "page": 4,
        "evidence": "liquidated damages shall be levied at 0.5% per week subject to a maximum of 10%"
    }
}

tender_data = {
    "tender_id": "tender_001",
    "total_pages": 4,
    "tender_fields": tender_fields
}

with open(OUTPUT_DIR / "tender.json", "w", encoding="utf-8") as f:
    json.dump(tender_data, f, indent=4, ensure_ascii=False)

# 2. Common Tender BOQ Data
tender_boq = [
    {"item_no": "1.01", "description": "Earthwork excavation in all types of soil", "quantity": 1500.0, "unit": "cum", "rate": 350.0, "amount": 525000.0, "gst": 18.0},
    {"item_no": "1.02", "description": "Plain Cement Concrete (PCC 1:4:8)", "quantity": 400.0, "unit": "cum", "rate": 4500.0, "amount": 1800000.0, "gst": 18.0},
    {"item_no": "1.03", "description": "Reinforced Cement Concrete (RCC M25)", "quantity": 850.0, "unit": "cum", "rate": 8200.0, "amount": 6970000.0, "gst": 18.0},
    {"item_no": "1.04", "description": "TMT Steel reinforcement Fe500D", "quantity": 95.0, "unit": "MT", "rate": 68000.0, "amount": 6460000.0, "gst": 18.0},
    {"item_no": "1.05", "description": "Structural steel framing and roof trusses", "quantity": 120.0, "unit": "MT", "rate": 78000.0, "amount": 9360000.0, "gst": 18.0}
]

with open(OUTPUT_DIR / "tender_boq.json", "w", encoding="utf-8") as f:
    json.dump(tender_boq, f, indent=4, ensure_ascii=False)

# 3. Bidder A (Alpha Construction Pvt Ltd)
bidder_A_fields = {
    "bidder_name": {"value": "Alpha Construction Pvt Ltd", "page": 1, "evidence": "Company Name: Alpha Construction Pvt Ltd"},
    "registration_number": {"value": "CIN-U45200MH2012PTC234567", "page": 1, "evidence": "CIN: CIN-U45200MH2012PTC234567"},
    "technical_score": {"value": "82", "page": 2, "evidence": "Technical evaluation score: 82 marks"},
    "total_quoted_amount": {"value": "INR 4.82 crore", "page": 1, "evidence": "Total Quoted Bid Amount: INR 4.82 crore"},
    "completion_period": {"value": "12 months", "page": 1, "evidence": "Completion period: 12 months"},
    "performance_security": {"value": "10%", "page": 2, "evidence": "Performance security: 10%"},
    "emd_submitted": {"value": "INR 5,00,000", "page": 1, "evidence": "EMD: INR 5,00,000"}
}
bidder_A_boq = [
    {"item_no": "1.01", "description": "Earthwork excavation", "quantity": 1500.0, "rate": 340.0, "quoted_amount": 510000.0, "expected_amount": 510000.0, "status": "VALID", "issues": []},
    {"item_no": "1.02", "description": "Plain Cement Concrete", "quantity": 400.0, "rate": 4400.0, "quoted_amount": 1760000.0, "expected_amount": 1760000.0, "status": "VALID", "issues": []},
    {"item_no": "1.03", "description": "Reinforced Cement Concrete", "quantity": 850.0, "rate": 8100.0, "quoted_amount": 6885000.0, "expected_amount": 6885000.0, "status": "VALID", "issues": []}
]
bidder_A_data = {
    "bidder_id": "bidder_A",
    "bidder_name": "Alpha Construction Pvt Ltd",
    "bidder_fields": bidder_A_fields,
    "boq_validation": bidder_A_boq
}
with open(OUTPUT_DIR / "bidder_A.json", "w", encoding="utf-8") as f:
    json.dump(bidder_A_data, f, indent=4, ensure_ascii=False)

# 4. Bidder B (Beta Infrastructure Ltd) - DISQUALIFIED for 15 months completion
bidder_B_fields = {
    "bidder_name": {"value": "Beta Infrastructure Ltd", "page": 1, "evidence": "Company Name: Beta Infrastructure Ltd"},
    "registration_number": {"value": "CIN-L45201DL2008PLC178901", "page": 1, "evidence": "CIN: CIN-L45201DL2008PLC178901"},
    "technical_score": {"value": "88", "page": 2, "evidence": "Technical evaluation score: 88 marks"},
    "total_quoted_amount": {"value": "INR 4.65 crore", "page": 1, "evidence": "Total Quoted Bid Amount: INR 4.65 crore"},
    "completion_period": {"value": "15 months", "page": 1, "evidence": "Completion period: 15 months"},
    "performance_security": {"value": "10%", "page": 2, "evidence": "Performance security: 10%"},
    "emd_submitted": {"value": "INR 5,00,000", "page": 1, "evidence": "EMD: INR 5,00,000"}
}
bidder_B_boq = [
    {"item_no": "1.01", "description": "Earthwork excavation", "quantity": 1500.0, "rate": 320.0, "quoted_amount": 480000.0, "expected_amount": 480000.0, "status": "VALID", "issues": []},
    {"item_no": "1.02", "description": "Plain Cement Concrete", "quantity": 400.0, "rate": 4300.0, "quoted_amount": 1720000.0, "expected_amount": 1720000.0, "status": "VALID", "issues": []}
]
bidder_B_data = {
    "bidder_id": "bidder_B",
    "bidder_name": "Beta Infrastructure Ltd",
    "bidder_fields": bidder_B_fields,
    "boq_validation": bidder_B_boq
}
with open(OUTPUT_DIR / "bidder_B.json", "w", encoding="utf-8") as f:
    json.dump(bidder_B_data, f, indent=4, ensure_ascii=False)

# 5. Bidder C (Gamma Infra Projects)
bidder_C_fields = {
    "bidder_name": {"value": "Gamma Infra Projects", "page": 1, "evidence": "Company Name: Gamma Infra Projects"},
    "registration_number": {"value": "CIN-U45202KA2015PTC089123", "page": 1, "evidence": "CIN: CIN-U45202KA2015PTC089123"},
    "technical_score": {"value": "79", "page": 2, "evidence": "Technical evaluation score: 79 marks"},
    "total_quoted_amount": {"value": "INR 4.75 crore", "page": 1, "evidence": "Total Quoted Bid Amount: INR 4.75 crore"},
    "completion_period": {"value": "12 months", "page": 1, "evidence": "Completion period: 12 months"},
    "performance_security": {"value": "10%", "page": 2, "evidence": "Performance security: 10%"},
    "emd_submitted": {"value": "INR 5,00,000", "page": 1, "evidence": "EMD: INR 5,00,000"}
}
bidder_C_boq = [
    {"item_no": "1.01", "description": "Earthwork excavation", "quantity": 1500.0, "rate": 330.0, "quoted_amount": 495000.0, "expected_amount": 495000.0, "status": "VALID", "issues": []},
    {"item_no": "1.02", "description": "Plain Cement Concrete", "quantity": 400.0, "rate": 4350.0, "quoted_amount": 1740000.0, "expected_amount": 1740000.0, "status": "VALID", "issues": []}
]
bidder_C_data = {
    "bidder_id": "bidder_C",
    "bidder_name": "Gamma Infra Projects",
    "bidder_fields": bidder_C_fields,
    "boq_validation": bidder_C_boq
}
with open(OUTPUT_DIR / "bidder_C.json", "w", encoding="utf-8") as f:
    json.dump(bidder_C_data, f, indent=4, ensure_ascii=False)

all_bidders_data = [bidder_A_data, bidder_B_data, bidder_C_data]

# 6. Run Multi-Bidder Comparison
comparison_result = compare_bids(tender_fields, all_bidders_data)

# 7. Run Bidder Ranker
boq_evals = {
    b["bidder_id"]: {
        "summary": {
            "total_items": len(b.get("boq_validation", [])),
            "missing_rates": sum(1 for itm in b.get("boq_validation", []) if "Missing Rate" in itm.get("issues", [])),
            "fatal_anomalies": sum(1 for itm in b.get("boq_validation", []) if str(itm.get("status", "")).upper() == "ERROR")
        }
    }
    for b in all_bidders_data
}

ranker = BidderRanker()
ranking_result = ranker.rank_bidders(tender_fields, all_bidders_data, boq_evals)
save_ranking_results(ranking_result, str(OUTPUT_DIR / "bidder_ranking.json"))

# 8. Align Recommendation
rec_result = generate_recommendation(comparison_result, ranking_data=ranking_result, bidders_data=all_bidders_data)
comparison_result["recommended_bidder"] = ranking_result["recommended_bidder"]
comparison_result["recommendation"] = ranking_result["recommendation_statement"]
comparison_result["next_eligible_bidder"] = ranking_result.get("next_eligible_bidder")
comparison_result["recommendation_details"] = rec_result
comparison_result["ranking_summary"] = ranking_result

with open(OUTPUT_DIR / "bid_comparison.json", "w", encoding="utf-8") as f:
    json.dump(comparison_result, f, indent=4, ensure_ascii=False)

print("Demo dataset seeded successfully into data/processed/tender_001:")
print(f"  ✓ Tender: {tender_fields['tender_number']['value']}")
print(f"  ✓ Bidders: Alpha Construction, Beta Infrastructure, Gamma Infra Projects")
print(f"  ✓ Recommended (Rank 1): {ranking_result['recommended_bidder']}")
print(f"  ✓ Next Eligible (Rank 2): {ranking_result['next_eligible_bidder']}")
print(f"  ✓ Disqualified: {ranking_result['disqualified_bidders'][0]['bidder_name']} (Schedule overrun)")

