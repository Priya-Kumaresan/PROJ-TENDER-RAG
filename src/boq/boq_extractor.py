import pandas as pd
import re


def normalize_column_name(column):
    """
    Normalize different BOQ column headings.

    Examples:
        Item No.       -> item_no
        Description    -> description
        Qty            -> quantity
        Rate (INR)     -> rate
        Amount (INR)   -> amount
        GST %          -> gst
    """

    column = str(column).strip().lower()

    # Remove bracketed text such as (INR)
    column = re.sub(r"\([^)]*\)", "", column)

    # Remove / replace special characters
    column = column.replace("%", "")
    column = column.replace(".", "")
    column = column.replace("-", " ")
    column = column.replace("/", " ")

    # Spaces -> underscore
    column = re.sub(r"\s+", "_", column)
    column = column.strip("_")

    mapping = {
        # Item number
        "item_no": "item_no",
        "item_number": "item_no",
        "item": "item_no",
        "sl_no": "item_no",
        "s_no": "item_no",
        "serial_no": "item_no",
        "sr_no": "item_no",

        # Description
        "description": "description",
        "item_description": "description",
        "description_of_item": "description",
        "description_of_work": "description",

        # Unit
        "unit": "unit",
        "uom": "unit",
        "unit_of_measurement": "unit",

        # Quantity
        "quantity": "quantity",
        "qty": "quantity",

        # Rate
        "rate": "rate",
        "unit_rate": "rate",
        "quoted_rate": "rate",

        # Amount
        "amount": "amount",
        "total_amount": "amount",
        "quoted_amount": "amount",

        # GST
        "gst": "gst",
        "gst_rate": "gst",
        "gst_percentage": "gst",
    }

    return mapping.get(column, column)


def find_header_row(excel_path, max_rows=30):
    """
    Find the row containing the actual BOQ table headings.

    This allows Excel files to contain title rows before
    Item No / Description / Quantity / Rate / Amount.
    """

    preview = pd.read_excel(
        excel_path,
        header=None,
        nrows=max_rows
    )

    best_row = None
    best_score = 0

    keywords = {
        "item",
        "description",
        "quantity",
        "qty",
        "unit",
        "uom",
        "rate",
        "amount",
        "gst"
    }

    for row_index, row in preview.iterrows():

        score = 0

        for value in row:

            if pd.isna(value):
                continue

            text = str(value).strip().lower()

            # Clean text for comparison
            text = re.sub(r"[^a-z0-9]+", " ", text)

            words = set(text.split())

            if words.intersection(keywords):
                score += 1

        if score > best_score:
            best_score = score
            best_row = row_index

    # Require at least 3 recognizable BOQ headings
    if best_row is None or best_score < 3:
        raise ValueError(
            "Could not automatically locate the BOQ header row. "
            "Expected headings such as Item No, Description, "
            "Quantity, Rate and Amount."
        )

    return best_row


def extract_boq(excel_path):

    print("\n--------------------------------")
    print("Reading BOQ:")
    print(excel_path)
    print("--------------------------------")

    # --------------------------------------------------
    # STEP 1: Automatically locate actual table header
    # --------------------------------------------------

    header_row = find_header_row(excel_path)

    print(f"Detected BOQ header row: {header_row + 1}")

    # --------------------------------------------------
    # STEP 2: Read Excel using detected header
    # --------------------------------------------------

    df = pd.read_excel(
        excel_path,
        header=header_row
    )

    print("\nOriginal BOQ columns:")
    print(df.columns.tolist())

    # --------------------------------------------------
    # STEP 3: Normalize headings
    # --------------------------------------------------

    df.columns = [
        normalize_column_name(column)
        for column in df.columns
    ]

    print("\nNormalized BOQ columns:")
    print(df.columns.tolist())

    # --------------------------------------------------
    # STEP 4: Check required columns
    # --------------------------------------------------

    required_columns = [
        "item_no",
        "description",
        "unit",
        "quantity",
        "rate",
        "amount"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "BOQ is missing required columns: "
            + ", ".join(missing_columns)
            + "\nDetected columns: "
            + ", ".join(map(str, df.columns))
        )

    # GST is optional
    if "gst" not in df.columns:
        df["gst"] = None

    # --------------------------------------------------
    # STEP 5: Keep required BOQ columns
    # --------------------------------------------------

    df = df[
        [
            "item_no",
            "description",
            "unit",
            "quantity",
            "rate",
            "amount",
            "gst"
        ]
    ].copy()

    # --------------------------------------------------
    # STEP 6: Remove empty rows
    # --------------------------------------------------

    df = df.dropna(how="all")

    # Require an item number and description
    df = df[
        df["item_no"].notna()
        & df["description"].notna()
    ]

    # --------------------------------------------------
    # STEP 7: Convert numeric values
    # --------------------------------------------------

    numeric_columns = [
        "quantity",
        "rate",
        "amount",
        "gst"
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # --------------------------------------------------
    # STEP 8: Reset index
    # --------------------------------------------------

    df = df.reset_index(drop=True)

    print(f"\nBOQ items extracted: {len(df)}")

    return df