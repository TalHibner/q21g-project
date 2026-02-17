# Logger Output PRD - Player Perspective

**Version:** 1.3
**Status:** CANONICAL REFERENCE
**Last Updated:** 2026-02-11

---

## 1. Overview

This document specifies the logger output format for the **Player** agent. The logger should only output protocol-related messages (sent/received emails) and callback function invocations. All standard [INFO] level logs should be suppressed.

---

## 2. Display Rules

| Log Type | Color | When to Display |
|----------|-------|-----------------|
| Protocol Messages | **Green** | When sending or receiving protocol emails |
| Callback Functions | **Orange** | When invoking or receiving response from callbacks |
| Errors | **Red** | When an error occurs |

**Suppressed:** All [INFO] level logs - only protocol send/receive and callbacks are shown.

---

## 3. Protocol Message Log Format

### 3.1 Format Specification

```
HH:MM:SS | GAME-ID: SSRRGGG | SENT/RECEIVED | to/from {email} | MESSAGE-NAME | EXPECTED-RESPONSE: {next} | ROLE: {role} | DEADLINE: HH:MM:SS
```

### 3.2 Field Definitions

| Field | Label | Format | Description |
|-------|-------|--------|-------------|
| F1 | *(none)* | `HH:MM:SS` | Time (Hour:Minute:Seconds) |
| F2 | `GAME-ID:` | `SSRRGGG` | Game ID (SS=Season, RR=Round, GGG=Game). Normalized to 7-digit format. |
| F3 | *(none)* | `SENT` or `RECEIVED` | Direction of email |
| F4 | `to` or `from` | `{email address}` | Email address with direction prefix |
| F5 | *(none)* | Message name | Simplified name from lookup table |
| F6 | `EXPECTED-RESPONSE:` | Next message | Next message per protocol flow |
| F7 | `ROLE:` | Role status | `PLAYER-ACTIVE` or `PLAYER-INACTIVE` |
| F8 | `DEADLINE:` | `HH:MM:SS` | Deadline for next message |

### 3.3 Role Determination (F7)

| Status | Condition |
|--------|-----------|
| `PLAYER-ACTIVE` | Player is participating in the current game/round |
| `PLAYER-INACTIVE` | Player is NOT participating in the current game/round |

**Rule:** Q21 messages (game-level) always imply `PLAYER-ACTIVE`. The referee only sends Q21 messages to participating players. The `PLAYER-INACTIVE` status only applies to round-level `START-ROUND` messages when the player has no assignments for that round.

### 3.4 Game ID Normalization (F2)

The game_id must always be displayed in 7-digit `SSRRGGG` format. Non-standard formats are normalized:

| Input Format | Output | Example |
|--------------|--------|---------|
| Standard 7-digit | Pass through | `0102001` → `0102001` |
| Training format | Extract trailing 7 digits | `TRAIN_2026-02-11_0900_0102001` → `0102001` |
| Other with trailing digits | Extract trailing 7 digits | `PREFIX_0103002` → `0103002` |

**Implementation:** The `_normalize_game_id()` function in `log_context.py` handles this extraction.

---

## 4. Player Message Flow

### 4.1 Messages Player RECEIVES

| Original Message Type | Display Name (F5) | Expected Response (F6) | Sender |
|-----------------------|-------------------|------------------------|--------|
| `BROADCAST_START_SEASON` | `START-SEASON` | `SEASON-SIGNUP` | League Manager |
| `SEASON_REGISTRATION_RESPONSE` | `SIGNUP-RESPONSE` | `Wait for ASSIGNMENT-TABLE` | League Manager |
| `BROADCAST_ASSIGNMENT_TABLE` | `ASSIGNMENT-TABLE` | `Wait for START-ROUND` | League Manager |
| `BROADCAST_NEW_LEAGUE_ROUND` | `START-ROUND` | `Wait for PING-CALL` | League Manager |
| `Q21WARMUPCALL` | `PING-CALL` | `PING-RESPONSE` | Referee |
| `Q21ROUNDSTART` | `START-GAME` | `ASK-20-QUESTIONS` | Referee |
| `Q21ANSWERSBATCH` | `QUESTION-ANSWERS` | `MY-GUESS` | Referee |
| `Q21SCOREFEEDBACK` | `ROUND-SCORE-REPORT` | `None (terminal)` | Referee |
| `LEAGUE_COMPLETED` | `SEASON-ENDED` | `None (terminal)` | League Manager |

