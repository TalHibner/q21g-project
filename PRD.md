# Q21G Product Requirements Document

**Version**: 1.0.0
**Date**: 2026-02-17
**Status**: Implemented (Phases 0-5 complete)

---

## 1. Overview

### 1.1 Problem Statement

Build two AI agents (Referee and Player) that compete in a "21 Questions" game over Gmail. The agents use a shared knowledge base built from 22 Hebrew academic PDFs. The Referee selects a secret paragraph and provides hints; the Player asks strategic questions and guesses the paragraph's opening sentence.

### 1.2 Success Criteria

- Private score consistently above 70 (2+ league points per game)
- Target: 85+ private score (3 league points) on 60%+ of games
- All 4 callbacks per agent complete within SDK timeouts
- Zero crashes from LLM failures or network errors

### 1.3 Users

- **League Manager**: External system broadcasting season events (not our code)
- **Opponent Referees/Players**: Other teams' agents we play against via Gmail
- **Course Staff**: Evaluates our implementation

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Gmail (OAuth API)                       │
│                   Protocol: league.v2 / Q21G.v1              │
└────────────┬─────────────────────────────┬──────────────────┘
             │                             │
     ┌───────▼───────┐            ┌────────▼────────┐
     │  Referee SDK  │            │   Player SDK    │
     │  (RLGMRunner) │            │   (run.py)      │
     │               │            │                 │
     │  Poll 10s     │            │  Poll 10s       │
     │  Parse msgs   │            │  Parse msgs     │
     │  Route to AI  │            │  Route to AI    │
     └───────┬───────┘            └────────┬────────┘
             │                             │
     ┌───────▼───────┐            ┌────────▼────────┐
     │  MyRefereeAI  │            │  MyPlayerAI     │
     │  (my_ai.py)   │            │  (my_player.py) │
     │               │            │                 │
     │  4 callbacks  │            │  4 callbacks    │
     └───────┬───────┘            └────────┬────────┘
             │                             │
     ┌───────▼───────┐            ┌────────▼────────┐
     │    Helpers     │            │    Helpers      │
     │  - hint gen   │            │  - search       │
     │  - answering  │            │  - questions    │
     │  - scoring    │            │  - guess        │
     └───────┬───────┘            └────────┬────────┘
             │                             │
             └──────────┬──────────────────┘
                        │
              ┌─────────▼──────────┐
              │   Shared Layer     │
              │                    │
              │  llm_client.py     │  Claude API (retry + timeout)
              │  skills/*.md       │  LLM prompt templates
              └─────────┬──────────┘
                        │
              ┌─────────▼──────────┐
              │  Knowledge Base    │
              │                    │
              │  ParagraphDB       │  SQLite (fast lookups)
              │  VectorStore       │  ChromaDB (semantic search)
              │  ParagraphFilter   │  Quality filtering
              │  SentenceExtractor │  Hebrew sentence parsing
              │  DifficultyIndexer │  Paragraph difficulty scores
              └────────────────────┘
                        │
              ┌─────────▼──────────┐
              │    Data Layer      │
              │                    │
              │  22 Hebrew PDFs    │  Source material
              │  paragraphs.json   │  Extracted corpus
              │  paragraphs.db     │  SQLite database
              │  chroma_db/        │  Vector embeddings
              └────────────────────┘
```

### 2.2 Data Flow Per Game Round

```
┌──────────┐                                        ┌──────────┐
│ REFEREE  │                                        │  PLAYER  │
└────┬─────┘                                        └────┬─────┘
     │                                                   │
     │  CB1: get_warmup_question()                       │
     │  ──── "What is 7 * 8?" ─────────────────────────> │
     │                                                   │  CB1: get_warmup_answer()
     │  <──── "56" ──────────────────────────────────── │
     │                                                   │
     │  CB2: get_round_start_info()                      │
     │  1. Select paragraph (SQLite random)              │
     │  2. Generate hint (LLM + taboo check)             │
     │  3. Self-test hint (ChromaDB)                     │
     │  4. Store: _paragraph_text,                       │
     │           _opening_sentence,                      │
     │           _association_word                        │
     │  ──── {book_name, book_hint, association_word} ─> │
     │                                                   │  CB2: get_questions()
     │                                                   │  1. Dual search (filtered + unfiltered)
     │                                                   │  2. Store _candidates (top 20)
     │                                                   │  3. Generate 20 questions (LLM)
     │  <──── {questions: [{q1..q20}]} ──────────────── │
     │                                                   │
     │  CB3: get_answers()                               │
     │  1. Answer all 20 Qs in 1 LLM call               │
     │  ──── {answers: [A, B, C, ...]} ────────────────> │
     │                                                   │  CB3: get_guess()
     │                                                   │  1. Shuffle candidates (anti-bias)
     │                                                   │  2. Score each candidate vs Q&A
     │                                                   │  3. Pick highest consistency
     │                                                   │  4. Look up exact opening sentence
     │                                                   │  5. Extract association word from text
     │  <──── {opening_sentence, associative_word,       │
     │         justifications, confidence} ──────────── │
     │                                                   │
     │  CB4: get_score_feedback()                        │
     │  1. String pre-check (SequenceMatcher)            │
     │  2. LLM scoring (4 components)                    │
     │  3. Weighted private_score                        │
     │  4. League points (85→3, 70→2, 50→1)             │
     │  ──── {league_points, private_score,              │
     │        breakdown, feedback} ─────────────────────>│
     │                                                   │  CB4: on_score_received()
     │                                                   │  Log results
```

---

## 3. Component Specifications

### 3.1 Knowledge Base Pipeline

**Input**: 22 Hebrew academic PDF files (course lectures on ML/AI)

**Pipeline**:

```
PDF files
    │  pdfplumber (page-by-page extraction)
    ▼
Raw text (per page)
    │  split on double newlines, filter by word count (>=15)
    ▼
Raw paragraphs (~1123)
    │  paragraph_filter.py (reject formulas, code, noise, low Hebrew ratio)
    ▼
Valid paragraphs (~340)
    │  sentence_extractor.py (Hebrew RTL-aware first sentence)
    ▼
paragraphs.json (id, pdf_name, text, opening_sentence, word_count)
    │
    ├──> paragraphs.db (SQLite — fast lookups, random selection)
    ├──> chroma_db/ (ChromaDB — semantic search, cosine distance)
    └──> difficulty_score (per-paragraph, stored in SQLite)
```

**Paragraph Filter Criteria** (`paragraph_filter.py`):
- Must contain Hebrew characters in opening sentence
- Opening sentence >= 8 words
- Not code (no `=`, `{`, `import`, etc. as first token)
- Not heading/TOC (no short numbered lines)
- Not formulaic (< 2 equals signs, < 3 decimals, no P() notation)
- No code artifacts (`.json`, `.py`, `API`, `http://`, etc.)
- Hebrew ratio >= 40% of alphabetic characters
- Word uniqueness >= 40% (rejects tables)

**Difficulty Scoring** (`difficulty_indexer.py`):
- 0.3 * nearest_neighbor_similarity (how confusable)
- 0.3 * (1 - opening_sentence_uniqueness) (generic opener = harder)
- 0.2 * normalized_pdf_paragraph_count (more paragraphs = harder)
- 0.2 * topic_commonality (cross-PDF similarity)
- Target range for referee selection: 0.4-0.7

### 3.2 Referee Agent

**File**: `Q21G-referee-whl/examples/my_ai.py` (113 lines)

**Dependencies**:
- `referee_helpers.py` (144 lines) — hint generation, question answering
- `referee_scoring.py` (120 lines) — scoring with string pre-check

**Callback Details**:

| # | Callback | SDK Timeout | LLM Calls | Key Logic |
|---|---|---|---|---|
| 1 | `get_warmup_question` | 30s | 0 | Random math: `a op b` |
| 2 | `get_round_start_info` | 60s | 2-6 | Paragraph select + hint gen + self-test |
| 3 | `get_answers` | 120s | 1 | Batch 20 Qs in one prompt |
| 4 | `get_score_feedback` | 180s | 1 | Pre-check + LLM + weighted formula |

**Hint Generation Flow**:
1. Select random paragraph (30-200 words, difficulty 0.4-0.7, is_valid=1)
2. Extract forbidden words from paragraph text
3. LLM generates 15-word hint using only synonyms/paraphrases
4. Validate: no taboo word overlap (set intersection)
5. Self-test: ChromaDB can find paragraph in top-10 with this hint
6. Retry up to 2x per paragraph, 3 different paragraphs

**Scoring Formula**:
```
private_score = 0.50 * sentence_score
              + 0.20 * sentence_justification_score
              + 0.20 * association_word_score
              + 0.10 * word_justification_score

League points:
  85-100 → 3 points
  70-84  → 2 points
  50-69  → 1 point
  0-49   → 0 points
```

**String Pre-Check Overrides** (before LLM scoring):
| Similarity (SequenceMatcher) | Override Score |
|---|---|
| >= 0.95 | 98 |
| >= 0.85 | 88 |
| >= 0.70 | 75 |
| Word >= 0.90 | 95 |

### 3.3 Player Agent

**File**: `Q21G-player-whl/my_player.py` (95 lines)

**Dependencies**:
- `player_helpers.py` (111 lines) — search, warmup, question generation
- `player_guess.py` (125 lines) — re-ranking, guess with Q&A citations

**Search Strategy (Dual Search)**:
1. **Filtered search**: `vs.search_by_pdf(hint, book_name, n=20)` — same PDF only
2. **Unfiltered search**: `vs.search(hint, n=20)` — all paragraphs
3. **Priority merge**: All filtered results first, fill remaining with unfiltered
4. **Fallback**: Random paragraphs from the PDF if both searches empty

**Re-Ranking Strategy**:
1. Shuffle top-8 candidates (removes position bias)
2. Track shuffle mapping (shuffled position -> original index)
3. LLM scores each candidate's consistency with 20 Q&A answers
4. Pick candidate with highest consistency score
5. Look up exact opening sentence from stored candidate data (never trust LLM copy)
6. Extract association word from paragraph text keywords

**Justification Requirements**:
- `sentence_justification`: Must cite >= 3 specific Q numbers with answers
- `word_justification`: Must cite >= 2 specific Q numbers with answers

### 3.4 Shared LLM Client

**File**: `knowledge_base/llm_client.py` (45 lines)

**Model**: `claude-sonnet-4-20250514`

**Retry Policy**:
- Retries 2x on: `APITimeoutError`, `RateLimitError`, `APIConnectionError`, `InternalServerError`
- Exponential backoff: 1s, 2s between retries
- No retry on `AuthenticationError` (immediate fail)
- Per-call network timeouts: 15s (hint), 60s (answers), 90s (scoring/questions)

**Graceful Degradation**:

| Callback | On Total LLM Failure | Fallback |
|---|---|---|
| Hint generation | Catches error, tries next paragraph | Generic fallback hint |
| Answer questions | Catches error | All answers = "Not Relevant" |
| Score guess | Catches error | String pre-check scores only |
| Generate questions | Catches error | 20 generic questions |
| Make guess | Catches error | Top-ranked candidate |

### 3.5 Skills System

6 Markdown prompt templates in `skills/`:

```
skills/
├── warmup_solver.md               # Math question solving (no LLM needed)
├── referee_hint_generator.md      # Paragraph -> hint + association word
├── referee_question_answerer.md   # Paragraph + 20 Qs -> 20 answers
├── referee_scorer.md              # Guess vs actual -> 4 scores + feedback
├── player_question_generator.md   # Candidates + hint -> 20 strategic Qs
└── player_guess_maker.md          # Candidates + Q&A -> final guess
```

Loaded at runtime via:
```python
SKILLS_DIR = Path(__file__).resolve().parents[N] / "skills"
skill_text = (SKILLS_DIR / "referee_scorer.md").read_text()
```

---

## 4. Data Models

### 4.1 Paragraph Record

```python
{
    "id": "00011_p0059",              # {pdf_stem}_p{index:04d}
    "pdf_name": "00011",              # PDF filename stem
    "pdf_filename": "00011.pdf",
    "paragraph_index": 59,
    "opening_sentence": "...",         # First sentence (Hebrew)
    "full_text": "...",                # Complete paragraph text
    "word_count": 87,
    "is_valid": 1,                     # Passes paragraph filter
    "difficulty_score": 0.54           # 0.0-1.0, target 0.4-0.7
}
```

### 4.2 Referee Callback Returns

```python
# CB1: get_warmup_question
{"warmup_question": "What is 7 * 8?"}

# CB2: get_round_start_info
{"book_name": "00011", "book_hint": "...", "association_word": "academia"}

# CB3: get_answers
{"answers": [{"question_number": 1, "answer": "A"}, ...]}  # 20 items

# CB4: get_score_feedback
{
    "league_points": 3,
    "private_score": 87.5,
    "breakdown": {
        "opening_sentence_score": 98.0,
        "sentence_justification_score": 85.0,
        "associative_word_score": 65.0,
        "word_justification_score": 70.0,
    },
    "feedback": {
        "opening_sentence": "150-200 words...",
        "associative_word": "150-200 words...",
    }
}
```

### 4.3 Player Callback Returns

```python
# CB1: get_warmup_answer
{"answer": "56"}

# CB2: get_questions
{"questions": [
    {"question_number": 1, "question_text": "...",
     "options": {"A": "...", "B": "...", "C": "...", "D": "..."}},
    ...  # 20 items
]}

# CB3: get_guess
{
    "opening_sentence": "exact text from DB lookup",
    "sentence_justification": "Q3(A) confirmed..., Q7(B) ruled out...",
    "associative_word": "keyword from paragraph text",
    "word_justification": "Q17(A) confirmed..., Q18(B) narrowed...",
    "confidence": 0.85,
}
```

---

## 5. Configuration

### 5.1 Referee Config (`Q21G-referee-whl/config.json`)

```json
{
    "credentials_path": "/path/to/client_secret.json",
    "token_path": "/path/to/token.json",
    "referee_id": "user0006",
    "group_id": "grogu123",
    "display_name": "grogu123-referee",
    "league_manager_email": "user0001@gtai-tech.org",
    "poll_interval_seconds": 10
}
```

### 5.2 Player Config (`Q21G-player-whl/js/config.json`)

```json
{
    "league": {
        "manager_email": "user0001@gtai-tech.org",
        "protocol_version": "league.v2"
    },
    "player": {
        "user_id": "user0005",
        "display_name": "grogu123-player"
    },
    "app": {
        "player_ai_module": "my_player",
        "player_ai_class": "MyPlayerAI"
    }
}
```

### 5.3 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API key for LLM calls |
| `HF_TOKEN` | No | HuggingFace token (faster model downloads) |

---

## 6. Testing

### 6.1 Test Suite (81 tests)

| Module | Tests | What's Covered |
|---|---|---|
| `test_knowledge_base.py` | ~15 | Sentence extraction, DB queries, vector search, filter |
| `test_referee.py` | ~20 | Warmup, hint gen, taboo, scoring formula, feedback |
| `test_player.py` | ~25 | Search, questions, guess, shuffle, fallbacks |
| `test_game_simulation.py` | ~15 | Full round chain, edge cases |
| `test_live_simulation.py` | ~6 | Live LLM calls (skipped without API key) |

### 6.2 Running Tests

```bash
pytest tests/ -v                           # All tests
pytest tests/test_referee.py -v            # Referee only
pytest tests/test_player.py -v             # Player only
pytest tests/test_game_simulation.py -v    # E2E simulation
```

---

## 7. Performance Benchmarks

### 7.1 Score Progression (Development)

| Stage | Avg Private Score | League Points (5 games) | Exact Matches |
|---|---|---|---|
| Initial implementation | 34.8 | 0 | 0/5 |
| + Paragraph filter + pre-check | 51.4 | 5 | 0/5 |
| + Sentence extractor fix | 54.0 | 5 | 0/5 |
| + Dual search priority merge | 53.6 | 5 | 1/5 |
| + Shuffle + per-candidate scoring | 57.3 | 5 | 4/5 |
| + Justification Q&A citations | 86.5 (best) | 3 (best game) | 4/5 |

### 7.2 Timeout Compliance

| Callback | SDK Deadline | Max LLM Calls | Worst Case | Margin |
|---|---|---|---|---|
| `get_warmup_question` | 30s | 0 | <1ms | 30s |
| `get_round_start_info` | 60s | 6 | ~48s | 12s |
| `get_answers` | 120s | 1 | ~10s | 110s |
| `get_score_feedback` | 180s | 1 | ~10s | 170s |

---

## 8. Development Phases & Timeline

| Phase | Description | Status | Timeline |
|---|---|---|---|
| 0 | Project setup, venv, SDK installation | Done | Week 1 |
| 1 | Knowledge base (PDF -> SQLite + ChromaDB) | Done | Weeks 1-2 |
| 2 | Referee implementation (4 callbacks) | Done | Weeks 2-3 |
| 3 | Player implementation (4 callbacks) | Done | Weeks 3-4 |
| 4 | End-to-end simulation + optimization | Done | Weeks 4-5 |
| 5 | Gmail integration + production deployment | Done | Week 5 |
| 6 | Testing, documentation, multiprocessing polish | Done | Week 6 |

### 8.1 Milestones

| Milestone | Date | Deliverable |
|---|---|---|
| M1: KB Pipeline Operational | Week 2 | 22 PDFs → 340 valid paragraphs in SQLite + ChromaDB |
| M2: Referee Self-Play | Week 3 | All 4 referee callbacks working against mock player |
| M3: Player Complete | Week 4 | All 4 player callbacks, dual search, question generation |
| M4: Score Optimization | Week 5 | Private score ≥70 average, 2+ league points/game |
| M5: Production Ready | Week 5 | Gmail OAuth integration, live tournament ready |
| M6: Submission Ready | Week 6 | ≥70% test coverage, full documentation, multiprocessing |

---

## 9. File Reference

### 9.1 Our Code (what we wrote)

| File | Lines | Purpose |
|---|---|---|
| `Q21G-referee-whl/examples/my_ai.py` | 113 | Referee 4 callbacks |
| `Q21G-referee-whl/examples/referee_helpers.py` | 144 | Hint gen, Q&A answering |
| `Q21G-referee-whl/examples/referee_scoring.py` | 120 | Scoring + pre-check |
| `Q21G-referee-whl/examples/main.py` | 58 | Referee entry point |
| `Q21G-player-whl/my_player.py` | 95 | Player 4 callbacks |
| `Q21G-player-whl/player_helpers.py` | 111 | Search, warmup, questions |
| `Q21G-player-whl/player_guess.py` | 125 | Re-ranking + guess |
| `knowledge_base/llm_client.py` | 45 | Shared LLM client |
| `knowledge_base/corpus_builder.py` | 103 | PDF extraction |
| `knowledge_base/sentence_extractor.py` | 93 | Hebrew sentence parsing |
| `knowledge_base/paragraph_filter.py` | 130 | Quality filter |
| `knowledge_base/db.py` | 114 | SQLite wrapper |
| `knowledge_base/vector_store.py` | 107 | ChromaDB wrapper |
| `knowledge_base/difficulty_indexer.py` | 148 | Difficulty scoring |
| `skills/*.md` | 890 | 6 LLM prompt templates |
| `tests/*.py` | ~1500 | 81 tests |
| **Total** | **~3796** | |

### 9.2 SDK Code (don't modify)

| Directory | Purpose |
|---|---|
| `Q21G-referee-whl/src/q21_referee/` | Referee SDK internals |
| `Q21G-player-whl/_infra/` | Player SDK internals |
