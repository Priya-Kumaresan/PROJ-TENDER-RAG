import re


def normalize_percentage(value):
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value)

    match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if match:
        return float(match.group(1))

    match = re.search(r"(\d+(?:\.\d+)?)\s*percent", text, re.IGNORECASE)
    if match:
        return float(match.group(1))

    return None


def normalize_currency(value):
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().lower()

    # Check for Indian crore / cr notation (1 crore = 10,000,000)
    crore_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:crores?|cr)\b", text)
    if crore_match:
        try:
            return float(crore_match.group(1)) * 10000000.0
        except ValueError:
            pass

    # Check for Indian lakh / lac notation (1 lakh = 100,000)
    lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakhs?|lacs?|lac)\b", text)
    if lakh_match:
        try:
            return float(lakh_match.group(1)) * 100000.0
        except ValueError:
            pass

    text = re.sub(r"(?i)(inr|rs\.?|₹|\$|€|£)", "", text)
    text = text.replace(",", "").replace("/-", "").strip()

    try:
        return float(text)
    except ValueError:
        return None


def normalize_duration(value):
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).lower()

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:\([a-zA-Z]+\))?\s*(days?|weeks?|months?|years?)",
        text
    )

    if not match:
        return None

    number = float(match.group(1))
    unit = match.group(2)

    if unit.startswith("day"):
        days = number
    elif unit.startswith("week"):
        days = number * 7
    elif unit.startswith("month"):
        days = number * 30
    else:
        days = number * 365

    return days


def compare_duration(tender_value, bidder_value):
    tender_days = normalize_duration(tender_value)
    bidder_days = normalize_duration(bidder_value)

    if tender_days is None or bidder_days is None:
        return "UNKNOWN", "Unable to compare completion periods."

    if bidder_days <= tender_days:
        return "COMPLIANT", "Bidder meets the tender completion requirement."

    difference = bidder_days - tender_days
    return (
        "NON-COMPLIANT",
        f"Bidder completion period exceeds the tender requirement by approximately {difference:g} days."
    )


def compare_proposal_validity(tender_value, bidder_value):
    tender_days = normalize_duration(tender_value)
    bidder_days = normalize_duration(bidder_value)

    if tender_days is None or bidder_days is None:
        return "UNKNOWN", "Unable to compare proposal validity."

    if bidder_days >= tender_days:
        return "COMPLIANT", f"Bidder proposal validity satisfies tender requirement ({tender_value})."

    return "NON-COMPLIANT", f"Bidder proposal validity ({bidder_value}) is less than tender requirement ({tender_value})."


def compare_percentage(tender_value, bidder_value, field_name):
    tender_percentage = normalize_percentage(tender_value)
    bidder_percentage = normalize_percentage(bidder_value)

    if tender_percentage is None or bidder_percentage is None:
        return "UNKNOWN", f"Unable to compare {field_name}."

    if bidder_percentage >= tender_percentage:
        return "COMPLIANT", f"Bidder meets or exceeds the tender {field_name} requirement."

    return "NON-COMPLIANT", f"Bidder's {field_name} is below the tender requirement."


def compare_currency(tender_value, bidder_value, field_name):
    tender_amount = normalize_currency(tender_value)
    bidder_amount = normalize_currency(bidder_value)

    if tender_amount is None or bidder_amount is None:
        return "UNKNOWN", f"Unable to compare {field_name}."

    if bidder_amount >= tender_amount:
        return "COMPLIANT", f"Bidder meets or exceeds the tender {field_name} requirement."

    return "NON-COMPLIANT", f"Bidder's {field_name} is below the tender requirement."


def compare_technical_score(tender_min, bidder_score):
    if tender_min is None or bidder_score is None:
        return "UNKNOWN", "Technical score not specified."

    try:
        t_val = float(re.sub(r"[^\d.]", "", str(tender_min)))
        b_val = float(re.sub(r"[^\d.]", "", str(bidder_score)))
    except (ValueError, TypeError):
        return "UNKNOWN", "Unable to parse technical score."

    if b_val >= t_val:
        return "COMPLIANT", f"Achieved {b_val} marks (meets minimum qualifying score of {t_val} marks)."

    return "NON-COMPLIANT", f"Technical score {b_val} marks is below mandatory cutoff of {t_val} marks."


def compare_registration(bidder_val):
    if bidder_val and str(bidder_val).strip().lower() not in ("none", "unknown", ""):
        return "COMPLIANT", f"Company registration / CIN submitted: {bidder_val}"
    return "UNKNOWN", "Registration document status not recorded."


