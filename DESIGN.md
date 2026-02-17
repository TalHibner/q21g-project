# Q21G RAG Pipeline — Updated Design
## Hebrew Corpus + Claude Skills Architecture

---

## 1. Resolved Decisions

| Question | Answer | Impact |
|----------|--------|--------|
| PDF count | 22 files | Manageable corpus, ~200-2000 paragraphs total |
| PDF type | Text-based with diagrams | pdfplumber will work; skip OCR |
| Language | **Hebrew** | Needs multilingual embedding model |
| Paragraph definition | TBD — need to inspect actual PDFs | Will define after first extraction attempt |
| Association word | Per PDF: player gets **domain** only, not the word | SDK field `association_word` carries domain to player |
| Repeated paragraphs | Follow PDF rules (no explicit prohibition found) | Referee can reuse |
| LLM approach | **Claude Skills** (Claude Code CLI) | Each callback = a Skill; no subagents needed |

---

## 2. Hebrew Embedding Model Selection

For ChromaDB semantic search over Hebrew academic text, we need a multilingual embedding model. Here are the options ranked:

### Recommended: `paraphrase-multilingual-MiniLM-L12-v2`
- **384 dimensions**, 118M params
- Trained on 50+ languages **including Hebrew**
- Fast, good quality for semantic similarity
- Native ChromaDB support via `SentenceTransformerEmbeddingFunction`
- Proven in production RAG systems with Hebrew

### Alternative options:
| Model | Dims | Hebrew Quality | Speed | Notes |
|-------|------|---------------|-------|-------|
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | ★★★★ | Fast | **Best balance** |
| `paraphrase-multilingual-mpnet-base-v2` | 768 | ★★★★★ | Medium | Higher quality, 2x slower |
| `intfloat/multilingual-e5-large` | 1024 | ★★★★★ | Slow | Best quality, heavy |
| `imvladikon/sentence-transformers-alephbert` | 768 | ★★★★★ | Medium | Hebrew-specific, best for Hebrew-only |
| `all-MiniLM-L6-v2` (default) | 384 | ★★ | Fastest | English-centric, poor Hebrew |

### Decision: **`paraphrase-multilingual-MiniLM-L12-v2`**
Rationale: Good Hebrew support, fast enough for real-time game callbacks, small model size for easy deployment. If accuracy is insufficient after testing, upgrade to `multilingual-mpnet-base-v2` or the Hebrew-specific AlephBERT model.

**Important**: The course material likely mixes Hebrew text with English technical terms (LLM, transformer, attention, etc.). The multilingual models handle this code-switching well.

---

## 3. Corpus Processing Pipeline

### 3.1 Extraction Script: `corpus_builder.py`

