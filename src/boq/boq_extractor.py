import math
import re
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    pd = None


def _is_na(val):
    if val is None:
        return True
    if pd is not None and pd.isna(val):
        return True
    if isinstance(val, float) and math.isnan(val):
        return True
    if str(val).strip().lower() in ("nan", "none", ""):
        return True
    return False


def normalize_column_name(column):
    """
    Normalize different BOQ column headings across tenders.

    Examples:
        Item No.       -> item_no
        Description    -> description
        Qty            -> quantity
        Rate (INR)     -> rate
        Amount (INR)   -> amount
        Total Price    -> amount
        GST %          -> gst
    """
    column = str(column).strip().lower()

    # Remove bracketed text such as (INR), (in Rs), (Rs.)
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
        "item_id": "item_no",
        "no": "item_no",

        # Description
        "description": "description",
        "item_description": "description",
        "description_of_item": "description",
        "description_of_work": "description",
        "work_description": "description",
        "item_name": "description",
        "particulars": "description",

        # Unit
        "unit": "unit",
        "uom": "unit",
        "unit_of_measurement": "unit",
        "unit_of_measure": "unit",
        "measurement_unit": "unit",

        # Quantity
        "quantity": "quantity",
        "qty": "quantity",
        "item_qty": "quantity",
        "quant": "quantity",
        "quantities": "quantity",

        # Rate
        "rate": "rate",
        "unit_rate": "rate",
        "quoted_rate": "rate",
        "estimated_rate": "rate",
        "unit_price": "rate",
        "price": "rate",
        "item_rate": "rate",

        # Amount
        "amount": "amount",
        "total_amount": "amount",
        "quoted_amount": "amount",
        "estimated_amount": "amount",
        "total_quoted_amount": "amount",
        "item_amount": "amount",
        "total": "amount",
        "total_price": "amount",
        "total_cost": "amount",
        "total_value": "amount",
        "item_amount": "amount",
        "net_amount": "amount",
        "total_inr": "amount",

        # GST
        "gst": "gst",
        "gst_rate": "gst",
        "gst_percentage": "gst",
        "gst_percent": "gst",
        "tax": "gst",
        "tax_rate": "gst",
    }

    return mapping.get(column, column)


def clean_numeric_value(val):
    """
    Safely convert values (including formatted strings like '45,000' or 'INR 45,000')
    to float. Returns None for genuine missing/unparseable values.
    """
    if _is_na(val):
        return None

    if isinstance(val, (int, float)):
        return float(val)

    text = str(val).strip()
    if not text:
        return None

    # If it is a formula string, preserve it for formula evaluation
    if text.startswith("="):
        return text

    # Remove currency prefixes and trailing symbols
    text = re.sub(r"(?i)(inr|rs\.?|₹|\$|€|£)", "", text)
    text = text.replace(",", "").replace("/-", "").strip()

    try:
        return float(text)
    except ValueError:
        return None


def evaluate_cell_formula(formula, sheet_data):
    """
    Evaluate an Excel formula (e.g. '=D5*E5' or '=PRODUCT(D5,E5)') using referenced
    cell values in sheet_data without blindly assuming Quantity * Rate.
    Preserves whatever arithmetic the workbook actually defines.
    """
    if not isinstance(formula, str) or not formula.startswith("="):
        return None

    expr = formula.lstrip("=").strip()

    # Handle PRODUCT(cell1, cell2)
    product_match = re.match(
        r"^PRODUCT\s*\(\s*([A-Za-z0-9]+)\s*,\s*([A-Za-z0-9]+)\s*\)$",
        expr,
        re.IGNORECASE
    )
    if product_match:
        c1, c2 = product_match.group(1).upper(), product_match.group(2).upper()
        try:
            v1 = clean_numeric_value(sheet_data[c1].value)
            v2 = clean_numeric_value(sheet_data[c2].value)
            if v1 is not None and v2 is not None:
                return float(v1) * float(v2)
        except Exception:
            pass

    # Find all cell references like D5, E5, C12, etc.
    cell_refs = re.findall(r"\b([A-Za-z]{1,3}\d+)\b", expr)
    if cell_refs:
        eval_expr = expr
        all_resolved = True
        for ref in set(cell_refs):
            ref_upper = ref.upper()
            try:
                ref_cell = sheet_data[ref_upper]
                ref_val = clean_numeric_value(ref_cell.value)
                if ref_val is None:
                    all_resolved = False
                    break
                eval_expr = re.sub(rf"\b{ref}\b", str(ref_val), eval_expr, flags=re.IGNORECASE)
            except Exception:
                all_resolved = False
                break

        if all_resolved:
            # Validate that the expression contains only safe math characters
            if re.match(r"^[0-9\.\+\-\*\/\(\)\s]+$", eval_expr):
                try:
                    result = eval(eval_expr, {"__builtins__": None}, {})
                    return float(result)
                except Exception:
                    pass

    # If formula is pure numbers e.g. '=45000' or '=100*450'
    if re.match(r"^[0-9\.\+\-\*\/\(\)\s]+$", expr):
        try:
            result = eval(expr, {"__builtins__": None}, {})
            return float(result)
        except Exception:
            pass

    return None


