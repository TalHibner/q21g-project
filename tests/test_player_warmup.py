"""Tests for player warmup and search candidates."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

PLAYER_DIR = Path(__file__).parent.parent / "Q21G-player-whl"
sys.path.insert(0, str(PLAYER_DIR))


@pytest.fixture
def ai():
    with patch("anthropic.Anthropic"):
        from my_player import MyPlayerAI
        return MyPlayerAI()


# ── Callback 1: Warmup (no LLM) ──


def test_warmup_addition():
    from player_helpers import solve_warmup
    assert solve_warmup("What is 7 + 8?") == "15"


def test_warmup_subtraction():
    from player_helpers import solve_warmup
    assert solve_warmup("What is 12 - 5?") == "7"


def test_warmup_multiplication():
    from player_helpers import solve_warmup
    assert solve_warmup("What is 6 * 9?") == "54"


def test_warmup_division():
    from player_helpers import solve_warmup
    assert solve_warmup("What is 15 / 3?") == "5"


def test_warmup_division_by_zero():
    from player_helpers import solve_warmup
    assert solve_warmup("What is 10 / 0?") == "0"


def test_warmup_hebrew_format():
    from player_helpers import solve_warmup
    assert solve_warmup("?מה זה 7 * 8") == "56"


def test_warmup_fallback_on_garbage():
    from player_helpers import solve_warmup
    assert solve_warmup("no numbers here") == "0"


def test_warmup_callback_returns_dict(ai):
    ctx = {"dynamic": {"warmup_question": "What is 3 + 4?"}, "service": {}}
    result = ai.get_warmup_answer(ctx)
    assert result == {"answer": "7"}


def test_warmup_extra_whitespace():
    from player_helpers import solve_warmup
    assert solve_warmup("What is  7  +  8 ?") == "15"


# ── Search candidates ──


def test_search_candidates_filtered_first():
    from player_helpers import search_candidates
    mock_vs = MagicMock()
    mock_db = MagicMock()
    mock_vs.search_by_pdf.return_value = [{"id": "p1"}]
    result = search_candidates(mock_vs, mock_db, "Lec1", "hint")
    assert result == [{"id": "p1"}]
    mock_vs.search_by_pdf.assert_called_once()


def test_search_candidates_falls_back_to_all():
    from player_helpers import search_candidates
    mock_vs = MagicMock()
    mock_db = MagicMock()
    mock_vs.search_by_pdf.return_value = []
    mock_vs.search.return_value = [{"id": "p2"}]
    result = search_candidates(mock_vs, mock_db, "Lec1", "hint")
    assert result == [{"id": "p2"}]


def test_search_candidates_falls_back_to_db():
    from player_helpers import search_candidates
    mock_vs = MagicMock()
    mock_db = MagicMock()
    mock_vs.search_by_pdf.return_value = []
    mock_vs.search.return_value = []
    mock_db.get_by_pdf_name.return_value = [{"id": "p3"}, {"id": "p4"}]
    result = search_candidates(mock_vs, mock_db, "Lec1", "hint", n=1)
    assert result == [{"id": "p3"}]


def test_search_candidates_with_empty_hint():
    """Empty hint should not crash — still returns results via fallbacks."""
    from player_helpers import search_candidates
    mock_vs = MagicMock()
    mock_db = MagicMock()
    mock_vs.search_by_pdf.return_value = [{"id": "p1"}]
    result = search_candidates(mock_vs, mock_db, "Lec1", "")
    assert result == [{"id": "p1"}]
    mock_vs.search_by_pdf.assert_called_once_with("", "Lec1", n_results=20)
