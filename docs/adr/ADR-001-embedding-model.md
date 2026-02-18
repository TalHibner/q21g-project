# ADR-001: Hebrew Embedding Model Selection

**Date**: 2025-01
**Status**: Accepted

## Context

The knowledge base stores ~1,123 paragraphs from 22 Hebrew academic PDFs. ChromaDB requires an embedding function to convert Hebrew text into vectors for semantic search. The game requires real-time search (within the 600 s player callback deadline), so model speed matters alongside quality.

The course material code-switches between Hebrew prose and English technical terms (e.g., "transformer", "attention", "LLM"), so the model must handle both.

## Decision

Use **`paraphrase-multilingual-MiniLM-L12-v2`** from Sentence Transformers.

## Alternatives Considered

| Model | Dims | Hebrew Quality | Speed | Why Rejected |
|-------|------|---------------|-------|--------------|
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | ★★★★ | Fast | **Selected** |
| `paraphrase-multilingual-mpnet-base-v2` | 768 | ★★★★★ | Medium | 2× slower, marginal gain |
| `intfloat/multilingual-e5-large` | 1024 | ★★★★★ | Slow | Too slow for real-time, large download |
| `imvladikon/sentence-transformers-alephbert` | 768 | ★★★★★ | Medium | Hebrew-only; poor on English code-switch |
| `all-MiniLM-L6-v2` | 384 | ★★ | Fastest | English-centric, poor Hebrew support |

## Consequences

- **Good**: Native ChromaDB support via `SentenceTransformerEmbeddingFunction`, fast enough for real-time callbacks, good multilingual coverage.
- **Good**: Handles English–Hebrew code-switching common in academic PDFs.
- **Trade-off**: Not the highest-quality Hebrew model. If semantic search accuracy proves insufficient in live play, upgrade to `multilingual-mpnet-base-v2`.
- **Constraint**: Model download (~500 MB) required at first run; cached after that. Set `HF_TOKEN` for private/gated models.
