# Smart Writer V2

Registry id: `smart-writer-v2`. **One** Railway service (D5 re-lock 2026-09-21): FastAPI `/v1` + served Next UI (v0 design) **same-origin**. Preview gate = **V1-style** (user enters shared secret; browser sends `X-Audit-Secret`).

> Prior “second service `smart-writer-v2-ui` + BFF custody” is **superseded**. Packet: `notes/packets/2026-09-21-swv2-d5-one-service-ui.md` (T069).

Copy `.env.example` → `.env` in this directory (gitignored). Never commit values.

## In-memory / restart (A9)

Conversations, `InternalRunState`, and `JobRunner` jobs live in **this process only**. A worker restart drops them. Multiple Railway replicas do **not** share state — keep replica count **1**. Durable store is plan P3, not MVP.

## Local API + UI (same origin)

```bash
cd apps/smart-writer-v2 && uv sync --locked
# .env: OPENAI_API_KEY, SMART_WRITER_V2_AUDIT_SECRET; optional TAVILY_API_KEY

# Build Next static export into app/static/ui (needs Node — e.g. nix-shell -p nodejs_22)
cd web && npm ci && npm run build:fastapi && cd ..

uv run uvicorn app.entrypoints.http:app --reload --host 0.0.0.0 --port 8080
# Open http://127.0.0.1:8080/  — Settings → preview secret → chat
curl -sS http://127.0.0.1:8080/health   # public; process up
curl -sS http://127.0.0.1:8080/ready    # 200 iff OPENAI_API_KEY set (no OpenAI call)
```

Protected `/v1` routes need header `X-Audit-Secret` matching `SMART_WRITER_V2_AUDIT_SECRET`. Unset secret → 503 on those routes. The UI stores the typed secret in `sessionStorage` and sends that header (no BFF).

```bash
uv run pytest
uv run ruff check app/ tests/
```

## Local UI (dev hot-reload)

For polish only (API still on `:8080`; CORS not required if you only use same-origin serve):

```bash
cd apps/smart-writer-v2/web && npm run dev
```

Prefer `build:fastapi` + uvicorn for the product path.

## Image / ship (UI in worker)

Nix cattle copies `apps/smart-writer-v2` as-is. **Commit refreshed `app/static/ui/`** after UI source changes (`npm run build:fastapi`), then:

```bash
nix build .#container-smart-writer-v2 --option sandbox false
# Ship/deploy (human if Codespace lacks actions:write):
#   gh workflow run ship-registry.yml -f app_id=smart-writer-v2 \
#     -f nix_attr=container-smart-writer-v2 -f image_name=smart-writer-v2
#   gh workflow run deploy.yml -f app_id=smart-writer-v2 -f tag=latest -f environment=production
#   gh workflow run smoke-test.yml -f app_id=smart-writer-v2 -f environment=production
```

Do **not** publish `smart-writer-v2-ui`.

## Production

- Service: `smart-writer-v2` — `https://smart-writer-v2-production.up.railway.app`
- Cattle: `deploy/railway/production/smart-writer-v2.yml`
- Secret: Infisical → A23 sync onto **this** service only (users type the same value in Settings)
