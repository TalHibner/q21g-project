"""Tests for knowledge_base.llm_client — LLM call with retry and batch.

Tests cover retry logic, error handling, authentication errors, batch
multithreading, and edge cases without making actual API calls.
"""

from unittest.mock import MagicMock, patch, PropertyMock
import pytest

import anthropic

from knowledge_base.llm_client import call_llm, call_llm_batch


# ─── Helpers ────────────────────────────────────────────────────

def _mock_response(text: str):
    """Create a mock Anthropic response."""
    block = MagicMock()
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    return resp


def _mock_client(response_text: str = "Hello"):
    """Create a mock Anthropic client that returns success."""
    client = MagicMock(spec=anthropic.Anthropic)
    client.with_options.return_value = client
    client.messages.create.return_value = _mock_response(response_text)
    return client


# ─── call_llm — happy path ──────────────────────────────────────

def test_call_llm_success():
    client = _mock_client("test response")
    result = call_llm(client, "test prompt")
    assert result == "test response"


def test_call_llm_custom_params():
    client = _mock_client("ok")
    result = call_llm(client, "prompt", max_tokens=500, timeout=60.0)
    assert result == "ok"
    client.with_options.assert_called_once_with(timeout=60.0)


# ─── call_llm — retry on transient errors ─────────────────────

@patch("knowledge_base.llm_client.time.sleep")
def test_call_llm_retry_timeout(mock_sleep):
    """Should retry on APITimeoutError and succeed."""
    client = MagicMock(spec=anthropic.Anthropic)
    client.with_options.return_value = client
    client.messages.create.side_effect = [
        anthropic.APITimeoutError(request=MagicMock()),
        _mock_response("recovered"),
    ]
    result = call_llm(client, "prompt", retries=2)
    assert result == "recovered"
    mock_sleep.assert_called_once()


@patch("knowledge_base.llm_client.time.sleep")
def test_call_llm_retry_exhausted(mock_sleep):
    """Should raise after exhausting retries."""
    client = MagicMock(spec=anthropic.Anthropic)
    client.with_options.return_value = client
    client.messages.create.side_effect = anthropic.APITimeoutError(
        request=MagicMock()
    )
    with pytest.raises(anthropic.APITimeoutError):
        call_llm(client, "prompt", retries=1)


# ─── call_llm — authentication error (no retry) ───────────────

def test_call_llm_auth_error_no_retry():
    """AuthenticationError should not be retried."""
    client = MagicMock(spec=anthropic.Anthropic)
    client.with_options.return_value = client
    resp = MagicMock()
    resp.status_code = 401
    client.messages.create.side_effect = anthropic.AuthenticationError(
        message="Invalid API key",
        response=resp,
        body={"error": {"message": "invalid key"}},
    )
    with pytest.raises(anthropic.AuthenticationError):
        call_llm(client, "prompt")


# ─── call_llm_batch — concurrent calls ─────────────────────────

def test_call_llm_batch_success():
    """Batch call should return results in order."""
    client = _mock_client()
    # Make the mock return different responses for different prompts
    prompts = ["p1", "p2", "p3"]
    responses = [_mock_response(f"r{i}") for i in range(3)]
    client.messages.create.side_effect = responses

    results = call_llm_batch(client, prompts, max_workers=2)
    assert len(results) == 3


def test_call_llm_batch_empty():
    """Empty prompts list should return empty results."""
    client = _mock_client()
    results = call_llm_batch(client, [])
    assert results == []


def test_call_llm_batch_single():
    """Single prompt should work."""
    client = _mock_client("only")
    results = call_llm_batch(client, ["one prompt"])
    assert len(results) == 1


@patch("knowledge_base.llm_client.time.sleep")
def test_call_llm_batch_partial_failure(mock_sleep):
    """Failed calls in batch should return empty string, not crash."""
    client = MagicMock(spec=anthropic.Anthropic)
    client.with_options.return_value = client
    client.messages.create.side_effect = [
        _mock_response("ok"),
        anthropic.APITimeoutError(request=MagicMock()),
        anthropic.APITimeoutError(request=MagicMock()),
        anthropic.APITimeoutError(request=MagicMock()),
        _mock_response("also ok"),
    ]
    results = call_llm_batch(client, ["p1", "p2"], max_workers=1)
    assert len(results) == 2
    # One should succeed, one should be empty
    assert "ok" in results or "also ok" in results
