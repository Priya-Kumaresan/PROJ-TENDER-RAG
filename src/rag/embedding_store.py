"""
Embedding Store Module (ChromaDB + SentenceTransformers with In-Memory Semantic Fallback)
Maintains local vector store for tender chunks with page and section metadata.
"""

import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False


class TenderVectorStore:
    """
    Persistent ChromaDB vector database with sentence-transformers embedding.
    Includes a built-in deterministic lexical/cosine similarity fallback when chromadb
    or sentence-transformers is not installed in the active environment.
    """

    def __init__(self, db_path="data/vector_db"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.fallback_file = self.db_path / "chunks_fallback.json"

        if HAS_CHROMADB:
            try:
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
                self.client = chromadb.PersistentClient(path=str(self.db_path))
                self.collection = self.client.get_or_create_collection(name="tender_chunks")
                self.is_chroma = True
            except Exception:
                self.is_chroma = False
                self._load_fallback_store()
        else:
            self.is_chroma = False
            self._load_fallback_store()

    def _load_fallback_store(self):
        """Load in-memory fallback chunks from JSON file if available."""
        self.fallback_chunks = []
        if self.fallback_file.exists():
            try:
                with open(self.fallback_file, "r", encoding="utf-8") as f:
                    self.fallback_chunks = json.load(f)
            except Exception:
                self.fallback_chunks = []

    def _save_fallback_store(self):
        """Save fallback chunks to disk."""
        try:
            with open(self.fallback_file, "w", encoding="utf-8") as f:
                json.dump(self.fallback_chunks, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Convert tender chunks into embeddings and store them in ChromaDB or fallback store.
        """
        if not chunks:
            return

        texts = [chunk["text"] for chunk in chunks]

        if self.is_chroma:
            try:
                embeddings = self.model.encode(texts).tolist()
                ids = [chunk["chunk_id"] for chunk in chunks]
                metadatas = [
                    {
                        "tender_id": chunk.get("tender_id", "tender_001"),
                        "section_number": chunk.get("section_number", "INTRO"),
                        "section_title": chunk.get("section_title", "Tender Information"),
                        "page_number": chunk.get("page_number", 1),
                        "chunk_index": chunk.get("chunk_index", 1)
                    }
                    for chunk in chunks
                ]
                self.collection.upsert(
                    ids=ids,
                    documents=texts,
                    embeddings=embeddings,
                    metadatas=metadatas
                )
                return
            except Exception:
                # If Chroma write fails, fall through to fallback
                pass

        # Fallback in-memory storage
        existing_ids = {c.get("chunk_id") for c in self.fallback_chunks}
        for chunk in chunks:
            cid = chunk.get("chunk_id")
            if cid not in existing_ids:
                self.fallback_chunks.append(chunk)
                existing_ids.add(cid)
        self._save_fallback_store()

    def search(self, query: str, top_k: int = 3) -> Dict[str, List[Any]]:
        """
        Search for chunks semantically similar to the user's question.
        Returns ChromaDB-compatible dictionary:
        {"documents": [[...]], "metadatas": [[...]], "distances": [[...]]}
        """
        if self.is_chroma:
            try:
                query_embedding = self.model.encode([query]).tolist()
                results = self.collection.query(
                    query_embeddings=query_embedding,
                    n_results=top_k
                )
                if results and results.get("documents") and len(results["documents"][0]) > 0:
                    return results
            except Exception:
                pass

        # Fallback lexical / BM25 term overlap search
        q_tokens = set(re.findall(r"\w+", query.lower()))
        scored = []

        for chunk in self.fallback_chunks:
            c_text = chunk.get("text", "")
            c_tokens = re.findall(r"\w+", c_text.lower())
            if not c_tokens:
                continue

            # Token overlap score
            overlap = sum(1 for t in q_tokens if t in c_tokens)
            score = overlap / (math.sqrt(len(c_tokens)) + 1e-5)
            # Distance inversely proportional to score
            distance = round(1.0 / (score + 1.0), 4)

            metadata = {
                "tender_id": chunk.get("tender_id", "tender_001"),
                "section_number": chunk.get("section_number", "INTRO"),
                "section_title": chunk.get("section_title", "Tender Information"),
                "page_number": chunk.get("page_number", 1),
                "chunk_index": chunk.get("chunk_index", 1)
            }
            scored.append((score, distance, c_text, metadata))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_matches = scored[:top_k]

        docs = [item[2] for item in top_matches]
        metas = [item[3] for item in top_matches]
        dists = [item[1] for item in top_matches]

        return {
            "documents": [docs],
            "metadatas": [metas],
            "distances": [dists]
        }

    def count(self) -> int:
        """Return count of stored chunks (Chroma or fallback)."""
        if self.is_chroma and hasattr(self, "collection"):
            try:
                return self.collection.count()
            except Exception:
                pass
        return len(self.fallback_chunks)

    def delete(self, where: Optional[Dict[str, Any]] = None) -> None:
        """Delete chunks matching filter from Chroma or fallback store."""
        if self.is_chroma and hasattr(self, "collection"):
            try:
                self.collection.delete(where=where)
            except Exception:
                pass
        if where and "tender_id" in where:
            target_id = where["tender_id"]
            self.fallback_chunks = [c for c in self.fallback_chunks if c.get("tender_id") != target_id]
            self._save_fallback_store()

