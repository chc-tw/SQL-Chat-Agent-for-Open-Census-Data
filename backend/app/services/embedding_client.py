from __future__ import annotations

from typing import Iterable, List, Sequence

from openai import OpenAI

from app.settings import openai_settings

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-large"
DEFAULT_BATCH_SIZE = 32

client = OpenAI(api_key=openai_settings.api_key)


def embed_texts(
    texts: Sequence[str],
    model: str = DEFAULT_EMBEDDING_MODEL,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> List[List[float]]:
    if not texts:
        return []
    if batch_size <= 0:
        raise ValueError("batch size must be positive")

    vectors: List[List[float]] = []
    for batch in _batch(texts, batch_size):
        response = client.embeddings.create(
            model=model,
            input=batch,
        )
        vectors.extend([item.embedding for item in response.data])
    return vectors


def embed_text(
    text: str,
    model: str = DEFAULT_EMBEDDING_MODEL,
) -> List[float]:
    return embed_texts([text], model=model)[0]


def _batch(items: Sequence[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(items), size):
        yield list(items[i : i + size])
