from __future__ import annotations

from functools import lru_cache

import structlog
from sentence_transformers import CrossEncoder

from app.config import get_settings

logger = structlog.get_logger("cliniq.retrieval.reranker")


@lru_cache(maxsize=1)
def load_cross_encoder() -> CrossEncoder:
    settings = get_settings()
    logger.info("reranker_loading", model=settings.reranker_model)
    return CrossEncoder(settings.reranker_model)


class CrossEncoderReranker:
    def __init__(self, model: CrossEncoder | None = None, load_model: bool = True):
        self.model = model if model is not None else (load_cross_encoder() if load_model else None)

    def rerank(self, query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
        if not candidates:
            return []
        if self.model is None:
            ranked = sorted(candidates, key=lambda item: item.get("fusion_score", 0.0), reverse=True)
            return ranked[:top_k]
        pairs = [(query, item.get("chunk_text", "")) for item in candidates]
        scores = self.model.predict(pairs)
        ranked = [
            {**candidate, "rerank_score": float(score)}
            for candidate, score in zip(candidates, scores, strict=True)
        ]
        ranked.sort(key=lambda item: item["rerank_score"], reverse=True)
        logger.info(
            "rerank_complete",
            candidate_count=len(candidates),
            returned=min(top_k, len(candidates)),
            top_score=ranked[0]["rerank_score"] if ranked else None,
        )
        return ranked[:top_k]


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoderReranker:
    return CrossEncoderReranker()
