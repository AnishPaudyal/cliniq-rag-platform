from __future__ import annotations

import time
from collections import defaultdict

import structlog
from openai import AsyncOpenAI

from app.config import get_settings
from app.retrieval.bm25_index import BM25SearchResult, get_bm25_index
from app.retrieval.qdrant_client import get_qdrant_client

logger = structlog.get_logger("cliniq.retrieval.hybrid")


def _doc_id(doc: dict) -> str:
    return f"{doc.get('pmid', '')}:{doc.get('chunk_index', '')}:{doc.get('chunk_strategy', '')}"


def rrf_fuse(
    dense_results: list[dict],
    bm25_results: list[BM25SearchResult] | list[dict],
    top_k: int = 10,
    k: int = 60,
) -> list[dict]:
    scores: dict[str, float] = defaultdict(float)
    docs: dict[str, dict] = {}

    for rank, result in enumerate(dense_results, start=1):
        doc = result.get("document", result)
        key = _doc_id(doc)
        docs[key] = {**doc, "dense_score": float(result.get("score", 0.0))}
        scores[key] += 1 / (k + rank)

    for rank, result in enumerate(bm25_results, start=1):
        if isinstance(result, BM25SearchResult):
            doc = result.document
            bm25_score = result.score
        else:
            doc = result.get("document", result)
            bm25_score = result.get("score", 0.0)
        key = _doc_id(doc)
        docs.setdefault(key, doc)
        docs[key]["bm25_score"] = float(bm25_score)
        scores[key] += 1 / (k + rank)

    fused = []
    for key, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]:
        fused.append({**docs[key], "fusion_score": float(score)})
    return fused


async def _embed_query(query: str) -> list[float]:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for dense query embedding.")
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.embeddings.create(model=settings.embedding_model, input=query)
    return response.data[0].embedding


async def dense_search(query: str, top_k: int = 20) -> list[dict]:
    settings = get_settings()
    vector = await _embed_query(query)
    client = get_qdrant_client()
    points = client.search(
        collection_name=settings.qdrant_collection,
        query_vector=vector,
        limit=top_k,
        with_payload=True,
    )
    return [
        {"document": point.payload or {}, "score": float(point.score), "rank": rank + 1}
        for rank, point in enumerate(points)
    ]


async def hybrid_search(query: str, top_k: int = 10) -> list[dict]:
    started = time.perf_counter()
    dense = await dense_search(query, top_k=20)
    bm25 = get_bm25_index().search(query, top_k=20)
    fused = rrf_fuse(dense, bm25, top_k=top_k)
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(
        "hybrid_search_complete",
        query=query,
        dense_count=len(dense),
        bm25_count=len(bm25),
        fused_count=len(fused),
        latency_ms=latency_ms,
        fusion_scores=[item.get("fusion_score") for item in fused],
    )
    return fused
