# Q21G Warmup Solver

Handles the warmup phase for both referee and player. This is Phase 0 — a connectivity check before the real game begins.

## Referee Side: `get_warmup_question(ctx)`

### What You Receive
```
ctx["dynamic"]["round_number"]  — Current round (1, 2, 3, ...)
ctx["dynamic"]["round_id"]      — Round identifier (e.g., "ROUND_1")
ctx["dynamic"]["game_id"]       — Game identifier (e.g., "0101001")
```

### What You Generate
A simple math question to verify players are online and responsive.

```json
{
  "warmup_question": "What is 7 * 8?"
}
```

### Rules
- Question must be simple enough to solve programmatically (basic arithmetic)
- Supported operations: addition (+), subtraction (-), multiplication (*), integer division (/)
- Keep numbers reasonable (single or double digit operands)
- Vary questions across rounds — don't always ask the same one
- This is NOT scored — it's purely a connectivity/readiness check
- Warmup failure does NOT cancel the game (PDF Section 1.9.1)

### Generation Strategy
Use Python's `random` module to generate varied questions:
```python
import random
ops = [('+', lambda a,b: a+b), ('-', lambda a,b: a-b), ('*', lambda a,b: a*b)]
a, b = random.randint(2, 15), random.randint(2, 15)
op_sym, op_fn = random.choice(ops)
question = f"What is {a} {op_sym} {b}?"
answer = str(op_fn(a, b))
```

No LLM needed for this callback.

---

## Player Side: `get_warmup_answer(ctx)`

### What You Receive
```
ctx["dynamic"]["warmup_question"]  — A math question string (e.g., "What is 7 * 8?")
```

### What You Return
```json
{
  "answer": "56"
}
```

### Parsing Strategy
Extract numbers and operator from the question string, compute the result:

```python
import re

def solve_warmup(question: str) -> str:
    """Parse and solve a simple math question."""
    # Extract numbers and operator
    match = re.search(r'(\d+)\s*([+\-*/])\s*(\d+)', question)
    if match:
        a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
        if op == '+': return str(a + b)
        if op == '-': return str(a - b)
        if op == '*': return str(a * b)
        if op == '/': return str(a // b)
    
    # Fallback: try eval on extracted expression (safe for simple math)
    numbers = re.findall(r'\d+', question)
    ops = re.findall(r'[+\-*/]', question)
    if len(numbers) == 2 and len(ops) == 1:
        try:
            result = eval(f"{numbers[0]} {ops[0]} {numbers[1]}")
            return str(int(result))
        except:
            pass
    
    return "0"  # Safe fallback
```

No LLM needed for this callback.

### Important
- The answer must be a **string**, not an integer
- Handle edge cases: division by zero → return "0"
- Handle both English ("What is 7 * 8?") and Hebrew ("?מה זה 7 * 8") question formats
- Timeout: 5 minutes (PDF Section 1.9.5, Table 9), with one retry allowed before disqualification
