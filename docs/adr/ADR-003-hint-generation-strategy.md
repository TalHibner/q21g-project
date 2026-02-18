# ADR-003: Hint Generation Strategy (Taboo Word Constraint)

**Date**: 2025-01
**Status**: Accepted

## Context

The game rules require the referee's `book_hint` (a 15-word paragraph description) to contain **zero words from the paragraph text**. This is the hardest constraint in the entire system. A naive LLM prompt often produces hints that inadvertently echo paragraph words, especially for domain-specific Hebrew terms.

Additionally, the hint must be useful enough for the player's semantic search to find the correct paragraph from among ~340 valid candidates.

## Decision

Use a **generate–validate–retry loop** with up to 3 LLM attempts, followed by a **ChromaDB self-test**:

1. Generate hint via LLM with forbidden word list in the prompt.
2. Normalise both hint and paragraph words (strip punctuation, lowercase).
3. If intersection is non-empty, retry with explicit overlap feedback (words listed in prompt).
4. After a valid hint passes taboo check, query ChromaDB with the hint and verify the correct paragraph appears in the top results. If not, select a different paragraph and restart.

```python
for attempt in range(3):
    hint = llm_generate(prompt_with_forbidden_words)
    if not word_overlap(hint, paragraph):
        if chroma_self_test(hint, paragraph_id):
            return hint
        else:
            select_new_paragraph(); break  # hint works but paragraph not findable
    # else: retry with overlap={overlap} in prompt
return fallback_hint  # generic, always passes
```

## Alternatives Considered

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Generate–validate–retry (3×) + self-test** | Robust, handles overlap gracefully | Adds up to ~10 s latency | **Selected** |
| Single LLM call with very strict prompt | Simple | ~30% failure rate in practice | Rejected |
| Rule-based synonym replacement | Deterministic | Doesn't generalise to Hebrew NLP | Rejected |
| Pre-generate all hints offline | No latency | Hints go stale; paragraph pool changes | Rejected |

## Consequences

- **Good**: Self-test guarantees the hint is actually useful for semantic search — not just taboo-compliant.
- **Good**: Retry feedback ("you used these forbidden words: X, Y") dramatically reduces second-attempt failures.
- **Constraint**: Maximum 3 retries per the deadline budget (60 s for `get_round_start_info`). The fallback generic hint always passes taboo but may score lower for the player (acceptable — this is a competitive game).
- **Constraint**: Word normalisation must handle Hebrew morphology. Current approach uses simple punctuation stripping; full Hebrew stemming would be more robust but adds complexity.
