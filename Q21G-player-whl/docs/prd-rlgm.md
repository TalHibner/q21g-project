# PRD: RLGM (Referee-League Game Manager)
Version: 1.4.0

## Document Info
- **Area**: League Management
- **PRD Location**: `docs/prd-rlgm.md`
- **Comparison Doc**: `docs/comparison-gmailasplayer-vs-rlgm.md`
- **Related Modules**: `_infra/rlgm/`, `_infra/gmc/`

---

## 1. Executive Summary

The RLGM (Referee-League Game Manager) is a middleware component that sits between the League Manager and the GMC (Game Manager Component). It handles all league-level communication while delegating individual game execution to the GMC.

**Key Principle**: Students only see the 4 PlayerAI callbacks. All RLGM and GMC code is hidden infrastructure.

---

## 2. Terminology

| Term | Full Name | Description |
|------|-----------|-------------|
| **GMC** | Game Manager Component | Handles a single Q21 game cycle with the referee |
| **RLGM** | Referee-League Game Manager | Interfaces between League Manager and GMC |
| **GPRM** | Game Parameters | Input data needed to run a single game |

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           STUDENT LAYER                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  my_player.py (StudentPlayerAI)                                  │    │
│  │  ├── get_warmup_answer(ctx) -> {"answer": str}                   │    │
│  │  ├── get_questions(ctx) -> {"questions": [...]}                  │    │
│  │  ├── get_guess(ctx) -> {"opening_sentence": ..., ...}            │    │
│  │  └── on_score_received(ctx) -> None                              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        HIDDEN INFRASTRUCTURE                             │
│                                                                          │
│  ┌──────────────────────┐         ┌──────────────────────┐             │
│  │      RLGM            │         │        GMC           │             │
│  │  ┌────────────────┐  │         │  ┌────────────────┐  │             │
│  │  │ RLGMController │  │ GPRM    │  │ GMController   │  │             │
│  │  └───────┬────────┘  │────────>│  └───────┬────────┘  │             │
│  │          │           │         │          │           │             │
│  │  ┌───────▼────────┐  │ Result  │  ┌───────▼────────┐  │             │
│  │  │ LeagueHandler  │  │<────────│  │ GameExecutor   │  │             │
│  │  │ RoundManager   │  │         │  │ Q21Handler     │  │             │
│  │  │ GPRMBuilder    │  │         │  └────────────────┘  │             │
│  │  └────────────────┘  │         │                      │             │
│  └──────────┬───────────┘         └──────────┬───────────┘             │
│             │                                │                          │
└─────────────┼────────────────────────────────┼──────────────────────────┘
              │                                │
              ▼                                ▼
┌─────────────────────────┐      ┌─────────────────────────┐
│    LEAGUE MANAGER       │      │       REFEREE           │
│    (via Gmail)          │      │       (via Gmail)       │
│                         │      │                         │
│ - BROADCAST_START_SEASON│      │ - Q21_WARMUP_CALL       │
│ - BROADCAST_ASSIGNMENT  │      │ - Q21_ROUND_START       │
│ - BROADCAST_NEW_ROUND   │      │ - Q21_ANSWERS_BATCH     │
│ - BROADCAST_KEEP_ALIVE  │      │ - Q21_SCORE_FEEDBACK    │
│ - LEAGUE_COMPLETED      │      │                         │
└─────────────────────────┘      └─────────────────────────┘
```

---

## 4. Module Structure

```
_infra/
├── rlgm/                              # RLGM Package (~450 lines total)
│   ├── __init__.py                    # ~20 lines - exports
│   ├── controller.py                  # ~120 lines - Main orchestrator
│   ├── league_handler.py              # ~100 lines - League broadcasts
│   ├── round_manager.py               # ~80 lines - Round lifecycle
│   ├── gprm.py                        # ~50 lines - GPRM dataclass
│   └── game_scheduler.py              # ~80 lines - Game scheduling
│
├── gmc/                               # GMC Package (~385 lines total)
│   ├── __init__.py                    # ~15 lines - exports
│   ├── controller.py                  # ~100 lines - Game lifecycle
│   ├── q21_handler.py                 # ~90 lines - Q21 dispatch
│   └── game_executor.py               # ~80 lines - Phase execution
│
└── (existing files remain)
```

---

## 5. GPRM Definition

```python
# File: _infra/rlgm/gprm.py
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class GPRM:
    """Game Parameters - immutable input to GMC."""
    # Identity
    match_id: str           # e.g., "S1R2G003"
    game_id: str            # e.g., "0102003"
    season_id: str          # e.g., "SEASON01"
    round_number: int       # e.g., 2
    game_number: int        # e.g., 3

    # Participants
    referee_email: str      # From assignment
    opponent_email: Optional[str]
    my_role: str            # "PLAYER_A", "PLAYER_B", "QUESTIONER"

    # Game content
    book_name: str          # Book/lecture title
    book_hint: str          # Description (15 words)
    association_domain: str # Domain for associative word

    # Authentication
    auth_token: str


