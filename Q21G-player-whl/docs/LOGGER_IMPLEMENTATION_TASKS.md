# Player Logger Output - Implementation Tasks

**PRD Reference:** `docs/LOGGER_OUTPUT_PLAYER.md`
**Version:** 1.0
**Created:** 2026-02-10

---

## Overview

Implement a protocol-aware logging system for the Player SDK:
- **Protocol messages** (GREEN) - sent/received emails with structured format
- **Callback functions** (ORANGE) - PlayerAI invocations with CALL/RESPONSE
- **Errors** (RED) - error messages only
- Suppress all INFO-level logs

---

## Phase 1: Core Logger Infrastructure

- [x] **1.1 Create ProtocolLogger class**
  - File: `_infra/shared/logging/protocol_logger.py` (NEW)
  - ANSI color constants (GREEN, ORANGE, RED, RESET)
  - Format protocol messages per PRD spec
  - Format callback messages per PRD spec
  - Format error messages per PRD spec

- [x] **1.2 Create Message Lookup Table**
  - File: `_infra/shared/logging/protocol_logger.py`
  - Map original message types to display names (F5)
  - Map message types to expected responses (F6)
  - Table from PRD Section 10

- [x] **1.3 Create Role Determiner utility**
  - File: `_infra/shared/logging/protocol_logger.py`
  - Query assignment repository for current game
  - Return `PLAYER-ACTIVE` or `PLAYER-INACTIVE`

---

## Phase 2: Protocol Message Logging

- [x] **2.1 Update scan_handler.py - RECEIVED messages**
  - Replace `logger.warning(f"RECEIVED: ...")` with ProtocolLogger call
  - Extract game_id from payload or query DB
  - Extract deadline from payload
  - Determine role status

- [x] **2.2 Update scan_handler.py - SENT messages**
  - Replace `logger.warning(f"SENT: ...")` with ProtocolLogger call
  - Include expected response from lookup table
  - Include deadline for response

- [x] **2.3 Update scan_handler.py - REJECTED messages**
  - Use RED color for rejection logs
  - Follow error format from PRD

---

## Phase 3: Callback Function Logging

- [x] **3.1 Update sdk_strategy.py - Warmup callback**
  - Log CALL before `player_ai.get_warmup_answer(ctx)`
  - Log RESPONSE after callback returns
  - Use ORANGE color, include milliseconds

- [x] **3.2 Update sdk_strategy.py - Questions callback**
  - Log CALL before `player_ai.get_questions(ctx)`
  - Log RESPONSE after callback returns
  - Map to `generate_questions` display name

- [x] **3.3 Update sdk_strategy.py - Guess callback**
  - Log CALL before `player_ai.get_guess(ctx)`
  - Log RESPONSE after callback returns
  - Map to `formulate_guess` display name

- [x] **3.4 Update score_feedback_handler.py - Score callback**
  - Log CALL before `player_ai.on_score_received(ctx)`
  - Log RESPONSE after callback returns (even though void)
  - **GAP FIX:** Added missing on_score_received() callback

---

## Phase 4: Log Level Configuration

- [x] **4.1 Set default log level to WARNING**
  - Update `.env.example` - already done (LOG_LEVEL=WARNING)
  - Ensure ProtocolLogger outputs at WARNING level
  - Callback logs at WARNING level

- [x] **4.2 Suppress third-party INFO logs**
  - googleapiclient.discovery_cache
  - database.pool
  - gmail.client
  - Set these loggers to WARNING in logger.py

---

## Phase 5: Game ID and Deadline Extraction

- [x] **5.1 Create GameContext tracker**
  - File: `_infra/shared/logging/protocol_logger.py`
  - Track current game_id from messages
  - Parse SSRRGGG format
  - Query DB when not in message payload

- [x] **5.2 Extract deadlines from payloads**
  - Parse deadline field from protocol messages
  - Format as HH:MM:SS
  - Use `--:--:--` for terminal messages

---

## Phase 6: Integration and Testing

- [x] **6.1 Rebuild wheel package**
  - Include new protocol_logger.py ✓
  - Include updated scan_handler.py ✓
  - Include updated sdk_strategy.py ✓
  - Include updated score_feedback_handler.py ✓
  - Include updated logger.py ✓
  - Rebuilt as q21_player-1.0.1-py3-none-any.whl

- [x] **6.2 Test complete session logging**
  - Verify GREEN protocol messages
  - Verify ORANGE callback messages
  - Verify RED error messages ✓
  - Verify INFO suppression (requires LOG_LEVEL=WARNING in .env)

