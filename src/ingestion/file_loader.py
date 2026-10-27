from pathlib import Path


def find_files(folder):

    folder = Path(folder)

    if not folder.exists():

        raise FileNotFoundError(
            f"Folder not found: {folder}"
        )


    pdf_files = list(
        folder.glob("*.pdf")
    )


    excel_files = (
        list(folder.glob("*.xlsx"))
        + list(folder.glob("*.xls"))
    )


    return {
        "pdf_files": pdf_files,
        "excel_files": excel_files
    }


def find_tender_files(tender_folder):

    return find_files(
        tender_folder
    )


def find_bidder_files(bidder_folder):

    return find_files(
        bidder_folder
    )