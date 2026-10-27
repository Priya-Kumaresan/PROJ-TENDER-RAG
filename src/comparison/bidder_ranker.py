"""
Bidder Ranker Module (Priorities 6, 7, 8, 9, 10, 11, 12, 13)
Deterministic multi-bidder qualification, scoring, ranking, fallback recommendation,
and recommendation audit trail for tender evaluation.
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.comparison.bid_comparator import (
    compare_currency,
    compare_duration,
    compare_percentage,
    normalize_currency,
    normalize_duration,
    normalize_percentage,
)


def _extract_val(field_obj: Any) -> Any:
    """Helper to extract primitive value from either a dict or direct scalar."""
    if isinstance(field_obj, dict):
        return field_obj.get("value")
    return field_obj


class BidderRanker:
    """
    Evaluates mandatory qualification criteria, calculates technical and financial
    scores using tender-defined weightages, ranks all qualified bidders, manages fallback
    recommendations, and maintains an immutable audit trail.
    """

    DEFAULT_TECHNICAL_WEIGHT = 0.80
    DEFAULT_FINANCIAL_WEIGHT = 0.20
    DEFAULT_MIN_TECHNICAL_SCORE = 70.0

    def __init__(
        self,
        technical_weight: Optional[float] = None,
        financial_weight: Optional[float] = None,
        min_technical_score: Optional[float] = None,
    ):
        self.custom_tech_weight = technical_weight
        self.custom_fin_weight = financial_weight
        self.custom_min_tech_score = min_technical_score

    def _resolve_evaluation_weights(
        self, tender_fields: Dict[str, Any]
    ) -> Tuple[float, float, float]:
        """
        Dynamically extracts technical weight, financial weight, and minimum technical score
        from tender metadata, falling back to defaults if unspecified.
        """
        # 1. Technical Weight
        tech_w = self.custom_tech_weight
        if tech_w is None:
            raw_val = _extract_val(tender_fields.get("technical_weightage"))
            norm = normalize_percentage(raw_val)
            if norm is not None and norm > 0:
                tech_w = norm / 100.0 if norm > 1.0 else norm
            else:
                tech_w = self.DEFAULT_TECHNICAL_WEIGHT

        # 2. Financial Weight
        fin_w = self.custom_fin_weight
        if fin_w is None:
            raw_val = _extract_val(tender_fields.get("financial_weightage"))
            norm = normalize_percentage(raw_val)
            if norm is not None and norm > 0:
                fin_w = norm / 100.0 if norm > 1.0 else norm
            else:
                fin_w = self.DEFAULT_FINANCIAL_WEIGHT

        # Normalize weights so they sum to 1.0
        total_w = tech_w + fin_w
        if total_w > 0:
            tech_w = tech_w / total_w
            fin_w = fin_w / total_w
        else:
            tech_w, fin_w = self.DEFAULT_TECHNICAL_WEIGHT, self.DEFAULT_FINANCIAL_WEIGHT

        # 3. Minimum Technical Score Threshold
        min_score = self.custom_min_tech_score
        if min_score is None:
            raw_val = _extract_val(tender_fields.get("min_technical_score"))
            if raw_val is not None:
                try:
                    cleaned = re.sub(r"[^\d.]", "", str(raw_val))
                    min_score = float(cleaned)
                except ValueError:
                    min_score = self.DEFAULT_MIN_TECHNICAL_SCORE
            else:
                min_score = self.DEFAULT_MIN_TECHNICAL_SCORE

        return round(tech_w, 4), round(fin_w, 4), min_score

    def evaluate_bidder_qualification(
        self,
        bidder: Dict[str, Any],
        tender_fields: Dict[str, Any],
        min_technical_score: float,
        boq_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Performs mandatory statutory and tender compliance checks for a single bidder.
        Assigns status: QUALIFIED, CONDITIONALLY QUALIFIED, NON-COMPLIANT, or DISQUALIFIED.
        """
        bidder_id = bidder.get("bidder_id", "unknown_bidder")
        bidder_name = bidder.get("bidder_name", bidder_id)
        b_fields = bidder.get("bidder_fields", {})

        mandatory_checks = []
        disqualifications = []
        conditions = []

        # 1. Completion Period Check (Mandatory: bidder <= tender)
        tender_completion = _extract_val(tender_fields.get("completion_period"))
        bidder_completion = _extract_val(b_fields.get("completion_period"))
        if tender_completion and bidder_completion:
            status, msg = compare_duration(tender_completion, bidder_completion)
            passed = status == "COMPLIANT"
            mandatory_checks.append({
                "check_name": "Completion Period Compliance",
                "tender_requirement": tender_completion,
                "bidder_submission": bidder_completion,
                "status": status,
                "passed": passed,
                "message": msg,
            })
            if not passed:
                disqualifications.append(
                    f"Completion period '{bidder_completion}' exceeds tender requirement '{tender_completion}'."
                )

        # 2. EMD / Bid Security Check (Mandatory: bidder >= tender)
        tender_emd = _extract_val(tender_fields.get("emd"))
        bidder_emd = _extract_val(b_fields.get("emd_submitted")) or _extract_val(b_fields.get("emd"))
        if tender_emd:
            if not bidder_emd:
                mandatory_checks.append({
                    "check_name": "EMD Submission",
                    "tender_requirement": tender_emd,
                    "bidder_submission": "Not submitted / missing",
                    "status": "NON-COMPLIANT",
                    "passed": False,
                    "message": "EMD document or proof of payment missing.",
                })
                disqualifications.append("Mandatory EMD / Bid Security not submitted.")
            else:
                status, msg = compare_currency(tender_emd, bidder_emd, "EMD")
                passed = status == "COMPLIANT"
                mandatory_checks.append({
                    "check_name": "EMD Value Adequacy",
                    "tender_requirement": tender_emd,
                    "bidder_submission": bidder_emd,
                    "status": status,
                    "passed": passed,
                    "message": msg,
                })
                if not passed:
                    disqualifications.append(
                        f"Submitted EMD ({bidder_emd}) is less than required tender EMD ({tender_emd})."
                    )

        # 3. Performance Security Requirement (Mandatory commitment)
        tender_ps = _extract_val(tender_fields.get("performance_security"))
        bidder_ps = _extract_val(b_fields.get("performance_security"))
        if tender_ps and bidder_ps:
            status, msg = compare_percentage(tender_ps, bidder_ps, "Performance Security")
            passed = status == "COMPLIANT"
            mandatory_checks.append({
                "check_name": "Performance Security Commitment",
                "tender_requirement": tender_ps,
                "bidder_submission": bidder_ps,
                "status": status,
                "passed": passed,
                "message": msg,
            })
            if not passed:
                conditions.append(
                    f"Performance security offered ({bidder_ps}) is below tender requirement ({tender_ps})."
                )

        # 4. Minimum Technical Score Threshold
        raw_tech_score = _extract_val(b_fields.get("technical_score"))
        tech_score = None
        if raw_tech_score is not None:
            try:
                cleaned_tech = re.sub(r"[^\d.]", "", str(raw_tech_score))
                tech_score = float(cleaned_tech)
            except ValueError:
                tech_score = None

        if tech_score is not None:
            passed = tech_score >= min_technical_score
            mandatory_checks.append({
                "check_name": "Minimum Technical Score Threshold",
                "tender_requirement": f"Minimum {min_technical_score} marks",
                "bidder_submission": f"{tech_score} marks",
                "status": "COMPLIANT" if passed else "NON-COMPLIANT",
                "passed": passed,
                "message": (
                    f"Achieved {tech_score} marks (cutoff: {min_technical_score})."
                    if passed
                    else f"Failed technical cutoff: {tech_score} marks < {min_technical_score} required."
                ),
            })
            if not passed:
                disqualifications.append(
                    f"Technical score of {tech_score} is below the mandatory minimum threshold of {min_technical_score}."
                )
        else:
            # If technical score is missing from documents
            mandatory_checks.append({
                "check_name": "Technical Evaluation Score",
                "tender_requirement": f"Minimum {min_technical_score} marks",
                "bidder_submission": "Pending / Not extracted",
                "status": "UNKNOWN",
                "passed": True,  # Don't disqualify yet if not evaluated
                "message": "Technical score not present in submission metadata.",
            })

        # 5. BOQ Material Integrity Checks
        boq_issues = []
        if boq_data:
            summary = boq_data.get("summary", {})
            fatal_errors = summary.get("fatal_anomalies", 0)
            unquoted_items = summary.get("missing_rates", 0)
            if fatal_errors > 0 or unquoted_items > 0:
                boq_issues.append(
                    f"BOQ contains {unquoted_items} unquoted item(s) and {fatal_errors} critical error(s)."
                )

        # Determine Final Qualification Status
        if disqualifications:
            status = "DISQUALIFIED"
            summary_reason = "; ".join(disqualifications)
        elif conditions:
            status = "CONDITIONALLY QUALIFIED"
            summary_reason = "; ".join(conditions)
        else:
            status = "QUALIFIED"
            summary_reason = "Satisfies all evaluated mandatory tender criteria."

        return {
            "bidder_id": bidder_id,
            "bidder_name": bidder_name,
            "qualification_status": status,
            "is_qualified": status in ("QUALIFIED", "CONDITIONALLY QUALIFIED"),
            "technical_score": tech_score,
            "mandatory_checks": mandatory_checks,
            "disqualifications": disqualifications,
            "conditions": conditions,
            "boq_issues": boq_issues,
            "qualification_reason": summary_reason,
        }

    def rank_bidders(
        self,
        tender_fields: Dict[str, Any],
        bidders_list: List[Dict[str, Any]],
        boq_evaluations: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Complete end-to-end evaluation:
        1. Evaluates qualification for all bidders.
        2. Calculates technical score, financial score, and overall score for qualified bidders.
        3. Ranks qualified bidders descending by overall score.
        4. Designates Rank 1 (Recommended) and Rank 2 (Next Eligible / Reserve).
        5. Isolates disqualified bidders with detailed justification.
        6. Generates full audit trail.
        """
        tech_weight, fin_weight, min_tech_score = self._resolve_evaluation_weights(tender_fields)

        boq_evaluations = boq_evaluations or {}

        # 1. Qualification Evaluation for all bidders
        evaluations = []
        for bidder in bidders_list:
            b_id = bidder.get("bidder_id", "")
            b_boq = boq_evaluations.get(b_id)
            eval_res = self.evaluate_bidder_qualification(
                bidder=bidder,
                tender_fields=tender_fields,
                min_technical_score=min_tech_score,
                boq_data=b_boq,
            )
            # Attach quoted amount
            b_fields = bidder.get("bidder_fields", {})
            raw_quote = _extract_val(b_fields.get("total_quoted_amount"))
            eval_res["raw_quoted_amount"] = raw_quote
            eval_res["normalized_quoted_amount"] = normalize_currency(raw_quote)
            eval_res["completion_period"] = _extract_val(b_fields.get("completion_period"))
            eval_res["emd_submitted"] = _extract_val(b_fields.get("emd_submitted"))
            eval_res["performance_security"] = _extract_val(b_fields.get("performance_security"))
            evaluations.append(eval_res)

        # 2. Filter Qualified vs Disqualified
        qualified_bidders = [b for b in evaluations if b["is_qualified"]]
        disqualified_bidders = [b for b in evaluations if not b["is_qualified"]]

        # 3. Find Lowest Qualified Bid (L1) among QUALIFIED bidders only
        valid_quotes = [
            b["normalized_quoted_amount"]
            for b in qualified_bidders
            if b["normalized_quoted_amount"] is not None and b["normalized_quoted_amount"] > 0
        ]
        lowest_qualified_bid = min(valid_quotes) if valid_quotes else None

        # 4. Compute Financial and Overall Composite Scores for Qualified Bidders
        for b in qualified_bidders:
            # Technical Score (Normalized to 100 max)
            t_score = b["technical_score"] if b["technical_score"] is not None else 75.0
            b["technical_score_normalized"] = round(float(t_score), 2)

            # Financial Score Formula: (Lowest Qualified Bid / Bidder Bid) * 100
            quote = b["normalized_quoted_amount"]
            if quote and quote > 0 and lowest_qualified_bid and lowest_qualified_bid > 0:
                f_score = (lowest_qualified_bid / quote) * 100.0
                b["financial_score"] = round(f_score, 2)
            else:
                b["financial_score"] = 0.0

            # Composite Overall Score: (Technical * Weight) + (Financial * Weight)
            overall = (b["technical_score_normalized"] * tech_weight) + (b["financial_score"] * fin_weight)
            b["overall_score"] = round(overall, 2)

        # 5. Handle Disqualified Bidders (No active ranking or overall score)
        for b in disqualified_bidders:
            b["technical_score_normalized"] = b["technical_score"]
            b["financial_score"] = None
            b["overall_score"] = None
            b["rank"] = None

        # 6. Rank Qualified Bidders Descending by Overall Score
        # Tie-breaker: higher technical score wins
        qualified_bidders.sort(
            key=lambda x: (x["overall_score"] or 0.0, x["technical_score_normalized"] or 0.0),
            reverse=True,
        )

        for idx, b in enumerate(qualified_bidders, start=1):
            b["rank"] = idx

        # Combine for full tabular view: Qualified first in rank order, then Disqualified
        all_ranked_table = []
        for b in qualified_bidders:
            all_ranked_table.append({
                "rank": b["rank"],
                "bidder_id": b["bidder_id"],
                "bidder_name": b["bidder_name"],
                "qualification": b["qualification_status"],
                "qualification_status": b["qualification_status"],
                "technical_score": b["technical_score_normalized"],
                "quoted_amount": b["raw_quoted_amount"],
                "financial_score": b["financial_score"],
                "overall_score": b["overall_score"],
                "status_reason": b["qualification_reason"],
            })

        for b in disqualified_bidders:
            all_ranked_table.append({
                "rank": "-",
                "bidder_id": b["bidder_id"],
                "bidder_name": b["bidder_name"],
                "qualification": b["qualification_status"],
                "qualification_status": b["qualification_status"],
                "technical_score": b["technical_score_normalized"],
                "quoted_amount": b["raw_quoted_amount"],
                "financial_score": "N/A (Disqualified)",
                "overall_score": "N/A",
                "status_reason": b["qualification_reason"],
            })

        # 7. Recommendations
        recommended = None
        next_eligible = None

        if qualified_bidders:
            recommended = qualified_bidders[0]
            rec_id = recommended["bidder_id"]
            rec_name = recommended["bidder_name"]
            rec_score = recommended["overall_score"]
            rec_tech = recommended["technical_score_normalized"]
            rec_fin = recommended["financial_score"]
            rec_quote = recommended["raw_quoted_amount"] or "N/A"

            recommendation_text = (
                f"{rec_name} is RECOMMENDED for contract award consideration as Rank 1 "
                f"with the highest overall score of {rec_score}/100 "
                f"(Technical Score: {rec_tech}, Financial Score: {rec_fin}, Quoted Amount: {rec_quote}). "
                f"The bidder satisfies all mandatory tender qualification criteria."
            )

            if len(qualified_bidders) > 1:
                next_eligible = qualified_bidders[1]
                ne_name = next_eligible["bidder_name"]
                ne_score = next_eligible["overall_score"]
                ne_quote = next_eligible["raw_quoted_amount"] or "N/A"
                next_eligible_text = (
                    f"{ne_name} is designated as NEXT ELIGIBLE (Reserve / Fallback) as Rank 2 "
                    f"with an overall score of {ne_score}/100 (Quoted Amount: {ne_quote})."
                )
            else:
                next_eligible_text = "No secondary qualified bidder available as reserve."
        else:
            recommendation_text = (
                "NO BIDDER RECOMMENDED: None of the submitted bids satisfied all mandatory tender criteria. "
                "Retendering or committee review recommended."
            )
            next_eligible_text = "N/A"

        # 8. Recommendation Audit Trail
        timestamp_str = datetime.now().isoformat()
        audit_entry = {
            "timestamp": timestamp_str,
            "action": "INITIAL_EVALUATION_AND_RANKING",
            "parameters": {
                "technical_weight": tech_weight,
                "financial_weight": fin_weight,
                "min_technical_score": min_tech_score,
                "lowest_qualified_bid_l1": lowest_qualified_bid,
            },
            "recommended_bidder": recommended["bidder_name"] if recommended else None,
            "next_eligible_bidder": next_eligible["bidder_name"] if next_eligible else None,
            "qualified_count": len(qualified_bidders),
            "disqualified_count": len(disqualified_bidders),
            "notes": "Automated deterministic qualification and ranking completed.",
        }

        return {
            "evaluation_parameters": {
                "technical_weight": tech_weight,
                "financial_weight": fin_weight,
                "technical_weight_percent": f"{tech_weight * 100:g}%",
                "financial_weight_percent": f"{fin_weight * 100:g}%",
                "min_technical_score": min_tech_score,
                "lowest_qualified_bid_l1": lowest_qualified_bid,
            },
            "recommended_bidder": recommended["bidder_name"] if recommended else None,
            "recommended_bidder_id": recommended["bidder_id"] if recommended else None,
            "recommended_bidder_data": recommended,
            "recommendation_statement": recommendation_text,
            "next_eligible_bidder": next_eligible["bidder_name"] if next_eligible else None,
            "next_eligible_bidder_id": next_eligible["bidder_id"] if next_eligible else None,
            "next_eligible_data": next_eligible,
            "next_eligible_statement": next_eligible_text,
            "ranking_table": all_ranked_table,
            "qualified_bidders": qualified_bidders,
            "disqualified_bidders": disqualified_bidders,
            "audit_trail": [audit_entry],
            "legal_disclaimer": (
                "DECISION-SUPPORT NOTICE: This automated evaluation provides transparent decision-support "
                "based strictly on deterministic tender rules and retrieved documents. Final contract award "
                "authority rests solely with the competent procurement authority."
            ),
        }

    def simulate_fallback(
        self,
        ranking_result: Dict[str, Any],
        disqualified_bidder_id: str,
        disqualification_reason: str,
    ) -> Dict[str, Any]:
        """
        Priority 12: Recalculate ranking if the first-ranked (or any active) bidder is disqualified
        or withdraws during post-qualification due diligence.
        - Updates lowest qualified bid if the disqualified bidder was L1.
        - Recalculates financial and composite overall scores.
        - Reranks remaining qualified bidders.
        - Appends an immutable audit event to audit_trail.
        """
        qualified = ranking_result.get("qualified_bidders", [])
        disqualified = ranking_result.get("disqualified_bidders", [])
        params = ranking_result.get("evaluation_parameters", {})
        audit_trail = list(ranking_result.get("audit_trail", []))

        tech_w = params.get("technical_weight", self.DEFAULT_TECHNICAL_WEIGHT)
        fin_w = params.get("financial_weight", self.DEFAULT_FINANCIAL_WEIGHT)

        # Locate bidder to disqualify
        target_bidder = None
        remaining_qualified = []

        for b in qualified:
            if b["bidder_id"] == disqualified_bidder_id:
                target_bidder = dict(b)
            else:
                remaining_qualified.append(dict(b))

        if not target_bidder:
            # Bidder not in qualified list; nothing to recalculate
            return ranking_result

        # Update target bidder to DISQUALIFIED
        target_bidder["is_qualified"] = False
        target_bidder["qualification_status"] = "DISQUALIFIED"
        target_bidder["qualification_reason"] = (
            f"Post-qualification disqualification / withdrawal: {disqualification_reason}"
        )
        target_bidder["disqualifications"].append(disqualification_reason)
        target_bidder["financial_score"] = None
        target_bidder["overall_score"] = None
        target_bidder["rank"] = None
        disqualified.append(target_bidder)

        # Recalculate Lowest Qualified Bid (L1)
        valid_quotes = [
            b["normalized_quoted_amount"]
            for b in remaining_qualified
            if b.get("normalized_quoted_amount") is not None and b.get("normalized_quoted_amount", 0) > 0
        ]
        new_l1 = min(valid_quotes) if valid_quotes else None
        params["lowest_qualified_bid_l1"] = new_l1

        # Recalculate Financial & Overall Scores for remaining qualified bidders
        for b in remaining_qualified:
            t_score = b.get("technical_score_normalized") or 75.0
            quote = b.get("normalized_quoted_amount")
            if quote and quote > 0 and new_l1 and new_l1 > 0:
                b["financial_score"] = round((new_l1 / quote) * 100.0, 2)
            else:
                b["financial_score"] = 0.0

            overall = (t_score * tech_w) + (b["financial_score"] * fin_w)
            b["overall_score"] = round(overall, 2)

        # Rerank remaining qualified bidders
        remaining_qualified.sort(
            key=lambda x: (x["overall_score"] or 0.0, x.get("technical_score_normalized") or 0.0),
            reverse=True,
        )

        for idx, b in enumerate(remaining_qualified, start=1):
            b["rank"] = idx

        # Rebuild table
        new_table = []
        for b in remaining_qualified:
            new_table.append({
                "rank": b["rank"],
                "bidder_id": b["bidder_id"],
                "bidder_name": b["bidder_name"],
                "qualification": b["qualification_status"],
                "qualification_status": b["qualification_status"],
                "technical_score": b["technical_score_normalized"],
                "quoted_amount": b["raw_quoted_amount"],
                "financial_score": b["financial_score"],
                "overall_score": b["overall_score"],
                "status_reason": b["qualification_reason"],
            })

        for b in disqualified:
            new_table.append({
                "rank": "-",
                "bidder_id": b["bidder_id"],
                "bidder_name": b["bidder_name"],
                "qualification": b["qualification_status"],
                "qualification_status": b["qualification_status"],
                "technical_score": b.get("technical_score_normalized"),
                "quoted_amount": b.get("raw_quoted_amount"),
                "financial_score": "N/A (Disqualified)",
                "overall_score": "N/A",
                "status_reason": b["qualification_reason"],
            })

        # Update Recommendations
        new_rec = remaining_qualified[0] if remaining_qualified else None
        new_next = remaining_qualified[1] if len(remaining_qualified) > 1 else None

        if new_rec:
            new_rec_text = (
                f"FALLBACK RECOMMENDATION: Following the disqualification of {target_bidder['bidder_name']}, "
                f"{new_rec['bidder_name']} is now RECOMMENDED as Rank 1 with an updated overall score of "
                f"{new_rec['overall_score']}/100 (Technical: {new_rec['technical_score_normalized']}, "
                f"Financial: {new_rec['financial_score']})."
            )
            new_next_text = (
                f"{new_next['bidder_name']} is designated as the fallback reserve bidder (Rank 2) with "
                f"an overall score of {new_next['overall_score']}/100."
                if new_next
                else "No further qualified reserve bidders available."
            )
        else:
            new_rec_text = "NO QUALIFIED BIDDERS REMAIN: All submitted bids have been disqualified."
            new_next_text = "N/A"

        # Record Audit Event
        audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "action": "FALLBACK_RECALCULATION",
            "disqualified_bidder": target_bidder["bidder_name"],
            "disqualification_reason": disqualification_reason,
            "new_recommended_bidder": new_rec["bidder_name"] if new_rec else None,
            "new_next_eligible_bidder": new_next["bidder_name"] if new_next else None,
            "new_lowest_qualified_bid_l1": new_l1,
            "notes": f"Triggered fallback: {target_bidder['bidder_name']} disqualified. Ranking recalculated.",
        })

        return {
            "evaluation_parameters": params,
            "recommended_bidder": new_rec["bidder_name"] if new_rec else None,
            "recommended_bidder_id": new_rec["bidder_id"] if new_rec else None,
            "recommended_bidder_data": new_rec,
            "recommendation_statement": new_rec_text,
            "next_eligible_bidder": new_next["bidder_name"] if new_next else None,
            "next_eligible_bidder_id": new_next["bidder_id"] if new_next else None,
            "next_eligible_data": new_next,
            "next_eligible_statement": new_next_text,
            "ranking_table": new_table,
            "qualified_bidders": remaining_qualified,
            "disqualified_bidders": disqualified,
            "audit_trail": audit_trail,
            "legal_disclaimer": ranking_result.get("legal_disclaimer"),
        }


def save_ranking_results(ranking_result: Dict[str, Any], output_path: str) -> None:
    """Save structured ranking dictionary as JSON to disk."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(ranking_result, f, indent=2, ensure_ascii=False)


def load_ranking_results(file_path: str) -> Optional[Dict[str, Any]]:
    """Load structured ranking dictionary from JSON file."""
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
