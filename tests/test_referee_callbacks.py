"""Tests for referee AI callbacks: warmup, round start, and answers."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent / "Q21G-referee-whl" / "examples"
sys.path.insert(0, str(EXAMPLES_DIR))


@pytest.fixture
def ai():
    with patch("anthropic.Anthropic"):
        from my_ai import MyRefereeAI
        return MyRefereeAI()


def _mock_llm_hint(*_args, **_kwargs):
    return {
        "book_hint": "Computational paradigm for sequential data modeling",
        "association_word": "gradient",
        "association_domain": "mathematics",
    }


# ── Callback 1: Warmup (no LLM) ──


def test_warmup_returns_math_question(ai):
    ctx = {"dynamic": {"round_number": 1, "round_id": "R1"}, "service": {}}
    result = ai.get_warmup_question(ctx)
    assert "warmup_question" in result
    q = result["warmup_question"]
    assert "What is" in q
    assert any(op in q for op in ["+", "-", "*"])


def test_warmup_varies_across_calls(ai):
    ctx = {"dynamic": {"round_number": 1, "round_id": "R1"}, "service": {}}
    questions = {ai.get_warmup_question(ctx)["warmup_question"] for _ in range(10)}
    assert len(questions) > 1


# ── Callback 2: Round start (mocked LLM) ──


def test_round_start_selects_paragraph(ai):
    with patch("my_ai.generate_hint_and_word", side_effect=_mock_llm_hint):
        ctx = {
            "dynamic": {
                "round_number": 1, "round_id": "R1",
                "player_a": {"id": "P1", "email": "a@t.com", "warmup_answer": "5"},
                "player_b": {"id": "P2", "email": "b@t.com", "warmup_answer": "5"},
            },
            "service": {},
        }
        result = ai.get_round_start_info(ctx)

        assert "book_name" in result
        assert "book_hint" in result
        assert "association_word" in result
        assert ai._paragraph_text is not None
        assert ai._opening_sentence is not None
        assert ai._association_word == "gradient"


def test_round_start_medium_difficulty(ai):
    with patch("my_ai.generate_hint_and_word", side_effect=_mock_llm_hint):
        ctx = {
            "dynamic": {
                "round_number": 1, "round_id": "R1",
                "player_a": {"id": "P1", "email": "a@t.com", "warmup_answer": "5"},
                "player_b": {"id": "P2", "email": "b@t.com", "warmup_answer": "5"},
            },
            "service": {},
        }
        ai.get_round_start_info(ctx)
        wc = len(ai._paragraph_text.split())
        assert wc >= 30


# ── Callback 3: Answers (mocked LLM) ──


def test_answers_returns_20(ai):
    ai._paragraph_text = "This is a test paragraph about machine learning."
    questions = [
        {"question_number": i, "question_text": f"Q{i}?",
         "options": {"A": "Yes", "B": "No", "C": "Maybe", "D": "N/A"}}
        for i in range(1, 21)
    ]
    mock_answers = [{"question_number": i, "answer": "A"} for i in range(1, 21)]

    with patch("my_ai.answer_questions", return_value=mock_answers):
        ctx = {"dynamic": {"questions": questions}, "service": {}}
        result = ai.get_answers(ctx)
        assert len(result["answers"]) == 20
        assert all(a["answer"] in ("A", "B", "C", "D", "Not Relevant")
                   for a in result["answers"])


def test_answers_fallback_when_no_paragraph(ai):
    """When no paragraph stored, return Not Relevant for all."""
    ai._paragraph_text = None
    questions = [
        {"question_number": i, "question_text": f"Q{i}?",
         "options": {"A": "Y", "B": "N", "C": "M", "D": "X"}}
        for i in range(1, 21)
    ]
    ctx = {"dynamic": {"questions": questions}, "service": {}}
    result = ai.get_answers(ctx)
    assert all(a["answer"] == "Not Relevant" for a in result["answers"])


# ── Callback 2: Domain vs secret word ──


def test_round_start_returns_domain_not_secret(ai):
    """association_word in return should be domain, not the actual secret word."""
    mock_result = {
        "book_hint": "Some topic description",
        "association_word": "gradient",
        "association_domain": "mathematics",
    }
    with patch("my_ai.generate_hint_and_word", return_value=mock_result):
        ctx = {
            "dynamic": {
                "round_number": 1, "round_id": "R1",
                "player_a": {"id": "P1", "email": "a@t.com", "warmup_answer": "5"},
                "player_b": {"id": "P2", "email": "b@t.com", "warmup_answer": "5"},
            },
            "service": {},
        }
        result = ai.get_round_start_info(ctx)
    assert result["association_word"] == "mathematics"
    assert ai._association_word == "gradient"