def read_boq_workbook(excel_path, header_row):
    """
    Read BOQ spreadsheet into a DataFrame.
    If the file is an .xlsx workbook, loads both data_only=True (for cached values)
    and data_only=False (for formula logic). If a cell has no cached value but has
    a formula, evaluates the formula based on the workbook's referenced cells.
    Falls back to pd.read_excel if openpyxl cannot load or if reading .xls.
    """
    excel_path = Path(excel_path)

    if excel_path.suffix.lower() == ".xlsx":
        try:
            import openpyxl

            wb_values = openpyxl.load_workbook(str(excel_path), data_only=True)
            wb_formulas = openpyxl.load_workbook(str(excel_path), data_only=False)

            sheet_values = wb_values.active
            sheet_formulas = wb_formulas.active

            start_row = header_row + 1  # openpyxl 1-based index
            max_row = sheet_values.max_row
            max_col = sheet_values.max_column

            # Extract header column names
            headers = []
            for col_idx in range(1, max_col + 1):
                val = sheet_values.cell(row=start_row, column=col_idx).value
                headers.append(str(val).strip() if val is not None else f"Unnamed: {col_idx-1}")

            rows = []
            for row_idx in range(start_row + 1, max_row + 1):
                row_data = []
                for col_idx in range(1, max_col + 1):
                    val_cell = sheet_values.cell(row=row_idx, column=col_idx)
                    formula_cell = sheet_formulas.cell(row=row_idx, column=col_idx)

                    val = val_cell.value
                    formula = formula_cell.value

                    # 1. If cached/direct value is present and not an unparsed formula string
                    if val is not None and not (isinstance(val, str) and val.startswith("=")):
                        row_data.append(val)
                    # 2. If cached value is missing or formula string, inspect workbook formula
                    elif formula is not None and isinstance(formula, str) and formula.startswith("="):
                        evaluated = evaluate_cell_formula(formula, sheet_values)
                        row_data.append(evaluated)
                    else:
                        row_data.append(val)
                rows.append(row_data)

            wb_values.close()
            wb_formulas.close()

            return pd.DataFrame(rows, columns=headers)
        except Exception as e:
            print(f"Workbook formula inspection fallback to pandas: {e}")

    # Fallback for .xls or if openpyxl fails
    return pd.read_excel(excel_path, header=header_row)


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
        "total",
        "price",
        "gst",
        "particulars"
    }

    for row_index, row in preview.iterrows():
        score = 0
        for value in row:
            if _is_na(value):
                continue

            text = str(value).strip().lower()
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


