# Q21G — Prompt Engineering Log (ספר הפרומפטים)

Version: 1.0.0 | Updated: 2025-01

This document tracks the iterative development of all 6 LLM skill prompts used in Q21G,
including design rationale, key decisions, and observed failure modes.

---

## Prompt Index

| # | Skill File | Agent | Callback | Status |
|---|---|---|---|---|
| 1 | `referee_hint_generator.md` | Referee | `get_round_start_info` | v3 — Production |
| 2 | `referee_question_answerer.md` | Referee | `get_answers` | v2 — Production |
| 3 | `referee_scorer.md` | Referee | `get_score_feedback` | v2 — Production |
| 4 | `player_question_generator.md` | Player | `get_questions` | v2 — Production |
| 5 | `player_guess_maker.md` | Player | `get_guess` | v3 — Production |
| 6 | `warmup_solver.md` | Both | warmup callbacks | v1 — Production |

---

## 1. Referee Hint Generator (`referee_hint_generator.md`)

### Purpose
Generate a 15-word max description of a selected paragraph that (a) contains **no words** from
the paragraph text (Taboo Word Rule), and (b) semantically matches the paragraph well enough
that ChromaDB can retrieve it.

### v1 — Initial Draft

**Design**: Simple instruction to describe the paragraph without repeating its words.

```
Describe this paragraph in 15 words or fewer, without using any words from the paragraph.

Paragraph: {paragraph_text}
```

**Failure mode**: LLM frequently used synonyms that were too close to the taboo words
(e.g., using "neural" when paragraph contained "neuron"). Also generated vague, generic
hints that ChromaDB couldn't retrieve.

---

### v2 — Structured Validation Prompt

**Change**: Added explicit taboo word list, validation step, and self-test instruction.

**Key additions:**
- Provide the explicit forbidden word set (not just the paragraph text)
- Require the LLM to output a `hint_overlap_check` validation line
- Added instruction: "After generating, verify every hint word is NOT in the forbidden set"

**Failure mode**: LLM would declare "PASS" on overlap check even when words overlapped.
The self-validation was unreliable. Also: ChromaDB self-test wasn't implemented yet.

---

### v3 — ChromaDB Self-Test + Goldilocks Calibration (Current)

**Change**: Added hint self-test logic (coded in `referee_helpers.py`), calibration guidance,
and retry protocol.

**Key design decisions:**

1. **Taboo validation is done in code** (`referee_helpers.py`), not trusted to the LLM.
   The LLM generates the hint; Python validates it.

2. **Goldilocks calibration** — the prompt now explains the strategic goal:
   - Too specific (1 paragraph match) → both players find it → tie → 0 referee points
   - Too vague (50+ matches) → neither finds it → 0 referee points
   - Target: 3–5 paragraph matches

3. **ChromaDB self-test** — after hint generation, code runs:
   `chroma.search(hint, filter_pdf=book_name, n=10)` — if the target paragraph isn't in
   top-5, a new hint is regenerated with feedback.

**Sample successful prompt input/output:**

*Paragraph (Hebrew):*
```
מנגנון הקשב (Attention) הוא רכיב מרכזי בארכיטקטורת הטרנספורמר.
הוא מאפשר למודל לתת משקל שונה לכל אלמנט ברצף הקלט בעת עיבוד כל
אלמנט פלט. ישנם שלושה וקטורים מרכזיים: שאילתה (Query), מפתח (Key)
וערך (Value).
```

*Generated hint (v3):*
```
"Mechanism enabling selective weighting across sequence elements using three learned vectors"
```

*Validation:* No forbidden words. ChromaDB finds paragraph at rank #2. ✓

---

## 2. Referee Question Answerer (`referee_question_answerer.md`)

### Purpose
Answer all 20 player questions in a single LLM call, using only the secret paragraph text.
Answers must be: A, B, C, D, or "Not Relevant".

### v1 — Initial Draft