### 4.2 Messages Player SENDS

| Original Message Type | Display Name (F5) | Expected Response (F6) | Recipient |
|-----------------------|-------------------|------------------------|-----------|
| `SEASON_REGISTRATION_REQUEST` | `SEASON-SIGNUP` | `SIGNUP-RESPONSE` | League Manager |
| `Q21WARMUPRESPONSE` | `PING-RESPONSE` | `Wait for START-GAME` | Referee |
| `Q21QUESTIONSBATCH` | `ASK-20-QUESTIONS` | `QUESTION-ANSWERS` | Referee |
| `Q21GUESSSUBMISSION` | `MY-GUESS` | `ROUND-SCORE-REPORT` | Referee |

---

## 5. Protocol Log Examples

### 5.1 Season Registration Phase

```
18:30:00 | GAME-ID: 0100000 | RECEIVED | from server@league.com      | START-SEASON       | EXPECTED-RESPONSE: SEASON-SIGNUP            | ROLE: PLAYER-ACTIVE | DEADLINE: 18:35:00
18:30:15 | GAME-ID: 0100000 | SENT     | to server@league.com        | SEASON-SIGNUP      | EXPECTED-RESPONSE: SIGNUP-RESPONSE          | ROLE: PLAYER-ACTIVE | DEADLINE: 18:35:00
18:32:00 | GAME-ID: 0100000 | RECEIVED | from server@league.com      | SIGNUP-RESPONSE    | EXPECTED-RESPONSE: Wait for ASSIGNMENT-TABLE | ROLE: PLAYER-ACTIVE | DEADLINE: 18:45:00
18:45:00 | GAME-ID: 0100000 | RECEIVED | from server@league.com      | ASSIGNMENT-TABLE   | EXPECTED-RESPONSE: Wait for START-ROUND     | ROLE: PLAYER-ACTIVE | DEADLINE: 19:00:00
```

### 5.2 Game Round Phase (Active Player)

```
19:00:00 | GAME-ID: 0101001 | RECEIVED | from server@league.com      | START-ROUND        | EXPECTED-RESPONSE: Wait for PING-CALL       | ROLE: PLAYER-ACTIVE | DEADLINE: 19:05:00
19:00:30 | GAME-ID: 0101001 | RECEIVED | from referee@example.com    | PING-CALL          | EXPECTED-RESPONSE: PING-RESPONSE            | ROLE: PLAYER-ACTIVE | DEADLINE: 19:02:30
19:00:45 | GAME-ID: 0101001 | SENT     | to referee@example.com      | PING-RESPONSE      | EXPECTED-RESPONSE: Wait for START-GAME      | ROLE: PLAYER-ACTIVE | DEADLINE: 19:05:00
19:05:00 | GAME-ID: 0101001 | RECEIVED | from referee@example.com    | START-GAME         | EXPECTED-RESPONSE: ASK-20-QUESTIONS         | ROLE: PLAYER-ACTIVE | DEADLINE: 19:10:00
19:08:30 | GAME-ID: 0101001 | SENT     | to referee@example.com      | ASK-20-QUESTIONS   | EXPECTED-RESPONSE: QUESTION-ANSWERS         | ROLE: PLAYER-ACTIVE | DEADLINE: 19:15:00
19:12:00 | GAME-ID: 0101001 | RECEIVED | from referee@example.com    | QUESTION-ANSWERS   | EXPECTED-RESPONSE: MY-GUESS                 | ROLE: PLAYER-ACTIVE | DEADLINE: 19:17:00
19:15:30 | GAME-ID: 0101001 | SENT     | to referee@example.com      | MY-GUESS           | EXPECTED-RESPONSE: ROUND-SCORE-REPORT       | ROLE: PLAYER-ACTIVE | DEADLINE: 19:20:00
19:18:00 | GAME-ID: 0101001 | RECEIVED | from referee@example.com    | ROUND-SCORE-REPORT | EXPECTED-RESPONSE: None (terminal)          | ROLE: PLAYER-ACTIVE | DEADLINE: --:--:--
```