```python
"""
Extract paragraphs from 22 Hebrew course PDFs.

Input: course_pdfs/ directory with 22 PDF files
Output: 
  - knowledge_base/paragraphs.json (master index)
  - knowledge_base/paragraphs.db (SQLite)
  - knowledge_base/chroma_db/ (vector store)
"""

import pdfplumber
import json
import sqlite3
import re
from pathlib import Path

def extract_text_from_pdf(pdf_path: Path) -> list[dict]:
    """Extract pages from a single PDF."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                pages.append({
                    "page_number": i + 1,
                    "text": text.strip()
                })
    return pages


def split_into_paragraphs(full_text: str) -> list[str]:
    """Split Hebrew text into paragraphs.
    
    Strategy: Split on double newlines, then filter.
    Hebrew text flows RTL but paragraph breaks are universal.
    """
    # Split on 2+ newlines (paragraph boundaries)
    raw_paragraphs = re.split(r'\n\s*\n', full_text)
    
    # Filter out non-content paragraphs
    paragraphs = []
    for p in raw_paragraphs:
        p = p.strip()
        # Skip very short fragments (headers, page numbers, captions)
        if len(p.split()) < 15:
            continue
        # Skip table-of-contents style lines
        if re.match(r'^[\d.]+\s', p) and len(p.split()) < 10:
            continue
        # Skip lines that are mostly numbers/symbols (likely tables/formulas)
        alpha_ratio = sum(1 for c in p if c.isalpha()) / max(len(p), 1)
        if alpha_ratio < 0.4:
            continue
        paragraphs.append(p)
    
    return paragraphs


def extract_first_sentence_hebrew(text: str) -> str:
    """Extract first sentence from Hebrew paragraph.
    
    Hebrew sentence endings: period (.), question mark (?), exclamation (!).
    Must handle:
    - English abbreviations mixed in (e.g., Dr., i.e., etc.)
    - Decimal numbers (3.14)
    - URLs and technical notation
    - Hebrew doesn't use capitalization, so can't use capital-after-period heuristic
    """
    # Strategy: Find first sentence-ending punctuation that looks like a real sentence end
    # For Hebrew: a period followed by a space (and the space is followed by more text)
    
    # Common abbreviations to skip (English ones that appear in Hebrew academic text)
    abbrev_pattern = r'(?:Dr|Mr|Mrs|Prof|e\.g|i\.e|etc|vs|al|Fig|Eq|Sec|Ch|No|Vol)\.'
    
    # Try to find sentence boundary
    # Look for: period/question/exclamation followed by space
    # But not after abbreviations or digits (decimals)
    
    sentences = []
    current = ""
    i = 0
    while i < len(text):
        current += text[i]
        if text[i] in '.!?' and i + 1 < len(text):
            # Check it's not an abbreviation
            is_abbrev = bool(re.search(abbrev_pattern + '$', current))
            # Check it's not a decimal number (digit before and after period)
            is_decimal = (i > 0 and text[i-1].isdigit() and 
                         i + 1 < len(text) and text[i+1].isdigit())
            # Check it's not part of ellipsis
            is_ellipsis = (i + 1 < len(text) and text[i+1] == '.')
            
            if not is_abbrev and not is_decimal and not is_ellipsis:
                # Check if followed by space (end of sentence)
                if i + 1 < len(text) and text[i+1] in ' \n\t':
                    return current.strip()
        i += 1
    
    # If no clear sentence boundary, return the whole text
    return text.strip()


def build_corpus(pdf_dir: Path, output_dir: Path):
    """Main pipeline: PDFs → paragraphs.json + SQLite + ChromaDB."""
    
    output_dir.mkdir(parents=True, exist_ok=True)
    all_paragraphs = []
    
    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDFs")
    
    for pdf_path in pdf_files:
        print(f"Processing: {pdf_path.name}")
        pages = extract_text_from_pdf(pdf_path)
        
        # Join all pages into one text
        full_text = "\n\n".join(p["text"] for p in pages)
        
        # Split into paragraphs
        paragraphs = split_into_paragraphs(full_text)
        print(f"  → {len(paragraphs)} paragraphs")
        
        for i, para_text in enumerate(paragraphs):
            record = {
                "id": f"{pdf_path.stem}_p{i:04d}",
                "pdf_name": pdf_path.stem,
                "pdf_filename": pdf_path.name,
                "paragraph_index": i,
                "text": para_text,
                "opening_sentence": extract_first_sentence_hebrew(para_text),
                "word_count": len(para_text.split()),
            }
            all_paragraphs.append(record)
    
    # Save JSON
    json_path = output_dir / "paragraphs.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "paragraphs": all_paragraphs,
            "metadata": {
                "total_paragraphs": len(all_paragraphs),
                "total_pdfs": len(pdf_files),
                "pdf_names": [p.stem for p in pdf_files],
            }
        }, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(all_paragraphs)} paragraphs to {json_path}")
    
    # Build SQLite
    build_sqlite(all_paragraphs, output_dir / "paragraphs.db")
    
    # Build ChromaDB
    build_chroma(all_paragraphs, output_dir / "chroma_db")


def build_sqlite(paragraphs: list, db_path: Path):
    """Build SQLite database for fast lookups."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS paragraphs (
            id TEXT PRIMARY KEY,
            pdf_name TEXT NOT NULL,
            pdf_filename TEXT,
            paragraph_index INTEGER,
            opening_sentence TEXT NOT NULL,
            full_text TEXT NOT NULL,
            word_count INTEGER
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pdf_name ON paragraphs(pdf_name)")
    
    for p in paragraphs:
        conn.execute(
            "INSERT OR REPLACE INTO paragraphs VALUES (?, ?, ?, ?, ?, ?, ?)",
            (p["id"], p["pdf_name"], p["pdf_filename"], 
             p["paragraph_index"], p["opening_sentence"], 
             p["text"], p["word_count"])
        )
    conn.commit()
    conn.close()
    print(f"SQLite DB saved to {db_path}")


def build_chroma(paragraphs: list, chroma_path: Path):
    """Build ChromaDB vector store with Hebrew-optimized embeddings."""
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    
    ef = SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )
    
    client = chromadb.PersistentClient(path=str(chroma_path))
    
    # Delete existing collection if rebuilding
    try:
        client.delete_collection("course_paragraphs")
    except:
        pass
    
    collection = client.create_collection(
        name="course_paragraphs",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"}
    )
    
    # Add in batches (ChromaDB recommends batches of ~5000)
    batch_size = 100
    for i in range(0, len(paragraphs), batch_size):
        batch = paragraphs[i:i+batch_size]
        collection.add(
            ids=[p["id"] for p in batch],
            documents=[p["text"] for p in batch],
            metadatas=[{
                "pdf_name": p["pdf_name"],
                "opening_sentence": p["opening_sentence"],
                "paragraph_index": p["paragraph_index"],
                "word_count": p["word_count"],
            } for p in batch]
        )
    
    print(f"ChromaDB built at {chroma_path} with {len(paragraphs)} vectors")
```

