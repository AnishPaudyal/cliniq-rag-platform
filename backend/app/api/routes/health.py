import httpx
import redis.asyncio as redis
from fastapi import APIRouter
from openai import AsyncOpenAI
from sqlalchemy import text

from app.config import get_settings
from app.db.postgres import engine

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def live():
    return {"status": "ok"}


@router.get("/health")
async def health():
    settings = get_settings()
    services = {}
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(f"{settings.qdrant_url}/healthz")
        services["qdrant"] = "green" if response.status_code == 200 else "red"
    except Exception:
        services["qdrant"] = "red"

    try:
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        services["redis"] = "green" if await redis_client.ping() else "red"
        await redis_client.aclose()
    except Exception:
        services["redis"] = "red"

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["postgres"] = "green"
    except Exception:
        services["postgres"] = "red"

    try:
        if settings.openai_api_key:
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            await client.models.retrieve(settings.llm_model)
            services["llm"] = "green"
        else:
            services["llm"] = "not_configured"
    except Exception:
        services["llm"] = "red"

    overall = "ok" if all(value in {"green", "not_configured"} for value in services.values()) else "degraded"
    return {
        "status": overall,
        "services": {"api": "green", **services},
    }
