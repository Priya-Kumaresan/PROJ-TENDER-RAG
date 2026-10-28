import json
import sys
from pathlib import Path

from src.ingestion.file_loader import (
    find_tender_files,
    find_bidder_files,
    find_all_bidder_folders,
    load_bidder_names
)
from src.extraction.pdf_extractor import extract_pdf
from src.extraction.section_detector import detect_sections
from src.extraction.field_extractor import extract_tender_fields
from src.extraction.bidder_field_extractor import extract_bidder_fields
from src.boq.boq_extractor import extract_boq
from src.boq.boq_validator import validate_boq
from src.rag.chunker import create_section_chunks
from src.rag.embedding_store import TenderVectorStore
from src.comparison.bid_comparator import compare_bids
from src.comparison.recommendation import generate_recommendation
from src.comparison.bidder_ranker import BidderRanker, save_ranking_results

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ============================================================
# CONFIGURATION
# ============================================================

RAW_FOLDER = Path("data/raw/tender_001")
TENDER_FOLDER = RAW_FOLDER / "tender"
OUTPUT_FOLDER = Path("data/processed/tender_001")

OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

# Load bidder names dictionary if present
names_file = RAW_FOLDER / "bidder_names.json"
names = load_bidder_names(names_file)

print("\n============================================================")
print("TENDER AND MULTI-BIDDER EVALUATION PIPELINE")
print("============================================================")

# ============================================================
# PROCESS COMMON TENDER
# ============================================================

print("\nProcessing common Tender document...")

tender_files = find_tender_files(TENDER_FOLDER)

if not tender_files["pdf_files"]:
    print("Raw tender PDF not found in data/raw/tender_001/tender.")
    if (OUTPUT_FOLDER / "tender.json").exists():
        print("Loading baseline tender dataset from processed repository...")
        with open(OUTPUT_FOLDER / "tender.json", "r", encoding="utf-8") as file:
            tender_data = json.load(file)
    else:
        raise FileNotFoundError("Tender PDF not found and no processed tender.json available.")
else:
    tender_pdf = tender_files["pdf_files"][0]
    print("Tender PDF:", tender_pdf.name)

    # 1. Extract Tender PDF
    tender_data = extract_pdf(tender_pdf)

    # 2. Detect Tender Sections
    tender_data["sections"] = detect_sections(tender_data["pages"])

    # 3. Extract Tender Fields
    tender_data["tender_fields"] = extract_tender_fields(tender_data)

    # ============================================================
    # CREATE & STORE RAG CHUNKS
    # ============================================================

    tender_data["rag_chunks"] = create_section_chunks(
        tender_data,
        tender_id="tender_001"
    )

    print(f"RAG chunks created: {len(tender_data['rag_chunks'])}")
    print("Updating RAG vector database (ChromaDB)...")

    vector_store = TenderVectorStore()

    try:
        vector_store.delete(where={"tender_id": "tender_001"})
        print("Previous tender chunks removed from ChromaDB.")
    except Exception as error:
        print("Collection reset:", str(error))

    vector_store.add_chunks(tender_data["rag_chunks"])
    print("RAG chunks stored. Total chunks in store:", vector_store.count())

    # Save Tender JSON
    tender_output = OUTPUT_FOLDER / "tender.json"
    with open(tender_output, "w", encoding="utf-8") as file:
        json.dump(tender_data, file, indent=4, ensure_ascii=False)

    print("Tender PDF processing completed.")

# ============================================================
# PROCESS TENDER BOQ
# ============================================================

print("\nProcessing Tender BOQ...")

if tender_files["excel_files"]:
    tender_boq_path = tender_files["excel_files"][0]
    print("Tender BOQ:", tender_boq_path.name)
    tender_boq_df = extract_boq(tender_boq_path)
    tender_boq_validation = validate_boq(tender_boq_df)

    tender_boq_output = OUTPUT_FOLDER / "tender_boq.json"
    with open(tender_boq_output, "w", encoding="utf-8") as file:
        json.dump(tender_boq_validation, file, indent=4, ensure_ascii=False, default=str)
    print("Tender BOQ processing completed.")