### 3.2 Running the Pipeline

```bash
# Install dependencies
pip install pdfplumber chromadb sentence-transformers

# Directory structure
course_pdfs/           # ← Put all 22 PDFs here
knowledge_base/        # ← Auto-generated output
├── paragraphs.json
├── paragraphs.db
└── chroma_db/

# Run
python corpus_builder.py
```

---

## 4. Claude Skills Architecture

Since we're using Claude Skills (Claude Code CLI), each callback is a separate skill invocation. The key insight: **Skills are stateless per invocation**, so we need a persistence layer between callbacks.

### 4.1 State Management Between Callbacks

The referee needs to remember the chosen paragraph across callbacks 2→3→4. Options:

| Approach | Pros | Cons |
|----------|------|------|
| **Instance variable on class** | Simple, SDK already supports it | Works only if same object across callbacks ✓ |
| JSON file per game | Survives crashes | File I/O overhead |
| SQLite game_state table | Query-friendly | Overkill for single game |

**Decision**: Use **instance variables** (same as DemoAI does with `self._actual_opening_sentence`). The SDK instantiates one AI object and calls all 4 callbacks on it sequentially within the same process.

### 4.2 Skill Mapping

```
REFEREE SKILLS:
┌─────────────────────────────────────────────────────────┐
│ Skill: warmup-generator                                 │
│ Input:  ctx (round info, player list)                   │
│ Action: Generate simple math question                   │
│ Output: {"warmup_question": "What is 7 * 8?"}          │
│ LLM:    Optional (can use random math)                  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Skill: paragraph-selector                               │
│ Input:  ctx (round info, warmup answers)                │
│ Action: 1. Pick random PDF from corpus                  │
│         2. Pick random paragraph (50-150 words)         │
│         3. Extract & store opening sentence             │
│         4. LLM→ generate 15-word hint (NO word overlap!)│
│         5. LLM→ choose association word + domain        │
│ State:  Store paragraph_text, opening_sentence,         │
│         association_word on self                         │
│ Output: {"book_name": ..., "book_hint": ...,            │
│          "association_word": domain}                     │
│ LLM:    YES — hint generation, association word         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Skill: question-answerer                                │
│ Input:  ctx (20 questions + stored paragraph)           │
│ Action: RAG — answer each question from paragraph       │
│         perspective, optionally with broader PDF context │
│ Output: {"answers": [{q_num, answer}, ...]}             │
│ LLM:    YES — one prompt with all 20 questions          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Skill: guess-scorer                                     │
│ Input:  ctx (player guess + stored actuals)             │
│ Action: 1. Compare guessed vs actual opening sentence   │
│         2. Compare guessed vs actual association word    │
│         3. Evaluate justification quality               │
│         4. Calculate weighted score                     │
│         5. Generate 150-200 word feedback               │
│ Output: {league_points, private_score, breakdown,       │
│          feedback}                                       │
│ LLM:    YES — scoring + feedback generation             │
└─────────────────────────────────────────────────────────┘

PLAYER SKILLS:
┌─────────────────────────────────────────────────────────┐
│ Skill: warmup-solver                                    │
│ Input:  ctx with math question                          │
│ Action: Parse & compute (e.g., "What is 7 * 8?" → 56)  │
│ Output: {"answer": "56"}                                │
│ LLM:    Optional (can use eval() or simple parser)      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Skill: question-strategist                              │
│ Input:  ctx (book_name, book_hint, association_domain)  │
│ Action: 1. Filter ChromaDB by pdf_name                  │
│         2. Semantic search with hint → top-K candidates │
│         3. LLM→ generate 20 discriminating questions    │
│ State:  Store candidate paragraphs on self              │
│ Output: {"questions": [...20 questions...]}             │
│ LLM:    YES — question generation                       │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Skill: guess-deducer                                    │
│ Input:  ctx (20 answers + book info + stored candidates)│
│ Action: 1. Use answers to re-rank candidates            │
│         2. Pick best matching paragraph                 │
│         3. Retrieve EXACT opening sentence from SQLite  │
│         4. LLM→ guess association word from content     │
│         5. LLM→ generate justifications                 │
│ Output: {opening_sentence, sentence_justification,      │
│          associative_word, word_justification,           │
│          confidence}                                     │
│ LLM:    YES — re-ranking, word guess, justifications    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Skill: score-logger                                     │
│ Input:  ctx (score, breakdown)                          │
│ Action: Log results, optionally update learning stats   │
│ Output: None                                            │
│ LLM:    No                                              │
└─────────────────────────────────────────────────────────┘
```

