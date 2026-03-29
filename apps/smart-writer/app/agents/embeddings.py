"""OpenAI text embeddings for canonical library matching (design §5.1–5.2).

Vectors are **L2-normalized** after fetch so cosine similarity equals dot product in [-1, 1]
(see ``cosine_similarity``).
"""

from __future__ import annotations

import math
import os
from typing import Literal

import logfire
from openai import OpenAI

EmbeddingFailurePolicy = Literal["skip_library", "fail_run"]

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_EMBEDDING_BATCH = 16
DEFAULT_EMBEDDING_TIMEOUT_SEC = 60.0


def get_embedding_model_id() -> str:
    """``SMART_WRITER_EMBEDDING_MODEL`` — must match corpus ``embedding_model_id`` (§4.2)."""
    raw = os.getenv("SMART_WRITER_EMBEDDING_MODEL")
    if raw is None or not str(raw).strip():
        return DEFAULT_EMBEDDING_MODEL
    return str(raw).strip()


def get_embedding_batch_size() -> int:
    """``SMART_WRITER_EMBEDDING_BATCH_SIZE`` — chunk size for ``embed_texts`` (OpenAI allows large batches)."""
    raw = os.getenv("SMART_WRITER_EMBEDDING_BATCH_SIZE", str(DEFAULT_EMBEDDING_BATCH))
    try:
        n = int(str(raw).strip(), 10)
    except ValueError:
        return DEFAULT_EMBEDDING_BATCH
    return max(1, min(n, 256))


def get_embedding_timeout_sec() -> float:
    """``SMART_WRITER_EMBEDDING_TIMEOUT_SEC`` — per HTTP call to the embeddings API."""
    raw = os.getenv("SMART_WRITER_EMBEDDING_TIMEOUT_SEC", str(DEFAULT_EMBEDDING_TIMEOUT_SEC))
    try:
        v = float(str(raw).strip())
    except ValueError:
        return DEFAULT_EMBEDDING_TIMEOUT_SEC
    return max(5.0, min(v, 600.0))


def get_embedding_failure_policy() -> EmbeddingFailurePolicy:
    """``SMART_WRITER_EMBEDDING_ON_FAILURE`` — ``skip_library`` (k=0, log) or ``fail_run``."""
    raw = (os.getenv("SMART_WRITER_EMBEDDING_ON_FAILURE") or "skip_library").strip().lower()
    if raw in ("fail", "fail_run", "error", "raise"):
        return "fail_run"
    return "skip_library"


def l2_normalize(vector: list[float]) -> list[float]:
    s = math.sqrt(sum(x * x for x in vector))
    if s <= 0:
        return vector
    return [x / s for x in vector]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Dot product of L2-normalized vectors (range [-1, 1])."""
    if len(a) != len(b):
        raise ValueError("Vectors must have the same length.")
    return sum(x * y for x, y in zip(a, b, strict=True))


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed strings using OpenAI; returns **L2-normalized** vectors (one per input, same order).

    Batches according to ``get_embedding_batch_size()``. Requires ``OPENAI_API_KEY``.
    """
    if not texts:
        return []
    model = get_embedding_model_id()
    timeout = get_embedding_timeout_sec()
    client = OpenAI(timeout=timeout)
    bs = get_embedding_batch_size()
    out: list[list[float]] = []
    for i in range(0, len(texts), bs):
        batch = texts[i : i + bs]
        with logfire.span("openai.embeddings.create", model=model, batch=len(batch)):
            resp = client.embeddings.create(model=model, input=batch)
        # API returns sorted by index
        indexed = sorted(resp.data, key=lambda d: d.index)
        for item in indexed:
            out.append(l2_normalize(list(item.embedding)))
    if len(out) != len(texts):
        raise RuntimeError(f"Embedding count mismatch: expected {len(texts)}, got {len(out)}")
    return out
