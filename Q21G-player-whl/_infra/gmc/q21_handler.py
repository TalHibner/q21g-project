"""Q21 Handler - routes Q21 messages to appropriate phase handlers.

This module handles all Q21G protocol messages from the referee
and routes them to the appropriate game phase handlers.
"""
from typing import Any, Callable, Optional
from dataclasses import dataclass


@dataclass
class Q21Response:
    """Response data from handling a Q21 message."""
    message_type: str
    payload: dict
    recipient: str
    correlation_id: Optional[str] = None


class Q21Handler:
    """Routes Q21 messages to appropriate game phase handlers.

    Handles the following message types (Q21G.v1 protocol - no underscores):
    - Q21WARMUPCALL -> execute warmup phase
    - Q21ROUNDSTART -> initialize round and trigger questions
    - Q21ANSWERSBATCH -> receive answers and submit guess
    - Q21SCOREFEEDBACK -> handle score notification

    Response message types:
    - Q21WARMUPRESPONSE
    - Q21QUESTIONSBATCH
    - Q21GUESSSUBMISSION
    """

    # Message type constants (Q21G.v1 protocol - NO underscores)
    WARMUP_CALL = "Q21WARMUPCALL"
    ROUND_START = "Q21ROUNDSTART"
    ANSWERS_BATCH = "Q21ANSWERSBATCH"
    SCORE_FEEDBACK = "Q21SCOREFEEDBACK"

    # Response message types
    WARMUP_RESPONSE = "Q21WARMUPRESPONSE"
    QUESTIONS_BATCH = "Q21QUESTIONSBATCH"
    GUESS_SUBMISSION = "Q21GUESSSUBMISSION"

    def __init__(self) -> None:
        """Initialize the Q21Handler with message routing table."""
        self._handlers: dict[str, Callable[..., Optional[Q21Response]]] = {
            self.WARMUP_CALL: self._handle_warmup,
            self.ROUND_START: self._handle_round_start,
            self.ANSWERS_BATCH: self._handle_answers,
            self.SCORE_FEEDBACK: self._handle_score,
        }

    def dispatch(
        self,
        msg_type: str,
        payload: dict[str, Any],
        sender: str,
        player_email: str,
        request_id: Optional[str] = None
    ) -> Optional[Q21Response]:
        """Dispatch Q21 message to appropriate handler.

        Args:
            msg_type: The Q21 message type (e.g., Q21_WARMUP_CALL).
            payload: Message payload containing game data.
            sender: Sender email (referee).
            player_email: Player's email address.
            request_id: Optional correlation/request ID.

        Returns:
            Q21Response with response data, or None if no response needed.

        Raises:
            ValueError: If message type is unknown.
        """
        handler = self._handlers.get(msg_type)
        if handler is None:
            raise ValueError(f"Unknown Q21 message type: {msg_type}")

        return handler(payload, sender, player_email, request_id)

    def _handle_warmup(
        self,
        payload: dict[str, Any],
        sender: str,
        player_email: str,
        request_id: Optional[str]
    ) -> Q21Response:
        """Handle Q21WARMUPCALL - solve warmup question."""
        raise NotImplementedError("Q21Handler._handle_warmup() - Part 4")

    def _handle_round_start(
        self,
        payload: dict[str, Any],
        sender: str,
        player_email: str,
        request_id: Optional[str]
    ) -> Q21Response:
        """Handle Q21ROUNDSTART - receive book info and respond with Q21QUESTIONSBATCH."""
        raise NotImplementedError("Q21Handler._handle_round_start() - Part 5")

    def _handle_answers(
        self,
        payload: dict[str, Any],
        sender: str,
        player_email: str,
        request_id: Optional[str]
    ) -> Q21Response:
        """Handle Q21ANSWERSBATCH - receive answers and respond with Q21GUESSSUBMISSION."""
        raise NotImplementedError("Q21Handler._handle_answers() - Part 6")

    def _handle_score(
        self,
        payload: dict[str, Any],
        sender: str,
        player_email: str,
        request_id: Optional[str]
    ) -> Optional[Q21Response]:
        """Handle Q21SCOREFEEDBACK - process game score.

        Returns None as score feedback doesn't require a response (terminal message).
        """
        raise NotImplementedError("Q21Handler._handle_score() - Part 7")