---

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `_infra/shared/logging/protocol_logger.py` | CREATE | New protocol-aware logger |
| `_infra/cli/scan_handler.py` | MODIFY | Use ProtocolLogger for SENT/RECEIVED/REJECTED |
| `_infra/strategy/sdk_strategy.py` | MODIFY | Add callback CALL/RESPONSE logging |
| `_infra/cli/score_feedback_handler.py` | MODIFY | Add on_score_received callback + logging |
| `_infra/shared/logging/logger.py` | MODIFY | Suppress third-party INFO logs |

---

## Player Protocol Flow (from PRD)

### Messages Player RECEIVES
| From | Message | Display As | Player Responds With |
|------|---------|------------|---------------------|
| League Manager | `BROADCAST_START_SEASON` | `START-SEASON` | `SEASON-SIGNUP` |
| League Manager | `SEASON_REGISTRATION_RESPONSE` | `SIGNUP-RESPONSE` | *(wait)* |
| League Manager | `BROADCAST_ASSIGNMENT_TABLE` | `ASSIGNMENT-TABLE` | *(wait)* |
| League Manager | `BROADCAST_NEW_LEAGUE_ROUND` | `START-ROUND` | *(wait for referee)* |
| Referee | `Q21WARMUPCALL` | `PING-CALL` | `PING-RESPONSE` |
| Referee | `Q21ROUNDSTART` | `START-GAME` | `ASK-20-QUESTIONS` |
| Referee | `Q21ANSWERSBATCH` | `QUESTION-ANSWERS` | `MY-GUESS` |
| Referee | `Q21SCOREFEEDBACK` | `ROUND-SCORE-REPORT` | *(terminal)* |
| League Manager | `LEAGUE_COMPLETED` | `SEASON-ENDED` | *(terminal)* |

### Messages Player SENDS
| To | Message | Display As | Expects Response |
|----|---------|------------|------------------|
| League Manager | `SEASON_REGISTRATION_REQUEST` | `SEASON-SIGNUP` | `SIGNUP-RESPONSE` |
| Referee | `Q21WARMUPRESPONSE` | `PING-RESPONSE` | `START-GAME` |
| Referee | `Q21QUESTIONSBATCH` | `ASK-20-QUESTIONS` | `QUESTION-ANSWERS` |
| Referee | `Q21GUESSSUBMISSION` | `MY-GUESS` | `ROUND-SCORE-REPORT` |

---

## Reference: Message Lookup Table

| Original Message Type | Display Name | Expected Response |
|-----------------------|--------------|-------------------|
| `BROADCAST_START_SEASON` | `START-SEASON` | `SEASON-SIGNUP` |
| `SEASON_REGISTRATION_REQUEST` | `SEASON-SIGNUP` | `SIGNUP-RESPONSE` |
| `SEASON_REGISTRATION_RESPONSE` | `SIGNUP-RESPONSE` | `Wait for ASSIGNMENT-TABLE` |
| `BROADCAST_ASSIGNMENT_TABLE` | `ASSIGNMENT-TABLE` | `Wait for START-ROUND` |
| `BROADCAST_NEW_LEAGUE_ROUND` | `START-ROUND` | `Wait for PING-CALL` |
| `Q21WARMUPCALL` | `PING-CALL` | `PING-RESPONSE` |
| `Q21WARMUPRESPONSE` | `PING-RESPONSE` | `Wait for START-GAME` |
| `Q21ROUNDSTART` | `START-GAME` | `ASK-20-QUESTIONS` |
| `Q21QUESTIONSBATCH` | `ASK-20-QUESTIONS` | `QUESTION-ANSWERS` |
| `Q21ANSWERSBATCH` | `QUESTION-ANSWERS` | `MY-GUESS` |
| `Q21GUESSSUBMISSION` | `MY-GUESS` | `ROUND-SCORE-REPORT` |
| `Q21SCOREFEEDBACK` | `ROUND-SCORE-REPORT` | `None (terminal)` |
| `LEAGUE_COMPLETED` | `SEASON-ENDED` | `None (terminal)` |

---

## Reference: Callback Display Names

| Callback Method | Display Name |
|-----------------|--------------|
| `get_warmup_answer` | `answer_warmup` |
| `get_questions` | `generate_questions` |
| `get_guess` | `formulate_guess` |
| `on_score_received` | `receive_score` |

---

## Reference: Output Formats

### Protocol Message (GREEN)
```
HH:MM:SS | GAME-ID: SSRRGGG | SENT/RECEIVED | to/from {email} | MESSAGE-NAME | EXPECTED-RESPONSE: {next} | ROLE: {role} | DEADLINE: HH:MM:SS
```

### Callback Message (ORANGE)
```
HH:MM:SS:MS | CALLBACK: {function_name} | CALL/RESPONSE | ROLE: PLAYER
```

### Error Message (RED)
```
[ERROR] HH:MM:SS | {Error description}
```
