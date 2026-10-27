from src.rag.retriever import TenderRetriever
from src.rag.llm_generator import TenderLLM


def answer_question(
    question,
    tender_id="tender_001",
    top_k=3
):
    """
    Complete RAG pipeline for tender question answering.

    Flow:
        Question
            ↓
        TenderRetriever
            ↓
        Relevant tender chunks
            ↓
        Context
            ↓
        TenderLLM
            ↓
        Grounded answer + sources
    """

    # --------------------------------------------------------
    # Validate question
    # --------------------------------------------------------

    if not question or not question.strip():

        return {
            "question": question,
            "answer": "Please enter a question.",
            "sources": []
        }

    # --------------------------------------------------------
    # Create retriever
    # --------------------------------------------------------

    retriever = TenderRetriever()

    # --------------------------------------------------------
    # Retrieve relevant chunks
    # --------------------------------------------------------

    retrieved_chunks = retriever.retrieve(
        question,
        top_k=top_k
    )

    # --------------------------------------------------------
    # Check retrieval result
    # --------------------------------------------------------

    if not retrieved_chunks:

        return {
            "question": question,
            "answer": (
                "The information was not found in "
                "the retrieved tender evidence."
            ),
            "sources": []
        }

    # --------------------------------------------------------
    # Build context
    # --------------------------------------------------------

    context = retriever.build_context(
        retrieved_chunks
    )

    # --------------------------------------------------------
    # Create LLM
    # --------------------------------------------------------

    llm = TenderLLM(
        model_name="llama3.2:3b"
    )

    # --------------------------------------------------------
    # Generate grounded answer
    # --------------------------------------------------------

    answer = llm.generate_answer(
        question=question,
        context=context
    )

    # --------------------------------------------------------
    # Prepare sources for Streamlit
    # --------------------------------------------------------

    sources = []

    for chunk in retrieved_chunks:

        source = {
            "rank": chunk.get(
                "rank"
            ),

            "section_number": chunk.get(
                "section_number"
            ),

            "section_title": chunk.get(
                "section_title",
                "Unknown Section"
            ),

            "page_number": chunk.get(
                "page_number",
                "Unknown"
            ),

            "text": chunk.get(
                "text",
                ""
            ),

            "distance": chunk.get(
                "distance"
            )
        }

        sources.append(source)

    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return {
        "question": question,
        "answer": answer,
        "sources": sources
    }