"""End-to-end simulation: full game chain and score structure validation.

Uses REAL knowledge base but MOCKED LLM calls for determinism and speed.
"""

import sys
import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

REFEREE_DIR = Path(__file__).parent.parent / "Q21G-referee-whl" / "examples"
PLAYER_DIR = Path(__file__).parent.parent / "Q21G-player-whl"
sys.path.insert(0, str(REFEREE_DIR))
sys.path.insert(0, str(PLAYER_DIR))

from tests.game_mocks import _mock_hint, _route_llm_call


@pytest.fixture
def referee():
    with patch("anthropic.Anthropic"):
        from my_ai import MyRefereeAI
        return MyRefereeAI()


@pytest.fixture
def player():
    with patch("anthropic.Anthropic"):
        from my_player import MyPlayerAI
        return MyPlayerAI()


def test_full_game_chain(referee, player):
    """Simulate a complete game: warmup -> round start -> questions -> answers -> guess -> score."""
    warmup_q = referee.get_warmup_question(
        {"dynamic": {"round_number": 1, "round_id": "R1"}, "service": {}})
    warmup_a = player.get_warmup_answer(
        {"dynamic": {"warmup_question": warmup_q["warmup_question"]}, "service": {}})
    assert "answer" in warmup_a

    with patch("my_ai.generate_hint_and_word", side_effect=_mock_hint):
        round_info = referee.get_round_start_info({
            "dynamic": {
                "round_number": 1, "round_id": "R1",
                "player_a": {"id": "P1", "email": "a@t.com", "warmup_answer": warmup_a["answer"]},
                "player_b": {"id": "P2", "email": "b@t.com", "warmup_answer": "0"},
            },
            "service": {},
        })
    assert "book_name" in round_info
    assert referee._paragraph_text is not None

    with patch("player_helpers.call_llm", side_effect=lambda c, p, **kw: _route_llm_call(p)):
        questions_result = player.get_questions({
            "dynamic": {"book_name": round_info["book_name"],
                        "book_hint": round_info["book_hint"],
                        "association_word": round_info["association_word"]},
            "service": {},
        })
    assert len(questions_result["questions"]) == 20

    with patch("referee_helpers.call_llm", side_effect=lambda c, p, **kw: _route_llm_call(p)):
        answers_result = referee.get_answers({
            "dynamic": {"questions": questions_result["questions"]}, "service": {},
        })
    assert len(answers_result["answers"]) == 20

    with patch("player_helpers.call_llm", side_effect=lambda c, p, **kw: _route_llm_call(p)):
        guess = player.get_guess({
            "dynamic": {"answers": answers_result["answers"],
                        "book_name": round_info["book_name"],
                        "book_hint": round_info["book_hint"],
                        "association_word": round_info["association_word"]},
            "service": {},
        })
    for key in ("opening_sentence", "sentence_justification", "associative_word",
                "word_justification", "confidence"):
        assert key in guess

    with patch("referee_helpers.call_llm", side_effect=lambda c, p, **kw: _route_llm_call(p)):
        score = referee.get_score_feedback({
            "dynamic": {"player_guess": guess,
                        "actual_opening_sentence": None,
                        "actual_associative_word": None},
            "service": {},
        })
    assert 0 <= score["league_points"] <= 3
    assert 0 <= score["private_score"] <= 100


def test_game_produces_valid_score_structure(referee, player):
    """Verify score breakdown has all 4 components and feedback has 2 fields."""
    with patch("my_ai.generate_hint_and_word", side_effect=_mock_hint):
        round_info = referee.get_round_start_info({
            "dynamic": {
                "round_number": 1, "round_id": "R1",
                "player_a": {"id": "P1", "email": "a@t.com", "warmup_answer": "5"},
                "player_b": {"id": "P2", "email": "b@t.com", "warmup_answer": "5"},
            },
            "service": {},
        })

    with patch("player_helpers.call_llm", side_effect=lambda c, p, **kw: _route_llm_call(p)):
        qr = player.get_questions({
            "dynamic": {"book_name": round_info["book_name"],
                        "book_hint": round_info["book_hint"],
                        "association_word": round_info["association_word"]},
            "service": {},
        })

    with patch("referee_helpers.call_llm", side_effect=lambda c, p, **kw: _route_llm_call(p)):
        ar = referee.get_answers({"dynamic": {"questions": qr["questions"]}, "service": {}})

    with patch("player_helpers.call_llm", side_effect=lambda c, p, **kw: _route_llm_call(p)):
        guess = player.get_guess({
            "dynamic": {"answers": ar["answers"], "book_name": round_info["book_name"],
                        "book_hint": round_info["book_hint"],
                        "association_word": round_info["association_word"]},
            "service": {},
        })

    with patch("referee_helpers.call_llm", side_effect=lambda c, p, **kw: _route_llm_call(p)):
        score = referee.get_score_feedback({
            "dynamic": {"player_guess": guess,
                        "actual_opening_sentence": None,
                        "actual_associative_word": None},
            "service": {},
        })

    bd = score["breakdown"]
    for key in ("opening_sentence_score", "sentence_justification_score",
                "associative_word_score", "word_justification_score"):
        assert key in bd
        assert 0 <= bd[key] <= 100
    fb = score["feedback"]
    assert len(fb["opening_sentence"]) > 0
    assert len(fb["associative_word"]) > 0


def test_warmup_round_trip(referee, player):
    """Referee generates math question, player solves it correctly."""
    q = referee.get_warmup_question(
        {"dynamic": {"round_number": 1, "round_id": "R1"}, "service": {}})
    a = player.get_warmup_answer(
        {"dynamic": {"warmup_question": q["warmup_question"]}, "service": {}})
    match = re.search(r'(\d+)\s*([+\-*/])\s*(\d+)', q["warmup_question"])
    if match:
        x, op, y = int(match.group(1)), match.group(2), int(match.group(3))
        expected = {'+': x + y, '-': x - y, '*': x * y}.get(op, 0)
        assert a["answer"] == str(expected)
