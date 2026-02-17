"""Player helper functions — warmup solver, search, question generation."""

import json
import logging
import re
from pathlib import Path

import anthropic

from player_guess import make_guess  # noqa: F401 — re-exported for my_player
from knowledge_base.llm_client import call_llm  # shared retry logic

SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"
logger = logging.getLogger(__name__)


def _load_skill(name: str) -> str:
    return (SKILLS_DIR / name).read_text(encoding="utf-8")


def solve_warmup(question: str) -> str:
    """Parse and solve a simple math question."""
    match = re.search(r'(\d+)\s*([+\-*/])\s*(\d+)', question)
    if match:
        a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
        if op == '+': return str(a + b)
        if op == '-': return str(a - b)
        if op == '*': return str(a * b)
        if op == '/': return str(a // b) if b != 0 else "0"
    return "0"


def search_candidates(vs, db, book_name: str, book_hint: str, n: int = 20) -> list[dict]:
    """Dual search: PDF-filtered (priority) + unfiltered, deduplicated."""
    # Search 1: filtered by PDF name (these are highest priority)
    filtered = vs.search_by_pdf(book_hint, book_name, n_results=n)
    # Search 2: unfiltered across all paragraphs
    unfiltered = vs.search(book_hint, n_results=n)

    # Prioritize filtered results, fill remaining with unfiltered
    seen_ids = set()
    merged = []
    for c in filtered:
        cid = c.get("id", "")
        if cid and cid not in seen_ids:
            seen_ids.add(cid)
            merged.append(c)
    for c in unfiltered:
        cid = c.get("id", "")
        if cid and cid not in seen_ids:
            seen_ids.add(cid)
            merged.append(c)

    if merged:
        return merged[:n]

    # Last resort: random from the PDF
    rows = db.get_by_pdf_name(book_name)
    return rows[:n] if rows else []


def generate_questions(client, candidates: list, book_name: str,
                       book_hint: str, association_word: str) -> list[dict]:
    """Generate 20 strategic questions via LLM."""
    skill = _load_skill("player_question_generator.md")

    # Format candidate summaries for the LLM
    cand_text = ""
    for i, c in enumerate(candidates[:8], 1):
        opening = c.get("opening_sentence", c.get("metadata", {}).get("opening_sentence", ""))
        text_preview = c.get("full_text", c.get("text", c.get("document", "")))[:200]
        cand_text += f"Candidate {i}: [{opening}] {text_preview}...\n\n"

    prompt = f"""{skill}

CONTEXT:
- book_name: {book_name}
- book_hint: {book_hint}
- association_word (domain): {association_word}

CANDIDATE PARAGRAPHS (from semantic search):
{cand_text if cand_text else "No candidates found — generate exploratory questions."}

Generate exactly 20 questions as a JSON array:
[{{"question_number": 1, "question_text": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}]"""

    try:
        raw = call_llm(client, prompt, max_tokens=3000, timeout=90.0)
    except (anthropic.APIError, anthropic.APIConnectionError):
        logger.error("LLM failed for question generation — using generic questions")
        raw = ""

    try:
        match = re.search(r'\[[\s\S]*\]', raw)
        questions = json.loads(match.group()) if match else []
    except (json.JSONDecodeError, AttributeError):
        questions = []

    # Ensure exactly 20 questions, fill gaps with generic ones
    q_map = {q["question_number"]: q for q in questions if "question_number" in q}
    result = []
    for i in range(1, 21):
        if i in q_map:
            result.append(q_map[i])
        else:
            result.append({
                "question_number": i,
                "question_text": f"Does the paragraph discuss a specific concept related to {book_hint}?",
                "options": {"A": "Yes", "B": "No", "C": "Partially", "D": "Not applicable"},
            })
    return result
