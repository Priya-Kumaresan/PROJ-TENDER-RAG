def generate_recommendation(
    comparison_result,
    bidder_a_name,
    bidder_b_name
):
    """
    Generate a deterministic bidder recommendation
    from tender compliance results.

    The recommendation is based on compliance first.
    Financial/BOQ considerations can be added later
    after BOQ validation is finalized.
    """

    field_comparisons = comparison_result.get(
        "field_comparisons",
        []
    )

    bidder_a_compliant = 0
    bidder_a_non_compliant = 0

    bidder_b_compliant = 0
    bidder_b_non_compliant = 0

    bidder_a_failures = []
    bidder_b_failures = []

    for item in field_comparisons:

        field_name = item.get(
            "field",
            "Unknown field"
        )

        tender_requirement = item.get(
            "tender_requirement"
        )

        bidder_a_status = item.get(
            "bidder_a_status",
            "UNKNOWN"
        )

        bidder_b_status = item.get(
            "bidder_b_status",
            "UNKNOWN"
        )

        # ----------------------------------------------------
        # Bidder A
        # ----------------------------------------------------

        if bidder_a_status == "COMPLIANT":

            bidder_a_compliant += 1

        elif bidder_a_status == "NON-COMPLIANT":

            bidder_a_non_compliant += 1

            bidder_a_failures.append({
                "field": field_name,
                "requirement": tender_requirement,
                "bidder_value": item.get(
                    "bidder_a_value"
                )
            })

        # ----------------------------------------------------
        # Bidder B
        # ----------------------------------------------------

        if bidder_b_status == "COMPLIANT":

            bidder_b_compliant += 1

        elif bidder_b_status == "NON-COMPLIANT":

            bidder_b_non_compliant += 1

            bidder_b_failures.append({
                "field": field_name,
                "requirement": tender_requirement,
                "bidder_value": item.get(
                    "bidder_b_value"
                )
            })

    # ========================================================
    # DETERMINE RECOMMENDED BIDDER
    # ========================================================

    if (
        bidder_a_non_compliant == 0
        and bidder_b_non_compliant > 0
    ):

        recommended_bidder = bidder_a_name

        reason = (
            f"{bidder_a_name} is recommended because "
            f"the bidder satisfies all currently evaluated "
            f"tender requirements, while {bidder_b_name} "
            f"has {bidder_b_non_compliant} "
            f"non-compliant requirement(s)."
        )

    elif (
        bidder_b_non_compliant == 0
        and bidder_a_non_compliant > 0
    ):

        recommended_bidder = bidder_b_name

        reason = (
            f"{bidder_b_name} is recommended because "
            f"the bidder satisfies all currently evaluated "
            f"tender requirements, while {bidder_a_name} "
            f"has {bidder_a_non_compliant} "
            f"non-compliant requirement(s)."
        )

    elif (
        bidder_a_non_compliant
        < bidder_b_non_compliant
    ):

        recommended_bidder = bidder_a_name

        reason = (
            f"{bidder_a_name} is provisionally recommended "
            f"because the bidder has fewer non-compliant "
            f"requirements than {bidder_b_name}."
        )

    elif (
        bidder_b_non_compliant
        < bidder_a_non_compliant
    ):

        recommended_bidder = bidder_b_name

        reason = (
            f"{bidder_b_name} is provisionally recommended "
            f"because the bidder has fewer non-compliant "
            f"requirements than {bidder_a_name}."
        )

    else:

        recommended_bidder = None

        reason = (
            "No single bidder can be recommended from "
            "the currently evaluated compliance criteria. "
            "Further technical, financial and BOQ "
            "evaluation is required."
        )

    # ========================================================
    # BUILD RESULT
    # ========================================================

    return {
        "recommended_bidder":
            recommended_bidder,

        "recommendation":
            reason,

        "recommendation_basis":
            "Tender compliance evaluation",

        "provisional":
            True,

        "bidder_a": {
            "name":
                bidder_a_name,

            "compliant_requirements":
                bidder_a_compliant,

            "non_compliant_requirements":
                bidder_a_non_compliant,

            "non_compliance_details":
                bidder_a_failures
        },

        "bidder_b": {
            "name":
                bidder_b_name,

            "compliant_requirements":
                bidder_b_compliant,

            "non_compliant_requirements":
                bidder_b_non_compliant,

            "non_compliance_details":
                bidder_b_failures
        },

        "note": (
            "This is a provisional recommendation based "
            "on the currently implemented compliance "
            "checks. BOQ and final financial evaluation "
            "should be incorporated before final award."
        )
    }