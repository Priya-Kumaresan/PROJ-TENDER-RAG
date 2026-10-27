import math

try:
    import pandas as pd
except ImportError:
    pd = None


def _is_na(val):
    if val is None:
        return True
    if isinstance(val, float) and math.isnan(val):
        return True
    if str(val).strip().lower() in ("nan", "none", ""):
        return True
    return False


def _not_na(val):
    return not _is_na(val)


def validate_boq(df):
    """
    Validate BOQ items for arithmetic consistency (Quantity * Rate = Amount),
    missing quantities, missing rates, and missing amounts.
    Supports both pandas DataFrames and native lists of row dictionaries.
    """
    results = []

    if hasattr(df, "iterrows"):
        row_iter = df.iterrows()
    elif isinstance(df, list):
        row_iter = enumerate(df)
    else:
        row_iter = []

    for index, row in row_iter:
        item_no = row.get("item_no") if isinstance(row, dict) else row["item_no"]
        description = row.get("description") if isinstance(row, dict) else row["description"]
        quantity = row.get("quantity") if isinstance(row, dict) else row["quantity"]
        rate = row.get("rate") if isinstance(row, dict) else row["rate"]
        amount = row.get("amount") if isinstance(row, dict) else row["amount"]
        gst = row.get("gst") if isinstance(row, dict) else row["gst"]

        issues = []

        # -----------------------------
        # Missing value validation
        # -----------------------------
        if _is_na(quantity):
            issues.append("Missing quantity")

        if _is_na(rate):
            issues.append("Missing rate")

        if _is_na(amount):
            issues.append("Missing amount")

        # -----------------------------
        # Calculation validation
        # -----------------------------
        expected_amount = None

        if _not_na(quantity) and _not_na(rate):
            try:
                expected_amount = float(quantity) * float(rate)
                if _not_na(amount):
                    difference = abs(expected_amount - float(amount))
                    if difference > 0.01:
                        issues.append("Amount mismatch")
            except (ValueError, TypeError):
                pass

        # -----------------------------
        # Final status
        # -----------------------------
        if len(issues) == 0:
            status = "VALID"
        else:
            status = "ISSUE"

        results.append({
            "item_no": item_no,
            "description": description,
            "quantity": quantity,
            "rate": rate,
            "quoted_amount": amount,
            "expected_amount": expected_amount,
            "gst": gst,
            "status": status,
            "issues": issues
        })

    return results


def analyze_boq_risks(items):
    """
    Perform deterministic BOQ anomaly analysis.
    """
    risks = []

    for item in items:
        item_no = item.get("item_no")
        description = item.get("description", "")

        quantity = item.get("quantity")
        rate = item.get("rate")
        amount = item.get("quoted_amount")

        quantity_missing = _is_na(quantity)
        rate_missing = _is_na(rate)
        amount_missing = _is_na(amount)

        # -----------------------------
        # Missing quantity
        # -----------------------------
        if quantity_missing:
            risks.append({
                "item_no": item_no,
                "category": "Missing Value",
                "severity": "HIGH",
                "issue": "Quantity is missing",
                "description": description
            })

        # -----------------------------
        # Missing rate
        # -----------------------------
        if rate_missing:
            risks.append({
                "item_no": item_no,
                "category": "Missing Value",
                "severity": "HIGH",
                "issue": "Rate is missing",
                "description": description
            })

        # -----------------------------
        # Missing amount
        # -----------------------------
        if amount_missing:
            risks.append({
                "item_no": item_no,
                "category": "Missing Value",
                "severity": "HIGH",
                "issue": "Amount is missing",
                "description": description
            })

        # -----------------------------
        # Arithmetic validation
        # -----------------------------
        if (
            not quantity_missing
            and not rate_missing
            and not amount_missing
        ):
            try:
                expected_amount = float(quantity) * float(rate)
                difference = abs(expected_amount - float(amount))
                tolerance = 0.01

                if difference > tolerance:
                    risks.append({
                        "item_no": item_no,
                        "category": "Calculation Error",
                        "severity": "HIGH",
                        "issue": "Quantity × Rate does not match Amount",
                        "description": description,
                        "expected_amount": expected_amount,
                        "actual_amount": amount,
                        "difference": difference
                    })
            except (ValueError, TypeError):
                pass

    # ---------------------------------
    # Duplicate item detection
    # ---------------------------------
    seen_descriptions = {}

    for item in items:
        item_no = item.get("item_no")
        description = (
            item.get("description", "")
            .strip()
            .lower()
        )

        if not description:
            continue

        if description in seen_descriptions:
            risks.append({
                "item_no": item_no,
                "category": "Duplicate Item",
                "severity": "MEDIUM",
                "issue": "Possible duplicate BOQ item",
                "description": item.get("description", ""),
                "duplicate_of": seen_descriptions[description]
            })
        else:
            seen_descriptions[description] = item_no

    return risks
