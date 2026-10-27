from src.rag.embedding_store import (
    TenderVectorStore
)


class TenderRetriever:

    def __init__(self):
        self.vector_store = TenderVectorStore()


    def retrieve(
        self,
        question,
        top_k=3
    ):
        """
        Retrieve relevant tender chunks
        for a user question.
        """

        results = self.vector_store.search(
            question,
            top_k=top_k
        )

        retrieved_chunks = []

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for index in range(
            len(documents)
        ):

            metadata = metadatas[index]

            chunk = {
                "rank": index + 1,
                "text": documents[index],

                "section_number":
                    metadata[
                        "section_number"
                    ],

                "section_title":
                    metadata[
                        "section_title"
                    ],

                "page_number":
                    metadata[
                        "page_number"
                    ],

                "distance":
                    distances[index]
            }

            retrieved_chunks.append(
                chunk
            )

        return retrieved_chunks


    def build_context(
        self,
        retrieved_chunks
    ):
        """
        Convert retrieved chunks into
        structured context for an LLM.
        """

        context_parts = []

        for chunk in retrieved_chunks:

            source = (
                f"[Section "
                f"{chunk['section_number']}: "
                f"{chunk['section_title']}, "
                f"Page "
                f"{chunk['page_number']}]"
            )

            context_parts.append(
                source
                + "\n"
                + chunk["text"]
            )

        return "\n\n".join(
            context_parts
        )