"""Paragraph quality filter — filters out code fragments, headings, and noise.

Determines which paragraphs are valid game candidates based on their
opening sentence and content.
"""

import re

# Tokens that indicate a code fragment (as first token)
CODE_TOKENS = frozenset({
    '{', '}', '=', '//', 'import', 'def', 'class', 'return',
    'from', 'if', 'for', 'while', 'try', 'except', 'with',
    'print', 'self', '#', '"""', "'''", 'async', 'await',
    'const', 'let', 'var', 'function', 'export', 'module',
    'result', 'response', 'model', 'config', 'data',
    'json', 'xml', 'html', 'http', 'https', 'api',
    'protection_level', 'details', 'markdown',
})

# Hebrew TOC/heading keywords
HEBREW_TOC_WORDS = {'תמישר', 'תואלבט', 'םיניינע', 'ןכות'}

# Hebrew character range
_HEBREW_RE = re.compile(r'[\u0590-\u05FF]')


def _first_line(text: str) -> str:
    """Get the first non-empty line of text."""
    for line in text.split('\n'):
        line = line.strip()
        if line:
            return line
    return text.strip()


def _has_hebrew(text: str) -> bool:
    """Check if text contains at least one Hebrew character."""
    return bool(_HEBREW_RE.search(text))


def _is_code_fragment(opening: str) -> bool:
    """Check if opening starts with a code token or looks like code."""
    first_line = _first_line(opening)
    first_token = first_line.split()[0] if first_line.split() else ""
    # Strip punctuation for matching
    clean = re.sub(r'[^\w#{}=/"\'.]', '', first_token)
    if clean.lower() in CODE_TOKENS or clean in CODE_TOKENS:
        return True
    # Code patterns: contains =, (), {} in first line without Hebrew
    if not _has_hebrew(first_line) and re.search(r'[=(){}\[\];]', first_line):
        return True
    return False


def _is_heading_or_toc(opening: str) -> bool:
    """Check if opening sentence is a heading/TOC entry."""
    first_line = _first_line(opening)
    words = first_line.split()
    if not words:
        return False
    # Number + short title pattern (e.g., "8.7 Summary")
    if len(words) <= 5 and re.match(r'^[\d.]+$', words[0]):
        return True
    # Contains Hebrew TOC keywords
    for w in words:
        if w in HEBREW_TOC_WORDS:
            return True
    return False


def _has_formula_or_noise(text: str) -> bool:
    """Check if text has math formulas, graph data, or technical noise."""
    # Math formula indicators: =, P(...), multiple decimals
    if text.count('=') >= 2:
        return True
    if re.search(r'P\([^)]+\)', text):  # P(x) probability notation
        return True
    # Many decimal numbers (graph data, tables)
    decimals = re.findall(r'\d+\.\d+', text)
    if len(decimals) >= 3:
        return True
    # cid artifacts from PDF extraction
    if '(cid:' in text:
        return True
    # Code/technical artifacts
    if any(x in text for x in ['.json', '.py', '.js', 'API ', 'plugin',
                                'http://', 'https://', 'google.com', '.com/',
                                'localhost', 'W₁', 'h₁', 'ht−1']):
        return True
    # Section numbering pattern (5.2.1, א.5, etc.)
    if re.search(r'\d+\.\d+\.\d+', text):
        return True
    # Too many parentheses (formulas/code)
    if text.count('(') + text.count(')') >= 6:
        return True
    return False


def _hebrew_ratio(text: str) -> float:
    """Fraction of alphabetic chars that are Hebrew."""
    hebrew = len(_HEBREW_RE.findall(text))
    alpha = len(re.findall(r'[a-zA-Z\u0590-\u05FF]', text))
    return hebrew / alpha if alpha > 0 else 0


def is_valid_paragraph(opening_sentence: str, full_text: str) -> bool:
    """Determine if a paragraph is a valid game candidate."""
    opening = opening_sentence.strip()
    first_line = _first_line(opening)
    words = first_line.split()

    if not _has_hebrew(first_line):
        return False
    if len(words) < 8:
        return False
    if _is_code_fragment(opening):
        return False
    if _is_heading_or_toc(opening):
        return False
    # Skip repetitive content (tables/diagrams)
    unique_words = set(w.lower() for w in words)
    if len(unique_words) < len(words) * 0.4:
        return False
    # Reject formulas, graph data, code references
    if _has_formula_or_noise(first_line):
        return False
    # Opening sentence must be mostly Hebrew (≥40% Hebrew chars)
    if _hebrew_ratio(first_line) < 0.4:
        return False
    return True
