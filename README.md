# Q21G — Competitive 21 Questions AI Game

Two AI agents play "21 Questions" over Gmail using Hebrew academic course PDFs as the knowledge base. A **Referee** picks a secret paragraph and gives hints; a **Player** asks 20 strategic questions then guesses the opening sentence.

## Architecture

```
                         Gmail (OAuth)
                      /                \
              Referee Agent           Player Agent
              (RLGMRunner)            (run.py --watch)
                   |                       |
            4 Callbacks               4 Callbacks
            (my_ai.py)               (my_player.py)
                   |                       |
          +--------+--------+     +--------+--------+
          |        |        |     |        |        |
       Hint Gen  Answer  Score  Search  Questions  Guess
          |      Questions  |     |                  |
          +--------+--------+     +--------+--------+
                   |                       |
            Claude Sonnet API        Claude Sonnet API
            (via llm_client.py)      (via llm_client.py)
                   |                       |
                   +----------+------------+
                              |
                      Knowledge Base (shared)
                     /        |         \
               SQLite    ChromaDB    Paragraph
             (lookups)  (semantic    Filter
                         search)
                              |
                   sentence-transformers
              (paraphrase-multilingual-MiniLM-L12-v2)
```

## Game Flow

```
Round Start
    |
    v
[Referee] select paragraph from KB --> generate hint (no taboo words) --> send to player
    |
    v
[Player] semantic search KB with hint --> find 20 candidates --> generate 20 questions
    |
    v
[Referee] answer 20 questions (A/B/C/D/Not Relevant) based on secret paragraph
    |
    v
[Player] re-rank candidates using Q&A evidence --> guess opening sentence + association word
    |
    v
[Referee] score guess (0-100 weighted) --> assign league points (3/2/1/0)
```

## Project Structure

```
q21g-project/
├── skills/                      # 6 LLM prompt templates
│   ├── referee_hint_generator.md
│   ├── referee_question_answerer.md
│   ├── referee_scorer.md
│   ├── player_question_generator.md
│   ├── player_guess_maker.md
│   └── warmup_solver.md
│
├── knowledge_base/              # Shared RAG infrastructure (pip install -e)
│   ├── corpus_builder.py        # PDF -> paragraphs.json
│   ├── sentence_extractor.py    # Hebrew first-sentence extraction
│   ├── paragraph_filter.py      # Quality filter (formulas, code, noise)
│   ├── db.py                    # SQLite (ParagraphDB)
│   ├── vector_store.py          # ChromaDB (VectorStore)
│   ├── difficulty_indexer.py    # Paragraph difficulty scoring
│   ├── llm_client.py           # Shared Claude API client with retry
│   └── data/                    # Built locally (gitignored)
│
├── Q21G-referee-whl/            # Referee SDK + our implementation
│   ├── src/q21_referee/         # SDK internals (don't modify)
│   ├── examples/
│   │   ├── my_ai.py            # <-- Our referee (4 callbacks)
│   │   ├── referee_helpers.py   # Hint gen, question answering
│   │   ├── referee_scoring.py   # Scoring with string pre-check
│   │   └── main.py             # Production entry point
│   └── config.json              # Gmail OAuth + group config
│
├── Q21G-player-whl/             # Player SDK + our implementation
│   ├── _infra/                  # SDK internals (don't modify)
│   ├── my_player.py            # <-- Our player (4 callbacks)
│   ├── player_helpers.py        # Search, question generation
│   ├── player_guess.py          # Re-ranking, guess with Q&A citations
│   ├── run.py                   # Production entry point
│   └── js/config.json           # Player config
│
├── tests/                       # 81 tests
│   ├── test_knowledge_base.py
│   ├── test_referee.py
│   ├── test_player.py
│   ├── test_game_simulation.py  # End-to-end referee <-> player
│   └── test_live_simulation.py
│
└── course_pdfs/                 # 22 Hebrew academic PDFs (gitignored)
```

## Setup

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager (recommended)
- Gmail OAuth credentials for both agents
- Anthropic API key

