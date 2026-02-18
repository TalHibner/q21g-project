"""Tests for knowledge_base.paragraph_filter — quality filtering module.

Covers all helper functions and the main is_valid_paragraph function
with various edge cases: code fragments, headings, formulas, Hebrew
ratio, and valid paragraphs.
"""

from knowledge_base.paragraph_filter import (
    _first_line,
    _has_hebrew,
    _is_code_fragment,
    _is_heading_or_toc,
    _has_formula_or_noise,
    _hebrew_ratio,
    is_valid_paragraph,
)


# ─── _first_line ────────────────────────────────────────────────

def test_first_line_simple():
    assert _first_line("hello world") == "hello world"


def test_first_line_multiline():
    assert _first_line("\n\nhello\nworld") == "hello"


def test_first_line_empty():
    assert _first_line("") == ""


def test_first_line_whitespace_only():
    result = _first_line("   \n   ")
    assert result == ""


# ─── _has_hebrew ────────────────────────────────────────────────

def test_has_hebrew_true():
    assert _has_hebrew("שלום עולם") is True


def test_has_hebrew_false():
    assert _has_hebrew("hello world") is False


def test_has_hebrew_mixed():
    assert _has_hebrew("hello שלום") is True


# ─── _is_code_fragment ──────────────────────────────────────────

def test_code_fragment_import():
    assert _is_code_fragment("import os") is True


def test_code_fragment_def():
    assert _is_code_fragment("def foo():") is True


def test_code_fragment_class():
    assert _is_code_fragment("class MyClass:") is True


def test_code_fragment_bracket():
    assert _is_code_fragment("{key: value}") is True


def test_code_fragment_equals_no_hebrew():
    assert _is_code_fragment("x = 5 + y") is True


def test_code_fragment_hebrew_text():
    assert _is_code_fragment("זהו טקסט בעברית רגיל ולא קוד") is False


# ─── _is_heading_or_toc ────────────────────────────────────────

def test_heading_numbered():
    assert _is_heading_or_toc("8.7 Summary") is True


def test_heading_longer_text():
    assert _is_heading_or_toc("8.7 This is a longer heading with more words wow") is False


def test_heading_normal_text():
    assert _is_heading_or_toc("This is a normal sentence about something") is False


def test_heading_empty():
    assert _is_heading_or_toc("") is False


# ─── _has_formula_or_noise ──────────────────────────────────────

def test_formula_equals():
    assert _has_formula_or_noise("x = 5 and y = 10") is True


def test_formula_probability():
    assert _has_formula_or_noise("The value P(x|y) is important") is True


def test_formula_decimals():
    assert _has_formula_or_noise("Values are 1.5 and 2.3 and 3.7") is True


def test_formula_cid():
    assert _has_formula_or_noise("text with (cid:123) artifacts") is True


def test_formula_code_artifacts():
    assert _has_formula_or_noise("see file config.json for details") is True


def test_formula_url():
    assert _has_formula_or_noise("visit https://example.com for info") is True


def test_formula_section_numbering():
    assert _has_formula_or_noise("section 5.2.1 covers this topic") is True


def test_formula_many_parens():
    assert _has_formula_or_noise("f(x) = g(y) + h(z)") is True


def test_formula_clean_text():
    assert _has_formula_or_noise("זהו טקסט נקי בעברית") is False


def test_formula_api_keyword():
    assert _has_formula_or_noise("The API endpoint is available") is True


def test_formula_python_file():
    assert _has_formula_or_noise("Open the main.py file") is True


# ─── _hebrew_ratio ──────────────────────────────────────────────

def test_hebrew_ratio_all_hebrew():
    ratio = _hebrew_ratio("שלום עולם")
    assert ratio > 0.9


def test_hebrew_ratio_all_english():
    assert _hebrew_ratio("hello world") == 0.0


def test_hebrew_ratio_mixed():
    ratio = _hebrew_ratio("שלום hello")
    assert 0.0 < ratio < 1.0


def test_hebrew_ratio_no_alpha():
    assert _hebrew_ratio("123 456") == 0


# ─── is_valid_paragraph (integration) ──────────────────────────

def test_valid_hebrew_paragraph():
    """A good Hebrew paragraph should pass the filter."""
    opening = "למידת מכונה היא תחום במדעי המחשב שעוסק בפיתוח אלגוריתמים המאפשרים למחשבים ללמוד מנתונים"
    full_text = opening + " ולשפר את הביצועים שלהם ללא תכנות מפורש"
    assert is_valid_paragraph(opening, full_text) is True


def test_invalid_no_hebrew():
    """English-only paragraphs should be rejected."""
    opening = "Machine learning is a field of computer science that deals with developing algorithms"
    assert is_valid_paragraph(opening, opening) is False


def test_invalid_too_short():
    """Short opening sentences should be rejected."""
    opening = "שלום עולם טוב"
    assert is_valid_paragraph(opening, opening) is False


def test_invalid_code_fragment():
    """Code fragments should be rejected."""
    opening = "import tensorflow as tf and then we can start building models for deep learning"
    assert is_valid_paragraph(opening, opening) is False


def test_invalid_low_uniqueness():
    """Repetitive text should be rejected."""
    opening = "שלום שלום שלום שלום שלום שלום שלום שלום שלום שלום"
    assert is_valid_paragraph(opening, opening) is False


def test_invalid_formula_in_opening():
    """Formulas in the opening should reject the paragraph."""
    opening = "הערך של P(x|y) הוא חשוב מאוד בהקשר של למידת מכונה ובינה מלאכותית"
    assert is_valid_paragraph(opening, opening) is False


def test_invalid_low_hebrew_ratio():
    """Low Hebrew ratio should be rejected."""
    opening = "The value of machine learning is important שלום in modern computer science applications today"
    assert is_valid_paragraph(opening, opening) is False
