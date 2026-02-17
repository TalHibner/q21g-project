# Q21G Winning Strategy Guide

## Game Structure Recap

Each round, the League Manager creates triples by **mixing groups**:
- Our **referee** judges 2 **other teams' players**
- Our **player** plays under **another team's referee**

Our referee never judges our player. Scoring is separate per role.

---

## REFEREE STRATEGY: Maximize Differentiation

**Goal**: Exactly one player wins, one loses → referee gets 2 points.
Both win or both lose (tie) → referee gets 0 points.

### 1. Paragraph Selection — "Goldilocks Difficulty"

**Don't pick:**
- ❌ Very famous/obvious paragraphs (both players find it → tie → 0 pts)
- ❌ Very obscure/short paragraphs (neither finds it → tie → 0 pts)
- ❌ Paragraphs with very generic opening sentences ("In this chapter we discuss...")
- ❌ Paragraphs with very unique/long opening sentences (too easy to identify)

**Do pick:**
- ✅ Medium-length paragraphs (60-120 words) — enough context for questions but not trivially identifiable
- ✅ Paragraphs with moderately distinctive opening sentences — recognizable if you know the material, but not trivially guessable
- ✅ Paragraphs from PDFs with MANY similar paragraphs — creates confusion between candidates
- ✅ Paragraphs where the opening sentence shares vocabulary with OTHER paragraphs in the same PDF

**Difficulty Scoring Heuristic — pre-compute for each paragraph:**
```python
difficulty_score = (
    0.3 * similarity_to_nearest_neighbor  # How similar is this to other paragraphs?
    + 0.3 * (1 - opening_sentence_uniqueness)  # How distinctive is the first sentence?
    + 0.2 * paragraph_count_in_same_pdf  # More paragraphs in PDF = harder
    + 0.2 * topic_commonality  # Common topic across PDFs = harder
)
# Target: difficulty_score in [0.4, 0.7] — the "medium" zone
```

### 2. Hint Quality — "Helpful But Ambiguous"

The hint should be:
- ✅ Accurate enough that a GOOD player can narrow down the PDF
- ✅ Vague enough that it matches 3-5 paragraphs, not just 1
- ✅ Uses **synonyms and paraphrases** (Taboo Word Rule already enforces this)
- ❌ Don't make the hint so specific it points to exactly one paragraph
- ❌ Don't make it so vague it's useless

**Hint calibration strategy:**
```
If paragraph is about "attention mechanisms in neural networks":
  TOO SPECIFIC: "Mathematical framework for query-key-value computations"  → points to 1 paragraph
  GOOD:         "Processing method that weighs input importance dynamically" → matches 3-5 paragraphs
  TOO VAGUE:    "A concept in computer science"  → matches 100+ paragraphs
```

**Hint self-test (CRITICAL)**: After generating the hint, verify it works by searching ChromaDB with it. If our own search can't find the paragraph in the top 5, no player will find it either → both fail → tie → 0 referee points. Regenerate until the hint passes the self-test. See `referee_hint_generator.md` step 9 for implementation.

### 3. Association Word — "Domain, Not Answer"

Return a broad domain (e.g., "biology", "mathematics") not a specific word.
The actual secret word stored on `self._association_word` should be:
- Moderately connected to the paragraph — not the first thing you'd guess, but logical after seeing it
- Something where the DOMAIN narrows it to ~5-10 possibilities

### 4. Question Answering — "Honest But Strategic"

You MUST answer truthfully (game integrity). But:
- For ambiguous questions where multiple answers are defensible, choose the answer that is **technically correct but less revealing**
- Use "Not Relevant" for questions that would too directly identify the paragraph
- Be consistent — don't contradict yourself across 20 questions

### 5. Scoring — "Fair But Firm"

As referee, you control the scoring. Strategy:
- Score HONESTLY — the League Manager may audit anomalous scores
- But use the FULL range: don't be overly generous to both players
- If both players score similarly → your differentiation failed → you get 0 pts
- A good paragraph choice makes differentiation natural

---

## PLAYER STRATEGY: Maximize Private Score

**Goal**: Achieve private_score ≥ 85 → 3 league points.
The 50% weight is on opening sentence accuracy → exact match is critical.

### 1. Question Strategy — "Narrowing Funnel"

With 20 questions and 4 options each, you have 20 × log2(4) = 40 bits of information theoretically.
But questions aren't perfectly discriminating, so practically ~15-20 bits.

**Phase structure for 20 questions:**

**Questions 1-5: PDF Identification (narrow from 22 PDFs to 1-2)**
- "Is this from a lecture about machine learning?"
- "Does this paragraph discuss a mathematical formula?"
- Use book_name and book_hint to guide PDF filtering

**Questions 6-12: Paragraph Cluster (narrow from ~100 paragraphs to 5-10)**
- "Does the paragraph discuss a specific algorithm?"
- "Is the opening sentence longer than 15 words?"
- "Does the paragraph contain a comparison between two approaches?"

