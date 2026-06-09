from __future__ import annotations

import asyncio
import json
from pathlib import Path

import mlflow
import structlog
from datasets import Dataset
from openai import AsyncOpenAI
from ragas import evaluate
from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

from app.agents.generator import generate_answer
from app.agents.retriever import retrieve_context
from app.config import get_settings
from app.retrieval.bm25_index import load_chunks_from_qdrant

logger = structlog.get_logger("cliniq.evaluation.ragas")


async def build_eval_dataset(size: int = 50, output_path: str = "data/eval_questions.json") -> list[dict]:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required to generate the evaluation dataset.")
    chunks = load_chunks_from_qdrant(limit=size)
    if not chunks:
        raise RuntimeError("No Qdrant chunks available. Run ingestion before evaluation.")
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    rows = []
    for chunk in chunks[:size]:
        prompt = f"""Create one clinical question and grounded answer from this PubMed abstract chunk.
Return JSON with keys question and ground_truth.
PMID: {chunk.get('pmid')}
Title: {chunk.get('title')}
Text: {chunk.get('chunk_text')}"""
        response = await client.chat.completions.create(
            model=settings.llm_model,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content or "{}"
        try:
            qa = json.loads(content)
        except json.JSONDecodeError:
            qa = {
                "question": f"What evidence is reported in PMID {chunk.get('pmid')}?",
                "ground_truth": chunk.get("chunk_text", ""),
            }
        rows.append({**qa, "pmid": chunk.get("pmid"), "context": chunk.get("chunk_text", "")})
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return rows


async def _answer_dataset(dataset: list[dict]) -> Dataset:
    rows = []
    for item in dataset:
        docs, context = await retrieve_context(item["question"])
        answer = await generate_answer(item["question"], context)
        rows.append(
            {
                "question": item["question"],
                "answer": answer,
                "contexts": [doc.get("chunk_text", "") for doc in docs],
                "ground_truth": item["ground_truth"],
            }
        )
    return Dataset.from_list(rows)


async def run_ragas_eval(size: int = 50) -> dict:
    settings = get_settings()
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    dataset = await build_eval_dataset(size=size)
    answered = await _answer_dataset(dataset)
    with mlflow.start_run(run_name="cliniq_ragas_eval"):
        mlflow.log_param("chunking_strategy", "sentence_boundary")
        mlflow.log_param("embedding_model", settings.embedding_model)
        mlflow.log_param("retriever_top_k", 10)
        mlflow.log_param("reranker_model", settings.reranker_model)
        result = evaluate(
            answered,
            metrics=[faithfulness, answer_relevancy, context_recall, context_precision],
        )
        scores = dict(result)
        for metric, value in scores.items():
            try:
                mlflow.log_metric(metric, float(value))
            except (TypeError, ValueError):
                logger.warning("ragas_metric_not_numeric", metric=metric, value=value)
        return scores


if __name__ == "__main__":
    print(asyncio.run(run_ragas_eval()))
