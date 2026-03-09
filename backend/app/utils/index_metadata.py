from __future__ import annotations

import csv
from pathlib import Path
from typing import cast

from chromadb.api.types import Embedding, Metadata
from tqdm import tqdm

from app.services.chromadb_client import chroma_client
from app.services.embedding_client import embed_texts


def index_metadata_csv(csv_path: Path) -> str:
    """
    Ingest a metadata CSV into its own collection.
    Each row becomes: "Feature Topic {topic} on the population of {universe}"
    """
    csv_path = csv_path.resolve()
    collection_name = f"{csv_path.stem.lower().replace(' ', '_')}"
    collection = chroma_client.get_or_create_collection(name=collection_name)

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[Metadata] = []

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(tqdm(reader, desc=f"Rows in {csv_path.name}")):
            topic = (
                row.get("TABLE_TITLE")
                or row.get("COLUMN_TOPIC")
                or row.get("COLUMN_NAME")
                or row.get("topic")
                or row.get("Topic")
                or ""
            ).strip()
            universe = (
                row.get("TABLE_UNIVERSE")
                or row.get("COLUMN_UNIVERSE")
                or row.get("universe")
                or row.get("Universe")
                or ("SafeGraph CBG mobility patterns" if row.get("COLUMN_NAME") else "")
            ).strip()
            if not topic or not universe:
                continue

            documents.append(f"Feature Topic {topic} on the population of {universe}")
            ids.append(f"{csv_path.stem}-{idx}")
            metadatas.append(
                {
                    "topic": topic,
                    "universe": universe,
                    "source_file": csv_path.name,
                }
            )

    if documents:
        embeddings = cast(list[Embedding], embed_texts(documents))
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    return collection_name


def index_metadata_csvs(csv_paths: list[Path]) -> list[str]:
    return [index_metadata_csv(path) for path in tqdm(csv_paths, desc="CSV files")]


if __name__ == "__main__":
    metadata_dir = Path(__file__).resolve().parents[3] / "Dataset" / "FEATURE_OPTION_TABLE"
    csv_paths = sorted(metadata_dir.glob("*.csv"))
    if not csv_paths:
        raise FileNotFoundError(f"No CSV files found in {metadata_dir}")

    collection_names = index_metadata_csvs(csv_paths)
    print("Indexed collections:")
    for name in collection_names:
        print(f"- {name}")
