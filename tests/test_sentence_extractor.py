"""Tests for sentence extraction from paragraphs."""

from knowledge_base.sentence_extractor import extract_first_sentence


def test_simple_period():
    assert extract_first_sentence("Hello world. More text here.") == "Hello world."


def test_question_mark():
    assert extract_first_sentence("Is this a question? Yes it is.") == "Is this a question?"


def test_exclamation():
    assert extract_first_sentence("Wow! That was great.") == "Wow!"


def test_skip_abbreviation():
    text = "Dr. Smith went home early today. Then he rested."
    assert extract_first_sentence(text) == "Dr. Smith went home early today."


def test_skip_decimal():
    text = "The value is 3.14 in the formula. Next sentence."
    assert extract_first_sentence(text) == "The value is 3.14 in the formula."


def test_skip_ellipsis():
    text = "He thought... then acted. Done."
    assert extract_first_sentence(text) == "He thought... then acted."


def test_no_boundary_returns_full():
    text = "No punctuation here at all"
    assert extract_first_sentence(text) == text


def test_empty_string():
    assert extract_first_sentence("") == ""


def test_mixed_hebrew_english():
    text = "Transformer לדומה תא ונחב. אבה בלשה."
    result = extract_first_sentence(text)
    assert result == "Transformer לדומה תא ונחב."


def test_single_sentence_with_period():
    assert extract_first_sentence("Only one sentence.") == "Only one sentence."
