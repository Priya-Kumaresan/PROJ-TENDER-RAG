import re


def get_value(fields, field_name):
    """
    Safely get a value from extracted tender fields.
    """

    field = fields.get(field_name)

    if isinstance(field, dict):
        return field.get("value")

    return field


def get_page(fields, field_name):
    """
    Get source page for an extracted tender field.
    """

    field = fields.get(field_name)

    if isinstance(field, dict):
        return field.get("page")

    return None


def extract_number(value):
    """
    Extract the first numeric value from text.

    Example:
        '10%' -> 10
        '0.5% per week' -> 0.5
        '12 months' -> 12
    """

    if value is None:
        return None

    match = re.search(
        r"(\d+(?:\.\d+)?)",
        str(value)
    )

    if not match:
        return None

    try:
        return float(match.group(1))
    except ValueError:
        return None


def analyze_risks(tender_fields):
    """
    Rule-based tender risk analysis.

    Returns:
        list of risk dictionaries
    """

    risks = []

    # ========================================================
    # PERFORMANCE SECURITY
    # ========================================================

    performance_security = get_value(
        tender_fields,
        "performance_security"
    )

    performance_security_page = get_page(
        tender_fields,
        "performance_security"
    )

    security_percentage = extract_number(
        performance_security
    )

    if security_percentage is not None:

        if security_percentage >= 10:

            risks.append({
                "risk_type": "Performance Security",
                "category": "Financial",
                "severity": "HIGH",
                "description": (
                    f"Performance security requirement is "
                    f"{performance_security}. This creates a "
                    f"significant financial commitment for "
                    f"the successful bidder."
                ),
                "page": performance_security_page
            })

        elif security_percentage >= 5:

            risks.append({
                "risk_type": "Performance Security",
                "category": "Financial",
                "severity": "MEDIUM",
                "description": (
                    f"Performance security requirement is "
                    f"{performance_security}."
                ),
                "page": performance_security_page
            })

    # ========================================================
    # LIQUIDATED DAMAGES
    # ========================================================

    ld = get_value(
        tender_fields,
        "liquidated_damages"
    )

    ld_page = get_page(
        tender_fields,
        "liquidated_damages"
    )

    if ld:

        risks.append({
            "risk_type": "Liquidated Damages",
            "category": "Contractual",
            "severity": "HIGH",
            "description": (
                f"Liquidated damages provision detected: "
                f"{ld}. Delayed completion may result in "
                f"financial penalties."
            ),
            "page": ld_page
        })

    # ========================================================
    # EMD
    # ========================================================

    emd = get_value(
        tender_fields,
        "emd"
    )

    emd_page = get_page(
        tender_fields,
        "emd"
    )

    if emd:

        risks.append({
            "risk_type": "Earnest Money Deposit",
            "category": "Financial",
            "severity": "MEDIUM",
            "description": (
                f"EMD requirement detected: {emd}. "
                f"The bidder must ensure the required "
                f"bid security is correctly submitted."
            ),
            "page": emd_page
        })

    # ========================================================
    # COMPLETION PERIOD
    # ========================================================

    completion_period = get_value(
        tender_fields,
        "completion_period"
    )

    completion_page = get_page(
        tender_fields,
        "completion_period"
    )

    completion_number = extract_number(
        completion_period
    )

    if completion_number is not None:

        risks.append({
            "risk_type": "Completion Period",
            "category": "Schedule",
            "severity": "MEDIUM",
            "description": (
                f"The specified completion period is "
                f"{completion_period}. The bidder should "
                f"verify that sufficient labour, equipment "
                f"and resources are available to meet the "
                f"schedule."
            ),
            "page": completion_page
        })

    # ========================================================
    # ELIGIBILITY
    # ========================================================

    eligibility = get_value(
        tender_fields,
        "eligibility"
    )

    if eligibility is None:

        eligibility = get_value(
            tender_fields,
            "eligibility_requirements"
        )

    eligibility_page = (
        get_page(
            tender_fields,
            "eligibility"
        )
        or get_page(
            tender_fields,
            "eligibility_requirements"
        )
    )

    if eligibility:

        risks.append({
            "risk_type": "Eligibility Requirements",
            "category": "Compliance",
            "severity": "HIGH",
            "description": (
                "Eligibility requirements must be "
                "carefully verified against each bidder's "
                "technical submission. Failure to satisfy "
                "a mandatory eligibility requirement may "
                "make the bid non-compliant."
            ),
            "page": eligibility_page
        })

    # ========================================================
    # PROPOSAL VALIDITY
    # ========================================================

    proposal_validity = get_value(
        tender_fields,
        "proposal_validity"
    )

    validity_page = get_page(
        tender_fields,
        "proposal_validity"
    )

    if proposal_validity:

        risks.append({
            "risk_type": "Proposal Validity",
            "category": "Contractual",
            "severity": "LOW",
            "description": (
                f"Bid validity requirement is "
                f"{proposal_validity}. The bidder must "
                f"keep the offer valid for the required "
                f"period."
            ),
            "page": validity_page
        })

    return risks


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def analyze_tender_risks(tender_fields):
    """
    Keep compatibility with older project code that may call
    analyze_tender_risks().
    """

    return analyze_risks(tender_fields)