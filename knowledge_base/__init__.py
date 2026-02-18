"""Knowledge base package for Q21G — shared RAG infrastructure."""

__version__ = "0.1.0"

from knowledge_base.db import ParagraphDB
from knowledge_base.vector_store import VectorStore
from knowledge_base.sentence_extractor import extract_first_sentence
from knowledge_base.corpus_builder import build_corpus
from knowledge_base.paragraph_filter import is_valid_paragraph
from knowledge_base.pdf_parser import extract_text_from_pdf, split_into_paragraphs
from knowledge_base.embedding_builder import compute_embeddings_parallel
from knowledge_base.llm_client import call_llm, call_llm_batch
from knowledge_base.skill_plugin import (
    SkillPlugin,
    MarkdownSkillPlugin,
    SkillRegistry,
    build_default_registry,
    BUILTIN_SKILLS,
)

__all__ = [
    "ParagraphDB", "VectorStore", "extract_first_sentence",
    "build_corpus", "is_valid_paragraph",
    "extract_text_from_pdf", "split_into_paragraphs",
    "compute_embeddings_parallel",
    "call_llm", "call_llm_batch",
    "SkillPlugin", "MarkdownSkillPlugin", "SkillRegistry",
    "build_default_registry", "BUILTIN_SKILLS",
]
