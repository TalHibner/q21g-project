# Q21G Project — Claude Code Context

## What Is This Project

Q21G is a competitive "21 Questions" game where AI agents play via Gmail. We implement TWO agents:
- **Referee**: Chooses a paragraph from course PDFs, gives hints, answers questions, scores guesses
- **Player**: Asks 20 strategic questions, then guesses the paragraph's opening sentence

Both agents use a shared knowledge base (RAG pipeline) built from 22 Hebrew academic PDFs.

For SDK dev principles (150-line limit, TDD, etc.), see:
- `Q21G-referee-whl/CLAUDE.md`
- `Q21G-player-whl/CLAUDE.md`

## Repository Structure

Single monorepo. SDK repos live as subdirectories, pip-installed in editable mode.

```
q21g-project/                            # Workspace root (Claude Code opens this)
├── CLAUDE.md                            # ← This file (read by Claude Code)
├── DESIGN.md                            # RAG pipeline design
├── TASKS.md                             # Implementation tasks
├── VERIFICATION_REPORT.md               # PDF vs SDK discrepancies
│
├── skills/                              # All 6 LLM skill prompts
│   ├── warmup_solver.md
│   ├── referee_hint_generator.md
│   ├── referee_question_answerer.md
│   ├── referee_scorer.md
│   ├── player_question_generator.md
│   └── player_guess_maker.md
│
├── knowledge_base/                      # Shared RAG infrastructure
│   ├── __init__.py
│   ├── setup.py                         # pip install -e knowledge_base/
│   ├── corpus_builder.py
│   ├── db.py
│   ├── vector_store.py
│   ├── sentence_extractor.py
│   └── data/                            # Pre-built (gitignored)
│       ├── paragraphs.json
│       ├── paragraphs.db
│       └── chroma_db/
│
├── course_pdfs/                         # 22 Hebrew PDF files (gitignored)
│
├── tests/
│   ├── test_knowledge_base.py
│   ├── test_referee.py
│   ├── test_player.py
│   └── test_game_simulation.py          # End-to-end referee ↔ player
│
├── Q21G-referee-whl/                    # Referee SDK (pip install -e, don't modify internals)
│   ├── CLAUDE.md                        # SDK's own dev principles
│   ├── examples/
│   │   ├── my_ai.py                     # ← OUR MyRefereeAI — 4 callbacks
│   │   └── main.py                      # ← Production entry point
│   ├── src/q21_referee/                 # SDK internals (don't modify)
│   └── ...
│
└── Q21G-player-whl/                     # Player SDK (pip install -e, don't modify internals)
    ├── CLAUDE.md                        # SDK's own dev principles
    ├── my_player.py                     # ← OUR MyPlayerAI — 4 callbacks
    ├── run.py                           # ← Production entry point
    ├── _infra/                          # SDK internals (don't modify)
    └── ...
```

## Setup

```bash
cd q21g-project
pip install -e Q21G-referee-whl/         # provides: q21_referee
pip install -e Q21G-player-whl/          # provides: q21_player
pip install -e knowledge_base/           # provides: knowledge_base (importable everywhere)
pip install pdfplumber chromadb sentence-transformers anthropic
```

## How Imports Work

```python
# In Q21G-referee-whl/examples/my_ai.py:
from q21_referee import RefereeAI              # from SDK (pip installed)
from knowledge_base.db import ParagraphDB      # from shared package (pip installed)

# In Q21G-player-whl/my_player.py:
from q21_player import PlayerAI                # from SDK (pip installed)
from knowledge_base.db import ParagraphDB      # from shared package (pip installed)
```

## How Skills Are Loaded

Skills live at `q21g-project/skills/`. Both `my_ai.py` and `my_player.py` load them relative to the workspace root:

```python
from pathlib import Path

# Find workspace root (q21g-project/) from any subdirectory
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]  # adjust depth as needed
SKILLS_DIR = WORKSPACE_ROOT / "skills"

# Load a skill
skill_text = (SKILLS_DIR / "referee_hint_generator.md").read_text()
```

Alternatively, set an environment variable:
```bash
export Q21G_SKILLS_DIR=/path/to/q21g-project/skills
```

## Tech Stack

- Python 3.11+
- pdfplumber: PDF text extraction
- chromadb: Vector store
- sentence-transformers: Embeddings (paraphrase-multilingual-MiniLM-L12-v2)
- anthropic: Claude API for LLM calls
- sqlite3: Fast lookups (built-in)
- UV package manager (user preference)

## Development Workflow

