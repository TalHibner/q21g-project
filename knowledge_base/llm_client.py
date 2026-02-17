"""Shared LLM client with retry on transient errors."""

import logging
import time

import anthropic

MODEL = "claude-sonnet-4-20250514"
logger = logging.getLogger(__name__)

_RETRYABLE = (
    anthropic.APITimeoutError,
    anthropic.RateLimitError,
    anthropic.APIConnectionError,
    anthropic.InternalServerError,
)


def call_llm(client: anthropic.Anthropic, prompt: str, max_tokens: int = 1024,
             timeout: float = 30.0, retries: int = 2) -> str:
    """LLM call with retry on timeout/rate-limit/connection errors.

    Raises the original exception after exhausting retries.
    Raises AuthenticationError immediately (no retry).
    """
    for attempt in range(retries + 1):
        try:
            resp = client.with_options(timeout=timeout).messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text
        except _RETRYABLE as e:
            if attempt == retries:
                logger.error("LLM failed after %d retries: %s", retries, e)
                raise
            wait = 2 ** attempt  # 1s, 2s
            logger.warning("LLM retry %d/%d after %s (wait %ds)",
                           attempt + 1, retries, type(e).__name__, wait)
            time.sleep(wait)
        except anthropic.AuthenticationError:
            logger.error("Invalid API key — check ANTHROPIC_API_KEY")
            raise
    raise anthropic.APIError("Exhausted retries")
