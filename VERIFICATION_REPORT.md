# Q21G Verification Report — PDF vs SDK vs Our Design

## 🔴 CRITICAL FINDING #1: Referee Does NOT Choose the Paragraph

### PDF Says (Chapter 8.5, page 177):
The `MATCH_ASSIGNMENT` message from the League Manager contains the **full book info**:
```json
"book": {
    "name": "The Little Prince",
    "description": "A philosophical tale about love and loss",
    "associative_domain": "animal",
    "opening_sentence": "All grown-ups were once children...",
    "associative_word": "fox"
}
```

### SDK Reality (context_builder.py + warmup.py):
The SDK's `build_round_start_info_ctx()` does **NOT** pass any book info. The ctx only has:
- round_number, round_id, player_a info, player_b info

The student callback `get_round_start_info(ctx)` is expected to **return** `{book_name, book_hint, association_word}`.

### Contradiction Resolution:
The PDF describes the **protocol-level** message flow (what happens over email). The SDK **abstracts this away**. Here's what actually happens:

1. League Manager sends `MATCH_ASSIGNMENT` to referee **via email** (with full book info — but only in warmup/training mode or as a placeholder)
2. The SDK receives this, stores player info on GameState
3. SDK calls student's `get_round_start_info()` — student **generates** book_name, book_hint, association_word
4. SDK stores the result in `state.book_name/book_hint/association_word`
5. SDK sends `Q21_ROUND_START` to players with these values

**BUT** the `MATCH_ASSIGNMENT` in the PDF example includes `opening_sentence` and `associative_word` — these are the **correct answers**. In the actual implementation:
- **Training mode**: The League Manager may provide these, and the referee SDK may store them for scoring reference
- **Our implementation**: We MUST generate our own — the SDK's `get_round_start_info` is where WE choose the paragraph

### Impact on Our Design:
✅ **Our design is CORRECT for the SDK callbacks.** The referee callback DOES generate the book info. The SDK stores what we return.

### BUT — Scoring Needs the "Actual" Answers:
The `build_score_feedback_ctx()` has:
```python
"actual_opening_sentence": actual_opening_sentence or self.config.get("actual_opening_sentence"),
"actual_associative_word": actual_associative_word or self.config.get("actual_associative_word"),
```

This means the SDK **can** receive the actual answers from config (i.e., from MATCH_ASSIGNMENT), but falls back to None. The DemoAI stores them on `self._actual_opening_sentence` and `self._actual_associative_word`.

**WE must also store the actual opening sentence and association word on `self`** to use in scoring. The SDK doesn't automatically pass them to callback 4 — we have to manage this ourselves.

---

## 🔴 CRITICAL FINDING #2: Scoring Breakdown Scale

### PDF Table 82 (page 184) says:
| Component | Range |
|---|---|
| Opening sentence | **0-50** |
| Sentence justification | **0-20** |
| Associative word | **0-20** |
| Word justification | **0-10** |
| Total | 0-100 |

### SDK callbacks.py (Score Feedback docstring) says:
```python
"breakdown": {
    "opening_sentence_score": float,        # 0-100 (50% weight)
    "sentence_justification_score": float,  # 0-100 (20% weight)
    "associative_word_score": float,        # 0-100 (20% weight)
    "word_justification_score": float       # 0-100 (10% weight)
}
```

### SDK demo_ai.py ACTUALLY implements:
Each component scored 0-100, then weighted:
```python
private_score = (
    sentence_score * 0.50 +
    sentence_just_score * 0.20 +
    word_score * 0.20 +
    word_just_score * 0.10
)
```

### PDF Section 1.10.2 formula:
`private_score = 0.50×S_sentence + 0.20×S_justification + 0.20×S_word + 0.10×S_word_justification`
Where each S is 0-100.

### Resolution:
**Two valid interpretations coexist:**
- PDF Table 82: breakdown values are **already weighted** (0-50, 0-20, 0-20, 0-10), total = sum
- SDK + PDF formula: breakdown values are **raw** (0-100 each), total = weighted sum

**The SDK and formula both say 0-100 per component with weights.** Table 82 just shows the weighted result ranges. The Q21_SCORE_FEEDBACK message example confirms:
```json
"opening_sentence_score": 45.0  // could be either interpretation
```

### Our Design Decision:
✅ **Follow the SDK** — score each component 0-100, multiply by weights. The breakdown dict stores raw 0-100 scores. The `private_score` is the weighted sum.

---

## 🔴 CRITICAL FINDING #3: League Points Thresholds Mismatch

### PDF Table 11 (page 43):
| Private Score | League Points |
|---|---|
| 85-100 | 3 |
| 70-84 | 2 |
| 50-69 | 1 |
| 0-49 | 0 |

### SDK callbacks.py docstring:
```
league_points: 3 if private_score >= 80, 2 if >= 60, 1 if >= 40, else 0
```

### SDK demo_ai.py actually implements:
```python
if private_score >= 85: league_points = 3
elif private_score >= 70: league_points = 2
elif private_score >= 50: league_points = 1
else: league_points = 0
```

