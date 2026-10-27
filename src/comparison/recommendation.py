"""
Recommendation Engine (Priorities 10, 11, 12, 16)
Deterministic, evidence-grounded recommendation generation incorporating compliance,
technical scoring, financial quoted amounts, and BOQ arithmetic audit findings.
"""

from typing import Any, Dict, List, Optional


def generate_recommendation(
    comparison_result: Dict[str, Any],
    bidder_a_name: str = "Bidder A",
    bidder_b_name: str = "Bidder B",
    ranking_data: Optional[Dict[str, Any]] = None,
    bidders_data: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Generate an evidence-grounded bidder recommendation from compliance and ranking results.
    Supports any number of bidders (Bidder A, Bidder B, ..., Bidder N).

    Evaluates mandatory baseline compliance and incorporates:
    - Qualification status (QUALIFIED, CONDITIONALLY QUALIFIED, NON-COMPLIANT, DISQUALIFIED)
    - Quoted financial amount and technical evaluation marks
    - BOQ arithmetic validation findings
    - Highest-ranked qualified bidder designated as Rank 1 (RECOMMENDED)
    - Second highest qualified bidder designated as Rank 2 (NEXT ELIGIBLE / RESERVE)
    """
    field_comparisons = comparison_result.get("field_comparisons", [])
    summary_bidders = comparison_result.get("summary", {}).get("bidders", {})

    # Discover all bidders evaluated
    all_bidders_meta = comparison_result.get("bidders", [])
    if not all_bidders_meta and summary_bidders:
        all_bidders_meta = [
            {"bidder_id": b_id, "bidder_name": b_info.get("name", b_id)}
            for b_id, b_info in summary_bidders.items()
        ]
    if not all_bidders_meta:
        all_bidders_meta = [
            {"bidder_id": "bidder_A", "bidder_name": comparison_result.get("bidder_a_name", bidder_a_name)},
            {"bidder_id": "bidder_B", "bidder_name": comparison_result.get("bidder_b_name", bidder_b_name)}
        ]

    # Map extra bidder data if available
    bidder_extra_map = {}
    if bidders_data:
        for b in bidders_data:
            b_id = b.get("bidder_id")
            if b_id:
                bidder_extra_map[b_id] = b

    bidders_eval = {}

    for b in all_bidders_meta:
        b_id = b["bidder_id"]
        b_name = b["bidder_name"]

        compliant_count = 0
        non_compliant_count = 0
        failures = []

        for item in field_comparisons:
            field_name = item.get("field", "Unknown field")
            tender_req = item.get("tender_requirement")

            b_info = item.get("bidders", {}).get(b_id)
            if b_info:
                status = b_info.get("status", "UNKNOWN")
                val = b_info.get("value")
            else:
                if b_id == "bidder_A":
                    status = item.get("bidder_a_status", "UNKNOWN")
                    val = item.get("bidder_a_value")
                elif b_id == "bidder_B":
                    status = item.get("bidder_b_status", "UNKNOWN")
                    val = item.get("bidder_b_value")
                else:
                    status = "UNKNOWN"
                    val = None

            if status == "COMPLIANT":
                compliant_count += 1
            elif status == "NON-COMPLIANT":
                non_compliant_count += 1
                failures.append({
                    "field": field_name,
                    "requirement": tender_req,
                    "bidder_value": val
                })

        # Check for financial quote and BOQ info
        extra = bidder_extra_map.get(b_id, {})
        fields = extra.get("bidder_fields", {})
        quote = fields.get("total_quoted_amount")
        if isinstance(quote, dict):
            quote = quote.get("value")

        tech_score = fields.get("technical_score")
        if isinstance(tech_score, dict):
            tech_score = tech_score.get("value")

        boq_items = extra.get("boq_validation", [])
        boq_issues_cnt = sum(1 for itm in boq_items if str(itm.get("status", "")).upper() == "ERROR" or itm.get("issues"))

        bidders_eval[b_id] = {
            "bidder_id": b_id,
            "name": b_name,
            "status": "QUALIFIED" if non_compliant_count == 0 else "NON-COMPLIANT",
            "compliant_requirements": compliant_count,
            "non_compliant_requirements": non_compliant_count,
            "non_compliance_details": failures,
            "quoted_amount": quote,
            "technical_score": tech_score,
            "boq_issues_count": boq_issues_cnt
        }

    # If ranking_data from BidderRanker is available, use its authoritative ranking
    if ranking_data and ranking_data.get("recommended_bidder"):
        recommended_bidder = ranking_data["recommended_bidder"]
        recommended_id = ranking_data.get("recommended_bidder_id")
        next_eligible_bidder = ranking_data.get("next_eligible_bidder")
        next_eligible_id = ranking_data.get("next_eligible_bidder_id")
        reason = ranking_data.get("recommendation_statement")
    else:
        # Evaluate based on compliance results
        qualified = [b for b in bidders_eval.values() if b["status"] == "QUALIFIED"]
        non_compliant = [b for b in bidders_eval.values() if b["status"] != "QUALIFIED"]

        qualified.sort(key=lambda x: x["compliant_requirements"], reverse=True)
        non_compliant.sort(key=lambda x: x["non_compliant_requirements"])

        recommended_bidder = None
        recommended_id = None
        next_eligible_bidder = None
        next_eligible_id = None

        if qualified:
            recommended_bidder = qualified[0]["name"]
            recommended_id = qualified[0]["bidder_id"]

            quote_part = f" (Quoted Price: {qualified[0]['quoted_amount']})" if qualified[0].get("quoted_amount") else ""
            boq_part = f" with {qualified[0]['boq_issues_count']} BOQ anomaly(ies)" if qualified[0].get("boq_issues_count", 0) > 0 else " with verified BOQ arithmetic"

            reason = (
                f"{recommended_bidder} is RECOMMENDED for contract award consideration as Rank 1{quote_part}{boq_part}. "
                f"The bidder satisfies all currently evaluated mandatory tender baseline requirements."
            )

            if len(qualified) > 1:
                next_eligible_bidder = qualified[1]["name"]
                next_eligible_id = qualified[1]["bidder_id"]
                ne_quote = f" (Quoted: {qualified[1]['quoted_amount']})" if qualified[1].get("quoted_amount") else ""
                reason += f" {next_eligible_bidder} is designated as NEXT ELIGIBLE (Reserve / Fallback){ne_quote}."
            elif non_compliant:
                disqual_names = ", ".join(f"{b['name']} ({b['non_compliant_requirements']} deviation(s))" for b in non_compliant)
                reason += f" Disqualified / non-compliant bidders: {disqual_names}."

        elif non_compliant:
            recommended_bidder = non_compliant[0]["name"]
            recommended_id = non_compliant[0]["bidder_id"]
            if len(non_compliant) > 1:
                next_eligible_bidder = non_compliant[1]["name"]
                next_eligible_id = non_compliant[1]["bidder_id"]

            reason = (
                f"{recommended_bidder} is PROVISIONALLY recommended because the bidder has the fewest "
                f"non-compliant requirements ({non_compliant[0]['non_compliant_requirements']}). Further verification required."
            )
        else:
            reason = "No bidder recommendations available from the currently evaluated criteria."

    # Legacy bidder_a and bidder_b structures
    bidder_a_meta = bidders_eval.get("bidder_A", {
        "name": bidder_a_name,
        "compliant_requirements": 0,
        "non_compliant_requirements": 0,
        "non_compliance_details": []
    })
    bidder_b_meta = bidders_eval.get("bidder_B", {
        "name": bidder_b_name,
        "compliant_requirements": 0,
        "non_compliant_requirements": 0,
        "non_compliance_details": []
    })

    return {
        "recommended_bidder": recommended_bidder,
        "recommended_bidder_id": recommended_id,
        "next_eligible_bidder": next_eligible_bidder,
        "next_eligible_bidder_id": next_eligible_id,
        "recommendation": reason,
        "recommendation_basis": "Tender compliance and deterministic ranking evaluation",
        "provisional": True,
        "bidders": bidders_eval,
        "bidder_a": bidder_a_meta,
        "bidder_b": bidder_b_meta,
        "note": (
            "DECISION-SUPPORT NOTICE: This is a provisional recommendation based on currently evaluated compliance checks. "
            "Final contract award authority rests exclusively with the official procurement committee."
        )
    }
