"""Shared LLM client with retry on transient errors.

Provides both single-call and batch (multithreaded) interfaces.
Batch calls use ThreadPoolExecutor for concurrent I/O-bound API requests.

Building Block: call_llm / call_llm_batch
    Input Data:  anthropic.Anthropic client, prompt string(s), max_tokens, timeout
    Output Data: LLM response text string(s)
    Setup Data:  ANTHROPIC_API_KEY env var, claude-sonnet-4-20250514 model
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

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


def call_llm_batch(
    client: anthropic.Anthropic,
    prompts: list[str],
    max_tokens: int = 1024,
    timeout: float = 30.0,
    max_workers: int = 5,
) -> list[str]:
    """Concurrent LLM calls using multithreading (I/O-bound).

    Each prompt is sent to the API in a separate thread. Since LLM
    calls are I/O-bound (network wait), threads release the GIL and
    run concurrently.

    Returns list of responses in input order. Failed calls return "".
    """
    if not prompts:
        return []

    results: dict[int, str] = {}

    def _call_one(idx: int, prompt: str) -> tuple[int, str]:
        try:
            return idx, call_llm(client, prompt, max_tokens, timeout)
        except Exception as exc:
            logger.error("Batch LLM call %d failed: %s", idx, exc)
            return idx, ""

    logger.info("Sending %d LLM calls with %d threads",
                len(prompts), max_workers)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_call_one, i, p): i
            for i, p in enumerate(prompts)
        }
        for future in as_completed(futures):
            idx, text = future.result()
            results[idx] = text

    return [results[i] for i in range(len(prompts))]

