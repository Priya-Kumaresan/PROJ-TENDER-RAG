def analyze_comparison_differences(
    differences
):
    """
    Analyze important differences between
    two tenders using deterministic rules.
    """

    analyzed = []

    # Fields that identify the tender rather than
    # represent a substantive requirement.
    identifier_fields = {
        "tender_number",
        "organisation",
        "project_name"
    }

    for item in differences:

        field = item["field"]

        value_a = item["normalized_a"]
        value_b = item["normalized_b"]

        # -----------------------------------
        # Ignore identifier differences
        # -----------------------------------

        if field in identifier_fields:
            continue

        analysis = {
            "field": field,
            "tender_a": item["tender_a"],
            "tender_b": item["tender_b"],
            "impact": None,
            "message": None
        }

        # -----------------------------------
        # Completion period
        # -----------------------------------

        if (
            field == "completion_period"
            and isinstance(value_a, dict)
            and isinstance(value_b, dict)
        ):

            if value_a["unit"] == value_b["unit"]:

                if value_a["value"] < value_b["value"]:

                    analysis["impact"] = "Schedule"

                    analysis["message"] = (
                        "Tender A has a shorter "
                        "completion period than "
                        "Tender B."
                    )

                elif value_a["value"] > value_b["value"]:

                    analysis["impact"] = "Schedule"

                    analysis["message"] = (
                        "Tender A has a longer "
                        "completion period than "
                        "Tender B."
                    )

        # -----------------------------------
        # EMD
        # -----------------------------------

        elif (
            field == "emd"
            and isinstance(value_a, (int, float))
            and isinstance(value_b, (int, float))
        ):

            analysis["impact"] = "Financial"

            if value_a > value_b:

                analysis["message"] = (
                    "Tender A requires a "
                    "higher EMD than Tender B."
                )

            elif value_a < value_b:

                analysis["message"] = (
                    "Tender A requires a "
                    "lower EMD than Tender B."
                )

        # -----------------------------------
        # Performance security
        # -----------------------------------

        elif (
            field == "performance_security"
            and isinstance(value_a, (int, float))
            and isinstance(value_b, (int, float))
        ):

            analysis["impact"] = "Financial"

            if value_a > value_b:

                analysis["message"] = (
                    "Tender A has a higher "
                    "performance security "
                    "requirement."
                )

            elif value_a < value_b:

                analysis["message"] = (
                    "Tender A has a lower "
                    "performance security "
                    "requirement."
                )

        # -----------------------------------
        # Liquidated damages
        # -----------------------------------

        elif field == "liquidated_damages":

            analysis["impact"] = (
                "Contractual / Financial"
            )

            analysis["message"] = (
                "The liquidated damages "
                "requirements differ between "
                "the two tenders."
            )

        # -----------------------------------
        # Other requirement differences
        # -----------------------------------

        if analysis["message"] is None:

            analysis["impact"] = (
                "Administrative / Contractual"
            )

            analysis["message"] = (
                f"The {field} requirement "
                "differs between the two tenders."
            )

        analyzed.append(analysis)

    return analyzed