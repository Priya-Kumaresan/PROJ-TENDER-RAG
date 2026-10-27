import json
from pathlib import Path


def find_files(folder):
    """
    Find PDF and Excel files inside a specified directory.
    """
    folder = Path(folder)

    if not folder.exists():
        return {
            "pdf_files": [],
            "excel_files": []
        }

    pdf_files = list(folder.glob("*.pdf"))

    excel_files = (
        list(folder.glob("*.xlsx"))
        + list(folder.glob("*.xls"))
    )

    return {
        "pdf_files": sorted(pdf_files, key=lambda f: f.name),
        "excel_files": sorted(excel_files, key=lambda f: f.name)
    }


def find_tender_files(tender_folder):
    """
    Find common tender documents (PDF and BOQ Excel).
    """
    return find_files(tender_folder)


def find_bidder_files(bidder_folder):
    """
    Find bidder submission documents (Technical PDF, Financial PDF, BOQ Excel).
    """
    return find_files(bidder_folder)


def find_all_bidder_folders(raw_tender_folder):
    """
    Dynamically discover all bidder directories in the tender folder.
    Matches any directory starting with 'bidder' (e.g. bidder_A, bidder_B, bidder_C, bidder_01, etc.).
    Returns a sorted list of Path objects.
    """
    raw_folder = Path(raw_tender_folder)
    if not raw_folder.exists():
        return []

    bidder_folders = [
        f for f in raw_folder.iterdir()
        if f.is_dir() and f.name.lower().startswith("bidder")
    ]
    return sorted(bidder_folders, key=lambda f: f.name)


def load_bidder_names(names_file):
    """
    Safely load bidder mapping from bidder_names.json, e.g.:
    {
        "bidder_A": "Alpha Construction Pvt Ltd",
        "bidder_B": "Beta Infrastructure Ltd",
        "bidder_C": "Gamma Infra Projects"
    }
    """
    names_file = Path(names_file)
    if names_file.exists():
        try:
            with open(names_file, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            pass
    return {}