### Installation

```bash
git clone https://github.com/TalHibner/q21g-project.git
cd q21g-project

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install SDKs and knowledge base
pip install -e Q21G-referee-whl/
pip install -e Q21G-player-whl/
pip install -e knowledge_base/
pip install anthropic
```

### Environment Variables

Create `.env` in the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
HF_TOKEN=hf_...
```

### Build Knowledge Base

```bash
# 1. Place 22 Hebrew PDFs in course_pdfs/

# 2. Build the corpus
python -m knowledge_base.corpus_builder

# 3. Build SQLite + ChromaDB
python -c "
from knowledge_base.corpus_builder import build_corpus
from knowledge_base.db import build_sqlite
from knowledge_base.vector_store import build_chroma
from pathlib import Path
import json

data_dir = Path('knowledge_base/data')
with open(data_dir / 'paragraphs.json') as f:
    paras = json.load(f)['paragraphs']

build_sqlite(paras, data_dir / 'paragraphs.db')
build_chroma(paras, data_dir / 'chroma_db')
"

# 4. Compute difficulty scores
python -m knowledge_base.difficulty_indexer

# 5. Verify
python -c "
from knowledge_base.db import ParagraphDB
from knowledge_base.vector_store import VectorStore
db = ParagraphDB(); vs = VectorStore()
print(f'SQLite: {db.count()} paragraphs')
print(f'ChromaDB: {vs.count()} vectors')
"
```

### Gmail OAuth

Both agents need OAuth tokens. Follow the SDK setup guides:

```bash
# Referee
cd Q21G-referee-whl && python authenticate.py

# Player
cd Q21G-player-whl && python setup_gmail.py
```

## Running

### Referee (Production)

```bash
cd Q21G-referee-whl/examples
source ../../.venv/bin/activate
python main.py
```

Or with uv:

```bash
cd Q21G-referee-whl/examples
/home/hibta/.local/bin/uv run python main.py
```

### Player (Production)

```bash
cd Q21G-player-whl
source ../.venv/bin/activate
python run.py --watch
```

### Running Tests

```bash
source .venv/bin/activate
pytest tests/ -v              # All 81 tests
pytest tests/test_referee.py  # Referee only
pytest tests/test_player.py   # Player only
```

## Scoring

Each guess is scored on 4 components (0-100 each):

| Component | Weight | What's Measured |
|---|---|---|
| Opening sentence | 50% | Exact match of guessed vs actual opening sentence |
| Sentence justification | 20% | Quality of reasoning, must cite 3+ Q&A pairs |
| Association word | 20% | Match between guessed and actual association word |
| Word justification | 10% | Quality of reasoning, must cite 2+ Q&A pairs |

**Private score** = weighted sum (0-100)

**League points**: 85-100 = 3 pts, 70-84 = 2 pts, 50-69 = 1 pt, 0-49 = 0 pts

## Key Optimizations

- **Dual search**: PDF-filtered results get priority, unfiltered fill remaining slots
- **Hint self-test**: Referee verifies ChromaDB can find the paragraph using the generated hint
- **Taboo word validation**: Hint must not share any word with the paragraph text
- **Candidate shuffling**: Removes LLM position bias in guess-making
- **Sentence lookup**: Opening sentence is read from stored candidate data, never copied by LLM
- **String pre-check**: `SequenceMatcher` overrides LLM scoring for obvious matches (>=95% = 98 pts)
- **Paragraph filter**: Rejects formulas, code, noise — 1123 raw -> 340 valid paragraphs
- **LLM retry**: 2x retry with exponential backoff on timeout/rate-limit/connection errors

## Tech Stack

| Component | Technology |
|---|---|
| LLM | Claude Sonnet (claude-sonnet-4-20250514) |
| Embeddings | paraphrase-multilingual-MiniLM-L12-v2 |
| Vector Store | ChromaDB (cosine distance) |
| Database | SQLite3 |
| PDF Extraction | pdfplumber |
| Communication | Gmail API (OAuth) |
| Language | Python 3.11+ |
