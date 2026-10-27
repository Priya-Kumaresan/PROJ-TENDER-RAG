import re


def normalize_percentage(value):

    if value is None:
        return None

    text = str(value)

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*%",
        text
    )

    if match:

        return float(
            match.group(1)
        )


    match = re.search(
        r"(\d+(?:\.\d+)?)\s*percent",
        text,
        re.IGNORECASE
    )

    if match:

        return float(
            match.group(1)
        )


    return None


def normalize_currency(value):

    if value is None:
        return None

    text = str(value)

    text = re.sub(
        r"(?i)(inr|rs\.?|₹)",
        "",
        text
    )

    text = text.replace(
        ",",
        ""
    ).strip()


    try:

        return float(text)

    except ValueError:

        return None


def normalize_duration(value):

    if value is None:
        return None

    text = str(value).lower()


    match = re.search(
        r"(\d+(?:\.\d+)?)\s*"
        r"(days?|weeks?|months?|years?)",
        text
    )


    if not match:

        return None


    number = float(
        match.group(1)
    )


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


def compare_duration(
    tender_value,
    bidder_value
):

    tender_days = normalize_duration(
        tender_value
    )

    bidder_days = normalize_duration(
        bidder_value
    )


    if (
        tender_days is None
        or bidder_days is None
    ):

        return (
            "UNKNOWN",
            "Unable to compare completion periods."
        )


    if bidder_days <= tender_days:

        return (
            "COMPLIANT",
            "Bidder meets the tender completion requirement."
        )


    difference = (
        bidder_days
        - tender_days
    )


    return (
        "NON-COMPLIANT",
        f"Bidder completion period exceeds the "
        f"tender requirement by approximately "
        f"{difference:g} days."
    )


def compare_percentage(
    tender_value,
    bidder_value,
    field_name
):

    tender_percentage = normalize_percentage(
        tender_value
    )

    bidder_percentage = normalize_percentage(
        bidder_value
    )


    if (
        tender_percentage is None
        or bidder_percentage is None
    ):

        return (
            "UNKNOWN",
            f"Unable to compare {field_name}."
        )


    if bidder_percentage >= tender_percentage:

        return (
            "COMPLIANT",
            f"Bidder meets or exceeds the "
            f"tender {field_name} requirement."
        )


    return (
        "NON-COMPLIANT",
        f"Bidder's {field_name} is below "
        f"the tender requirement."
    )


def compare_currency(
    tender_value,
    bidder_value,
    field_name
):

    tender_amount = normalize_currency(
        tender_value
    )

    bidder_amount = normalize_currency(
        bidder_value
    )


    if (
        tender_amount is None
        or bidder_amount is None
    ):

        return (
            "UNKNOWN",
            f"Unable to compare {field_name}."
        )


    if bidder_amount >= tender_amount:

        return (
            "COMPLIANT",
            f"Bidder meets or exceeds the "
            f"tender {field_name} requirement."
        )


    return (
        "NON-COMPLIANT",
        f"Bidder's {field_name} is below "
        f"the tender requirement."
    )


