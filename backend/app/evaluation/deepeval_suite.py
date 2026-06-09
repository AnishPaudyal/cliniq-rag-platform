from __future__ import annotations

import json
from pathlib import Path

import mlflow
from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric, ContextualPrecisionMetric, HallucinationMetric
from deepeval.test_case import LLMTestCase

from app.config import get_settings


def load_cases(path: str = "data/eval_questions.json") -> list[LLMTestCase]:
    source = Path(path)
    if not source.exists():
        raise RuntimeError("Evaluation dataset missing. Run ragas_eval.py first.")
    data = json.loads(source.read_text(encoding="utf-8"))
    return [
        LLMTestCase(
            input=item["question"],
            actual_output=item.get("ground_truth", ""),
            expected_output=item.get("ground_truth", ""),
            retrieval_context=[item.get("context", "")],
        )
        for item in data
    ]


def run_deepeval_suite(path: str = "data/eval_questions.json") -> dict:
    settings = get_settings()
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    metrics = [
        HallucinationMetric(threshold=0.4),
        AnswerRelevancyMetric(threshold=0.7),
        ContextualPrecisionMetric(threshold=0.7),
    ]
    cases = load_cases(path)
    with mlflow.start_run(run_name="cliniq_deepeval_suite"):
        result = evaluate(cases, metrics)
        summary = {"case_count": len(cases), "passed": getattr(result, "passed", None)}
        mlflow.log_param("deepeval_case_count", len(cases))
        for metric in metrics:
            score = getattr(metric, "score", None)
            if score is not None:
                mlflow.log_metric(metric.__class__.__name__, float(score))
        return summary


if __name__ == "__main__":
    print(run_deepeval_suite())
