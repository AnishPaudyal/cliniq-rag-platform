# ClinIQ Documentation

## 1. PROJECT OVERVIEW

ClinIQ is a clinical knowledge AI assistant built to retrieve, synthesize, and cite biomedical evidence from PubMed abstracts and clinical guideline-style content. The platform is designed for clinicians, researchers, and medical students who need fast, grounded answers from dense medical literature without losing traceability to source documents.

The project was built as a production-grade AI portfolio system for Anish Paudyal. It demonstrates enterprise GenAI engineering across ingestion, retrieval, reranking, agent orchestration, hallucination detection, streaming APIs, authentication, evaluation, CI/CD, and deployment. ClinIQ solves a common RAG problem in healthcare: standard search returns raw papers, while generic chatbots can produce uncited or unsupported medical claims. ClinIQ constrains answers to retrieved context and reports source PMIDs and grounding metadata.

## 2. TECHNICAL ARCHITECTURE

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

Ingestion pipeline: `pubmed_fetcher.py` queries NCBI E-utilities for 500+ abstracts across clinical guidelines, drug interactions, evidence-based medicine, and diagnostic criteria. It parses PMID, title, abstract, authors, publication date, MeSH terms, and PubMed URLs, then saves raw JSON to `data/raw/`.

Chunking: `chunker.py` implements fixed-size, sentence-boundary, and semantic chunking. Chunk counts and average lengths are logged to MLflow. Sentence-boundary chunking is the default because it preserves clinical meaning while avoiding overly long retrieval units.

Embeddings and vector storage: `embedder.py` batches OpenAI `text-embedding-3-small` calls with retry and exponential backoff, then upserts vectors to Qdrant with source metadata payloads.

Hybrid retrieval: `hybrid_search.py` performs dense Qdrant search and lexical BM25 search, combines top-20 results from each with Reciprocal Rank Fusion, logs latency and fusion scores, and returns top-10 candidates.

Reranking: `reranker.py` loads `cross-encoder/ms-marco-MiniLM-L-6-v2` once and rescored fused candidates against the user query, returning top-5 passages.

LangGraph: `graph.py` defines `ROUTER -> RETRIEVER -> GENERATOR -> HALLUCINATION_CHECKER -> RESPONSE`. If hallucination score exceeds 0.4, the graph retries retrieval with an expanded evidence-oriented query.

Router: `router.py` classifies queries into `clinical_fact`, `drug_interaction`, `guideline_lookup`, `general_medical`, and `out_of_scope` using GPT-4o-mini with few-shot examples. Out-of-scope queries short-circuit to a refusal.

Generator: `generator.py` uses a strict system prompt: answer only from context, say when context is insufficient, and cite PMIDs. It supports token streaming for FastAPI SSE.

Hallucination detection: `hallucination.py` splits the answer into sentences and scores grounding against retrieved context with `cross-encoder/nli-deberta-v3-small`. The score is the fraction of answer sentences with entailment below 0.5.

Redis memory: `redis_memory.py` stores the last 10 turns per session as JSON objects with a 24-hour TTL, then injects history into generation context.

Auth and streaming: FastAPI routes implement JWT registration/login, protected query endpoints, SSE response streaming, feedback capture, and service health checks.

Evaluation: RAGAS evaluates faithfulness, answer relevancy, context recall, and context precision. DeepEval adds hallucination, relevancy, and contextual precision checks. MLflow records chunking, retrieval, reranking, and evaluation metrics.

## 3. CHUNKING EXPERIMENTS

Fixed-size chunking: 512-token chunks with 50-token overlap. This strategy is predictable and simple, but it can split clinical statements across boundaries.

Sentence-boundary chunking: groups complete sentences up to a target token budget. This is the default because it preserves clinical claims, citations, and diagnostic criteria more cleanly than fixed windows.

Semantic chunking: embeds sentences with SentenceTransformers and groups adjacent sentences above a cosine similarity threshold. This can produce coherent topical chunks, but it adds local model cost and can fragment short abstracts.

