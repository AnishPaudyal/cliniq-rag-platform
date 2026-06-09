from __future__ import annotations

from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.config import get_settings

SYSTEM_PROMPT = """You are ClinIQ, a clinical knowledge assistant. Answer ONLY from the provided context. If the context is insufficient, say so. Always cite your sources by PMID.

Safety:
- Do not diagnose the user.
- Do not provide emergency instructions beyond advising professional care.
- Use concise clinical language for clinicians, researchers, and students."""


def _messages(query: str, context: str, history: list[dict] | None = None) -> list[dict]:
    history_block = "\n".join(
        f"{turn.get('role', 'user')}: {turn.get('content', '')}" for turn in (history or [])[-10:]
    )
    user_content = f"""Conversation history:
{history_block or 'No prior session history.'}

Retrieved context:
{context or 'No retrieved context.'}

Question:
{query}"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


async def stream_answer(query: str, context: str, history: list[dict] | None = None) -> AsyncIterator[str]:
    settings = get_settings()
    if not settings.openai_api_key:
        yield "The context is available, but OPENAI_API_KEY is not configured for generation. "
        yield "ClinIQ cannot produce an LLM answer in this environment."
        return
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    stream = await client.chat.completions.create(
        model=settings.llm_model,
        temperature=0.1,
        messages=_messages(query, context, history),
        stream=True,
    )
    async for event in stream:
        token = event.choices[0].delta.content
        if token:
            yield token


async def generate_answer(query: str, context: str, history: list[dict] | None = None) -> str:
    chunks = []
    async for token in stream_answer(query, context, history):
        chunks.append(token)
    return "".join(chunks)
