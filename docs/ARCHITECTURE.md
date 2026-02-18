# Q21G — Architecture Documentation

Version: 1.0.0 | Last updated: 2025-01

---

## 1. C4 Context Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Q21G League Platform                          │
│                                                                      │
│   ┌───────────┐     Gmail API      ┌──────────────────────────────┐ │
│   │  Referee  │◄──────────────────►│       League Manager         │ │
│   │  Agent    │                   │  (user0001@gtai-tech.org)     │ │
│   │(user0006) │                   └──────────────────────────────┘ │
│   └─────┬─────┘                                                     │
│         │  Gmail API                                                 │
│   ┌─────▼─────┐                   ┌──────────────────────────────┐ │
│   │  Player   │                   │       Game Logger             │ │
│   │  Agent    │◄──────────────────►│  (user0002@gtai-tech.org)    │ │
│   │(user0005) │                   └──────────────────────────────┘ │
│   └───────────┘                                                     │
│                                                                      │
│   External: Anthropic API (Claude Sonnet), Hugging Face Models      │
└─────────────────────────────────────────────────────────────────────┘
```

**System users:**
- **League Manager**: Orchestrates rounds, sends game start messages, collects scores
- **Logger**: Receives all communications for audit trail
- **Referee Agent** (our implementation): Picks paragraphs, generates hints, scores guesses
- **Player Agent** (our implementation): Searches KB, asks questions, guesses opening sentences

---

## 2. C4 Container Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Q21G Monorepo                                    │
│                                                                            │
│   ┌──────────────────────────┐   ┌──────────────────────────────────────┐ │
│   │     Referee Agent        │   │          Player Agent                 │ │
│   │  Q21G-referee-whl/       │   │       Q21G-player-whl/               │ │
│   │                          │   │                                       │ │
│   │  ┌──────────────────┐   │   │  ┌────────────────────────────────┐  │ │
│   │  │    my_ai.py      │   │   │  │         my_player.py           │  │ │
│   │  │  (4 callbacks)   │   │   │  │        (4 callbacks)           │  │ │
│   │  └────────┬─────────┘   │   │  └──────────────┬─────────────────┘  │ │
│   │           │              │   │                 │                     │ │
│   │  ┌────────▼─────────┐   │   │  ┌──────────────▼─────────────────┐  │ │
│   │  │ referee_helpers  │   │   │  │   player_helpers.py            │  │ │
│   │  │ referee_scoring  │   │   │  │   player_guess.py              │  │ │
│   │  └────────┬─────────┘   │   │  └──────────────┬─────────────────┘  │ │
│   │           │              │   │                 │                     │ │
│   │  ┌────────▼─────────┐   │   │  ┌──────────────▼─────────────────┐  │ │
│   │  │  RLGMRunner      │   │   │  │         run.py                 │  │ │
│   │  │  (SDK internal)  │   │   │  │   (SDK internal: --watch)      │  │ │
│   │  └──────────────────┘   │   │  └────────────────────────────────┘  │ │
│   └──────────┬───────────────┘   └───────────────┬──────────────────────┘ │
│              │                                    │                         │
│              └──────────────┬─────────────────────┘                        │
│                             │                                               │
│   ┌─────────────────────────▼───────────────────────────────────────────┐  │
│   │                    Shared Knowledge Base                              │  │
│   │                   knowledge_base/                                    │  │
│   │                                                                       │  │
│   │  ┌────────────┐  ┌────────────┐  ┌──────────────┐  ┌─────────────┐ │  │
│   │  │  db.py     │  │vector_store│  │llm_client.py │  │skill_plugin │ │  │
│   │  │ (SQLite)   │  │(ChromaDB)  │  │(Claude API)  │  │.py          │ │  │
│   │  └────────────┘  └────────────┘  └──────────────┘  └─────────────┘ │  │
│   │                                                                       │  │
│   │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│   │  │               data/ (gitignored)                                 │ │  │
│   │  │   paragraphs.db (SQLite)   chroma_db/   paragraphs.json         │ │  │
│   │  └─────────────────────────────────────────────────────────────────┘ │  │
│   └───────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
│   ┌───────────────────────────────────────────────────────────────────────┐  │
│   │                       skills/  (Prompt Templates)                      │  │
│   │  referee_hint_generator.md   referee_question_answerer.md              │  │
│   │  referee_scorer.md           player_question_generator.md              │  │
│   │  player_guess_maker.md       warmup_solver.md                          │  │
│   └───────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. C4 Component Diagram — Knowledge Base

```
┌────────────────────────────────────────────────────────────────┐
│                    knowledge_base package                        │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  OFFLINE (build once)                                     │  │
│   │                                                           │  │
│   │  corpus_builder.py                                        │  │
│   │    └─ pdfplumber → raw text → paragraphs.json (1123 raw) │  │
│   │                                                           │  │
│   │  paragraph_filter.py                                      │  │
│   │    └─ Filter formula/code/noise → 340 valid paragraphs   │  │
│   │                                                           │  │
│   │  sentence_extractor.py                                    │  │
│   │    └─ Hebrew RTL first-sentence extraction                │  │
│   │                                                           │  │
│   │  difficulty_indexer.py                                    │  │
│   │    └─ Uniqueness + cluster scores → difficulty_score [0,1]│  │
│   └──────────────────────────────────────────────────────────┘  │
│                             │                                    │
│                             ▼                                    │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  RUNTIME (called per-game)                               │  │
│   │                                                           │  │
│   │  db.py (ParagraphDB)                                     │  │
│   │    └─ SQLite: get_random(), get_by_difficulty_range()    │  │
│   │                                                           │  │
│   │  vector_store.py (VectorStore)                           │  │
│   │    └─ ChromaDB: search(hint, filter_pdf, n)              │  │
│   │    └─ Dual search: PDF-filtered + unfiltered, merge      │  │
│   │                                                           │  │
│   │  llm_client.py (LLMClient)                               │  │
│   │    └─ Claude Sonnet API with 2x retry + exponential      │  │
│   │       backoff                                            │  │
│   │                                                           │  │
│   │  skill_plugin.py (SkillPlugin / SkillRegistry)           │  │
│   │    └─ ABC + MarkdownSkillPlugin + registry pattern       │  │
│   └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

