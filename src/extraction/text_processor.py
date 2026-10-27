import re


def clean_text(text):
    """
    Clean extracted PDF text without destroying
    important tender information.
    """

    if not text:
        return ""

    # Remove null characters
    text = text.replace("\x00", "")

    # Replace tabs with spaces
    text = text.replace("\t", " ")

    # Replace multiple spaces with one space
    text = re.sub(r"[ ]+", " ", text)

    # Remove excessive blank lines
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    return text.strip()


def check_text_quality(text):
    """
    Decide whether directly extracted PDF text
    is usable or whether OCR may be required.
    """

    if not text:
        return {
            "is_readable": False,
            "reason": "No text extracted"
        }

    cleaned = text.strip()

    # Very little text often indicates a scanned page
    if len(cleaned) < 50:
        return {
            "is_readable": False,
            "reason": "Very little text extracted"
        }

    # Count alphabetic characters
    alphabetic_count = sum(
        char.isalpha()
        for char in cleaned
    )

    alphabetic_ratio = (
        alphabetic_count / len(cleaned)
    )

    # Extremely low alphabetic content may indicate
    # extraction failure or corrupted text
    if alphabetic_ratio < 0.30:
        return {
            "is_readable": False,
            "reason": "Low readable-text ratio"
        }

    return {
        "is_readable": True,
        "reason": "Direct extraction successful"
    }