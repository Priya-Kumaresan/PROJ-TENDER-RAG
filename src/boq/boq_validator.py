import pandas as pd
import math

def validate_boq(df):

    results = []

    for index, row in df.iterrows():

        item_no = row["item_no"]
        description = row["description"]
        quantity = row["quantity"]
        rate = row["rate"]
        amount = row["amount"]
        gst = row["gst"]

        issues = []

        # -----------------------------
        # Missing value validation
        # -----------------------------

        if pd.isna(quantity):
            issues.append("Missing quantity")

        if pd.isna(rate):
            issues.append("Missing rate")

        if pd.isna(amount):
            issues.append("Missing amount")

        # -----------------------------
        # Calculation validation
        # -----------------------------

        expected_amount = None

        if (
            pd.notna(quantity)
            and pd.notna(rate)
        ):

            expected_amount = quantity * rate

            if pd.notna(amount):

                difference = abs(
                    expected_amount - amount
                )

                if difference > 0.01:
                    issues.append(
                        "Amount mismatch"
                    )

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
        description = item.get(
            "description",
            ""
        )

        quantity = item.get("quantity")
        rate = item.get("rate")
        amount = item.get("quoted_amount")
        quantity_missing = (
            quantity is None
            or (
                isinstance(quantity, float)
                and math.isnan(quantity)
            )
        )

        rate_missing = (
            rate is None
            or (
                isinstance(rate, float)
                and math.isnan(rate)
            )
        )

        amount_missing = (
            amount is None
            or (
                isinstance(amount, float)
                and math.isnan(amount)
            )
        )
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

            expected_amount = (
                quantity * rate
            )

            difference = abs(
                expected_amount - amount
            )

            tolerance = 0.01

            if difference > tolerance:

                risks.append({
                    "item_no": item_no,
                    "category":
                        "Calculation Error",
                    "severity": "HIGH",
                    "issue":
                        "Quantity × Rate does not "
                        "match Amount",
                    "description": description,
                    "expected_amount":
                        expected_amount,
                    "actual_amount":
                        amount,
                    "difference":
                        difference
                })
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
                "issue":
                    "Possible duplicate BOQ item",
                "description":
                    item.get("description", ""),
                "duplicate_of":
                    seen_descriptions[
                        description
                    ]
            })

        else:

            seen_descriptions[
                description
            ] = item_no
    return risks