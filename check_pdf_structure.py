from pathlib import Path

from src.extraction.pdf_extractor import extract_pdf


pdf_path = Path(
    "data/raw/tender_001/tender/sample_tender.pdf"
)

data = extract_pdf(pdf_path)


print("=" * 60)
print("PDF STRUCTURE CHECK")
print("=" * 60)

print("\nTop-level keys:")
print(data.keys())


pages = data.get("pages", [])

print("\nNumber of pages:")
print(len(pages))


if pages:

    print("\nFirst page keys:")
    print(pages[0].keys())

    print("\nFirst page complete data:")
    print(pages[0])

else:

    print("\nNo pages found.")