elif (OUTPUT_FOLDER / "tender_boq.json").exists():
    print("Loaded tender BOQ baseline from processed repository.")
else:
    print("Notice: Tender BOQ Excel file not found.")

# ============================================================
# FUNCTION TO PROCESS AN INDIVIDUAL BIDDER
# ============================================================

def process_bidder(bidder_folder, bidder_name, bidder_id):
    print(f"\nProcessing {bidder_name} ({bidder_id})...")

    files = find_bidder_files(bidder_folder)

    if not files["pdf_files"]:
        raise FileNotFoundError(f"No PDF documents found for {bidder_name} in {bidder_folder}")

    # Combine all PDF documents submitted by this bidder
    combined_pages = []
    for pdf_path in files["pdf_files"]:
        print(f"  • Reading PDF: {pdf_path.name}")
        pdf_data = extract_pdf(pdf_path)
        for page in pdf_data["pages"]:
            page_copy = dict(page)
            page_copy["source_file"] = pdf_path.name
            combined_pages.append(page_copy)

    combined_pdf_data = {
        "file_name": f"{bidder_id}_documents",
        "total_pages": len(combined_pages),
        "pages": combined_pages
    }

    # Extract Bidder Fields
    bidder_fields = extract_bidder_fields(combined_pdf_data, bidder_name)

    # Process Bidder BOQ
    boq_validation = []
    if files["excel_files"]:
        boq_path = files["excel_files"][0]
        print(f"  • Reading BOQ: {boq_path.name}")
        boq_df = extract_boq(boq_path)
        boq_validation = validate_boq(boq_df)

    bidder_data = {
        "bidder_id": bidder_id,
        "bidder_name": bidder_name,
        "total_pages": len(combined_pages),
        "bidder_fields": bidder_fields,
        "boq_validation": boq_validation
    }

    output_file = OUTPUT_FOLDER / f"{bidder_id}.json"
    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(bidder_data, file, indent=4, ensure_ascii=False, default=str)

    print(f"{bidder_name} processing completed.")
    return bidder_data


# ============================================================
# DYNAMIC MULTI-BIDDER DISCOVERY & PROCESSING
# ============================================================

bidder_folders = find_all_bidder_folders(RAW_FOLDER)

# Fallback: check standard folders if discover returns empty
if not bidder_folders:
    candidate_folders = [RAW_FOLDER / "bidder_A", RAW_FOLDER / "bidder_B"]
    bidder_folders = [f for f in candidate_folders if f.exists()]

all_bidders_data = []

has_raw_bidders = any(
    find_bidder_files(f).get("pdf_files") for f in bidder_folders
) if bidder_folders else False

if has_raw_bidders:
    print(f"\nDiscovered {len(bidder_folders)} bidder folder(s): {[f.name for f in bidder_folders]}")
    for b_folder in bidder_folders:
        b_id = b_folder.name
        b_name = names.get(b_id, b_id.replace("_", " ").title())
        b_data = process_bidder(b_folder, b_name, b_id)
        all_bidders_data.append(b_data)
else:
    print("\nRaw bidder documents not found in data/raw. Loading processed bidder submissions...")
    for b_file in sorted(OUTPUT_FOLDER.glob("bidder_*.json"), key=lambda p: p.name):
        if b_file.name == "bidder_ranking.json":
            continue
        with open(b_file, "r", encoding="utf-8") as f:
            b_json = json.load(f)
            all_bidders_data.append(b_json)
    print(f"Loaded {len(all_bidders_data)} bidder submission(s): {[b.get('bidder_name') for b in all_bidders_data]}")

if not all_bidders_data:
    raise FileNotFoundError("No bidder submissions found in raw or processed folders.")