**Questions 13-18: Paragraph Identification (narrow to 1-3)**
- Use candidates from ChromaDB semantic search
- Ask questions that DIFFERENTIATE between top candidates
- "Does the opening sentence mention [concept A]?" where concept A appears in candidate 1 but not candidate 2

**Questions 19-20: Confirmation**
- Verify your top candidate with targeted yes/no questions

### 2. Candidate Pre-filtering — "Smart Search"

Before generating questions:
```python
# Step 1: Filter by book_name → all paragraphs from that PDF
candidates = db.get_by_pdf_name(book_name)  # ~50-200 paragraphs

# Step 2: Semantic search with book_hint → top 10-20
ranked = chroma.search(book_hint, n=20, filter_pdf=book_name)

# Step 3: For each candidate, compute "match probability"
for c in ranked:
    c.probability = semantic_similarity(book_hint, c.text)
    # Also factor in: word count match, topic match, etc.
```

### 3. Question Design — "Information-Theoretic"

Each question should **maximally split** the candidate set:
```python
# GOOD question: splits candidates roughly 50/50
# If you have 8 candidates, ideal question eliminates ~4

# For each potential question, compute information gain:
for question in potential_questions:
    yes_count = count(candidates where answer would be "A" or "C")
    no_count = count(candidates where answer would be "B" or "D")
    # Closer to 50/50 = higher information gain
    info_gain = 1 - abs(yes_count - no_count) / len(candidates)
```

The LLM generates questions, but the SELECTION should prioritize questions that best discriminate between remaining candidates.

### 4. Answer Analysis — "Bayesian Update"

After receiving 20 answers, update candidate probabilities:
```python
for candidate in candidates:
    for q, answer in zip(questions, answers):
        # How likely is this answer IF this candidate is correct?
        likelihood = estimate_likelihood(candidate, q, answer)
        candidate.probability *= likelihood
    candidate.probability = normalize(candidate.probability)

best_candidate = max(candidates, key=lambda c: c.probability)
```

### 5. Guess — "Exact Lookup, Not Generation"

**CRITICAL**: Don't let the LLM GENERATE the opening sentence. LOOK IT UP from the database.
```python
# The competitive edge: exact string from our knowledge base
opening_sentence = db.get_by_id(best_candidate.id)["opening_sentence"]
```

This guarantees 100% accuracy on the sentence match if we identified the right paragraph.
LLM-generated sentences will always have small differences → lower score.

### 6. Association Word Guess — "Semantic Clustering"

The referee gives us a domain (e.g., "biology"). We need the specific word.
```python
# Strategy: Extract key concepts from the identified paragraph
# then pick the one most related to the domain
keywords = extract_keywords(best_candidate.text)
domain = ctx["dynamic"]["association_word"]
best_word = pick_most_related(keywords, domain)
```

---

## PRE-GAME PREPARATION: Difficulty Indexing

Build offline (during Phase 1), store in SQLite:

```python
for each paragraph:
    # 1. Nearest-neighbor similarity (how confusable with others?)
    neighbors = chroma.search(paragraph.text, n=5)
    avg_similarity = mean([n.similarity for n in neighbors])
    
    # 2. Opening sentence distinctiveness
    sentence_embedding = embed(paragraph.opening_sentence)
    all_sentence_embeddings = [embed(p.opening_sentence) for p in all_paragraphs]
    sentence_uniqueness = 1 - max_cosine_similarity(sentence_embedding, all_sentence_embeddings)
    
    # 3. Paragraph count in same PDF
    pdf_paragraph_count = count(paragraphs where pdf_name == paragraph.pdf_name)
    
    # Store: paragraph.difficulty_score, paragraph.confusability, etc.
```

This lets the referee quickly select "medium difficulty" paragraphs without runtime computation.

---

## EDGE CASES — Defensive Strategies

### Player: Bad input from opponent's referee

| Scenario | Detection | Fallback |
|---|---|---|
| Vague hint (matches 100+ paragraphs) | Top ChromaDB result has low similarity (<0.3) | Use `book_name` for PDF filtering first, ask broad topic questions |
| Misleading hint (wrong synonyms) | No candidate scores well after Q&A | Trust ChromaDB top-1 result, ignore Q&A |
| Unknown `book_name` | `db.get_by_pdf_name()` returns empty | Search all paragraphs, use hint only |
| Empty `book_hint` | String is empty or whitespace | Fall back to random paragraphs from the PDF identified by `book_name` |
| All answers "Not Relevant" | Count > 15 "Not Relevant" answers | Ignore Q&A, use pure ChromaDB ranking |
| Contradictory answers | Q&A consistency check fails | Weight later questions higher, or ignore Q&A |
| Correct paragraph not in top-20 | Can't detect (silent failure) | Questions 1-5 may reveal mismatch, triggering broader search |

