"""
Unit test for BOQ extraction and formula/number resolution.
Verifies that:
1. Comma-formatted strings and currency prefixes are converted safely.
2. Excel formulas are evaluated based on workbook cell references when cached values are absent.
3. Intentionally mismatched amounts are preserved so validator detects them.
4. Genuine missing amounts remain None / NaN.
"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.boq.boq_extractor import (
    clean_numeric_value,
    evaluate_cell_formula,
    normalize_column_name,
)
from src.boq.boq_validator import validate_boq

try:
    import pandas as pd
except ImportError:
    pd = None


class MockCell:
    def __init__(self, value):
        self.value = value


def test_clean_numeric_value():
    print("Testing clean_numeric_value...")
    assert clean_numeric_value(100) == 100.0
    assert clean_numeric_value(450.5) == 450.5
    assert clean_numeric_value("45,000") == 45000.0
    assert clean_numeric_value("2,50,000") == 250000.0
    assert clean_numeric_value("INR 45,000") == 45000.0
    assert clean_numeric_value("₹ 6,37,500.00") == 637500.0
    assert clean_numeric_value("45000/-") == 45000.0
    assert clean_numeric_value(None) is None
    assert clean_numeric_value("") is None
    assert clean_numeric_value("   ") is None
    print("✓ clean_numeric_value passed all tests.")


def test_normalize_column_name():
    print("\nTesting normalize_column_name...")
    assert normalize_column_name("Item No.") == "item_no"
    assert normalize_column_name("Sl. No.") == "item_no"
    assert normalize_column_name("Description of Item") == "description"
    assert normalize_column_name("Qty") == "quantity"
    assert normalize_column_name("Unit Rate (INR)") == "rate"
    assert normalize_column_name("Amount (INR)") == "amount"
    assert normalize_column_name("Total Price") == "amount"
    assert normalize_column_name("Total Quoted Amount") == "amount"
    assert normalize_column_name("GST %") == "gst"
    print("✓ normalize_column_name passed all tests.")


def test_formula_evaluation():
    print("\nTesting formula evaluation...")
    mock_sheet = {
        "D5": MockCell(100),
        "E5": MockCell(450),
        "D6": MockCell(50),
        "E6": MockCell("5,000"),
        "D7": MockCell(120),
        "E7": MockCell(6000),
    }

    # Item 1: D5 * E5 = 100 * 450 = 45000
    res1 = evaluate_cell_formula("=D5*E5", mock_sheet)
    assert res1 == 45000.0, f"Expected 45000, got {res1}"

    # Item 2: D6 * E6 = 50 * 5,000 = 250000
    res2 = evaluate_cell_formula("=D6*E6", mock_sheet)
    assert res2 == 250000.0, f"Expected 250000, got {res2}"

    # PRODUCT function
    res3 = evaluate_cell_formula("=PRODUCT(D5, E5)", mock_sheet)
    assert res3 == 45000.0, f"Expected 45000, got {res3}"

    # Formula with discrepancy: =D5*E5 + 3000 -> 48000
    res_disc = evaluate_cell_formula("=D5*E5 + 3000", mock_sheet)
    assert res_disc == 48000.0, f"Expected 48000, got {res_disc}"

    print("✓ Formula evaluation passed all tests.")


def test_validation_integrity():
    print("\nTesting validator integrity with extracted values...")
    # Test items:
    # 1. Valid (100 * 450 = 45000)
    # 2. Arithmetic Mismatch (50 * 5000 = 250000, but amount quoted is 260000)
    # 3. Missing Amount (Quantity = 1000, Rate = 250, Amount = None)
    raw_items = [
        {
            "item_no": "1",
            "description": "Excavation",
            "quantity": 100.0,
            "rate": 450.0,
            "amount": 45000.0,
            "gst": 18.0
        },
        {
            "item_no": "2",
            "description": "PCC",
            "quantity": 50.0,
            "rate": 5000.0,
            "amount": 260000.0,  # Mismatched on purpose
            "gst": 18.0
        },
        {
            "item_no": "3",
            "description": "Plastering",
            "quantity": 1000.0,
            "rate": 250.0,
            "amount": None,      # Genuine missing amount
            "gst": 18.0
        }
    ]

    data = pd.DataFrame(raw_items) if pd is not None else raw_items

    results = validate_boq(data)
    assert len(results) == 3

    # Item 1 should be VALID
    assert results[0]["status"] == "VALID"
    assert len(results[0]["issues"]) == 0

    # Item 2 should have Amount mismatch
    assert results[1]["status"] == "ISSUE"
    assert "Amount mismatch" in results[1]["issues"]

    # Item 3 should have Missing amount
    assert results[2]["status"] == "ISSUE"
    assert "Missing amount" in results[2]["issues"]

    print("✓ Validation integrity confirmed:")
    print("  - Item 1 (Valid): VALID")
    print("  - Item 2 (Arithmetic Mismatch): Flagged with 'Amount mismatch'")
    print("  - Item 3 (Missing Amount): Flagged with 'Missing amount'")


if __name__ == "__main__":
    print("=" * 60)
    print("BOQ EXTRACTION & FORMULA RESOLUTION TEST")
    print("=" * 60)
    test_clean_numeric_value()
    test_normalize_column_name()
    test_formula_evaluation()
    test_validation_integrity()
    print("\n" + "=" * 60)
    print("ALL BOQ TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)
