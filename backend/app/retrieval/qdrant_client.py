from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.config import get_settings


def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url)


def ensure_collection(vector_size: int = 1536) -> None:
    settings = get_settings()
    client = get_qdrant_client()
    existing = {collection.name for collection in client.get_collections().collections}
    if settings.qdrant_collection in existing:
        return
    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
    )


def collection_count() -> int:
    settings = get_settings()
    client = get_qdrant_client()
    try:
        return client.count(collection_name=settings.qdrant_collection, exact=True).count
    except Exception:
        return 0
