from __future__ import annotations

import pickle
import re
from dataclasses import dataclass
from pathlib import Path

import structlog
from rank_bm25 import BM25Okapi

from app.config import get_settings
from app.retrieval.qdrant_client import collection_count, get_qdrant_client

logger = structlog.get_logger("cliniq.retrieval.bm25")


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


@dataclass
class BM25SearchResult:
    document: dict
    score: float
    rank: int


class BM25Index:
    def __init__(self, documents: list[dict], source_count: int):
        self.documents = documents
        self.source_count = source_count
        self._tokenized = [tokenize(doc.get("chunk_text", "")) for doc in documents]
        self._index = BM25Okapi(self._tokenized) if self._tokenized else None

    def search(self, query: str, top_k: int = 20) -> list[BM25SearchResult]:
        if not self._index or not self.documents:
            return []
        scores = self._index.get_scores(tokenize(query))
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)[:top_k]
        return [
            BM25SearchResult(document=self.documents[idx], score=float(score), rank=rank + 1)
            for rank, (idx, score) in enumerate(ranked)
            if score > 0
        ]

    def save(self, path: str | Path | None = None) -> None:
        target = Path(path or get_settings().bm25_index_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            pickle.dump(self, handle)

    @classmethod
    def load(cls, path: str | Path | None = None) -> "BM25Index | None":
        target = Path(path or get_settings().bm25_index_path)
        if not target.exists():
            return None
        with target.open("rb") as handle:
            index: BM25Index = pickle.load(handle)
        current_count = collection_count()
        if index.source_count != current_count:
            logger.info("bm25_index_stale", saved_count=index.source_count, current_count=current_count)
            return None
        return index


def load_chunks_from_qdrant(limit: int = 10000) -> list[dict]:
    settings = get_settings()
    client = get_qdrant_client()
    documents: list[dict] = []
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=settings.qdrant_collection,
            limit=min(limit, 256),
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        documents.extend(point.payload for point in points if point.payload)
        if offset is None or len(documents) >= limit:
            break
    return documents


def build_bm25_from_qdrant() -> BM25Index:
    docs = load_chunks_from_qdrant()
    index = BM25Index(docs, source_count=collection_count())
    index.save()
    logger.info("bm25_index_built", documents=len(docs))
    return index


def get_bm25_index() -> BM25Index:
    return BM25Index.load() or build_bm25_from_qdrant()
