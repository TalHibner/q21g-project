"""Infrastructure package for Q21 Player SDK.

This package provides the RLGM (Referee-League Game Manager) and
GMC (Game Manager Component) for handling league and game communication.

Main entry point:
    MessageRouter - routes all protocol messages to appropriate handlers

Components:
    RLGMController - handles league-level communication
    GMController - handles individual game execution
    GPRM - game parameters for game execution
    GameResult - result of game execution
    DemoAI - demo PlayerAI for testing without LLM
"""
from _infra._license import __license__, __copyright__
from _infra.router import MessageRouter, RoutingResult
from _infra.demo_ai import DemoAI
from _infra.rlgm import (
    GPRM,
    GameResult,
    GPRMBuilder,
    RLGMController,
    LeagueHandler,
    LeagueResponse,
    RoundManager,
)
from _infra.gmc import (
    GMController,
    GameExecutor,
    Q21Handler,
    Q21Response,
)

__all__ = [
    # License
    "__license__",
    "__copyright__",
    # Main router
    "MessageRouter",
    "RoutingResult",
    # Demo AI
    "DemoAI",
    # RLGM components
    "RLGMController",
    "LeagueHandler",
    "LeagueResponse",
    "RoundManager",
    "GPRM",
    "GameResult",
    "GPRMBuilder",
    # GMC components
    "GMController",
    "GameExecutor",
    "Q21Handler",
    "Q21Response",
]
