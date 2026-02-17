"""Tests for the player AI implementation."""

import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add player dir to path for imports
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


# ── Callback 1: Warmup (no LLM) ──


def test_warmup_addition():
    from player_helpers import solve_warmup
    assert solve_warmup("What is 7 + 8?") == "15"


def test_warmup_subtraction():
    from player_helpers import solve_warmup
    assert solve_warmup("What is 12 - 5?") == "7"


def test_warmup_multiplication():
    from player_helpers import solve_warmup
    assert solve_warmup("What is 6 * 9?") == "54"


def test_warmup_division():
    from player_helpers import solve_warmup
    assert solve_warmup("What is 15 / 3?") == "5"


def test_warmup_division_by_zero():
    from player_helpers import solve_warmup
    assert solve_warmup("What is 10 / 0?") == "0"


def test_warmup_hebrew_format():
    from player_helpers import solve_warmup
    assert solve_warmup("?מה זה 7 * 8") == "56"


def test_warmup_fallback_on_garbage():
    from player_helpers import solve_warmup
    assert solve_warmup("no numbers here") == "0"


def test_warmup_callback_returns_dict(ai):
    ctx = {"dynamic": {"warmup_question": "What is 3 + 4?"}, "service": {}}
    result = ai.get_warmup_answer(ctx)
    assert result == {"answer": "7"}


# ── Callback 2: Questions (mocked LLM) ──


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
    # Gap-filled questions should have valid format
    assert "options" in result[1]


def test_questions_all_fallback_on_bad_json():
    from player_helpers import generate_questions
    with patch("player_helpers.call_llm", return_value="not json"):
        result = generate_questions(None, [], "book", "hint", "domain")
    assert len(result) == 20
    assert all(q["options"] for q in result)


# ── Callback 3: Guess (mocked LLM) ──


