# Q21 Player SDK - Startup Context

## Project Overview

This is a **Python SDK template** for building an AI player that competes in a "21 Questions" guessing game about books.

### Purpose

Players must identify a book's opening sentence through strategic questioning:
1. Answer a warmup math question
2. Generate 20 yes/no questions about the book
3. Make a final guess of the opening sentence based on answers received
4. Receive scoring (0-100 league points)

### Repository

- **Origin:** https://github.com/OmryTzabbar1/q21-player-sdk.git
- **Branch:** main

---

## Tech Stack

| Technology | Purpose |
|------------|---------|
| Python 3.11 | Runtime with virtual environment |
| q21-player | Core SDK framework |
| Gmail API | Game communication with referees |
| PostgreSQL | Optional state persistence |
| Anthropic API | Optional LLM-based strategies |

### Dependencies

- `q21-player` - Main SDK package
- `google-api-python-client` (v2.189.0) - Gmail API integration
- `google-auth` (v2.48.0) - OAuth 2.0 authentication
- `anthropic` (v0.79.0) - Anthropic's LLM API client
- `python-dotenv` - Environment variable loading

---

## Directory Structure

```
q21-player-sdk/
├── .venv/                    # Python virtual environment
├── js/
│   └── config.json           # Configuration file
├── my_player.py              # Main player implementation (CUSTOMIZE THIS)
├── README.md                 # Quick start guide
├── CONFIG_GUIDE.md           # Detailed configuration documentation
├── credentials.json          # (User provides from Google Cloud)
└── token.json                # (Generated on first run - OAuth token)
```

---

## Key Files

| File | Purpose |
|------|---------|
| `my_player.py` | Main implementation - **customize this** |
| `js/config.json` | Configuration (Gmail, database, player identity) |
| `README.md` | Quick start guide |
| `CONFIG_GUIDE.md` | Detailed config documentation |

---

## Core Implementation

### `my_player.py` - MyPlayerAI Class

The `MyPlayerAI` class inherits from `PlayerAI` and has 4 methods to implement:

#### 1. `get_warmup_answer(ctx: dict) -> dict`
- **Purpose:** Solve a math warmup question
- **Input:** `ctx["dynamic"]["warmup_question"]` - math question string
- **Output:** `{"answer": "numeric_answer"}`
- **Current state:** Placeholder returning "0"

#### 2. `get_questions(ctx: dict) -> dict`
- **Purpose:** Generate 20 strategic yes/no questions
- **Input:** Book name, book hint, association word
- **Output:** List of exactly 20 questions with multiple choice options (A/B/C/D)
- **Current state:** Generic placeholder questions

#### 3. `get_guess(ctx: dict) -> dict`
- **Purpose:** Predict the book's opening sentence based on answers
- **Input:** All 20 answers (A/B/C/D), book info
- **Output:**
  - `opening_sentence` - The guessed opening sentence
  - `sentence_justification` - Detailed explanation (35+ words required)
  - `associative_word` - Thematic word related to the book
  - `word_justification` - Explanation of word choice (35+ words required)
  - `confidence` - 0.0 to 1.0 confidence score
- **Current state:** Placeholder text

#### 4. `on_score_received(ctx: dict) -> None`
- **Purpose:** Handle game completion and scoring
- **Input:** League points (0-100), match ID
- **Current state:** Prints score to console

---

## Configuration

### `js/config.json` Structure

```json
{
  "app": {
    "player_ai_module": "my_player",
    "player_ai_class": "MyPlayerAI"
  },
  "gmail": {
    "account": "your-email@gmail.com",
    "credentials_path": "credentials.json",
    "token_path": "token.json"
  },
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "q21_player",
    "user": "postgres",
    "password": "your-password"
  },
  "league": {
    "manager_email": "referee@example.com",
    "league_id": "LEAGUE001"
  },
  "player": {
    "user_id": "student001",
    "display_name": "Student Name"
  }
}
```

### Configuration Categories

- **app** - Python module/class for player implementation
- **gmail** - Gmail API credentials and OAuth token paths
- **database** - PostgreSQL connection details
- **league** - Game league settings and referee contact
- **player** - Player identity and display information

---

## CLI Commands

```bash
q21-player --scan              # Process messages once
q21-player --watch             # Continuous polling mode
q21-player --test-connectivity # Test Gmail/database setup
```

---

## Game Flow

1. User receives game message from referee (via Gmail)
2. System parses book information from message
3. Call `get_warmup_answer()` - answer math question
4. Call `get_questions()` - generate 20 strategic questions
5. Referee answers the 20 questions
6. Call `get_guess()` - predict opening sentence based on answers
7. Call `on_score_received()` - handle final scoring

---

## Setup Requirements

1. Python 3.11 virtual environment (`.venv/`)
2. `credentials.json` from Google Cloud Console (Gmail API OAuth)
3. Configure `js/config.json` with your details
4. Optional: PostgreSQL database for state persistence

### Files NOT to Commit

- `credentials.json` - OAuth credentials from Google Cloud
- `token.json` - Generated OAuth token
- `.env` - Environment variables with secrets

---

## Current Status

- Clean git repo on `main` branch
- Virtual environment set up in `.venv/`
- `my_player.py` contains placeholder implementations (TODOs to complete)
