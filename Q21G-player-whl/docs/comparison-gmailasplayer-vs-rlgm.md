# Comparison: GmailAsPlayer vs GMC+RLGM
Version: 1.0.0

This document provides a detailed comparison between the existing GmailAsPlayer implementation and the proposed GMC+RLGM architecture to ensure no functionality gaps.

---

## Overview

| Aspect | GmailAsPlayer | GMC+RLGM |
|--------|---------------|----------|
| **Architecture** | Monolithic scan handler | Separated RLGM (league) + GMC (game) |
| **League Communication** | Mixed in scan_handler | Dedicated RLGM module |
| **Game Execution** | Inline handlers | Dedicated GMC module |
| **Student Interface** | PlayerAI callbacks | PlayerAI callbacks (unchanged) |

---

## Season Registration

| Functionality | GmailAsPlayer Location | GMC+RLGM Location | Gap? |
|--------------|------------------------|-------------------|------|
| BROADCAST_START_SEASON | `message_processor.py:30-34` | RLGM `league_handler.handle_start_season()` | No |
| SEASON_REGISTRATION_RESPONSE | `season_registration_handler.py` | RLGM `league_handler.handle_registration_response()` | No |
| Auto-register on season start | `message_processor.py:34` | RLGM automatic in `handle_start_season()` | No |
| Store registration status | `state_repository.py` | RLGM reuses same repository | No |

---

## Assignment Management

| Functionality | GmailAsPlayer Location | GMC+RLGM Location | Gap? |
|--------------|------------------------|-------------------|------|
| BROADCAST_ASSIGNMENT_TABLE | `player_gatekeeper.py:45-70` | RLGM `league_handler.handle_assignment_table()` | No |
| Filter assignments for player | `assignment_handler.py:18-49` | RLGM reuses same handler | No |
| Enrich with opponent/referee | `assignment_handler.py:51-72` | RLGM `GPRMBuilder` uses same logic | No |
| Store assignments | `assignment_repository.py` | RLGM reuses same repository | No |
| GROUP_ASSIGNMENT_RESPONSE | `broadcast_response_builder.py` | RLGM reuses same builder | No |

---

## Round Management

| Functionality | GmailAsPlayer Location | GMC+RLGM Location | Gap? |
|--------------|------------------------|-------------------|------|
| BROADCAST_NEW_LEAGUE_ROUND | `broadcast_handler.py:110-134` | RLGM `league_handler.handle_new_league_round()` | No |
| Create game states for round | `broadcast_handler.py:120-130` | RLGM `round_manager.prepare_games()` | No |
| BROADCAST_ROUND_RESULTS | `broadcast_handler.py:100-108` | RLGM `league_handler.handle_round_results()` | No |
| Store standings | `standings_repository.py` | RLGM reuses + adds score tracking | Enhanced |

---

## Keep Alive

| Functionality | GmailAsPlayer Location | GMC+RLGM Location | Gap? |
|--------------|------------------------|-------------------|------|
| BROADCAST_KEEP_ALIVE | `message_processor.py:36-38` | RLGM `league_handler.handle_keep_alive()` | No |
| KEEP_ALIVE_RESPONSE | `broadcast_response_builder.py:37-41` | RLGM reuses same builder | No |
| Machine state reporting | `message_processor.py:38` | RLGM same logic | No |

---

## Critical Operations

| Functionality | GmailAsPlayer Location | GMC+RLGM Location | Gap? |
|--------------|------------------------|-------------------|------|
| BROADCAST_CRITICAL_PAUSE | `broadcast_handler.py:70-76` | RLGM `league_handler.handle_critical_pause()` | No |
| Save pause state | `pause_state_repository.py` | RLGM reuses same repository | No |
| BROADCAST_CRITICAL_CONTINUE | `broadcast_handler.py:78-86` | RLGM `league_handler.handle_critical_continue()` | No |
| Restore from pause | `pause_state_repository.py` | RLGM reuses same repository | No |
| BROADCAST_CRITICAL_RESET | `broadcast_handler.py:66-68` | RLGM `league_handler.handle_critical_reset()` | No |
| Full state reset | `broadcast_handler.py:67` | RLGM same logic | No |
| CRITICAL_*_RESPONSE | `broadcast_response_builder.py` | RLGM reuses same builder | No |

---

## Q21 Game Flow

