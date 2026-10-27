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


def get_evidence(fields, field_name):
    """
    Get verbatim evidence excerpt for an extracted tender field.
    """
    field = fields.get(field_name)
    if isinstance(field, dict):
        evidence = field.get("evidence")
        if evidence:
            return str(evidence).strip()
        val = field.get("value")
        if val is not None:
            return str(val).strip()
    elif field is not None:
        return str(field).strip()
    return ""


def extract_number(value):
    """
    Extract the first numeric value from text.

    Examples:
        '10%' -> 10.0
        '0.5% per week' -> 0.5
        '12 months' -> 12.0
    """
    if value is None:
        return None

    match = re.search(r"(\d+(?:\.\d+)?)", str(value))
    if not match:
        return None

    try:
        return float(match.group(1))
    except ValueError:
        return None


def analyze_risks(tender_data_or_fields):
    """
    Rule-based deterministic tender risk analysis.

    Accepts either full tender_data dictionary (containing 'tender_fields')
    or tender_fields dictionary directly.

    Returns:
        list of structured risk dictionaries with risk_id, title, category,
        severity, description, page, and evidence.
    """
    if not tender_data_or_fields or not isinstance(tender_data_or_fields, dict):
        return []

    # If full tender data dictionary is passed, extract tender_fields
    if "tender_fields" in tender_data_or_fields:
        tender_fields = tender_data_or_fields["tender_fields"]
    else:
        tender_fields = tender_data_or_fields

    raw_risks = []

    # ========================================================
    # 1. PERFORMANCE SECURITY (Financial)
    # ========================================================
    performance_security = get_value(tender_fields, "performance_security")
    performance_security_page = get_page(tender_fields, "performance_security")
    performance_security_evidence = get_evidence(tender_fields, "performance_security")
    security_percentage = extract_number(performance_security)

    if security_percentage is not None:
        if security_percentage >= 10:
            raw_risks.append({
                "title": "Performance Security",
                "risk_type": "Performance Security",
                "category": "Financial",
                "severity": "HIGH",
                "description": (
                    f"Performance security requirement is {performance_security}. "
                    f"This creates a significant financial commitment and working capital "
                    f"tie-up for the successful bidder."
                ),
                "page": performance_security_page,
                "evidence": performance_security_evidence or f"Performance Security equal to {performance_security}"
            })
        elif security_percentage >= 5:
            raw_risks.append({
                "title": "Performance Security",
                "risk_type": "Performance Security",
                "category": "Financial",
                "severity": "MEDIUM",
                "description": f"Performance security requirement is {performance_security}.",
                "page": performance_security_page,
                "evidence": performance_security_evidence or f"Performance Security equal to {performance_security}"
            })

    # ========================================================
    # 2. LIQUIDATED DAMAGES (Contractual / Financial)
    # ========================================================
    ld = get_value(tender_fields, "liquidated_damages")
    ld_page = get_page(tender_fields, "liquidated_damages")
    ld_evidence = get_evidence(tender_fields, "liquidated_damages")

    if ld:
        ld_str = (
            f"{ld.get('rate', '0.5%')} per week up to maximum of {ld.get('maximum', '10%')}"
            if isinstance(ld, dict)
            else str(ld)
        )
        raw_risks.append({
            "title": "Liquidated Damages",
            "risk_type": "Liquidated Damages",
            "category": "Contractual",
            "severity": "HIGH",
            "description": (
                f"Liquidated damages provision detected: {ld_str}. Delayed project "
                f"milestones or completion will result in recurring financial deductions."
            ),
            "page": ld_page,
            "evidence": ld_evidence or f"Liquidated damages shall be levied at {ld_str}"
        })

    # ========================================================
    # 3. EARNEST MONEY DEPOSIT (Financial)
    # ========================================================
    emd = get_value(tender_fields, "emd")
    emd_page = get_page(tender_fields, "emd")
    emd_evidence = get_evidence(tender_fields, "emd")

    if emd:
        raw_risks.append({
            "title": "Earnest Money Deposit",
            "risk_type": "Earnest Money Deposit",
            "category": "Financial",
            "severity": "MEDIUM",
            "description": (
                f"EMD requirement detected: {emd}. The bidder must ensure the required "
                f"bid security instrument is submitted in the exact specified format before the deadline."
            ),
            "page": emd_page,
            "evidence": emd_evidence or f"Earnest Money Deposit (EMD) of {emd}"
        })

    # ========================================================
    # 4. COMPLETION PERIOD (Schedule)
    # ========================================================
    completion_period = get_value(tender_fields, "completion_period")
    completion_page = get_page(tender_fields, "completion_period")
    completion_evidence = get_evidence(tender_fields, "completion_period")
    completion_number = extract_number(completion_period)

    if completion_number is not None:
        raw_risks.append({
            "title": "Completion Period",
            "risk_type": "Completion Period",
            "category": "Schedule",
            "severity": "MEDIUM",
            "description": (
                f"The specified completion schedule is {completion_period}. The contractor "
                f"must mobilize sufficient plant, labour, and materials to prevent liquidated damages."
            ),
            "page": completion_page,
            "evidence": completion_evidence or f"Project must be completed within {completion_period}"
        })

    # ========================================================
    # 5. ELIGIBILITY REQUIREMENTS (Compliance)
    # ========================================================
    eligibility = (
        get_value(tender_fields, "eligibility")
        or get_value(tender_fields, "eligibility_requirements")
    )
    eligibility_page = (
        get_page(tender_fields, "eligibility")
        or get_page(tender_fields, "eligibility_requirements")
    )
    eligibility_evidence = (
        get_evidence(tender_fields, "eligibility")
        or get_evidence(tender_fields, "eligibility_requirements")
    )

    if eligibility:
        raw_risks.append({
            "title": "Eligibility Requirements",
            "risk_type": "Eligibility Requirements",
            "category": "Compliance",
            "severity": "HIGH",
            "description": (
                "Mandatory eligibility requirements must be satisfied with verified documentation. "
                "Failure to meet any qualification criteria results in immediate bid disqualification."
            ),
            "page": eligibility_page,
            "evidence": eligibility_evidence or str(eligibility)
        })

    # ========================================================
    # 6. PROPOSAL VALIDITY (Contractual)
    # ========================================================
    proposal_validity = get_value(tender_fields, "proposal_validity")
    validity_page = get_page(tender_fields, "proposal_validity")
    validity_evidence = get_evidence(tender_fields, "proposal_validity")

    if proposal_validity:
        raw_risks.append({
            "title": "Proposal Validity",
            "risk_type": "Proposal Validity",
            "category": "Contractual",
            "severity": "LOW",
            "description": (
                f"Bid proposal validity is {proposal_validity}. Bidders must hold their quoted "
                f"prices firm and unconditionally valid throughout this duration."
            ),
            "page": validity_page,
            "evidence": validity_evidence or f"Proposal Validity: {proposal_validity}"
        })

    # ========================================================
    # 7. ASSIGN STRUCTURED RISK IDENTIFIERS (RISK_001, etc.)
    # ========================================================
    formatted_risks = []
    for idx, risk_dict in enumerate(raw_risks, start=1):
        risk_entry = {
            "risk_id": f"RISK_{idx:03d}",
            "title": risk_dict.get("title", "Tender Risk"),
            "risk_type": risk_dict.get("risk_type", risk_dict.get("title", "Tender Risk")),
            "category": risk_dict.get("category", "General"),
            "severity": risk_dict.get("severity", "MEDIUM"),
            "description": risk_dict.get("description", ""),
            "page": risk_dict.get("page", 1) or 1,
            "evidence": risk_dict.get("evidence", "")
        }
        formatted_risks.append(risk_entry)

    return formatted_risks


# ============================================================
# OBJECT-ORIENTED CLASS INTERFACE
# ============================================================

class TenderRiskAnalyzer:
    """
    Object-oriented class interface for Tender Risk Analysis.
    Used by test_risk_analysis.py, test_hybrid_risk.py, and modular evaluation scripts.
    """
    def __init__(self):
        pass

    def analyze(self, tender_data_or_fields):
        return analyze_risks(tender_data_or_fields)


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def analyze_tender_risks(tender_fields):
    """
    Compatibility wrapper for legacy code calling analyze_tender_risks().
    """
    return analyze_risks(tender_fields)
