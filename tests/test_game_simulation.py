"""End-to-end simulation: referee ↔ player callback chain.

Chains: warmup → referee CB2 → player CB2 → referee CB3 → player CB3 → referee CB4.
Uses REAL knowledge base but MOCKED LLM calls for determinism and speed.
"""

import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add both examples dirs to path
REFEREE_DIR = Path(__file__).parent.parent / "Q21G-referee-whl" / "examples"
PLAYER_DIR = Path(__file__).parent.parent / "Q21G-player-whl"
sys.path.insert(0, str(REFEREE_DIR))
sys.path.insert(0, str(PLAYER_DIR))


# ── Mock LLM responses ──


def _mock_hint(client, paragraph, vs=None):
    """Deterministic hint generation — uses first 3 words as hint."""
    words = paragraph["full_text"].split()[:3]
    return {
        "book_hint": f"Topic related to academic concepts in course material",
        "association_word": "concept",
        "association_domain": "academia",
    }


def _mock_answers_llm(raw_prompt, **kwargs):
    """Return all A answers for simplicity."""
    if "QUESTIONS:" in raw_prompt:
        answers = [{"question_number": i, "answer": "A"} for i in range(1, 21)]
        return json.dumps(answers)
    return "[]"


def _mock_questions_llm(raw_prompt, **kwargs):
    """Return 20 generic questions."""
    if "Generate exactly 20" in raw_prompt:
        qs = [{"question_number": i, "question_text": f"Is this about topic {i}?",
               "options": {"A": "Yes", "B": "No", "C": "Partially", "D": "N/A"}}
              for i in range(1, 21)]
        return json.dumps(qs)
    return "[]"


def _mock_guess_llm(raw_prompt, **kwargs):
    """Pick candidate 1 and return its opening sentence."""
    # Extract the first candidate's opening sentence from the prompt
    import re
    match = re.search(r'Candidate 1 \(opening: "([^"]+)"\)', raw_prompt)
    sentence = match.group(1) if match else "Unknown sentence."
    return json.dumps({
        "chosen_candidate": 1,
        "opening_sentence": sentence,
        "sentence_justification": "Based on semantic search ranking and Q&A evidence, "
            "candidate 1 was the strongest match for the given hint and domain.",
        "associative_word": "concept",
        "word_justification": "Central concept from the paragraph's academic domain.",
        "confidence": 0.7,
    })


def _mock_score_llm(raw_prompt, **kwargs):
    """Return component scores based on actual match."""
    return json.dumps({
        "opening_sentence_score": 50,
        "sentence_justification_score": 60,
        "associative_word_score": 40,
        "word_justification_score": 50,
        "feedback_sentence": "Your guess showed understanding of the topic. " * 10,
        "feedback_word": "The association word was in the right domain. " * 10,
    })


def _route_llm_call(prompt, max_tokens=2048):
    """Route to appropriate mock based on prompt content."""
    if "QUESTIONS:" in prompt and "PARAGRAPH TEXT:" in prompt:
        return _mock_answers_llm(prompt)
    if "Generate exactly 20" in prompt:
        return _mock_questions_llm(prompt)
    if "Q&A EVIDENCE:" in prompt:
        return _mock_guess_llm(prompt)
    if "Score each component" in prompt:
        return _mock_score_llm(prompt)
    return "{}"


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


# ── Full game simulation ──


