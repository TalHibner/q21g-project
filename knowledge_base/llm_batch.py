"""Batch/concurrent LLM utilities using multithreading.

Provides call_llm_batch for concurrent I/O-bound API requests via
ThreadPoolExecutor.  This module extends llm_client.py with batch
capabilities while keeping the single-call interface unchanged.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic

from knowledge_base.llm_client import call_llm

logger = logging.getLogger(__name__)


def call_llm_batch(
    client: anthropic.Anthropic,
    prompts: list[str],
    max_tokens: int = 1024,
    timeout: float = 30.0,
    max_workers: int = 5,
) -> list[str]:
    """Concurrent LLM calls using multithreading (I/O-bound).

    Each prompt is sent to the API in a separate thread.  Since LLM
    calls are I/O-bound (network wait), Python threads release the GIL
    and run concurrently — ideal for batch question answering where
    the referee needs to answer 20 questions or the player needs to
    evaluate multiple candidates simultaneously.

    Args:
        client: Anthropic API client.
        prompts: List of prompt strings.
        max_tokens: Max tokens per response.
        timeout: Timeout per individual call.
        max_workers: Maximum concurrent threads (default 5 to respect
                     rate limits).

    Returns:
        List of response strings, in the same order as the input
        prompts.  Failed calls return an empty string.
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

    logger.info("Sending %d LLM calls with %d threads", len(prompts), max_workers)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_call_one, i, p): i
            for i, p in enumerate(prompts)
        }
        for future in as_completed(futures):
            idx, text = future.result()
            results[idx] = text

    return [results[i] for i in range(len(prompts))]
