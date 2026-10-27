"""
Section and Clause Detector
Detects authentic sections, clauses, and structural divisions in tender PDF text to enrich RAG chunk metadata.
"""

import re
from typing import Any, Dict, List


def detect_sections(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detect genuine tender sections from extracted pages.
    First checks for an explicit Index / Table of Contents in the opening pages.
    Falls back to structural heading detection while filtering out false-positive bullet lists.
    """
    sections = []

    # 1. Strategy A: Check for structured Index / Table of Contents in the first 5 pages
    for page in pages[:5]:
        raw_text = page.get("raw_text") or page.get("cleaned_text", "")
        if "index" in raw_text.lower() or "table of contents" in raw_text.lower():
            # Pattern matching: Item_Number \n Details \n Page_From \n Page_To
            index_matches = re.findall(
                r"(\d+)\s*\n([^\n]+?)\s*\n(\d+)\s*\n(\d+)",
                raw_text
            )
            if len(index_matches) >= 3:
                page_texts = {
                    p.get("page_number", idx + 1): p.get("cleaned_text") or p.get("raw_text", "")
                    for idx, p in enumerate(pages)
                }

                for item in index_matches:
                    sec_num = item[0].strip()
                    raw_title = item[1].strip()
                    # Clean out replacement / artifact characters
                    clean_title = raw_title.replace("\ufffd", '"')
                    clean_title = re.sub(r"[\u2013\u2014]+", "-", clean_title)
                    clean_title = re.sub(r"\s+", " ", clean_title).strip()

                    try:
                        from_page = int(item[2].strip())
                        to_page = int(item[3].strip())
                    except ValueError:
                        from_page = 1
                        to_page = 1

                    # Collect text across the section's page range
                    sec_text_parts = [
                        page_texts.get(p_num, "")
                        for p_num in range(from_page, to_page + 1)
                    ]
                    sec_text = " ".join(sec_text_parts).strip()

                    sections.append({
                        "section_number": sec_num,
                        "section_title": clean_title,
                        "title": clean_title,
                        "start_page": from_page,
                        "end_page": to_page,
                        "char_count": len(sec_text),
                        "text": sec_text
                    })

                if sections:
                    return sections

    # 2. Strategy B: Pattern-based structural heading detection
    # Only match true structural section headings, NOT bulleted sentences
    structural_patterns = [
        # SECTION I - ... / PART 2: ... / CLAUSE 4.2: ...
        re.compile(r"^(?:SECTION|PART|CLAUSE|SCHEDULE|CHAPTER|ANNEXURE)\s+([IVXLCDM\d]+(?:\.\d+)?)\s*[:\.\-]?\s+(.+)$", re.IGNORECASE),
        # All-caps structural headers: 1. NOTICE INVITING TENDER, etc.
        re.compile(r"^(\d+(?:\.\d+)?)\s*[\.\:\-]\s+([A-Z\s\(\)\/\-]{4,60})$")
    ]

    # Filter out common bullet sentence starters (e.g. declarations, undertakings, legal disclaimers)
    bullet_starters = [
        "i am", "i / we", "we hereby", "the contractor", "if the", "in case",
        "for the", "no contractor", "all work", "the tender", "it is", "signature"
    ]

    current_section = None

    for page in pages:
        page_number = page.get("page_number", 1)
        text = page.get("cleaned_text") or page.get("raw_text", "")
        lines = text.splitlines()

        for line in lines:
            line_clean = line.strip()
            if not line_clean or len(line_clean) < 4:
                continue

            # Check if this line is a bulleted body sentence
            low_line = line_clean.lower()
            if any(low_line.startswith(starter) for starter in bullet_starters):
                if current_section is not None:
                    current_section["text"] += line_clean + " "
                continue

            matched = False
            for pattern in structural_patterns:
                m = pattern.match(line_clean)
                if m:
                    sec_num = m.group(1).strip()
                    sec_title = m.group(2).strip()

                    # Avoid capturing long sentences
                    if len(sec_title.split()) > 10:
                        continue

                    # Save previous section if exists
                    if current_section is not None:
                        current_section["text"] = current_section["text"].strip()
                        current_section["char_count"] = len(current_section["text"])
                        sections.append(current_section)

                    # Start new section
                    current_section = {
                        "section_number": sec_num,
                        "section_title": sec_title,
                        "title": sec_title,
                        "start_page": page_number,
                        "char_count": 0,
                        "text": ""
                    }
                    matched = True
                    break

            if not matched and current_section is not None:
                current_section["text"] += line_clean + " "

    # Save final section
    if current_section is not None:
        current_section["text"] = current_section["text"].strip()
        current_section["char_count"] = len(current_section["text"])
        sections.append(current_section)

    return sections
