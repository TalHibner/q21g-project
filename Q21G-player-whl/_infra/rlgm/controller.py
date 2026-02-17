# Area: RLGM (League Manager Interface)
# PRD: docs/prd-rlgm.md
"""RLGM Controller - League communication orchestrator."""
from typing import Any, Optional, Tuple, List

from _infra.gmc.controller import GMController
from _infra.gmc.game_executor import PlayerAIProtocol
from _infra.rlgm.gprm import GPRM, GPRMBuilder
from _infra.rlgm.league_handler import LeagueHandler, LeagueResponse
from _infra.rlgm.round_manager import RoundManager


class RLGMController:
    """Orchestrates league-level communication with League Manager and GMC."""

    def __init__(
        self,
        player_email: str = "",
        player_name: str = "",
        player_ai: Optional[PlayerAIProtocol] = None
    ) -> None:
        """Initialize the RLGMController.

        Args:
            player_email: Player's email address.
            player_name: Player's display name.
            player_ai: Optional PlayerAI implementation.
        """
        self._player_email = player_email
        self._player_name = player_name
        self._league_handler = LeagueHandler(player_email, player_name)
        self._round_manager = RoundManager(player_email=player_email)
        self._gprm_builder = GPRMBuilder()
        self._gmc = GMController(player_ai=player_ai)
        self._auth_token = ""
        self._round_assignments: dict[int, list] = {}  # round_number -> assignments

    def set_auth_token(self, token: str) -> None:
        """Set authentication token for game requests."""
        self._auth_token = token
        self._round_manager.set_auth_token(token)
        self._gprm_builder.set_auth_token(token)

    def process_message(
        self,
        msg_type: str,
        payload: dict[str, Any],
        sender: str
    ) -> Tuple[Optional[LeagueResponse], List[GPRM]]:
        """Process incoming league message.

        Args:
            msg_type: The message type (e.g., BROADCAST_START_SEASON).
            payload: Message payload data.
            sender: Sender email address.

        Returns:
            Tuple of (LeagueResponse or None, list of GPRM for games to run).
        """
        games_to_run: List[GPRM] = []
        response: Optional[LeagueResponse] = None

        # Route to appropriate handler based on message type
        if msg_type == LeagueHandler.START_SEASON:
            response = self._league_handler.handle_start_season(payload, sender)
            season_id = payload.get("season_id", "")
            self._round_manager.set_season(season_id)
            self._gprm_builder.set_season_id(season_id)

        elif msg_type == LeagueHandler.REGISTRATION_RESPONSE:
            self._league_handler.handle_registration_response(payload)

        elif msg_type == LeagueHandler.ASSIGNMENT_TABLE:
            response = self._league_handler.handle_assignment_table(payload, sender)
            raw_assignments = payload.get("assignments", [])
            enriched = self._league_handler.parse_assignments_for_player(raw_assignments)
            for assignment in enriched:
                round_number = assignment.get("round_number", 1)
                if round_number not in self._round_assignments:
                    self._round_assignments[round_number] = []
                self._round_assignments[round_number].append(assignment)
            for round_num, assignments in self._round_assignments.items():
                self._round_manager.set_assignments(round_num, assignments)

        elif msg_type == LeagueHandler.NEW_ROUND:
            round_number = payload.get("round_number", 1)
            self._round_manager.set_current_round(round_number)
            games_to_run = self._round_manager.get_games_for_round(round_number)

        elif msg_type == LeagueHandler.LEAGUE_COMPLETED:
            self._league_handler.handle_league_completed(payload)

        else:
            raise ValueError(f"Unknown league message type: {msg_type}")

        return response, games_to_run

    def process_q21_message(
        self,
        msg_type: str,
        payload: dict[str, Any],
        sender: str
    ) -> Optional[dict]:
        """Process incoming Q21 game message.

        Delegates to GMController for game-level handling.

        Args:
            msg_type: The Q21 message type (e.g., Q21_WARMUP_CALL).
            payload: Message payload data.
            sender: Sender email (referee).

        Returns:
            Response dict or None if no response needed.
        """
        q21_response = self._gmc.handle_q21_message(msg_type, payload, sender)
        if q21_response is None:
            return None
        return {
            "message_type": q21_response.message_type,
            "payload": q21_response.payload,
            "recipient": q21_response.recipient,
        }

    def get_gmc(self) -> GMController:
        """Get the GMController for direct game handling."""
        return self._gmc

    def is_registered(self) -> bool:
        """Check if player is registered."""
        return self._league_handler.is_registered()
