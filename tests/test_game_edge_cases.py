"""End-to-end edge cases: unknown book names, round variation, candidate persistence."""

import sys
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


def test_game_with_unknown_book_name(referee, player):
    """Player should still produce a valid guess even if book_name doesn't match."""
    referee._paragraph_text = "Some unknown paragraph text."
    referee._opening_sentence = "Some unknown paragraph text."
    referee._association_word = "mystery"

    with patch("player_helpers.call_llm", side_effect=lambda c, p, **kw: _route_llm_call(p)):
        questions_result = player.get_questions({
            "dynamic": {"book_name": "NonexistentLecture99",
                        "book_hint": "obscure topic from unknown source",
                        "association_word": "unknown"},
            "service": {},
        })
    assert len(questions_result["questions"]) == 20

    with patch("referee_helpers.call_llm", side_effect=lambda c, p, **kw: _route_llm_call(p)):
        answers_result = referee.get_answers({
            "dynamic": {"questions": questions_result["questions"]}, "service": {},
        })

    with patch("player_helpers.call_llm", side_effect=lambda c, p, **kw: _route_llm_call(p)):
        guess = player.get_guess({
            "dynamic": {"answers": answers_result["answers"],
                        "book_name": "NonexistentLecture99",
                        "book_hint": "obscure topic",
                        "association_word": "unknown"},
            "service": {},
        })
    assert "opening_sentence" in guess
    assert "confidence" in guess


def test_multiple_rounds_use_different_paragraphs(referee):
    """Across multiple rounds, referee should select different paragraphs."""
    paragraphs = set()
    for _ in range(5):
        with patch("my_ai.generate_hint_and_word", side_effect=_mock_hint):
            referee.get_round_start_info({
                "dynamic": {
                    "round_number": 1, "round_id": "R1",
                    "player_a": {"id": "P1", "email": "a@t.com", "warmup_answer": "5"},
                    "player_b": {"id": "P2", "email": "b@t.com", "warmup_answer": "5"},
                },
                "service": {},
            })
        paragraphs.add(referee._opening_sentence)
    assert len(paragraphs) > 1


def test_player_candidates_persist_across_callbacks(referee, player):
    """Candidates stored in get_questions must be available in get_guess."""
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
        player.get_questions({
            "dynamic": {"book_name": round_info["book_name"],
                        "book_hint": round_info["book_hint"],
                        "association_word": round_info["association_word"]},
            "service": {},
        })

    saved_candidates = player._candidates[:]
    assert len(saved_candidates) > 0

    answers = [{"question_number": i, "answer": "A"} for i in range(1, 21)]
    with patch("player_helpers.call_llm", side_effect=lambda c, p, **kw: _route_llm_call(p)):
        player.get_guess({
            "dynamic": {"answers": answers,
                        "book_name": round_info["book_name"],
                        "book_hint": round_info["book_hint"],
                        "association_word": round_info["association_word"]},
            "service": {},
        })
    assert player._candidates == saved_candidates
