"""
Section and Clause Detector (Priority 17)
Detects sections, clauses, and structural divisions in tender PDF text to enrich RAG chunk metadata.
"""

import re


def detect_sections(pages):
    """
    Detect numbered and labeled tender sections from extracted pages.

    Expected heading formats:
    - 1. Scope of Work
    - 1.0 Scope of Work
    - SECTION 1: Invitation for Bids
    - SECTION I - General Conditions of Contract
    - CLAUSE 4.2 - Liquidated Damages
    - PART A: Technical Specifications
    """
    sections = []

    # Comprehensive multi-pattern matcher for tender structural headings
    patterns = [
        # Pattern 1: SECTION / PART / CLAUSE (e.g., "SECTION 1: INVITATION", "Clause 4.2: Liquidated Damages")
        re.compile(r"^(?:SECTION|PART|CLAUSE)\s+([IVXLCDM\d]+(?:\.\d+)?)\s*[:\.\-]?\s+(.+)$", re.IGNORECASE),
        # Pattern 2: Standard numbering (e.g., "1. Scope of Work", "2.0 Eligibility Criteria")
        re.compile(r"^(\d+(?:\.\d+)?)\s*[\.\:\-]\s+([A-Z][^\n]+)$"),
        # Pattern 3: Numbered uppercase headings without punctuation
        re.compile(r"^(\d+)\s+([A-Z\s]{3,50})$")
    ]

    current_section = None

    for page in pages:
        page_number = page.get("page_number", 1)
        text = page.get("cleaned_text") or page.get("raw_text", "")

        lines = text.splitlines()

        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue

            matched = False
            for pattern in patterns:
                m = pattern.match(line_clean)
                if m:
                    sec_num = m.group(1).strip()
                    sec_title = m.group(2).strip()

                    # Save previous section if exists
                    if current_section is not None:
                        current_section["text"] = current_section["text"].strip()
                        sections.append(current_section)

                    # Start new section
                    current_section = {
                        "section_number": sec_num,
                        "section_title": sec_title,
                        "start_page": page_number,
                        "text": ""
                    }
                    matched = True
                    break

            if not matched and current_section is not None:
                current_section["text"] += line_clean + " "

    # Save final section
    if current_section is not None:
        current_section["text"] = current_section["text"].strip()
        sections.append(current_section)

    return sections
