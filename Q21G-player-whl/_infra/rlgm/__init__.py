"""RLGM (Referee-League Game Manager) package.

Handles all league-level communication while delegating
individual game execution to the GMC.
"""
from _infra.rlgm.controller import RLGMController
from _infra.rlgm.gprm import GPRM, GameResult, GPRMBuilder
from _infra.rlgm.league_handler import LeagueHandler, LeagueResponse
from _infra.rlgm.round_manager import RoundManager, Assignment

__all__ = [
    "GPRM", "GameResult", "GPRMBuilder",
    "RLGMController", "RoundManager", "Assignment",
    "LeagueHandler", "LeagueResponse"
]
