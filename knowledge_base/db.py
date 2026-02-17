"""SQLite database for paragraph lookups.

Provides ParagraphDB class for fast queries over the corpus.
"""

import sqlite3
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = Path(__file__).parent / "data" / "paragraphs.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS paragraphs (
    id TEXT PRIMARY KEY,
    pdf_name TEXT NOT NULL,
    pdf_filename TEXT,
    paragraph_index INTEGER,
    opening_sentence TEXT NOT NULL,
    full_text TEXT NOT NULL,
    word_count INTEGER,
    is_valid INTEGER DEFAULT 1
)
"""


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


class ParagraphDB:
    """SQLite wrapper for the paragraphs corpus."""

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or DEFAULT_DB_PATH
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row

    def create_db(self, paragraphs: list[dict]) -> None:
        """Create table and insert all paragraph records."""
        self._conn.execute(_SCHEMA)
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pdf ON paragraphs(pdf_name)"
        )
        for p in paragraphs:
            self._conn.execute(
                "INSERT OR REPLACE INTO paragraphs VALUES (?,?,?,?,?,?,?,?)",
                (p["id"], p["pdf_name"], p.get("pdf_filename", ""),
                 p["paragraph_index"], p["opening_sentence"],
                 p["text"], p["word_count"],
                 1 if p.get("is_valid", True) else 0),
            )
        self._conn.commit()

    def get_by_id(self, paragraph_id: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM paragraphs WHERE id = ?", (paragraph_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None

    def get_by_pdf_name(self, pdf_name: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM paragraphs WHERE pdf_name = ?", (pdf_name,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def get_random(
        self, min_words: int = 50, max_words: int = 150,
        min_difficulty: float = 0.0, max_difficulty: float = 1.0,
    ) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM paragraphs "
            "WHERE word_count BETWEEN ? AND ? "
            "AND COALESCE(difficulty_score, 0.5) BETWEEN ? AND ? "
            "AND COALESCE(is_valid, 1) = 1 "
            "ORDER BY RANDOM() LIMIT 1",
            (min_words, max_words, min_difficulty, max_difficulty),
        ).fetchone()
        if not row:
            row = self._conn.execute(
                "SELECT * FROM paragraphs "
                "WHERE COALESCE(is_valid, 1) = 1 "
                "ORDER BY RANDOM() LIMIT 1"
            ).fetchone()
        return _row_to_dict(row) if row else None

    def search_text(self, query: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM paragraphs WHERE full_text LIKE ?",
            (f"%{query}%",),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def get_all_pdf_names(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT pdf_name FROM paragraphs ORDER BY pdf_name"
        ).fetchall()
        return [r["pdf_name"] for r in rows]

    def count(self) -> int:
        return self._conn.execute(
            "SELECT COUNT(*) FROM paragraphs"
        ).fetchone()[0]

    def close(self) -> None:
        self._conn.close()


def build_sqlite(paragraphs: list[dict], db_path: Path) -> None:
    """Build SQLite database from paragraphs list."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = ParagraphDB(db_path)
    db.create_db(paragraphs)
    db.close()
    print(f"SQLite DB saved to {db_path} ({len(paragraphs)} paragraphs)")
