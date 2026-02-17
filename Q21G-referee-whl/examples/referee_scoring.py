"""Referee scoring — LLM-based guess evaluation and league point calculation."""

import json
import logging
import re
from difflib import SequenceMatcher
from pathlib import Path

import anthropic

MODEL = "claude-sonnet-4-20250514"
SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"
logger = logging.getLogger(__name__)


def _load_skill(name: str) -> str:
    return (SKILLS_DIR / name).read_text(encoding="utf-8")


def _string_similarity(a: str, b: str) -> float:
    """Normalized character-level similarity using SequenceMatcher."""
    return SequenceMatcher(None, a.strip(), b.strip()).ratio()


def score_guess(client, opening_sentence: str, association_word: str,
                paragraph_text: str, guess: dict) -> dict:
    """Score a player's guess via LLM with string pre-check. Returns full scoring dict."""
    from referee_helpers import call_llm

    # ── String pre-check: override LLM for obvious matches ──
    sentence_sim = _string_similarity(
        guess["opening_sentence"], opening_sentence)
    word_sim = _string_similarity(
        guess["associative_word"], association_word)

    # Determine if pre-check should override sentence score
    sentence_override = None
    if sentence_sim >= 0.95:
        sentence_override = 98.0
    elif sentence_sim >= 0.85:
        sentence_override = 88.0
    elif sentence_sim >= 0.70:
        sentence_override = 75.0

    word_override = None
    if word_sim >= 0.90:
        word_override = 95.0

    # ── LLM scoring ──
    skill = _load_skill("referee_scorer.md")
    prompt = f"""{skill}

ACTUAL OPENING SENTENCE: {opening_sentence}
ACTUAL ASSOCIATION WORD: {association_word}
PARAGRAPH TEXT: {paragraph_text}

PLAYER'S GUESS:
- Opening sentence: {guess["opening_sentence"]}
- Sentence justification: {guess["sentence_justification"]}
- Associative word: {guess["associative_word"]}
- Word justification: {guess["word_justification"]}
- Confidence: {guess["confidence"]}

Score each component 0-100. Compute private_score as the weighted sum.
Use league point thresholds: >=85→3, >=70→2, >=50→1, <50→0.
Write 150-200 word feedback for each of the two feedback fields.

Respond in this exact JSON format:
{{"opening_sentence_score": N, "sentence_justification_score": N,
  "associative_word_score": N, "word_justification_score": N,
  "feedback_sentence": "150-200 words...",
  "feedback_word": "150-200 words..."}}"""

    try:
        raw = call_llm(client, prompt, max_tokens=2048, timeout=90.0)
    except (anthropic.APIError, anthropic.APIConnectionError):
        logger.error("LLM failed for scoring — using pre-check scores only")
        raw = ""

    try:
        match = re.search(r'\{[\s\S]*\}', raw)
        data = json.loads(match.group()) if match else {}
    except (json.JSONDecodeError, AttributeError):
        data = {}

    # Apply overrides or use LLM scores
    ss = sentence_override or float(data.get("opening_sentence_score", 30))
    sj = float(data.get("sentence_justification_score", 40))
    ws = word_override or float(data.get("associative_word_score", 20))
    wj = float(data.get("word_justification_score", 40))

    private_score = round(ss * 0.50 + sj * 0.20 + ws * 0.20 + wj * 0.10, 1)

    if private_score >= 85:
        lp = 3
    elif private_score >= 70:
        lp = 2
    elif private_score >= 50:
        lp = 1
    else:
        lp = 0

    return {
        "league_points": lp,
        "private_score": private_score,
        "breakdown": {
            "opening_sentence_score": ss,
            "sentence_justification_score": sj,
            "associative_word_score": ws,
            "word_justification_score": wj,
        },
        "feedback": {
            "opening_sentence": data.get("feedback_sentence",
                f"Your guess was compared against the actual opening sentence. "
                f"Score: {ss}/100. The actual sentence was: {opening_sentence[:100]}..."),
            "associative_word": data.get("feedback_word",
                f"Your association word was compared against the actual word. "
                f"Score: {ws}/100. The actual word was: {association_word}."),
        },
    }
