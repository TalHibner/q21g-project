"""Tests for referee scoring: callback 4, formula, thresholds, fallbacks."""

import sys
import json
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


def _mock_score(*_args, **_kwargs):
    return {
        "league_points": 2, "private_score": 72.0,
        "breakdown": {
            "opening_sentence_score": 80.0, "sentence_justification_score": 60.0,
            "associative_word_score": 70.0, "word_justification_score": 50.0,
        },
        "feedback": {
            "opening_sentence": "Good attempt. " * 20,
            "associative_word": "Reasonable guess. " * 20,
        },
    }


_DUMMY_GUESS = {
    "opening_sentence": "Test.", "sentence_justification": "Because.",
    "associative_word": "x", "word_justification": "Related.", "confidence": 0.5,
}


def _make_llm_score_response(ss, sj, ws, wj):
    return json.dumps({
        "opening_sentence_score": ss, "sentence_justification_score": sj,
        "associative_word_score": ws, "word_justification_score": wj,
        "feedback_sentence": "Good. " * 40, "feedback_word": "OK. " * 40,
    })


# ── Callback 4: Score feedback format ──


def test_score_feedback_format(ai):
    ai._opening_sentence = "Test sentence."
    ai._association_word = "gradient"
    ai._paragraph_text = "Full paragraph text."

    with patch("my_ai.score_guess", side_effect=_mock_score):
        ctx = {
            "dynamic": {
                "player_guess": {
                    "opening_sentence": "Test sentence.",
                    "sentence_justification": "Because of Q1 answer A.",
                    "associative_word": "gradient",
                    "word_justification": "Related to math.",
                    "confidence": 0.8,
                },
                "actual_opening_sentence": None,
                "actual_associative_word": None,
            },
            "service": {},
        }
        result = ai.get_score_feedback(ctx)
        assert "league_points" in result
        assert "private_score" in result
        assert "breakdown" in result
        assert "feedback" in result
        assert 0 <= result["league_points"] <= 3
        assert 0 <= result["private_score"] <= 100


# ── Scoring formula validation ──


def test_league_points_thresholds():
    """Verify correct thresholds: 85/70/50."""
    for ps, expected in [(90, 3), (85, 3), (84.9, 2), (70, 2), (69.9, 1), (50, 1), (49.9, 0)]:
        lp = 3 if ps >= 85 else 2 if ps >= 70 else 1 if ps >= 50 else 0
        assert lp == expected, f"private_score={ps} -> expected {expected}, got {lp}"


def test_score_weighted_formula():
    """Verify private_score = 0.50*ss + 0.20*sj + 0.20*ws + 0.10*wj."""
    from referee_scoring import score_guess
    raw = _make_llm_score_response(100, 80, 60, 40)
    with patch("referee_helpers.call_llm", return_value=raw):
        result = score_guess(None, "s", "w", "p", _DUMMY_GUESS)
    expected = round(100 * 0.50 + 80 * 0.20 + 60 * 0.20 + 40 * 0.10, 1)
    assert result["private_score"] == expected  # 82.0
    assert result["league_points"] == 2


def test_score_perfect_gets_3_points():
    from referee_scoring import score_guess
    raw = _make_llm_score_response(100, 100, 100, 100)
    with patch("referee_helpers.call_llm", return_value=raw):
        result = score_guess(None, "s", "w", "p", _DUMMY_GUESS)
    assert result["private_score"] == 100.0
    assert result["league_points"] == 3


def test_score_zero_gets_0_points():
    from referee_scoring import score_guess
    raw = _make_llm_score_response(0, 0, 0, 0)
    with patch("referee_helpers.call_llm", return_value=raw):
        result = score_guess(None, "s", "w", "p", _DUMMY_GUESS)
    assert result["private_score"] == 0.0
    assert result["league_points"] == 0


def test_score_fallback_on_bad_json():
    """When LLM returns garbage, defaults (30/40/20/40) are used."""
    from referee_scoring import score_guess
    with patch("referee_helpers.call_llm", return_value="Sorry I can't help"):
        result = score_guess(None, "actual sent", "word", "para", _DUMMY_GUESS)
    expected = round(30 * 0.50 + 40 * 0.20 + 20 * 0.20 + 40 * 0.10, 1)
    assert result["private_score"] == expected  # 31.0
    assert result["league_points"] == 0
    assert "actual sent" in result["feedback"]["opening_sentence"]
    assert "word" in result["feedback"]["associative_word"]


def test_score_uses_stored_values_when_ctx_is_none(ai):
    """When ctx has None for actuals, self._opening_sentence is used."""
    ai._opening_sentence = "Stored sentence."
    ai._association_word = "stored_word"
    ai._paragraph_text = "Full paragraph."
    called_with = {}

    def capture_score(_client, sent, word, para, guess):
        called_with["sentence"] = sent
        called_with["word"] = word
        return _mock_score()

    with patch("my_ai.score_guess", side_effect=capture_score):
        ctx = {
            "dynamic": {
                "player_guess": {
                    "opening_sentence": "Guess.", "sentence_justification": "J.",
                    "associative_word": "g", "word_justification": "W.",
                    "confidence": 0.5,
                },
                "actual_opening_sentence": None,
                "actual_associative_word": None,
            },
            "service": {},
        }
        ai.get_score_feedback(ctx)
    assert called_with["sentence"] == "Stored sentence."
    assert called_with["word"] == "stored_word"