### Resolution:
The SDK docstring has different thresholds (80/60/40) than the PDF (85/70/50), but the demo_ai matches the PDF. The PDF says:
> "In case of contradiction between the document and the model — the model takes precedence"

### Our Design Decision:
✅ **Follow the PDF thresholds (85/70/50)** as implemented in demo_ai. The callbacks.py docstring is slightly wrong but the actual implementation is correct.

---

## 🟡 FINDING #4: Verbal Feedback Length

### PDF Section 3.7.2 (page 95):
> "30-50 word verbal explanation for each of the four scoring components"

### SDK callbacks.py docstring:
> "150-200 word feedback" for opening_sentence and associative_word

### Q21_SCORE_FEEDBACK message (page 185):
Only two feedback fields: `opening_sentence` and `associative_word`

### Resolution:
The SDK has TWO feedback fields (not four). The PDF says 30-50 words per component. The SDK says 150-200 per field.

### Our Design Decision:
⚠️ **Follow the SDK format** — two feedback fields in the `feedback` dict: `opening_sentence` and `associative_word`. For length, use the SDK's 150-200 words since that's what the SDK validates. **UPDATE our referee_scorer.md accordingly.**

---

## 🟡 FINDING #5: Player Guess Field Names

### PDF message format (page 183):
```json
"opening_sentence_guess": "...",
"associative_word_guess": "fox",
```

### SDK player template (my_player.py):
```python
"opening_sentence": "...",
"associative_word": "...",
```

### SDK player game_executor.py:
```python
"opening_sentence": result.get("opening_sentence", ""),
"associative_word": result.get("associative_word", ""),
```

### SDK referee context_builder.py (what referee receives):
```python
"player_guess": {
    "opening_sentence": guess.get("opening_sentence", ""),
    "associative_word": guess.get("associative_word", ""),
}
```

### Resolution:
The PDF uses `_guess` suffix in protocol messages. The SDK strips the suffix in callbacks.

### Our Design Decision:
✅ **Follow the SDK** — use `opening_sentence` and `associative_word` (no `_guess` suffix) in our return dicts. The SDK handles protocol field mapping.

---

## 🟡 FINDING #6: Warmup Message Includes Book Description

### PDF (page 178-179):
The `Q21_WARMUP_CALL` message includes:
```json
"book_description": "A philosophical tale about love and loss",
"associative_domain": "animal"
```

### SDK envelope_builder.py:
The warmup call only sends:
```python
"warmup_question": warmup_question,
"deadline": deadline,
"auth_token": auth_token,
```
**No book_description or associative_domain in warmup call.**

### Resolution:
The SDK sends book info in `Q21_ROUND_START` (after warmup), not in warmup. The PDF example may be from an older version.

### Our Design Decision:
✅ **Follow the SDK** — warmup is just a math question, no book info.

---

## 🟡 FINDING #7: Answer Format Values

### PDF Table 78 (page 182):
| Value | Meaning |
|---|---|
| A | Yes / Positive |
| B | No / Negative |
| C | Partially / Sometimes |
| D | Unknown / Can't determine |
| NOT_RELEVANT | Question is irrelevant |

### SDK:
Valid answers: `"A"`, `"B"`, `"C"`, `"D"`, or `"Not Relevant"`

### Resolution:
PDF says `NOT_RELEVANT` (underscore). SDK says `"Not Relevant"` (space). The actual Q21_ANSWERS_BATCH example in the PDF also uses `NOT_RELEVANT`.

### Our Design Decision:
⚠️ **Follow the SDK format** — use `"Not Relevant"` (with space). The SDK is what actually validates our output. **BUT** the question options are designed by the PLAYER, so the A/B/C/D meaning varies per question. Table 78 is just a common convention.

---

## 🟢 CONFIRMED CORRECT: Game Flow in Our Design

| Phase | PDF | SDK | Our Design | Status |
|---|---|---|---|---|
| 0: Warmup | Referee sends math Q, players answer | ✅ Matches | ✅ warmup_solver.md | ✅ |
| 1: Choose Paragraph | Referee chooses | SDK calls `get_round_start_info` | ✅ referee_hint_generator.md | ✅ |
| 2: Questions | Player sends 20 MCQ | SDK calls `get_questions` | ✅ player_question_generator.md | ✅ |
| 3: Answers | Referee answers per player | SDK calls `get_answers` per player | ✅ referee_question_answerer.md | ✅ |
| 4: Guess | Player sends guess | SDK calls `get_guess` | ✅ player_guess_maker.md | ✅ |
| 5: Score | Referee scores per player | SDK calls `get_score_feedback` per player | ✅ referee_scorer.md | ✅ |

---

## 🟢 CONFIRMED CORRECT: ctx Fields (SDK Source Code)

### Player `get_questions(ctx)`:
```python
ctx["dynamic"]["book_name"]         # str
ctx["dynamic"]["book_hint"]         # str  
ctx["dynamic"]["association_word"]  # str
```

### Player `get_guess(ctx)`:
```python
ctx["dynamic"]["book_name"]         # str
ctx["dynamic"]["book_hint"]         # str
ctx["dynamic"]["association_word"]  # str
ctx["dynamic"]["answers"]           # list of {question_number, answer}
ctx["dynamic"]["questions_sent"]    # list (may be empty)
```

