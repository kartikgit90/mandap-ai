# Wedding Affair AI Planner

**An AI wedding planning prototype built for Wedding Affair.**
It turns the magazine's content and advertiser network into two working AI services for couples.

> Prototype. Brand names, products and prices are demo data. In production they come from the magazine's own advertisers and editors.

## What a couple can do

| Service | What the AI does | What the couple approves |
| --- | --- | --- |
| **Shop the Look** | An AI stylist builds complete looks (outfit, jewellery, accessories) for each function from brands featured in the magazine, within the couple's budget, checks delivery time against the wedding date, and links each look to the issue it appeared in. | Sending an enquiry to a brand. The agent only drafts it. |
| **Destination weddings** | A destination planner compares places for the couple's guest count and month, estimates the budget line by line from verified price bands, and suggests concrete changes to bring it under budget. | Applying a change to the plan. The agent only proposes it. |

| **Knowledge base** (magazine team) | Editors upload articles and fact sheets (paste, .txt, .md, .pdf) and tag each with a trust tier. Documents are split into passages and indexed by meaning (RAG); the agents answer from them and cite the source. A built-in tester shows exactly what the AI receives for a question and what the tier rule held back. | Tier changes and uploads are editor-only. |

Other services (vendors, budget, checklist, astrology, honeymoon, beauty, home and gifting) appear as "Coming soon".

## Why it matters for the magazine

- **Content becomes a product.** Every look links back to the article it came from.
- **Advertisers get qualified leads.** Each enquiry carries the couple's function, date and budget.
- **Trust is built in.** Every answer shows its sources and how trusted they are.

## How the AI is kept safe and accurate

- **Knowledge tiers.** Every piece of knowledge is tagged:
  `verified` (editor-approved facts), `published` (articles), `internal` (e.g. brand commissions), `confidential` (contracts, contacts).
  Couples and the AI only ever see `verified` and `published`. This is enforced in code (`api/app/knowledge.py`, `api/app/rag.py`): Firestore filters on the tier before the similarity search, and the code checks it again afterwards. Covered by tests.
- **Grounded answers (RAG).** Style and destination advice comes from the magazine's own passages, retrieved by meaning with Google embeddings and Firestore vector search. Weak matches are dropped, so the AI says it doesn't know rather than guessing.
- **No made-up products or prices.** The stylist can only show products returned by the catalogue tool; looks are re-priced on the server.
- **No made-up budgets.** Destination budgets are calculated in code from verified price bands, not by the AI.
- **Human approval.** Agents create drafts and proposals; only the couple's button press sends or applies them.
- **Limits.** Each request has a step limit and a cost cap; every AI call logs tokens and cost in rupees.

## Architecture

```
Next.js web app (Firebase App Hosting)
        │  HTTPS + Firebase login token
        ▼
Python FastAPI on Cloud Run (Mumbai)
   ├── Auth: Firebase ID tokens, roles (couple / editor / admin)
   ├── Agents: Claude tool use (stylist, destination planner)
   ├── Knowledge base with trust tiers + RAG (Google embeddings, Firestore vector search)
   └── Firestore (Mumbai): looks, enquiries, plans per couple
        │
        ▼
Claude (Haiku 4.5) via Anthropic API, switchable to Google Vertex AI with one setting
```

| Layer | Choice |
| --- | --- |
| Front end | Next.js, TypeScript, Tailwind |
| Backend | Python, FastAPI, Cloud Run (asia-south1) |
| AI | Claude with tool use; prompt caching; provider switch (`LLM_PROVIDER`) |
| Data | Firestore (asia-south1), Cloud Storage |
| RAG | `gemini-embedding-001` on Vertex AI (768 dims), Firestore vector index, ~500-char passages |
| Auth | Firebase Auth (Google, email, one-click guest demo) |
| Secrets | Google Secret Manager |
| Deploy | Push to `main` → Cloud Build → Cloud Run, and App Hosting for the web |

## Code map

```
api/app/knowledge.py         catalogue, tier rules, budget maths
api/app/rag.py               RAG: chunking, embeddings, vector search, tier filter
api/app/kb_routes.py         knowledge base console API (upload, re-tier, search tester)
api/app/agents/stylist.py    Shop the Look agent: tools and prompt
api/app/agents/destination.py  Destination agent: tools and prompt
api/app/llm.py               Claude connection, agent loop, limits, cost tracking
api/app/routes.py            API endpoints
api/app/data/                demo catalogue, articles, destination price bands
api/tests/                   36 tests: tiers, RAG, approval gates, limits, auth
web/src/app/                 Home, Shop the Look, Destination weddings, Knowledge base pages
docs/decisions.md            every decision and why
```

## Run locally

```bash
# backend
cd api && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
STORE_BACKEND=memory EMBED_BACKEND=hash ANTHROPIC_API_KEY=... uvicorn app.main:app --reload --port 8080
pytest

# web
cd web && npm install && npm run dev
```
