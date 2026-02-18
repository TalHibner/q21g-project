"""Live end-to-end simulation with REAL Claude LLM calls.

Requires ANTHROPIC_API_KEY environment variable.
Run: pytest tests/test_live_simulation.py -v -s
"""

import sys
import os
from pathlib import Path

import pytest

# Skip entire module if no API key
pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)

REFEREE_DIR = Path(__file__).parent.parent / "Q21G-referee-whl" / "examples"
PLAYER_DIR = Path(__file__).parent.parent / "Q21G-player-whl"
sys.path.insert(0, str(REFEREE_DIR))
sys.path.insert(0, str(PLAYER_DIR))


@pytest.fixture
def referee():
    from my_ai import MyRefereeAI
    return MyRefereeAI()


@pytest.fixture
def player():
    from my_player import MyPlayerAI
    return MyPlayerAI()


def test_live_full_game(referee, player):
    """Full game with REAL LLM: warmup → hint → questions → answers → guess → score."""

    # Step 0: Warmup (no LLM)
    warmup_q = referee.get_warmup_question(
        {"dynamic": {"round_number": 1, "round_id": "R1"}, "service": {}})
    print(f"\n{'='*60}")
    print(f"WARMUP: {warmup_q['warmup_question']}")

    warmup_a = player.get_warmup_answer(
        {"dynamic": {"warmup_question": warmup_q["warmup_question"]}, "service": {}})
    print(f"ANSWER: {warmup_a['answer']}")

    # Step 1: Referee selects paragraph + generates hint (REAL LLM)
    print(f"\n{'='*60}")
    print("STEP 1: Referee selecting paragraph and generating hint...")
    round_info = referee.get_round_start_info({
        "dynamic": {
            "round_number": 1, "round_id": "R1",
            "player_a": {"id": "P1", "email": "a@t.com",
                         "warmup_answer": warmup_a["answer"]},
            "player_b": {"id": "P2", "email": "b@t.com", "warmup_answer": "0"},
        },
        "service": {},
    })
    print(f"  book_name: {round_info['book_name']}")
    print(f"  book_hint: {round_info['book_hint']}")
    print(f"  association_word: {round_info['association_word']}")
    print(f"  [SECRET] opening_sentence: {referee._opening_sentence[:80]}...")
    print(f"  [SECRET] association_word: {referee._association_word}")

    assert round_info["book_name"]
    assert round_info["book_hint"]
    assert round_info["association_word"]

    # Step 2: Player generates 20 questions (REAL LLM)
    print(f"\n{'='*60}")
    print("STEP 2: Player generating 20 questions...")
    questions_result = player.get_questions({
        "dynamic": {
            "book_name": round_info["book_name"],
            "book_hint": round_info["book_hint"],
            "association_word": round_info["association_word"],
        },
        "service": {},
    })
    qs = questions_result["questions"]
    print(f"  Generated {len(qs)} questions")
    for q in qs[:5]:
        print(f"    Q{q['question_number']}: {q['question_text'][:60]}")
    print(f"    ... ({len(qs) - 5} more)")
    print(f"  Candidates found: {len(player._candidates)}")

    assert len(qs) == 20
    assert all("options" in q for q in qs)

    # Step 3: Referee answers questions (REAL LLM)
    print(f"\n{'='*60}")
    print("STEP 3: Referee answering 20 questions...")
    answers_result = referee.get_answers({
        "dynamic": {"questions": qs},
        "service": {},
    })
    ans = answers_result["answers"]
    print(f"  Answered {len(ans)} questions")
    for a in ans[:5]:
        print(f"    Q{a['question_number']}: {a['answer']}")
    print(f"    ... ({len(ans) - 5} more)")

    assert len(ans) == 20
    assert all(a["answer"] in ("A", "B", "C", "D", "Not Relevant") for a in ans)

    # Step 4: Player makes final guess (REAL LLM)
    print(f"\n{'='*60}")
    print("STEP 4: Player making final guess...")
    guess = player.get_guess({
        "dynamic": {
            "answers": ans,
            "book_name": round_info["book_name"],
            "book_hint": round_info["book_hint"],
            "association_word": round_info["association_word"],
        },
        "service": {},
    })
    print(f"  opening_sentence: {guess['opening_sentence'][:80]}...")
    print(f"  associative_word: {guess['associative_word']}")
    print(f"  confidence: {guess['confidence']}")
    print(f"  justification: {guess['sentence_justification'][:80]}...")

    assert guess["opening_sentence"]
    assert guess["associative_word"]
    assert isinstance(guess["confidence"], float)

    # Step 5: Referee scores the guess (REAL LLM)
    print(f"\n{'='*60}")
    print("STEP 5: Referee scoring guess...")
    score = referee.get_score_feedback({
        "dynamic": {
            "player_guess": guess,
            "actual_opening_sentence": None,
            "actual_associative_word": None,
        },
        "service": {},
    })
    print(f"  league_points: {score['league_points']}")
    print(f"  private_score: {score['private_score']:.1f}")
    print(f"  breakdown: {score['breakdown']}")
    print(f"  feedback (sentence): {score['feedback']['opening_sentence'][:80]}...")
    print(f"  feedback (word): {score['feedback']['associative_word'][:80]}...")

    # Compare guess vs actual
    print(f"\n{'='*60}")
    print("COMPARISON:")
    print(f"  Actual sentence: {referee._opening_sentence[:80]}...")
    print(f"  Guessed sentence: {guess['opening_sentence'][:80]}...")
    match = guess["opening_sentence"].strip() == referee._opening_sentence.strip()
    print(f"  EXACT MATCH: {'YES' if match else 'NO'}")

    assert 0 <= score["league_points"] <= 3
    assert 0 <= score["private_score"] <= 100
    assert "breakdown" in score
    assert "feedback" in score