### 5.3 Game Round Phase (Inactive Player)

```
19:00:00 | GAME-ID: 0101002 | RECEIVED | from server@league.com      | START-ROUND        | EXPECTED-RESPONSE: Wait for PING-CALL       | ROLE: PLAYER-INACTIVE | DEADLINE: 19:30:00
```

### 5.4 Season End

```
21:45:00 | GAME-ID: 0106000 | RECEIVED | from server@league.com      | SEASON-ENDED       | EXPECTED-RESPONSE: None (terminal)          | ROLE: PLAYER-ACTIVE | DEADLINE: --:--:--
```

---

## 6. Callback Function Log Format

### 6.1 Format Specification

```
HH:MM:SS:MS | CALLBACK: {function_name} | CALL/RESPONSE | ROLE: PLAYER
```

### 6.2 Field Definitions

| Field | Label | Format | Description |
|-------|-------|--------|-------------|
| F1 | *(none)* | `HH:MM:SS:MS` | Time with milliseconds |
| F2 | `CALLBACK:` | Function name | Name of the callback function being invoked |
| F3 | *(none)* | `CALL` or `RESPONSE` | `CALL` when invoked, `RESPONSE` when returns |
| F4 | `ROLE:` | `PLAYER` | Always `PLAYER` for this PRD |

### 6.3 Display Rules

- **Color:** Orange
- Log both when the callback is called AND when it returns a response

---

## 7. Callback Log Examples

### 7.1 Question Generation Callback

```
19:05:15:123 | CALLBACK: generate_questions | CALL     | ROLE: PLAYER
19:08:25:456 | CALLBACK: generate_questions | RESPONSE | ROLE: PLAYER
```

### 7.2 Guess Formulation Callback

```
19:12:05:789 | CALLBACK: formulate_guess    | CALL     | ROLE: PLAYER
19:15:28:012 | CALLBACK: formulate_guess    | RESPONSE | ROLE: PLAYER
```

### 7.3 Warmup Response Callback

```
19:00:32:345 | CALLBACK: answer_warmup      | CALL     | ROLE: PLAYER
19:00:44:678 | CALLBACK: answer_warmup      | RESPONSE | ROLE: PLAYER
```

---

## 8. Complete Session Example

A complete player session showing both protocol (green) and callback (orange) logs:

