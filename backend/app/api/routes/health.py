from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def live():
    return {"status": "ok"}


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "services": {
            "api": "green",
            "qdrant": "pending",
            "redis": "pending",
            "postgres": "pending",
            "llm": "pending",
        },
    }
