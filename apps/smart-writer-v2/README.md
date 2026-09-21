# Smart Writer V2

Registry id: `smart-writer-v2`. **One** Railway service (D5 re-lock 2026-09-21): FastAPI `/v1` + served Next UI (v0 design) **same-origin**. Preview gate = **V1-style** (user enters shared secret; browser sends `X-Audit-Secret`).

> Prior “second service `smart-writer-v2-ui` + BFF custody” is **superseded**. Implement: `notes/packets/2026-09-21-swv2-d5-one-service-ui.md` (T069).

Copy `.env.example` → `.env` in this directory (gitignored). Never commit values.

## In-memory / restart (A9)

Conversations, `InternalRunState`, and `JobRunner` jobs live in **this process only**. A worker restart drops them. Multiple Railway replicas do **not** share state — keep replica count **1**. Durable store is plan P3, not MVP.

## Local API

```bash
cd apps/smart-writer-v2 && uv sync --locked
# .env: OPENAI_API_KEY, SMART_WRITER_V2_AUDIT_SECRET; optional TAVILY_API_KEY
uv run uvicorn app.entrypoints.http:app --reload --host 0.0.0.0 --port 8080
curl -sS http://127.0.0.1:8080/health   # public; process up
curl -sS http://127.0.0.1:8080/ready    # 200 iff OPENAI_API_KEY set (no OpenAI call)
```

Protected routes need header `X-Audit-Secret` matching `SMART_WRITER_V2_AUDIT_SECRET`. Unset secret → 503 on those routes.

```bash
uv run pytest
uv run ruff check app/ tests/
```

## Local UI (dev)

Until T069 lands same-origin serve from FastAPI, you may still run Next separately for polish:

```bash
cd apps/smart-writer-v2/web
npm run dev
```

Target model after T069: open the **API origin** (e.g. `:8080`); UI is static assets; type the preview secret in the page (V1-style). See `web/README.md`.

## Production

- Service: `smart-writer-v2` — `https://smart-writer-v2-production.up.railway.app`
- Cattle: `deploy/railway/production/smart-writer-v2.yml`
- Secret: Infisical → A23 sync onto **this** service only
