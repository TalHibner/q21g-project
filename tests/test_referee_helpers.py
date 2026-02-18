"""Tests for referee helper functions: taboo validation, hint generation, answer parsing."""

import sys
import json
from pathlib import Path
from unittest.mock import patch

EXAMPLES_DIR = Path(__file__).parent.parent / "Q21G-referee-whl" / "examples"
sys.path.insert(0, str(EXAMPLES_DIR))


# ── Taboo word validation ──


def test_validate_taboo():
    from referee_helpers import validate_taboo
    assert validate_taboo("cat dog", "the cat sat") == {"cat"}
    assert validate_taboo("bird flies high", "the cat sat") == set()
    assert validate_taboo("", "anything") == set()


def test_extract_words():
    from referee_helpers import _extract_words
    words = _extract_words("Hello, World! Test 123.")
    assert "hello" in words
    assert "world" in words
    assert "test" in words


def test_validate_taboo_hebrew():
    from referee_helpers import validate_taboo
    assert validate_taboo("למידת מכונה", "למידת עמוקה ורשתות") == {"למידת"}
    assert validate_taboo("ביולוגיה", "מתמטיקה ופיזיקה") == set()


def test_extract_words_filters_single_char():
    """Single-char words (Hebrew ו/ב/ל prefixes) should be filtered."""
    from referee_helpers import _extract_words
    words = _extract_words("a I ב the fox")
    assert "a" not in words
    assert "ב" not in words
    assert "fox" in words


# ── Hint generation edge cases ──


def test_hint_fallback_after_3_failures():
    """When LLM returns bad JSON 3 times, generic fallback is used."""
    from referee_helpers import generate_hint_and_word
    paragraph = {"full_text": "Some paragraph text here.", "opening_sentence": "Some."}
    with patch("referee_helpers.call_llm", return_value="not json at all"):
        result = generate_hint_and_word(None, paragraph)
    assert result["book_hint"] == "Academic discussion of theoretical concepts from course material"
    assert result["association_word"] == "concept"


def test_hint_retries_on_taboo_overlap():
    """When first hint has overlap, retries; succeeds on 2nd attempt."""
    from referee_helpers import generate_hint_and_word
    paragraph = {"full_text": "Neural networks learn patterns.", "opening_sentence": "Neural."}
    bad = json.dumps({"book_hint": "neural modeling systems",
                      "association_word": "brain", "association_domain": "biology"})
    good = json.dumps({"book_hint": "computational pattern recognition",
                       "association_word": "brain", "association_domain": "biology"})
    with patch("referee_helpers.call_llm", side_effect=[bad, good]):
        result = generate_hint_and_word(None, paragraph)
    assert result["book_hint"] == "computational pattern recognition"


# ── Answer parsing edge cases ──


def test_answers_fills_gaps_from_partial_llm():
    """When LLM only answers some questions, rest get Not Relevant."""
    from referee_helpers import answer_questions
    questions = [
        {"question_number": i, "question_text": f"Q{i}?",
         "options": {"A": "Y", "B": "N", "C": "M", "D": "X"}}
        for i in range(1, 21)
    ]
    partial = json.dumps([{"question_number": 1, "answer": "B"},
                          {"question_number": 5, "answer": "C"}])
    with patch("referee_helpers.call_llm", return_value=partial):
        result = answer_questions(None, "paragraph text", questions)
    assert len(result) == 20
    assert result[0]["answer"] == "B"
    assert result[4]["answer"] == "C"
    assert result[1]["answer"] == "Not Relevant"
    assert result[19]["answer"] == "Not Relevant"


def test_answers_all_not_relevant_on_bad_json():
    from referee_helpers import answer_questions
    questions = [
        {"question_number": i, "question_text": f"Q{i}?",
         "options": {"A": "Y", "B": "N", "C": "M", "D": "X"}}
        for i in range(1, 21)
    ]
    with patch("referee_helpers.call_llm", return_value="broken output"):
        result = answer_questions(None, "paragraph text", questions)
    assert len(result) == 20
    assert all(a["answer"] == "Not Relevant" for a in result)
