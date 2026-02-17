# Configuration Guide

The config file must be at `js/config.json` in your project root.

---

## `app` - Your PlayerAI Implementation

```json
"app": {
  "player_ai_module": "my_player",
  "player_ai_class": "MyPlayerAI"
}
```

| Field | Description |
|-------|-------------|
| `player_ai_module` | Python module name (filename without `.py`). If your file is `my_player.py`, use `"my_player"`. Must be importable from the directory where you run `q21-player`. |
| `player_ai_class` | Class name inside that module. Must inherit from `PlayerAI`. |

**Example:** If you have `my_player.py` with `class MyPlayerAI(PlayerAI):`, use:
```json
"player_ai_module": "my_player",
"player_ai_class": "MyPlayerAI"
```

---

## `gmail` - Gmail API Credentials

```json
"gmail": {
  "account": "your-email@gmail.com",
  "credentials_path": "credentials.json",
  "token_path": "token.json"
}
```

| Field | Description |
|-------|-------------|
| `account` | Your Gmail address that will send/receive game messages. |
| `credentials_path` | Path to OAuth credentials file from Google Cloud Console. Can be absolute (`/Users/you/credentials.json`) or relative to where you run `q21-player`. |
| `token_path` | Path where the OAuth token will be saved after first login. Created automatically. Same path rules as above. |

**Setup:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable Gmail API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download JSON → Save as `credentials.json` in your project folder

---

## `database` - PostgreSQL Connection

```json
"database": {
  "host": "localhost",
  "port": 5432,
  "name": "q21_player",
  "user": "postgres",
  "password": "your-password"
}
```

| Field | Description |
|-------|-------------|
| `host` | Database server address. Use `localhost` for local PostgreSQL. |
| `port` | PostgreSQL port. Default is `5432`. |
| `name` | Database name. Create it first with `createdb q21_player`. |
| `user` | PostgreSQL username. |
| `password` | PostgreSQL password. |

**Setup:**
```bash
# Install PostgreSQL, then:
createdb q21_player
```

---

## `league` - Game League Settings

```json
"league": {
  "manager_email": "referee@example.com",
  "league_id": "LEAGUE001"
}
```

| Field | Description |
|-------|-------------|
| `manager_email` | Email address of the referee/game manager. You'll receive game messages from this address. **Get this from your instructor.** |
| `league_id` | League identifier. **Get this from your instructor.** |

---

## `player` - Your Player Identity

```json
"player": {
  "user_id": "student001",
  "display_name": "Student Name"
}
```

| Field | Description |
|-------|-------------|
| `user_id` | Unique identifier for your player. Use something unique like your student ID. **No spaces, alphanumeric only.** |
| `display_name` | Your name as shown in the game. Can include spaces. |

---

## Alternative: Environment Variables

You can also use a `.env` file instead of (or in addition to) `config.json`:

```bash
# .env
GMAIL_ACCOUNT=your-email@gmail.com
GMAIL_CREDENTIALS_PATH=./credentials.json
GMAIL_TOKEN_PATH=./token.json

GTAI_DB_HOST=localhost
GTAI_DB_PORT=5432
GTAI_DB_NAME=q21_player
GTAI_DB_USER=postgres
GTAI_DB_PASSWORD=your-password
```

Environment variables are loaded first, then `js/config.json` values override them.

---

## Complete Example

Your project structure:
```
q21-player-sdk/
├── .venv/
├── js/
│   └── config.json
├── credentials.json      # From Google Cloud Console
├── token.json            # Created automatically on first run
├── my_player.py          # Your PlayerAI implementation
└── .env                  # Optional
```
