"""Knowledge base package for Q21G — shared RAG infrastructure."""

from knowledge_base.db import ParagraphDB
from knowledge_base.vector_store import VectorStore
from knowledge_base.sentence_extractor import extract_first_sentence
from knowledge_base.corpus_builder import build_corpus
from knowledge_base.paragraph_filter import is_valid_paragraph

__all__ = [
    "ParagraphDB", "VectorStore", "extract_first_sentence",
    "build_corpus", "is_valid_paragraph",
]
