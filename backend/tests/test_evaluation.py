from app.evaluation.hallucination_scorer import score


def test_standalone_hallucination_scorer_returns_score(monkeypatch):
    monkeypatch.setattr("app.evaluation.hallucination_scorer.score_hallucination", lambda answer, context: 0.25)
    assert score("query", "answer", "context") == 0.25
