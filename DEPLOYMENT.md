# ClinIQ Deployment

## Run Locally

1. Copy `.env.example` to `.env`.
2. Set `OPENAI_API_KEY` and replace `JWT_SECRET` with a long random value.
3. Start the stack:

```bash
docker compose up --env-file .env --build
```

4. Open the frontend at `http://localhost:5173`.
5. Confirm backend health at `http://localhost:8000/health`.

The first backend startup creates PostgreSQL tables, ensures the Qdrant collection exists, runs PubMed ingestion when the collection is empty and `OPENAI_API_KEY` is present, embeds chunks, and builds the BM25 index.

## Required Environment Variables

- `OPENAI_API_KEY`
- `POSTGRES_URL`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `REDIS_URL`
- `QDRANT_URL`
- `QDRANT_COLLECTION`
- `JWT_SECRET`
- `MLFLOW_TRACKING_URI`
- `FRONTEND_ORIGIN`
- `BACKEND_URL`

## Deploy to Render

1. Create managed PostgreSQL, Redis, and Qdrant services or point Render to externally hosted equivalents.
2. Create a Render web service from this repository using the `backend/Dockerfile` or import `render.yaml`.
3. Add all required environment variables in Render. Store secrets as Render secret values, not in the repository.
4. Create a Render deploy hook and save it as the GitHub Actions secret `RENDER_DEPLOY_HOOK`.
5. Push to `main`; `.github/workflows/deploy.yml` triggers the Render deployment hook.

## Evaluation and MLflow

Run:

```bash
make eval
```

The target runs RAGAS, DeepEval, and starts the MLflow UI at `http://localhost:5000`.
