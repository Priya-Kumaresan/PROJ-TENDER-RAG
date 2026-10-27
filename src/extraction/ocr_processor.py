import io

try:
    import pymupdf
except ImportError:
    try:
        import fitz as pymupdf
    except ImportError:
        pymupdf = None

try:
    import pytesseract
    from PIL import Image
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
except ImportError:
    pytesseract = None
    Image = None


def ocr_page(page):
    """
    Convert a PDF page to an image and extract text using Tesseract OCR.
    """
    if pymupdf is None or pytesseract is None or Image is None:
        return ""

    zoom = 2
    matrix = pymupdf.Matrix(zoom, zoom)
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
    image_bytes = pixmap.tobytes("png")
    image = Image.open(io.BytesIO(image_bytes))
    text = pytesseract.image_to_string(image, lang="eng")
    return text.strip()
