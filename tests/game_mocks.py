"""Shared mock LLM functions for game simulation tests."""

import json
import re


def _mock_hint(client, paragraph, vs=None):
    """Deterministic hint generation."""
    return {
        "book_hint": "Topic related to academic concepts in course material",
        "association_word": "concept",
        "association_domain": "academia",
    }


def _mock_answers_llm(raw_prompt):
    if "QUESTIONS:" in raw_prompt:
        return json.dumps([{"question_number": i, "answer": "A"} for i in range(1, 21)])
    return "[]"


def _mock_questions_llm(raw_prompt):
    if "Generate exactly 20" in raw_prompt:
        return json.dumps([
            {"question_number": i, "question_text": f"Is this about topic {i}?",
             "options": {"A": "Yes", "B": "No", "C": "Partially", "D": "N/A"}}
            for i in range(1, 21)
        ])
    return "[]"


def _mock_guess_llm(raw_prompt):
    match = re.search(r'Candidate 1 \(opening: "([^"]+)"\)', raw_prompt)
    sentence = match.group(1) if match else "Unknown sentence."
    return json.dumps({
        "chosen_candidate": 1,
        "opening_sentence": sentence,
        "sentence_justification": "Based on semantic search ranking and Q&A evidence, "
            "candidate 1 was the strongest match for the given hint and domain.",
        "associative_word": "concept",
        "word_justification": "Central concept from the paragraph's academic domain.",
        "confidence": 0.7,
    })


def _mock_score_llm(raw_prompt):
    return json.dumps({
        "opening_sentence_score": 50,
        "sentence_justification_score": 60,
        "associative_word_score": 40,
        "word_justification_score": 50,
        "feedback_sentence": "Your guess showed understanding of the topic. " * 10,
        "feedback_word": "The association word was in the right domain. " * 10,
    })


def _route_llm_call(prompt, max_tokens=2048):
    """Route to appropriate mock based on prompt content."""
    if "QUESTIONS:" in prompt and "PARAGRAPH TEXT:" in prompt:
        return _mock_answers_llm(prompt)
    if "Generate exactly 20" in prompt:
        return _mock_questions_llm(prompt)
    if "Q&A EVIDENCE:" in prompt:
        return _mock_guess_llm(prompt)
    if "Score each component" in prompt:
        return _mock_score_llm(prompt)
    return "{}"
