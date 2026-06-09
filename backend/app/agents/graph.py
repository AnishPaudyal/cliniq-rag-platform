from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.agents.generator import generate_answer
from app.agents.hallucination import score_hallucination
from app.agents.retriever import retrieve_context
from app.agents.router import route_query
from app.memory.redis_memory import RedisConversationMemory


class ClinIQState(TypedDict, total=False):
    query: str
    route: str
    retrieved_docs: list[dict]
    answer: str
    hallucination_score: float
    sources: list[dict]
    session_id: str
    context: str
    history: list[dict]
    retry_count: int


async def router_node(state: ClinIQState) -> ClinIQState:
    route = await route_query(state["query"])
    if route == "out_of_scope":
        return {
            **state,
            "route": route,
            "answer": "I can only help with clinical and biomedical knowledge questions grounded in retrieved sources.",
            "retrieved_docs": [],
            "sources": [],
            "hallucination_score": 0.0,
        }
    return {**state, "route": route}


async def retriever_node(state: ClinIQState) -> ClinIQState:
    query = state["query"]
    if state.get("retry_count", 0) > 0:
        query = f"{query} {state.get('route', '')} evidence guideline PubMed"
    docs, context = await retrieve_context(query)
    return {**state, "retrieved_docs": docs, "context": context, "sources": docs}


async def generator_node(state: ClinIQState) -> ClinIQState:
    memory = RedisConversationMemory()
    history = await memory.get_history(state.get("session_id", "default"))
    answer = await generate_answer(state["query"], state.get("context", ""), history)
    await memory.append_turn(state.get("session_id", "default"), "user", state["query"])
    await memory.append_turn(state.get("session_id", "default"), "assistant", answer)
    await memory.close()
    return {**state, "answer": answer, "history": history}


async def hallucination_node(state: ClinIQState) -> ClinIQState:
    score = score_hallucination(state.get("answer", ""), state.get("context", ""))
    return {**state, "hallucination_score": score}


async def response_node(state: ClinIQState) -> ClinIQState:
    return state


def hallucination_route(state: ClinIQState) -> str:
    if state.get("hallucination_score", 0.0) > 0.4 and state.get("retry_count", 0) < 1:
        state["retry_count"] = state.get("retry_count", 0) + 1
        return "retry"
    return "response"


def route_after_router(state: ClinIQState) -> str:
    return "response" if state.get("route") == "out_of_scope" else "retrieve"


def build_graph():
    graph = StateGraph(ClinIQState)
    graph.add_node("ROUTER", router_node)
    graph.add_node("RETRIEVER", retriever_node)
    graph.add_node("GENERATOR", generator_node)
    graph.add_node("HALLUCINATION_CHECKER", hallucination_node)
    graph.add_node("RESPONSE", response_node)
    graph.set_entry_point("ROUTER")
    graph.add_conditional_edges("ROUTER", route_after_router, {"retrieve": "RETRIEVER", "response": "RESPONSE"})
    graph.add_edge("RETRIEVER", "GENERATOR")
    graph.add_edge("GENERATOR", "HALLUCINATION_CHECKER")
    graph.add_conditional_edges(
        "HALLUCINATION_CHECKER",
        hallucination_route,
        {"retry": "RETRIEVER", "response": "RESPONSE"},
    )
    graph.add_edge("RESPONSE", END)
    return graph.compile()
