"""Edge-case tests for player guess: candidate selection, fallbacks, format edge cases."""

import sys
import json
from pathlib import Path
from unittest.mock import patch

import pytest

PLAYER_DIR = Path(__file__).parent.parent / "Q21G-player-whl"
sys.path.insert(0, str(PLAYER_DIR))


@pytest.fixture(autouse=True)
def _stable_shuffle():
    with patch("player_guess.random.shuffle"):
        yield


def _mock_candidates():
    return [
        {"id": "lec1_p0001", "opening_sentence": "First sentence.",
         "full_text": "First sentence. More text here.", "metadata": {}},
        {"id": "lec1_p0002", "opening_sentence": "Second sentence.",
         "full_text": "Second sentence. More text here.", "metadata": {}},
    ]


def _make_guess_response():
    return json.dumps({
        "chosen_candidate": 1, "opening_sentence": "First sentence.",
        "sentence_justification": "Based on Q3 answer A confirming the topic " * 2,
        "associative_word": "algorithm",
        "word_justification": "Connected to computational methods in the domain.",
        "confidence": 0.85,
    })


def test_guess_uses_candidate_sentence_not_fabricated():
    from player_guess import make_guess
    cands = _mock_candidates()
    resp = json.dumps({
        "chosen_candidate": 1, "opening_sentence": "First sentence.",
        "sentence_justification": "Q&A evidence points to candidate 1. " * 2,
        "associative_word": "algo",
        "word_justification": "Related to computational methods.",
        "confidence": 0.9,
    })
    with patch("player_helpers.call_llm", return_value=resp):
        result = make_guess(None, cands, [], [], "book", "hint", "domain")
    assert result["opening_sentence"] in [c["opening_sentence"] for c in cands]


def test_guess_prefers_llm_choice_when_valid():
    from player_guess import make_guess
    cands = _mock_candidates()
    resp = json.dumps({
        "chosen_candidate": 2, "opening_sentence": "Second sentence.",
        "sentence_justification": "Evidence points to candidate 2. " * 2,
        "associative_word": "network",
        "word_justification": "Connected to the paragraph's theme.",
        "confidence": 0.75,
    })
    with patch("player_helpers.call_llm", return_value=resp):
        result = make_guess(None, cands, [], [], "book", "hint", "domain")
    assert result["opening_sentence"] == "Second sentence."
    assert result["associative_word"] == "network"


def test_guess_with_no_questions_sent():
    from player_guess import make_guess
    answers = [{"question_number": i, "answer": "A"} for i in range(1, 21)]
    cands = _mock_candidates()
    with patch("player_helpers.call_llm", return_value=_make_guess_response()):
        result = make_guess(None, cands, [], answers, "book", "hint", "domain")
    assert result["opening_sentence"] == "First sentence."


def test_guess_with_empty_candidates():
    from player_guess import make_guess
    with patch("player_helpers.call_llm", return_value="broken"):
        result = make_guess(None, [], [], [], "book", "hint", "domain")
    for key in ("opening_sentence", "sentence_justification",
                "associative_word", "word_justification", "confidence"):
        assert key in result
    assert result["associative_word"] == "domain"


def test_guess_with_all_not_relevant_answers():
    from player_guess import make_guess
    answers = [{"question_number": i, "answer": "Not Relevant"} for i in range(1, 21)]
    cands = _mock_candidates()
    resp = json.dumps({
        "chosen_candidate": 1, "opening_sentence": "First sentence.",
        "sentence_justification": "No useful Q&A signals. " * 2,
        "associative_word": "concept",
        "word_justification": "Central term in the domain.",
        "confidence": 0.3,
    })
    with patch("player_helpers.call_llm", return_value=resp):
        result = make_guess(None, cands, [], answers, "book", "hint", "domain")
    assert result["opening_sentence"] == "First sentence."
    assert result["confidence"] == 0.3


def test_guess_handles_chromadb_candidate_format():
    from player_guess import make_guess
    chromadb_cands = [
        {"id": "p1", "document": "Full text here.",
         "metadata": {"opening_sentence": "ChromaDB sentence.", "pdf_name": "lec1"}},
    ]
    with patch("player_helpers.call_llm", return_value="broken"):
        result = make_guess(None, chromadb_cands, [], [], "book", "hint", "domain")
    assert result["opening_sentence"] == "ChromaDB sentence."
