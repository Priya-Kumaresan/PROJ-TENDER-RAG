import re


def find_page_containing(pages, search_text):
    """
    Find which page contains a piece of text.
    """

    search_text = search_text.lower()

    for page in pages:

        text = page["cleaned_text"].lower()

        if search_text in text:
            return page["page_number"]

    return None


def extract_tender_fields(pdf_data):
    """
    Extract important structured tender fields
    using simple rules and regular expressions.
    """

    pages = pdf_data["pages"]

    # Combine all page text
    full_text = "\n".join(
        page["cleaned_text"]
        for page in pages
    )

    fields = {}

    # -----------------------------------
    # Tender Number
    # -----------------------------------

    match = re.search(
        r"Tender\s*No\s*:\s*([^\n]+)",
        full_text,
        re.IGNORECASE
    )

    if match:

        value = match.group(1).strip()

        fields["tender_number"] = {
            "value": value,
            "page": find_page_containing(
                pages,
                value
            ),
            "evidence": match.group(0)
        }


    # -----------------------------------
    # Organisation
    # -----------------------------------

    match = re.search(
        r"Organisation\s*:\s*([^\n]+)",
        full_text,
        re.IGNORECASE
    )

    if match:

        value = match.group(1).strip()

        fields["organisation"] = {
            "value": value,
            "page": find_page_containing(
                pages,
                value
            ),
            "evidence": match.group(0)
        }


    # -----------------------------------
    # Project
    # -----------------------------------

    match = re.search(
        r"Project\s*:\s*([^\n]+)",
        full_text,
        re.IGNORECASE
    )

    if match:

        value = match.group(1).strip()

        fields["project_name"] = {
            "value": value,
            "page": find_page_containing(
                pages,
                value
            ),
            "evidence": match.group(0)
        }


    # -----------------------------------
    # Proposal Validity
    # -----------------------------------

    match = re.search(
        r"Proposal\s+Validity\s*:\s*([^\n]+)",
        full_text,
        re.IGNORECASE
    )

    if match:

        value = match.group(1).strip()

        fields["proposal_validity"] = {
            "value": value,
            "page": find_page_containing(
                pages,
                value
            ),
            "evidence": match.group(0)
        }


    # -----------------------------------
    # EMD
    # -----------------------------------

    match = re.search(
        r"Earnest Money Deposit.*?"
        r"(INR\s*[\d,]+)",
        full_text,
        re.IGNORECASE | re.DOTALL
    )

    if match:

        value = match.group(1).strip()

        fields["emd"] = {
            "value": value,
            "page": find_page_containing(
                pages,
                value
            ),
            "evidence": match.group(0)[:500]
        }


    # -----------------------------------
    # Performance Security
    # -----------------------------------

    match = re.search(
        r"Performance Security equal to "
        r"(\d+(?:\.\d+)?%\s+of\s+the\s+accepted\s+contract\s+value)",
        full_text,
        re.IGNORECASE
    )

    if match:

        value = match.group(1).strip()

        fields["performance_security"] = {
            "value": value,
            "page": find_page_containing(
                pages,
                "Performance Security equal to"
            ),
            "evidence": match.group(0)
        }


    # -----------------------------------
    # Completion Period
    # -----------------------------------

    match = re.search(
        r"completed within\s+(\d+\s+months?)",
        full_text,
        re.IGNORECASE
    )

    if match:

        value = match.group(1).strip()

        fields["completion_period"] = {
            "value": value,
            "page": find_page_containing(
                pages,
                "completed within"
            ),
            "evidence": match.group(0)
        }


    # -----------------------------------
    # Liquidated Damages
    # -----------------------------------

    match = re.search(
        r"liquidated damages shall be levied at "
        r"(\d+(?:\.\d+)?%).*?"
        r"maximum of\s+(\d+(?:\.\d+)?%)",
        full_text,
        re.IGNORECASE | re.DOTALL
    )

    if match:

        rate = match.group(1)
        maximum = match.group(2)

        fields["liquidated_damages"] = {
            "rate": rate,
            "maximum": maximum,
            "page": find_page_containing(
                pages,
                "liquidated damages shall be levied"
            ),
            "evidence": match.group(0)
        }


    return fields