import json
from pathlib import Path


from src.ingestion.file_loader import (
    find_tender_files,
    find_bidder_files
)


from src.extraction.pdf_extractor import (
    extract_pdf
)


from src.extraction.section_detector import (
    detect_sections
)


from src.extraction.field_extractor import (
    extract_tender_fields
)


from src.extraction.bidder_field_extractor import (
    extract_bidder_fields
)


from src.boq.boq_extractor import (
    extract_boq
)


from src.boq.boq_validator import (
    validate_boq
)


from src.rag.chunker import (
    create_section_chunks
)


from src.rag.embedding_store import (
    TenderVectorStore
)


from src.comparison.bid_comparator import (
    compare_bids
)
from src.comparison.recommendation import (
    generate_recommendation
)

# ============================================================
# CONFIGURATION
# ============================================================

RAW_FOLDER = Path(
    "data/raw/tender_001"
)


TENDER_FOLDER = (
    RAW_FOLDER / "tender"
)


BIDDER_A_FOLDER = (
    RAW_FOLDER / "bidder_A"
)


BIDDER_B_FOLDER = (
    RAW_FOLDER / "bidder_B"
)


OUTPUT_FOLDER = Path(
    "data/processed/tender_001"
)


OUTPUT_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LOAD BIDDER NAMES
# ============================================================

names_file = (
    RAW_FOLDER
    / "bidder_names.json"
)


bidder_a_name = "Bidder A"
bidder_b_name = "Bidder B"


if names_file.exists():

    with open(
        names_file,
        "r",
        encoding="utf-8"
    ) as file:

        names = json.load(
            file
        )


    bidder_a_name = names.get(
        "bidder_A",
        "Bidder A"
    )


    bidder_b_name = names.get(
        "bidder_B",
        "Bidder B"
    )


print(
    "\n============================================================"
)

print(
    "TENDER AND BID ANALYSIS"
)

print(
    "============================================================"
)


# ============================================================
# PROCESS COMMON TENDER
# ============================================================

print(
    "\nProcessing common Tender..."
)


tender_files = find_tender_files(
    TENDER_FOLDER
)


if not tender_files["pdf_files"]:

    raise FileNotFoundError(
        "Tender PDF not found."
    )


tender_pdf = (
    tender_files["pdf_files"][0]
)


print(
    "Tender PDF:",
    tender_pdf.name
)


# ------------------------------------------------------------
# Extract Tender PDF
# ------------------------------------------------------------

tender_data = extract_pdf(
    tender_pdf
)


# ------------------------------------------------------------
# Detect Tender Sections
# ------------------------------------------------------------

tender_data["sections"] = detect_sections(
    tender_data["pages"]
)


# ------------------------------------------------------------
# Extract Tender Fields
# ------------------------------------------------------------

tender_data["tender_fields"] = (
    extract_tender_fields(
        tender_data
    )
)


# ============================================================
# CREATE RAG CHUNKS
# ============================================================

tender_data["rag_chunks"] = (
    create_section_chunks(
        tender_data,
        tender_id="tender_001"
    )
)


print(
    f"RAG chunks created: "
    f"{len(tender_data['rag_chunks'])}"
)


# ============================================================
# STORE RAG CHUNKS IN CHROMADB
# ============================================================

print(
    "Updating RAG vector database..."
)


vector_store = TenderVectorStore()


# ------------------------------------------------------------
# Delete old chunks for this tender
# ------------------------------------------------------------

try:

    vector_store.collection.delete(
        where={
            "tender_id": "tender_001"
        }
    )

    print(
        "Old tender chunks removed from ChromaDB."
    )

except Exception as error:

    print(
        "No previous tender chunks removed "
        "or collection was empty."
    )

    print(
        "Chroma message:",
        str(error)
    )


# ------------------------------------------------------------
# Add newly generated chunks
# ------------------------------------------------------------

vector_store.add_chunks(
    tender_data["rag_chunks"]
)


print(
    "RAG chunks stored in ChromaDB."
)


print(
    "Current Chroma chunk count:",
    vector_store.collection.count()
)


# ============================================================
# SAVE TENDER JSON
# ============================================================

tender_output = (
    OUTPUT_FOLDER
    / "tender.json"
)


with open(
    tender_output,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        tender_data,
        file,
        indent=4,
        ensure_ascii=False
    )


print(
    "Tender PDF processing completed."
)


# ============================================================
# PROCESS TENDER BOQ
# ============================================================

print(
    "\nProcessing Tender BOQ..."
)


if not tender_files["excel_files"]:

    raise FileNotFoundError(
        "Tender BOQ not found."
    )


tender_boq_path = (
    tender_files["excel_files"][0]
)


print(
    "Tender BOQ:",
    tender_boq_path.name
)


tender_boq_df = extract_boq(
    tender_boq_path
)


tender_boq_validation = (
    validate_boq(
        tender_boq_df
    )
)


tender_boq_output = (
    OUTPUT_FOLDER
    / "tender_boq.json"
)


with open(
    tender_boq_output,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        tender_boq_validation,
        file,
        indent=4,
        ensure_ascii=False,
        default=str
    )


print(
    "Tender BOQ processing completed."
)


# ============================================================
# FUNCTION TO PROCESS BIDDER
# ============================================================