@dataclass
class GameResult:
    """Result returned by GMC."""
    match_id: str
    game_id: str
    status: str             # COMPLETED, FAILED, TIMEOUT
    league_points: int
    private_score: float
    breakdown: dict
    error: Optional[str] = None
```

---

## 6. Message Flow

### 6.1 RLGM <-> League Manager

| Direction | Message | Handler | Response |
|-----------|---------|---------|----------|
| LM -> RLGM | `BROADCAST_START_SEASON` | `league_handler.handle_start_season()` | `SEASON_REGISTRATION_REQUEST` |
| LM -> RLGM | `SEASON_REGISTRATION_RESPONSE` | `league_handler.handle_registration_response()` | None |
| LM -> RLGM | `BROADCAST_ASSIGNMENT_TABLE` | `league_handler.handle_assignment_table()` | `GROUP_ASSIGNMENT_RESPONSE` |
| LM -> RLGM | `BROADCAST_NEW_LEAGUE_ROUND` | `league_handler.handle_new_league_round()` | None (triggers games) |
| LM -> RLGM | `BROADCAST_ROUND_RESULTS` | `league_handler.handle_round_results()` | None (updates scores) |
| LM -> RLGM | `BROADCAST_KEEP_ALIVE` | `league_handler.handle_keep_alive()` | `KEEP_ALIVE_RESPONSE` |
| LM -> RLGM | `BROADCAST_CRITICAL_PAUSE` | `league_handler.handle_critical_pause()` | `CRITICAL_PAUSE_RESPONSE` |
| LM -> RLGM | `BROADCAST_CRITICAL_CONTINUE` | `league_handler.handle_critical_continue()` | `CRITICAL_CONTINUE_RESPONSE` |
| LM -> RLGM | `BROADCAST_CRITICAL_RESET` | `league_handler.handle_critical_reset()` | `CRITICAL_RESET_RESPONSE` |
| LM -> RLGM | `LEAGUE_COMPLETED` | `league_handler.handle_league_completed()` | None |

### 6.2 GMC <-> Referee

| Direction | Message | Handler | Callback |
|-----------|---------|---------|----------|
| REF -> GMC | `Q21_WARMUP_CALL` | `game_executor.execute_warmup()` | `get_warmup_answer()` |
| GMC -> REF | `Q21_WARMUP_RESPONSE` | | |
| REF -> GMC | `Q21_ROUND_START` | `game_executor.handle_round_start()` | None |
| REF -> GMC | `Q21_QUESTIONS_CALL` | `game_executor.execute_questions()` | `get_questions()` |
| GMC -> REF | `Q21_QUESTIONS_BATCH` | | |
| REF -> GMC | `Q21_ANSWERS_BATCH` | `game_executor.execute_guess()` | `get_guess()` |
| GMC -> REF | `Q21_GUESS_SUBMISSION` | | |
| REF -> GMC | `Q21_SCORE_FEEDBACK` | `game_executor.handle_score()` | `on_score_received()` |

### 6.3 Score Tracking

The player tracks scores internally for:
- Knowing league standing
- Optimizing callback strategies

```python
@dataclass
class PlayerStandings:
    season_id: str
    round_number: int
    total_score: float
    games_played: int
    games_won: int
    rank: int
    history: list[RoundResult]
