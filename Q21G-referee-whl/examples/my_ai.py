"""
my_ai.py — Q21G Referee AI Implementation
==========================================

Implements 4 callbacks using knowledge base (SQLite + ChromaDB) and
Claude LLM for hint generation, question answering, and scoring.
"""

import random

import anthropic
from q21_referee import RefereeAI
from knowledge_base.db import ParagraphDB
from knowledge_base.vector_store import VectorStore

from referee_helpers import (
    generate_hint_and_word,
    answer_questions,
    score_guess,
)


class MyRefereeAI(RefereeAI):

    def __init__(self):
        self._db = ParagraphDB()
        self._vs = VectorStore()
        self._client = anthropic.Anthropic()
        # State stored across callbacks (per round)
        self._paragraph_text = None
        self._opening_sentence = None
        self._association_word = None

    # ── Callback 1: Warmup ──────────────────────────────

    def get_warmup_question(self, ctx):
        """Generate a simple math question (no LLM needed)."""
        ops = [('+', lambda a, b: a + b),
               ('-', lambda a, b: a - b),
               ('*', lambda a, b: a * b)]
        a, b = random.randint(2, 15), random.randint(2, 15)
        sym, _ = random.choice(ops)
        return {"warmup_question": f"What is {a} {sym} {b}?"}

    # ── Callback 2: Paragraph Selection + Hint ──────────

    def get_round_start_info(self, ctx):
        """Select paragraph, generate hint, choose association word."""
        _FALLBACK_HINT = "Academic discussion of theoretical concepts"

        # Try up to 3 paragraphs — retry if hint generation fails self-test
        for _attempt in range(3):
            paragraph = self._db.get_random(
                min_words=30, max_words=200,
                min_difficulty=0.4, max_difficulty=0.7,
            )
            if not paragraph:
                paragraph = self._db.get_random(min_words=30, max_words=300)

            result = generate_hint_and_word(
                self._client, paragraph, vs=self._vs,
            )
            hint = result.get("book_hint", "")
            if hint and _FALLBACK_HINT not in hint:
                break  # Good hint found

        self._paragraph_text = paragraph["full_text"]
        self._opening_sentence = paragraph["opening_sentence"]
        self._association_word = result.get("association_word", "concept")

        return {
            "book_name": paragraph["pdf_name"],
            "book_hint": result.get("book_hint", "Academic course content"),
            "association_word": result.get("association_domain", "academia"),
        }

    # ── Callback 3: Answer 20 Questions ─────────────────

    def get_answers(self, ctx):
        """Answer player's 20 questions about the secret paragraph."""
        questions = ctx["dynamic"]["questions"]

        if not self._paragraph_text:
            return {"answers": [
                {"question_number": q["question_number"], "answer": "Not Relevant"}
                for q in questions
            ]}

        answers = answer_questions(
            self._client, self._paragraph_text, questions
        )
        return {"answers": answers}

    # ── Callback 4: Score Player's Guess ────────────────

    def get_score_feedback(self, ctx):
        """Score the player's guess against actual answers."""
        guess = ctx["dynamic"]["player_guess"]

        # Use stored values (ctx may have None for these)
        actual_sentence = (
            self._opening_sentence
            or ctx["dynamic"].get("actual_opening_sentence", "")
        )
        actual_word = (
            self._association_word
            or ctx["dynamic"].get("actual_associative_word", "")
        )
        paragraph = self._paragraph_text or ""

        return score_guess(
            self._client, actual_sentence, actual_word, paragraph, guess
        )
