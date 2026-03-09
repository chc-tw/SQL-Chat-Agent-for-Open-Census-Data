from __future__ import annotations

from pathlib import Path
from typing import Sequence

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.api.types import Embedding, Metadata

PERSIST_DIR = Path(__file__).resolve().parents[2] / "chroma_db"
PERSIST_DIR.mkdir(parents=True, exist_ok=True)
chroma_client = chromadb.PersistentClient(path=str(PERSIST_DIR))


def get_or_create_collection(name: str) -> Collection:
    return chroma_client.get_or_create_collection(name=name)


def upsert_documents(
    collection: Collection,
    ids: Sequence[str],
    embeddings: Sequence[Embedding],
    documents: Sequence[str],
    metadatas: Sequence[Metadata] | None = None,
) -> None:
    collection.upsert(
        ids=list(ids),
        embeddings=list(embeddings),
        documents=list(documents),
        metadatas=list(metadatas) if metadatas else None,
    )
