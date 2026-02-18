"""
my_player.py — Q21G Player AI Implementation
==============================================

Building Block: MyPlayerAI (4 SDK callbacks)
    Input Data:  ctx dicts from SDK with dynamic fields per callback
    Output Data: warmup answer, 20 questions, final guess (sentence + word), score log
    Setup Data:  knowledge_base (SQLite + ChromaDB), ANTHROPIC_API_KEY, skills/*.md prompts
"""

import sys
from pathlib import Path

import anthropic
from q21_player import PlayerAI
from knowledge_base.db import ParagraphDB
from knowledge_base.vector_store import VectorStore

# Add player dir to path for helper imports
_PLAYER_DIR = Path(__file__).resolve().parent
if str(_PLAYER_DIR) not in sys.path:
    sys.path.insert(0, str(_PLAYER_DIR))

from player_helpers import (
    solve_warmup,
    search_candidates,
    generate_questions,
    make_guess,
)


class MyPlayerAI(PlayerAI):

    def __init__(self):
        self._db = ParagraphDB()
        self._vs = VectorStore()
        self._client = anthropic.Anthropic()
        # State stored across callbacks (per round)
        self._candidates = []
        self._questions_sent = []

    # ── Callback 1: Warmup Answer ──────────────────────────

    def get_warmup_answer(self, ctx: dict) -> dict:
        """Parse and solve the math question (no LLM needed)."""
        question = ctx["dynamic"]["warmup_question"]
        return {"answer": solve_warmup(question)}

    # ── Callback 2: Generate 20 Questions ──────────────────

    def get_questions(self, ctx: dict) -> dict:
        """Search knowledge base for candidates, generate discriminating questions."""
        book_name = ctx["dynamic"]["book_name"]
        book_hint = ctx["dynamic"].get("book_hint", "")
        association_word = ctx["dynamic"].get("association_word", "")

        # Search for candidate paragraphs (top-20 for better recall)
        self._candidates = search_candidates(
            self._vs, self._db, book_name, book_hint, n=20,
        )

        # Generate 20 strategic questions via LLM
        questions = generate_questions(
            self._client, self._candidates,
            book_name, book_hint, association_word,
        )
        self._questions_sent = questions
        return {"questions": questions}

    # ── Callback 3: Make Final Guess ───────────────────────

    def get_guess(self, ctx: dict) -> dict:
        """Re-rank candidates using Q&A answers, look up exact opening sentence."""
        answers = ctx["dynamic"]["answers"]
        book_name = ctx["dynamic"].get("book_name", "")
        book_hint = ctx["dynamic"].get("book_hint", "")
        association_word = ctx["dynamic"].get("association_word", "")

        # If no candidates stored, do a fresh search
        if not self._candidates:
            self._candidates = search_candidates(
                self._vs, self._db, book_name, book_hint, n=20,
            )

        return make_guess(
            self._client, self._candidates, self._questions_sent,
            answers, book_name, book_hint, association_word,
        )

    # ── Callback 4: Score Received ─────────────────────────

    def on_score_received(self, ctx: dict) -> None:
        """Log results for analysis."""
        points = ctx["dynamic"].get("league_points", 0)
        score = ctx["dynamic"].get("private_score", 0)
        match_id = ctx["dynamic"].get("match_id", "unknown")
        print(f"Game {match_id}: {points} league pts, {score} private score")
