"""Demo PlayerAI implementation for testing.

Provides predictable responses matching GmailAsPlayer's DemoPlayerAI
without requiring the LLM infrastructure.
"""
from typing import Any


class DemoAI:
    """Demo implementation with predictable responses for testing.

    Matches GmailAsPlayer's DemoPlayerAI output:
    - Warmup: returns "4"
    - Questions: 20 demo questions with A/B/C/D options
    - Guess: fixed opening sentence, "demo" word, 75% confidence
    - Score: prints to console
    """

    def get_warmup_answer(self, ctx: dict[str, Any]) -> dict[str, Any]:
        """Return fixed warmup answer.

        Args:
            ctx: Context with warmup_question in ctx["dynamic"].

        Returns:
            {"answer": "4"}
        """
        return {"answer": "4"}

    def get_questions(self, ctx: dict[str, Any]) -> dict[str, Any]:
        """Return 20 demo questions.

        Args:
            ctx: Context with book_name, book_hint, association_word.

        Returns:
            {"questions": [...]} with 20 demo questions.
        """
        questions = [
            {
                "question_number": i,
                "question_text": f"Demo question {i}?",
                "options": {"A": "Yes", "B": "No", "C": "Maybe", "D": "Unknown"},
            }
            for i in range(1, 21)
        ]
        return {"questions": questions}

    def get_guess(self, ctx: dict[str, Any]) -> dict[str, Any]:
        """Return fixed demo guess.

        Args:
            ctx: Context with answers, book_name, book_hint, association_word.

        Returns:
            Fixed guess with 75% confidence.
        """
        return {
            "opening_sentence": "Demo opening sentence for testing.",
            "sentence_justification": (
                "The opening sentence was carefully analyzed based on the pattern "
                "of answers received during the questioning phase combined with the "
                "book hint and associative domain provided at game start to make this guess."
            ),
            "associative_word": "demo",
            "word_justification": (
                "The association word was chosen based on thematic connections "
                "observed throughout the answer patterns and the overall context "
                "of the book description provided."
            ),
            "confidence": 0.75,
        }

    def on_score_received(self, ctx: dict[str, Any]) -> None:
        """Print score to console.

        Args:
            ctx: Context with league_points, private_score, breakdown.
        """
        dynamic = ctx.get("dynamic", {})
        match_id = ctx.get("service", {}).get("match_id", "unknown")
        league_points = dynamic.get("league_points", 0)
        private_score = dynamic.get("private_score", 0.0)
        print(f"[DemoAI] Game {match_id}: {league_points} pts, score={private_score}")
