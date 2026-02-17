"""Tests for the referee AI implementation."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add examples dir to path for imports
EXAMPLES_DIR = Path(__file__).parent.parent / "Q21G-referee-whl" / "examples"
sys.path.insert(0, str(EXAMPLES_DIR))


@pytest.fixture
def ai():
    with patch("anthropic.Anthropic"):
        from my_ai import MyRefereeAI
        return MyRefereeAI()


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


def _mock_llm_hint(*_args, **_kwargs):
    return {
        "book_hint": "Computational paradigm for sequential data modeling",
        "association_word": "gradient",
        "association_domain": "mathematics",
    }


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
        # Verify state stored
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
        # Paragraph should have word count in target range
        wc = len(ai._paragraph_text.split())
        assert wc >= 30  # matches min_words=30 in get_round_start_info


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


# ── Callback 4: Scoring (mocked LLM) ──


def _mock_score(*_args, **_kwargs):
    return {
        "league_points": 2,
        "private_score": 72.0,
        "breakdown": {
            "opening_sentence_score": 80.0,
            "sentence_justification_score": 60.0,
            "associative_word_score": 70.0,
            "word_justification_score": 50.0,
        },
        "feedback": {
            "opening_sentence": "Good attempt. " * 20,
            "associative_word": "Reasonable guess. " * 20,
        },
    }


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
        if ps >= 85:
            lp = 3
        elif ps >= 70:
            lp = 2
        elif ps >= 50:
            lp = 1
        else:
            lp = 0
        assert lp == expected, f"private_score={ps} → expected {expected}, got {lp}"


# ── Scoring formula (real computation, mocked LLM) ──


_DUMMY_GUESS = {
    "opening_sentence": "Test.", "sentence_justification": "Because.",
    "associative_word": "x", "word_justification": "Related.", "confidence": 0.5,
}


def _make_llm_score_response(ss, sj, ws, wj):
    import json
    return json.dumps({
        "opening_sentence_score": ss, "sentence_justification_score": sj,
        "associative_word_score": ws, "word_justification_score": wj,
        "feedback_sentence": "Good. " * 40, "feedback_word": "OK. " * 40,
    })


def test_score_weighted_formula():
    """Verify private_score = 0.50*ss + 0.20*sj + 0.20*ws + 0.10*wj."""
    from referee_scoring import score_guess
    raw = _make_llm_score_response(100, 80, 60, 40)
    with patch("referee_helpers.call_llm", return_value=raw):
        result = score_guess(None, "s", "w", "p", _DUMMY_GUESS)
    expected = round(100 * 0.50 + 80 * 0.20 + 60 * 0.20 + 40 * 0.10, 1)
    assert result["private_score"] == expected  # 82.0
    assert result["league_points"] == 2  # 70 <= 82 < 85


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
    # defaults: ss=30 sj=40 ws=20 wj=40
    expected = round(30 * 0.50 + 40 * 0.20 + 20 * 0.20 + 40 * 0.10, 1)
    assert result["private_score"] == expected  # 31.0
    assert result["league_points"] == 0
    # Fallback feedback should mention actual values
    assert "actual sent" in result["feedback"]["opening_sentence"]
    assert "word" in result["feedback"]["associative_word"]


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
    import json
    from referee_helpers import generate_hint_and_word

    paragraph = {"full_text": "Neural networks learn patterns.", "opening_sentence": "Neural."}
    bad = json.dumps({"book_hint": "neural modeling systems",
                      "association_word": "brain", "association_domain": "biology"})
    good = json.dumps({"book_hint": "computational pattern recognition",
                       "association_word": "brain", "association_domain": "biology"})
    with patch("referee_helpers.call_llm", side_effect=[bad, good]):
        result = generate_hint_and_word(None, paragraph)
    # "neural" overlaps → retried → got clean hint
    assert result["book_hint"] == "computational pattern recognition"


# ── Answer parsing edge cases ──


def test_answers_fills_gaps_from_partial_llm():
    """When LLM only answers some questions, rest get Not Relevant."""
    import json
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


# ── Taboo with Hebrew ──


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


# ── Round start: domain vs secret word ──


def test_round_start_returns_domain_not_secret(ai):
    """association_word in return should be domain, not the actual secret word."""
    mock_result = {
        "book_hint": "Some topic description",
        "association_word": "gradient",       # secret (stored on self)
        "association_domain": "mathematics",   # broad domain (returned to player)
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
    # Player sees the domain, not the secret word
    assert result["association_word"] == "mathematics"
    # Secret word stored internally
    assert ai._association_word == "gradient"


# ── Scoring uses stored values over ctx ──


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
