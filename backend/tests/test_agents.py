import pytest

from app.agents.graph import build_graph
from app.agents.hallucination import score_hallucination
from app.agents.router import route_query


@pytest.mark.asyncio
async def test_router_correctly_classifies_sample_queries(monkeypatch):
    monkeypatch.setattr("app.agents.router.get_settings", lambda: type("Settings", (), {"openai_api_key": ""})())
    assert await route_query("Does warfarin interact with amiodarone?") == "drug_interaction"
    assert await route_query("What are the diagnostic criteria for diabetes?") == "guideline_lookup"
    assert await route_query("Can you help with my stock portfolio?") == "out_of_scope"


@pytest.mark.asyncio
async def test_full_graph_runs_end_to_end_with_mock_retriever(monkeypatch):
    async def fake_route(query):
        return "clinical_fact"

    async def fake_retrieve(query):
        docs = [{"pmid": "123", "title": "Test", "chunk_text": "Aspirin is an antiplatelet.", "source_url": "url"}]
        return docs, "PMID: 123\nText: Aspirin is an antiplatelet."

    async def fake_generate(query, context, history=None):
        return "Aspirin is described as an antiplatelet in PMID 123."

    class FakeMemory:
        async def get_history(self, session_id):
            return []

        async def append_turn(self, session_id, role, content):
            return None

        async def close(self):
            return None

    monkeypatch.setattr("app.agents.graph.route_query", fake_route)
    monkeypatch.setattr("app.agents.graph.retrieve_context", fake_retrieve)
    monkeypatch.setattr("app.agents.graph.generate_answer", fake_generate)
    monkeypatch.setattr("app.agents.graph.RedisConversationMemory", FakeMemory)
    monkeypatch.setattr("app.agents.graph.score_hallucination", lambda answer, context: 0.0)

    result = await build_graph().ainvoke({"query": "What is aspirin?", "session_id": "test", "retry_count": 0})
    assert result["answer"].endswith("PMID 123.")
    assert result["hallucination_score"] == 0.0


def test_hallucination_scorer_returns_float_between_zero_and_one():
    score = score_hallucination(
        "Aspirin is an antiplatelet.",
        "Aspirin is an antiplatelet medication.",
        load_model=False,
    )
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0