def compare_bidder_to_tender(
    tender_fields,
    bidder_a_fields,
    bidder_b_fields,
    bidder_a_name="Bidder A",
    bidder_b_name="Bidder B"
):

    comparisons = []


    # ========================================================
    # COMPLETION PERIOD
    # ========================================================

    tender_completion = tender_fields.get(
        "completion_period",
        {}
    ).get(
        "value"
    )


    bidder_a_completion = bidder_a_fields.get(
        "completion_period",
        {}
    ).get(
        "value"
    )


    bidder_b_completion = bidder_b_fields.get(
        "completion_period",
        {}
    ).get(
        "value"
    )


    a_status, a_message = compare_duration(
        tender_completion,
        bidder_a_completion
    )


    b_status, b_message = compare_duration(
        tender_completion,
        bidder_b_completion
    )


    comparisons.append({
        "field": "completion_period",
        "tender_requirement": tender_completion,
        "bidder_a_value": bidder_a_completion,
        "bidder_a_status": a_status,
        "bidder_a_message": a_message,
        "bidder_b_value": bidder_b_completion,
        "bidder_b_status": b_status,
        "bidder_b_message": b_message
    })


    # ========================================================
    # PERFORMANCE SECURITY
    # ========================================================

    tender_security = tender_fields.get(
        "performance_security",
        {}
    ).get(
        "value"
    )


    bidder_a_security = bidder_a_fields.get(
        "performance_security",
        {}
    ).get(
        "value"
    )


    bidder_b_security = bidder_b_fields.get(
        "performance_security",
        {}
    ).get(
        "value"
    )


    a_status, a_message = compare_percentage(
        tender_security,
        bidder_a_security,
        "performance security"
    )


    b_status, b_message = compare_percentage(
        tender_security,
        bidder_b_security,
        "performance security"
    )


    comparisons.append({
        "field": "performance_security",
        "tender_requirement": tender_security,
        "bidder_a_value": bidder_a_security,
        "bidder_a_status": a_status,
        "bidder_a_message": a_message,
        "bidder_b_value": bidder_b_security,
        "bidder_b_status": b_status,
        "bidder_b_message": b_message
    })


    # ========================================================
    # EMD
    # ========================================================

    tender_emd = tender_fields.get(
        "emd",
        {}
    ).get(
        "value"
    )


    bidder_a_emd = bidder_a_fields.get(
        "emd_submitted",
        {}
    ).get(
        "value"
    )


    bidder_b_emd = bidder_b_fields.get(
        "emd_submitted",
        {}
    ).get(
        "value"
    )


    tender_emd_value = normalize_currency(
        tender_emd
    )


    bidder_a_emd_value = normalize_currency(
        bidder_a_emd
    )


    bidder_b_emd_value = normalize_currency(
        bidder_b_emd
    )


    if (
        tender_emd_value is not None
        and bidder_a_emd_value is not None
    ):

        if bidder_a_emd_value >= tender_emd_value:

            a_status = "COMPLIANT"

            a_message = (
                "Bidder submitted an EMD "
                "meeting the tender requirement."
            )

        else:

            a_status = "NON-COMPLIANT"

            a_message = (
                "Bidder submitted an EMD "
                "below the tender requirement."
            )

    else:

        a_status = "UNKNOWN"

        a_message = (
            "Unable to compare EMD."
        )


    if (
        tender_emd_value is not None
        and bidder_b_emd_value is not None
    ):

        if bidder_b_emd_value >= tender_emd_value:

            b_status = "COMPLIANT"

            b_message = (
                "Bidder submitted an EMD "
                "meeting the tender requirement."
            )

        else:

            b_status = "NON-COMPLIANT"

            b_message = (
                "Bidder submitted an EMD "
                "below the tender requirement."
            )

    else:

        b_status = "UNKNOWN"

        b_message = (
            "Unable to compare EMD."
        )


    comparisons.append({
        "field": "emd",
        "tender_requirement": tender_emd,
        "bidder_a_value": bidder_a_emd,
        "bidder_a_status": a_status,
        "bidder_a_message": a_message,
        "bidder_b_value": bidder_b_emd,
        "bidder_b_status": b_status,
        "bidder_b_message": b_message
    })


    return comparisons


def create_bid_summary(
    comparisons
):

    fields_compared = len(
        comparisons
    )


    bidder_a_compliant = sum(
        1
        for item in comparisons
        if item["bidder_a_status"]
        == "COMPLIANT"
    )


    bidder_b_compliant = sum(
        1
        for item in comparisons
        if item["bidder_b_status"]
        == "COMPLIANT"
    )


    return {
        "fields_compared": fields_compared,
        "bidder_a_compliant":
            bidder_a_compliant,
        "bidder_b_compliant":
            bidder_b_compliant
    }


def create_differences(
    comparisons,
    bidder_a_name,
    bidder_b_name
):

    differences = []


    for item in comparisons:

        if (
            item["bidder_a_value"]
            == item["bidder_b_value"]
        ):

            continue


        field = item["field"]


        if field == "completion_period":

            impact = "Schedule"

            message = (
                f"{bidder_a_name} and "
                f"{bidder_b_name} have different "
                f"completion commitments."
            )


        elif field == "emd":

            impact = "Financial"

            message = (
                f"{bidder_a_name} and "
                f"{bidder_b_name} submitted "
                f"different EMD values."
            )


        elif field == "performance_security":

            impact = "Financial / Contractual"

            message = (
                f"{bidder_a_name} and "
                f"{bidder_b_name} have different "
                f"performance security commitments."
            )


        else:

            impact = "Contractual"

            message = (
                f"{field} differs between "
                f"the two bidders."
            )


        differences.append({
            "field": field,
            "impact": impact,
            "message": message
        })


    return differences


def compare_bids(
    tender_fields,
    bidder_a_fields,
    bidder_b_fields,
    bidder_a_name="Bidder A",
    bidder_b_name="Bidder B"
):

    comparisons = compare_bidder_to_tender(
        tender_fields,
        bidder_a_fields,
        bidder_b_fields,
        bidder_a_name,
        bidder_b_name
    )


    summary = create_bid_summary(
        comparisons
    )


    differences = create_differences(
        comparisons,
        bidder_a_name,
        bidder_b_name
    )


    return {
        "bidder_a_name": bidder_a_name,
        "bidder_b_name": bidder_b_name,
        "summary": summary,
        "field_comparisons": comparisons,
        "differences": differences
    }