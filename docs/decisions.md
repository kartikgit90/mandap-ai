# Decisions log

Short record of what we chose and why. Newest first.

| Date | Decision | Why |
| --- | --- | --- |
| 2026-10-02 | Granted `Developer Connect Read Token Accessor` to the default compute service account | First build failed with 403 fetching the GitHub token; least-privilege fix instead of Admin |
| 2026-10-02 | Cloud Run service `mandap-api`, asia-south1, public ingress, min 0 / max 2 instances, auto-deploy from `main` via Developer Connect | Pay only per request; cap cost; app checks Firebase tokens itself |
| 2026-10-02 | Firestore Standard edition, `(default)` database, asia-south1, production mode | Free tier, vector search, data in India, locked by default |
| 2026-10-02 | Cloud Storage bucket in asia-south1, Standard class | Keep files next to the database and in India; files are read often |
| 2026-10-02 | Firebase Auth: Google + Email/Password; phone OTP later | Easiest sign-up; SMS costs money |
| 2026-10-02 | Google Analytics off | Own event log in BigQuery; avoids cookie consent work |
| 2026-10-02 | LLM provider switch (`LLM_PROVIDER`) | Vertex quota pending for new project; use Anthropic API meanwhile |
| 2026-10-02 | Python FastAPI backend, Next.js front end | Python leads for RAG, parsing, evals; one TS front end |
| 2026-10-02 | Claude Haiku 4.5 (most work) + Sonnet 5.5 (planner) | Cost vs quality balance |