---

## 4. Game Protocol Sequence Diagram

```
LM (League        Referee Agent        Player Agent
 Manager)            (my_ai.py)         (my_player.py)
    │                    │                    │
    │── round_start ────►│                    │
    │                    │                    │
    │          [get_round_start_info]          │
    │          select paragraph (difficulty    │
    │          filter + Goldilocks strategy)   │
    │          generate hint (Taboo check +    │
    │          self-test via ChromaDB)         │
    │                    │                    │
    │◄── book_name ──────│                    │
    │    book_hint        │                    │
    │    association_word │                    │
    │                    │                    │
    │── game_start ───────────────────────────►│
    │   (book_name, book_hint, assoc_word)     │
    │                    │                    │
    │                              [get_questions]
    │                              dual ChromaDB search
    │                              store 20 candidates on self
    │                              LLM generates 20 questions
    │                              (shuffled to reduce bias)
    │                    │                    │
    │◄── 20 questions ────────────────────────│
    │                    │                    │
    │── questions ───────►│                    │
    │                    │                    │
    │          [get_answers]                   │
    │          batch all 20 in ONE LLM call   │
    │          answer A/B/C/D/Not Relevant     │
    │                    │                    │
    │◄── 20 answers ─────│                    │
    │                    │                    │
    │── answers ──────────────────────────────►│
    │                    │                    │
    │                              [get_guess]
    │                              re-rank candidates by Q&A evidence
    │                              exact sentence lookup from SQLite
    │                              LLM generates justifications
    │                    │                    │
    │◄── guess (sentence + justifications) ───│
    │                    │                    │
    │── guess ───────────►│                    │
    │                    │                    │
    │          [get_score_feedback]            │
    │          string pre-check (≥95% →       │
    │          override to 98 pts)            │
    │          LLM scores remaining components│
    │          weighted sum → league points   │
    │                    │                    │
    │◄── score + feedback│                    │
    │                    │                    │
```

---

## 5. Architecture Decision Records (ADRs)

All ADRs live in `docs/adr/`:

| ADR | Decision | Status |
|-----|----------|--------|
| [ADR-001](adr/ADR-001-embedding-model.md) | Use `paraphrase-multilingual-MiniLM-L12-v2` for Hebrew embeddings | Accepted |
| [ADR-002](adr/ADR-002-state-management.md) | Store referee secrets on `self` (not ctx) | Accepted |
| [ADR-003](adr/ADR-003-hint-generation-strategy.md) | Goldilocks difficulty targeting (0.4–0.7 range) | Accepted |
| [ADR-004](adr/ADR-004-dual-search-strategy.md) | Dual-search with PDF-filtered priority slots | Accepted |
| [ADR-005](adr/ADR-005-paragraph-filtering.md) | Multi-criteria paragraph filter (1123→340 valid) | Accepted |

---

## 6. SDK API Contract

### Referee Callbacks (RefereeAI base class)

| Method | Input (ctx keys) | Output (dict keys) | Deadline |
|--------|-------------------|-------------------|---------|
| `get_warmup_question` | round_number, player_a, player_b | `{question: str}` | 30s |
| `get_round_start_info` | round_number, round_id, player_a, player_b | `{book_name, book_hint, association_word}` | 60s |
| `get_answers` | questions (list), book_name | `{answers: [{question_number, answer}]}` | 120s |
| `get_score_feedback` | opening_sentence, sentence_justification, associative_word, word_justification, confidence | `{private_score, feedback}` | 180s |