---

## 5. The "No Word Overlap" Hint Challenge

The PDF (page 39) requires the hint to contain **NO words from the paragraph**. This is the hardest constraint for the referee's hint generation. Here's the detailed approach:

```python
def generate_hint_no_overlap(paragraph_text: str, llm_client) -> str:
    """Generate a 15-word hint with ZERO word overlap with the paragraph.
    
    This is iterative — we generate, check, and retry if needed.
    """
    # Extract all unique words from paragraph (normalized)
    paragraph_words = set()
    for word in paragraph_text.split():
        # Normalize: remove punctuation, lowercase
        cleaned = re.sub(r'[^\w]', '', word).lower()
        if cleaned:
            paragraph_words.add(cleaned)
    
    # Also add English transliterations if present
    # (Hebrew academic text often has English terms)
    
    for attempt in range(3):
        prompt = f"""Generate a hint for the following paragraph.

RULES:
1. Maximum 15 words
2. The hint must describe the paragraph's topic/theme
3. CRITICAL: The hint must NOT contain ANY word that appears in the paragraph
4. Use synonyms, paraphrases, or related terms instead of direct words

PARAGRAPH:
{paragraph_text}

FORBIDDEN WORDS (do NOT use any of these):
{', '.join(sorted(paragraph_words)[:50])}  {"[...and more]" if len(paragraph_words) > 50 else ""}

Generate the hint (15 words max, NO forbidden words):"""
        
        hint = llm_client.generate(prompt).strip()
        
        # Validate: check for overlap
        hint_words = set()
        for word in hint.split():
            cleaned = re.sub(r'[^\w]', '', word).lower()
            if cleaned:
                hint_words.add(cleaned)
        
        overlap = hint_words & paragraph_words
        if not overlap:
            return hint
        
        # Retry with explicit overlap feedback
        print(f"  Hint attempt {attempt+1} had overlap: {overlap}, retrying...")
    
    # Last resort: very generic hint
    return "Academic content discussing theoretical concepts from course lecture material"
```

