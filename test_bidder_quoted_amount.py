"""
Unit test for Bidder B quoted amount extraction and currency normalization.
Verifies that:
1. Bidder B financial proposal variations are matched accurately by bidder_field_extractor.py.
2. Crores / Lakhs / standard rupee currency formats normalize to accurate numeric values.
3. Financial ratio between Bidder B (4.65 Cr) and Bidder A (4.82 Cr) yields 96.47.
"""
import sys
from src.extraction.bidder_field_extractor import extract_bidder_fields
from src.comparison.normalizer import normalize_currency, normalize_field
from src.comparison.bid_comparator import normalize_currency as comparator_normalize_currency

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def test_extraction_variations():
    print("Testing extract_bidder_fields for quoted amount...")

    cases = [
        ("Total Quoted Bid Amount: INR 4,65,00,000", "INR 4,65,00,000"),
        ("Total Quoted Bid Amount: INR 4.65 crore", "INR 4.65 crore"),
        ("Total Bid Amount: INR 4,65,00,000/-", "INR 4,65,00,000"),
        ("Total Contract Price: ₹ 4,65,00,000", "INR 4,65,00,000"),
        ("Total Quoted Amount for the Project is INR 4,65,00,000", "INR 4,65,00,000"),
        ("Total Bid: INR 4.65 crore", "INR 4.65 crore"),
    ]

    for text_sample, expected_val in cases:
        mock_pdf_data = {
            "pages": [
                {
                    "page_number": 1,
                    "cleaned_text": f"Proposal Submission.\n{text_sample}\nCompany Registration: BETA-REG-2019-332\nCompletion: 15 months\nTechnical score: 88\nPerformance security: 10%\nEMD: INR 5,00,000"
                }
            ]
        }

        fields = extract_bidder_fields(mock_pdf_data, "Beta Infrastructure Ltd")
        extracted_quote = fields.get("total_quoted_amount", {}).get("value")

        assert extracted_quote is not None, f"Failed to extract quote from: '{text_sample}'"
        assert extracted_quote.strip() == expected_val.strip(), (
            f"Expected '{expected_val}', got '{extracted_quote}' for '{text_sample}'"
        )

    print("✓ All quoted amount text variations extracted successfully.")


def test_currency_normalization():
    print("\nTesting normalize_currency across standard and Indian formats...")

    # Both INR 4,65,00,000 and INR 4.65 crore must yield 46,500,000.0
    val1 = normalize_currency("INR 4,65,00,000")
    val2 = normalize_currency("INR 4.65 crore")
    val3 = normalize_currency("INR 4.65 Cr")
    val4 = normalize_currency("₹ 4,65,00,000")

    assert val1 == 46500000.0, f"Expected 46500000.0, got {val1}"
    assert val2 == 46500000.0, f"Expected 46500000.0, got {val2}"
    assert val3 == 46500000.0, f"Expected 46500000.0, got {val3}"
    assert val4 == 46500000.0, f"Expected 46500000.0, got {val4}"

    # Bidder A: 4.82 Cr
    val_a = normalize_currency("INR 4.82 crore")
    assert val_a == 48200000.0, f"Expected 48200000.0, got {val_a}"

    # Verify comparator_normalize_currency in bid_comparator.py
    comp_val = comparator_normalize_currency("INR 4.65 crore")
    assert comp_val == 46500000.0, f"Expected 46500000.0, got {comp_val}"

    # Verify normalize_field dispatcher
    field_dict = {"value": "INR 4.65 crore", "page": 1}
    norm_field = normalize_field("total_quoted_amount", field_dict)
    assert norm_field == 46500000.0, f"Expected 46500000.0, got {norm_field}"

    # Verify Financial Score formula: (Lowest Bid / Bidder Bid) * 100
    # Bidder B is lowest (4.65 Cr), Bidder A is 4.82 Cr
    score_b = (val2 / val2) * 100
    score_a = (val2 / val_a) * 100

    assert round(score_b, 2) == 100.00
    assert round(score_a, 2) == 96.47, f"Expected 96.47, got {round(score_a, 2)}"

    print("✓ Currency normalization confirmed:")
    print(f"  - Bidder B (4.65 Cr) normalized: {val2:,.0f}")
    print(f"  - Bidder A (4.82 Cr) normalized: {val_a:,.0f}")
    print(f"  - Bidder B Financial Score: {score_b:.2f}")
    print(f"  - Bidder A Financial Score: {score_a:.2f}")


if __name__ == "__main__":
    print("=" * 60)
    print("BIDDER B QUOTED AMOUNT VERIFICATION TEST")
    print("=" * 60)
    test_extraction_variations()
    test_currency_normalization()
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

