# Q21G Implementation Tasks

## Repo Structure

Single monorepo. SDK repos are subdirectories, pip-installed in editable mode.
Skills live at workspace root `skills/`. Knowledge base is a pip-installable package.

```
q21g-project/                            # Claude Code workspace root
├── CLAUDE.md, DESIGN.md, TASKS.md, VERIFICATION_REPORT.md
│
├── skills/                              # All 6 LLM skill prompts
│   ├── warmup_solver.md
│   ├── referee_hint_generator.md
│   ├── referee_question_answerer.md
│   ├── referee_scorer.md
│   ├── player_question_generator.md
│   └── player_guess_maker.md
│
├── knowledge_base/                      # Shared RAG (pip install -e)
│   ├── __init__.py
│   ├── setup.py
│   ├── corpus_builder.py
│   ├── db.py
│   ├── vector_store.py
│   ├── sentence_extractor.py
│   └── data/                            # paragraphs.db, chroma_db/ (gitignored)
│
├── course_pdfs/                         # 22 Hebrew PDFs (gitignored)
│
├── tests/
│
├── Q21G-referee-whl/                    # Referee SDK (don't modify src/)
│   ├── examples/my_ai.py               # ← OUR code
│   ├── examples/main.py                # ← Production entry point
│   └── src/q21_referee/                 # SDK internals
│
└── Q21G-player-whl/                     # Player SDK (don't modify _infra/)
    ├── my_player.py                     # ← OUR code
    ├── run.py                           # ← Production entry point
    └── _infra/                          # SDK internals
```

---

## Phase 0: Project Setup

- [ ] 0.1 Create `q21g-project/` repo, `git init`
- [ ] 0.2 Move/copy `Q21G-referee-whl/` and `Q21G-player-whl/` into the repo as subdirectories
- [ ] 0.3 Place handoff docs at root: `CLAUDE.md`, `DESIGN.md`, `TASKS.md`, `VERIFICATION_REPORT.md`
- [ ] 0.4 Place all 6 skill files in `skills/`
- [ ] 0.5 Place 22 Hebrew PDFs in `course_pdfs/`
- [ ] 0.6 Create directories: `knowledge_base/`, `knowledge_base/data/`, `tests/`
- [ ] 0.7 Create `knowledge_base/setup.py` so it's pip-installable:
  ```python
  from setuptools import setup, find_packages
  setup(name="knowledge_base", version="0.1", packages=find_packages())
  ```
- [ ] 0.8 Install everything:
  ```bash
  pip install -e Q21G-referee-whl/
  pip install -e Q21G-player-whl/
  pip install -e knowledge_base/
  pip install pdfplumber chromadb sentence-transformers anthropic
  ```
- [ ] 0.9 Verify imports:
  ```bash
  python -c "from q21_referee import RefereeAI; print('referee OK')"
  python -c "from q21_player import PlayerAI; print('player OK')"
  ```

---

## Phase 1: Knowledge Base — Corpus Builder (PRIORITY)

Work in: `knowledge_base/`

- [ ] 1.1 Implement `sentence_extractor.py` — Hebrew first-sentence extraction
  - Handle: period/question/exclamation followed by space
  - Skip: abbreviations (Dr., e.g.), decimals (3.14), English abbreviations
- [ ] 1.2 Implement `corpus_builder.py` — PDF → paragraphs extraction pipeline
  - Input: `course_pdfs/*.pdf`
  - Split on double newlines, filter (min 15 words, skip TOC/headers/tables)
  - Extract first sentence per paragraph
  - Output: `data/paragraphs.json`
- [ ] 1.3 Run on 1 PDF first, inspect output quality
- [ ] 1.4 Tune paragraph splitting rules for Hebrew academic text
- [ ] 1.5 Run on all 22 PDFs → generate `data/paragraphs.json`
- [ ] 1.6 Implement `db.py` — SQLite helper
  - create_db(), get_by_id(), get_by_pdf_name(), get_random(), search_text()
- [ ] 1.7 Build `data/paragraphs.db` from paragraphs.json
- [ ] 1.8 Implement `vector_store.py` — ChromaDB helper
  - create_collection(), search(), search_by_pdf()
  - Embedding model: `paraphrase-multilingual-MiniLM-L12-v2`
- [ ] 1.9 Build `data/chroma_db/` index
- [ ] 1.10 Validate: spot-check 10 paragraphs — correct opening sentences?
- [ ] 1.11 Validate: semantic search with Hebrew paraphrase → correct paragraph?
- [ ] 1.12 Pre-compute difficulty index for each paragraph:
  - Nearest-neighbor similarity (confusability with other paragraphs)
  - Opening sentence uniqueness (how distinctive vs all other sentences)
  - Paragraph count in same PDF (more = harder to narrow)
  - Store as `difficulty_score` column in SQLite (target range: 0.4-0.7 for referee)
- [ ] 1.13 Write `tests/test_knowledge_base.py`

---

## Phase 2: Referee Implementation

Work in: `Q21G-referee-whl/examples/my_ai.py`
Skills loaded from: `skills/` (workspace root)

- [ ] 2.1 Implement `__init__()`:
  - Load knowledge base: `from knowledge_base.db import ParagraphDB`
  - Resolve skills dir: `SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"`
- [ ] 2.2 Implement callback 1: `get_warmup_question(ctx)`
  - Read `skills/warmup_solver.md` for approach
  - Generate random math question
  - Return: `{"warmup_question": "What is 7 * 8?"}`
