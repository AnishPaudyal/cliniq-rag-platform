from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from app.agents.generator import stream_answer
from app.agents.hallucination import score_hallucination
from app.agents.retriever import retrieve_context
from app.agents.router import route_query
from app.api.limiter import limiter
from app.auth.jwt_handler import get_current_user
from app.db.models import User
from app.memory.redis_memory import RedisConversationMemory

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    session_id: str = Field(default_factory=lambda: str(uuid4()))


def _sse(event: str, data: dict | str) -> str:
    payload = data if isinstance(data, str) else json.dumps(data)
    return f"event: {event}\ndata: {payload}\n\n"


@router.post("")
@limiter.limit("10/minute")
async def query(request: Request, payload: QueryRequest, user: User = Depends(get_current_user)):
    async def event_stream():
        route = await route_query(payload.query)
        if route == "out_of_scope":
            refusal = "I can only help with clinical and biomedical knowledge questions grounded in retrieved sources."
            yield _sse("token", refusal)
            yield _sse("done", {"query_id": str(uuid4()), "route": route, "sources": [], "hallucination_score": 0.0})
            return

        docs, context = await retrieve_context(payload.query)
        memory = RedisConversationMemory()
        history = await memory.get_history(payload.session_id)
        answer_parts: list[str] = []
        async for token in stream_answer(payload.query, context, history):
            answer_parts.append(token)
            yield _sse("token", token)
        answer = "".join(answer_parts)
        score = score_hallucination(answer, context)
        await memory.append_turn(payload.session_id, "user", payload.query)
        await memory.append_turn(payload.session_id, "assistant", answer)
        await memory.close()
        yield _sse(
            "done",
            {
                "query_id": str(uuid4()),
                "route": route,
                "hallucination_score": score,
                "sources": docs,
            },
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/history/{session_id}")
@limiter.limit("10/minute")
async def history(request: Request, session_id: str, user: User = Depends(get_current_user)):
    memory = RedisConversationMemory()
    turns = await memory.get_history(session_id)
    await memory.close()
    return {"session_id": session_id, "turns": turns}