```
[GREEN]  18:30:00 | GAME-ID: 0100000 | RECEIVED | from server@league.com      | START-SEASON       | EXPECTED-RESPONSE: SEASON-SIGNUP            | ROLE: PLAYER-ACTIVE | DEADLINE: 18:35:00
[GREEN]  18:30:15 | GAME-ID: 0100000 | SENT     | to server@league.com        | SEASON-SIGNUP      | EXPECTED-RESPONSE: SIGNUP-RESPONSE          | ROLE: PLAYER-ACTIVE | DEADLINE: 18:35:00
[GREEN]  18:32:00 | GAME-ID: 0100000 | RECEIVED | from server@league.com      | SIGNUP-RESPONSE    | EXPECTED-RESPONSE: Wait for ASSIGNMENT-TABLE | ROLE: PLAYER-ACTIVE | DEADLINE: 18:45:00
[GREEN]  18:45:00 | GAME-ID: 0100000 | RECEIVED | from server@league.com      | ASSIGNMENT-TABLE   | EXPECTED-RESPONSE: Wait for START-ROUND     | ROLE: PLAYER-ACTIVE | DEADLINE: 19:00:00
[GREEN]  19:00:00 | GAME-ID: 0101001 | RECEIVED | from server@league.com      | START-ROUND        | EXPECTED-RESPONSE: Wait for PING-CALL       | ROLE: PLAYER-ACTIVE | DEADLINE: 19:05:00
[GREEN]  19:00:30 | GAME-ID: 0101001 | RECEIVED | from referee@example.com    | PING-CALL          | EXPECTED-RESPONSE: PING-RESPONSE            | ROLE: PLAYER-ACTIVE | DEADLINE: 19:02:30
[ORANGE] 19:00:32:345 | CALLBACK: answer_warmup      | CALL     | ROLE: PLAYER
[ORANGE] 19:00:44:678 | CALLBACK: answer_warmup      | RESPONSE | ROLE: PLAYER
[GREEN]  19:00:45 | GAME-ID: 0101001 | SENT     | to referee@example.com      | PING-RESPONSE      | EXPECTED-RESPONSE: Wait for START-GAME      | ROLE: PLAYER-ACTIVE | DEADLINE: 19:05:00
[GREEN]  19:05:00 | GAME-ID: 0101001 | RECEIVED | from referee@example.com    | START-GAME         | EXPECTED-RESPONSE: ASK-20-QUESTIONS         | ROLE: PLAYER-ACTIVE | DEADLINE: 19:10:00
[ORANGE] 19:05:15:123 | CALLBACK: generate_questions | CALL     | ROLE: PLAYER
[ORANGE] 19:08:25:456 | CALLBACK: generate_questions | RESPONSE | ROLE: PLAYER
[GREEN]  19:08:30 | GAME-ID: 0101001 | SENT     | to referee@example.com      | ASK-20-QUESTIONS   | EXPECTED-RESPONSE: QUESTION-ANSWERS         | ROLE: PLAYER-ACTIVE | DEADLINE: 19:15:00
[GREEN]  19:12:00 | GAME-ID: 0101001 | RECEIVED | from referee@example.com    | QUESTION-ANSWERS   | EXPECTED-RESPONSE: MY-GUESS                 | ROLE: PLAYER-ACTIVE | DEADLINE: 19:17:00
[ORANGE] 19:12:05:789 | CALLBACK: formulate_guess    | CALL     | ROLE: PLAYER
[ORANGE] 19:15:28:012 | CALLBACK: formulate_guess    | RESPONSE | ROLE: PLAYER
[GREEN]  19:15:30 | GAME-ID: 0101001 | SENT     | to referee@example.com      | MY-GUESS           | EXPECTED-RESPONSE: ROUND-SCORE-REPORT       | ROLE: PLAYER-ACTIVE | DEADLINE: 19:20:00
[GREEN]  19:18:00 | GAME-ID: 0101001 | RECEIVED | from referee@example.com    | ROUND-SCORE-REPORT | EXPECTED-RESPONSE: None (terminal)          | ROLE: PLAYER-ACTIVE | DEADLINE: --:--:--
```

**Note:** `[GREEN]` and `[ORANGE]` tags shown for illustration only - actual output displays colored text without tags.

---

## 9. Error Messages

Errors are displayed in **Red**. Error format:

```
[ERROR] HH:MM:SS | {Error description}
```

Examples:
```
[ERROR] 19:08:35 | Failed to send ASK-20-QUESTIONS: Connection timeout
[ERROR] 19:12:10 | CALLBACK: formulate_guess failed: LLM API error
```

---

## 10. Message Lookup Table Reference

| Original Message Type | Display Name (F5) | Expected Response (F6) |
|-----------------------|-------------------|------------------------|
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
