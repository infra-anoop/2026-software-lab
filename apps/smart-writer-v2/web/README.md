# Smart Writer V2 — Next.js UI + BFF (Railway)

**Production host:** Railway service `smart-writer-v2-ui` (project `2026-software-lab`).  
**Design:** in-repo v0-class pass on chat + Settings (literal Vercel v0 export optional later).  
**Not production:** Vercel hosting, Codespaces-only dogfood.

Browser talks **only** to same-origin Next routes; the BFF attaches the preview secret and proxies to the FastAPI worker.

## Cattle

| Piece | Path |
|-------|------|
| Railway YAML | `deploy/railway/production/smart-writer-v2-ui.yml` |
| Image | Docker `apps/smart-writer-v2/web/Dockerfile` → `ghcr.io/<owner>/smart-writer-v2-ui` (standalone Next) |
| First-ship steps | `deploy/railway/README.md` § Smart Writer V2 UI |

Worker stays `smart-writer-v2` (Nix/registry). UI is **Docker-only** for now — not in `apps/registry.yaml` (avoids a Node ship-matrix epic).

## Env names (server only)

Set on the **Railway UI service** (or local `.env.local`). **Never** prefix with `NEXT_PUBLIC_`.

| Name | Where used | Notes |
|------|------------|--------|
| `SMART_WRITER_V2_AUDIT_SECRET` | `app/api/proxy/[...path]/route.ts` | Same shared secret as the worker preview gate. Server-only; unset → BFF returns 503. |
| `SMART_WRITER_V2_WORKER_URL` | same BFF route | Base URL of the FastAPI worker (no trailing slash). Local default: `http://127.0.0.1:8080`. Production: `https://smart-writer-v2-production.up.railway.app`. |

Worker secret **name** is in `deploy/secrets/schema.yaml` (Infisical → Railway **worker** via A23 / ops tags). Until UI is registry-wired, paste the same audit secret onto `smart-writer-v2-ui` Variables manually. `SMART_WRITER_V2_WORKER_URL` is plain config, not vault.

## Settings (D4 / T065)

Header **Settings** holds chat preferences. First preference: **citation format**
(`panel` | `inline` | `footnotes` | `combo`). Default is **sources panel**. The
value is sent as `citation_mode` on each turn; citation UI is hidden when a draft
has no sources (FR-010a).

## Local (dev only)

```bash
# Terminal A — worker
cd apps/smart-writer-v2 && uv sync --locked
# set SMART_WRITER_V2_AUDIT_SECRET + OPENAI_API_KEY in app `.env`
uv run uvicorn app.entrypoints.http:app --reload --host 0.0.0.0 --port 8080

# Terminal B — UI
cd apps/smart-writer-v2/web
# .env.local: SMART_WRITER_V2_AUDIT_SECRET=<same> SMART_WRITER_V2_WORKER_URL=http://127.0.0.1:8080
npm install && npm run dev
```

## Production image (Docker)

```bash
cd apps/smart-writer-v2/web
docker build -t ghcr.io/<owner>/smart-writer-v2-ui:latest .
docker push ghcr.io/<owner>/smart-writer-v2-ui:latest
gh workflow run deploy.yml \
  -f app_id=smart-writer-v2-ui \
  -f tag=latest \
  -f environment=production
```

See `deploy/railway/README.md` for service provision + Variables.

## Out of scope here

- Expanding `apps/registry.yaml` / Nix `container-*` for Node (platform epic).
- Literal paid Vercel v0 session (optional human polish).
- Infisical→UI A23 sync until UI has a registry deploy target.
