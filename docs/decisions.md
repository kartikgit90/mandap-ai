# Decisions log

Short record of what we chose and why. Newest first.

| Date | Decision | Why |
| --- | --- | --- |
| 2026-10-04 | Guest access via Firebase Anonymous sign-in; `?demo=1` link signs in automatically | Reviewers can try the product with one click, no password. Each guest gets a private demo wedding; per-request AI cost cap and 2-instance limit bound spend |
| 2026-10-04 | Clean white UI with Wedding Affair orange (#d9702f decorative, #c45a1c for buttons/text) | Match the magazine's brand; deeper shade keeps white button text readable |
| 2026-10-04 | Claude via Anthropic API for now (`LLM_PROVIDER=anthropic`), key in Secret Manager `anthropic-api-key`, read only by the compute service account | Vertex AI Claude quota auto-rejected twice for a new billing account; switch is one setting |
| 2026-10-04 | Website on Firebase App Hosting, backend `mandap-ai`, asia-southeast1 (Singapore) | App Hosting has no Mumbai region; the web server holds no data, all data stays in Mumbai |
| 2026-10-04 | Added `mandap-ai--mandap-ai.asia-southeast1.hosted.app` to Firebase Auth authorized domains | Firebase only allows logins from known sites |
| 2026-10-04 | Backend CORS: only our App Hosting sites and localhost | Browsers must not let other sites call our API with a user's login |
| 2026-10-04 | System fonts instead of Google Fonts | Fewer external downloads, faster load, builds anywhere |
| 2026-10-02 | Granted `Developer Connect Read Token Accessor` to the default compute service account | First build failed with 403 fetching the GitHub token; least-privilege fix instead of Admin |
| 2026-10-02 | Cloud Run service `mandap-api`, asia-south1, public ingress, min 0 / max 2 instances, auto-deploy from `main` via Developer Connect | Pay only per request; cap cost; app checks Firebase tokens itself |
| 2026-10-02 | Firestore Standard edition, `(default)` database, asia-south1, production mode | Free tier, vector search, data in India, locked by default |
| 2026-10-02 | Cloud Storage bucket in asia-south1, Standard class | Keep files next to the database and in India; files are read often |
| 2026-10-02 | Firebase Auth: Google + Email/Password; phone OTP later | Easiest sign-up; SMS costs money |
| 2026-10-02 | Google Analytics off | Own event log in BigQuery; avoids cookie consent work |
| 2026-10-02 | LLM provider switch (`LLM_PROVIDER`) | Vertex quota pending for new project; use Anthropic API meanwhile |
| 2026-10-02 | Python FastAPI backend, Next.js front end | Python leads for RAG, parsing, evals; one TS front end |
| 2026-10-02 | Claude Haiku 4.5 (most work) + Sonnet 5.5 (planner) | Cost vs quality balance |