def process_bidder(
    bidder_folder,
    bidder_name,
    bidder_id
):

    print(
        f"\nProcessing {bidder_name}..."
    )


    files = find_bidder_files(
        bidder_folder
    )


    if not files["pdf_files"]:

        raise FileNotFoundError(
            f"No PDF documents found for "
            f"{bidder_name}."
        )


    # --------------------------------------------------------
    # Combine PDF information
    # --------------------------------------------------------

    combined_pages = []


    for pdf_path in files["pdf_files"]:

        print(
            f"Processing PDF: "
            f"{pdf_path.name}"
        )


        pdf_data = extract_pdf(
            pdf_path
        )


        for page in pdf_data["pages"]:

            page_copy = dict(page)


            page_copy["source_file"] = (
                pdf_path.name
            )


            combined_pages.append(
                page_copy
            )


    combined_pdf_data = {

        "file_name":
            f"{bidder_id}_documents",

        "total_pages":
            len(combined_pages),

        "pages":
            combined_pages
    }


    # --------------------------------------------------------
    # Extract bidder fields
    # --------------------------------------------------------

    bidder_fields = extract_bidder_fields(
        combined_pdf_data,
        bidder_name
    )


    # --------------------------------------------------------
    # Process bidder BOQ
    # --------------------------------------------------------

    boq_validation = []


    if files["excel_files"]:

        boq_path = (
            files["excel_files"][0]
        )


        print(
            f"Processing BOQ: "
            f"{boq_path.name}"
        )


        boq_df = extract_boq(
            boq_path
        )


        boq_validation = validate_boq(
            boq_df
        )


    # --------------------------------------------------------
    # Save bidder data
    # --------------------------------------------------------

    bidder_data = {

        "bidder_id":
            bidder_id,

        "bidder_name":
            bidder_name,

        "total_pages":
            len(combined_pages),

        "bidder_fields":
            bidder_fields,

        "boq_validation":
            boq_validation
    }


    output_file = (
        OUTPUT_FOLDER
        / f"{bidder_id}.json"
    )


    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            bidder_data,
            file,
            indent=4,
            ensure_ascii=False,
            default=str
        )


    print(
        f"{bidder_name} processing completed."
    )


    return bidder_data


# ============================================================
# PROCESS BIDDER A
# ============================================================

bidder_a_data = process_bidder(
    BIDDER_A_FOLDER,
    bidder_a_name,
    "bidder_A"
)


# ============================================================
# PROCESS BIDDER B
# ============================================================

bidder_b_data = process_bidder(
    BIDDER_B_FOLDER,
    bidder_b_name,
    "bidder_B"
)


# ============================================================
# BIDDER COMPARISON
# ============================================================

print(
    "\nProcessing Bid Comparison..."
)


comparison_result = compare_bids(

    tender_data[
        "tender_fields"
    ],

    bidder_a_data[
        "bidder_fields"
    ],

    bidder_b_data[
        "bidder_fields"
    ],

    bidder_a_name,

    bidder_b_name
)
# ============================================================
# GENERATE BIDDER RECOMMENDATION
# ============================================================

recommendation_result = generate_recommendation(
    comparison_result,
    bidder_a_name,
    bidder_b_name
)


comparison_result["recommended_bidder"] = (
    recommendation_result[
        "recommended_bidder"
    ]
)


comparison_result["recommendation"] = (
    recommendation_result[
        "recommendation"
    ]
)


comparison_result["recommendation_details"] = (
    recommendation_result
)

comparison_output = (
    OUTPUT_FOLDER
    / "bid_comparison.json"
)


with open(
    comparison_output,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        comparison_result,
        file,
        indent=4,
        ensure_ascii=False
    )


# ============================================================
# DISPLAY SUMMARY
# ============================================================

summary = comparison_result[
    "summary"
]


print(
    "\n============================================================"
)

print(
    "BID COMPARISON"
)

print(
    "============================================================"
)


print(
    "Fields Compared:",
    summary[
        "fields_compared"
    ]
)


print(
    f"{bidder_a_name} Compliant:",
    summary[
        "bidder_a_compliant"
    ]
)


print(
    f"{bidder_b_name} Compliant:",
    summary[
        "bidder_b_compliant"
    ]
)


print(
    "\nRequirement Comparison"
)


print(
    "------------------------------------------------------------"
)


for item in comparison_result[
    "field_comparisons"
]:

    print(
        f"\nField: {item['field']}"
    )


    print(
        "Tender Requirement:",
        item["tender_requirement"]
    )


    print(
        f"{bidder_a_name}:",
        item["bidder_a_value"],
        "|",
        item["bidder_a_status"]
    )


    print(
        f"{bidder_b_name}:",
        item["bidder_b_value"],
        "|",
        item["bidder_b_status"]
    )


print(
    "\nImportant Differences"
)


print(
    "------------------------------------------------------------"
)


for item in comparison_result[
    "differences"
]:

    print(
        f"\nField: {item['field']}"
    )


    print(
        "Impact:",
        item["impact"]
    )


    print(
        "Analysis:",
        item["message"]
    )


# ============================================================
# END
# ============================================================

print(
    "\n============================================================"
)

print(
    "All tender and bidder processing steps completed successfully."
)

print(
    "============================================================"
)