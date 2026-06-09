from __future__ import annotations

import re
from statistics import mean

import mlflow
import numpy as np
import structlog
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import get_settings

logger = structlog.get_logger("cliniq.ingestion.chunker")


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+|[^\w\s]", text)


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def _base_text(doc: dict) -> str:
    return f"{doc.get('title', '')}. {doc.get('abstract', '')}".strip()


def _metadata(doc: dict, chunk_text: str, index: int, strategy: str) -> dict:
    return {
        "pmid": doc.get("pmid", ""),
        "title": doc.get("title", ""),
        "authors": doc.get("authors", []),
        "publication_date": doc.get("publication_date", ""),
        "mesh_terms": doc.get("mesh_terms", []),
        "source_url": doc.get("source_url", ""),
        "chunk_text": chunk_text,
        "chunk_index": index,
        "chunk_strategy": strategy,
    }


def fixed_size_chunks(documents: list[dict], size: int = 512, overlap: int = 50) -> list[dict]:
    chunks = []
    step = size - overlap
    for doc in documents:
        tokens = _tokens(_base_text(doc))
        for index, start in enumerate(range(0, len(tokens), step)):
            text = " ".join(tokens[start : start + size]).strip()
            if text:
                chunks.append(_metadata(doc, text, index, "fixed_size"))
    return chunks


def sentence_boundary_chunks(documents: list[dict], target_tokens: int = 512) -> list[dict]:
    chunks = []
    for doc in documents:
        current: list[str] = []
        current_len = 0
        chunk_index = 0
        for sentence in _sentences(_base_text(doc)):
            length = len(_tokens(sentence))
            if current and current_len + length > target_tokens:
                chunks.append(_metadata(doc, " ".join(current), chunk_index, "sentence_boundary"))
                chunk_index += 1
                current = []
                current_len = 0
            current.append(sentence)
            current_len += length
        if current:
            chunks.append(_metadata(doc, " ".join(current), chunk_index, "sentence_boundary"))
    return chunks


def semantic_chunks(
    documents: list[dict],
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    similarity_threshold: float = 0.72,
) -> list[dict]:
    model = SentenceTransformer(model_name)
    chunks = []
    for doc in documents:
        sentences = _sentences(_base_text(doc))
        if not sentences:
            continue
        embeddings = model.encode(sentences, normalize_embeddings=True)
        groups: list[list[str]] = [[sentences[0]]]
        for idx in range(1, len(sentences)):
            sim = cosine_similarity([embeddings[idx - 1]], [embeddings[idx]])[0][0]
            if sim >= similarity_threshold:
                groups[-1].append(sentences[idx])
            else:
                groups.append([sentences[idx]])
        for chunk_index, group in enumerate(groups):
            chunks.append(_metadata(doc, " ".join(group), chunk_index, "semantic"))
    return chunks


def _log_strategy(strategy: str, chunks: list[dict]) -> None:
    lengths = [len(_tokens(chunk["chunk_text"])) for chunk in chunks] or [0]
    metrics = {
        f"{strategy}_chunk_count": len(chunks),
        f"{strategy}_avg_tokens": float(mean(lengths)),
        f"{strategy}_p95_tokens": float(np.percentile(lengths, 95)),
    }
    try:
        mlflow.set_tracking_uri(get_settings().mlflow_tracking_uri)
        with mlflow.start_run(run_name=f"chunking_{strategy}", nested=True):
            mlflow.log_metrics(metrics)
    except Exception as exc:
        logger.warning("mlflow_chunk_log_failed", strategy=strategy, error=str(exc))
    logger.info("chunking_strategy_metrics", strategy=strategy, **metrics)


def chunk_documents(documents: list[dict], strategy: str = "sentence_boundary") -> list[dict]:
    strategies = {
        "fixed_size": fixed_size_chunks,
        "sentence_boundary": sentence_boundary_chunks,
        "semantic": semantic_chunks,
    }
    if strategy == "compare":
        results = {name: fn(documents) for name, fn in strategies.items()}
        for name, chunks in results.items():
            _log_strategy(name, chunks)
        return results["sentence_boundary"]
    chunks = strategies[strategy](documents)
    _log_strategy(strategy, chunks)
    return chunks
