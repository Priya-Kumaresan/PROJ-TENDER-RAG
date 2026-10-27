import pymupdf
from pathlib import Path


source_pdf = Path(
    "data/raw/tender_001/sample_tender.pdf"
)

output_folder = Path(
    "data/raw/tender_ocr_test"
)

output_folder.mkdir(
    parents=True,
    exist_ok=True
)

output_pdf = (
    output_folder
    / "scanned_tender.pdf"
)


# Open original PDF
source_document = pymupdf.open(
    source_pdf
)


# Create new PDF
scanned_document = pymupdf.open()


# Use page 2 because it contains
# our tender clauses
page = source_document[1]


# Render page as an image
pixmap = page.get_pixmap(
    matrix=pymupdf.Matrix(2, 2),
    alpha=False
)


# Create a new blank page
new_page = scanned_document.new_page(
    width=page.rect.width,
    height=page.rect.height
)


# Insert the rendered image
new_page.insert_image(
    new_page.rect,
    stream=pixmap.tobytes("png")
)


# Save image-only PDF
scanned_document.save(
    output_pdf
)


source_document.close()
scanned_document.close()


print(
    "OCR test PDF created:",
    output_pdf
)