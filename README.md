# ClinIQ

A production-grade multi-agent RAG platform for clinical and biomedical knowledge retrieval.

Live demo URL: TBD after Render deployment.

## Architecture

```text
React + Tailwind UI
        |
        v
FastAPI SSE API -- JWT Auth -- PostgreSQL feedback/users
        |
        v
LangGraph: ROUTER -> RETRIEVER -> GENERATOR -> HALLUCINATION_CHECKER
        |              |              |                |
        |              v              v                v
        |        Hybrid retrieval   GPT-4o-mini     NLI grounding
        |          /        \
        v         v          v
     Redis     Qdrant      BM25
    memory   dense search lexical search
                  ^
                  |
       PubMed ingestion -> chunking -> OpenAI embeddings
```

## Quick Start

```bash
cp .env.example .env
docker compose up --env-file .env --build
```

Frontend: `http://localhost:5173`  
Backend health: `http://localhost:8000/health`  
MLflow: `http://localhost:5000`

## Tech Stack

| Layer | Tools |
|---|---|
| Backend | Python 3.11, FastAPI, structlog, slowapi |
| Agents | LangChain, LangGraph, GPT-4o-mini |
| Retrieval | Qdrant, BM25, Reciprocal Rank Fusion, cross-encoder reranker |
| Ingestion | PubMed E-utilities, OpenAI `text-embedding-3-small`, MLflow |
| Data | PostgreSQL, Redis |
| Evaluation | RAGAS, DeepEval, MLflow |
| Frontend | React 18, Vite, Tailwind CSS |
| DevOps | Docker Compose, GitHub Actions, Render |

## Key Metrics

| Metric | Value |
|---|---:|
| Documents indexed | `[X]` PubMed abstracts |
| RAGAS faithfulness | `[X]` |
| Average response time | `[X]` ms |
| Hallucination rate | `[X]` |

## Screenshots

Placeholder for deployed application screenshots.

## License

MIT
