from __future__ import annotations

import json

from openai import AsyncOpenAI

from app.config import get_settings

ROUTES = {
    "clinical_fact",
    "drug_interaction",
    "guideline_lookup",
    "general_medical",
    "out_of_scope",
}

SYSTEM_PROMPT = """Classify a user query for a clinical RAG assistant.
Return only JSON: {"route": "..."}.
Routes:
- clinical_fact: factual clinical or biomedical question
- drug_interaction: medication interaction or contraindication question
- guideline_lookup: clinical guideline, recommendation, diagnostic criteria question
- general_medical: broad medical education question
- out_of_scope: non-medical, personal diagnosis, emergency, legal, finance, or unsupported request

Examples:
Q: Does warfarin interact with amiodarone?
A: {"route": "drug_interaction"}
Q: What are diagnostic criteria for diabetes?
A: {"route": "guideline_lookup"}
Q: Write my tax return.
A: {"route": "out_of_scope"}"""


def heuristic_route(query: str) -> str:
    text = query.lower()
    if any(term in text for term in ["stock", "tax", "weather", "write code", "lawsuit"]):
        return "out_of_scope"
    if any(term in text for term in ["interaction", "contraindication", "interact", "drug"]):
        return "drug_interaction"
    if any(term in text for term in ["guideline", "criteria", "recommendation", "screening"]):
        return "guideline_lookup"
    if any(term in text for term in ["symptom", "diagnosis", "treatment", "disease", "clinical"]):
        return "clinical_fact"
    return "general_medical"


async def route_query(query: str) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        return heuristic_route(query)
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=settings.llm_model,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
    )
    content = response.choices[0].message.content or "{}"
    try:
        route = json.loads(content).get("route", "general_medical")
    except json.JSONDecodeError:
        route = heuristic_route(query)
    return route if route in ROUTES else "general_medical"
