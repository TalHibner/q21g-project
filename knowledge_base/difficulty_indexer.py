"""Pre-compute difficulty scores for each paragraph.

Components (from STRATEGY.md):
  0.3 * nearest_neighbor_similarity   — how confusable with other paragraphs
  0.3 * (1 - opening_sentence_uniqueness) — generic opener = harder
  0.2 * normalized_pdf_paragraph_count — more paragraphs in same PDF = harder
  0.2 * topic_commonality             — approximated by cross-PDF neighbor similarity

Target range for referee selection: 0.4–0.7 ("medium" difficulty).
"""

from pathlib import Path

from knowledge_base.db import ParagraphDB, DEFAULT_DB_PATH
from knowledge_base.vector_store import VectorStore


def _normalize(value: float, lo: float, hi: float) -> float:
    """Clamp and scale value to [0, 1]."""
    if hi <= lo:
        return 0.5
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def compute_difficulty_scores(
    db: ParagraphDB, vs: VectorStore
) -> dict[str, float]:
    """Return {paragraph_id: difficulty_score} for every paragraph."""
    # --- gather raw data ---
    pdf_names = db.get_all_pdf_names()
    pdf_counts: dict[str, int] = {}
    all_ids: list[str] = []

    for name in pdf_names:
        rows = db.get_by_pdf_name(name)
        pdf_counts[name] = len(rows)
        all_ids.extend(r["id"] for r in rows)

    max_pdf_count = max(pdf_counts.values()) if pdf_counts else 1

    col = vs._get_collection()

    # --- per-paragraph metrics via batched ChromaDB queries ---
    nn_sim: dict[str, float] = {}       # nearest-neighbor similarity
    sentence_sim: dict[str, float] = {}  # opening-sentence max similarity
    cross_pdf_sim: dict[str, float] = {} # topic commonality (cross-PDF)

    batch_size = 50
    for start in range(0, len(all_ids), batch_size):
        batch_ids = all_ids[start:start + batch_size]

        # Query paragraphs by their own text -> 6 neighbors (self + 5 others)
        batch_rows = [db.get_by_id(pid) for pid in batch_ids]
        texts = [r["full_text"] for r in batch_rows]
        sentences = [r["opening_sentence"] for r in batch_rows]

        # Full-text nearest neighbors
        text_results = col.query(
            query_texts=texts, n_results=6,
            include=["distances", "metadatas"],
        )
        # Opening-sentence nearest neighbors
        sent_results = col.query(
            query_texts=sentences, n_results=6,
            include=["distances", "metadatas"],
        )

        for i, pid in enumerate(batch_ids):
            row = batch_rows[i]
            pdf = row["pdf_name"]

            # Nearest-neighbor similarity (skip self, cosine distance -> similarity)
            dists = text_results["distances"][i]
            metas = text_results["metadatas"][i]
            non_self = [1.0 - d for d, m in zip(dists, metas)
                        if m.get("pdf_name") != "__skip__" and d > 0.001]
            nn_sim[pid] = non_self[0] if non_self else 0.5

            # Cross-PDF similarity (neighbors from OTHER PDFs)
            cross = [1.0 - d for d, m in zip(dists, metas)
                     if m.get("pdf_name", pdf) != pdf]
            cross_pdf_sim[pid] = cross[0] if cross else 0.0

            # Opening sentence similarity (skip self)
            s_dists = sent_results["distances"][i]
            non_self_s = [1.0 - d for d in s_dists if d > 0.001]
            sentence_sim[pid] = non_self_s[0] if non_self_s else 0.0

        pct = min(100, (start + batch_size) * 100 // len(all_ids))
        print(f"  difficulty indexing... {pct}%")

    # --- combine into final score ---
    scores: dict[str, float] = {}
    for pid in all_ids:
        row = db.get_by_id(pid)
        pdf = row["pdf_name"]

        neighbor_similarity = nn_sim.get(pid, 0.5)
        opening_uniqueness = 1.0 - sentence_sim.get(pid, 0.5)
        pdf_count_norm = _normalize(pdf_counts[pdf], 1, max_pdf_count)
        topic_common = cross_pdf_sim.get(pid, 0.0)

        score = (
            0.3 * neighbor_similarity
            + 0.3 * (1.0 - opening_uniqueness)
            + 0.2 * pdf_count_norm
            + 0.2 * topic_common
        )
        scores[pid] = round(score, 4)

    return scores


def add_difficulty_column(db_path: Path = DEFAULT_DB_PATH) -> None:
    """Compute and store difficulty_score in the existing SQLite DB."""
    db = ParagraphDB(db_path)
    vs = VectorStore()

    # Add column if missing
    import sqlite3
    try:
        db._conn.execute(
            "ALTER TABLE paragraphs ADD COLUMN difficulty_score REAL"
        )
    except sqlite3.OperationalError:
        pass  # column already exists

    print(f"Computing difficulty for {db.count()} paragraphs...")
    scores = compute_difficulty_scores(db, vs)

    for pid, score in scores.items():
        db._conn.execute(
            "UPDATE paragraphs SET difficulty_score = ? WHERE id = ?",
            (score, pid),
        )
    db._conn.commit()

    # Report distribution
    vals = list(scores.values())
    medium = [v for v in vals if 0.4 <= v <= 0.7]
    print(f"Done. range=[{min(vals):.3f}, {max(vals):.3f}], "
          f"mean={sum(vals)/len(vals):.3f}, "
          f"medium-zone={len(medium)}/{len(vals)}")
    db.close()


if __name__ == "__main__":
    add_difficulty_column()
