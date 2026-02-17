"""Game Executor - executes Q21 game phases.

Handles the execution of each game phase by calling the appropriate
PlayerAI callback methods and managing game state transitions.
"""
from typing import Any, Optional, Protocol


class PlayerAIProtocol(Protocol):
    """Protocol defining the PlayerAI callback interface."""

    def get_warmup_answer(self, ctx: dict) -> dict: ...
    def get_questions(self, ctx: dict) -> dict: ...
    def get_guess(self, ctx: dict) -> dict: ...
    def on_score_received(self, ctx: dict) -> None: ...


class GameExecutor:
    """Executes Q21 game phases by calling PlayerAI callbacks.

    Manages the execution flow for:
    - Warmup phase (answer math question)
    - Questions phase (generate 20 questions)
    - Guess phase (submit final guess)
    - Score phase (receive and process score)
    """

    def __init__(self, player_ai: Optional[PlayerAIProtocol] = None) -> None:
        """Initialize the GameExecutor.

        Args:
            player_ai: PlayerAI implementation for callbacks.
                       If None, will be loaded from strategy factory.
        """
        self._player_ai = player_ai

    def _get_player_ai(self) -> PlayerAIProtocol:
        """Get PlayerAI instance, loading from factory if needed."""
        if self._player_ai is None:
            from q21_player._infra.strategy.strategy_factory import get_strategy
            self._player_ai = get_strategy()._ai
        return self._player_ai

    def execute_warmup(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute warmup phase - answer the warmup question.

        Args:
            payload: Warmup call payload with:
                - match_id: Game match identifier
                - warmup_question or question: Math question to answer

        Returns:
            dict with:
                - match_id: Game match identifier
                - warmup_question: The question asked
                - warmup_answer: The computed answer
        """
        match_id = payload.get("match_id", "")
        warmup_question = payload.get("warmup_question") or payload.get("question", "")

        # Build context for PlayerAI callback
        ctx = {
            "dynamic": {"warmup_question": warmup_question},
            "service": {"match_id": match_id}
        }

        # Call PlayerAI callback
        player_ai = self._get_player_ai()
        result = player_ai.get_warmup_answer(ctx)
        warmup_answer = str(result.get("answer", "0"))

        return {
            "match_id": match_id,
            "warmup_question": warmup_question,
            "warmup_answer": warmup_answer,
        }

    def handle_round_start(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle round start - store book info for questions phase.

        Q21ROUNDSTART payload fields (per protocol):
            - match_id: Game match identifier
            - book_name: Name of the book/lecture
            - book_hint: Book hint (15 words)
            - association_word: Word from association domain (e.g., "color")
            - questions_required: Number of questions (20)
            - deadline: Question submission deadline
            - auth_token: Authentication token

        Returns:
            dict with stored book info for the round.
        """
        match_id = payload.get("match_id", "")
        book_name = payload.get("book_name", "")
        book_hint = payload.get("book_hint", "")
        association_word = payload.get("association_word", "")

        return {
            "match_id": match_id,
            "book_name": book_name,
            "book_hint": book_hint,
            "association_word": association_word,
        }

    def execute_questions(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute questions phase - generate 20 strategic questions.

        Args:
            payload: Q21ROUNDSTART payload with:
                - match_id: Game match identifier
                - book_name: Name of the book/lecture
                - book_hint: Book hint (15 words)
                - association_word: Word from association domain

        Returns:
            dict with:
                - match_id: Game match identifier
                - questions: List of 20 questions with options
        """
        match_id = payload.get("match_id", "")
        book_name = payload.get("book_name", "")
        book_hint = payload.get("book_hint", "")
        association_word = payload.get("association_word", "")

        # Build context for PlayerAI callback
        ctx = {
            "dynamic": {
                "book_name": book_name,
                "book_hint": book_hint,
                "association_word": association_word,
            },
            "service": {"match_id": match_id, "game_id": match_id}
        }

        # Call PlayerAI callback
        player_ai = self._get_player_ai()
        result = player_ai.get_questions(ctx)
        questions = result.get("questions", [])

        return {
            "match_id": match_id,
            "questions": questions,
        }

    def receive_answers(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Receive answers batch from referee.

        Args:
            payload: Answers batch payload with:
                - match_id: Game match identifier
                - answers: List of answer objects with question_number and answer

        Returns:
            dict with match_id and answers_count.
        """
        match_id = payload.get("match_id", "")
        answers = payload.get("answers", [])

        return {
            "match_id": match_id,
            "answers_count": len(answers),
            "answers": answers,
        }

    def execute_guess(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute guess phase - generate final guess based on answers.

        Args:
            payload: Payload with:
                - match_id: Game match identifier
                - book_name: Name of the book/lecture
                - book_hint: Book hint (15 words)
                - association_word: Word from association domain
                - answers: List of answers (A/B/C/D or "Not Relevant")

        Returns:
            dict with:
                - match_id: Game match identifier
                - guess: dict with opening_sentence, sentence_justification,
                         associative_word, word_justification, confidence
        """
        match_id = payload.get("match_id", "")
        book_name = payload.get("book_name", "")
        book_hint = payload.get("book_hint", "")
        association_word = payload.get("association_word", "")
        answers = payload.get("answers", [])

        # Build context for PlayerAI callback
        ctx = {
            "dynamic": {
                "book_name": book_name,
                "book_hint": book_hint,
                "association_word": association_word,
                "answers": answers,
                "questions_sent": [],  # Could be populated if questions are tracked
            },
            "service": {"match_id": match_id, "game_id": match_id}
        }

        # Call PlayerAI callback
        player_ai = self._get_player_ai()
        result = player_ai.get_guess(ctx)

        return {
            "match_id": match_id,
            "guess": {
                "opening_sentence": result.get("opening_sentence", ""),
                "sentence_justification": result.get("sentence_justification", ""),
                "associative_word": result.get("associative_word", ""),
                "word_justification": result.get("word_justification", ""),
                "confidence": float(result.get("confidence", 0.5)),
            },
        }

    def handle_score(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle score feedback - notify PlayerAI of game result.

        GAP FIX #1: This method ensures on_score_received() is called,
        which was missing in the original GmailAsPlayer implementation.

        Args:
            payload: Score feedback payload with:
                - match_id: Game match identifier
                - league_points: Points earned (0-100)
                - private_score: Internal score metric
                - breakdown: Detailed score breakdown

        Returns:
            dict with match_id and score info.
        """
        match_id = payload.get("match_id", "")
        league_points = payload.get("league_points", 0)
        private_score = payload.get("private_score", 0.0)
        breakdown = payload.get("breakdown", {})

        # Build context for PlayerAI callback
        ctx = {
            "dynamic": {
                "league_points": league_points,
                "private_score": private_score,
                "breakdown": breakdown,
            },
            "service": {"match_id": match_id}
        }

        # GAP FIX: Call PlayerAI.on_score_received() callback
        player_ai = self._get_player_ai()
        player_ai.on_score_received(ctx)

        return {
            "match_id": match_id,
            "league_points": league_points,
            "private_score": private_score,
            "breakdown": breakdown,
        }
