"""Player guess maker — re-ranks candidates using Q&A and produces final guess.

Building Block: make_guess
    Input Data:  Anthropic client, candidate list, questions_sent, answers,
                 book_name, book_hint, association_word
    Output Data: {opening_sentence, sentence_justification, associative_word,
                 word_justification, confidence}
    Setup Data:  skills/player_guess_maker.md, ANTHROPIC_API_KEY
"""

import json
import logging
import random
import re
from pathlib import Path

import anthropic

SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"
logger = logging.getLogger(__name__)


def _load_skill(name: str) -> str:
    return (SKILLS_DIR / name).read_text(encoding="utf-8")


def make_guess(client, candidates: list, questions_sent: list,
               answers: list, book_name: str, book_hint: str,
               association_word: str) -> dict:
    """Re-rank candidates using Q&A answers and produce final guess."""
    from player_helpers import call_llm

    skill = _load_skill("player_guess_maker.md")

    # Format Q&A pairs
    qa_text = ""
    for a in answers:
        q = next((q for q in questions_sent
                  if q["question_number"] == a["question_number"]), None)
        q_str = q["question_text"] if q else f"Q{a['question_number']}"
        qa_text += f"Q{a['question_number']}: {q_str} → {a['answer']}\n"

    # Shuffle candidates to remove position bias, track mapping
    top_cands = list(enumerate(candidates[:8]))  # (original_idx, candidate)
    random.shuffle(top_cands)
    idx_map = {}  # shuffled_pos → original_idx

    cand_text = ""
    for shuffled_i, (orig_idx, c) in enumerate(top_cands, 1):
        idx_map[shuffled_i] = orig_idx
        opening = c.get("opening_sentence", c.get("metadata", {}).get("opening_sentence", ""))
        text_preview = c.get("full_text", c.get("text", c.get("document", "")))[:300]
        cand_text += f"Candidate {shuffled_i} (opening: \"{opening}\"): {text_preview}...\n\n"

    prompt = f"""{skill}

CONTEXT:
- book_name: {book_name}
- book_hint: {book_hint}
- association_word (domain): {association_word}

Q&A EVIDENCE:
{qa_text}

CANDIDATE PARAGRAPHS:
{cand_text if cand_text else "No candidates available."}

INSTRUCTIONS (follow exactly):

STEP 1 — SCORE: For each candidate, count Q&A answers CONSISTENT with it.
STEP 2 — PICK: Choose the candidate with the HIGHEST consistency score.
STEP 3 — ASSOCIATION WORD: From the chosen candidate's text, extract the 3 most important keywords. Pick the one most related to the domain "{association_word}". Use an ACTUAL word from the paragraph, not an abstract guess.
STEP 4 — JUSTIFY with Q&A citations:

sentence_justification MUST cite ≥3 specific Q numbers with answers. Example format:
"Q3(A) confirmed the paragraph discusses attention mechanisms, Q7(B) ruled out transformer architecture, Q12(A) confirmed a definition-style opening, making Candidate 5 the strongest match with 16/20 consistent answers."

word_justification MUST cite ≥2 specific Q numbers. Example format:
"Q17(A) confirmed the word relates to computation, and Q18(B) narrowed it to a specific technique mentioned in the paragraph."

Respond as JSON:
{{"scores": "C1:X, C2:Y, ...", "chosen_candidate": 1,
  "sentence_justification": "30-50 words citing Q numbers...",
  "associative_word": "keyword from paragraph text within {association_word} domain",
  "word_justification": "20-30 words citing Q numbers...",
  "confidence": 0.8}}"""

    try:
        raw = call_llm(client, prompt, max_tokens=1500)
    except (anthropic.APIError, anthropic.APIConnectionError):
        logger.error("LLM failed for guess — falling back to top candidate")
        raw = ""

    try:
        match = re.search(r'\{[\s\S]*\}', raw)
        data = json.loads(match.group()) if match else {}
    except (json.JSONDecodeError, AttributeError):
        data = {}

    # CRITICAL: Use the candidate's stored opening sentence, not the LLM's copy.
    # Map shuffled position back to original candidate index.
    if "chosen_candidate" in data:
        shuffled_pick = int(data["chosen_candidate"])
        orig_idx = idx_map.get(shuffled_pick, 0)
        orig_idx = max(0, min(orig_idx, len(candidates[:8]) - 1))
        chosen_cand = candidates[orig_idx] if candidates else {}
    else:
        # LLM failed — fall back to top-ranked candidate (rank 0)
        chosen_cand = candidates[0] if candidates else {}
    exact_sentence = chosen_cand.get(
        "opening_sentence",
        chosen_cand.get("metadata", {}).get("opening_sentence", ""))

    # Fallback: if LLM didn't return chosen_candidate, use its sentence text
    if not exact_sentence:
        exact_sentence = data.get("opening_sentence", "")
    # Final fallback: top candidate
    if not exact_sentence and candidates:
        c = candidates[0]
        exact_sentence = c.get("opening_sentence",
                               c.get("metadata", {}).get("opening_sentence", ""))

    return {
        "opening_sentence": exact_sentence,
        "sentence_justification": data.get("sentence_justification",
            f"Based on semantic search matching the hint '{book_hint}' "
            f"against paragraphs from {book_name}, the top candidate was selected."),
        "associative_word": data.get("associative_word", association_word),
        "word_justification": data.get("word_justification",
            f"The word relates to the domain '{association_word}' "
            f"and the paragraph's central theme as revealed by Q&A answers."),
        "confidence": float(data.get("confidence", 0.4)),
    }
