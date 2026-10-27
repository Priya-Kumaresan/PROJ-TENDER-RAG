import re


def detect_sections(pages):
    """
    Detect numbered tender sections from extracted pages.

    Expected headings:
    1. Scope of Work
    2. Eligibility Criteria
    3. Earnest Money Deposit (EMD)
    etc.
    """

    sections = []

    # Matches headings such as:
    # 1. Scope of Work
    # 10. Evaluation Criteria
    heading_pattern = re.compile(
        r"^(\d+)\.\s+(.+)$"
    )

    current_section = None

    for page in pages:

        page_number = page["page_number"]
        text = page["cleaned_text"]

        lines = text.splitlines()

        for line in lines:

            line = line.strip()

            if not line:
                continue

            match = heading_pattern.match(line)

            if match:

                # Save previous section
                if current_section is not None:
                    current_section["text"] = (
                        current_section["text"].strip()
                    )

                    sections.append(
                        current_section
                    )

                # Start new section
                current_section = {
                    "section_number": match.group(1),
                    "section_title": match.group(2),
                    "start_page": page_number,
                    "text": ""
                }

            elif current_section is not None:

                current_section["text"] += (
                    line + " "
                )

    # Save final section
    if current_section is not None:

        current_section["text"] = (
            current_section["text"].strip()
        )

        sections.append(
            current_section
        )

    return sections