import re


def _create_field(
    value,
    page,
    evidence
):
    """
    Create a standard structured field.
    """

    return {
        "value": value,
        "page": page,
        "evidence": evidence
    }


def _search_pages(
    pages,
    patterns
):
    """
    Search all extracted PDF pages using
    a list of regular-expression patterns.
    """

    for page in pages:

        text = page.get(
            "cleaned_text",
            ""
        )

        # Fallback in case cleaned text
        # is unavailable.
        if not text:
            text = page.get(
                "raw_text",
                ""
            )

        if not text:
            continue

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE | re.DOTALL
            )

            if match:

                return (
                    match.group(1).strip(),
                    page.get("page_number"),
                    match.group(0).strip()
                )

    return None


def extract_bidder_fields(
    pdf_data,
    bidder_name
):

    pages = pdf_data.get(
        "pages",
        []
    )

    fields = {}


    # ========================================================
    # BIDDER NAME
    # ========================================================

    result = _search_pages(
        pages,
        [
            r"(?:Company Name|Bidder Name|Name of Bidder)"
            r"\s*:\s*(.+?)(?:\n|$)"
        ]
    )

    if result:

        value, page, evidence = result

        fields["bidder_name"] = _create_field(
            value,
            page,
            evidence
        )

    else:

        fields["bidder_name"] = _create_field(
            bidder_name,
            None,
            "Provided bidder name"
        )


    # ========================================================
    # REGISTRATION NUMBER
    # ========================================================

    result = _search_pages(
        pages,
        [
            r"(?:Registration No\.?|Registration Number)"
            r"\s*:\s*(.+?)(?:\n|$)",

            r"(?:CIN|Company Registration No\.?)"
            r"\s*:\s*(.+?)(?:\n|$)"
        ]
    )

    if result:

        value, page, evidence = result

        fields["registration_number"] = _create_field(
            value,
            page,
            evidence
        )


    # ========================================================
    # EMD
    # ========================================================

    result = _search_pages(
        pages,
        [
            r"(?:EMD|Earnest Money Deposit)"
            r".{0,100}?"
            r"(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)"
        ]
    )

    if result:

        value, page, evidence = result

        fields["emd_submitted"] = _create_field(
            f"INR {value}",
            page,
            evidence
        )


    # ========================================================
    # COMPLETION PERIOD
    # ========================================================

    result = _search_pages(
        pages,
        [
            r"(?:completion period|completion|complete)"
            r".{0,100}?"
            r"(\d+(?:\.\d+)?\s*"
            r"(?:days?|weeks?|months?|years?))"
        ]
    )

    if result:

        value, page, evidence = result

        fields["completion_period"] = _create_field(
            value,
            page,
            evidence
        )


    # ========================================================
    # PERFORMANCE SECURITY
    # ========================================================

    result = _search_pages(
        pages,
        [
            r"(?:performance security|performance guarantee)"
            r".{0,100}?"
            r"(\d+(?:\.\d+)?\s*%)"
        ]
    )

    if result:

        value, page, evidence = result

        fields["performance_security"] = _create_field(
            value,
            page,
            evidence
        )


    # ========================================================
    # TOTAL QUOTED AMOUNT
    # ========================================================

    result = _search_pages(
        pages,
        [
            # Example:
            # Total Quoted Bid Amount: INR 4,65,00,000
            r"(?:total quoted bid amount|"
            r"total quoted amount|"
            r"total bid amount|"
            r"total contract price|"
            r"total quoted price|"
            r"grand total|"
            r"total amount)"
            r"\s*[:\-]?\s*"
            r"(?:INR|Rs\.?|₹)\s*"
            r"([\d,]+(?:\.\d+)?)",

            # Allows small amount of text between
            # label and currency.
            r"(?:total quoted bid amount|"
            r"total quoted amount|"
            r"total bid amount|"
            r"total contract price)"
            r".{0,80}?"
            r"(?:INR|Rs\.?|₹)\s*"
            r"([\d,]+(?:\.\d+)?)"
        ]
    )

    if result:

        value, page, evidence = result

        fields["total_quoted_amount"] = _create_field(
            f"INR {value}",
            page,
            evidence
        )


    # ========================================================
    # TECHNICAL SCORE
    # ========================================================

    result = _search_pages(
        pages,
        [
            r"(?:technical score|"
            r"technical marks|"
            r"technical evaluation score)"
            r".{0,50}?"
            r"(\d+(?:\.\d+)?)"
        ]
    )

    if result:

        value, page, evidence = result

        fields["technical_score"] = _create_field(
            value,
            page,
            evidence
        )


    return fields