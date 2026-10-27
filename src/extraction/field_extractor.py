import re


def find_page_containing(pages, search_text):
    """
    Find which page contains a piece of text.
    """
    search_text = search_text.lower()

    for page in pages:
        text = page.get("cleaned_text", "").lower()
        if not text:
            text = page.get("raw_text", "").lower()

        if search_text in text:
            return page.get("page_number")

    return None


def extract_tender_fields(pdf_data):
    """
    Extract important structured tender fields
    using simple rules and regular expressions.
    """
    pages = pdf_data.get("pages", [])

    # Combine all page text
    full_text = "\n".join(
        page.get("cleaned_text") or page.get("raw_text", "")
        for page in pages
    )

    fields = {}

    # -----------------------------------
    # Tender Number
    # -----------------------------------
    match = re.search(
        r"(?:Tender\s*No\.?|NIT\s*No\.?|Tender\s+Reference|Tender\s+Notice\s+No\.?)\s*[:\.]?\s*([A-Za-z0-9\/\(\)\-_]+)",
        full_text,
        re.IGNORECASE
    )
    if match:
        value = match.group(1).strip()
        fields["tender_number"] = {
            "value": value,
            "page": find_page_containing(pages, value),
            "evidence": match.group(0)
        }

    # -----------------------------------
    # Organisation
    # -----------------------------------
    match = re.search(
        r"(?:Organisation\s*:\s*([^\n]+)|(BHARAT\s+SANCHAR\s+NIGAM\s+LIMITED|CENTRAL\s+PUBLIC\s+WORKS\s+DEPARTMENT|INDIAN\s+INSTITUTE\s+OF\s+TECHNOLOGY|MILITARY\s+ENGINEER\s+SERVICES))",
        full_text,
        re.IGNORECASE
    )
    if match:
        value = (match.group(1) or match.group(2)).strip()
        fields["organisation"] = {
            "value": value,
            "page": find_page_containing(pages, value),
            "evidence": match.group(0)
        }

    # -----------------------------------
    # Project Name
    # -----------------------------------
    match = re.search(
        r"(?:Project\s*:\s*([^\n]+)|(?:Name\s+of\s+work\s*:\s*|For\s+the\s+work\s+of\s*)([^\n\r]+))",
        full_text,
        re.IGNORECASE
    )
    if match:
        value = (match.group(1) or match.group(2)).strip()
        fields["project_name"] = {
            "value": value,
            "page": find_page_containing(pages, value),
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
            "page": find_page_containing(pages, value),
            "evidence": match.group(0)
        }

    # -----------------------------------
    # EMD (Earnest Money Deposit)
    # -----------------------------------
    match = re.search(
        r"(?:Earnest\s+Money(?:\s+Deposit)?|EMD)\s*(?:of|is)?\s*[:\.]?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d+)?)(?:\s*/-)?",
        full_text,
        re.IGNORECASE
    )
    if match:
        raw_val = match.group(1).strip()
        value = f"INR {raw_val}" if not raw_val.startswith("INR") else raw_val
        fields["emd"] = {
            "value": value,
            "page": find_page_containing(pages, raw_val),
            "evidence": match.group(0)[:500]
        }

    # -----------------------------------
    # Performance Security
    # -----------------------------------
    match = re.search(
        r"(?:Performance\s+Security|Performance\s+Guarantee)\s*(?:equal\s+to|@|\()?\s*(\d+(?:\.\d+)?\s*%)",
        full_text,
        re.IGNORECASE
    )
    if match:
        value = match.group(1).strip()
        fields["performance_security"] = {
            "value": value,
            "page": find_page_containing(pages, value),
            "evidence": match.group(0)
        }

    # -----------------------------------
    # Completion Period
    # -----------------------------------
    match = re.search(
        r"(?:completed\s+within|time\s+allowed\s+for.*?work.*?will\s+be|Time allowed for execution of work\.|Time\s*:)\s*([0-9]+\s*(?:\([A-Za-z]+\))?\s*months?)",
        full_text,
        re.IGNORECASE
    )
    if match:
        value = match.group(1).strip()
        fields["completion_period"] = {
            "value": value,
            "page": find_page_containing(pages, value),
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
            "page": find_page_containing(pages, "liquidated damages shall be levied"),
            "evidence": match.group(0)
        }

    # -----------------------------------
    # Minimum Technical Score / Qualification Threshold
    # -----------------------------------
    match = re.search(
        r"(?:minimum\s+technical\s+score|mandatory\s+technical\s+(?:qualification\s+)?score|qualifying\s+technical\s+score)"
        r"\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:marks|points|%|percent)?",
        full_text,
        re.IGNORECASE
    )
    if match:
        value = match.group(1).strip()
        fields["min_technical_score"] = {
            "value": value,
            "page": find_page_containing(pages, match.group(0)),
            "evidence": match.group(0)
        }

    # -----------------------------------
    # Technical Weightage
    # -----------------------------------
    match = re.search(
        r"(?:technical\s+weightage|technical\s+weight|weightage\s+for\s+technical)"
        r"\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:%|percent)?",
        full_text,
        re.IGNORECASE
    )
    if match:
        value = match.group(1).strip()
        fields["technical_weightage"] = {
            "value": value,
            "page": find_page_containing(pages, match.group(0)),
            "evidence": match.group(0)
        }

    # -----------------------------------
    # Financial Weightage
    # -----------------------------------
    match = re.search(
        r"(?:financial\s+weightage|financial\s+weight|commercial\s+weightage|weightage\s+for\s+financial)"
        r"\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:%|percent)?",
        full_text,
        re.IGNORECASE
    )
    if match:
        value = match.group(1).strip()
        fields["financial_weightage"] = {
            "value": value,
            "page": find_page_containing(pages, match.group(0)),
            "evidence": match.group(0)
        }

    # -----------------------------------
    # Estimated Project Value
    # -----------------------------------
    match = re.search(
        r"(?:estimated\s+(?:project\s+)?(?:cost|value)|approximate\s+cost|tender\s+value)"
        r"\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?\s*(?:crores?|cr|lakhs?|lac|lacs)?)",
        full_text,
        re.IGNORECASE
    )
    if match:
        value = match.group(1).strip()
        fields["estimated_value"] = {
            "value": value,
            "page": find_page_containing(pages, match.group(0)),
            "evidence": match.group(0)
        }

    # -----------------------------------
    # Submission Deadline
    # -----------------------------------
    match = re.search(
        r"(?:submission\s+deadline|last\s+date\s+(?:and\s+time\s+)?of\s+submission|bid\s+submission\s+date)"
        r"\s*[:\-]?\s*([^\n]+)",
        full_text,
        re.IGNORECASE
    )
    if match:
        value = match.group(1).strip()
        fields["submission_deadline"] = {
            "value": value,
            "page": find_page_containing(pages, match.group(0)),
            "evidence": match.group(0)
        }

    return fields
