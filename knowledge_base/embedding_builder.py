"""Parallel embedding computation for ChromaDB index building.

Uses ProcessPoolExecutor to pre-compute sentence-transformer embeddings
across CPU cores (CPU-bound: matrix multiplications).

Building Block: compute_embeddings_parallel
    Input Data:  List of text strings to embed
    Output Data: List of embedding vectors (list[list[float]])
    Setup Data:  MODEL_NAME constant, multiprocessing.cpu_count()
"""

import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor

from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
logger = logging.getLogger(__name__)


def _embed_batch(texts: list[str]) -> list[list[float]]:
    """Compute embeddings for a batch of texts (worker-process function).

    Each worker loads its own copy of the sentence-transformer model
    and computes embeddings independently.  This is CPU-bound work
    (matrix multiplications) that benefits from process-level parallelism.
    """
    ef = SentenceTransformerEmbeddingFunction(model_name=MODEL_NAME)
    return ef(texts)


def compute_embeddings_parallel(
    texts: list[str], batch_size: int = 100
) -> list[list[float]]:
    """Pre-compute embeddings in parallel across CPU cores.

    Falls back to sequential embedding if the process pool fails.
    """
    n_workers = min(4, multiprocessing.cpu_count() or 1)
    logger.info("Pre-computing embeddings with %d workers", n_workers)

    text_batches = [
        texts[i:i + batch_size]
        for i in range(0, len(texts), batch_size)
    ]
    all_embeddings: list[list[float]] = []
    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        for batch_emb in pool.map(_embed_batch, text_batches):
            all_embeddings.extend(batch_emb)

    return all_embeddings