def _make_guess_response():
    return json.dumps({
        "chosen_candidate": 1,
        "opening_sentence": "First sentence.",
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

    assert "opening_sentence" in result
    assert "sentence_justification" in result
    assert "associative_word" in result
    assert "word_justification" in result
    assert "confidence" in result
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

    # Should fallback to top candidate's opening sentence
    assert result["opening_sentence"] == "First sentence."
    assert result["associative_word"] == "tech"


def test_guess_does_fresh_search_if_no_candidates(ai):
    """When candidates are empty, get_guess does a fresh search."""
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


# ── Callback 4: Score ──


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


# ── Search candidates ──


def test_search_candidates_filtered_first():
    from player_helpers import search_candidates
    mock_vs = MagicMock()
    mock_db = MagicMock()
    mock_vs.search_by_pdf.return_value = [{"id": "p1"}]
    result = search_candidates(mock_vs, mock_db, "Lec1", "hint")
    assert result == [{"id": "p1"}]
    mock_vs.search_by_pdf.assert_called_once()


def test_search_candidates_falls_back_to_all():
    from player_helpers import search_candidates
    mock_vs = MagicMock()
    mock_db = MagicMock()
    mock_vs.search_by_pdf.return_value = []
    mock_vs.search.return_value = [{"id": "p2"}]
    result = search_candidates(mock_vs, mock_db, "Lec1", "hint")
    assert result == [{"id": "p2"}]


def test_search_candidates_falls_back_to_db():
    from player_helpers import search_candidates
    mock_vs = MagicMock()
    mock_db = MagicMock()
    mock_vs.search_by_pdf.return_value = []
    mock_vs.search.return_value = []
    mock_db.get_by_pdf_name.return_value = [{"id": "p3"}, {"id": "p4"}]
    result = search_candidates(mock_vs, mock_db, "Lec1", "hint", n=1)
    assert result == [{"id": "p3"}]


def test_search_candidates_with_empty_hint():
    """Empty hint should not crash — still returns results via fallbacks."""
    from player_helpers import search_candidates
    mock_vs = MagicMock()
    mock_db = MagicMock()
    mock_vs.search_by_pdf.return_value = [{"id": "p1"}]
    result = search_candidates(mock_vs, mock_db, "Lec1", "")
    assert result == [{"id": "p1"}]
    mock_vs.search_by_pdf.assert_called_once_with("", "Lec1", n_results=20)


# ── Warmup edge cases ──


def test_warmup_extra_whitespace():
    from player_helpers import solve_warmup
    assert solve_warmup("What is  7  +  8 ?") == "15"


# ── Question format validation ──


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


# ── Guess: exact DB sentence (competitive edge) ──


def test_guess_uses_candidate_sentence_not_fabricated():
    """LLM should return EXACT opening sentence from candidate, not fabricate."""
    from player_guess import make_guess
    cands = _mock_candidates()
    # LLM returns candidate 1's exact sentence
    resp = json.dumps({
        "chosen_candidate": 1,
        "opening_sentence": "First sentence.",
        "sentence_justification": "Q&A evidence points to candidate 1. " * 2,
        "associative_word": "algo",
        "word_justification": "Related to computational methods.",
        "confidence": 0.9,
    })
    with patch("player_helpers.call_llm", return_value=resp):
        result = make_guess(None, cands, [], [], "book", "hint", "domain")
    # Verify it's the exact string from candidates, not something novel
    assert result["opening_sentence"] in [c["opening_sentence"] for c in cands]


def test_guess_prefers_llm_choice_when_valid():
    """When LLM returns valid JSON, its choice should be used over blind fallback."""
    from player_guess import make_guess
    cands = _mock_candidates()
    # LLM picks candidate 2
    resp = json.dumps({
        "chosen_candidate": 2,
        "opening_sentence": "Second sentence.",
        "sentence_justification": "Evidence points to candidate 2. " * 2,
        "associative_word": "network",
        "word_justification": "Connected to the paragraph's theme.",
        "confidence": 0.75,
    })
    with patch("player_helpers.call_llm", return_value=resp):
        result = make_guess(None, cands, [], [], "book", "hint", "domain")
    # Should use LLM's choice (candidate 2), not fallback to candidate 1
    assert result["opening_sentence"] == "Second sentence."
    assert result["associative_word"] == "network"


# ── Guess edge cases ──


def test_guess_with_empty_candidates():
    """Empty candidate list should return valid dict, not crash."""
    from player_guess import make_guess
    with patch("player_helpers.call_llm", return_value="broken"):
        result = make_guess(None, [], [], [], "book", "hint", "domain")
    assert "opening_sentence" in result
    assert "sentence_justification" in result
    assert "associative_word" in result
    assert "word_justification" in result
    assert "confidence" in result
    # Fallback to association_word from ctx
    assert result["associative_word"] == "domain"


def test_guess_with_no_questions_sent():
    """No questions_sent should still format Q&A text without crashing."""
    from player_guess import make_guess
    answers = [{"question_number": i, "answer": "A"} for i in range(1, 21)]
    cands = _mock_candidates()
    with patch("player_helpers.call_llm", return_value=_make_guess_response()):
        result = make_guess(None, cands, [], answers, "book", "hint", "domain")
    assert result["opening_sentence"] == "First sentence."


def test_guess_with_all_not_relevant_answers():
    """All 'Not Relevant' answers should still produce a valid guess."""
    from player_guess import make_guess
    answers = [{"question_number": i, "answer": "Not Relevant"} for i in range(1, 21)]
    cands = _mock_candidates()
    # LLM falls back to top candidate despite useless answers
    resp = json.dumps({
        "chosen_candidate": 1,
        "opening_sentence": "First sentence.",
        "sentence_justification": "No useful Q&A signals, relying on search rank. " * 2,
        "associative_word": "concept",
        "word_justification": "Central term in the domain.",
        "confidence": 0.3,
    })
    with patch("player_helpers.call_llm", return_value=resp):
        result = make_guess(None, cands, [], answers, "book", "hint", "domain")
    assert result["opening_sentence"] == "First sentence."
    assert result["confidence"] == 0.3


def test_guess_confidence_is_float_in_range(ai):
    """Confidence must always be a float in [0, 1]."""
    ai._candidates = _mock_candidates()
    ai._questions_sent = []
    answers = [{"question_number": i, "answer": "A"} for i in range(1, 21)]

    # Test with valid LLM response
    with patch("player_helpers.call_llm", return_value=_make_guess_response()):
        ctx = {
            "dynamic": {"answers": answers, "book_name": "Lec",
                        "book_hint": "hint", "association_word": "tech"},
            "service": {},
        }
        result = ai.get_guess(ctx)
    assert isinstance(result["confidence"], float)
    assert 0 <= result["confidence"] <= 1

    # Test with fallback (bad JSON)
    with patch("player_helpers.call_llm", return_value="garbage"):
        result2 = ai.get_guess(ctx)
    assert isinstance(result2["confidence"], float)
    assert 0 <= result2["confidence"] <= 1


# ── Guess with metadata-style candidates (ChromaDB format) ──


def test_guess_handles_chromadb_candidate_format():
    """Candidates from ChromaDB have metadata dict instead of flat fields."""
    from player_guess import make_guess
    chromadb_cands = [
        {"id": "p1", "document": "Full text here.",
         "metadata": {"opening_sentence": "ChromaDB sentence.", "pdf_name": "lec1"}},
    ]
    with patch("player_helpers.call_llm", return_value="broken"):
        result = make_guess(None, chromadb_cands, [], [], "book", "hint", "domain")
    # Should extract opening_sentence from metadata
    assert result["opening_sentence"] == "ChromaDB sentence."