# ============================================================
# MULTI-BIDDER COMPLIANCE COMPARISON
# ============================================================

print("\nProcessing Multi-Bidder Comparison against Baseline...")

comparison_result = compare_bids(
    tender_data["tender_fields"],
    all_bidders_data
)

# ============================================================
# BIDDER RANKING & QUALIFICATION (Priorities 6-13)
# ============================================================

print("\nProcessing Dynamic Multi-Bidder Qualification and Ranking...")

boq_evaluations = {}
for b in all_bidders_data:
    b_id = b.get("bidder_id")
    b_boq = b.get("boq_validation", [])
    boq_evaluations[b_id] = {
        "summary": {
            "total_items": len(b_boq),
            "missing_rates": sum(1 for itm in b_boq if "Missing Rate" in itm.get("issues", [])),
            "fatal_anomalies": sum(1 for itm in b_boq if str(itm.get("status", "")).upper() == "ERROR")
        }
    }

ranker = BidderRanker()
ranking_result = ranker.rank_bidders(
    tender_fields=tender_data["tender_fields"],
    bidders_list=all_bidders_data,
    boq_evaluations=boq_evaluations
)

ranking_output = OUTPUT_FOLDER / "bidder_ranking.json"
save_ranking_results(ranking_result, str(ranking_output))
print(f"Saved bidder ranking results to: {ranking_output.name}")

# ============================================================
# GENERATE BIDDER RECOMMENDATION
# ============================================================

recommendation_result = generate_recommendation(
    comparison_result
)

# Align recommendation with dynamic ranker if qualified bidders exist
if ranking_result.get("recommended_bidder"):
    comparison_result["recommended_bidder"] = ranking_result["recommended_bidder"]
    comparison_result["recommendation"] = ranking_result["recommendation_statement"]
    comparison_result["next_eligible_bidder"] = ranking_result.get("next_eligible_bidder")
else:
    comparison_result["recommended_bidder"] = recommendation_result["recommended_bidder"]
    comparison_result["recommendation"] = recommendation_result["recommendation"]
    comparison_result["next_eligible_bidder"] = recommendation_result.get("next_eligible_bidder")

comparison_result["recommendation_details"] = recommendation_result
comparison_result["ranking_summary"] = ranking_result

# Save bid_comparison.json
comparison_output = OUTPUT_FOLDER / "bid_comparison.json"
with open(comparison_output, "w", encoding="utf-8") as file:
    json.dump(comparison_result, file, indent=4, ensure_ascii=False)

# ============================================================
# INDEX UNIFIED MULTI-PILLAR KNOWLEDGE INTO RAG VECTOR STORE
# ============================================================
print("\nIndexing Unified Knowledge (Tender, Bidders, Evaluation) into RAG Vector Store...")
try:
    from src.rag.chunker import create_tender_boq_chunks, create_bidder_chunks, create_evaluation_chunks
    from src.rag.embedding_store import TenderVectorStore

    all_knowledge_chunks = list(tender_data.get("rag_chunks", []))

    # 1. Tender BOQ chunks
    tender_boq_json_path = OUTPUT_FOLDER / "tender_boq.json"
    if tender_boq_json_path.exists():
        with open(tender_boq_json_path, "r", encoding="utf-8") as f:
            t_boq_data = json.load(f)
        all_knowledge_chunks.extend(create_tender_boq_chunks(t_boq_data, tender_id="tender_001"))

    # 2. Bidder Technical, Financial, and BOQ Chunks
    try:
        import pypdf
    except ImportError:
        pypdf = None

    for b in all_bidders_data:
        b_id = b.get("bidder_id")
        b_name = b.get("bidder_name")
        pdf_texts = {}
        if pypdf:
            b_folder = RAW_FOLDER / b_id
            for pdf_f in ["Technical_Bid.pdf", "Financial_Bid.pdf"]:
                p_path = b_folder / pdf_f
                if p_path.exists():
                    try:
                        reader = pypdf.PdfReader(str(p_path))
                        pdf_texts[pdf_f] = "\n".join([pg.extract_text() or "" for pg in reader.pages])
                    except Exception:
                        pass
        b_chunks = create_bidder_chunks(
            bidder_id=b_id,
            bidder_name=b_name,
            raw_pdf_texts=pdf_texts,
            bidder_fields=b.get("bidder_fields"),
            boq_items=b.get("boq_validation"),
            tender_id="tender_001"
        )
        all_knowledge_chunks.extend(b_chunks)

    # 3. Evaluation & Ranking Chunks
    eval_chunks = create_evaluation_chunks(
        ranking_result=ranking_result,
        comparison_result=comparison_result,
        tender_id="tender_001"
    )
    all_knowledge_chunks.extend(eval_chunks)

    # Reset and store unified knowledge base
    v_store = TenderVectorStore()
    v_store.delete(where={"tender_id": "tender_001"})
    v_store.add_chunks(all_knowledge_chunks)
    print(f"RAG Vector Database successfully updated with {len(all_knowledge_chunks)} unified chunks across all 3 pillars.")
