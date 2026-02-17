# Area: Protocol Logging
# PRD: docs/LOGGER_OUTPUT_PLAYER.md
"""Tests for log_context.set_logging_context role and game_id determination.

Per PRD and CLAUDE.md:
- game_id must always be 7-digit SSRRGGG format
- Q21 messages (game-level) -> normalize game_id, always PLAYER-ACTIVE
- START-ROUND -> SSRR999 format from round_number
- Season-level messages -> SS99999, no role
"""
import pytest
from unittest.mock import patch, MagicMock

from q21_player._infra.cli.log_context import set_logging_context

MODULE = "q21_player._infra.cli.log_context"


@pytest.fixture
def mock_repo():
    return MagicMock()


class TestQ21GameIdNormalization:
    """Q21 messages must normalize game_id to SSRRGGG format."""

    @patch(f"{MODULE}.set_game_context")
    def test_training_game_id_normalized_to_ssrrggg(self, mock_set_ctx, mock_repo):
        """Training format 'TRAIN_..._0102001' -> '0102001'."""
        raw_game_id = "TRAIN_2026-02-11_0900_0102001"

        set_logging_context("Q21WARMUPCALL", raw_game_id, {}, {}, mock_repo, None)

        # Should extract trailing 7 digits
        mock_set_ctx.assert_called_once_with("0102001", True)

    @patch(f"{MODULE}.set_game_context")
    def test_standard_7digit_game_id_unchanged(self, mock_set_ctx, mock_repo):
        """Standard '0102001' -> '0102001' (no change)."""
        set_logging_context("Q21WARMUPCALL", "0102001", {}, {}, mock_repo, None)

        mock_set_ctx.assert_called_once_with("0102001", True)

    @patch(f"{MODULE}.set_game_context")
    def test_empty_game_id_handled(self, mock_set_ctx, mock_repo):
        """Empty game_id should not crash."""
        set_logging_context("Q21ROUNDSTART", "", {}, {}, mock_repo, None)

        mock_set_ctx.assert_called_once_with("", True)


class TestQ21MessagesAlwaysActive:
    """Q21 messages mean the referee is talking to us -> PLAYER-ACTIVE."""

    Q21_TYPES = [
        "Q21WARMUPCALL",
        "Q21ROUNDSTART",
        "Q21ANSWERSBATCH",
        "Q21SCOREFEEDBACK",
    ]

    @pytest.mark.parametrize("msg_type", Q21_TYPES)
    @patch(f"{MODULE}.set_game_context")
    def test_q21_sets_player_active_true(self, mock_set_ctx, msg_type, mock_repo):
        """All Q21 messages should set player_active=True."""
        set_logging_context(msg_type, "0103001", {}, {}, mock_repo, None)

        mock_set_ctx.assert_called_once_with("0103001", True)


class TestStartRoundRoleDetermination:
    """START-ROUND role depends on assignment table."""

    @patch(f"{MODULE}.set_round_context")
    def test_round_with_assignments_is_active(
        self, mock_set_ctx, mock_repo
    ):
        assignment = MagicMock(my_role="PLAYER")
        mock_repo.get_by_round.return_value = [assignment]

        set_logging_context(
            "BROADCASTNEWLEAGUEROUND", "", {"round_number": 2},
            {}, mock_repo, "S01"
        )

        mock_set_ctx.assert_called_once_with(2, True)

    @patch(f"{MODULE}.set_round_context")
    def test_round_without_assignments_is_inactive(
        self, mock_set_ctx, mock_repo
    ):
        mock_repo.get_by_round.return_value = []

        set_logging_context(
            "BROADCASTNEWLEAGUEROUND", "", {"round_number": 3},
            {}, mock_repo, "S01"
        )

        mock_set_ctx.assert_called_once_with(3, False)


class TestSeasonLevelMessages:
    """Season-level messages use set_season_context (no role)."""

    @patch(f"{MODULE}.set_season_context")
    def test_start_season_uses_season_context(
        self, mock_set_ctx, mock_repo
    ):
        set_logging_context(
            "BROADCASTSTARTSEASON", "", {}, {}, mock_repo, None
        )

        mock_set_ctx.assert_called_once()