### Player Callbacks (PlayerAI base class)

| Method | Input (ctx keys) | Output (dict keys) | Deadline |
|--------|-------------------|-------------------|---------|
| `get_warmup_answer` | question | `{answer: str}` | 300s |
| `get_questions` | book_name, book_hint, association_word | `{questions: [str×20]}` | 600s |
| `get_guess` | book_name, book_hint, association_word, answers | `{opening_sentence, sentence_justification, associative_word, word_justification, confidence}` | 300s |

---

## 7. Data Flow Architecture

```
PDF Files (22 Hebrew academic PDFs, 39 MB)
         │
         ▼ pdfplumber
Raw text paragraphs (1,123 total)
         │
         ▼ paragraph_filter.py
Valid paragraphs (340)
    - No formulas (≥2 `=`)
    - No decimals (≥3)
    - No `(cid:` artifacts
    - ≥40% Hebrew character ratio
    - 50-200 word range
         │
         ├──► SQLite (paragraphs.db)
         │      └─ id, text, opening_sentence, book_name,
         │         difficulty_score, is_valid
         │
         └──► ChromaDB (chroma_db/)
                └─ sentence-transformers embeddings (384-dim)
                   cosine distance metric
                   metadata: book_name, paragraph_id
```

---

## 8. Scoring Architecture

```python
# Weighted scoring formula
private_score = (
    0.50 * sentence_score        +  # 0-100: exact sentence match
    0.20 * justification_score   +  # 0-100: cites ≥3 Q&A pairs
    0.20 * word_score            +  # 0-100: association word match
    0.10 * word_justification    +  # 0-100: cites ≥2 Q&A pairs
)

# String pre-check (referee_scoring.py)
similarity = SequenceMatcher(None, guess, actual).ratio()
if similarity >= 0.95:
    sentence_score = 98  # Override LLM score

# League points mapping
if private_score >= 85: league_points = 3
elif private_score >= 70: league_points = 2
elif private_score >= 50: league_points = 1
else: league_points = 0
```

---

## 9. Plugin Architecture (Skill System)

```
skills/*.md (6 prompt templates)
         │
         ▼ build_default_registry(SKILLS_DIR)
SkillRegistry
    ├── referee_hint_generator.md → MarkdownSkillPlugin
    ├── referee_question_answerer.md → MarkdownSkillPlugin
    ├── referee_scorer.md → MarkdownSkillPlugin
    ├── player_question_generator.md → MarkdownSkillPlugin
    ├── player_guess_maker.md → MarkdownSkillPlugin
    └── warmup_solver.md → MarkdownSkillPlugin

# Runtime usage (referee_helpers.py, player_helpers.py)
registry = build_default_registry(SKILLS_DIR)
prompt = registry.get("referee_hint_generator.md").get_prompt()
```

Custom skills can be injected at runtime:
```python
class MyCustomHintPlugin(SkillPlugin):
    @property
    def name(self) -> str:
        return "referee_hint_generator.md"  # replaces built-in
    def get_prompt(self, context=None) -> str:
        return "My custom prompt..."

registry.register(MyCustomHintPlugin())
```

---

## 10. Deployment Architecture

```
Production Deployment (single Linux machine / WSL2)

Terminal 1: Referee
  cd Q21G-referee-whl/examples
  source ../../.venv/bin/activate
  python main.py
  # Blocks, processes rounds via Gmail polling

Terminal 2: Player
  cd Q21G-player-whl
  source ../.venv/bin/activate
  python run.py --watch
  # Blocks, watches Gmail inbox for game invitations

Shared filesystem:
  knowledge_base/data/paragraphs.db   (SQLite, ~2 MB)
  knowledge_base/data/chroma_db/      (ChromaDB, ~50 MB)
  .venv/                              (Python environment)
  .env                                (API keys, gitignored)
```

---

## 11. Non-Functional Characteristics (ISO/IEC 25010)

| Quality Attribute | Design Decision | Evidence |
|---|---|---|
| **Performance** | Single LLM call for all 20 answers | Stays within 120s deadline |
| **Reliability** | 2× retry + exponential backoff in LLMClient | Handles rate limits + transient errors |
| **Maintainability** | 150-line file limit, modular helper files | Each file has single responsibility |
| **Extensibility** | SkillPlugin ABC + SkillRegistry | Custom prompts injectable at runtime |
| **Security** | API keys in `.env` (gitignored) | No credentials in source control |
| **Correctness** | String pre-check in scoring | Prevents LLM from under-scoring exact matches |
| **Testability** | Mock-friendly LLMClient, 94 tests, ≥70% coverage | CI/CD enforced via GitHub Actions |
