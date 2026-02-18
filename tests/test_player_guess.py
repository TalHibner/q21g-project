"""Tests for player guess callback: get_guess, on_score_received, confidence."""

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


@pytest.fixture
def ai():
    with patch("anthropic.Anthropic"):
        from my_player import MyPlayerAI
        return MyPlayerAI()


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


def test_guess_returns_all_fields(ai):
    ai._candidates = _mock_candidates()
    ai._questions_sent = [
        {"question_number": i, "question_text": f"Q{i}?",
         "options": {"A": "Y", "B": "N", "C": "P", "D": "X"}}
        for i in range(1, 21)
    ]
    answers = [{"question_number": i, "answer": "A"} for i in range(1, 21)]
    with patch("player_helpers.call_llm", return_value=_make_guess_response()):
        ctx = {
            "dynamic": {"answers": answers, "book_name": "Lec",
                        "book_hint": "hint", "association_word": "tech"},
            "service": {},
        }
        result = ai.get_guess(ctx)
    for key in ("opening_sentence", "sentence_justification", "associative_word",
                "word_justification", "confidence"):
        assert key in result
    assert 0 <= result["confidence"] <= 1


def test_guess_fallback_on_bad_json(ai):
    ai._candidates = _mock_candidates()
    ai._questions_sent = []
    answers = [{"question_number": i, "answer": "B"} for i in range(1, 21)]
    with patch("player_helpers.call_llm", return_value="broken output"):
        ctx = {
            "dynamic": {"answers": answers, "book_name": "Lec",
                        "book_hint": "hint", "association_word": "tech"},
            "service": {},
        }
        result = ai.get_guess(ctx)
    assert result["opening_sentence"] == "First sentence."
    assert result["associative_word"] == "tech"


def test_guess_does_fresh_search_if_no_candidates(ai):
    ai._candidates = []
    ai._questions_sent = []
    answers = [{"question_number": i, "answer": "A"} for i in range(1, 21)]
    fresh_cands = _mock_candidates()
    with patch("my_player.search_candidates", return_value=fresh_cands), \
         patch("player_helpers.call_llm", return_value=_make_guess_response()):
        ctx = {
            "dynamic": {"answers": answers, "book_name": "Lec",
                        "book_hint": "hint", "association_word": "tech"},
            "service": {},
        }
        result = ai.get_guess(ctx)
    assert ai._candidates == fresh_cands
    assert result["opening_sentence"] == "First sentence."


def test_on_score_received(ai, capsys):
    ctx = {
        "dynamic": {"league_points": 3, "private_score": 92.0,
                     "match_id": "0101001"},
        "service": {},
    }
    ai.on_score_received(ctx)
    out = capsys.readouterr().out
    assert "0101001" in out
    assert "3" in out


def test_guess_confidence_is_float_in_range(ai):
    ai._candidates = _mock_candidates()
    ai._questions_sent = []
    answers = [{"question_number": i, "answer": "A"} for i in range(1, 21)]
    with patch("player_helpers.call_llm", return_value=_make_guess_response()):
        ctx = {"dynamic": {"answers": answers, "book_name": "Lec",
                            "book_hint": "hint", "association_word": "tech"}, "service": {}}
        result = ai.get_guess(ctx)
    assert isinstance(result["confidence"], float)
    assert 0 <= result["confidence"] <= 1
    with patch("player_helpers.call_llm", return_value="garbage"):
        result2 = ai.get_guess(ctx)
    assert isinstance(result2["confidence"], float)
    assert 0 <= result2["confidence"] <= 1
