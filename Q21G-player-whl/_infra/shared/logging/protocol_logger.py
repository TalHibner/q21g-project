# Area: Protocol Logging
# PRD: docs/LOGGER_OUTPUT_PLAYER.md
"""Protocol Logger - Colored output for player protocol messages."""
from datetime import datetime
from typing import Optional

from _infra.shared.logging.constants import (
    Colors, MESSAGE_DISPLAY_NAMES, EXPECTED_RESPONSES, CALLBACK_DISPLAY_NAMES
)


class ProtocolLogger:
    """Logger for protocol messages. Context: Season=SS99999, Round=SSRR999, Game=SSRRGGG."""
    _current_game_id: str = "0199999"
    _season: str = "01"
    _show_role: bool = False
    _player_active: bool = True

    @classmethod
    def set_season_context(cls) -> None:
        """Set context for season-level messages (SS99999, empty role)."""
        cls._current_game_id = cls._season + "99999"
        cls._show_role = False

    @classmethod
    def set_round_context(cls, round_number: int, player_active: bool = True) -> None:
        """Set context for round-level messages (SSRR999, with role)."""
        cls._current_game_id = cls._season + f"{round_number:02d}" + "999"
        cls._show_role = True
        cls._player_active = player_active

    @classmethod
    def set_game_context(cls, game_id: str, player_active: bool = True) -> None:
        """Set context for game-level messages (SSRRGGG, with role)."""
        cls._current_game_id = game_id or "0199999"
        cls._show_role = True
        cls._player_active = player_active
        if len(game_id) >= 2:
            cls._season = game_id[:2]

    @classmethod
    def _get_display_name(cls, msg_type: str) -> str:
        """Get display name for message type."""
        if msg_type in MESSAGE_DISPLAY_NAMES:
            return MESSAGE_DISPLAY_NAMES[msg_type]
        normalized = msg_type.replace("_", "").upper()
        for key, value in MESSAGE_DISPLAY_NAMES.items():
            if key.replace("_", "").upper() == normalized:
                return value
        return msg_type

    @classmethod
    def _get_expected_response(cls, msg_type: str) -> str:
        """Get expected response for message type."""
        if msg_type in EXPECTED_RESPONSES:
            return EXPECTED_RESPONSES[msg_type]
        normalized = msg_type.replace("_", "").upper()
        for key, value in EXPECTED_RESPONSES.items():
            if key.replace("_", "").upper() == normalized:
                return value
        return "Unknown"

    @classmethod
    def _get_role(cls) -> str:
        """Get current role status. Empty if _show_role is False."""
        if not cls._show_role:
            return ""
        return "PLAYER-ACTIVE" if cls._player_active else "PLAYER-INACTIVE"

    @classmethod
    def _format_time(cls, with_ms: bool = False) -> str:
        """Format current time."""
        now = datetime.now()
        if with_ms:
            return now.strftime("%H:%M:%S:%f")[:-3]
        return now.strftime("%H:%M:%S")

    @classmethod
    def _format_deadline(cls, deadline: Optional[str]) -> str:
        """Format deadline string."""
        if not deadline:
            return "--:--:--"
        try:
            dt = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
            return dt.strftime("%H:%M:%S")
        except (ValueError, AttributeError):
            return deadline if deadline else "--:--:--"

    @classmethod
    def log_received(cls, msg_type: str, sender: str, deadline: Optional[str] = None) -> None:
        """Log a received protocol message (GREEN)."""
        line = (
            f"{Colors.GREEN}{cls._format_time()} | GAME-ID: {cls._current_game_id} | "
            f"RECEIVED | from {sender:<30} | {cls._get_display_name(msg_type):<20} | "
            f"EXPECTED-RESPONSE: {cls._get_expected_response(msg_type):<25} | "
            f"ROLE: {cls._get_role()} | DEADLINE: {cls._format_deadline(deadline)}{Colors.RESET}"
        )
        print(line)

    @classmethod
    def log_sent(cls, msg_type: str, recipient: str, deadline: Optional[str] = None) -> None:
        """Log a sent protocol message (GREEN)."""
        line = (
            f"{Colors.GREEN}{cls._format_time()} | GAME-ID: {cls._current_game_id} | "
            f"SENT     | to {recipient:<32} | {cls._get_display_name(msg_type):<20} | "
            f"EXPECTED-RESPONSE: {cls._get_expected_response(msg_type):<25} | "
            f"ROLE: {cls._get_role()} | DEADLINE: {cls._format_deadline(deadline)}{Colors.RESET}"
        )
        print(line)

    @classmethod
    def log_rejected(cls, msg_type: str, sender: str, reason: str = "") -> None:
        """Log a rejected message (RED)."""
        msg = f"REJECTED {cls._get_display_name(msg_type)} from {sender}"
        if reason:
            msg += f": {reason}"
        print(f"{Colors.RED}[ERROR] {cls._format_time()} | {msg}{Colors.RESET}")

    @classmethod
    def log_error(cls, message: str) -> None:
        """Log an error message (RED)."""
        print(f"{Colors.RED}[ERROR] {cls._format_time()} | {message}{Colors.RESET}")

    @classmethod
    def log_callback_call(cls, callback_name: str) -> None:
        """Log callback invocation (ORANGE)."""
        display = CALLBACK_DISPLAY_NAMES.get(callback_name, callback_name)
        print(f"{Colors.ORANGE}{cls._format_time(True)} | CALLBACK: {display:<20} | "
              f"CALL     | ROLE: PLAYER{Colors.RESET}")

    @classmethod
    def log_callback_response(cls, callback_name: str) -> None:
        """Log callback response (ORANGE)."""
        display = CALLBACK_DISPLAY_NAMES.get(callback_name, callback_name)
        print(f"{Colors.ORANGE}{cls._format_time(True)} | CALLBACK: {display:<20} | "
              f"RESPONSE | ROLE: PLAYER{Colors.RESET}")


# Convenience functions - delegate to ProtocolLogger class methods
def set_season_context(): ProtocolLogger.set_season_context()
def set_round_context(rn: int, active: bool = True): ProtocolLogger.set_round_context(rn, active)
def set_game_context(gid: str, active: bool = True): ProtocolLogger.set_game_context(gid, active)
def log_received(msg: str, sender: str, dl: str = None): ProtocolLogger.log_received(msg, sender, dl)
def log_sent(msg: str, to: str, dl: str = None): ProtocolLogger.log_sent(msg, to, dl)
def log_rejected(msg: str, sender: str, reason: str = ""): ProtocolLogger.log_rejected(msg, sender, reason)
def log_error(message: str): ProtocolLogger.log_error(message)
def log_callback_call(name: str): ProtocolLogger.log_callback_call(name)
def log_callback_response(name: str): ProtocolLogger.log_callback_response(name)
