"""GMC Controller - Game lifecycle orchestrator.

Manages the full lifecycle of a single Q21 game match.
Coordinates Q21Handler and GameExecutor for game execution.
"""
from typing import Any, Optional, TYPE_CHECKING

from _infra.gmc.game_executor import GameExecutor, PlayerAIProtocol
from _infra.gmc.q21_handler import Q21Handler, Q21Response

if TYPE_CHECKING:
    from _infra.rlgm.gprm import GPRM, GameResult


class GMController:
    """Orchestrates a single Q21 game lifecycle.

    Takes GPRM (game parameters) as input and returns GameResult.
    Coordinates Q21Handler and GameExecutor for game execution.
    """

    def __init__(self, player_ai: Optional[PlayerAIProtocol] = None) -> None:
        """Initialize the GMController.

        Args:
            player_ai: Optional PlayerAI implementation for callbacks.
        """
        self._executor = GameExecutor(player_ai=player_ai)
        self._handler = Q21Handler()
        self._game_state: dict[str, Any] = {}
        self._player_email: str = ""

    def set_player_email(self, email: str) -> None:
        """Set the player email for response building."""
        self._player_email = email

    def run_game(self, gprm: "GPRM") -> "GameResult":
        """Execute a complete Q21 game.

        This is a synchronous method that simulates running through
        all game phases. In practice, the game is driven by incoming
        messages from the referee.

        Args:
            gprm: Game parameters containing match info and content.

        Returns:
            GameResult with status and scoring information.
        """
        from _infra.rlgm.gprm import GameResult

        # Initialize game state from GPRM
        self._game_state = {
            "match_id": gprm.match_id,
            "game_id": gprm.game_id,
            "book_name": gprm.book_name,
            "book_hint": gprm.book_hint,
            "association_domain": gprm.association_domain,
            "referee_email": gprm.referee_email,
            "phase": "INITIALIZED",
        }

        # Game execution is message-driven, so run_game returns
        # a placeholder result. Actual game flow is via handle_q21_message.
        return GameResult(
            match_id=gprm.match_id,
            game_id=gprm.game_id,
            status="INITIALIZED",
            league_points=0,
            private_score=0.0,
            breakdown={},
        )

    def handle_q21_message(
        self,
        msg_type: str,
        payload: dict[str, Any],
        sender: str
    ) -> Optional[Q21Response]:
        """Handle incoming Q21 message from referee.

        Args:
            msg_type: The Q21 message type (e.g., Q21_WARMUP_CALL).
            payload: Message payload data.
            sender: Sender email address.

        Returns:
            Q21Response with response data, or None if no response needed.
        """
        match_id = payload.get("match_id", "")

        if msg_type == Q21Handler.WARMUP_CALL:
            result = self._executor.execute_warmup(payload)
            self._game_state["phase"] = "WARMUP_COMPLETE"
            return Q21Response(
                message_type=Q21Handler.WARMUP_RESPONSE,
                payload={"match_id": match_id, "answer": result["warmup_answer"]},
                recipient=sender,
            )

        elif msg_type == Q21Handler.ROUND_START:
            # Q21ROUNDSTART triggers immediate Q21QUESTIONSBATCH response
            result = self._executor.handle_round_start(payload)
            self._game_state.update(result)
            questions_result = self._executor.execute_questions(payload)
            self._game_state["questions"] = questions_result["questions"]
            self._game_state["phase"] = "QUESTIONS_SENT"
            return Q21Response(
                message_type=Q21Handler.QUESTIONS_BATCH,
                payload={"match_id": match_id, "questions": questions_result["questions"]},
                recipient=sender,
            )

        elif msg_type == Q21Handler.ANSWERS_BATCH:
            result = self._executor.receive_answers(payload)
            self._game_state["answers"] = result["answers"]
            # Q21ANSWERSBATCH triggers immediate Q21GUESSSUBMISSION response
            guess_payload = {**payload, "answers": result["answers"]}
            guess_result = self._executor.execute_guess(guess_payload)
            self._game_state["phase"] = "GUESS_SUBMITTED"
            return Q21Response(
                message_type=Q21Handler.GUESS_SUBMISSION,
                payload={"match_id": match_id, "guess": guess_result["guess"]},
                recipient=sender,
            )

        elif msg_type == Q21Handler.SCORE_FEEDBACK:
            result = self._executor.handle_score(payload)
            self._game_state["phase"] = "COMPLETED"
            self._game_state["score"] = result
            # Score feedback is terminal - no response required
            return None

        else:
            raise ValueError(f"Unknown Q21 message type: {msg_type}")

    def get_game_state(self) -> dict[str, Any]:
        """Get current game state for debugging/testing."""
        return self._game_state.copy()

    def get_game_result(self) -> "GameResult":
        """Get final game result after completion."""
        from _infra.rlgm.gprm import GameResult

        score = self._game_state.get("score", {})
        return GameResult(
            match_id=self._game_state.get("match_id", ""),
            game_id=self._game_state.get("game_id", ""),
            status=self._game_state.get("phase", "UNKNOWN"),
            league_points=score.get("league_points", 0),
            private_score=score.get("private_score", 0.0),
            breakdown=score.get("breakdown", {}),
        )
