from uuid import uuid5, NAMESPACE_URL

import structlog
from openai import AsyncOpenAI
from qdrant_client.http import models
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.retrieval.qdrant_client import ensure_collection, get_qdrant_client

logger = structlog.get_logger("cliniq.ingestion.embedder")


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5))
async def _embed_batch(client: AsyncOpenAI, texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    response = await client.embeddings.create(model=settings.embedding_model, input=texts)
    return [item.embedding for item in response.data]


async def embed_and_store(chunks: list[dict], batch_size: int = 64) -> int:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required to embed PubMed chunks.")
    ensure_collection(vector_size=1536)
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    qdrant = get_qdrant_client()
    stored = 0
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        embeddings = await _embed_batch(openai_client, [chunk["chunk_text"] for chunk in batch])
        points = [
            models.PointStruct(
                id=str(uuid5(NAMESPACE_URL, f"{chunk['pmid']}:{chunk['chunk_index']}:{chunk['chunk_strategy']}")),
                vector=embedding,
                payload=chunk,
            )
            for chunk, embedding in zip(batch, embeddings, strict=True)
        ]
        qdrant.upsert(collection_name=settings.qdrant_collection, points=points)
        stored += len(points)
        logger.info("qdrant_chunks_upserted", stored=stored, total=len(chunks))
    return stored
