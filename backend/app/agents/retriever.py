from __future__ import annotations

from app.retrieval.hybrid_search import hybrid_search
from app.retrieval.reranker import get_reranker


def format_context(docs: list[dict]) -> str:
    blocks = []
    for idx, doc in enumerate(docs, start=1):
        authors = ", ".join(doc.get("authors", [])[:3])
        blocks.append(
            "\n".join(
                [
                    f"[Source {idx}]",
                    f"PMID: {doc.get('pmid', 'unknown')}",
                    f"Title: {doc.get('title', 'unknown')}",
                    f"Authors: {authors or 'unknown'}",
                    f"URL: {doc.get('source_url', '')}",
                    f"Relevance: {doc.get('rerank_score', doc.get('fusion_score', 0.0))}",
                    f"Text: {doc.get('chunk_text', '')}",
                ]
            )
        )
    return "\n\n".join(blocks)


async def retrieve_context(query: str) -> tuple[list[dict], str]:
    candidates = await hybrid_search(query, top_k=10)
    docs = get_reranker().rerank(query, candidates, top_k=5)
    return docs, format_context(docs)
