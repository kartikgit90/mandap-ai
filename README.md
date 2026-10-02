# Mandap AI

AI wedding planner for Indian couples, grounded in a tiered knowledge base.

## Stack

| Layer | Choice |
| --- | --- |
| Front end | Next.js (TypeScript) on Firebase App Hosting |
| Backend | Python, FastAPI, on Cloud Run (asia-south1) |
| LLM | Claude (Haiku 4.5, Sonnet 5.5) on Vertex AI, or the Anthropic API during development |
| Database | Firestore (asia-south1), with vector search for RAG |
| Files | Cloud Storage (asia-south1) |
| Login | Firebase Auth (Google, Email/Password), roles via custom claims |
| Analytics | BigQuery |

## Folders

```
api/     Python backend (FastAPI): APIs, agents, RAG, ingestion
web/     Next.js front end: couples app + admin console (coming next)
evals/   Test questions and scoring scripts (coming later)
docs/    Notes and decisions
```

## Run the backend locally

```bash
cd api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env        # then fill in values
uvicorn app.main:app --reload --port 8080
```

Open http://localhost:8080/health and http://localhost:8080/docs.

## Tests

```bash
cd api && pytest
```
