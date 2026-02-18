"""League Handler - handles League Manager broadcast messages.

Processes all BROADCAST_* messages from the League Manager
and generates appropriate responses.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class LeagueResponse:
    """Response to send back to League Manager."""
    message_type: str
    payload: Dict[str, Any]
    recipient: str


class LeagueHandler:
    """Handles League Manager broadcast messages.

    Message types handled (per UNIFIED_PROTOCOL.md):
    - BROADCAST_START_SEASON -> SEASON_REGISTRATION_REQUEST
    - SEASON_REGISTRATION_RESPONSE -> (acknowledgment)
    - BROADCAST_ASSIGNMENT_TABLE -> (store assignments)
    - BROADCAST_NEW_LEAGUE_ROUND -> (triggers games, transition message)
    - LEAGUE_COMPLETED -> (finalize season)
    """

    # Message type constants (per protocol)
    START_SEASON = "BROADCAST_START_SEASON"
    REGISTRATION_RESPONSE = "SEASON_REGISTRATION_RESPONSE"
    ASSIGNMENT_TABLE = "BROADCAST_ASSIGNMENT_TABLE"
    NEW_ROUND = "BROADCAST_NEW_LEAGUE_ROUND"
    LEAGUE_COMPLETED = "LEAGUE_COMPLETED"

    def __init__(self, player_email: str = "", player_name: str = "") -> None:
        """Initialize the LeagueHandler.

        Args:
            player_email: Player's email address.
            player_name: Player's display name.
        """
        self._player_email = player_email
        self._player_name = player_name
        self._registered = False
        self._season_id: Optional[str] = None

    def handle_start_season(
        self,
        payload: Dict[str, Any],
        sender: str
    ) -> LeagueResponse:
        """Handle BROADCAST_START_SEASON - register for the season.

        Args:
            payload: Start season payload with season_id, etc.
            sender: League Manager email.

        Returns:
            LeagueResponse with SEASON_REGISTRATION_REQUEST.
        """
        self._season_id = payload.get("season_id", "")

        return LeagueResponse(
            message_type="SEASON_REGISTRATION_REQUEST",
            payload={
                "season_id": self._season_id,
                "player_email": self._player_email,
                "player_name": self._player_name,
                "machine_state": "READY",
            },
            recipient=sender,
        )

    def handle_registration_response(
        self,
        payload: Dict[str, Any]
    ) -> None:
        """Handle SEASON_REGISTRATION_RESPONSE - confirm registration.

        Args:
            payload: Registration response with status.
        """
        status = payload.get("status", "")
        if status in ("REGISTERED", "ACCEPTED", "OK"):
            self._registered = True

    def is_registered(self) -> bool:
        """Check if player is registered for current season."""
        return self._registered

    def get_season_id(self) -> Optional[str]:
        """Get current season ID."""
        return self._season_id

    def handle_assignment_table(
        self,
        payload: Dict[str, Any],
        sender: str
    ) -> LeagueResponse:
        """Handle BROADCAST_ASSIGNMENT_TABLE - acknowledge assignments.

        Protocol format per assignment:
        - role: "player1", "player2", or "referee"
        - email: participant's email
        - game_id: 7-digit SSRRGGG format (e.g., "0101001")
        - group_id: group identifier

        Args:
            payload: Assignment table with season assignments.
            sender: League Manager email.

        Returns:
            LeagueResponse acknowledging receipt.
        """
        assignments = payload.get("assignments", [])

        # Filter assignments for this player (role is player1 or player2)
        my_assignments = [
            a for a in assignments
            if a.get("email") == self._player_email
            and a.get("role") in ("player1", "player2")
        ]

        return LeagueResponse(
            message_type="GROUP_ASSIGNMENT_RESPONSE",
            payload={
                "season_id": self._season_id,
                "player_email": self._player_email,
                "assignments_received": len(my_assignments),
                "status": "ACKNOWLEDGED",
            },
            recipient=sender,
        )

    def parse_assignments_for_player(
        self,
        assignments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Parse protocol-format assignments and enrich for this player.

        Protocol assignment format:
        - role: "player1", "player2", or "referee"
        - email: participant's email
        - game_id: 7-digit SSRRGGG format
        - group_id: group identifier

        Args:
            assignments: Raw assignments from BROADCAST_ASSIGNMENT_TABLE.

        Returns:
            List of enriched assignment dicts for games where this player participates.
        """
        # Group assignments by game_id to find participants per game
        games: Dict[str, Dict[str, str]] = {}
        for a in assignments:
            game_id = a.get("game_id", "")
            if game_id not in games:
                games[game_id] = {"game_id": game_id, "group_id": a.get("group_id", "")}
            role = a.get("role", "")
            email = a.get("email", "")
            games[game_id][role] = email

        # Filter games where this player participates
        my_assignments = []
        for game_id, game_info in games.items():
            my_role = None
            if game_info.get("player1") == self._player_email:
                my_role = "PLAYER1"
            elif game_info.get("player2") == self._player_email:
                my_role = "PLAYER2"

            if my_role:
                # Parse round_number from game_id (format: SSRRGGG)
                round_number = int(game_id[2:4]) if len(game_id) >= 4 else 1

                enriched = {
                    "game_id": game_id,
                    "match_id": game_id,  # Use game_id as match_id
                    "round_number": round_number,
                    "referee_email": game_info.get("referee", ""),
                    "my_role": my_role,
                    "opponent_email": (
                        game_info.get("player2") if my_role == "PLAYER1"
                        else game_info.get("player1")
                    ),
                    "group_id": game_info.get("group_id", ""),
                }
                my_assignments.append(enriched)

        return my_assignments

    def handle_league_completed(
        self,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle LEAGUE_COMPLETED - finalize season.

        Protocol payload fields:
        - broadcast_id: Unique broadcast identifier
        - season_id: Season identifier
        - final_standings: Array of {rank, participant_id, display_name, total_points}
        - message_text: Optional message

        Args:
            payload: League completed payload with final standings.

        Returns:
            Dict with this player's final standings info.
        """
        final_standings = payload.get("final_standings", [])

        # Find this player in final standings
        my_rank = 0
        my_points = 0
        for entry in final_standings:
            if entry.get("participant_id") == self._player_email:
                my_rank = entry.get("rank", 0)
                my_points = entry.get("total_points", 0)
                break

        return {
            "season_id": self._season_id,
            "final_rank": my_rank,
            "total_points": my_points,
            "season_complete": True,
        }