except Exception as e:
    print(f"Warning updating vector store: {e}")

# ============================================================
# DISPLAY SUMMARY
# ============================================================

summary = comparison_result["summary"]

print("\n============================================================")
print("BIDDER EVALUATION SUMMARY")
print("============================================================")
print("Requirements Evaluated:", summary["fields_compared"])

for b_id, b_info in summary.get("bidders", {}).items():
    print(f"{b_info['name']}: {b_info['compliant']} Compliant / {b_info['non_compliant']} Non-Compliant")

print("\nRequirement Comparison Matrix:")
print("------------------------------------------------------------")
for item in comparison_result["field_comparisons"]:
    print(f"\nRequirement: {item['field'].replace('_', ' ').title()}")
    print("  Tender Baseline:", item["tender_requirement"])
    for b_id, b_resp in item.get("bidders", {}).items():
        name = summary.get("bidders", {}).get(b_id, {}).get("name", b_id)
        print(f"  {name}: {b_resp['value']} | Status: {b_resp['status']}")

print("\nSubstantive Differences:")
print("------------------------------------------------------------")
for diff in comparison_result.get("differences", []):
    print(f"• {diff['field'].replace('_', ' ').title()} ({diff['impact']}): {diff['message']}")

print("\n============================================================")
print("BIDDER RANKING & EVALUATION TABLE")
print("============================================================")
params = ranking_result["evaluation_parameters"]
print(f"Methodology: Technical Weight = {params['technical_weight_percent']}, Financial Weight = {params['financial_weight_percent']}")
print(f"Mandatory Tech Cutoff = {params['min_technical_score']} marks | L1 Lowest Qualified Quote = INR {params['lowest_qualified_bid_l1']:,.0f}" if params['lowest_qualified_bid_l1'] else "")
print("------------------------------------------------------------")
for row in ranking_result["ranking_table"]:
    print(f"Rank {row['rank']:<2}: {row['bidder_name']:<35} | Status: {row['qualification']:<12} | "
          f"Tech: {row['technical_score']} | Quote: {row['quoted_amount']} | "
          f"Fin Score: {row['financial_score']} | Overall: {row['overall_score']}")

print("\n============================================================")
print("PROVISIONAL DECISION-SUPPORT RECOMMENDATION")
print("============================================================")
print("Recommended Bidder (Rank 1):", ranking_result.get("recommended_bidder") or recommendation_result["recommended_bidder"])
print("Next Eligible Bidder (Rank 2):", ranking_result.get("next_eligible_bidder") or recommendation_result.get("next_eligible_bidder", "None"))
print("Recommendation Statement:\n", ranking_result.get("recommendation_statement") or recommendation_result["recommendation"])
print("============================================================\n")
