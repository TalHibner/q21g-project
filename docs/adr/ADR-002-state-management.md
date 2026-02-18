# ADR-002: State Management Between Callbacks

**Date**: 2025-01
**Status**: Accepted

## Context

Both the referee and player SDKs call 4 sequential callbacks on a single AI object instance within a game round. The referee must remember the chosen paragraph (opening sentence, full text, association word) from callback 2 through to callback 4. The player must remember candidate paragraphs from callback 2 (question generation) through to callback 3 (guessing).

The SDK does **not** pass the secret paragraph data back in later callbacks — it's the AI's responsibility to maintain state.

## Decision

Store cross-callback state as **instance variables on the AI class** (`self._*` attributes).

```python
# Referee: set in get_round_start_info(), read in get_answers() and get_score_feedback()
self._paragraph_text = paragraph["text"]
self._opening_sentence = paragraph["opening_sentence"]
self._association_word = chosen_word

# Player: set in get_questions(), read in get_guess()
self._candidates = candidates
```

## Alternatives Considered

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Instance variables** | Simple, zero I/O, SDK-idiomatic | Lost if process crashes between callbacks | **Selected** |
| JSON file per game | Crash-safe | File I/O overhead, path management | Rejected — callbacks run in seconds |
| SQLite game_state table | Query-friendly, crash-safe | Overkill; adds schema + connection logic | Rejected |
| SDK ctx pass-through | No hidden state | SDK doesn't support arbitrary ctx writes | Not available |

## Consequences

- **Good**: The SDK's `DemoAI` example uses the same pattern (`self._actual_opening_sentence`), confirming it's the intended approach.
- **Good**: Zero latency; no file or DB round-trips in the critical path.
- **Risk**: A process crash between callbacks would lose state. Acceptable because callbacks complete within seconds and the game protocol will timeout/retry at the round level.
- **Constraint**: Thread safety is not required — the SDK calls callbacks sequentially.
