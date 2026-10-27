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
            # Pattern 1: Label followed by currency then number (e.g. Total Quoted Bid Amount: INR 4,65,00,000 or INR 4.65 crore)
            r"(?:quoted\s+total(?:\s+lump[\s\-]sum)?\s+amount|"
            r"total\s+quoted(?:\s+lump[\s\-]sum)?\s+amount|"
            r"total\s+quoted\s+bid\s+amount|"
            r"total\s+quoted\s+amount|"
            r"total\s+bid\s+amount|"
            r"total\s+contract\s+price|"
            r"total\s+quoted\s+price|"
            r"total\s+bid\s+price|"
            r"total\s+financial\s+quote|"
            r"quoted\s+bid\s+amount|"
            r"quoted\s+amount|"
            r"grand\s+total|"
            r"total\s+bid|"
            r"total\s+amount|"
            r"total\s+price)"
            r"\s*[:\-]?\s*"
            r"(?:INR|Rs\.?|₹)\s*"
            r"([\d,]+(?:\.\d+)?\s*(?:crores?|cr|lakhs?|lac|lacs)?)",

            # Pattern 2: Label followed by number with crore/lakh notation
            r"(?:quoted\s+total(?:\s+lump[\s\-]sum)?\s+amount|"
            r"total\s+quoted(?:\s+lump[\s\-]sum)?\s+amount|"
            r"total\s+quoted\s+bid\s+amount|"
            r"total\s+quoted\s+amount|"
            r"total\s+bid\s+amount|"
            r"total\s+contract\s+price|"
            r"total\s+quoted\s+price|"
            r"total\s+financial\s+quote|"
            r"grand\s+total|"
            r"total\s+bid|"
            r"total\s+amount)"
            r"\s*[:\-]?\s*"
            r"([\d,]+(?:\.\d+)?\s*(?:crores?|cr|lakhs?|lac|lacs))\b",

            # Pattern 3: Label followed by number and trailing currency or /-
            r"(?:quoted\s+total(?:\s+lump[\s\-]sum)?\s+amount|"
            r"total\s+quoted(?:\s+lump[\s\-]sum)?\s+amount|"
            r"total\s+quoted\s+bid\s+amount|"
            r"total\s+quoted\s+amount|"
            r"total\s+bid\s+amount|"
            r"total\s+contract\s+price|"
            r"total\s+quoted\s+price|"
            r"grand\s+total|"
            r"total\s+amount)"
            r"\s*[:\-]?\s*"
            r"([\d,]+(?:\.\d+)?)\s*(?:INR|Rs\.?|₹|/\-)",

            # Pattern 4: Allows small interstitial text
            r"(?:quoted\s+total(?:\s+lump[\s\-]sum)?\s+amount|"
            r"total\s+quoted(?:\s+lump[\s\-]sum)?\s+amount|"
            r"total\s+quoted\s+bid\s+amount|"
            r"total\s+quoted\s+amount|"
            r"total\s+bid\s+amount|"
            r"total\s+contract\s+price)"
            r".{0,80}?"
            r"(?:INR|Rs\.?|₹)\s*"
            r"([\d,]+(?:\.\d+)?\s*(?:crores?|cr|lakhs?|lac|lacs)?)"
        ]
    )

    if result:

        value, page, evidence = result

        # Ensure consistent formatting without duplicate currency prefixes
        value_clean = re.sub(
            r"^(?:INR|Rs\.?|₹)\s*",
            "",
            value.strip(),
            flags=re.IGNORECASE
        )

        fields["total_quoted_amount"] = _create_field(
            f"INR {value_clean}",
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