"""Message Router - unified routing for all protocol messages.

Provides a single entry point for routing messages to either
RLGM (league messages) or GMC (game messages).
"""
from dataclasses import dataclass
from typing import Any, List, Optional

from _infra.gmc.game_executor import PlayerAIProtocol
from _infra.gmc.q21_handler import Q21Handler
from _infra.rlgm.controller import RLGMController
from _infra.rlgm.gprm import GPRM
from _infra.rlgm.league_handler import LeagueHandler


@dataclass
class RoutingResult:
    """Result of message routing."""
    response: Optional[dict]  # Response to send, or None
    games_to_run: List[GPRM]  # Games triggered by this message
    handled: bool  # Whether message was handled


class MessageRouter:
    """Routes protocol messages to RLGM or GMC.

    Determines message type and routes to appropriate handler:
    - BROADCAST_* -> RLGM (league messages)
    - Q21_* -> GMC (game messages)
    """

    # League message prefixes
    LEAGUE_PREFIXES = (
        "BROADCAST_",
        "SEASON_REGISTRATION",
        "LEAGUE_",
    )

    # Q21 game message prefix (Q21G.v1 protocol - no underscore after Q21)
    Q21_PREFIX = "Q21"

    def __init__(
        self,
        player_email: str = "",
        player_name: str = "",
        player_ai: Optional[PlayerAIProtocol] = None
    ) -> None:
        """Initialize the MessageRouter.

        Args:
            player_email: Player's email address.
            player_name: Player's display name.
            player_ai: PlayerAI implementation for game callbacks.
        """
        self._rlgm = RLGMController(
            player_email=player_email,
            player_name=player_name,
            player_ai=player_ai
        )

    def set_auth_token(self, token: str) -> None:
        """Set authentication token."""
        self._rlgm.set_auth_token(token)

    def route_message(
        self,
        msg_type: str,
        payload: dict[str, Any],
        sender: str
    ) -> RoutingResult:
        """Route message to appropriate handler.

        Args:
            msg_type: Message type string.
            payload: Message payload.
            sender: Sender email address.

        Returns:
            RoutingResult with response and any games to run.
        """
        # Check if it's a league message
        if self._is_league_message(msg_type):
            return self._route_league_message(msg_type, payload, sender)

        # Check if it's a Q21 game message
        if self._is_q21_message(msg_type):
            return self._route_q21_message(msg_type, payload, sender)

        # Unknown message type
        return RoutingResult(
            response=None,
            games_to_run=[],
            handled=False
        )

    def _is_league_message(self, msg_type: str) -> bool:
        """Check if message is a league message."""
        return any(msg_type.startswith(prefix) for prefix in self.LEAGUE_PREFIXES)

    def _is_q21_message(self, msg_type: str) -> bool:
        """Check if message is a Q21 game message."""
        return msg_type.startswith(self.Q21_PREFIX)

    def _route_league_message(
        self,
        msg_type: str,
        payload: dict[str, Any],
        sender: str
    ) -> RoutingResult:
        """Route league message to RLGM."""
        league_response, games = self._rlgm.process_message(msg_type, payload, sender)

        response = None
        if league_response is not None:
            response = {
                "message_type": league_response.message_type,
                "payload": league_response.payload,
                "recipient": league_response.recipient,
            }

        return RoutingResult(
            response=response,
            games_to_run=games,
            handled=True
        )

    def _route_q21_message(
        self,
        msg_type: str,
        payload: dict[str, Any],
        sender: str
    ) -> RoutingResult:
        """Route Q21 message to GMC."""
        response = self._rlgm.process_q21_message(msg_type, payload, sender)

        return RoutingResult(
            response=response,
            games_to_run=[],
            handled=True
        )

    def get_rlgm(self) -> RLGMController:
        """Get the RLGM controller for direct access."""
        return self._rlgm

    def is_registered(self) -> bool:
        """Check if player is registered."""
        return self._rlgm.is_registered()
