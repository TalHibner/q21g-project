"""Round Manager - tracks round state and assignments.

Manages the lifecycle of league rounds including assignment
tracking and game scheduling.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from _infra.rlgm.gprm import GPRM


@dataclass
class Assignment:
    """Represents a single game assignment.

    Protocol game_id format: SSRRGGG (7 digits)
    - SS: Season number (01-99)
    - RR: Round number (01-99)
    - GGG: Game number (001-999)
    """
    game_id: str           # 7-digit SSRRGGG format
    match_id: str          # Same as game_id
    round_number: int      # Extracted from game_id[2:4]
    game_number: int       # Extracted from game_id[4:7]
    referee_email: str
    opponent_email: Optional[str]
    my_role: str           # "PLAYER1" or "PLAYER2"
    group_id: str = ""


class RoundManager:
    """Tracks round state and manages game assignments.

    Responsible for:
    - Storing assignments received from League Manager
    - Tracking current round state
    - Building GPRM objects for game execution
    """

    def __init__(self, season_id: str = "", player_email: str = "") -> None:
        """Initialize the RoundManager.

        Args:
            season_id: Current season identifier.
            player_email: Player's email address.
        """
        self._season_id = season_id
        self._player_email = player_email
        self._current_round = 0
        self._assignments: Dict[int, List[Assignment]] = {}  # round -> assignments
        self._auth_token = ""

    def set_season(self, season_id: str) -> None:
        """Set the current season ID."""
        self._season_id = season_id

    def set_auth_token(self, token: str) -> None:
        """Set authentication token for game requests."""
        self._auth_token = token

    def set_assignments(
        self,
        round_number: int,
        assignments: List[Dict[str, Any]]
    ) -> None:
        """Store assignments for a round.

        Args:
            round_number: The round number.
            assignments: List of enriched assignment dicts from LeagueHandler.
        """
        parsed = []
        for a in assignments:
            game_id = a.get("game_id", "")
            # Extract game_number from game_id (last 3 digits)
            game_number = int(game_id[4:7]) if len(game_id) >= 7 else 1

            parsed.append(Assignment(
                game_id=game_id,
                match_id=a.get("match_id", game_id),
                round_number=a.get("round_number", round_number),
                game_number=game_number,
                referee_email=a.get("referee_email", ""),
                opponent_email=a.get("opponent_email"),
                my_role=a.get("my_role", "PLAYER1"),
                group_id=a.get("group_id", ""),
            ))
        self._assignments[round_number] = parsed

    def get_assignments(self, round_number: int) -> List[Assignment]:
        """Get assignments for a specific round."""
        return self._assignments.get(round_number, [])

    def get_games_for_round(self, round_number: int) -> List[GPRM]:
        """Get GPRM objects for all games in a round.

        Args:
            round_number: The round number.

        Returns:
            List of GPRM objects for game execution.
        """
        assignments = self._assignments.get(round_number, [])
        return [self._build_gprm(a) for a in assignments]

    def _build_gprm(self, assignment: Assignment) -> GPRM:
        """Build GPRM from assignment data.

        Note: Book info (book_name, book_hint, association_word) is NOT
        available at assignment time - it comes from Q21ROUNDSTART message.
        These fields are left empty in the initial GPRM.
        """
        return GPRM(
            match_id=assignment.match_id,
            game_id=assignment.game_id,
            season_id=self._season_id,
            round_number=assignment.round_number,
            game_number=assignment.game_number,
            referee_email=assignment.referee_email,
            opponent_email=assignment.opponent_email,
            my_role=assignment.my_role,
            book_name="",  # Filled in by Q21ROUNDSTART
            book_hint="",  # Filled in by Q21ROUNDSTART
            association_word="",  # Filled in by Q21ROUNDSTART
            auth_token=self._auth_token,
        )

    def advance_round(self) -> int:
        """Advance to the next round.

        Returns:
            The new current round number.
        """
        self._current_round += 1
        return self._current_round

    def get_current_round(self) -> int:
        """Get current round number."""
        return self._current_round

    def set_current_round(self, round_number: int) -> None:
        """Set current round number explicitly."""
        self._current_round = round_number
