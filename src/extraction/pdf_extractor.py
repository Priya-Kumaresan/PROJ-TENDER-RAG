from pathlib import Path

try:
    import pymupdf
except ImportError:
    try:
        import fitz as pymupdf
    except ImportError:
        pymupdf = None

try:
    import pypdf
except ImportError:
    pypdf = None

from src.extraction.text_processor import (
    clean_text,
    check_text_quality
)

from src.extraction.ocr_processor import (
    ocr_page
)


def extract_pdf(pdf_path):
    """
    Extract PDF text page-by-page.

    Direct extraction is attempted first.
    OCR is used as a fallback when the extracted
    text appears unreadable.
    """
    pdf_path = Path(pdf_path)
    if pymupdf is None and pypdf is None:
        raise ImportError(
            "Neither PyMuPDF nor pypdf is installed in the active Python environment. "
            "Please install with: pip install pypdf"
        )

    pages = []

    if pymupdf is not None:
        document = pymupdf.open(pdf_path)
        total_pages = len(document)

        for page_index in range(total_pages):
            page = document[page_index]
            raw_text = page.get_text("text")
            quality = check_text_quality(raw_text)

            if quality["is_readable"]:
                final_text = raw_text
                extraction_method = "direct"
                ocr_used = False
            else:
                print(f"Page {page_index + 1}: poor text detected -> running OCR")
                ocr_text = ocr_page(page)
                final_text = ocr_text
                extraction_method = "ocr"
                ocr_used = True

            cleaned_text = clean_text(final_text)
            final_quality = check_text_quality(cleaned_text)

            if ocr_used and final_quality["is_readable"]:
                quality_reason = "OCR extraction successful"
            elif ocr_used:
                quality_reason = "OCR completed but text quality remains poor"
            else:
                quality_reason = final_quality["reason"]

            page_data = {
                "page_number": page_index + 1,
                "raw_text": raw_text.strip(),
                "cleaned_text": cleaned_text,
                "character_count": len(cleaned_text),
                "is_readable": final_quality["is_readable"],
                "quality_reason": quality_reason,
                "ocr_required": not quality["is_readable"],
                "ocr_used": ocr_used,
                "extraction_method": extraction_method
            }
            pages.append(page_data)

        document.close()
    else:
        # Fallback to pure-python pypdf
        reader = pypdf.PdfReader(str(pdf_path))
        total_pages = len(reader.pages)

        for page_index in range(total_pages):
            page = reader.pages[page_index]
            raw_text = page.extract_text() or ""
            cleaned_text = clean_text(raw_text)
            final_quality = check_text_quality(cleaned_text)

            page_data = {
                "page_number": page_index + 1,
                "raw_text": raw_text.strip(),
                "cleaned_text": cleaned_text,
                "character_count": len(cleaned_text),
                "is_readable": final_quality["is_readable"],
                "quality_reason": final_quality["reason"],
                "ocr_required": False,
                "ocr_used": False,
                "extraction_method": "pypdf_direct"
            }
            pages.append(page_data)

    return {
        "file_name": pdf_path.name,
        "total_pages": total_pages,
        "pages": pages
    }
