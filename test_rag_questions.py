from src.rag.rag_pipeline import TenderRAG


print("Loading Tender RAG system...")

rag = TenderRAG()


test_questions = [
    "What is the Earnest Money Deposit amount?",

    "What performance security must the successful bidder provide?",

    "What is the project completion period?",

    "What are the bidder eligibility requirements?",

    "What minimum technical score is required?",

    "What is the defect liability period?",

    "What is the penalty if the contractor delays the work?",

    "What is the contractor's insurance premium amount?"
]


for number, question in enumerate(
    test_questions,
    start=1
):

    print("\n" + "=" * 70)

    print(
        f"QUESTION {number}:"
    )

    print(question)

    result = rag.ask(
        question,
        top_k=3
    )

    print("\nANSWER:")

    print(
        result["answer"]
    )

    print("\nTOP RETRIEVED SOURCE:")

    top_source = (
        result["sources"][0]
    )

    print(
        f"Section "
        f"{top_source['section_number']} - "
        f"{top_source['section_title']} "
        f"(Page {top_source['page_number']})"
    )

    print(
        top_source["text"]
    )