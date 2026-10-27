def split_text_into_chunks(
    text,
    chunk_size=800,
    overlap=150
):
    """
    Split text into overlapping chunks.

    chunk_size and overlap are measured
    approximately in characters.
    """

    if not text:
        return []

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:

        end = start + chunk_size

        chunk = text[start:end]

        # Try not to cut in the middle
        # of a sentence.
        if end < text_length:

            last_period = chunk.rfind(". ")

            if last_period > chunk_size // 2:
                end = start + last_period + 1
                chunk = text[start:end]

        chunk = chunk.strip()

        if chunk:
            chunks.append(chunk)

        # Stop when the end is reached
        if end >= text_length:
            break

        next_start = end - overlap

        # Safety check
        if next_start <= start:
            next_start = end

        start = next_start

    return chunks


def find_section_for_page(
    page_number,
    sections
):
    """
    Find section metadata associated with
    a particular PDF page.

    Pages appearing before the first detected
    numbered section are classified as
    Tender Information.
    """

    if not sections:

        return {
            "section_number": "INTRO",
            "section_title": "Tender Information"
        }

    matching_section = None

    for section in sections:

        start_page = section.get(
            "start_page",
            1
        )

        if start_page <= page_number:
            matching_section = section

        else:
            break

    if matching_section is None:

        return {
            "section_number": "INTRO",
            "section_title": "Tender Information"
        }

    return {
        "section_number":
            matching_section.get(
                "section_number",
                "UNKNOWN"
            ),

        "section_title":
            matching_section.get(
                "section_title",
                "Unknown Section"
            )
    }


def create_section_chunks(
    pdf_data,
    tender_id
):
    """
    Create page-aware RAG chunks from all
    extracted tender PDF pages.

    Uses cleaned_text produced by the PDF
    extraction pipeline.

    Falls back to raw_text when cleaned_text
    is unavailable.

    Section metadata is preserved where
    possible.
    """

    chunks = []

    pages = pdf_data.get(
        "pages",
        []
    )

    sections = pdf_data.get(
        "sections",
        []
    )

    # ========================================================
    # PAGE-WISE CHUNKING
    # ========================================================

    for page in pages:

        page_number = page.get(
            "page_number",
            1
        )

        # ----------------------------------------------------
        # IMPORTANT:
        # pdf_extractor.py stores extracted text as
        # "cleaned_text" and "raw_text".
        # ----------------------------------------------------

        page_text = page.get(
            "cleaned_text",
            ""
        )

        # Fallback to raw extracted text
        if not page_text:

            page_text = page.get(
                "raw_text",
                ""
            )

        # Skip genuinely empty pages
        if not page_text:
            continue

        # ----------------------------------------------------
        # Determine section metadata
        # ----------------------------------------------------

        section_info = find_section_for_page(
            page_number,
            sections
        )

        # ----------------------------------------------------
        # Split page into chunks
        # ----------------------------------------------------

        text_chunks = split_text_into_chunks(
            page_text
        )

        # ----------------------------------------------------
        # Create structured RAG chunks
        # ----------------------------------------------------

        for index, chunk_text in enumerate(
            text_chunks,
            start=1
        ):

            chunk_id = (
                f"{tender_id}_"
                f"page_{page_number}_"
                f"chunk_{index}"
            )

            chunk_data = {

                "chunk_id":
                    chunk_id,

                "tender_id":
                    tender_id,

                "section_number":
                    section_info[
                        "section_number"
                    ],

                "section_title":
                    section_info[
                        "section_title"
                    ],

                "page_number":
                    page_number,

                "chunk_index":
                    index,

                "text":
                    chunk_text
            }

            chunks.append(
                chunk_data
            )

    return chunks