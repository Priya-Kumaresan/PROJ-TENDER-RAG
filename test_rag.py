from src.rag.rag_pipeline import answer_question


def main():

    print("=" * 60)
    print("TENDER RAG TEST")
    print("=" * 60)

    question = "What is the proposal validity period?"

    print("\nQuestion:")
    print(question)

    print("\nSearching tender and generating answer...")

    result = answer_question(
        question,
        tender_id="tender_001",
        top_k=3
    )

    print("\n" + "=" * 60)
    print("ANSWER")
    print("=" * 60)

    print(
        result.get(
            "answer",
            "No answer generated."
        )
    )

    print("\n" + "=" * 60)
    print("RETRIEVED SOURCES")
    print("=" * 60)

    sources = result.get(
        "sources",
        []
    )

    if not sources:
        print("No sources retrieved.")

    for source in sources:

        print(
            f"\nRank: "
            f"{source.get('rank')}"
        )

        print(
            f"Section: "
            f"{source.get('section_number')} - "
            f"{source.get('section_title')}"
        )

        print(
            f"Page: "
            f"{source.get('page_number')}"
        )

        print(
            f"Distance: "
            f"{source.get('distance')}"
        )

        print("\nEvidence:")

        text = source.get(
            "text",
            ""
        )

        print(
            text[:500]
        )

        print("-" * 60)


if __name__ == "__main__":
    main()