---

## 6. Player's Semantic Search Strategy

### 6.1 Two-Phase Search

```
Phase 1: FILTER by pdf_name (exact match)
  → Narrows from ~1500 paragraphs to ~70 paragraphs from that PDF

Phase 2: SEMANTIC SEARCH with hint against filtered set
  → The hint has NO words from the paragraph (by design!)
  → But it describes the same CONCEPT/THEME
  → Multilingual embeddings capture semantic similarity across paraphrases
  → Returns top 5-10 candidates ranked by cosine similarity
```

### 6.2 Why This Works Despite No Word Overlap

The hint says things like "neural network training optimization techniques" while the paragraph actually discusses "שיטות אופטימיזציה לאימון רשתות נוירונים".

The multilingual embedding model maps both the Hebrew paragraph and the English/Hebrew hint into the same semantic space. Even without lexical overlap, **semantic overlap** is captured by the embeddings.

### 6.3 Question Strategy Based on Candidates

Once we have 5-10 candidates, the 20 questions should **discriminate** between them:

```
Questions 1-5:   BROAD TOPIC (eliminate wrong sections of the lecture)
Questions 6-10:  SPECIFIC CONCEPTS (does the paragraph mention X? Y? Z?)
Questions 11-15: STRUCTURAL (length, contains code, contains formula, etc.)
Questions 16-18: OPENING SENTENCE CLUES (starts with a definition? example? question?)
Questions 19-20: ASSOCIATION WORD CLUES (connect to the domain hint)
```

---

## 7. File Structure

```
q21g-project/                            # Monorepo (Claude Code workspace root)
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
│   └── data/                            # Generated (gitignored)
│       ├── paragraphs.json
│       ├── paragraphs.db
│       └── chroma_db/
│
├── course_pdfs/                         # 22 PDF files (gitignored)
│
├── tests/
│
├── Q21G-referee-whl/                    # Referee SDK (subdirectory, don't modify src/)
│   ├── examples/my_ai.py               # ← OUR referee code
│   ├── examples/main.py                # ← Referee production entry point
│   └── src/q21_referee/                 # SDK internals
│
└── Q21G-player-whl/                     # Player SDK (subdirectory, don't modify _infra/)
    ├── my_player.py                     # ← OUR player code
    ├── run.py                           # ← Player production entry point
    └── _infra/                          # SDK internals
```

SDKs are pip-installed in editable mode: `pip install -e Q21G-referee-whl/ && pip install -e Q21G-player-whl/`
Knowledge base is also pip-installed: `pip install -e knowledge_base/`

---

## 8. Dependencies

```
# requirements.txt
pdfplumber>=0.10.0          # PDF text extraction (Hebrew text-based PDFs)
chromadb>=0.4.0             # Vector store for semantic search
sentence-transformers>=2.2  # Hebrew-compatible embeddings
anthropic>=0.30.0           # Claude API for LLM calls in Skills

# Already in SDK
# sqlite3 (built-in)
# json (built-in)
# re (built-in)
```

---

## 9. Next Steps

### Immediate (need PDFs uploaded):
1. **Upload the 22 PDFs** to this conversation
2. **Run extraction** → see actual paragraph structure
3. **Tune chunking** — Hebrew paragraph splitting may need adjustment
4. **Build knowledge base** → JSON + SQLite + ChromaDB
5. **Spot-check** 10 paragraphs for quality

### After knowledge base is built:
6. Implement referee in `Q21G-referee-whl/examples/my_ai.py` with all 4 callbacks
7. Implement player in `Q21G-player-whl/my_player.py` with all 4 callbacks  
8. Local simulation: referee ↔ player end-to-end test
9. Tune: embedding model, candidate count, question strategy
10. Deploy with Claude Skills configuration