Metrics compared:

| Strategy | Chunk count | Avg length | Retrieval quality |
|---|---:|---:|---|
| Fixed-size | logged to MLflow | logged to MLflow | baseline |
| Sentence-boundary | logged to MLflow | logged to MLflow | selected default |
| Semantic | logged to MLflow | logged to MLflow | experimental |

Final rationale: sentence-boundary chunking is the best default for PubMed abstracts because abstracts are already concise and sentence-level boundaries preserve clinical meaning without requiring extra semantic model latency.

## 4. EVALUATION RESULTS

| Metric | Score |
|---|---:|
| RAGAS faithfulness | `[X]` |
| RAGAS answer relevancy | `[X]` |
| RAGAS context recall | `[X]` |
| RAGAS context precision | `[X]` |
| Hallucination rate | `[X]` |
| Latency p50 | `[X]` ms |
| Latency p95 | `[X]` ms |

| Configuration | Faithfulness | Hallucination rate | Avg latency |
|---|---:|---:|---:|
| Dense only, no reranker | `[X]` | `[X]` | `[X]` |
| Hybrid, no reranker | `[X]` | `[X]` | `[X]` |
| Hybrid + reranker | `[X]` | `[X]` | `[X]` |

Metrics are placeholders until ingestion and evaluation are run with live services and `OPENAI_API_KEY`.

## 5. DESIGN DECISIONS

LangGraph over a simple chain: ClinIQ needs explicit routing, retrieval, generation, hallucination scoring, and retry behavior. LangGraph makes those states inspectable and extensible.

Hybrid search over pure dense search: clinical queries often contain exact drug names, acronyms, diagnostic thresholds, or MeSH-style terms. BM25 preserves exact matching while Qdrant captures semantic similarity. RRF combines both without requiring score normalization.

Cross-encoder reranker over LLM reranking: a local cross-encoder is cheaper, lower latency, deterministic, and avoids spending LLM tokens on every candidate ranking pass.

Redis for memory: conversation history is short-lived, session-scoped, and latency-sensitive. Redis list operations and TTLs fit that access pattern cleanly.

Qdrant over FAISS: Qdrant provides a production service API, metadata payload filtering, persistence, Docker deployment, and easier cloud migration than an embedded FAISS index.

## 6. INSTALLATION & SETUP

1. Clone the repository.
2. Copy `.env.example` to `.env`.
3. Fill in `OPENAI_API_KEY`, `JWT_SECRET`, and service URLs.
4. Run `docker compose up --env-file .env --build`.
5. Visit `http://localhost:8000/health`.
6. Register through the frontend or `POST /auth/register`.
7. Ask a clinical question through the React UI.
8. Run `make eval` after ingestion completes.

## 7. API REFERENCE

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `/health/live` | No | none | `{status}` |
| GET | `/health` | No | none | service status map |
| POST | `/auth/register` | No | `{email,password}` | `{access_token,token_type}` |
| POST | `/auth/login` | No | `{email,password}` | `{access_token,token_type}` |
| POST | `/query` | Yes | `{query,session_id}` | SSE `token` and `done` events |
| GET | `/query/history/{session_id}` | Yes | none | last 10 turns |
| POST | `/feedback` | Yes | `{query_id,rating,comment,thumbs}` | stored feedback id |
| GET | `/feedback/summary` | Admin | none | avg rating and complaints |

## 8. STAR STORY (for job interviews)

SITUATION:
"During my graduate research at the University of Central Oklahoma, I recognized that clinical researchers and students had no efficient way to query the dense body of published medical literature. Standard search tools return raw papers but provide no synthesized, grounded answers — and existing chatbot solutions hallucinate medical facts at unacceptable rates."

