# ADR-005: Paragraph Quality Filter

**Date**: 2025-01
**Status**: Accepted

## Context

Raw PDF extraction yields 1,123 paragraph-like chunks from 22 PDFs. Many of these are not suitable game targets: mathematical formula blocks, code listings, table-of-contents entries, page headers, figure captions, and garbled PDF artefacts. Selecting such paragraphs as game targets would produce unsolvable or trivially rejectable rounds.

## Decision

Implement a **rule-based paragraph filter** (`paragraph_filter.py`) that rejects chunks meeting any of:

| Rule | Threshold | Rationale |
|------|-----------|-----------|
| Formula density | ≥ 2 `=` characters | Equation blocks, not prose |
| Decimal density | ≥ 3 decimal numbers | Tables, measurement lists |
| PDF encoding artefact | Contains `(cid:` | Corrupt character encoding |
| URL / code reference | Contains `http` or backtick | Not natural language |
| Hebrew character ratio | < 40% of alpha characters | Predominantly non-Hebrew text |
| Word count | < 15 words | Too short to be a meaningful paragraph |

Result: **340 valid paragraphs** from 1,123 raw (≈ 30% acceptance rate).

## Alternatives Considered

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Rule-based filter** | Fast, deterministic, inspectable | May reject borderline valid paragraphs | **Selected** |
| LLM quality classifier | High precision | Expensive, slow for 1,123 chunks | Rejected |
| Manual curation | Perfect quality | Not scalable across 22 PDFs | Rejected |
| No filter | Simple | Poor game quality; formula paragraphs unsolvable | Rejected |

## Consequences

- **Good**: Fully deterministic — same input always produces same valid set.
- **Good**: Fast at corpus-build time (runs once offline).
- **Trade-off**: 30% acceptance rate may feel aggressive. However, play-testing confirmed that rejected paragraphs were genuinely unusable (formula blocks, garbled text).
- **Constraint**: The 40% Hebrew ratio threshold is tunable. Lower it if valid paragraphs with heavy English notation are being rejected.
- **Monitoring**: Log rejected paragraph IDs at build time. Review if valid-set size drops below 200 after future PDF updates.
