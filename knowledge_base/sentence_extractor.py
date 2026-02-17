"""Hebrew first-sentence extraction for academic paragraphs.

Handles mixed Hebrew/English text with abbreviations, decimals, and URLs.
In Hebrew RTL text, periods often appear at line START (e.g., ".חווט\\n")
which is logically the END of the previous sentence.
"""

import re

# English abbreviations common in Hebrew academic text
ABBREVIATIONS = frozenset({
    'dr', 'mr', 'mrs', 'prof', 'e.g', 'i.e', 'etc', 'vs', 'al',
    'fig', 'eq', 'sec', 'ch', 'no', 'vol', 'st', 'jr', 'sr',
})


def _is_abbreviation(text_so_far: str) -> bool:
    """Check if the period ends a known abbreviation."""
    match = re.search(r'(\w+(?:\.\w+)*)\.$', text_so_far)
    if not match:
        return False
    word = match.group(1).lower()
    if word in ABBREVIATIONS:
        return True
    if '.' in word:
        base = word.replace('.', '')
        if base in {'eg', 'ie'}:
            return True
    return False


def extract_first_sentence(text: str) -> str:
    """Extract the first sentence from a Hebrew/mixed paragraph.

    Strategy (in order):
    1. Check for Hebrew RTL period at start of a line (sentence ends there)
    2. Standard char-by-char walk for . ! ? followed by whitespace
    3. Fallback: return just the first line

    Always returns a single-line result for clean matching.
    """
    if not text:
        return ""

    text = text.strip()

    # Strategy 1: Look for Hebrew RTL period pattern — period at start of line
    # Pattern: \n.word (period starts the next visual line, ending previous sentence)
    rtl_match = re.search(r'\n\.[\u0590-\u05FF\s]', text)
    if rtl_match:
        # Include content up through the period
        end = rtl_match.start() + 2
        candidate = text[:end].strip()
        # Collapse to single line and clean up
        single = ' '.join(candidate.split())
        if len(single.split()) >= 5:
            return single

    # Strategy 2: Standard char-by-char walk (within first 3 lines max)
    first_chunk = '\n'.join(text.split('\n')[:3])
    current = ""
    for i, ch in enumerate(first_chunk):
        current += ch

        if ch not in '.!?':
            continue

        if i + 1 >= len(first_chunk):
            break

        next_ch = first_chunk[i + 1]

        # Skip ellipsis
        if ch == '.' and (next_ch == '.' or (i > 0 and first_chunk[i - 1] == '.')):
            continue

        # Skip decimals: digit.digit
        if ch == '.' and i > 0 and first_chunk[i - 1].isdigit() and next_ch.isdigit():
            continue

        # Skip abbreviations
        if ch == '.' and _is_abbreviation(current):
            continue

        # Sentence boundary: punctuation followed by whitespace
        if next_ch in ' \n\t\r':
            result = current.strip()
            # Collapse to single line
            return ' '.join(result.split())

    # Strategy 3: No boundary found — return first line only
    first_line = text.split('\n')[0].strip()
    return first_line if first_line else text.strip()