### Referee `get_warmup_question(ctx)`:
```python
ctx["dynamic"]["round_number"]      # int
ctx["dynamic"]["round_id"]          # str
ctx["dynamic"]["player_a_id"]       # str
ctx["dynamic"]["player_b_id"]       # str
```

### Referee `get_round_start_info(ctx)`:
```python
ctx["dynamic"]["round_number"]      # int
ctx["dynamic"]["round_id"]          # str
ctx["dynamic"]["player_a"]          # dict with id, email, warmup_answer
ctx["dynamic"]["player_b"]          # dict with id, email, warmup_answer
```
**Note: NO book info in ctx — we must generate it ourselves**

### Referee `get_answers(ctx)`:
```python
ctx["dynamic"]["book_name"]         # str (what WE returned in callback 2)
ctx["dynamic"]["book_hint"]         # str
ctx["dynamic"]["association_word"]  # str
ctx["dynamic"]["questions"]         # list of question dicts
ctx["dynamic"]["player_email"]      # str
ctx["dynamic"]["player_id"]         # str
```

### Referee `get_score_feedback(ctx)`:
```python
ctx["dynamic"]["book_name"]                     # str
ctx["dynamic"]["book_hint"]                     # str
ctx["dynamic"]["association_word"]              # str
ctx["dynamic"]["actual_opening_sentence"]       # str or None
ctx["dynamic"]["actual_associative_word"]       # str or None
ctx["dynamic"]["player_guess"]["opening_sentence"]          # str
ctx["dynamic"]["player_guess"]["sentence_justification"]    # str
ctx["dynamic"]["player_guess"]["associative_word"]          # str
ctx["dynamic"]["player_guess"]["word_justification"]        # str
ctx["dynamic"]["player_guess"]["confidence"]                # float
```
**Note: actual_opening_sentence may be None — we MUST store it on self**

---

## 🟢 CONFIRMED CORRECT: Return Types

### Referee `get_warmup_question` returns:
```python
{"warmup_question": str}
```

### Referee `get_round_start_info` returns:
```python
{"book_name": str, "book_hint": str, "association_word": str}
```

### Referee `get_answers` returns:
```python
{"answers": [{"question_number": int, "answer": str}]}
```
Where answer is "A", "B", "C", "D", or "Not Relevant"

### Referee `get_score_feedback` returns:
```python
{
    "league_points": int,        # 0-3
    "private_score": float,      # 0-100
    "breakdown": {
        "opening_sentence_score": float,
        "sentence_justification_score": float,
        "associative_word_score": float,
        "word_justification_score": float,
    },
    "feedback": {
        "opening_sentence": str,
        "associative_word": str,
    }
}
```

### Player `get_warmup_answer` returns:
```python
{"answer": str}
```

### Player `get_questions` returns:
```python
{"questions": [{"question_number": int, "question_text": str, "options": {"A": str, "B": str, "C": str, "D": str}}]}
```

### Player `get_guess` returns:
```python
{
    "opening_sentence": str,
    "sentence_justification": str,
    "associative_word": str,
    "word_justification": str,
    "confidence": float,
}
```

### Player `on_score_received`: returns None

---

## REQUIRED UPDATES TO OUR SKILL FILES

### 1. referee_scorer.md — Fix feedback format
- ❌ Currently says "150-200 words per component" for 4 components
- ✅ Should be: TWO feedback fields only (`opening_sentence` and `associative_word`), 150-200 words each
- ❌ Currently says each component scored differently (50/20/20/10 scale)  
- ✅ Should be: Each component 0-100, then weighted by 0.50/0.20/0.20/0.10

### 2. referee_hint_generator.md — Clarify self-storage requirement
- ⚠️ Should explicitly note: `ctx` does NOT contain any book info
- ✅ We must select paragraph from knowledge base, store actual_opening_sentence and actual_associative_word on `self`
- ✅ Return only `{book_name, book_hint, association_word}` to SDK

### 3. referee_question_answerer.md — Verify ctx fields
- ✅ ctx already contains book_name, book_hint, association_word from what we returned
- ⚠️ Should note: We ALSO need self._paragraph_text for answering (SDK doesn't have the full text)

### 4. player_guess_maker.md — Confirm no word_variations field
- ❌ Our skill mentions `association_variations` field
- ✅ SDK expects: `associative_word` (single string), no variations array
- The PDF protocol message has `word_variations` but the SDK strips it

### 5. All skills — Verify ctx access patterns
- ✅ Always use `ctx["dynamic"]["field_name"]` pattern

---

## SUMMARY OF ACTION ITEMS

1. **FIX** referee_scorer.md: feedback is 2 fields (not 4), each 150-200 words
2. **FIX** player_guess_maker.md: remove `association_variations`, use `associative_word` only
3. **VERIFY** all skills reference correct ctx field names from SDK
4. **ENSURE** referee stores `self._actual_opening_sentence` and `self._actual_associative_word` in callback 2 for use in callback 4
5. **USE** league point thresholds: 85/70/50 (PDF), not 80/60/40 (SDK docstring)