def compare_boq_integrity(boq_items):
    if not boq_items or not isinstance(boq_items, list):
        return "COMPLIANT", "BOQ format accepted."

    fatal_errors = sum(1 for itm in boq_items if str(itm.get("status", "")).upper() == "ERROR")
    missing_rates = sum(1 for itm in boq_items if "Missing Rate" in itm.get("issues", []))

    if fatal_errors > 0 or missing_rates > 0:
        return "NON-COMPLIANT", f"BOQ has {missing_rates} unquoted item(s) and {fatal_errors} arithmetic error(s)."

    return "COMPLIANT", "BOQ arithmetic and item values validated with 0 critical issues."


def _extract_field_val(fields_dict, key):
    val = fields_dict.get(key)
    if isinstance(val, dict):
        return val.get("value")
    return val


def run_multi_bid_comparison(tender_fields, bidders_list):
    """
    Compare any number of bidders against the single common tender baseline.
    Evaluates:
    1. Completion Period
    2. Performance Security
    3. EMD / Bid Security
    4. Proposal Validity
    5. Technical Score Cutoff (if tender defines minimum)
    6. Company Registration / CIN
    7. BOQ Integrity & Arithmetic Checks
    """
    comparisons = []

    tender_completion = _extract_field_val(tender_fields, "completion_period")
    tender_security = _extract_field_val(tender_fields, "performance_security")
    tender_emd = _extract_field_val(tender_fields, "emd")
    tender_validity = _extract_field_val(tender_fields, "proposal_validity")
    tender_min_tech = _extract_field_val(tender_fields, "min_technical_score")

    b_a_id = bidders_list[0].get("bidder_id") if len(bidders_list) > 0 else "bidder_A"
    b_b_id = bidders_list[1].get("bidder_id") if len(bidders_list) > 1 else "bidder_B"

    # 1. Completion Period
    bidders_completion = {}
    for b in bidders_list:
        b_id = b.get("bidder_id", "bidder")
        b_fields = b.get("bidder_fields", {})
        val = _extract_field_val(b_fields, "completion_period")
        status, msg = compare_duration(tender_completion, val)
        bidders_completion[b_id] = {
            "value": val,
            "status": status,
            "message": msg
        }

    comparisons.append({
        "field": "completion_period",
        "tender_requirement": tender_completion,
        "bidder_a_value": bidders_completion.get(b_a_id, {}).get("value"),
        "bidder_a_status": bidders_completion.get(b_a_id, {}).get("status", "UNKNOWN"),
        "bidder_a_message": bidders_completion.get(b_a_id, {}).get("message", ""),
        "bidder_b_value": bidders_completion.get(b_b_id, {}).get("value"),
        "bidder_b_status": bidders_completion.get(b_b_id, {}).get("status", "UNKNOWN"),
        "bidder_b_message": bidders_completion.get(b_b_id, {}).get("message", ""),
        "bidders": bidders_completion
    })

    # 2. Performance Security
    bidders_security = {}
    for b in bidders_list:
        b_id = b.get("bidder_id", "bidder")
        b_fields = b.get("bidder_fields", {})
        val = _extract_field_val(b_fields, "performance_security")
        status, msg = compare_percentage(tender_security, val, "performance security")
        bidders_security[b_id] = {
            "value": val,
            "status": status,
            "message": msg
        }

    comparisons.append({
        "field": "performance_security",
        "tender_requirement": tender_security,
        "bidder_a_value": bidders_security.get(b_a_id, {}).get("value"),
        "bidder_a_status": bidders_security.get(b_a_id, {}).get("status", "UNKNOWN"),
        "bidder_a_message": bidders_security.get(b_a_id, {}).get("message", ""),
        "bidder_b_value": bidders_security.get(b_b_id, {}).get("value"),
        "bidder_b_status": bidders_security.get(b_b_id, {}).get("status", "UNKNOWN"),
        "bidder_b_message": bidders_security.get(b_b_id, {}).get("message", ""),
        "bidders": bidders_security
    })

    # 3. EMD Requirement
    bidders_emd = {}
    for b in bidders_list:
        b_id = b.get("bidder_id", "bidder")
        b_fields = b.get("bidder_fields", {})
        val = _extract_field_val(b_fields, "emd_submitted") or _extract_field_val(b_fields, "emd")
        status, msg = compare_currency(tender_emd, val, "EMD")
        bidders_emd[b_id] = {
            "value": val,
            "status": status,
            "message": msg
        }

    comparisons.append({
        "field": "emd",
        "tender_requirement": tender_emd,
        "bidder_a_value": bidders_emd.get(b_a_id, {}).get("value"),
        "bidder_a_status": bidders_emd.get(b_a_id, {}).get("status", "UNKNOWN"),
        "bidder_a_message": bidders_emd.get(b_a_id, {}).get("message", ""),
        "bidder_b_value": bidders_emd.get(b_b_id, {}).get("value"),
        "bidder_b_status": bidders_emd.get(b_b_id, {}).get("status", "UNKNOWN"),
        "bidder_b_message": bidders_emd.get(b_b_id, {}).get("message", ""),
        "bidders": bidders_emd
    })

    # 4. Proposal Validity
    if tender_validity:
        bidders_validity = {}
        for b in bidders_list:
            b_id = b.get("bidder_id", "bidder")
            b_fields = b.get("bidder_fields", {})
            val = _extract_field_val(b_fields, "proposal_validity")
            status, msg = compare_proposal_validity(tender_validity, val)
            bidders_validity[b_id] = {
                "value": val,
                "status": status,
                "message": msg
            }

        comparisons.append({
            "field": "proposal_validity",
            "tender_requirement": tender_validity,
            "bidder_a_value": bidders_validity.get(b_a_id, {}).get("value"),
            "bidder_a_status": bidders_validity.get(b_a_id, {}).get("status", "UNKNOWN"),
            "bidder_a_message": bidders_validity.get(b_a_id, {}).get("message", ""),
            "bidder_b_value": bidders_validity.get(b_b_id, {}).get("value"),
            "bidder_b_status": bidders_validity.get(b_b_id, {}).get("status", "UNKNOWN"),
            "bidder_b_message": bidders_validity.get(b_b_id, {}).get("message", ""),
            "bidders": bidders_validity
        })

    # 5. Technical Score Cutoff (if tender specifies minimum)
    if tender_min_tech:
        bidders_tech = {}
        for b in bidders_list:
            b_id = b.get("bidder_id", "bidder")
            b_fields = b.get("bidder_fields", {})
            val = _extract_field_val(b_fields, "technical_score")
            status, msg = compare_technical_score(tender_min_tech, val)
            bidders_tech[b_id] = {
                "value": f"{val} marks" if val else None,
                "status": status,
                "message": msg
            }

        comparisons.append({
            "field": "minimum_technical_score",
            "tender_requirement": f"{tender_min_tech} marks",
            "bidder_a_value": bidders_tech.get(b_a_id, {}).get("value"),
            "bidder_a_status": bidders_tech.get(b_a_id, {}).get("status", "UNKNOWN"),
            "bidder_a_message": bidders_tech.get(b_a_id, {}).get("message", ""),
            "bidder_b_value": bidders_tech.get(b_b_id, {}).get("value"),
            "bidder_b_status": bidders_tech.get(b_b_id, {}).get("status", "UNKNOWN"),
            "bidder_b_message": bidders_tech.get(b_b_id, {}).get("message", ""),
            "bidders": bidders_tech
        })

    # 6. Company Registration / Mandatory Docs
    bidders_reg = {}
    for b in bidders_list:
        b_id = b.get("bidder_id", "bidder")
        b_fields = b.get("bidder_fields", {})
        val = _extract_field_val(b_fields, "registration_number")
        status, msg = compare_registration(val)
        bidders_reg[b_id] = {
            "value": val or "Submitted",
            "status": status,
            "message": msg
        }

    comparisons.append({
        "field": "registration_number",
        "tender_requirement": "Mandatory CIN / Registration",
        "bidder_a_value": bidders_reg.get(b_a_id, {}).get("value"),
        "bidder_a_status": bidders_reg.get(b_a_id, {}).get("status", "UNKNOWN"),
        "bidder_a_message": bidders_reg.get(b_a_id, {}).get("message", ""),
        "bidder_b_value": bidders_reg.get(b_b_id, {}).get("value"),
        "bidder_b_status": bidders_reg.get(b_b_id, {}).get("status", "UNKNOWN"),
        "bidder_b_message": bidders_reg.get(b_b_id, {}).get("message", ""),
        "bidders": bidders_reg
    })

    # 7. BOQ Integrity & Arithmetic Validation
    bidders_boq = {}
    for b in bidders_list:
        b_id = b.get("bidder_id", "bidder")
        b_boq_items = b.get("boq_validation", [])
        status, msg = compare_boq_integrity(b_boq_items)
        bidders_boq[b_id] = {
            "value": f"{len(b_boq_items)} items verified",
            "status": status,
            "message": msg
        }

    comparisons.append({
        "field": "boq_arithmetic_integrity",
        "tender_requirement": "Quantity × Rate = Quoted Amount, 0 Missing Rates",
        "bidder_a_value": bidders_boq.get(b_a_id, {}).get("value"),
        "bidder_a_status": bidders_boq.get(b_a_id, {}).get("status", "UNKNOWN"),
        "bidder_a_message": bidders_boq.get(b_a_id, {}).get("message", ""),
        "bidder_b_value": bidders_boq.get(b_b_id, {}).get("value"),
        "bidder_b_status": bidders_boq.get(b_b_id, {}).get("status", "UNKNOWN"),
        "bidder_b_message": bidders_boq.get(b_b_id, {}).get("message", ""),
        "bidders": bidders_boq
    })

    # Build Summary
    summary_bidders = {}
    for b in bidders_list:
        b_id = b.get("bidder_id", "bidder")
        b_name = b.get("bidder_name", b_id)
        comp_count = sum(
            1 for c in comparisons
            if c.get("bidders", {}).get(b_id, {}).get("status") == "COMPLIANT"
        )
        non_comp_count = sum(
            1 for c in comparisons
            if c.get("bidders", {}).get(b_id, {}).get("status") == "NON-COMPLIANT"
        )
        summary_bidders[b_id] = {
            "name": b_name,
            "compliant": comp_count,
            "non_compliant": non_comp_count,
            "total": len(comparisons)
        }

    summary = {
        "fields_compared": len(comparisons),
        "bidder_a_compliant": summary_bidders.get(b_a_id, {}).get("compliant", 0),
        "bidder_b_compliant": summary_bidders.get(b_b_id, {}).get("compliant", 0),
        "bidders": summary_bidders
    }

    # Cross-bidder Differences
    differences = []
    for c in comparisons:
        field = c["field"]
        vals = set()
        for b_id, b_info in c.get("bidders", {}).items():
            vals.add(str(b_info.get("value")))

        if len(vals) > 1:
            if field == "completion_period":
                impact = "Schedule"
                msg = "Bidders have different proposed completion schedules."
            elif field == "emd":
                impact = "Financial"
                msg = "Bidders submitted different EMD amounts."
            elif field == "performance_security":
                impact = "Financial / Contractual"
                msg = "Bidders offered different performance security percentages."
            elif field == "minimum_technical_score":
                impact = "Technical Qualification"
                msg = "Bidders scored differently during technical evaluation."
            elif field == "boq_arithmetic_integrity":
                impact = "Financial / Arithmetic Risk"
                msg = "One or more bidders exhibited BOQ line item calculation or missing rate anomalies."
            else:
                impact = "Contractual"
                msg = f"{field.replace('_', ' ').title()} differs among bidders."

            differences.append({
                "field": field,
                "impact": impact,
                "message": msg
            })

    bidder_a_name = bidders_list[0].get("bidder_name", "Bidder A") if len(bidders_list) > 0 else "Bidder A"
    bidder_b_name = bidders_list[1].get("bidder_name", "Bidder B") if len(bidders_list) > 1 else "Bidder B"

    return {
        "bidder_a_name": bidder_a_name,
        "bidder_b_name": bidder_b_name,
        "bidders": [
            {"bidder_id": b.get("bidder_id"), "bidder_name": b.get("bidder_name")}
            for b in bidders_list
        ],
        "summary": summary,
        "field_comparisons": comparisons,
        "differences": differences
    }


def compare_bids(
    tender_fields,
    bidders_or_a,
    bidder_b_fields=None,
    bidder_a_name="Bidder A",
    bidder_b_name="Bidder B"
):
    """
    Main entry point for comparing bids against tender requirements.
    Supports both dynamic multi-bidder list format:
        compare_bids(tender_fields, [bidder_1_dict, bidder_2_dict, ...])
    and legacy two-bidder format:
        compare_bids(tender_fields, bidder_a_fields, bidder_b_fields, name_a, name_b)
    """
    if isinstance(bidders_or_a, list):
        bidders_list = bidders_or_a
    elif isinstance(bidders_or_a, dict) and "bidders" in bidders_or_a:
        bidders_list = bidders_or_a["bidders"]
    else:
        bidders_list = [
            {
                "bidder_id": "bidder_A",
                "bidder_name": bidder_a_name,
                "bidder_fields": bidders_or_a or {}
            },
            {
                "bidder_id": "bidder_B",
                "bidder_name": bidder_b_name,
                "bidder_fields": bidder_b_fields or {}
            }
        ]

    return run_multi_bid_comparison(tender_fields, bidders_list)
