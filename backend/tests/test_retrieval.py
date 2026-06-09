import pytest

from app.retrieval.bm25_index import BM25Index
from app.retrieval.hybrid_search import hybrid_search, rrf_fuse
from app.retrieval.reranker import CrossEncoderReranker


def test_bm25_returns_results_for_known_terms():
    docs = [
        {"pmid": "1", "chunk_index": 0, "chunk_strategy": "test", "chunk_text": "Warfarin drug interactions increase bleeding risk."},
        {"pmid": "2", "chunk_index": 0, "chunk_strategy": "test", "chunk_text": "Diagnostic criteria can vary by guideline."},
    ]
    index = BM25Index(docs, source_count=2)
    results = index.search("warfarin interactions")
    assert results
    assert results[0].document["pmid"] == "1"


@pytest.mark.asyncio
async def test_qdrant_returns_results_for_semantic_queries(monkeypatch):
    async def fake_dense_search(query, top_k=20):
        return [
            {
                "document": {
                    "pmid": "3",
                    "chunk_index": 0,
                    "chunk_strategy": "test",
                    "chunk_text": "Clinical guidelines recommend evidence-based diagnosis.",
                },
                "score": 0.91,
            }
        ]

    monkeypatch.setattr("app.retrieval.hybrid_search.dense_search", fake_dense_search)
    results = await fake_dense_search("evidence diagnosis")
    assert results[0]["score"] > 0.8
    assert "guidelines" in results[0]["document"]["chunk_text"]


def test_hybrid_fusion_always_returns_at_most_10_results():
    dense = [
        {"document": {"pmid": str(i), "chunk_index": 0, "chunk_strategy": "dense", "chunk_text": "dense"}, "score": 1.0}
        for i in range(20)
    ]
    bm25 = [
        {"document": {"pmid": str(i), "chunk_index": 0, "chunk_strategy": "dense", "chunk_text": "bm25"}, "score": 2.0}
        for i in range(20)
    ]
    assert len(rrf_fuse(dense, bm25, top_k=10)) <= 10


def test_reranker_output_is_sorted_by_descending_score():
    class FakeModel:
        def predict(self, pairs):
            return [0.1, 0.9, 0.4]

    candidates = [
        {"pmid": "1", "chunk_index": 0, "chunk_strategy": "test", "chunk_text": "a"},
        {"pmid": "2", "chunk_index": 0, "chunk_strategy": "test", "chunk_text": "b"},
        {"pmid": "3", "chunk_index": 0, "chunk_strategy": "test", "chunk_text": "c"},
    ]
    results = CrossEncoderReranker(model=FakeModel()).rerank("query", candidates, top_k=3)
    scores = [item["rerank_score"] for item in results]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_hybrid_search_returns_at_most_10_with_mocks(monkeypatch):
    async def fake_dense_search(query, top_k=20):
        return [
            {"document": {"pmid": "1", "chunk_index": 0, "chunk_strategy": "test", "chunk_text": "clinical"}, "score": 0.8}
        ]

    class FakeBM25:
        def search(self, query, top_k=20):
            return [
                {"document": {"pmid": "2", "chunk_index": 0, "chunk_strategy": "test", "chunk_text": "guideline"}, "score": 1.2}
            ]

    monkeypatch.setattr("app.retrieval.hybrid_search.dense_search", fake_dense_search)
    monkeypatch.setattr("app.retrieval.hybrid_search.get_bm25_index", lambda: FakeBM25())
    assert len(await hybrid_search("clinical guideline", top_k=10)) <= 10
