# ADR-004: Player Candidate Search — Dual Search with Priority Slots

**Date**: 2025-02
**Status**: Accepted
**Supersedes**: Initial single-query ChromaDB search

## Context

The player receives a `book_name` (PDF lecture title) and `book_hint` (15-word description). It must find the correct paragraph from ~340 valid candidates. Two search strategies are possible:

1. **PDF-filtered search**: Query ChromaDB with a `where={"pdf_name": book_name}` filter → guaranteed correct PDF, but fewer results (~70 per PDF).
2. **Unfiltered search**: Query ChromaDB without filter → all 340 paragraphs, potentially higher semantic match scores.

Early testing showed that the unfiltered search consistently dominated a simple distance-based merge (the correct paragraph's hint-embedding often scored slightly below an unrelated but semantically close paragraph from a different PDF).

## Decision

Use **dual search with priority slots**:

- Allocate the first N slots to PDF-filtered results (e.g., top 15 from the correct PDF).
- Backfill remaining slots with unfiltered results not already present (e.g., top 5 from global search).
- Deduplication by paragraph ID prevents double-counting.

```python
filtered   = chroma.search(hint, pdf_name=book_name, k=15)
unfiltered = chroma.search(hint, k=20)
seen = {r["id"] for r in filtered}
extra = [r for r in unfiltered if r["id"] not in seen][:5]
candidates = filtered + extra  # priority to filtered
```

## Alternatives Considered

| Approach | Result | Decision |
|----------|--------|----------|
| **Dual search, filtered first** | Correct PDF always in top slots | **Selected** |
| Distance-based merge (min distance wins) | Unfiltered dominated; correct PDF lost | Rejected after live testing |
| PDF-filtered only | Misses rare cross-PDF semantic matches | Rejected — too narrow |
| Unfiltered only | Correct PDF often excluded from top-20 | Rejected after live testing |
| Re-rank with cross-encoder | High quality | Not implemented — latency budget |

## Consequences

- **Good**: Guarantees at least 15 candidates from the correct PDF even if their raw scores are slightly lower than unrelated paragraphs.
- **Good**: Still allows global semantic results to influence the candidate set, catching edge cases where the hint is unusually generic.
- **Trade-off**: Fixed slot allocation (15/5) is a hyperparameter. Tune by adjusting `pdf_k` and `global_k` in `player_helpers.py`.
- **Learning**: Distance-based merging was the original design and proved incorrect under realistic hint semantics. Priority-slot allocation is the robust fix.