```

---

## 7. Code Isolation Plan

### 7.1 Files to REUSE (wrap in RLGM)

| File | Used By |
|------|---------|
| `broadcast_handler.py` | `league_handler.py` wraps this |
| `broadcast_response_builder.py` | `league_handler.py` uses this |
| `assignment_handler.py` | `league_handler.py` calls this |
| `season_registration_handler.py` | `league_handler.py` calls this |
| `standings_handler.py` | `league_handler.py` calls this |
| `player_gatekeeper.py` | RLGM uses for validation |

### 7.2 Files to REFACTOR into GMC

| Current File | New Location |
|-------------|--------------|
| `q21_dispatcher.py` | `gmc/q21_handler.py` |
| `warmup_handler.py` | Used by `gmc/game_executor.py` |
| `questions_handler.py` | Used by `gmc/game_executor.py` |
| `guess_handler.py` | Used by `gmc/game_executor.py` |
| `answers_handler.py` | Used by `gmc/game_executor.py` |
| `score_feedback_handler.py` | Used by `gmc/game_executor.py` |

### 7.3 NEW Files to Create

| File | Lines | Purpose |
|------|-------|---------|
| `_infra/rlgm/__init__.py` | ~20 | Package exports |
| `_infra/rlgm/controller.py` | ~120 | Main RLGM orchestrator |
| `_infra/rlgm/league_handler.py` | ~100 | Wraps broadcast handlers |
| `_infra/rlgm/round_manager.py` | ~80 | Round state management |
| `_infra/rlgm/gprm.py` | ~50 | GPRM dataclass + builder |
| `_infra/rlgm/game_scheduler.py` | ~80 | Game scheduling logic |
| `_infra/gmc/__init__.py` | ~15 | Package exports |
| `_infra/gmc/controller.py` | ~100 | Game lifecycle orchestrator |
| `_infra/gmc/game_executor.py` | ~80 | Executes game phases |

---

## 8. Implementation Phases

### Phase 0: Documentation
1. Create `CLAUDE.md` with development guidelines
2. Create `docs/prd-rlgm.md` with this PRD content
3. Create `docs/comparison-gmailasplayer-vs-rlgm.md`

### Phase 1: GPRM + GMC Refactor
1. Create `_infra/rlgm/gprm.py` with GPRM and GameResult
2. Create `_infra/gmc/` package structure
3. Refactor `q21_dispatcher.py` into `gmc/q21_handler.py`
4. Create `gmc/controller.py` wrapping game lifecycle
5. Create `gmc/game_executor.py` for phase execution
6. **Fix**: Add `on_score_received()` callback invocation

### Phase 2: RLGM Core
1. Create `_infra/rlgm/` package structure
2. Create `league_handler.py` wrapping existing handlers
3. Create `round_manager.py` for round state
4. Create `controller.py` as main orchestrator
5. Create `game_scheduler.py` for scheduling
6. **Fix**: Add `LEAGUE_COMPLETED` handler

### Phase 3: Integration
1. Modify `scan_handler.py` to route through RLGM/GMC
2. Update message routing logic
3. Test end-to-end flow
4. Verify all functionality preserved

---

## 9. Gap Fixes

### Gap #1: on_score_received() Not Called

**Fix**: In `score_feedback_handler.py` or `gmc/game_executor.py`:

```python
strategy = get_strategy()
ctx = {
    "dynamic": {
        "league_points": payload.get("league_points", 0),
        "private_score": payload.get("private_score", 0.0),
        "breakdown": payload.get("breakdown", {})
    },
    "service": {"match_id": match_id}
}
strategy.on_score_received(ctx)
```

### Gap #2: LEAGUE_COMPLETED Not Handled

**Fix**: In `_infra/rlgm/league_handler.py`:

```python
def handle_league_completed(self, payload: dict) -> None:
    season_id = payload.get("season_id")
    final_standings = payload.get("standings", [])
    self._standings_repo.save_final_standings(season_id, final_standings)
    self._state_repo.update_state_only(self._player_email, PlayerState.SEASON_COMPLETE)
```

### Gap #3: Logging Context Not Set for Game ID (Fixed in v1.1.0)

**Problem**: The `ProtocolLogger.set_game_context()` method existed but was never called,
causing all log messages to show the default game_id `0000000` instead of the actual game_id.

**Fix**: In `_infra/rlgm/controller.py`, added `set_game_context()` call in `process_q21_message()`:

```python
from _infra.shared.logging.protocol_logger import set_game_context

def process_q21_message(self, msg_type: str, payload: dict, sender: str) -> Optional[dict]:
    # Set logging context with game_id from payload (match_id == game_id)
    game_id = payload.get("match_id", "0000000")
    set_game_context(game_id, player_active=True)

    q21_response = self._gmc.handle_q21_message(msg_type, payload, sender)
    # ...
```

Now all Q21 message logs correctly display the 7-digit SSRRGGG game_id.

### Gap #4: Correct game_id Format Per Message Type (Fixed in v1.3.0)

**Problem**: Different message types require different game_id formats and role visibility.

**Solution**: Three context levels with specific formats:

| Context | game_id Format | Role | Messages |
|---------|---------------|------|----------|
| Season | SS99999 | empty | START-SEASON, SIGNUP-RESPONSE, ASSIGNMENT-TABLE, SEASON-ENDED |
| Round | SSRR999 | ACTIVE/INACTIVE | START-ROUND |
| Game | SSRRGGG | ACTIVE/INACTIVE | All Q21 messages |

**Implementation**:

1. Split `protocol_logger.py` into `constants.py` + `protocol_logger.py` (under 150 lines each)
2. Created `cli/log_context.py` for context-setting logic (43 lines)
3. Added three context methods:

```python
# In protocol_logger.py
def set_season_context()  # SS99999, empty role
def set_round_context(round_number, player_active)  # SSRR999, with role
def set_game_context(game_id, player_active)  # SSRRGGG, with role
```

4. `scan_handler.py` uses `set_logging_context()` from `cli/log_context.py`:

```python
from q21_player._infra.cli.log_context import set_logging_context

# In message processing loop
set_logging_context(normalized_type, game_id, inner, payload, assignment_repo, gatekeeper.current_season_id)
```

**Result**: Each message type displays the correct game_id format and role visibility.

---

## 10. Success Criteria

1. All League Manager broadcasts handled by RLGM
2. All Q21 messages handled by GMC
3. GPRM correctly populated from assignments
4. GMC returns GameResult to RLGM
5. All 4 PlayerAI callbacks invoked correctly
6. No functionality gaps vs GmailAsPlayer
7. Students only see PlayerAI interface
8. All files under 150 lines
9. No hardcoded values
10. Player score tracking for optimization
11. TDD approach with tests first