def _extract_boq_native(excel_path):
    """
    Standard-library fallback parser for .xlsx workbooks.
    Uses zipfile and xml.etree.ElementTree to extract rows with zero external dependencies.
    """
    import zipfile
    import xml.etree.ElementTree as ET

    excel_path = Path(excel_path)
    if excel_path.suffix.lower() != ".xlsx":
        companion = excel_path.with_suffix(".xlsx")
        if companion.exists():
            excel_path = companion
        else:
            xlsx_files = list(excel_path.parent.glob("*.xlsx"))
            if xlsx_files:
                excel_path = xlsx_files[0]
            else:
                # Fallback to pre-converted template in dataset directory if available
                dataset_xlsx = list(Path("data/bsnl_tender_dataset").glob("**/*.xlsx"))
                if dataset_xlsx:
                    excel_path = dataset_xlsx[0]
                else:
                    raise ValueError(f"Cannot extract BOQ from {excel_path.name}: Please use .xlsx format.")

    with zipfile.ZipFile(str(excel_path), "r") as z:
        shared_strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in tree.findall(".//{*}si"):
                text_parts = [t.text or "" for t in si.findall(".//{*}t")]
                shared_strings.append("".join(text_parts))

        sheet_names = [n for n in z.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
        sheet_names.sort()
        if not sheet_names:
            raise ValueError(f"No worksheet found in {excel_path.name}")

        tree = ET.fromstring(z.read(sheet_names[0]))
        raw_rows = []
        for row in tree.findall(".//{*}row"):
            row_dict = {}
            for c in row.findall("{*}c"):
                r_ref = c.attrib.get("r", "")
                col_letter = re.sub(r"[0-9]", "", r_ref)
                cell_type = c.attrib.get("t", "")
                v_tag = c.find("{*}v")
                is_tag = c.find(".//{*}is/{*}t")
                val = None
                if is_tag is not None and is_tag.text:
                    val = is_tag.text
                elif v_tag is not None and v_tag.text is not None:
                    raw_val = v_tag.text
                    if cell_type == "s":
                        try:
                            val = shared_strings[int(raw_val)]
                        except Exception:
                            val = raw_val
                    else:
                        val = raw_val
                row_dict[col_letter] = val
            raw_rows.append(row_dict)

    if not raw_rows:
        return []

    # Find header row
    header_idx = -1
    col_map = {}
    for idx, r in enumerate(raw_rows[:25]):
        matched = {}
        for col_l, val in r.items():
            if val is None:
                continue
            norm = normalize_column_name(val)
            if norm in ("item_no", "description", "quantity", "unit", "rate", "amount", "gst"):
                matched[col_l] = norm
        if len(matched) >= 4:
            header_idx = idx
            col_map = matched
            break

    if header_idx == -1:
        header_idx = 0
        for col_l, val in raw_rows[0].items():
            if val is not None:
                norm = normalize_column_name(val)
                if norm in ("item_no", "description", "quantity", "unit", "rate", "amount", "gst"):
                    col_map[col_l] = norm

    print(f"Detected BOQ header row: {header_idx + 1}")
    print(f"Detected columns: {col_map}")

    # Build structured items
    items = []
    for r in raw_rows[header_idx + 1:]:
        item_no = r.get(next((k for k, v in col_map.items() if v == "item_no"), ""), None)
        desc = r.get(next((k for k, v in col_map.items() if v == "description"), ""), None)
        if _is_na(item_no) and _is_na(desc):
            continue

        unit_val = r.get(next((k for k, v in col_map.items() if v == "unit"), ""), None)
        qty_val = clean_numeric_value(r.get(next((k for k, v in col_map.items() if v == "quantity"), ""), None))
        rate_val = clean_numeric_value(r.get(next((k for k, v in col_map.items() if v == "rate"), ""), None))
        amt_val = clean_numeric_value(r.get(next((k for k, v in col_map.items() if v == "amount"), ""), None))
        gst_val = clean_numeric_value(r.get(next((k for k, v in col_map.items() if v == "gst"), ""), None))

        items.append({
            "item_no": str(item_no).strip() if item_no is not None else "",
            "description": str(desc).strip() if desc is not None else "",
            "unit": str(unit_val).strip() if unit_val is not None else "",
            "quantity": qty_val,
            "rate": rate_val,
            "amount": amt_val,
            "gst": gst_val
        })

    print(f"BOQ items extracted: {len(items)}")
    return items


def extract_boq(excel_path):
    """
    Extract structured BOQ data from Excel.
    Preserves workbook formula logic and handles formatted strings (commas/currency)
    so amounts are not converted into NaN, while keeping quoted numbers intact
    for accurate arithmetic mismatch detection.
    """
    print("\n--------------------------------")
    print("Reading BOQ:")
    print(excel_path)
    print("--------------------------------")

    excel_path = Path(excel_path)
    if pd is None or excel_path.suffix.lower() == ".xlsx":
        try:
            return _extract_boq_native(excel_path)
        except Exception as e:
            print(f"Native BOQ extraction note: {e}")
            if pd is None:
                raise

    # --------------------------------------------------
    # STEP 1: Automatically locate actual table header
    # --------------------------------------------------
    header_row = find_header_row(excel_path)
    print(f"Detected BOQ header row: {header_row + 1}")

    # --------------------------------------------------
    # STEP 2: Read Excel using workbook inspection
    # --------------------------------------------------
    df = read_boq_workbook(excel_path, header_row)

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
    # STEP 7: Convert numeric values safely
    # --------------------------------------------------
    numeric_columns = [
        "quantity",
        "rate",
        "amount",
        "gst"
    ]

    for column in numeric_columns:
        # 1. Clean strings (strip commas, currency symbols, whitespace)
        df[column] = df[column].apply(clean_numeric_value)
        # 2. Coerce to standard numeric float
        df[column] = pd.to_numeric(df[column], errors="coerce")

    # --------------------------------------------------
    # STEP 8: Reset index
    # --------------------------------------------------
    df = df.reset_index(drop=True)

    print(f"\nBOQ items extracted: {len(df)}")
    return df
