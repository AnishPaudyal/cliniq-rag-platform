class CrossEncoderReranker:
    def rerank(self, query: str, candidates: list[dict], top_k: int = 5):
        raise NotImplementedError("Reranking is implemented in Phase 3.")