| Functionality | GmailAsPlayer Location | GMC+RLGM Location | Gap? |
|--------------|------------------------|-------------------|------|
| Q21_WARMUP_CALL | `warmup_handler.py:24-60` | GMC `game_executor.execute_warmup()` | No |
| Q21_WARMUP_RESPONSE | `q21_dispatcher.py:30-50` | GMC `q21_handler.build_warmup_response()` | No |
| Q21_ROUND_START | `warmup_handler.handle_round_start()` | GMC `game_executor.handle_round_start()` | No |
| Store book info | `game_state_repository.py` | GMC reuses same repository | No |
| Q21_QUESTIONS_CALL | `questions_handler.py:22-50` | GMC `game_executor.execute_questions()` | No |
| Q21_QUESTIONS_BATCH | `q21_dispatcher.py:65-96` | GMC `q21_handler.build_questions_response()` | No |
| Q21_ANSWERS_BATCH | `answers_handler.py:20-45` | GMC `game_executor.receive_answers()` | No |
| Auto-trigger guess | `q21_dispatcher.py:100-110` | GMC `game_executor.execute_guess()` | No |
| Q21_GUESS_SUBMISSION | `q21_dispatcher.py:99-132` | GMC `q21_handler.build_guess_response()` | No |
| Q21_SCORE_FEEDBACK | `score_feedback_handler.py:24-50` | GMC `game_executor.handle_score()` | No |
| Store game result | `game_result_repository.py` | GMC reuses same repository | No |

---

## PlayerAI Callbacks

| Callback | GmailAsPlayer Location | GMC+RLGM Location | Gap? |
|----------|------------------------|-------------------|------|
| `get_warmup_answer()` | `sdk_strategy.py:48-58` | GMC via same strategy | No |
| `get_questions()` | `sdk_strategy.py:24-34` | GMC via same strategy | No |
| `get_guess()` | `sdk_strategy.py:36-46` | GMC via same strategy | No |
| `on_score_received()` | **NOT CALLED** | GMC must add | **GAP - FIX REQUIRED** |

---

## Season End

| Functionality | GmailAsPlayer Location | GMC+RLGM Location | Gap? |
|--------------|------------------------|-------------------|------|
| LEAGUE_COMPLETED | **NOT HANDLED** | RLGM `league_handler.handle_league_completed()` | **GAP - FIX REQUIRED** |
| Final standings storage | N/A | RLGM `standings_repo.save_final_standings()` | New |
| Season complete state | N/A | RLGM `state_repo.update_state()` | New |

---

## State Management

| State Type | GmailAsPlayer Location | GMC+RLGM Location | Gap? |
|------------|------------------------|-------------------|------|
| Player state | `state_repository.py` | Shared by RLGM and GMC | No |
| Game state (per match) | `game_state_repository.py` | GMC owns | No |
| Assignments | `assignment_repository.py` | RLGM owns, GMC reads | No |
| Standings | `standings_repository.py` | RLGM owns | No |
| Game results | `game_result_repository.py` | GMC writes, RLGM reads | No |

---

## Sender Validation

| Functionality | GmailAsPlayer Location | GMC+RLGM Location | Gap? |
|--------------|------------------------|-------------------|------|
| Gatekeeper validation | `player_gatekeeper.py` | Shared by RLGM (league msgs) and GMC (Q21 msgs) | No |
| Manager email check | `sender_validator.py:56-59` | Same logic | No |
| Referee lookup | `player_gatekeeper.get_current_referee()` | GMC uses for Q21 responses | No |

---

## Response Building

| Response Type | GmailAsPlayer Location | GMC+RLGM Location | Gap? |
|---------------|------------------------|-------------------|------|
| League responses | `broadcast_response_builder.py` | RLGM reuses | No |
| Q21 responses | `q21g_response_builder.py` | GMC reuses | No |
| Envelope building | `envelope_factory.py` | Shared | No |

---

## Gap Summary

| Gap | Description | Fix Location | Priority |
|-----|-------------|--------------|----------|
| **#1** | `on_score_received()` not called after Q21_SCORE_FEEDBACK | `gmc/game_executor.py` | High |
| **#2** | `LEAGUE_COMPLETED` not handled | `rlgm/league_handler.py` | Medium |

---

## Enhancements in GMC+RLGM

| Enhancement | Description |
|-------------|-------------|
| Score tracking | Player can track their scores for callback optimization |
| Clear separation | League management separate from game execution |
| GPRM abstraction | Clean interface between RLGM and GMC |
| Testability | Each component can be tested independently |

---

## Verification Checklist

- [ ] All 10 League Manager messages handled
- [ ] All 8 Q21 game messages handled
- [ ] All 4 PlayerAI callbacks invoked
- [ ] All repositories reused correctly
- [ ] All response builders reused correctly
- [ ] State transitions preserved
- [ ] Gap #1 fixed: on_score_received() called
- [ ] Gap #2 fixed: LEAGUE_COMPLETED handled
