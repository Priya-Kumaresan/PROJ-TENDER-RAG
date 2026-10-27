from src.rag.retriever import (
    TenderRetriever
)


retriever = TenderRetriever()


question = (
    "What is the penalty "
    "if the contractor delays the work?"
)


# Retrieve relevant chunks
chunks = retriever.retrieve(
    question,
    top_k=3
)


print(
    "\nQUESTION:"
)

print(
    question
)


print(
    "\nRETRIEVED SOURCES:"
)

for chunk in chunks:

    print(
        f"\nRank {chunk['rank']}: "
        f"Section "
        f"{chunk['section_number']} - "
        f"{chunk['section_title']} "
        f"(Page {chunk['page_number']})"
    )


# Build context for future LLM
context = retriever.build_context(
    chunks
)


print(
    "\nCONTEXT FOR LLM:"
)

print(
    context
)