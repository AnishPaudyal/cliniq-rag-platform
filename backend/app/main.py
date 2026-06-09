import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from app.api.routes import auth, feedback, health, query
from app.config import get_settings

settings = get_settings()
logger = structlog.get_logger("cliniq")
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_starting", service="cliniq-backend")
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
