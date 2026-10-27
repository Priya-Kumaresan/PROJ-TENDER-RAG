from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


class TenderVectorStore:

    def __init__(
        self,
        db_path="data/vector_db"
    ):
        """
        Initialize embedding model and
        persistent Chroma vector database.
        """

        self.db_path = Path(db_path)

        self.db_path.mkdir(
            parents=True,
            exist_ok=True
        )

        # Small, efficient embedding model
        self.model = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )

        # Persistent local Chroma database
        self.client = chromadb.PersistentClient(
            path=str(self.db_path)
        )

        self.collection = (
            self.client.get_or_create_collection(
                name="tender_chunks"
            )
        )


    def add_chunks(self, chunks):
        """
        Convert tender chunks into embeddings
        and store them in ChromaDB.
        """

        if not chunks:
            return

        texts = [
            chunk["text"]
            for chunk in chunks
        ]

        embeddings = self.model.encode(
            texts
        ).tolist()

        ids = []
        metadatas = []

        for chunk in chunks:

            ids.append(
                chunk["chunk_id"]
            )

            metadata = {
                "tender_id":
                    chunk["tender_id"],

                "section_number":
                    chunk["section_number"],

                "section_title":
                    chunk["section_title"],

                "page_number":
                    chunk["page_number"],

                "chunk_index":
                    chunk["chunk_index"]
            }

            metadatas.append(
                metadata
            )

        self.collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas
        )


    def search(
        self,
        query,
        top_k=3
    ):
        """
        Search for chunks semantically similar
        to the user's question.
        """

        query_embedding = self.model.encode(
            [query]
        ).tolist()

        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k
        )

        return results