def test_full_game_chain(referee, player):
    """Simulate a complete game: warmup → round start → questions → answers → guess → score."""

    # Step 0: Warmup
    warmup_q = referee.get_warmup_question(
        {"dynamic": {"round_number": 1, "round_id": "R1"}, "service": {}})
    warmup_a = player.get_warmup_answer(
        {"dynamic": {"warmup_question": warmup_q["warmup_question"]}, "service": {}})
    assert "answer" in warmup_a

    # Step 1: Referee selects paragraph and generates hint
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
    assert "book_hint" in round_info
    assert "association_word" in round_info
    # Referee has stored secrets
    assert referee._paragraph_text is not None
    assert referee._opening_sentence is not None

    # Step 2: Player generates 20 questions using hint
    with patch("player_helpers.call_llm", side_effect=lambda c, p, **kw: _route_llm_call(p)):
        questions_result = player.get_questions({
            "dynamic": {
                "book_name": round_info["book_name"],
                "book_hint": round_info["book_hint"],
                "association_word": round_info["association_word"],
            },
            "service": {},
        })
    assert len(questions_result["questions"]) == 20
    assert player._candidates  # candidates stored

    # Step 3: Referee answers the 20 questions
    with patch("referee_helpers.call_llm", side_effect=lambda c, p, **kw: _route_llm_call(p)):
        answers_result = referee.get_answers({
            "dynamic": {"questions": questions_result["questions"]},
            "service": {},
        })
    assert len(answers_result["answers"]) == 20
    assert all(a["answer"] in ("A", "B", "C", "D", "Not Relevant")
               for a in answers_result["answers"])

    # Step 4: Player makes final guess
    with patch("player_helpers.call_llm", side_effect=lambda c, p, **kw: _route_llm_call(p)):
        guess = player.get_guess({
            "dynamic": {
                "answers": answers_result["answers"],
                "book_name": round_info["book_name"],
                "book_hint": round_info["book_hint"],
                "association_word": round_info["association_word"],
            },
            "service": {},
        })
    assert "opening_sentence" in guess
    assert "sentence_justification" in guess
    assert "associative_word" in guess
    assert "word_justification" in guess
    assert "confidence" in guess
    assert isinstance(guess["confidence"], float)

    # Step 5: Referee scores the guess
    with patch("referee_helpers.call_llm", side_effect=lambda c, p, **kw: _route_llm_call(p)):
        score = referee.get_score_feedback({
            "dynamic": {
                "player_guess": guess,
                "actual_opening_sentence": None,
                "actual_associative_word": None,
            },
            "service": {},
        })
    assert "league_points" in score
    assert "private_score" in score
    assert "breakdown" in score
    assert "feedback" in score
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
        questions_result = player.get_questions({
            "dynamic": {"book_name": round_info["book_name"],
                        "book_hint": round_info["book_hint"],
                        "association_word": round_info["association_word"]},
            "service": {},
        })

    with patch("referee_helpers.call_llm", side_effect=lambda c, p, **kw: _route_llm_call(p)):
        answers_result = referee.get_answers({
            "dynamic": {"questions": questions_result["questions"]},
            "service": {},
        })

    with patch("player_helpers.call_llm", side_effect=lambda c, p, **kw: _route_llm_call(p)):
        guess = player.get_guess({
            "dynamic": {"answers": answers_result["answers"],
                        "book_name": round_info["book_name"],
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
    assert "opening_sentence_score" in bd
    assert "sentence_justification_score" in bd
    assert "associative_word_score" in bd
    assert "word_justification_score" in bd
    assert all(0 <= v <= 100 for v in bd.values())

    fb = score["feedback"]
    assert "opening_sentence" in fb
    assert "associative_word" in fb
    assert len(fb["opening_sentence"]) > 0
    assert len(fb["associative_word"]) > 0


# ── Edge cases ──


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
            "dynamic": {"questions": questions_result["questions"]},
            "service": {},
        })

    with patch("player_helpers.call_llm", side_effect=lambda c, p, **kw: _route_llm_call(p)):
        guess = player.get_guess({
            "dynamic": {"answers": answers_result["answers"],
                        "book_name": "NonexistentLecture99",
                        "book_hint": "obscure topic",
                        "association_word": "unknown"},
            "service": {},
        })
    # Should still return valid structure, even if guess is wrong
    assert "opening_sentence" in guess
    assert "confidence" in guess


def test_warmup_round_trip(referee, player):
    """Referee generates math question, player solves it correctly."""
    ctx = {"dynamic": {"round_number": 1, "round_id": "R1"}, "service": {}}
    q = referee.get_warmup_question(ctx)
    a = player.get_warmup_answer(
        {"dynamic": {"warmup_question": q["warmup_question"]}, "service": {}})

    # Verify the player actually solved it correctly
    import re
    match = re.search(r'(\d+)\s*([+\-*/])\s*(\d+)', q["warmup_question"])
    if match:
        x, op, y = int(match.group(1)), match.group(2), int(match.group(3))
        expected = {'+': x+y, '-': x-y, '*': x*y}.get(op, 0)
        assert a["answer"] == str(expected)


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
    # With random selection from 1123 paragraphs, 5 rounds should vary
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

    # Candidates should still be the same (not cleared or replaced)
    assert player._candidates == saved_candidates
