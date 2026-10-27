import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.rag.rag_pipeline import TenderRAG
from src.rag.chunker import create_section_chunks

print("Loading Tender RAG system...")
rag = TenderRAG()

# Seed baseline tender chunks if empty so RAG has grounded evidence
store = rag.retriever.vector_store
sample_pdf_data = {
    "sections": [
        {"section_number": "1", "section_title": "Tender Information & Overview", "start_page": 1},
        {"section_number": "2", "section_title": "Commercial & Financial Requirements", "start_page": 2},
        {"section_number": "3", "section_title": "Eligibility & Evaluation Criteria", "start_page": 3},
        {"section_number": "4", "section_title": "Conditions of Contract & Penalties", "start_page": 4}
    ],
    "pages": [
        {
            "page_number": 1,
            "cleaned_text": (
                "Tender No: SIDA/WORKS/001/2026. Organisation: Special Infrastructure Development Authority. "
                "Project: Construction of Regional Transit Hub and Administrative Facility. "
                "Proposal Validity: 180 days from the deadline of bid submission. "
                "Bids must remain firm and unconditional during the entire validity period."
            )
        },
        {
            "page_number": 2,
            "cleaned_text": (
                "Section 2: Commercial & Financial Requirements. "
                "Earnest Money Deposit (EMD): The bidder must submit an Earnest Money Deposit of INR 5,00,000 "
                "in the form of a Bank Guarantee or Demand Draft from a scheduled commercial bank. "
                "Performance Security: The successful bidder shall furnish Performance Security equal to 10% "
                "of the accepted contract value within 21 days of issuance of Letter of Acceptance (LOA). "
                "Completion Period: The entire project work must be completed within 12 months from the date of handover of site."
            )
        },
        {
            "page_number": 3,
            "cleaned_text": (
                "Section 3: Eligibility & Evaluation Criteria. "
                "Bidder Eligibility Requirements: Bidders must be registered civil contractors with minimum 5 years experience. "
                "Technical Evaluation: Bids will be evaluated out of 100 marks. The mandatory minimum qualifying technical score "
                "is 70 marks. Bidders scoring below 70 marks will be disqualified and their financial bids will not be opened. "
                "Evaluation Method: Quality and Cost Based Selection (QCBS) with 80% Technical Weightage and 20% Financial Weightage."
            )
        },
        {
            "page_number": 4,
            "cleaned_text": (
                "Section 4: Conditions of Contract & Penalties. "
                "Liquidated Damages: In case of delay in completion beyond the stipulated 12 months schedule, "
                "liquidated damages shall be levied at 0.5% of contract price per week of delay, subject to a maximum of 10%. "
                "Defect Liability Period: The contractor shall guarantee all works against defects for a defect liability "
                "period of 12 months from the date of virtual completion certificate."
            )
        }
    ]
}

chunks = create_section_chunks(sample_pdf_data, "tender_001")
store.add_chunks(chunks)

test_questions = [
    "What is the Earnest Money Deposit amount?",
    "What performance security must the successful bidder provide?",
    "What is the project completion period?",
    "What are the bidder eligibility requirements?",
    "What minimum technical score is required?",
    "What is the defect liability period?",
    "What is the penalty if the contractor delays the work?",
    "What is the proposal validity period?"
]

for number, question in enumerate(test_questions, start=1):
    print("\n" + "=" * 70)
    print(f"QUESTION {number}: {question}")

    result = rag.ask(question, top_k=2)

    print("\nANSWER:")
    print(result["answer"])

    print("\nTOP RETRIEVED EVIDENCE:")
    if result.get("sources"):
        top_source = result["sources"][0]
        print(f"Section {top_source['section_number']}: {top_source['section_title']} (Page {top_source['page_number']})")
        print(top_source["text"][:300] + "...")
    else:
        print("No sources retrieved.")

print("\n" + "=" * 70)
print("ALL RAG QUESTIONS EVALUATED SUCCESSFULLY!")
print("=" * 70)
