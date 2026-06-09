import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

from app.api.limiter import limiter
from app.api.routes import auth, feedback, health, query
from app.config import get_settings
from app.db.postgres import init_db
from app.ingestion.chunker import chunk_documents
from app.ingestion.embedder import embed_and_store
from app.ingestion.pubmed_fetcher import fetch_pubmed_corpus
from app.retrieval.bm25_index import build_bm25_from_qdrant
from app.retrieval.qdrant_client import collection_count, ensure_collection

settings = get_settings()
logger = structlog.get_logger("cliniq")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_starting", service="cliniq-backend")
    try:
        await init_db()
        ensure_collection()
        if collection_count() == 0 and settings.openai_api_key:
            logger.info("startup_ingestion_begin")
            corpus = await fetch_pubmed_corpus(target_count=500)
            chunks = chunk_documents(corpus, strategy="sentence_boundary")
            await embed_and_store(chunks)
        if collection_count() > 0:
            build_bm25_from_qdrant()
    except Exception as exc:
        logger.warning("startup_ingestion_skipped_or_failed", error=str(exc))
    yield
    logger.info("app_stopping", service="cliniq-backend")


app = FastAPI(
    title="ClinIQ Clinical Knowledge AI Assistant",
    description="Production-grade multi-agent RAG platform for clinical and biomedical knowledge retrieval.",
    version="0.1.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        latency_ms=latency_ms,
        client=request.client.host if request.client else None,
    )
    return response


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(query.router)
app.include_router(feedback.router)