1. First: Build & validate knowledge_base (Phase 1)
2. Then: Implement referee callbacks in `Q21G-referee-whl/examples/my_ai.py` (Phase 2)
3. Then: Implement player callbacks in `Q21G-player-whl/my_player.py` (Phase 3)
4. Then: End-to-end simulation test (Phase 4)
5. Finally: Gmail integration test (Phase 5)

## Skills Architecture

Skills are LLM prompt templates in `skills/*.md`. Each callback reads its skill file, fills in context, and calls the Claude API.

### Skill → Callback Mapping

| Skill File | Role | Callback | LLM? |
|---|---|---|---|
| `warmup_solver.md` | Both | `get_warmup_question` / `get_warmup_answer` | No |
| `referee_hint_generator.md` | Referee | `get_round_start_info` | Yes |
| `referee_question_answerer.md` | Referee | `get_answers` | Yes |
| `referee_scorer.md` | Referee | `get_score_feedback` | Yes |
| `player_question_generator.md` | Player | `get_questions` | Yes |
| `player_guess_maker.md` | Player | `get_guess` | Yes |

### How Skills Are Used in Code

```python
# Example: referee answering questions
class MyRefereeAI(RefereeAI):
    def get_answers(self, ctx):
        # 1. Read the skill file
        skill = (SKILLS_DIR / "referee_question_answerer.md").read_text()
        
        # 2. Get context from SDK + our stored state
        questions = ctx["dynamic"]["questions"]
        paragraph = self._paragraph_text  # stored in callback 2
        
        # 3. Call LLM with skill prompt + context
        response = anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            messages=[{"role": "user", "content": f"{skill}\n\nParagraph: {paragraph}\n\nQuestions: {questions}"}]
        )
        
        # 4. Parse and return SDK-expected format
        return {"answers": parse_answers(response)}
```

## Critical Design Decisions

### 1. Referee Stores Secrets on self
The SDK does NOT pass the actual opening sentence or association word to callback 4. The referee MUST store them in callback 2:
```python
def get_round_start_info(self, ctx):
    paragraph = self._select_paragraph()
    self._opening_sentence = paragraph["opening_sentence"]   # for scoring later
    self._association_word = chosen_word                       # for scoring later
    self._paragraph_text = paragraph["text"]                  # for answering questions
    return {"book_name": ..., "book_hint": ..., "association_word": domain}
```

### 2. Player Stores Candidates on self
The player stores search results from callback 2 for use in callback 3:
```python
def get_questions(self, ctx):
    self._candidates = semantic_search(ctx["dynamic"]["book_hint"])
    return {"questions": generate_from_candidates(self._candidates)}

def get_guess(self, ctx):
    best = rerank(self._candidates, ctx["dynamic"]["answers"])
    return {"opening_sentence": best["opening_sentence"], ...}
```

### 3. Taboo Word Rule
The referee's hint (book_hint) MUST NOT contain ANY word from the paragraph text. Validate with set intersection, retry up to 3x if overlap found.

### 4. Scoring Formula
Each component scored 0-100, then weighted:
- `private_score = 0.50×sentence + 0.20×justification + 0.20×word + 0.10×word_justification`
- League points: 85-100→3, 70-84→2, 50-69→1, 0-49→0

### 5. SDK ctx Access Pattern
Always: `ctx["dynamic"]["field_name"]`

See `VERIFICATION_REPORT.md` for complete ctx fields per callback.

### 6. Timing Constraints — Hard Deadlines
The SDK enforces callback deadlines. **Exceeding = failure = 0 points.**

| Referee Callback | Deadline |
|---|---|
| `get_warmup_question` | 30s |
| `get_round_start_info` | 60s |
| `get_answers` | **120s — MUST batch all 20 Qs in ONE LLM call** |
| `get_score_feedback` | 180s |

Player protocol timeouts: warmup 300s, questions 600s, guess 300s.

**Rules**: Never make per-question LLM calls. Max 3 Taboo Word retries. Use Sonnet (not Opus) for speed. Pre-compute difficulty index offline. See `STRATEGY.md` for full timing budget.

## Important Notes

- See `STRATEGY.md` for full game theory analysis and tactical decisions
- Our referee NEVER judges our player — the League Manager mixes groups into triples each round
- The knowledge base uses Hebrew course PDFs, NOT famous English books
- `book_name` in the SDK = PDF lecture title (e.g., "הרצאה 3 — למידת מכונה")
- `book_hint` = 15-word description of the paragraph content (no overlap with paragraph words)
- `association_word` returned to players = domain/topic only (e.g., "ביולוגיה")
- The actual secret word is stored on `self._association_word` for scoring
- The competitive edge: player's exact opening-sentence lookup from knowledge base → 85-95% private score
