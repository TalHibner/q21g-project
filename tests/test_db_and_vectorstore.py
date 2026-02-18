"""Tests for SQLite database and ChromaDB vector store (require built data)."""

import pytest
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "knowledge_base" / "data"


# ── SQLite database tests ──


@pytest.fixture
def db():
    from knowledge_base.db import ParagraphDB
    db_path = DATA_DIR / "paragraphs.db"
    if not db_path.exists():
        pytest.skip("Knowledge base not built yet")
    d = ParagraphDB(db_path)
    yield d
    d.close()


def test_db_count(db):
    assert db.count() > 0


def test_get_by_id(db):
    p = db.get_random()
    assert p is not None
    result = db.get_by_id(p["id"])
    assert result is not None
    assert result["id"] == p["id"]


def test_get_by_pdf_name(db):
    names = db.get_all_pdf_names()
    assert len(names) > 0
    results = db.get_by_pdf_name(names[0])
    assert len(results) > 0
    assert all(r["pdf_name"] == names[0] for r in results)


def test_get_random(db):
    p = db.get_random()
    assert p is not None
    for key in ("id", "opening_sentence", "full_text"):
        assert key in p


def test_get_random_word_filter(db):
    p = db.get_random(min_words=50, max_words=150)
    if p:
        assert 50 <= p["word_count"] <= 150


def test_difficulty_score_exists(db):
    p = db.get_random()
    assert p is not None
    assert "difficulty_score" in p
    assert p["difficulty_score"] is not None
    assert 0.0 <= p["difficulty_score"] <= 1.0


def test_get_random_difficulty_filter(db):
    p = db.get_random(min_difficulty=0.4, max_difficulty=0.7)
    assert p is not None
    assert 0.4 <= p["difficulty_score"] <= 0.7


def test_search_text(db):
    results = db.search_text("AI")
    assert len(results) >= 0


def test_get_all_pdf_names(db):
    names = db.get_all_pdf_names()
    assert len(names) == 22


# ── Vector store tests (require built data + model) ──


@pytest.fixture
def vs():
    from knowledge_base.vector_store import VectorStore
    chroma_path = DATA_DIR / "chroma_db"
    if not chroma_path.exists():
        pytest.skip("ChromaDB not built yet")
    return VectorStore(chroma_path)


def test_vector_store_count(vs, db):
    assert vs.count() == db.count()


def test_search_returns_results(vs):
    results = vs.search("machine learning", n_results=5)
    assert len(results) > 0


def test_search_by_pdf_filters(vs, db):
    names = db.get_all_pdf_names()
    results = vs.search_by_pdf("test query", names[0], n_results=5)
    assert all(r["pdf_name"] == names[0] for r in results)


def test_search_result_format(vs):
    results = vs.search("neural network", n_results=1)
    assert len(results) > 0
    r = results[0]
    for key in ("id", "text", "distance", "pdf_name", "opening_sentence"):
        assert key in r
