"""ChromaDB vector store for semantic paragraph search.

Uses paraphrase-multilingual-MiniLM-L12-v2 for Hebrew+English embeddings.
"""

from pathlib import Path
from typing import Optional

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

DEFAULT_CHROMA_PATH = Path(__file__).parent / "data" / "chroma_db"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION_NAME = "course_paragraphs"


class VectorStore:
    """ChromaDB wrapper for semantic paragraph search."""

    def __init__(self, chroma_path: Optional[Path] = None):
        self._chroma_path = chroma_path or DEFAULT_CHROMA_PATH
        self._ef = SentenceTransformerEmbeddingFunction(
            model_name=MODEL_NAME
        )
        self._client = chromadb.PersistentClient(path=str(self._chroma_path))
        self._collection = None

    def _get_collection(self):
        if self._collection is None:
            self._collection = self._client.get_collection(
                name=COLLECTION_NAME, embedding_function=self._ef
            )
        return self._collection

    def create_collection(self, paragraphs: list[dict]) -> None:
        """Build the vector index from paragraph records."""
        try:
            self._client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

        col = self._client.create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )

        batch_size = 100
        for i in range(0, len(paragraphs), batch_size):
            batch = paragraphs[i:i + batch_size]
            col.add(
                ids=[p["id"] for p in batch],
                documents=[p["text"] for p in batch],
                metadatas=[{
                    "pdf_name": p["pdf_name"],
                    "opening_sentence": p["opening_sentence"],
                    "paragraph_index": p["paragraph_index"],
                    "word_count": p["word_count"],
                } for p in batch],
            )

        self._collection = col
        print(f"ChromaDB built with {len(paragraphs)} vectors")

    def _format_results(self, results: dict) -> list[dict]:
        """Convert ChromaDB query results to flat list of dicts."""
        out = []
        if not results["ids"] or not results["ids"][0]:
            return out
        for idx in range(len(results["ids"][0])):
            entry = {
                "id": results["ids"][0][idx],
                "text": results["documents"][0][idx],
                "distance": results["distances"][0][idx],
            }
            if results["metadatas"] and results["metadatas"][0]:
                entry.update(results["metadatas"][0][idx])
            out.append(entry)
        return out

    def search(self, query: str, n_results: int = 10) -> list[dict]:
        """Semantic search across all paragraphs."""
        col = self._get_collection()
        results = col.query(query_texts=[query], n_results=n_results)
        return self._format_results(results)

    def search_by_pdf(
        self, query: str, pdf_name: str, n_results: int = 10
    ) -> list[dict]:
        """Semantic search filtered to a specific PDF."""
        col = self._get_collection()
        results = col.query(
            query_texts=[query],
            n_results=n_results,
            where={"pdf_name": pdf_name},
        )
        return self._format_results(results)

    def count(self) -> int:
        return self._get_collection().count()


def build_chroma(paragraphs: list[dict], chroma_path: Path) -> None:
    """Build ChromaDB vector store from paragraphs list."""
    chroma_path.mkdir(parents=True, exist_ok=True)
    vs = VectorStore(chroma_path)
    vs.create_collection(paragraphs)