- [ ] 2.3 Implement helper: `_select_paragraph()` — random PDF → random paragraph
  - Filter: 50-150 words, content-rich, not lists/formulas
  - Vary across rounds
- [ ] 2.4 Implement helper: `_generate_hint()` — LLM with `skills/referee_hint_generator.md`
  - Generate 15-word hint with Taboo Word Rule validation
  - Retry up to 3x if word overlap detected
- [ ] 2.5 Implement callback 2: `get_round_start_info(ctx)`
  - Select paragraph, generate hint, choose association word + domain
  - **Store on self**: `self._paragraph_text`, `self._opening_sentence`, `self._association_word`
  - Return: `{"book_name": str, "book_hint": str, "association_word": str}`
- [ ] 2.6 Implement callback 3: `get_answers(ctx)`
  - LLM with `skills/referee_question_answerer.md` + `self._paragraph_text`
  - Read each question's options, choose A/B/C/D or "Not Relevant"
  - Return: `{"answers": [{"question_number": int, "answer": str}]}`
- [ ] 2.7 Implement callback 4: `get_score_feedback(ctx)`
  - LLM with `skills/referee_scorer.md`
  - Compare player guess vs `self._opening_sentence` and `self._association_word`
  - Calculate 4 component scores (0-100 each), weighted sum
  - League points: 85→3, 70→2, 50→1, <50→0
  - Return: `{"league_points", "private_score", "breakdown", "feedback"}`
- [ ] 2.8 Test with SDK's `examples/test_local.py` — full 4-callback flow
- [ ] 2.9 Test: generate 20 hints, verify zero word overlap with paragraphs
- [ ] 2.10 Write `tests/test_referee.py`

---

## Phase 3: Player Implementation

Work in: `Q21G-player-whl/my_player.py`
Skills loaded from: `skills/` (workspace root)

- [ ] 3.1 Implement `__init__()`:
  - Load knowledge base: `from knowledge_base.db import ParagraphDB`
  - Resolve skills dir: `SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"`
- [ ] 3.2 Implement callback 1: `get_warmup_answer(ctx)`
  - Parse math question from `ctx["dynamic"]["warmup_question"]`
  - Return: `{"answer": "56"}`
- [ ] 3.3 Implement callback 2: `get_questions(ctx)`
  - Filter ChromaDB by `book_name` → narrow to that lecture
  - Semantic search with `book_hint` → top 5-10 candidates
  - **Store on self**: `self._candidates`
  - LLM with `skills/player_question_generator.md`: generate 20 discriminating questions
  - Return: `{"questions": [{"question_number", "question_text", "options"}]}`
- [ ] 3.4 Implement callback 3: `get_guess(ctx)`
  - Retrieve `self._candidates` and answers from `ctx["dynamic"]["answers"]`
  - LLM with `skills/player_guess_maker.md`: re-rank candidates using Q&A
  - Look up EXACT opening sentence from SQLite for best candidate
  - Return: `{"opening_sentence", "sentence_justification", "associative_word", "word_justification", "confidence"}`
- [ ] 3.5 Implement callback 4: `on_score_received(ctx)` — log results
- [ ] 3.6 Write `tests/test_player.py`

---

## Phase 4: End-to-End Simulation

- [ ] 4.1 Write `tests/test_game_simulation.py` — chains: referee callback 2 → player callback 2 → referee callback 3 → player callback 3 → referee callback 4
- [ ] 4.2 Run 10 simulated games, measure:
  - Paragraph identification accuracy
  - Average private score
  - Average league points
- [ ] 4.3 Tune: number of candidates, question strategy, re-ranking prompt
- [ ] 4.4 Edge case: what if semantic search returns wrong candidates?

---

## Phase 5: Integration & Gmail — Production Deployment

### Gmail Setup
- [ ] 5.1 Configure Gmail OAuth for referee email (`groupname.referee@gmail.com`)
- [ ] 5.2 Configure Gmail OAuth for player email (`groupname.player@gmail.com`)

### Referee Production Setup
- [ ] 5.3 Update `Q21G-referee-whl/examples/main.py` to import our AI:
  ```python
  import sys
  from pathlib import Path
  # Ensure workspace root is on path for knowledge_base imports
  sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
  
  from q21_referee import RefereeRunner
  from my_ai import MyRefereeAI
  
  config = { ... }  # Gmail credentials, league config
  runner = RefereeRunner(config=config, ai=MyRefereeAI())
  runner.run()
  ```
- [ ] 5.4 Test: `cd Q21G-referee-whl/examples && python main.py`

### Player Production Setup
- [ ] 5.5 Verify `Q21G-player-whl/config.json` has:
  ```json
  {"app": {"player_ai_module": "my_player", "player_ai_class": "MyPlayerAI"}}
  ```
- [ ] 5.6 Test: `cd Q21G-player-whl && python run.py --watch`

### Game Night — Two Terminals

```bash
# Terminal 1 — Referee
cd q21g-project/Q21G-referee-whl/examples
python main.py

# Terminal 2 — Player
cd q21g-project/Q21G-player-whl
python run.py --watch
```

Both agents poll Gmail automatically. No manual intervention needed.
Leave running from ~18:00 until the evening ends.

### Validation
- [ ] 5.7 Verify timeout compliance (warmup <5min, questions <10min, guess <5min)
- [ ] 5.8 Test against training server / warmup sessions
- [ ] 5.9 Add error handling for LLM failures (timeout, rate limit)
- [ ] 5.10 Final code review and cleanup