**Golden rule**: Always return a valid guess. A bad guess scores 0-49 (0 league points). A crash/timeout scores 0 AND may give the opponent free points.

### Player: Graceful degradation tiers

```
Tier 1 (best):  ChromaDB match + Q&A confirmation → exact SQLite lookup → score 85-100
Tier 2 (good):  ChromaDB match, weak Q&A signal → trust top candidate → score 70-85
Tier 3 (okay):  No good match, but hint decodes → LLM reconstructs sentence → score 40-69
Tier 4 (worst): Everything fails → topically-correct guess from hint alone → score 20-40
```

### Referee: Bad input from opponent's players

| Scenario | Handling |
|---|---|
| Malformed questions (missing options, empty text) | Answer "Not Relevant" for empty; infer intent for malformed |
| Duplicate questions | Answer consistently (same question → same answer) |
| Questions not about the paragraph | Answer "Not Relevant" honestly |
| Player times out (no questions/guess received) | SDK handles this automatically — player gets 0 |

### Code-level defensive patterns

```python
# Always wrap LLM calls with timeout and fallback
try:
    response = anthropic.messages.create(..., timeout=50)
    result = parse_response(response)
except (TimeoutError, APIError) as e:
    logger.error(f"LLM call failed: {e}")
    result = fallback_result()  # pre-computed safe default

# Always validate ChromaDB results
candidates = chroma.search(query, n=20)
if not candidates or candidates[0].similarity < 0.1:
    candidates = db.get_random(pdf_name=book_name, n=10)  # fallback to random from PDF
```

### Lessons from Diagnostic (5-game simulation)

| Game | Root Cause | Fix |
|---|---|---|
| 1 | Player guessed EXACT correct sentence, LLM scored 25/100 | String pre-check in scorer: ≥95% char similarity → score 98, bypass LLM |
| 2 | Secret paragraph at rank 12, outside player top-10 | Better search: expand to top-20, combine hint + book_name filtering |
| 3 | Secret not in top-20, hint didn't match semantically | Paragraph quality filter: exclude garbage opening sentences |
| 4 | Secret at rank 5, player picked rank 4 (similar topic) | Question strategy: ask term-specific differentiating questions |
| 5 | Opening sentence was `}` (code fragment) | Paragraph quality filter: ≥8 words, must contain Hebrew, no code fragments |

**Primary fix**: 3 of 5 failures were caused by the referee selecting garbage paragraphs (code fragments, TOC entries, boilerplate). The paragraph quality filter (`is_valid_paragraph`) eliminates these entirely.

---

## TIMING CONSTRAINTS — Hard Deadlines

The SDK enforces callback-level deadlines. Exceeding them = callback failure = 0 points.

### Referee SDK Callback Deadlines (from `context_builder.py`)

| Callback | Deadline | Our Budget | Critical Rule |
|---|---|---|---|
| `get_warmup_question` | 30s | ~0.01s | No LLM needed — just return math question |
| `get_round_start_info` | 60s | ~3-40s | Max 3 hint retries × 8s = 24s worst case |
| `get_answers` | 120s | ~5-15s | **MUST batch all 20 Qs in ONE LLM call** |
| `get_score_feedback` | 180s | ~8-30s | Score + feedback in one LLM call |

### Player Protocol Timeouts (from PDF, enforced by referee)

| Phase | Timeout | Our Budget | Notes |
|---|---|---|---|
| Warmup answer | 300s (5 min) | ~0.01s | Parse math, compute answer — no LLM |
| Questions | 600s (10 min) | ~6-17s | ChromaDB search + one LLM call |
| Guess | 300s (5 min) | ~8-23s | Re-rank + SQLite lookup + one LLM call |

### Implementation Rules for Timing Safety

1. **NEVER make individual LLM calls per question** — always batch. 20 individual calls = 60-100s, too close to 120s deadline.
2. **Limit Taboo Word retries to 3** — each retry costs ~8s. 3 retries = 24s, still fits in 60s.
3. **Pre-compute everything possible offline** — difficulty index, paragraph embeddings, sentence extraction all happen in Phase 1, cost zero at runtime.
4. **Use `claude-sonnet-4-20250514` not Opus** — Sonnet is 3-5x faster with acceptable quality for game operations.
5. **Set LLM `max_tokens` conservatively** — don't let scoring feedback ramble beyond 200 words per field.
6. **Add timeout logging** — log elapsed time per callback so we can spot slow operations in testing.

---

## SUMMARY: What Makes Us Win

| Role | Key Advantage | How |
|---|---|---|
| Referee | Smart paragraph selection | Pre-computed difficulty index → always "medium" |
| Referee | Calibrated hints | Ambiguous enough for differentiation |
| Referee | Fair scoring | No gaming needed if paragraph choice is right |
| Player | Exact sentence lookup | RAG database → 100% match when correct paragraph found |
| Player | Information-theoretic questions | Maximize discrimination per question |
| Player | Bayesian re-ranking | Systematic candidate elimination from answers |
