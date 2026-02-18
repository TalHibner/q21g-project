"""Tests for player question generation callback."""

import sys
import json
from pathlib import Path
from unittest.mock import patch

import pytest

PLAYER_DIR = Path(__file__).parent.parent / "Q21G-player-whl"
sys.path.insert(0, str(PLAYER_DIR))


@pytest.fixture(autouse=True)
def _stable_shuffle():
    """Disable candidate shuffling so tests get deterministic ordering."""
    with patch("player_guess.random.shuffle"):
        yield


@pytest.fixture
def ai():
    with patch("anthropic.Anthropic"):
        from my_player import MyPlayerAI
        return MyPlayerAI()


def _mock_questions_json():
    return json.dumps([
        {"question_number": i, "question_text": f"Q{i}?",
         "options": {"A": "Yes", "B": "No", "C": "Partially", "D": "N/A"}}
        for i in range(1, 21)
    ])


def _mock_candidates():
    return [
        {"id": "lec1_p0001", "opening_sentence": "First sentence.",
         "full_text": "First sentence. More text here.", "metadata": {}},
        {"id": "lec1_p0002", "opening_sentence": "Second sentence.",
         "full_text": "Second sentence. More text here.", "metadata": {}},
    ]


def test_questions_returns_20(ai):
    with patch("my_player.search_candidates", return_value=_mock_candidates()), \
         patch("my_player.generate_questions") as mock_gen:
        mock_gen.return_value = [
            {"question_number": i, "question_text": f"Q{i}?",
             "options": {"A": "Y", "B": "N", "C": "P", "D": "X"}}
            for i in range(1, 21)
        ]
        ctx = {
            "dynamic": {"book_name": "Lecture 1", "book_hint": "some hint",
                        "association_word": "tech"},
            "service": {},
        }
        result = ai.get_questions(ctx)
        assert len(result["questions"]) == 20
        assert all("question_number" in q for q in result["questions"])
        assert all("options" in q for q in result["questions"])


def test_questions_stores_candidates(ai):
    cands = _mock_candidates()
    with patch("my_player.search_candidates", return_value=cands), \
         patch("my_player.generate_questions", return_value=[
             {"question_number": i, "question_text": f"Q{i}?",
              "options": {"A": "Y", "B": "N", "C": "P", "D": "X"}}
             for i in range(1, 21)
         ]):
        ctx = {
            "dynamic": {"book_name": "Lec", "book_hint": "hint",
                        "association_word": "domain"},
            "service": {},
        }
        ai.get_questions(ctx)
        assert ai._candidates == cands
        assert len(ai._questions_sent) == 20


def test_questions_fills_gaps_on_partial_llm():
    from player_helpers import generate_questions
    partial = json.dumps([
        {"question_number": 1, "question_text": "Q1?",
         "options": {"A": "Y", "B": "N", "C": "P", "D": "X"}},
        {"question_number": 5, "question_text": "Q5?",
         "options": {"A": "Y", "B": "N", "C": "P", "D": "X"}},
    ])
    with patch("player_helpers.call_llm", return_value=partial):
        result = generate_questions(None, [], "book", "hint", "domain")
    assert len(result) == 20
    assert result[0]["question_text"] == "Q1?"
    assert result[4]["question_text"] == "Q5?"
    assert "options" in result[1]


def test_questions_all_fallback_on_bad_json():
    from player_helpers import generate_questions
    with patch("player_helpers.call_llm", return_value="not json"):
        result = generate_questions(None, [], "book", "hint", "domain")
    assert len(result) == 20
    assert all(q["options"] for q in result)


def test_questions_all_have_abcd_keys():
    """Every question must have A, B, C, D option keys."""
    from player_helpers import generate_questions
    with patch("player_helpers.call_llm", return_value=_mock_questions_json()):
        result = generate_questions(None, _mock_candidates(), "book", "hint", "domain")
    for q in result:
        assert set(q["options"].keys()) == {"A", "B", "C", "D"}, \
            f"Q{q['question_number']} missing option keys: {q['options'].keys()}"


def test_questions_fallback_also_has_abcd():
    """Gap-filled fallback questions must also have A/B/C/D."""
    from player_helpers import generate_questions
    with patch("player_helpers.call_llm", return_value="garbage"):
        result = generate_questions(None, [], "book", "hint", "domain")
    for q in result:
        assert set(q["options"].keys()) == {"A", "B", "C", "D"}
