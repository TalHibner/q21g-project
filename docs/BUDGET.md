# Q21G — API Cost Budget & Tracking
Version: 1.0.0

---

## 1. Pricing Reference

Model used: **`claude-sonnet-4-20250514`**

| Token type | Price (as of 2025-Q2) |
|---|---|
| Input tokens | $3.00 / 1M tokens |
| Output tokens | $15.00 / 1M tokens |

> Update this table when Anthropic changes pricing. Check: https://www.anthropic.com/pricing

---

## 2. Per-Callback Token Estimates

Estimates based on actual skill file sizes (measured) + typical context lengths.
Token count ≈ word count × 1.3 (mixed Hebrew/English text).

### Referee Agent

| Callback | LLM? | Input tokens | Output tokens | Cost/call | Calls/game | Cost/game |
|---|---|---|---|---|---|---|
| `get_warmup_question` | No | 0 | 0 | $0.000 | 0 | **$0.000** |
| `get_round_start_info` | Yes | ~2,300 | ~100 | $0.008 | 1–2 (retries) | **$0.010** |
| `get_answers` | Yes | ~1,900 | ~300 | $0.010 | 1 | **$0.010** |
| `get_score_feedback` | Yes | ~2,400 | ~500 | $0.015 | 2 (two players) | **$0.030** |
| **Referee total** | | | | | | **~$0.050** |

**Input breakdown for `get_round_start_info`:**
- Skill file (`referee_hint_generator.md`): ~1,776 tokens
- Paragraph text (avg 80 words): ~105 tokens
- Forbidden words list: ~200 tokens
- Overhead: ~100 tokens

**Input breakdown for `get_answers`:**
- Skill file (`referee_question_answerer.md`): ~688 tokens
- Paragraph text: ~105 tokens
- 20 questions × ~45 tokens each: ~900 tokens

**Input breakdown for `get_score_feedback`:**
- Skill file (`referee_scorer.md`): ~1,271 tokens
- Paragraph + opening sentence: ~150 tokens
- Player guess + justifications: ~300 tokens
- Answers context: ~300 tokens

### Player Agent

| Callback | LLM? | Input tokens | Output tokens | Cost/call | Calls/game | Cost/game |
|---|---|---|---|---|---|---|
| `get_warmup_answer` | No | 0 | 0 | $0.000 | 0 | **$0.000** |
| `get_questions` | Yes | ~3,400 | ~1,000 | $0.025 | 1 | **$0.025** |
| `get_guess` | Yes | ~3,200 | ~250 | $0.013 | 1 | **$0.013** |
| **Player total** | | | | | | **~$0.038** |

**Input breakdown for `get_questions`:**
- Skill file (`player_question_generator.md`): ~1,557 tokens
- 8 candidate summaries × ~150 tokens: ~1,200 tokens
- Context (book_name, hint, domain): ~100 tokens
- Overhead: ~100 tokens

**Input breakdown for `get_guess`:**
- Skill file (`player_guess_maker.md`): ~1,817 tokens
- 20 Q&A pairs × ~25 tokens: ~500 tokens
- Top-3 candidate texts × ~200 tokens: ~600 tokens

---

## 3. Per-Game Cost Summary

| Agent | Cost/game |
|---|---|
| Referee | ~$0.050 |
| Player | ~$0.038 |
| **Total per game** | **~$0.088** |

> **Note**: Each team plays 1 referee game AND 1 player game per round.
> Cost per round = ~$0.088 × 1 = **~$0.09/round** (you only pay for your own API calls).

---

## 4. Tournament Season Projection

Assuming a typical Q21G tournament season:

| Rounds | Games as referee | Games as player | **Projected total** |
|---|---|---|---|
| 5 rounds | 5 | 5 | **~$0.44** |
| 10 rounds | 10 | 10 | **~$0.88** |
| 20 rounds | 20 | 20 | **~$1.76** |

This is well within typical academic project budgets.

---

## 5. Cost Reduction Opportunities

| Lever | Potential saving | Trade-off |
|---|---|---|
| Reduce `max_tokens` in `get_questions` (3000 → 2000) | ~30% on that call | Risk of truncated question list |
| Cache embeddings (already done in ChromaDB) | Saves re-embedding cost | n/a |
| Use `claude-haiku` for `get_answers` | ~12× cheaper on that call | Lower answer quality |
| Reduce candidate count (20 → 10) in `get_questions` | ~15% shorter input | Slightly less context for LLM |

---

## 6. Actual Spending Tracker

Fill this table after each game. Use the logger output for exact token counts
(the Anthropic API response includes `usage.input_tokens` and `usage.output_tokens`).

| Date | Round | Role | Input tokens | Output tokens | Actual cost | Notes |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | Awaiting first live game |

### How to capture actual token usage

Add to `knowledge_base/llm_client.py` after a successful response:

```python
# Log token usage for budget tracking
logger.info(
    "LLM usage — input: %d, output: %d, estimated_cost: $%.4f",
    resp.usage.input_tokens,
    resp.usage.output_tokens,
    resp.usage.input_tokens / 1_000_000 * 3.0
    + resp.usage.output_tokens / 1_000_000 * 15.0,
)
```

Then extract from logs with:

```bash
grep "LLM usage" logs/*.log | awk -F'$' '{sum += $2} END {print "Total: $" sum}'
```

---

## 7. Budget Alerts

Set an alert threshold to avoid unexpected spending:

| Alert level | Threshold | Action |
|---|---|---|
| Warning | $2.00 cumulative | Review usage, check for retry loops |
| Hard stop | $5.00 cumulative | Investigate before continuing |

Retry loops (e.g., hint generation retrying 10× instead of 3×) are the most common
cause of cost overruns. The 3-retry cap in `generate_hint_and_word()` prevents this.