TASK:
"I designed and built ClinIQ, a production-grade multi-agent RAG platform capable of ingesting 500+ PubMed abstracts, performing hybrid semantic and lexical retrieval, orchestrating a multi-agent answer pipeline with built-in hallucination detection, and serving grounded clinical answers through a real-time streaming UI — all containerized and deployed to the cloud."

ACTION:

- Implemented PubMed ingestion using NCBI E-utilities, parsing abstract metadata and storing raw corpora for reproducibility.
- Built three chunking strategies and logged chunking metrics to MLflow to choose sentence-boundary chunking.
- Implemented hybrid retrieval with Qdrant dense search, BM25 lexical search, and Reciprocal Rank Fusion.
- Added a local cross-encoder reranker to improve top-k evidence quality without extra LLM cost.
- Orchestrated the pipeline with LangGraph nodes for routing, retrieval, generation, hallucination checking, and retry.
- Added sentence-level hallucination scoring with an NLI cross-encoder and grounded answer metadata.
- Built protected FastAPI SSE endpoints and a React/Tailwind streaming UI with citations and feedback.
- Containerized the stack with Docker Compose and added GitHub Actions plus Render deployment configuration.

RESULT:
ClinIQ indexes `[X]` PubMed documents, evaluates on `[X]` generated clinical QA pairs, reaches RAGAS faithfulness `[X]`, reports hallucination rate `[X]`, and averages `[X]` ms response latency after retrieval and reranking.

## 9. COMMON INTERVIEW QUESTIONS & ANSWERS

Walk me through the architecture of this project.
ClinIQ ingests PubMed abstracts, chunks them, embeds chunks with OpenAI, and stores vectors in Qdrant while also building a BM25 index. At query time, FastAPI authenticates the user, LangGraph routes the query, hybrid retrieval fuses dense and lexical candidates, a cross-encoder reranks them, GPT-4o-mini generates a cited answer from context, and an NLI model scores hallucination risk. The frontend streams tokens and displays source cards.

Why did you use hybrid search instead of just vector search?
Clinical queries often include exact entities like drug names, thresholds, acronyms, and guideline terms. Dense search is good for semantic similarity, but BM25 is better at exact lexical matching. RRF lets the system combine both rankings without fragile score normalization.

How do you detect and handle hallucinations?
The answer is split into sentences. Each sentence is checked against retrieved context using an NLI cross-encoder. If too many sentences are unsupported, the hallucination score exceeds 0.4 and the graph retries retrieval with an expanded evidence query.

How did you evaluate your RAG system?
The evaluation pipeline builds a 50-question dataset from PubMed content, runs generated answers through RAGAS metrics, adds DeepEval hallucination and relevancy checks, and logs scores to MLflow with retriever and reranker configuration.

What would you change if you had more time?
I would add clinician-reviewed evaluation labels, guideline PDF ingestion, role-based admin dashboards, better automated regression datasets, and deployment-specific observability with traces and dashboards.

How does this scale to millions of documents?
I would shard Qdrant collections, move ingestion to background workers, store BM25 in a distributed lexical engine such as OpenSearch, cache frequent queries, batch embeddings asynchronously, and add document-level filters by date, specialty, and guideline type.

## 10. LESSONS LEARNED

The hardest part of clinical RAG is not only retrieving relevant text; it is preserving source fidelity under generation pressure. Clinical language is dense, and small differences in wording can change the meaning of an answer.

Hybrid retrieval worked well because it matches how biomedical queries behave. Exact terms matter, but so does semantic phrasing. RRF provided a simple and robust way to combine both retrieval modes.

The agent graph made the pipeline easier to reason about than a single chain. Routing, retrieval, generation, and hallucination scoring each have distinct failure modes, and separating them makes retries and observability more practical.

Evaluation needs to be treated as a product feature, not a final report. MLflow, RAGAS, and DeepEval make it possible to compare chunking and retrieval decisions over time instead of relying on manual spot checks.

If I extended this further, I would prioritize human-labeled clinical evaluation data, guideline PDF ingestion, and stricter medical safety policies before any production use in a care setting.