**Design**: Provide paragraph and all 20 questions, ask for answers.

**Failure mode**: LLM would sometimes answer only 15-18 questions, skipping the rest.
Also: would output free-text explanations instead of just A/B/C/D.

---

### v2 — Strict Format Enforcement (Current)

**Key changes:**

1. **Explicit format requirement** — output must be a numbered list, one answer per line:
   ```
   1. A
   2. Not Relevant
   3. C
   ...
   20. B
   ```

2. **"Not Relevant" rule** — if the paragraph doesn't contain enough information to
   distinguish between answer choices, respond "Not Relevant" rather than guessing.

3. **Batch requirement explicitly stated** — "Answer ALL 20 questions in this single
   response. Do not split across multiple messages."

**Sample output (v2):**
```
1. B
2. Not Relevant
3. A
4. A
5. C
...
20. B
```

**Parse logic** (`referee_helpers.py`):
```python
# Parse "1. B" → {"question_number": 1, "answer": "B"}
import re
for line in response.splitlines():
    m = re.match(r"^(\d+)\.\s+(A|B|C|D|Not Relevant)$", line.strip())
    if m:
        answers.append({"question_number": int(m.group(1)), "answer": m.group(2)})
```

---

## 3. Referee Scorer (`referee_scorer.md`)

### Purpose
Score the player's guess against the actual paragraph on 4 components (0-100 each),
weighted to produce a private score.

### v1 — Initial Draft

**Design**: Provide actual paragraph, actual opening sentence, and player guess.
Ask for 4 scores + justification.

**Failure mode**: LLM would be inconsistent — an exact sentence match might score 70
while a near-miss scored 85. The scoring was subjective and varied run-to-run.

---

### v2 — String Pre-check Override + Rubric (Current)

**Key changes:**

1. **String pre-check in code** (`referee_scoring.py`): Before calling LLM, compute
   `SequenceMatcher(None, guess_sentence, actual_sentence).ratio()`. If ≥ 0.95, set
   `sentence_score = 98` and skip LLM for this component.

2. **Explicit rubric in prompt** — prevents arbitrary scoring:
   - 90-100: Exact or near-exact match (≥95% character similarity)
   - 70-89: Same paragraph, slightly different wording
   - 40-69: Correct topic but wrong paragraph
   - 0-39: Unrelated

3. **Justification scoring criteria** — minimum 3 Q&A citations required for 70+.

4. **Structured output** — JSON with individual scores:
   ```json
   {"sentence_score": 98, "justification_score": 72, "word_score": 65, "word_justification_score": 55}
   ```

---

## 4. Player Question Generator (`player_question_generator.md`)

### Purpose
Generate 20 Yes/No questions about the secret paragraph (of which the player only knows
the hint, book_name, and association domain). Questions must narrow down which of the
candidate paragraphs is the target.

### v1 — Initial Draft

**Design**: Provide hint and list of candidate paragraphs, ask for 20 questions.

**Failure mode**: LLM generated questions that were too generic ("Is this about AI?")
or too specific to candidate #1 (position bias — LLM defaults to the first candidate).

---

### v2 — Shuffled Candidates + Discriminative Framing (Current)

**Key changes:**

1. **Candidate shuffling** — `player_helpers.py` randomizes candidate order before
   passing to LLM. Removes position bias where LLM defaults to asking about candidate #1.

2. **Discriminative question framing** — prompt now says:
   > "Your goal is to ELIMINATE candidates, not confirm one. Each question should rule
   > out as many wrong paragraphs as possible."

3. **Three question phases** built into prompt:
   - Phase 1 (Q1-7): Broad topic/domain questions
   - Phase 2 (Q8-14): Specific content questions to narrow candidates
   - Phase 3 (Q15-20): Precise questions about opening sentence style/structure

4. **Per-candidate evidence format** — show each candidate's key content so the LLM
   can design discriminating questions.

