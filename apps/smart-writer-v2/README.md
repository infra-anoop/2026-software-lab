# Smart Writer V2 (worker + Vercel BFF)

Registry id: `smart-writer-v2`. FastAPI worker on Railway (lab cattle). Chat UI + BFF is Next.js (`web/`); Vercel cattle is T067 / not required for worker `/health`.

Copy `.env.example` → `.env` in this directory (gitignored). Never commit values.

## In-memory / restart (A9)

Conversations, `InternalRunState`, and `JobRunner` jobs live in **this process only**. A worker restart drops them. Multiple Railway replicas do **not** share state — keep replica count **1**. Durable store is plan P3, not MVP.

## Local worker

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

## Local UI (optional)

The BFF at `web/app/api/proxy/[...path]/route.ts` reads `SMART_WRITER_V2_AUDIT_SECRET` from **server** env only. Do **not** add `NEXT_PUBLIC_*` for that secret.

```bash
cd apps/smart-writer-v2/web
# same audit secret as the worker; worker URL defaults to http://127.0.0.1:8080
SMART_WRITER_V2_AUDIT_SECRET=… SMART_WRITER_V2_WORKER_URL=http://127.0.0.1:8080 npm run dev
```

Open the Next origin, not port 8080. Needs Node (`nix develop` if `node` is missing).

## Production (Railway worker)

Git declares the service; workflows already exist. **Do not** `git tag v*` to ship this app alone (that deploys every `publish_container` app).

One-app path: packet `notes/packets/2026-09-17-swv2-railway-bootstrap.md` and `deploy/railway/README.md`.

- Config: `deploy/railway/production/smart-writer-v2.yml`
- Smoke: `GET /health` (no secrets). `/ready` needs `OPENAI_API_KEY` on the service.
