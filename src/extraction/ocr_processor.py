import io

import pymupdf
import pytesseract

from PIL import Image


# Windows Tesseract executable location
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def ocr_page(page):
    """
    Convert a PDF page to an image
    and extract text using Tesseract OCR.
    """

    zoom = 2

    matrix = pymupdf.Matrix(
        zoom,
        zoom
    )

    pixmap = page.get_pixmap(
        matrix=matrix,
        alpha=False
    )

    image_bytes = pixmap.tobytes(
        "png"
    )

    image = Image.open(
        io.BytesIO(image_bytes)
    )

    text = pytesseract.image_to_string(
        image,
        lang="eng"
    )

    return text.strip()