**Sample question output (v2):**
```
1. Does the paragraph discuss a specific computational mechanism (not a general concept)?
2. Is the main topic a method or technique rather than a dataset or evaluation?
...
20. Does the opening sentence begin with a definition of a technical term?
```

---

## 5. Player Guess Maker (`player_guess_maker.md`)

### Purpose
Combine 20 Q&A answers with candidate paragraph texts to identify the most likely
paragraph, then return its exact opening sentence with justification.

### v1 — Initial Draft

**Design**: Provide all Q&A answers and candidates, ask LLM to pick the best match
and write the opening sentence.

**Critical failure**: LLM would **copy the opening sentence from the prompt** but with
small transcription errors — especially in Hebrew. Hebrew text would get mis-rendered,
causing the sentence score to be 60-70 instead of 98.

---

### v2 — Candidate Index + Code Lookup

**Key change**: LLM no longer writes the Hebrew sentence. Instead:
1. LLM picks the **index** of the best candidate (e.g., "candidate 3")
2. Code performs exact lookup: `candidates[chosen_idx]["opening_sentence"]`

**Why this works**: The opening sentence was stored in SQLite during the knowledge base
build. It's the canonical ground truth. LLM can't corrupt it.

**Failure mode**: LLM would sometimes pick candidate 0 even when a better match existed,
because of position bias. Also: per-candidate reasoning was shallow.

---

### v3 — Per-Candidate Scoring + Explicit Evidence Chain (Current)

**Key changes:**

1. **Per-candidate scoring** — prompt says:
   > "For each candidate, count how many Q&A answers are consistent with that candidate.
   > Show your count. Pick the candidate with the HIGHEST count."

2. **Evidence chain required** — output must cite 3+ Q&A pairs in justification:
   > "Q3(A) confirms layered architecture, Q7(B) rules out neural networks..."

3. **Fallback protocol** documented in prompt:
   - All "Not Relevant": Use semantic search rank, ignore Q&A
   - Contradictory answers: Weight later questions higher
   - No candidates: Run emergency ChromaDB search in get_guess

**Sample output (v3):**
```json
{
  "chosen_candidate_index": 2,
  "sentence_justification": "Q3(A) confirmed layered design, Q7(B) ruled out neural nets,
    Q12(A) confirmed definition-style opening. Candidate 2 scores 14/20 consistent answers.",
  "associative_word": "שכבתיות",
  "word_justification": "Q11(A) confirmed architectural concept, term appears in candidate text.",
  "confidence": 0.82
}
```

The `opening_sentence` is then looked up from `candidates[2]["opening_sentence"]`.

---

## 6. Warmup Solver (`warmup_solver.md`)

### Purpose
Answer warmup questions that the referee sends to both players at round start. These are
not scored — they're used to signal player readiness.

### v1 — Current (No iterations needed)

**Design**: Simple prompt, no LLM call required. The warmup question is answered with a
fixed heuristic response ("Ready") or a short informational answer.

**Implementation**: The `get_warmup_answer` callback returns a fixed string without
calling the LLM. The warmup solver skill file is loaded for completeness but not used
in production — it exists as a reference/fallback.

---

## Summary: Key Prompt Engineering Lessons

| Lesson | Applied Where |
|--------|--------------|
| Never trust LLM to copy Hebrew text accurately | Guess maker v2: use index + code lookup |
| LLM position bias: shuffle candidates before passing | Question generator v2: shuffle before prompt |
| Code-side validation > LLM self-validation | Hint taboo check done in Python, not LLM |
| Explicit rubrics reduce scoring variance | Scorer v2: exact point ranges with examples |
| Per-item scoring forces thorough reasoning | Guess maker v3: count consistent Q&A per candidate |
| Batch all questions in one LLM call | Answerer v2: explicit batch instruction |
| Self-test with your own search engine | Hint generator v3: ChromaDB self-test before returning |
