# CLAUDE.md
**IMPORTANT: Read this entire file before making ANY code changes.**
Version: 1.1.0

## Development Principles

1. **Ask clarifying questions** — Always ask as many questions as needed before implementing. Never assume.
2. **Check existing code first** — Before implementing any function or system, search the current codebase to see if it already exists.
3. **Reuse existing code above all else** — Prefer wiring into existing functions and modules. This ensures easy integration.
4. **Recommend session splits** — If a task is too large for one session, recommend splitting it up.
5. **Modularity** — The project must be as modular as possible. Small, focused modules with clear responsibilities.
6. **TDD** — Follow Test-Driven Development. Write tests first, then implement to make them pass.
7. **150-line file limit** — All Python files must stay under 150 lines. If a file exceeds this, refactor or split it.
8. **No hardcoded secrets or paths** — Never hardcode secrets, credentials, file paths, URLs, or environment-specific values in source code. All such values must come from `config.json` or environment variables.

## Documentation & Versioning

1. **Document versioning** — All documentation files (README, PRDs, plans) must have a semantic version (e.g., `1.0.0`) at the top.
2. **Code-to-PRD mapping** — Every source file must have a header comment indicating its area/system and corresponding PRD:
   ```python
   # Area: <Feature Name>
   # PRD: docs/<prd-filename>.md
   ```
3. **Sync requirement** — When code changes, update the corresponding PRD:
   - Increment the PRD version
   - Update the PRD content to match the implementation
   - Update any affected README sections
4. **PRD location** — All PRD documents live in the `docs/` folder.

## Feature PRDs

| Feature | PRD | Modules |
|---------|-----|---------|
| RLGM (League Manager Interface) | `docs/prd-rlgm.md` | `_infra/rlgm/` |
| GMC (Game Manager Component) | `docs/prd-rlgm.md` | `_infra/gmc/` |
| Protocol Logging | `docs/LOGGER_OUTPUT_PLAYER.md` | `_infra/shared/logging/` |

## Project Structure

```
Q21G-player-whl/
├── CLAUDE.md                    # This file - development guidelines
├── README.md                    # Quick start guide
├── CONFIG_GUIDE.md              # Configuration documentation
├── STARTUP_CONTEXT_V01.md       # Project overview context
├── .env.example                 # Environment variables template
│
├── my_player.py                 # Student implementation (PUBLIC)
├── run.py                       # CLI entry point
├── setup.py                     # Unified setup wizard
├── setup_gmail.py               # Gmail OAuth setup
├── setup_config.py              # Configuration generator
├── init_db.py                   # Database schema initialization
├── verify_setup.py              # Setup verification script
│
├── _infra/                      # Hidden infrastructure
│   ├── __init__.py              # Package exports
│   ├── router.py                # MessageRouter - unified entry point
│   ├── demo_ai.py               # DemoAI for testing
│   │
│   ├── rlgm/                    # League-level components
│   │   ├── __init__.py
│   │   ├── controller.py        # RLGMController
│   │   ├── league_handler.py    # BROADCAST_* handlers
│   │   ├── round_manager.py     # Assignment tracking
│   │   └── gprm.py              # GPRM & GameResult dataclasses
│   │
│   ├── gmc/                     # Game-level components
│   │   ├── __init__.py
│   │   ├── controller.py        # GMController
│   │   ├── q21_handler.py       # Q21* message routing
│   │   └── game_executor.py     # PlayerAI callback execution
│   │
│   └── shared/
│       └── logging/
│           └── protocol_logger.py  # Colored protocol logging
│
├── docs/
│   ├── prd-rlgm.md              # RLGM/GMC architecture PRD
│   ├── LOGGER_OUTPUT_PLAYER.md  # Logger output specification
│   ├── LOGGER_IMPLEMENTATION_TASKS.md
│   └── comparison-gmailasplayer-vs-rlgm.md
│
├── js/
│   └── config.template.json     # Configuration template
│
└── dist/
    └── q21_player-*.whl         # SDK package
```

## Terminology

| Term | Full Name | Description |
|------|-----------|-------------|
| **GMC** | Game Manager Component | Handles a single Q21 game cycle with the referee |
| **RLGM** | Referee-League Game Manager | Interfaces between League Manager and GMC |
| **GPRM** | Game Parameters | Input data needed to run a single game (7-digit SSRRGGG format) |
| **PlayerAI** | Player AI Interface | The 4 callbacks students implement |
| **game_id** | Game Identifier | 7-digit format: SS (season) + RR (round) + GGG (game number) |
