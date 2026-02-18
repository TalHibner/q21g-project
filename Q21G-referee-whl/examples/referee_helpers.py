"""Referee helpers — hint generation, question answering.

Building Block: generate_hint_and_word, answer_questions
    Input Data:  paragraph dict, Anthropic client, questions list
    Output Data: hint/word dict, answers list [{question_number, answer}]
    Setup Data:  skills/ prompts, ANTHROPIC_API_KEY, optional VectorStore
"""

import json
import logging
import re
from pathlib import Path

import anthropic

from knowledge_base.llm_client import call_llm  # shared retry logic
from knowledge_base.skill_plugin import build_default_registry
from referee_scoring import score_guess  # noqa: F401 — re-exported for my_ai

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"
logger = logging.getLogger(__name__)
_registry = build_default_registry(SKILLS_DIR)


def _load_skill(name: str) -> str:
    return _registry.get(name).get_prompt()


def _extract_words(text: str) -> set[str]:
    """Extract normalized word set from text."""
    return {c for w in text.split()
            if len(c := re.sub(r'[^\w]', '', w).lower()) > 1}


def validate_taboo(hint: str, paragraph_text: str) -> set[str]:
    """Return overlapping words between hint and paragraph."""
    return _extract_words(hint) & _extract_words(paragraph_text)


def _hint_self_test(vs, hint: str, pdf_name: str, para_id: str) -> bool:
    """Check if ChromaDB can find the paragraph using this hint."""
    if not vs:
        return True
    results = vs.search_by_pdf(hint, pdf_name, n_results=10)
    return any(r.get("id") == para_id for r in results)


def generate_hint_and_word(client, paragraph: dict, vs=None) -> dict:
    """Generate hint + association word via LLM, with optional self-test."""
    text = paragraph["full_text"]
    pdf_name = paragraph.get("pdf_name", "")
    para_id = paragraph.get("id", "")
    forbidden = _extract_words(text)
    forbidden_sample = ", ".join(sorted(forbidden)[:60])

    prompt = f"""You are a referee in a 21-questions guessing game about Hebrew academic paragraphs.

PARAGRAPH TEXT:
{text}

OPENING SENTENCE:
{paragraph["opening_sentence"]}

TASK: Generate THREE things:
1. A book_hint: max 15 words describing the paragraph's topic using ONLY synonyms/paraphrases.
   CRITICAL: The hint must NOT contain ANY of these forbidden words: {forbidden_sample}
   {"[...and more]" if len(forbidden) > 60 else ""}
2. An association_word: a specific word thematically connected to the paragraph (e.g., "river", "focus", "gradient")
3. An association_domain: the broad category of the association word (e.g., "nature", "technology", "mathematics")

The hint should be semantically specific enough to find this paragraph via vector search.

Respond in this exact JSON format only:
{{"book_hint": "...", "association_word": "...", "association_domain": "..."}}"""

    for attempt in range(2):  # Max 2 attempts per paragraph (budget: 60s total)
        try:
            raw = call_llm(client, prompt, max_tokens=200, timeout=15.0)
        except (anthropic.APIError, anthropic.APIConnectionError):
            logger.warning("LLM failed in hint generation attempt %d", attempt + 1)
            continue
        try:
            match = re.search(r'\{[^}]+\}', raw, re.DOTALL)
            result = json.loads(match.group()) if match else json.loads(raw)
        except (json.JSONDecodeError, AttributeError):
            continue

        hint = result.get("book_hint", "")
        overlap = validate_taboo(hint, text)
        if overlap:
            prompt += f"\n\nHint '{hint}' had forbidden words: {overlap}. Avoid them!"
            continue

        # Self-test: can ChromaDB find our paragraph with this hint?
        if _hint_self_test(vs, hint, pdf_name, para_id):
            return result
        prompt += "\n\nHint was valid but not semantically findable. Make it MORE specific to the paragraph's unique content."

    return {
        "book_hint": "Academic discussion of theoretical concepts from course material",
        "association_word": "concept",
        "association_domain": "academia",
    }


def answer_questions(client, paragraph_text: str, questions: list) -> list[dict]:
    """Answer all 20 questions in one LLM call."""
    q_text = ""
    for q in questions:
        opts = q.get("options", {})
        q_text += (
            f"Q{q['question_number']}: {q['question_text']}\n"
            f"  A: {opts.get('A','')}, B: {opts.get('B','')}, "
            f"C: {opts.get('C','')}, D: {opts.get('D','')}\n"
        )

    skill = _load_skill("referee_question_answerer.md")
    prompt = f"""{skill}

PARAGRAPH TEXT:
{paragraph_text}

QUESTIONS:
{q_text}

Answer each question from the paragraph's perspective. Be truthful.
Respond as a JSON array of objects: [{{"question_number": 1, "answer": "A"}}, ...]
Valid answers: "A", "B", "C", "D", or "Not Relevant"."""

    try:
        raw = call_llm(client, prompt, max_tokens=1024, timeout=60.0)
    except (anthropic.APIError, anthropic.APIConnectionError):
        logger.error("LLM failed for answer_questions — returning Not Relevant")
        return [{"question_number": q["question_number"], "answer": "Not Relevant"}
                for q in questions]

    try:
        match = re.search(r'\[[\s\S]*\]', raw)
        answers = json.loads(match.group()) if match else []
    except (json.JSONDecodeError, AttributeError):
        answers = []

    answer_map = {a["question_number"]: a["answer"] for a in answers}
    return [
        {"question_number": q["question_number"],
         "answer": answer_map.get(q["question_number"], "Not Relevant")}
        for q in questions
    ]
